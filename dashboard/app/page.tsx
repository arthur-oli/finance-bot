"use client";
import { useState, useEffect, useMemo, useRef } from "react";
import { useRouter } from "next/navigation";
import { saveMonth, loadMonth } from "@/lib/month-store";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { AnalyticsResponse, ForecastResponse, Settings, TransactionList } from "@/lib/types";
import { format, startOfMonth, endOfMonth, subMonths, addMonths, isSameMonth } from "date-fns";
import { ptBR } from "date-fns/locale";
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend,
  LineChart, Line, ReferenceLine,
} from "recharts";

const PIE_COLORS = ["#f87171", "#fb923c", "#facc15", "#a78bfa", "#34d399", "#38bdf8", "#f472b6", "#6b7280"];
const CAT_LABELS: Record<string, string> = {
  alimentacao: "Alimentação", transporte: "Transporte", saude: "Saúde",
  lazer: "Lazer", compras: "Compras", salario: "Salário",
  investimento: "Investimento", assinatura: "Assinatura", moradia: "Moradia",
  pet: "Pet", mercado: "Mercado", vestuario: "Vestuário", cosmeticos: "Cosméticos", presentes: "Presentes", miscelanea: "Miscelânea", outros: "Miscelânea",
};

function fmt(v: number) {
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function KpiCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <p className="text-sm text-gray-400 mb-1">{label}</p>
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
    </div>
  );
}

function buildPieData(by_category: Record<string, number>) {
  const sorted = Object.entries(by_category).sort(([, a], [, b]) => b - a);
  const top = sorted.slice(0, 7);
  const rest = sorted.slice(7).reduce((s, [, v]) => s + v, 0);
  const data = top.map(([k, v]) => ({ key: k, name: CAT_LABELS[k] ?? k, value: v }));
  if (rest > 0) data.push({ key: "", name: "Demais", value: rest });
  return data;
}

