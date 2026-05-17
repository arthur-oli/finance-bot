"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import type { Card, Settings } from "@/lib/types";

const ALL_CATEGORIES = [
  "alimentacao", "transporte", "saude", "lazer", "compras",
  "salario", "investimento", "assinatura", "moradia", "pet",
  "mercado", "vestuario", "cosmeticos", "presentes", "miscelanea",
];

const CAT_LABEL: Record<string, string> = {
  alimentacao: "Alimentação", transporte: "Transporte", saude: "Saúde",
  lazer: "Lazer", compras: "Compras", salario: "Salário",
  investimento: "Investimento", assinatura: "Assinatura", moradia: "Moradia",
  pet: "Pet", mercado: "Mercado", vestuario: "Vestuário",
  cosmeticos: "Cosméticos", presentes: "Presentes", miscelanea: "Miscelânea",
};

const TABS = ["Geral", "IA", "Usuários"] as const;
type Tab = typeof TABS[number];

function Section({ title, description, children }: { title: string; description?: string; children: React.ReactNode }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <div className="mb-4">
        <h3 className="text-base font-semibold text-gray-100">{title}</h3>
        {description && <p className="text-sm text-gray-500 mt-0.5">{description}</p>}
      </div>
      {children}
    </div>
  );
}

function Chip({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors border ${
        active
          ? "bg-emerald-700/60 border-emerald-600 text-emerald-300"
          : "bg-gray-800 border-gray-700 text-gray-500 hover:border-gray-600 hover:text-gray-400"
      }`}
    >
      {active ? "✓ " : ""}{label}
    </button>
  );
}

export default function SettingsPage() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>("Geral");

  const { data: settings, isLoading } = useQuery<Settings>({
    queryKey: ["settings"],
    queryFn: () => api.get("/api/settings/"),
  });
  const { data: cards } = useQuery<Card[]>({
    queryKey: ["cards"],
    queryFn: () => api.get("/api/cards/"),
  });
  const { data: users } = useQuery<string[]>({
    queryKey: ["users"],
    queryFn: () => api.get("/api/users/"),
    staleTime: 5 * 60 * 1000,
  });

  // ── Local edit state ──────────────────────────────────────────────────────
  const [cats, setCats] = useState<string[]>(ALL_CATEGORIES);
  const [newCat, setNewCat] = useState("");
  const [est, setEst] = useState<Record<string, string[]>>({});
  const [newEst, setNewEst] = useState<Record<string, string>>({});
  const [detailMarkets, setDetailMarkets] = useState<string[]>([]);
  const [newMarket, setNewMarket] = useState("");
  const [pixCard, setPixCard] = useState("");
  const [extraPrompt, setExtraPrompt] = useState("");
  const [timezone, setTimezone] = useState("America/Sao_Paulo");
  const [baseBalance, setBaseBalance] = useState("0");
  const [allowedIds, setAllowedIds] = useState<number[]>([]);
  const [newId, setNewId] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!settings) return;
    setCats(settings.active_categories?.length ? settings.active_categories : ALL_CATEGORIES);
    setEst(settings.establishments ?? {});
    setDetailMarkets(settings.detail_markets ?? []);
    setPixCard(settings.default_pix_card ?? "");
    setExtraPrompt(settings.additional_system_prompt ?? "");
    setTimezone(settings.scheduler_timezone ?? "America/Sao_Paulo");
    setBaseBalance(String(settings.base_balance ?? "0"));
    setAllowedIds(settings.allowed_telegram_ids ?? []);
  }, [settings]);

  const save = useMutation({
    mutationFn: () =>
      api.patch<Settings>("/api/settings/", {
        active_categories: cats,
        establishments: est,
        detail_markets: detailMarkets,
        default_pix_card: pixCard,
        additional_system_prompt: extraPrompt,
        scheduler_timezone: timezone,
        base_balance: parseFloat(baseBalance) || 0,
        allowed_telegram_ids: allowedIds,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["settings"] });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    },
  });

  // ── Helpers ───────────────────────────────────────────────────────────────
  function toggleCat(cat: string) {
    setCats((prev) =>
      prev.includes(cat) ? (prev.length > 1 ? prev.filter((c) => c !== cat) : prev) : [...prev, cat]
    );
  }

  function addCat() {
    const v = newCat.trim().toLowerCase().replace(/\s+/g, "_");
    if (v && !cats.includes(v)) { setCats((p) => [...p, v]); setNewCat(""); }
  }

  function addEst(cat: string) {
    const v = (newEst[cat] ?? "").trim();
    if (!v) return;
    setEst((p) => ({ ...p, [cat]: [...(p[cat] ?? []), v] }));
    setNewEst((p) => ({ ...p, [cat]: "" }));
  }

  function removeEst(cat: string, idx: number) {
    setEst((p) => ({ ...p, [cat]: p[cat].filter((_, i) => i !== idx) }));
  }

  function toggleMarket(m: string) {
    setDetailMarkets((p) => (p.includes(m) ? p.filter((x) => x !== m) : [...p, m]));
  }

  function addMarket() {
    const v = newMarket.trim();
    if (v && !detailMarkets.includes(v)) { setDetailMarkets((p) => [...p, v]); setNewMarket(""); }
  }

  function addId() {
    const v = parseInt(newId.trim(), 10);
    if (!isNaN(v) && !allowedIds.includes(v)) { setAllowedIds((p) => [...p, v]); setNewId(""); }
  }

  function removeId(id: number) {
    setAllowedIds((p) => p.filter((x) => x !== id));
  }

  const inp = "bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 placeholder-gray-600 focus:outline-none focus:border-emerald-600 w-full";
  const saveBtn = (
    <button
      onClick={() => save.mutate()}
      disabled={save.isPending}
      className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white rounded-lg px-5 py-2 text-sm font-medium transition-colors"
    >
      {save.isPending ? "Salvando…" : saved ? "✓ Salvo!" : "Salvar alterações"}
    </button>
  );

  if (isLoading) return <div className="text-gray-500 text-sm p-4">Carregando configurações…</div>;

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold">Configurações</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            Alterações são aplicadas pelo bot em até 5 minutos, sem restart.
          </p>
        </div>
        {saveBtn}
      </div>

      {save.isError && (
        <div className="mb-4 bg-red-900/40 border border-red-700 text-red-300 rounded-lg px-4 py-3 text-sm">
          Erro ao salvar. Tente novamente.
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-gray-900 border border-gray-800 rounded-xl p-1 w-fit">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              tab === t
                ? "bg-gray-700 text-gray-100"
                : "text-gray-500 hover:text-gray-300"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="space-y-5">

        {/* ══ ABA: GERAL ══════════════════════════════════════════════════════ */}
        {tab === "Geral" && (
          <>
            <Section title="Configurações gerais">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-gray-500 mb-1.5 block">Fuso horário</label>
                  <input
                    className={inp}
                    value={timezone}
                    onChange={(e) => setTimezone(e.target.value)}
                    placeholder="America/Sao_Paulo"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1.5 block">Saldo base (R$)</label>
                  <input
                    className={inp}
                    type="number"
                    step="0.01"
                    value={baseBalance}
                    onChange={(e) => setBaseBalance(e.target.value)}
                    placeholder="0"
                  />
                  <p className="text-xs text-gray-600 mt-1">Valor inicial somado ao saldo calculado nas análises.</p>
                </div>
              </div>
            </Section>

            <Section
              title="Cartão padrão para pix / débito"
              description='Quando o usuário diz "pix", "débito" ou "conta" sem mencionar cartão, o bot usa esse.'
            >
              <div className="flex flex-col sm:flex-row gap-3">
                <input
                  className={inp}
                  placeholder="Ex: Nubank Conta"
                  value={pixCard}
                  onChange={(e) => setPixCard(e.target.value)}
                />
                {cards && cards.length > 0 && (
                  <select
                    className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-400 focus:outline-none focus:border-emerald-600 sm:w-56"
                    value=""
                    onChange={(e) => e.target.value && setPixCard(e.target.value)}
                  >
                    <option value="">Escolher dos cartões…</option>
                    {cards.map((c) => (
                      <option key={c.id} value={c.name}>{c.name}</option>
                    ))}
                  </select>
                )}
              </div>
            </Section>
          </>
        )}

        {/* ══ ABA: IA ══════════════════════════════════════════════════════════ */}
        {tab === "IA" && (
          <>
            <Section
              title="Categorias ativas"
              description="O bot só aceita transações nessas categorias. Pelo menos uma deve estar ativa."
            >
              <div className="flex flex-wrap gap-2 mb-4">
                {[...new Set([...ALL_CATEGORIES, ...cats.filter((c) => !ALL_CATEGORIES.includes(c))])].map((cat) => (
                  <Chip key={cat} label={CAT_LABEL[cat] ?? cat} active={cats.includes(cat)} onClick={() => toggleCat(cat)} />
                ))}
              </div>
              <div className="flex gap-2">
                <input
                  className={inp + " flex-1"}
                  placeholder="Nova categoria personalizada…"
                  value={newCat}
                  onChange={(e) => setNewCat(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && addCat()}
                />
                <button onClick={addCat} className="bg-gray-700 hover:bg-gray-600 text-gray-200 rounded-lg px-4 py-2 text-sm transition-colors">
                  + Adicionar
                </button>
              </div>
            </Section>

            <Section
              title="Estabelecimentos conhecidos"
              description="A IA usa essa lista para classificar automaticamente sem você precisar especificar a categoria."
            >
              <div className="space-y-4">
                {cats.map((cat) => (
                  <div key={cat} className="bg-gray-800/60 rounded-lg p-4">
                    <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
                      {CAT_LABEL[cat] ?? cat}
                    </p>
                    <div className="flex flex-wrap gap-2 mb-2">
                      {(est[cat] ?? []).map((place, idx) => (
                        <span key={idx} className="flex items-center gap-1 bg-gray-700 text-gray-300 text-sm rounded-full px-3 py-1">
                          {place}
                          <button onClick={() => removeEst(cat, idx)} className="text-gray-500 hover:text-red-400 ml-1 leading-none">✕</button>
                        </span>
                      ))}
                      {(est[cat] ?? []).length === 0 && (
                        <span className="text-xs text-gray-600 italic">Nenhum estabelecimento</span>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <input
                        className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-100 placeholder-gray-600 focus:outline-none focus:border-emerald-600 flex-1"
                        placeholder="Adicionar estabelecimento…"
                        value={newEst[cat] ?? ""}
                        onChange={(e) => setNewEst((p) => ({ ...p, [cat]: e.target.value }))}
                        onKeyDown={(e) => e.key === "Enter" && addEst(cat)}
                      />
                      <button onClick={() => addEst(cat)} className="bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg px-3 py-1.5 text-sm transition-colors">+</button>
                    </div>
                  </div>
                ))}
              </div>
            </Section>

            <Section
              title="Mercados com nota detalhada"
              description="Nesses mercados o bot lê cada item da nota e divide automaticamente entre categorias."
            >
              <div className="flex flex-wrap gap-2 mb-4">
                {detailMarkets.map((m) => (
                  <Chip key={m} label={m} active={true} onClick={() => toggleMarket(m)} />
                ))}
              </div>
              <div className="flex gap-2">
                <input
                  className={inp + " flex-1"}
                  placeholder="Nome do mercado…"
                  value={newMarket}
                  onChange={(e) => setNewMarket(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && addMarket()}
                />
                <button onClick={addMarket} className="bg-gray-700 hover:bg-gray-600 text-gray-200 rounded-lg px-4 py-2 text-sm transition-colors">
                  + Adicionar
                </button>
              </div>
            </Section>

            <Section
              title="Instruções extras para a IA"
              description="Texto adicionado ao final do prompt. Use para ensinar contextos pessoais: nomes, estabelecimentos incomuns, regras específicas."
            >
              <textarea
                className={inp + " min-h-[120px] resize-y font-mono text-xs leading-relaxed"}
                placeholder={"Exemplos:\n• Rodrigo é meu cachorro — gastos com ele vão em 'pet'\n• Cineflix é minha assinatura de cinema\n• Compras no AliExpress vão em 'compras'"}
                value={extraPrompt}
                onChange={(e) => setExtraPrompt(e.target.value)}
              />
              <p className="text-xs text-gray-600 mt-2">
                {extraPrompt.length} caracteres · aplicado nas próximas mensagens ao bot
              </p>
            </Section>
          </>
        )}

        {/* ══ ABA: USUÁRIOS ════════════════════════════════════════════════════ */}
        {tab === "Usuários" && (
          <>
            <Section
              title="IDs autorizados no bot"
              description="Somente esses IDs do Telegram podem confirmar transações. O bot ignora qualquer outra pessoa."
            >
              <div className="flex flex-wrap gap-2 mb-4">
                {allowedIds.length === 0 && (
                  <p className="text-sm text-gray-600 italic">Nenhum ID configurado — o bot usa a lista do Fly.io como fallback.</p>
                )}
                {allowedIds.map((id) => (
                  <span key={id} className="flex items-center gap-1.5 bg-gray-800 border border-gray-700 text-gray-300 text-sm rounded-full px-4 py-1.5 font-mono">
                    {id}
                    <button onClick={() => removeId(id)} className="text-gray-500 hover:text-red-400 leading-none">✕</button>
                  </span>
                ))}
              </div>
              <div className="flex gap-2">
                <input
                  className={inp + " flex-1 font-mono"}
                  placeholder="ID numérico do Telegram…"
                  value={newId}
                  onChange={(e) => setNewId(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && addId()}
                  type="number"
                />
                <button onClick={addId} className="bg-gray-700 hover:bg-gray-600 text-gray-200 rounded-lg px-4 py-2 text-sm transition-colors">
                  + Adicionar
                </button>
              </div>
              <p className="text-xs text-gray-600 mt-3">
                Para descobrir seu ID: envie qualquer mensagem para{" "}
                <a href="https://t.me/userinfobot" target="_blank" className="text-emerald-500 hover:underline">@userinfobot</a>{" "}
                no Telegram. Mudanças entram em vigor em até 5 minutos.
              </p>
            </Section>

            <Section
              title="Usuários com transações registradas"
              description="Nomes dos usuários que já enviaram ao menos uma transação pelo bot."
            >
              {!users || users.length === 0 ? (
                <p className="text-sm text-gray-600 italic">Nenhuma transação registrada ainda.</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {users.map((u) => (
                    <span key={u} className="bg-gray-800 border border-gray-700 text-gray-300 text-sm rounded-full px-4 py-1.5">
                      {u}
                    </span>
                  ))}
                </div>
              )}
            </Section>
          </>
        )}

      </div>

      {/* Bottom save */}
      <div className="flex justify-end mt-6">{saveBtn}</div>

      {/* Sticky save (mobile) */}
      <div className="sm:hidden fixed bottom-16 left-0 right-0 px-4 pb-2 pt-3 bg-gray-950/90 backdrop-blur border-t border-gray-800">
        <button
          onClick={() => save.mutate()}
          disabled={save.isPending}
          className="w-full bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white rounded-lg py-2.5 text-sm font-medium transition-colors"
        >
          {save.isPending ? "Salvando…" : saved ? "✓ Salvo!" : "Salvar alterações"}
        </button>
      </div>
    </div>
  );
}
