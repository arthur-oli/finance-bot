"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api";
import type { Goal, ForecastResponse } from "@/lib/types";
import { differenceInMonths } from "date-fns";

function fmt(v: number) {
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
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

  const [form, setForm] = useState({ name: "", target_amount: "", current_amount: "0", deadline: "" });

  const create = useMutation({
    mutationFn: (body: object) => api.post<Goal>("/api/goals/", body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["goals"] });
      setForm({ name: "", target_amount: "", current_amount: "0", deadline: "" });
    },
  });

  const update = useMutation({
    mutationFn: ({ id, body }: { id: string; body: object }) => api.patch<Goal>(`/api/goals/${id}`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["goals"] }),
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

  const monthlyBalance = forecast
    ? forecast.historical_avg_income - forecast.historical_avg_expenses
    : null;

  const today = new Date();

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Metas Financeiras</h2>

      <form onSubmit={handleSubmit} className="bg-gray-900 border border-gray-800 rounded-xl p-5 mb-6 grid grid-cols-1 sm:grid-cols-2 gap-3">
        <input placeholder="Nome da meta" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
          className="bg-gray-800 rounded-lg px-3 py-2 text-sm sm:col-span-2" required />
        <input type="number" placeholder="Valor alvo (R$)" step="0.01" min="0.01" value={form.target_amount}
          onChange={(e) => setForm({ ...form, target_amount: e.target.value })}
          className="bg-gray-800 rounded-lg px-3 py-2 text-sm" required />
        <input type="number" placeholder="Valor atual (R$)" step="0.01" min="0" value={form.current_amount}
          onChange={(e) => setForm({ ...form, current_amount: e.target.value })}
          className="bg-gray-800 rounded-lg px-3 py-2 text-sm" />
        <input type="date" value={form.deadline} onChange={(e) => setForm({ ...form, deadline: e.target.value })}
          className="bg-gray-800 rounded-lg px-3 py-2 text-sm" />
        <button type="submit" disabled={create.isPending}
          className="bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg px-4 py-2 text-sm font-medium transition-colors">
          {create.isPending ? "Salvando..." : "+ Nova meta"}
        </button>
      </form>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {goals?.map((g) => {
          const pct = g.target_amount > 0 ? Math.min(100, Math.round((g.current_amount / g.target_amount) * 100)) : 0;
          const remaining = g.target_amount - g.current_amount;

          let monthlyNeeded: number | null = null;
          if (g.deadline && remaining > 0) {
            const monthsLeft = differenceInMonths(new Date(g.deadline), today);
            if (monthsLeft > 0) monthlyNeeded = remaining / monthsLeft;
          }

          let monthsAtRate: number | null = null;
          if (monthlyBalance && monthlyBalance > 0 && remaining > 0) {
            monthsAtRate = Math.ceil(remaining / monthlyBalance);
          }

          return (
            <div key={g.id} className="bg-gray-900 border border-gray-800 rounded-xl p-5">
              <div className="flex justify-between items-start mb-3">
                <div>
                  <p className="font-semibold">{g.name}</p>
                  {g.deadline && <p className="text-xs text-gray-500">Prazo: {g.deadline}</p>}
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => update.mutate({ id: g.id, body: { completed: true } })}
                    className="text-xs text-emerald-600 hover:text-emerald-400">✓</button>
                  <button onClick={() => remove.mutate(g.id)} className="text-xs text-gray-600 hover:text-red-400">✕</button>
                </div>
              </div>

              <div className="w-full bg-gray-800 rounded-full h-2 mb-2">
                <div className="bg-emerald-500 h-2 rounded-full transition-all" style={{ width: `${pct}%` }} />
              </div>
              <div className="flex justify-between text-sm mb-3">
                <span className="text-gray-300">{fmt(g.current_amount)}</span>
                <span className="text-gray-400">{pct}% · {fmt(g.target_amount)}</span>
              </div>

              {remaining > 0 && (monthlyNeeded !== null || monthsAtRate !== null) && (
                <div className="border-t border-gray-800 pt-3 space-y-1">
                  {monthlyNeeded !== null && (
                    <p className="text-xs text-gray-400">
                      Guardar <span className="text-white font-medium">{fmt(monthlyNeeded)}/mês</span> para atingir no prazo
                    </p>
                  )}
                  {monthsAtRate !== null && (
                    <p className="text-xs text-gray-400">
                      No ritmo atual (<span className="text-emerald-400">{fmt(monthlyBalance!)}/mês</span>){" "}
                      → <span className="text-white font-medium">{monthsAtRate} {monthsAtRate === 1 ? "mês" : "meses"}</span>
                    </p>
                  )}
                  {monthsAtRate === null && monthlyBalance !== null && monthlyBalance <= 0 && (
                    <p className="text-xs text-red-400">Saldo mensal negativo — meta pode não ser atingida</p>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