export default function HomePage() {
  const router = useRouter();
  const today = new Date();
  const [selectedMonth, setSelectedMonth] = useState(today);
  const isCurrentMonth = isSameMonth(selectedMonth, today);
  const [activePieKey, setActivePieKey] = useState<string | null>(null);
  const activePieKeyRef = useRef<string | null>(null);

  useEffect(() => { setSelectedMonth(loadMonth()); }, []);

  function changeMonth(d: Date) {
    setSelectedMonth(d);
    saveMonth(d);
  }

  const start = format(startOfMonth(selectedMonth), "yyyy-MM-dd");
  const end = isCurrentMonth
    ? format(today, "yyyy-MM-dd")
    : format(endOfMonth(selectedMonth), "yyyy-MM-dd");
  const trendStart = format(startOfMonth(subMonths(today, 5)), "yyyy-MM-dd");
  const trendEnd = format(today, "yyyy-MM-dd");

  const { data: analytics } = useQuery<AnalyticsResponse>({
    queryKey: ["analytics", start, end],
    queryFn: () => api.get(`/api/analytics/?start=${start}&end=${end}`),
  });

  const { data: trend } = useQuery<AnalyticsResponse>({
    queryKey: ["analytics-trend", trendStart, trendEnd],
    queryFn: () => api.get(`/api/analytics/?start=${trendStart}&end=${trendEnd}`),
  });

  const { data: forecast } = useQuery<ForecastResponse>({
    queryKey: ["forecast"],
    queryFn: () => api.get("/api/forecast/"),
    enabled: isCurrentMonth,
  });

  const { data: settings } = useQuery<Settings>({
    queryKey: ["settings"],
    queryFn: () => api.get("/api/settings/"),
  });

  const { data: monthTxData } = useQuery<TransactionList>({
    queryKey: ["transactions-month", start, end],
    queryFn: () => api.get(`/api/transactions/?limit=1000&offset=0&start=${start}&end=${end}`),
  });

  const userChartData = useMemo(() => {
    if (!monthTxData?.items.length) return [];
    const map: Record<string, { income: number; expenses: number }> = {};
    for (const tx of monthTxData.items) {
      const name = tx.user ?? "—";
      if (!map[name]) map[name] = { income: 0, expenses: 0 };
      if (tx.type === "income") map[name].income += tx.amount;
      else map[name].expenses += tx.amount;
    }
    return Object.entries(map)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([name, v]) => ({ name, ...v }));
  }, [monthTxData]);

  const s = analytics?.summary;
  const pace = forecast ? Math.round(forecast.pace_factor * 100) : 0;
  const pieData = s?.by_category ? buildPieData(s.by_category) : [];
  const trendData = (trend?.monthly_trend ?? [])
    .filter((m) => m.income > 0 || m.expenses > 0)
    .map((m) => ({
      ...m,
      mes: format(new Date(m.month + "-02T12:00:00"), "MMM", { locale: ptBR }),
    }));

  const balanceData = (() => {
    const months = trend?.monthly_trend ?? [];
    if (months.length === 0) return [];
    let running = Number(settings?.base_balance ?? 0);
    return months.map((m) => {
      running += m.balance;
      return {
        mes: format(new Date(m.month + "-02T12:00:00"), "MMM/yy", { locale: ptBR }),
        saldo: Math.round(running * 100) / 100,
      };
    });
  })();

  const monthLabel = format(selectedMonth, "MMMM yyyy", { locale: ptBR })
    .replace(/^\w/, c => c.toUpperCase());

  return (
    <div>
      {/* Cabeçalho com navegação de mês */}
      <div className="flex items-center justify-center gap-3 mb-6">
        <button
          onClick={() => changeMonth(subMonths(selectedMonth, 1))}
          className="w-10 h-10 flex items-center justify-center rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 hover:text-white text-xl transition-colors"
        >‹</button>
        <h2 className="text-2xl font-bold min-w-[200px] text-center">{monthLabel}</h2>
        <button
          onClick={() => changeMonth(addMonths(selectedMonth, 1))}
          disabled={isCurrentMonth}
          className="w-10 h-10 flex items-center justify-center rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 hover:text-white text-xl transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
        >›</button>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <KpiCard label="Receitas" value={s ? fmt(s.total_income) : "—"} color="text-emerald-400" />
        <KpiCard label="Despesas" value={s ? fmt(s.total_expenses) : "—"} color="text-red-400" />
        <KpiCard label="Saldo" value={s ? fmt(s.balance) : "—"} color={s && s.balance >= 0 ? "text-emerald-400" : "text-red-400"} />
        {isCurrentMonth
          ? <KpiCard label="Ritmo do mês" value={forecast ? `${pace}%` : "—"} color="text-sky-400" />
          : <KpiCard label="Categorias" value={s?.by_category ? `${Object.keys(s.by_category).length}` : "—"} color="text-gray-300" />
        }
      </div>

      {/* Gráficos principais */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">

        {/* Pizza categorias */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h3 className="text-base font-semibold mb-4 text-gray-200">Despesas por categoria</h3>
          {pieData.length > 0 ? (
            <div>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={pieData} dataKey="value" cx="50%" cy="50%" outerRadius={90}
                    cursor="pointer"
                    onClick={(data) => {
                      const key = (data as { key?: string })?.key ?? "";
                      if (activePieKeyRef.current === key) {
                        activePieKeyRef.current = null;
                        setActivePieKey(null);
                        const month = format(selectedMonth, "yyyy-MM");
                        router.push(key ? `/transactions?month=${month}&category=${key}` : `/transactions?month=${month}`);
                      } else {
                        activePieKeyRef.current = key;
                        setActivePieKey(key);
                      }
                    }}
                  >
                    {pieData.map((_, i) => (
                      <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v: number) => fmt(v)} />
                </PieChart>
              </ResponsiveContainer>
              <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1">
                {pieData.map((entry, i) => {
                  const total = pieData.reduce((s, d) => s + d.value, 0);
                  const pct = total > 0 ? ((entry.value / total) * 100).toFixed(0) : "0";
                  return (
                    <button
                      key={entry.key || "outros"}
                      onClick={() => {
                        const month = format(selectedMonth, "yyyy-MM");
                        const url = entry.key
                          ? `/transactions?month=${month}&category=${entry.key}`
                          : `/transactions?month=${month}`;
                        router.push(url);
                      }}
                      className="flex items-center gap-1.5 text-left"
                    >
                      <span className="w-2.5 h-2.5 rounded-sm flex-shrink-0" style={{ background: PIE_COLORS[i % PIE_COLORS.length] }} />
                      <span className="text-xs text-gray-300 truncate">{entry.name}</span>
                      <span className="text-xs text-gray-500 ml-auto flex-shrink-0">{pct}%</span>
                    </button>
                  );
                })}
              </div>
            </div>
          ) : (
            <p className="text-gray-500 text-sm mt-8 text-center">Sem despesas no período</p>
          )}
        </div>

        {/* Barras tendência mensal */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h3 className="text-base font-semibold mb-4 text-gray-200">Tendência — últimos 6 meses</h3>
          {trendData.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart
                data={trendData}
                barCategoryGap="30%"
                style={{ cursor: "pointer" }}
                onClick={(payload) => {
                  const month = payload?.activePayload?.[0]?.payload?.month;
                  if (month) router.push(`/transactions?month=${month}`);
                }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="mes" tick={{ fill: "#9ca3af", fontSize: 12 }} />
                <YAxis tick={{ fill: "#9ca3af", fontSize: 11 }}
                  tickFormatter={(v) => `R$${(v / 1000).toFixed(0)}k`} />
                <Tooltip formatter={(v: number) => fmt(v)}
                  contentStyle={{ background: "#111827", border: "1px solid #374151" }} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Bar dataKey="income" name="Receitas" fill="#34d399" radius={[4, 4, 0, 0]} />
                <Bar dataKey="expenses" name="Despesas" fill="#f87171" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-gray-500 text-sm mt-8 text-center">Sem dados históricos</p>
          )}
        </div>
      </div>

      {/* Evolução do saldo */}
      {balanceData.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 mb-6">
          <h3 className="text-base font-semibold mb-4 text-gray-200">Evolução do saldo</h3>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={balanceData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="mes" tick={{ fill: "#9ca3af", fontSize: 12 }} />
              <YAxis
                tick={{ fill: "#9ca3af", fontSize: 11 }}
                tickFormatter={(v) => `R$${(v / 1000).toFixed(0)}k`}
                width={52}
              />
              <Tooltip
                formatter={(v: number) => fmt(v)}
                contentStyle={{ background: "#111827", border: "1px solid #374151" }}
                labelStyle={{ color: "#e5e7eb" }}
              />
              <ReferenceLine y={0} stroke="#6b7280" strokeDasharray="4 2" />
              <Line
                type="monotone"
                dataKey="saldo"
                name="Saldo"
                stroke="#38bdf8"
                strokeWidth={2}
                dot={{ r: 3, fill: "#38bdf8" }}
                activeDot={{ r: 5 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Por usuário */}
      {userChartData.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 mb-6">
          <h3 className="text-base font-semibold mb-4 text-gray-200">Por usuário — {monthLabel}</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart
              data={userChartData}
              barCategoryGap="40%"
              style={{ cursor: "pointer" }}
              onClick={(payload) => {
                const user = payload?.activePayload?.[0]?.payload?.name;
                if (user && user !== "—") {
                  const month = format(selectedMonth, "yyyy-MM");
                  router.push(`/transactions?month=${month}&user=${encodeURIComponent(user)}`);
                }
              }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="name" tick={{ fill: "#9ca3af", fontSize: 12 }} />
              <YAxis tick={{ fill: "#9ca3af", fontSize: 11 }} tickFormatter={(v) => `R$${(v / 1000).toFixed(0)}k`} width={52} />
              <Tooltip formatter={(v: number) => fmt(v)} contentStyle={{ background: "#111827", border: "1px solid #374151" }} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="income" name="Receitas" fill="#34d399" radius={[4, 4, 0, 0]} />
              <Bar dataKey="expenses" name="Despesas" fill="#f87171" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Ranking categorias */}
      {s?.by_category && Object.keys(s.by_category).length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 mb-6">
          <h3 className="text-base font-semibold mb-4 text-gray-200">Ranking de gastos</h3>
          <div className="space-y-3">
            {Object.entries(s.by_category)
              .sort(([, a], [, b]) => b - a)
              .map(([cat, val], i) => {
                const max = Math.max(...Object.values(s.by_category));
                const pct = Math.round((val / max) * 100);
                const month = format(selectedMonth, "yyyy-MM");
                return (
                  <div
                    key={cat}
                    className="cursor-pointer group"
                    onClick={() => router.push(`/transactions?month=${month}&category=${cat}`)}
                  >
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-300 group-hover:text-white transition-colors">{CAT_LABELS[cat] ?? cat}</span>
                      <span className="text-gray-400 group-hover:text-gray-200 transition-colors">{fmt(val)}</span>
                    </div>
                    <div className="h-1.5 bg-gray-800 rounded-full">
                      <div
                        className="h-1.5 rounded-full"
                        style={{ width: `${pct}%`, backgroundColor: PIE_COLORS[i % PIE_COLORS.length] }}
                      />
                    </div>
                  </div>
                );
              })}
          </div>
        </div>
      )}

      {/* Forecast — só no mês atual */}
      {isCurrentMonth && forecast && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h3 className="text-base font-semibold mb-4 text-gray-200">
            Previsão para {forecast.month}
            <span className="ml-2 text-sm font-normal text-gray-400">({pace}% do mês decorrido)</span>
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <p className="text-xs text-gray-500 mb-1">Receitas previstas</p>
              <p className="text-lg font-bold text-emerald-400">{fmt(forecast.projected_income)}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 mb-1">Despesas previstas</p>
              <p className="text-lg font-bold text-red-400">{fmt(forecast.projected_expenses)}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 mb-1">Saldo previsto</p>
              <p className={`text-lg font-bold ${forecast.projected_balance >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                {fmt(forecast.projected_balance)}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
