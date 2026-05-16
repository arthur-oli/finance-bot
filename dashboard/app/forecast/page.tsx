"use client";
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ForecastResponse, AnalyticsResponse } from "@/lib/types";
import { format, startOfMonth, endOfMonth, subMonths } from "date-fns";

function fmt(v: number) {
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

const CAT_LABELS: Record<string, string> = {
  alimentacao: "Alimentação", transporte: "Transporte", saude: "Saúde",
  lazer: "Lazer", compras: "Compras", salario: "Salário",
  investimento: "Investimento", assinatura: "Assinatura", moradia: "Moradia",
  pet: "Pet", mercado: "Mercado", vestuario: "Vestuário", cosmeticos: "Cosméticos", presentes: "Presentes", miscelanea: "Miscelânea",
};

const SKIP_CATS = new Set(["salario", "investimento"]);

export default function ForecastPage() {
  const today = new Date();
  const startCurrent = format(startOfMonth(today), "yyyy-MM-dd");
  const endCurrent = format(today, "yyyy-MM-dd");
  const start3 = format(startOfMonth(subMonths(today, 3)), "yyyy-MM-dd");
  const end3 = format(endOfMonth(subMonths(today, 1)), "yyyy-MM-dd");

  const { data: forecast } = useQuery<ForecastResponse>({
    queryKey: ["forecast"],
    queryFn: () => api.get("/api/forecast/"),
  });

  const { data: currentMonth } = useQuery<AnalyticsResponse>({
    queryKey: ["analytics-current", startCurrent, endCurrent],
    queryFn: () => api.get(`/api/analytics/?start=${startCurrent}&end=${endCurrent}`),
  });

  const { data: prev3 } = useQuery<AnalyticsResponse>({
    queryKey: ["analytics-prev3", start3, end3],
    queryFn: () => api.get(`/api/analytics/?start=${start3}&end=${end3}`),
  });

  const pace = forecast ? Math.round(forecast.pace_factor * 100) : 0;

  const monthCount = Math.max(prev3?.monthly_trend.length ?? 1, 1);

  const catRows = useMemo(() => {
    const current = currentMonth?.summary.by_category ?? {};
    const prev = prev3?.summary.by_category ?? {};
    const allCats = new Set([...Object.keys(current), ...Object.keys(prev)]);
    return Array.from(allCats)
      .filter(k => !SKIP_CATS.has(k))
      .map(cat => ({
        cat,
        label: CAT_LABELS[cat] ?? cat,
        curr: current[cat] ?? 0,
        avg: (prev[cat] ?? 0) / monthCount,
      }))
      .filter(d => d.curr > 0 || d.avg > 0)
      .sort((a, b) => b.curr - a.curr);
  }, [currentMonth, prev3, monthCount]);

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Previsão Financeira</h2>

      {forecast && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
            {[
              { label: "Receitas previstas", value: fmt(forecast.projected_income), color: "text-emerald-400" },
              { label: "Despesas previstas", value: fmt(forecast.projected_expenses), color: "text-red-400" },
              { label: "Assinaturas/mês", value: fmt(forecast.subscriptions_total), color: "text-amber-400" },
              { label: "Saldo previsto", value: fmt(forecast.projected_balance), color: forecast.projected_balance >= 0 ? "text-emerald-400" : "text-red-400" },
            ].map((c) => (
              <div key={c.label} className="bg-gray-900 border border-gray-800 rounded-xl px-4 py-3">
                <p className="text-xs text-gray-400 mb-1">{c.label}</p>
                <p className={`text-lg font-bold ${c.color}`}>{c.value}</p>
              </div>
            ))}
          </div>

          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 mb-6">
            <div className="flex justify-between text-xs text-gray-400 mb-2">
              <span>Ritmo do mês</span>
              <span>{pace}% — dia {forecast.days_elapsed} de {forecast.days_in_month}</span>
            </div>
            <div className="w-full bg-gray-800 rounded-full h-2.5">
              <div className="bg-emerald-500 h-2.5 rounded-full transition-all" style={{ width: `${pace}%` }} />
            </div>
          </div>
        </>
      )}

      {catRows.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <h3 className="text-sm font-semibold text-gray-300 mb-4">
            Este mês vs. média últimos {monthCount} {monthCount === 1 ? "mês" : "meses"}
          </h3>
          <div className="space-y-3">
            {catRows.map(({ cat, label, curr, avg }) => {
              const ratio = avg > 0 ? curr / avg : 2;
              const barPct = Math.min(100, Math.round(ratio * 50));
              const over = curr > avg;
              const pctLabel = avg > 0 ? `${Math.round(ratio * 100)}%` : "novo";
              return (
                <div key={cat}>
                  <div className="flex justify-between items-baseline mb-1">
                    <span className="text-sm text-gray-200">{label}</span>
                    <div className="text-right">
                      <span className={`text-sm font-medium ${over ? "text-red-400" : "text-emerald-400"}`}>
                        {fmt(curr)}
                      </span>
                      {avg > 0 && (
                        <span className="text-xs text-gray-500 ml-1.5">méd. {fmt(avg)}</span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 bg-gray-800 rounded-full h-1.5">
                      <div
                        className={`h-1.5 rounded-full transition-all ${over ? "bg-red-500" : "bg-emerald-500"}`}
                        style={{ width: `${barPct}%` }}
                      />
                    </div>
                    <span className={`text-xs w-10 text-right ${over ? "text-red-400" : "text-emerald-400"}`}>
                      {pctLabel}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
