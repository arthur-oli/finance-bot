"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api";
import type { Card } from "@/lib/types";

function getOwner(c: Card): string {
  return c.owner || "Compartilhado";
}

const EMPTY_FORM = { name: "", type: "credit" as "credit" | "debit", card_limit: "", closing_day: "", due_day: "", owner: "" };

export default function CardsPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState(EMPTY_FORM);

  const { data: cards } = useQuery<Card[]>({
    queryKey: ["cards", "all"],
    queryFn: () => api.get("/api/cards/?active_only=false"),
  });

  const create = useMutation({
    mutationFn: (body: object) => api.post<Card>("/api/cards/", body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cards"] });
      setForm(EMPTY_FORM);
      setShowForm(false);
    },
  });

  const update = useMutation({
    mutationFn: ({ id, body }: { id: string; body: object }) => api.patch<Card>(`/api/cards/${id}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cards"] });
      setEditingId(null);
    },
  });

  const remove = useMutation({
    mutationFn: (id: string) => api.delete(`/api/cards/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cards"] }),
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const body: Record<string, unknown> = { name: form.name, type: form.type };
    if (form.card_limit) body.card_limit = parseFloat(form.card_limit);
    if (form.closing_day) body.closing_day = parseInt(form.closing_day);
    if (form.due_day) body.due_day = parseInt(form.due_day);
    body.owner = form.owner || null;
    create.mutate(body);
  }

  function startEdit(c: Card) {
    setEditingId(c.id);
    setEditForm({
      name: c.name,
      type: c.type as "credit" | "debit",
      card_limit: c.card_limit ? String(c.card_limit) : "",
      closing_day: c.closing_day ? String(c.closing_day) : "",
      due_day: c.due_day ? String(c.due_day) : "",
      owner: c.owner ?? "",
    });
  }

  function saveEdit() {
    if (!editingId) return;
    const body: Record<string, unknown> = { name: editForm.name };
    body.card_limit = editForm.card_limit ? parseFloat(editForm.card_limit) : null;
    body.closing_day = editForm.closing_day ? parseInt(editForm.closing_day) : null;
    body.due_day = editForm.due_day ? parseInt(editForm.due_day) : null;
    body.owner = editForm.owner || null;
    update.mutate({ id: editingId, body });
  }

  const ownerOrder = [...new Set((cards ?? []).map(getOwner))].sort((a, b) =>
    a === "Compartilhado" ? 1 : b === "Compartilhado" ? -1 : a.localeCompare(b)
  );
  const grouped = ownerOrder
    .map((owner) => ({ owner, cards: (cards ?? []).filter((c) => getOwner(c) === owner) }))
    .filter((g) => g.cards.length > 0);

  const input = "bg-gray-800 rounded-lg px-3 py-2 text-sm w-full";

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">Cartões</h2>
        <button
          onClick={() => setShowForm(!showForm)}
          className="bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg px-4 py-2 text-sm font-medium transition-colors"
        >
          {showForm ? "Cancelar" : "+ Novo cartão"}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-gray-900 border border-gray-800 rounded-xl p-5 mb-6 grid grid-cols-1 sm:grid-cols-3 gap-3">
          <input placeholder="Nome do cartão" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="bg-gray-800 rounded-lg px-3 py-2 text-sm sm:col-span-2" required />
          <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value as "credit" | "debit" })}
            className="bg-gray-800 rounded-lg px-3 py-2 text-sm">
            <option value="credit">Crédito</option>
            <option value="debit">Débito</option>
          </select>
          <input placeholder="Dono (deixe vazio = compartilhado)" value={form.owner}
            onChange={(e) => setForm({ ...form, owner: e.target.value })}
            className="bg-gray-800 rounded-lg px-3 py-2 text-sm" />
          <input type="number" placeholder="Limite (opcional)" value={form.card_limit}
            onChange={(e) => setForm({ ...form, card_limit: e.target.value })}
            className="bg-gray-800 rounded-lg px-3 py-2 text-sm" />
          <input type="number" placeholder="Dia fechamento" min="1" max="31" value={form.closing_day}
            onChange={(e) => setForm({ ...form, closing_day: e.target.value })}
            className="bg-gray-800 rounded-lg px-3 py-2 text-sm" />
          <input type="number" placeholder="Dia vencimento" min="1" max="31" value={form.due_day}
            onChange={(e) => setForm({ ...form, due_day: e.target.value })}
            className="bg-gray-800 rounded-lg px-3 py-2 text-sm" />
          <button type="submit" disabled={create.isPending}
            className="bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg px-4 py-2 text-sm font-medium sm:col-span-3 transition-colors">
            {create.isPending ? "Salvando..." : "Salvar"}
          </button>
        </form>
      )}

      <div className="space-y-8">
        {grouped.map(({ owner, cards: ownerCards }, groupIdx) => (
          <div key={owner}>
            {groupIdx > 0 && <hr className="border-gray-800 mb-8" />}
            <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">{owner}</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {ownerCards.map((c) => {
                if (editingId === c.id) return (
                  <div key={c.id} className="bg-gray-900 border border-sky-700/50 rounded-xl p-5 flex flex-col gap-3">
                    <input value={editForm.name} onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                      placeholder="Nome" className={input} />
                    <div className="grid grid-cols-2 gap-2">
                      <select value={editForm.type} onChange={(e) => setEditForm({ ...editForm, type: e.target.value as "credit" | "debit" })}
                        className={input}>
                        <option value="credit">Crédito</option>
                        <option value="debit">Débito</option>
                      </select>
                      <input placeholder="Dono (vazio = compartilhado)" value={editForm.owner}
                        onChange={(e) => setEditForm({ ...editForm, owner: e.target.value })}
                        className={input} />
                      <input type="number" placeholder="Limite" value={editForm.card_limit}
                        onChange={(e) => setEditForm({ ...editForm, card_limit: e.target.value })}
                        className={input} />
                      <input type="number" placeholder="Dia fecha" min="1" max="31" value={editForm.closing_day}
                        onChange={(e) => setEditForm({ ...editForm, closing_day: e.target.value })}
                        className={input} />
                      <input type="number" placeholder="Dia vence" min="1" max="31" value={editForm.due_day}
                        onChange={(e) => setEditForm({ ...editForm, due_day: e.target.value })}
                        className={input} />
                    </div>
                    <div className="flex gap-2">
                      <button onClick={saveEdit} disabled={update.isPending}
                        className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg px-3 py-1.5 text-sm transition-colors disabled:opacity-40">
                        {update.isPending ? "Salvando..." : "Salvar"}
                      </button>
                      <button onClick={() => setEditingId(null)}
                        className="flex-1 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg px-3 py-1.5 text-sm transition-colors">
                        Cancelar
                      </button>
                    </div>
                  </div>
                );

                return (
                  <div key={c.id} className={`bg-gray-900 border rounded-xl p-5 ${c.active ? "border-gray-800" : "border-gray-700 opacity-50"}`}>
                    <div className="flex justify-between items-start mb-3">
                      <div>
                        <p className="font-semibold">{c.name}</p>
                        <p className="text-sm text-gray-400">{c.type === "credit" ? "Crédito" : "Débito"}</p>
                      </div>
                      <div className="flex gap-2">
                        <button onClick={() => startEdit(c)} title="Editar"
                          className="inline-flex items-center justify-center h-8 w-8 rounded-md text-gray-500 hover:text-sky-400 hover:bg-gray-700/60 transition-colors">
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                        </button>
                        <button onClick={() => { if (window.confirm(`Excluir ${c.name}?`)) remove.mutate(c.id); }} title="Excluir"
                          className="inline-flex items-center justify-center h-8 w-8 rounded-md text-gray-500 hover:text-red-400 hover:bg-red-400/10 transition-colors">
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>
                        </button>
                      </div>
                    </div>
                    {c.card_limit && (
                      <p className="text-sm text-gray-300">Limite: {Number(c.card_limit).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}</p>
                    )}
                    {c.closing_day && <p className="text-xs text-gray-500">Fecha dia {c.closing_day} · Vence dia {c.due_day}</p>}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
