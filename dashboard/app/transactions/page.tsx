"use client";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { saveMonth, loadMonth } from "@/lib/month-store";
import type { Transaction, TransactionList, Card, AnalyticsResponse } from "@/lib/types";
import { format, startOfMonth, endOfMonth, addMonths, subMonths, isSameMonth } from "date-fns";
import { ptBR } from "date-fns/locale";

function fmt(v: number) {
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

const CATEGORIES = [
  { key: "alimentacao", label: "Alimentação" },
  { key: "transporte", label: "Transporte" },
  { key: "saude", label: "Saúde" },
  { key: "lazer", label: "Lazer" },
  { key: "compras", label: "Compras" },
  { key: "salario", label: "Salário" },
  { key: "investimento", label: "Investimento" },
  { key: "assinatura", label: "Assinatura" },
  { key: "moradia", label: "Moradia" },
  { key: "pet", label: "Pet" },
  { key: "mercado", label: "Mercado" },
  { key: "vestuario", label: "Vestuário" },
  { key: "cosmeticos", label: "Cosméticos" },
  { key: "presentes", label: "Presentes" },
  { key: "miscelanea", label: "Miscelânea" },
];

const CAT_LABEL: Record<string, string> = Object.fromEntries(
  CATEGORIES.map(({ key, label }) => [key, label])
);

function monthFromParam(param: string | null): Date {
  if (!param) return new Date();
  const [y, m] = param.split("-").map(Number);
  if (!y || !m) return new Date();
  return new Date(y, m - 1, 1);
}

function TransactionsContent() {
  const searchParams = useSearchParams();
  const qc = useQueryClient();
  const limit = 20;

  const [selectedMonth, setSelectedMonth] = useState(() => {
    const param = searchParams.get("month");
    return param ? monthFromParam(param) : new Date();
  });

  useEffect(() => {
    const param = searchParams.get("month");
    const m = param ? monthFromParam(param) : loadMonth();
    saveMonth(m);
    setSelectedMonth(prev =>
      format(prev, "yyyy-MM") === format(m, "yyyy-MM") ? prev : m
    );
  }, []);
  const [filterCategory, setFilterCategory] = useState(searchParams.get("category") ?? "");
  const [filterCard, setFilterCard] = useState(searchParams.get("card_id") ?? "");
  const [filterType, setFilterType] = useState(searchParams.get("type") ?? "");
  const [filterUser, setFilterUser] = useState(searchParams.get("user") ?? "");
  const [page, setPage] = useState(0);
  const [showForm, setShowForm] = useState(false);
  const [sortDir, setSortDir] = useState<"asc" | "desc" | null>(null);
  const [filterOpen, setFilterOpen] = useState(false);
  const activeFilterCount = [filterCategory, filterCard, filterType, filterUser].filter(Boolean).length;

  const isCurrentMonth = isSameMonth(selectedMonth, new Date());
  const start = format(startOfMonth(selectedMonth), "yyyy-MM-dd");
  const end = isCurrentMonth ? format(new Date(), "yyyy-MM-dd") : format(endOfMonth(selectedMonth), "yyyy-MM-dd");

  // Sync URL when filters change
  useEffect(() => {
    const month = format(selectedMonth, "yyyy-MM");
    const params = new URLSearchParams();
    params.set("month", month);
    if (filterCategory) params.set("category", filterCategory);
    if (filterCard) params.set("card_id", filterCard);
    if (filterType) params.set("type", filterType);
    if (filterUser) params.set("user", filterUser);
    window.history.replaceState(null, '', `/transactions?${params.toString()}`);
    setPage(0);
  }, [selectedMonth, filterCategory, filterCard, filterType, filterUser]);

  function buildQuery() {
    const q = new URLSearchParams({ limit: String(limit), offset: String(page * limit), start, end });
    if (filterCategory) q.set("category", filterCategory);
    if (filterCard) q.set("card_id", filterCard);
    if (filterType) q.set("type", filterType);
    if (filterUser) q.set("user", filterUser);
    if (sortDir) { q.set("sort_by", "amount"); q.set("sort_dir", sortDir); }
    return q.toString();
  }

  const { data: analytics } = useQuery<AnalyticsResponse>({
    queryKey: ["analytics", start, end],
    queryFn: () => api.get(`/api/analytics/?start=${start}&end=${end}`),
  });

  const { data: totalsData } = useQuery<TransactionList>({
    queryKey: ["transactions-totals", start, end, filterCategory, filterCard, filterType, filterUser],
    queryFn: () => {
      const q = new URLSearchParams({ limit: "1000", offset: "0", start, end });
      if (filterCategory) q.set("category", filterCategory);
      if (filterCard) q.set("card_id", filterCard);
      if (filterType) q.set("type", filterType);
      if (filterUser) q.set("user", filterUser);
      return api.get(`/api/transactions/?${q.toString()}`);
    },
  });

  const totals = totalsData?.items.reduce(
    (acc, t) => {
      if (t.type === "income") acc.income += t.amount;
      else acc.expenses += t.amount;
      return acc;
    },
    { income: 0, expenses: 0 }
  );

  const availableCategories = analytics?.summary?.by_category
    ? CATEGORIES.filter(({ key }) => key in analytics.summary.by_category)
    : CATEGORIES;

  const { data } = useQuery<TransactionList>({
    queryKey: ["transactions", start, end, filterCategory, filterCard, filterType, filterUser, page, sortDir],
    queryFn: () => api.get(`/api/transactions/?${buildQuery()}`),
  });

  const { data: cards } = useQuery<Card[]>({
    queryKey: ["cards"],
    queryFn: () => api.get("/api/cards/"),
  });

  const defaultDebitCardId = cards?.find(c => c.is_default_debit)?.id ?? "";
  const defaultCreditCardId = cards?.find(c => c.is_default_credit)?.id ?? "";
  const defaultCardId = defaultDebitCardId || defaultCreditCardId || cards?.[0]?.id ?? "";

  const { data: users } = useQuery<string[]>({
    queryKey: ["users"],
    queryFn: () => api.get("/api/users/"),
    staleTime: 5 * 60 * 1000,
  });

  const [form, setForm] = useState({
    date: format(new Date(), "yyyy-MM-dd"),
    type: "expense" as "income" | "expense",
    category: "alimentacao",
    description: "",
    amount: "",
    card_id: "",
    user: "",
  });

  const effectiveCardId = form.card_id || defaultCardId;

  const create = useMutation({
    mutationFn: (body: object) => api.post<Transaction>("/api/transactions/", body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transactions"] });
      setForm((f) => ({ ...f, description: "", amount: "" }));
      setShowForm(false);
    },
  });

  const remove = useMutation({
    mutationFn: (id: string) => api.delete(`/api/transactions/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["transactions"] }),
  });

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState({
    date: "", type: "expense" as "income" | "expense",
    category: "", description: "", amount: "", card_id: "", user: "",
  });

  const update = useMutation({
    mutationFn: ({ id, body }: { id: string; body: object }) =>
      api.patch<Transaction>(`/api/transactions/${id}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transactions"] });
      setEditingId(null);
    },
    onError: (err: Error) => alert(err.message),
  });

  function startEdit(t: Transaction) {
    setEditingId(t.id);
    setEditForm({
      date: t.date,
      type: t.type,
      category: t.category,
      description: t.description,
      amount: String(t.amount),
      card_id: t.card_id ?? "",
      user: t.user ?? "",
    });
  }

  function saveEdit() {
    if (!editingId) return;
    const amount = parseFloat(editForm.amount);
    if (!isFinite(amount) || amount <= 0) return;
    update.mutate({
      id: editingId,
      body: {
        date: editForm.date,
        type: editForm.type,
        category: editForm.category,
        description: editForm.description,
        amount,
        card_id: editForm.card_id || null,
        user: editForm.user.trim() || null,
      },
    });
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const body: Record<string, unknown> = {
      date: form.date,
      type: form.type,
      category: form.category,
      description: form.description,
      amount: parseFloat(form.amount),
      card_id: effectiveCardId,
    };
    if (form.user.trim()) body.user = form.user.trim();
    create.mutate(body);
  }

  const monthLabel = format(selectedMonth, "MMMM yyyy", { locale: ptBR })
    .replace(/^\w/, c => c.toUpperCase());

  async function handleExport() {
    const q = new URLSearchParams({ limit: "1000", offset: "0", start, end });
    if (filterCategory) q.set("category", filterCategory);
    if (filterCard) q.set("card_id", filterCard);
    if (filterType) q.set("type", filterType);
    const result: TransactionList = await api.get(`/api/transactions/?${q.toString()}`);

    const cardMap = Object.fromEntries((cards ?? []).map(c => [c.id, c.name]));
    const rows = [
      ["Data", "Descrição", "Categoria", "Cartão", "Tipo", "Valor (R$)", "Autor"],
      ...result.items.map(t => [
        t.date,
        t.description,
        CAT_LABEL[t.category] ?? t.category,
        t.card_id ? (cardMap[t.card_id] ?? "") : "",
        t.type === "income" ? "Receita" : "Despesa",
        (t.type === "income" ? 1 : -1) * t.amount,
        t.user ?? "",
      ]),
    ];

    const csv = rows.map(r => r.map(v => `"${String(v).replace(/"/g, '""')}"`).join(",")).join("\n");
    const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `transacoes-${format(selectedMonth, "yyyy-MM")}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl font-bold mb-3">Transações</h2>
        <div className="flex gap-2">
          <button
            onClick={handleExport}
            className="border border-gray-700 hover:border-gray-500 text-gray-300 hover:text-white rounded-lg px-4 py-2 text-sm font-medium transition-colors"
          >
            ↓ CSV
          </button>
          <button
            onClick={() => setShowForm(!showForm)}
            className="bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg px-4 py-2 text-sm font-medium transition-colors"
          >
            {showForm ? "Cancelar" : "+ Nova transação"}
          </button>
        </div>
      </div>

      {/* Filtros mobile: mês + botão de filtros */}
      <div className="sm:hidden flex items-center gap-2 mb-4">
        <div className="flex items-center gap-1 flex-1 min-w-0">
          <button onClick={() => { const m = subMonths(selectedMonth, 1); setSelectedMonth(m); saveMonth(m); }}
            className="w-9 h-9 flex items-center justify-center rounded-lg bg-gray-800 text-gray-300 text-xl shrink-0">‹</button>
          <span className="text-sm font-semibold flex-1 text-center truncate">{monthLabel}</span>
          <button onClick={() => { const m = addMonths(selectedMonth, 1); setSelectedMonth(m); saveMonth(m); }}
            disabled={isCurrentMonth}
            className="w-9 h-9 flex items-center justify-center rounded-lg bg-gray-800 text-gray-300 text-xl shrink-0 disabled:opacity-30">›</button>
        </div>
        <button onClick={() => setFilterOpen(true)}
          className="relative flex items-center gap-1.5 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 shrink-0">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="4" y1="6" x2="20" y2="6"/><line x1="8" y1="12" x2="16" y2="12"/><line x1="11" y1="18" x2="13" y2="18"/>
          </svg>
          Filtros
          {activeFilterCount > 0 && (
            <span className="absolute -top-1.5 -right-1.5 bg-emerald-500 text-white text-[10px] w-4 h-4 rounded-full flex items-center justify-center font-bold">
              {activeFilterCount}
            </span>
          )}
        </button>
        <span className="text-xs text-gray-500 shrink-0">{data?.total ?? ""}</span>
      </div>

      {/* Bottom sheet de filtros (mobile) */}
      {filterOpen && (
        <div className="sm:hidden fixed inset-0 z-50 flex flex-col justify-end">
          <div className="absolute inset-0 bg-black/60" onClick={() => setFilterOpen(false)} />
          <div className="relative bg-gray-900 border-t border-gray-800 rounded-t-2xl p-5 pb-10 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-base">Filtros</h3>
              <button onClick={() => setFilterOpen(false)} className="text-gray-400 hover:text-white p-1">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Categoria</label>
              <select value={filterCategory} onChange={e => setFilterCategory(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-sm text-gray-200">
                <option value="">Todas</option>
                {availableCategories.map(({ key, label }) => <option key={key} value={key}>{label}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Cartão</label>
              <select value={filterCard} onChange={e => setFilterCard(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-sm text-gray-200">
                <option value="">Todos</option>
                {cards?.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Tipo</label>
              <select value={filterType} onChange={e => setFilterType(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-sm text-gray-200">
                <option value="">Receitas e despesas</option>
                <option value="income">Só receitas</option>
                <option value="expense">Só despesas</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Usuário</label>
              <select value={filterUser} onChange={e => setFilterUser(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-sm text-gray-200">
                <option value="">Todos</option>
                {users?.map(u => <option key={u} value={u}>{u}</option>)}
              </select>
            </div>
            <div className="flex gap-2 pt-1">
              {activeFilterCount > 0 && (
                <button onClick={() => { setFilterCategory(""); setFilterCard(""); setFilterType(""); setFilterUser(""); }}
                  className="flex-1 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg py-2.5 text-sm transition-colors">
                  Limpar
                </button>
              )}
              <button onClick={() => setFilterOpen(false)}
                className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg py-2.5 text-sm font-medium transition-colors">
                Aplicar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Filtros desktop */}
      <div className="hidden sm:flex flex-wrap items-center gap-3 mb-6">
        <div className="flex items-center gap-2">
          <button onClick={() => { const m = subMonths(selectedMonth, 1); setSelectedMonth(m); saveMonth(m); }}
            className="w-10 h-10 flex items-center justify-center rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 hover:text-white text-xl transition-colors">‹</button>
          <span className="text-sm font-semibold min-w-[130px] text-center">{monthLabel}</span>
          <button onClick={() => { const m = addMonths(selectedMonth, 1); setSelectedMonth(m); saveMonth(m); }}
            disabled={isCurrentMonth}
            className="w-10 h-10 flex items-center justify-center rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 hover:text-white text-xl transition-colors disabled:opacity-30 disabled:cursor-not-allowed">›</button>
        </div>
        <select value={filterCategory} onChange={e => setFilterCategory(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200">
          <option value="">Todas categorias</option>
          {availableCategories.map(({ key, label }) => <option key={key} value={key}>{label}</option>)}
        </select>
        <select value={filterCard} onChange={e => setFilterCard(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200">
          <option value="">Todos os cartões</option>
          {cards?.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <select value={filterType} onChange={e => setFilterType(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200">
          <option value="">Receitas e despesas</option>
          <option value="income">Só receitas</option>
          <option value="expense">Só despesas</option>
        </select>
        <select value={filterUser} onChange={e => setFilterUser(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200">
          <option value="">Todos os usuários</option>
          {users?.map(u => <option key={u} value={u}>{u}</option>)}
        </select>
        {(filterCategory || filterCard || filterType || filterUser) && (
          <button onClick={() => { setFilterCategory(""); setFilterCard(""); setFilterType(""); setFilterUser(""); }}
            className="text-xs text-gray-400 hover:text-white underline">Limpar</button>
        )}
        <span className="ml-auto text-sm text-gray-500">
          {data ? `${data.total} ${data.total === 1 ? "transação" : "transações"}` : ""}
        </span>
      </div>

      {/* Totalizador */}
      {totals && (
        <div className="flex gap-2 mb-4">
          {filterType !== "expense" && (
            <div className="flex-1 min-w-0 bg-gray-900 border border-gray-800 rounded-xl px-3 py-2 sm:px-4 sm:py-3">
              <p className="text-xs text-gray-500 mb-0.5">Receitas</p>
              <p className="text-sm sm:text-base font-bold text-emerald-400 truncate">{fmt(totals.income)}</p>
            </div>
          )}
          {filterType !== "income" && (
            <div className="flex-1 min-w-0 bg-gray-900 border border-gray-800 rounded-xl px-3 py-2 sm:px-4 sm:py-3">
              <p className="text-xs text-gray-500 mb-0.5">Despesas</p>
              <p className="text-sm sm:text-base font-bold text-red-400 truncate">{fmt(totals.expenses)}</p>
            </div>
          )}
          {!filterType && (
            <div className="flex-1 min-w-0 bg-gray-900 border border-gray-800 rounded-xl px-3 py-2 sm:px-4 sm:py-3">
              <p className="text-xs text-gray-500 mb-0.5">Saldo</p>
              <p className={`text-sm sm:text-base font-bold truncate ${totals.income - totals.expenses >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                {fmt(totals.income - totals.expenses)}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Formulário de nova transação */}
      {showForm && <form onSubmit={handleSubmit} className="bg-gray-900 border border-gray-800 rounded-xl p-5 mb-6 grid grid-cols-1 sm:grid-cols-3 gap-3">
        <input type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })}
          className="bg-gray-800 rounded-lg px-3 py-2 text-sm" required />

        <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value as "income" | "expense" })}
          className="bg-gray-800 rounded-lg px-3 py-2 text-sm">
          <option value="expense">Despesa</option>
          <option value="income">Receita</option>
        </select>

        <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}
          className="bg-gray-800 rounded-lg px-3 py-2 text-sm">
          {CATEGORIES.map(({ key, label }) => <option key={key} value={key}>{label}</option>)}
        </select>

        <input placeholder="Descrição" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })}
          className="bg-gray-800 rounded-lg px-3 py-2 text-sm sm:col-span-2" required />

        <input type="number" placeholder="Valor" step="0.01" min="0.01" value={form.amount}
          onChange={(e) => setForm({ ...form, amount: e.target.value })}
          className="bg-gray-800 rounded-lg px-3 py-2 text-sm" required />

        <select value={effectiveCardId} onChange={(e) => setForm({ ...form, card_id: e.target.value })}
          className="bg-gray-800 rounded-lg px-3 py-2 text-sm sm:col-span-2">
          {cards?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>

        <input
          placeholder="Autor (opcional)"
          value={form.user}
          onChange={(e) => setForm({ ...form, user: e.target.value })}
          list="users-datalist"
          className="bg-gray-800 rounded-lg px-3 py-2 text-sm sm:col-span-2"
        />
        <datalist id="users-datalist">
          {users?.map(u => <option key={u} value={u} />)}
        </datalist>

        <button type="submit" disabled={create.isPending}
          className="bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg px-4 py-2 text-sm font-medium transition-colors">
          {create.isPending ? "Salvando..." : "Salvar"}
        </button>
      </form>}

      {/* Mobile: cards */}
      <div className="sm:hidden space-y-2 mb-4">
        {data?.items.map((t) => {
          const isEditing = editingId === t.id;
          const inp = "w-full bg-gray-800 rounded-lg px-3 py-2 text-sm";

          if (isEditing) return (
            <div key={t.id} className="bg-gray-900 border border-sky-700/50 rounded-xl p-4 space-y-3">
              <div className="grid grid-cols-2 gap-2">
                <input type="date" value={editForm.date}
                  onChange={e => setEditForm(f => ({ ...f, date: e.target.value }))}
                  className={inp} />
                <select value={editForm.type}
                  onChange={e => setEditForm(f => ({ ...f, type: e.target.value as "income" | "expense" }))}
                  className={inp}>
                  <option value="expense">Despesa</option>
                  <option value="income">Receita</option>
                </select>
              </div>
              <input value={editForm.description}
                onChange={e => setEditForm(f => ({ ...f, description: e.target.value }))}
                placeholder="Descrição" className={inp} />
              <div className="grid grid-cols-2 gap-2">
                <select value={editForm.category}
                  onChange={e => setEditForm(f => ({ ...f, category: e.target.value }))}
                  className={inp}>
                  {CATEGORIES.map(({ key, label }) => <option key={key} value={key}>{label}</option>)}
                </select>
                <input type="number" step="0.01" value={editForm.amount}
                  onChange={e => setEditForm(f => ({ ...f, amount: e.target.value }))}
                  placeholder="Valor" className={inp} />
              </div>
              <select value={editForm.card_id}
                onChange={e => setEditForm(f => ({ ...f, card_id: e.target.value }))}
                className={inp}>
                <option value="">— Sem cartão —</option>
                {cards?.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
              <input
                value={editForm.user}
                onChange={e => setEditForm(f => ({ ...f, user: e.target.value }))}
                list="users-datalist"
                placeholder="Autor (opcional)"
                className={inp}
              />
              <div className="flex gap-2">
                <button onClick={saveEdit} disabled={update.isPending}
                  className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg py-2 text-sm font-medium transition-colors disabled:opacity-40">
                  {update.isPending ? "Salvando..." : "Salvar"}
                </button>
                <button onClick={() => setEditingId(null)}
                  className="flex-1 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg py-2 text-sm transition-colors">
                  Cancelar
                </button>
              </div>
            </div>
          );

          return (
            <div key={t.id} className="bg-gray-900 border border-gray-800 rounded-xl px-4 py-3 flex items-center gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-baseline justify-between gap-2">
                  <p className="text-sm font-medium truncate">{t.description}</p>
                  <p className={`text-sm font-bold shrink-0 ${t.type === "income" ? "text-emerald-400" : "text-red-400"}`}>
                    {t.type === "income" ? "+" : "−"}{fmt(t.amount)}
                  </p>
                </div>
                <p className="text-xs text-gray-500 mt-0.5">
                  {t.date.split("-").reverse().join("/")} · {CAT_LABEL[t.category] ?? t.category}
                  {t.user ? ` · ${t.user}` : ""}
                </p>
              </div>
              <div className="flex gap-0.5 shrink-0">
                <button onClick={() => startEdit(t)} title="Editar"
                  className="inline-flex items-center justify-center h-9 w-9 rounded-md text-gray-500 hover:text-sky-400 hover:bg-gray-700/60 transition-colors">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                </button>
                <button onClick={() => { if (window.confirm("Excluir esta transação?")) remove.mutate(t.id); }} title="Excluir"
                  className="inline-flex items-center justify-center h-9 w-9 rounded-md text-gray-500 hover:text-red-400 hover:bg-red-400/10 transition-colors">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>
                </button>
              </div>
            </div>
          );
        })}
        {data?.items.length === 0 && (
          <p className="text-center text-gray-500 text-sm py-8">Nenhuma transação encontrada</p>
        )}
        {data && data.total > limit && (
          <div className="flex justify-between pt-2 text-sm">
            <button disabled={page === 0} onClick={() => setPage(page - 1)}
              className="px-3 py-2 rounded-lg bg-gray-900 border border-gray-800 disabled:opacity-40">← Anterior</button>
            <span className="text-gray-400 self-center">{page * limit + 1}–{Math.min((page + 1) * limit, data.total)} de {data.total}</span>
            <button disabled={(page + 1) * limit >= data.total} onClick={() => setPage(page + 1)}
              className="px-3 py-2 rounded-lg bg-gray-900 border border-gray-800 disabled:opacity-40">Próximo →</button>
          </div>
        )}
      </div>

      {/* Desktop: tabela */}
      <div className="hidden sm:block bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <table className="w-full text-sm table-fixed">
          <thead className="bg-gray-800 text-gray-400">
            <tr>
              <th className="px-4 py-3 text-left w-40">Data</th>
              <th className="px-4 py-3 text-left w-48">Descrição</th>
              <th className="px-4 py-3 text-left w-36">Categoria</th>
              <th className="px-4 py-3 text-left hidden sm:table-cell w-36">Cartão</th>
              <th className="px-4 py-3 text-left hidden md:table-cell w-28">Autor</th>
              <th
                className="px-4 py-3 text-right cursor-pointer select-none hover:text-white w-44"
                onClick={() => setSortDir(d => d === "asc" ? "desc" : d === "desc" ? null : "asc")}
              >
                Valor {sortDir === "asc" ? "↑" : sortDir === "desc" ? "↓" : "↕"}
              </th>
              <th className="px-4 py-3 w-20" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800">
            {data?.items.map((t) => {
              const cardName = t.card_id ? (cards?.find(c => c.id === t.card_id)?.name ?? "—") : "—";
              const isEditing = editingId === t.id;
              const cell = "px-4 py-3";
              const input = "bg-gray-700 rounded px-2 py-0.5 text-xs w-full";

              if (isEditing) return (
                <tr key={t.id} className="bg-gray-800/60">
                  <td className={cell}>
                    <input type="date" value={editForm.date}
                      onChange={e => setEditForm(f => ({ ...f, date: e.target.value }))}
                      className={input} />
                  </td>
                  <td className={cell}>
                    <input value={editForm.description}
                      onChange={e => setEditForm(f => ({ ...f, description: e.target.value }))}
                      className={input} />
                  </td>
                  <td className={cell}>
                    <select value={editForm.category}
                      onChange={e => setEditForm(f => ({ ...f, category: e.target.value }))}
                      className={input}>
                      {CATEGORIES.map(({ key, label }) => <option key={key} value={key}>{label}</option>)}
                    </select>
                  </td>
                  <td className={`${cell} hidden sm:table-cell`}>
                    <select value={editForm.card_id}
                      onChange={e => setEditForm(f => ({ ...f, card_id: e.target.value }))}
                      className={input}>
                      <option value="">—</option>
                      {cards?.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                    </select>
                  </td>
                  <td className={`${cell} hidden md:table-cell`}>
                    <input
                      value={editForm.user}
                      onChange={e => setEditForm(f => ({ ...f, user: e.target.value }))}
                      list="users-datalist"
                      placeholder="—"
                      className={input}
                    />
                  </td>
                  <td className={cell}>
                    <div className="flex gap-1 items-center justify-end">
                      <select value={editForm.type}
                        onChange={e => setEditForm(f => ({ ...f, type: e.target.value as "income" | "expense" }))}
                        className="bg-gray-700 rounded px-1 py-0.5 text-xs">
                        <option value="expense">−</option>
                        <option value="income">+</option>
                      </select>
                      <input type="number" step="0.01" value={editForm.amount}
                        onChange={e => setEditForm(f => ({ ...f, amount: e.target.value }))}
                        className="bg-gray-700 rounded px-2 py-0.5 text-xs flex-1 min-w-0 text-right" />
                    </div>
                  </td>
                  <td className={`${cell} text-right whitespace-nowrap`}>
                    <button onClick={saveEdit} disabled={update.isPending} title="Salvar"
                      className="inline-flex items-center justify-center h-8 w-8 rounded-md text-gray-400 hover:text-emerald-400 hover:bg-emerald-400/10 transition-colors mr-1 disabled:opacity-40">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                    </button>
                    <button onClick={() => setEditingId(null)} title="Cancelar"
                      className="inline-flex items-center justify-center h-8 w-8 rounded-md text-gray-500 hover:text-gray-300 hover:bg-gray-700/60 transition-colors">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                    </button>
                  </td>
                </tr>
              );

              return (
                <tr key={t.id} className="hover:bg-gray-800/50">
                  <td className="px-4 py-3 text-gray-400">{t.date.split("-").reverse().join("/")}</td>
                  <td className="px-4 py-3">{t.description}</td>
                  <td className="px-4 py-3 text-gray-400">{CAT_LABEL[t.category] ?? t.category}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs hidden sm:table-cell">{cardName}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs hidden md:table-cell">{t.user ?? "—"}</td>
                  <td className={`px-4 py-3 text-right font-medium ${t.type === "income" ? "text-emerald-400" : "text-red-400"}`}>
                    {t.type === "income" ? "+" : "-"}{fmt(t.amount)}
                  </td>
                  <td className="px-4 py-3 text-right whitespace-nowrap">
                    <button onClick={() => startEdit(t)} title="Editar"
                      className="inline-flex items-center justify-center h-8 w-8 rounded-md text-gray-500 hover:text-sky-400 hover:bg-gray-700/60 transition-colors mr-1">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                    </button>
                    <button onClick={() => { if (window.confirm("Excluir esta transação?")) remove.mutate(t.id); }} title="Excluir"
                      className="inline-flex items-center justify-center h-8 w-8 rounded-md text-gray-500 hover:text-red-400 hover:bg-red-400/10 transition-colors">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>
                    </button>
                  </td>
                </tr>
              );
            })}
            {data?.items.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-gray-500 text-sm">
                  Nenhuma transação encontrada
                </td>
              </tr>
            )}
          </tbody>
        </table>
        {data && data.total > limit && (
          <div className="flex justify-between p-4 border-t border-gray-800 text-sm">
            <button disabled={page === 0} onClick={() => setPage(page - 1)}
              className="px-3 py-1 rounded bg-gray-800 disabled:opacity-40">← Anterior</button>
            <span className="text-gray-400">{page * limit + 1}–{Math.min((page + 1) * limit, data.total)} de {data.total}</span>
            <button disabled={(page + 1) * limit >= data.total} onClick={() => setPage(page + 1)}
              className="px-3 py-1 rounded bg-gray-800 disabled:opacity-40">Próximo →</button>
          </div>
        )}
      </div>{/* end desktop table */}
    </div>
  );
}

export default function TransactionsPage() {
  return (
    <Suspense fallback={<div className="text-gray-400 p-8">Carregando...</div>}>
      <TransactionsContent />
    </Suspense>
  );
}
