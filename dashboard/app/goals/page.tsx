"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api";
import type { Goal, ForecastResponse } from "@/lib/types";
import { differenceInMonths, format, parseISO } from "date-fns";
import { ptBR } from "date-fns/locale";

function fmt(v: number) {
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function fmtDate(dateStr: string) {
  try { return format(parseISO(dateStr), "d 'de' MMMM 'de' yyyy", { locale: ptBR }); }
  catch { return dateStr; }
}

export default function GoalsPage() {
  const qc = useQueryClient();

  const { data: goals } = useQuery<Goal[]>({
    queryKey: ["goals"],
    queryFn: () => api.get("/api/goals/?include_completed=false"),
  });

  const { data: forecast } = useQuery<ForecastResponse>({
    queryKey: ["forecast"],
    queryFn: () => api.get("/api/forecast/"),
  });

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", target_amount: "", current_amount: "0", deadline: "" });
  const [depositId, setDepositId] = useState<string | null>(null);
  const [depositValue, setDepositValue] = useState("");

  const create = useMutation({
    mutationFn: (body: object) => api.post<Goal>("/api/goals/", body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["goals"] });
      setForm({ name: "", target_amount: "", current_amount: "0", deadline: "" });
      setShowForm(false);
    },
  });

  const update = useMutation({
    mutationFn: ({ id, body }: { id: string; body: object }) => api.patch<Goal>(`/api/goals/${id}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["goals"] });
      setDepositId(null);
      setDepositValue("");
    },
  });

  const remove = useMutation({
    mutationFn: (id: string) => api.delete(`/api/goals/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["goals"] }),
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const body: Record<string, unknown> = {
      name: form.name,
      target_amount: parseFloat(form.target_amount),
      current_amount: parseFloat(form.current_amount || "0"),
    };
    if (form.deadline) body.deadline = form.deadline;
    create.mutate(body);
  }

  function handleDeposit(g: Goal) {
    const add = parseFloat(depositValue);
    if (!isFinite(add) || add <= 0) return;
    update.mutate({ id: g.id, body: { current_amount: g.current_amount + add } });
  }

  const monthlyBalance = forecast
    ? forecast.historical_avg_income - forecast.historical_avg_expenses
    : null;

  const today = new Date();
  const inp = "bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm w-full focus:outline-none focus:border-emerald-600 text-gray-100 placeholder-gray-600";

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">Metas</h2>
        <button
          onClick={() => setShowForm(!showForm)}
          className="bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg px-4 py-2 text-sm font-medium transition-colors"
        >
          {showForm ? "Cancelar" : "+ Nova meta"}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-gray-900 border border-gray-800 rounded-xl p-5 mb-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="sm:col-span-2">
            <label className="block text-xs text-gray-400 mb-1.5">Nome da meta</label>
            <input
              placeholder="Ex: Reserva de emergência, Viagem, Notebook…"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className={inp}
              required
            />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1.5">Valor alvo (R$)</label>
            <input
              type="number" placeholder="10000,00" step="0.01" min="0.01"
              value={form.target_amount}
              onChange={(e) => setForm({ ...form, target_amount: e.target.value })}
              className={inp} required
            />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1.5">Já guardei (R$)</label>
            <input
              type="number" placeholder="0,00" step="0.01" min="0"
              value={form.current_amount}
              onChange={(e) => setForm({ ...form, current_amount: e.target.value })}
              className={inp}
            />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1.5">Prazo (opcional)</label>
            <input
              type="date" value={form.deadline}
              onChange={(e) => setForm({ ...form, deadline: e.target.value })}
              className={inp}
            />
          </div>
          <div className="flex items-end">
            <button
              type="submit" disabled={create.isPending}
              className="w-full bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white rounded-lg px-4 py-2 text-sm font-medium transition-colors"
            >
              {create.isPending ? "Salvando…" : "Criar meta"}
            </button>
          </div>
        </form>
      )}

      {goals?.length === 0 && (
        <div className="text-center py-16 text-gray-500">
          <p className="text-5xl mb-3">🎯</p>
          <p className="text-sm">Nenhuma meta ativa. Crie a primeira!</p>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {goals?.map((g) => {
          const pct = g.target_amount > 0 ? Math.min(100, (g.current_amount / g.target_amount) * 100) : 0;
          const pctDisplay = Math.round(pct);
          const remaining = Math.max(0, g.target_amount - g.current_amount);
          const done = remaining === 0;

          let monthlyNeeded: number | null = null;
          if (g.deadline && remaining > 0) {
            const monthsLeft = differenceInMonths(new Date(g.deadline), today);
            if (monthsLeft > 0) monthlyNeeded = remaining / monthsLeft;
          }

          let monthsAtRate: number | null = null;
          if (monthlyBalance && monthlyBalance > 0 && remaining > 0) {
            monthsAtRate = Math.ceil(remaining / monthlyBalance);
          }

          const barColor = done
            ? "bg-emerald-400"
            : pct >= 75 ? "bg-emerald-500"
            : pct >= 40 ? "bg-sky-500"
            : "bg-amber-500";

          const isDepositing = depositId === g.id;

          return (
            <div key={g.id} className="bg-gray-900 border border-gray-800 rounded-xl p-5 flex flex-col gap-4">

              {/* Header */}
              <div className="flex justify-between items-start gap-3">
                <div className="min-w-0">
                  <p className="font-semibold text-base truncate">{g.name}</p>
                  {g.deadline && (
                    <p className="text-xs text-gray-500 mt-0.5">Prazo: {fmtDate(g.deadline)}</p>
                  )}
                </div>
                <div className="flex gap-1 shrink-0">
                  <button
                    onClick={() => { if (window.confirm(`Marcar "${g.name}" como concluída?`)) update.mutate({ id: g.id, body: { completed: true } }); }}
                    title="Marcar como concluída"
                    className="inline-flex items-center justify-center h-8 w-8 rounded-md text-gray-500 hover:text-emerald-400 hover:bg-emerald-400/10 transition-colors"
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                  </button>
                  <button
                    onClick={() => { if (window.confirm(`Excluir "${g.name}"?`)) remove.mutate(g.id); }}
                    title="Excluir meta"
                    className="inline-flex items-center justify-center h-8 w-8 rounded-md text-gray-500 hover:text-red-400 hover:bg-red-400/10 transition-colors"
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>
                  </button>
                </div>
              </div>

              {/* Progress bar */}
              <div>
                <div className="flex justify-between items-baseline mb-1.5">
                  <span className="text-xs text-gray-400">Progresso</span>
                  <span className={`text-sm font-bold ${done ? "text-emerald-400" : "text-white"}`}>{pctDisplay}%</span>
                </div>
                <div className="w-full bg-gray-800 rounded-full h-3 overflow-hidden">
                  <div
                    className={`h-3 rounded-full transition-all duration-500 ${barColor}`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <div className="flex justify-between mt-2 text-xs">
                  <div className="text-gray-400">
                    Guardado: <span className="text-gray-200 font-medium">{fmt(g.current_amount)}</span>
                  </div>
                  <div className="text-gray-400">
                    Meta: <span className="text-gray-200 font-medium">{fmt(g.target_amount)}</span>
                  </div>
                </div>
              </div>

              {/* Remaining / Done */}
              {done ? (
                <div className="bg-emerald-900/30 border border-emerald-700/40 rounded-lg px-3 py-2 text-center text-sm text-emerald-400 font-medium">
                  Meta atingida!
                </div>
              ) : (
                <div className="bg-gray-800/60 rounded-lg px-3 py-2.5 flex justify-between items-center">
                  <span className="text-xs text-gray-400">Faltam</span>
                  <span className="text-sm font-semibold text-white">{fmt(remaining)}</span>
                </div>
              )}

              {/* Insights */}
              {!done && (monthlyNeeded !== null || monthsAtRate !== null) && (
                <div className="border-t border-gray-800 pt-3 space-y-1.5">
                  {monthlyNeeded !== null && (
                    <p className="text-xs text-gray-400">
                      Guardar <span className="text-white font-medium">{fmt(monthlyNeeded)}/mês</span> para atingir no prazo
                    </p>
                  )}
                  {monthsAtRate !== null && (
                    <p className="text-xs text-gray-400">
                      No ritmo atual ({fmt(monthlyBalance!)}/mês) → <span className="text-white font-medium">{monthsAtRate} {monthsAtRate === 1 ? "mês" : "meses"}</span>
                    </p>
                  )}
                  {monthsAtRate === null && monthlyBalance !== null && monthlyBalance <= 0 && (
                    <p className="text-xs text-red-400">Saldo mensal negativo — meta pode não ser atingida</p>
                  )}
                </div>
              )}

              {/* Quick deposit */}
              {!done && (
                isDepositing ? (
                  <div className="flex gap-2">
                    <input
                      type="number" step="0.01" min="0.01"
                      placeholder="Valor a adicionar"
                      value={depositValue}
                      onChange={(e) => setDepositValue(e.target.value)}
                      autoFocus
                      onKeyDown={(e) => {
                        if (e.key === "Enter") handleDeposit(g);
                        if (e.key === "Escape") { setDepositId(null); setDepositValue(""); }
                      }}
                      className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-emerald-600 text-gray-100 placeholder-gray-600"
                    />
                    <button
                      onClick={() => handleDeposit(g)}
                      disabled={update.isPending}
                      className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white rounded-lg px-3 py-1.5 text-sm font-medium transition-colors shrink-0"
                    >
                      Guardar
                    </button>
                    <button
                      onClick={() => { setDepositId(null); setDepositValue(""); }}
                      className="bg-gray-800 hover:bg-gray-700 text-gray-400 rounded-lg px-2.5 py-1.5 text-sm transition-colors"
                    >
                      ✕
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => { setDepositId(g.id); setDepositValue(""); }}
                    className="w-full border border-dashed border-gray-700 hover:border-emerald-600 hover:text-emerald-400 text-gray-500 rounded-lg py-2 text-sm transition-colors"
                  >
                    + Registrar depósito
                  </button>
                )
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
