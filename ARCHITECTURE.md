# Finance Bot — Arquitetura

## Estrutura
```
finance-bot/
├── bot/                  # Telegram bot (worker Fly.io)
│   ├── handlers/         # text.py, photo.py, commands.py
│   ├── services/         # claude.py (Groq API), backend_client.py
│   └── main.py
├── backend/              # FastAPI (web Fly.io)
│   └── app/
│       ├── routers/      # transactions, cards, subscriptions, goals, forecast, analytics, settings
│       ├── services/     # transaction_service, forecast_service
│       ├── scheduler/    # jobs.py (APScheduler)
│       ├── deps/auth.py  # X-API-Key via hmac.compare_digest
│       └── main.py
├── dashboard/            # Next.js 15 (local, npm run dev)
│   ├── app/
│   │   ├── api/proxy/    # Server route injeta API key
│   │   └── page.tsx + transactions/ cards/ forecast/ goals/
│   └── lib/api.ts
├── supabase/migrations/  # 001_initial_schema.sql
├── Dockerfile.bot        # Copia bot/ como subdir (preserva imports)
└── fly.toml              # Bot worker (sem [[services]])
```

## Stack
| Camada | Tecnologia |
|---|---|
| Bot | python-telegram-bot 21, Groq API (llama-3.3-70b texto + llama-4-scout visão) |
| Backend | FastAPI, Uvicorn, APScheduler, SlowAPI, Structlog |
| Banco | Supabase (Postgres) — 6 tabelas: settings, cards, transactions, subscriptions, goals, seasonal_reserves |
| Dashboard | Next.js 15 App Router, React Query, Recharts, Tailwind v4 |
| Hosting | Fly.io (gru/São Paulo) — bot + backend, free tier |

## Deploy
```bash
# Backend
cd backend && flyctl deploy --remote-only

# Bot (Dockerfile.bot na raiz)
cd .. && flyctl deploy --remote-only

# Dashboard (local apenas)
cd dashboard && npm run dev   # http://localhost:3000
# Node em C:\Program Files\nodejs — adicionar ao PATH manualmente se necessário
```

## Secrets no Fly.io
- **Bot:** `TELEGRAM_BOT_TOKEN`, `TELEGRAM_USER_ID`, `API_SECRET_KEY`, `GROQ_API_KEY`
- **Backend:** `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `API_SECRET_KEY`
- **Bot fly.toml env:** `BACKEND_URL=https://finance-tutur-backend.fly.dev`

## Decisões relevantes
- Bot usa URL pública do backend (não `.internal`) — rede interna Fly.io era instável
- Dockerfile.bot na raiz (não em bot/) para preservar `from bot.handlers...` imports
- Dashboard proxy em `/api/proxy` esconde API key do browser
- Groq: `llama-3.3-70b-versatile` (texto), `meta-llama/llama-4-scout-17b-16e-instruct` (imagem)
- Forecast: 70% média histórica ponderada (3 meses: 0.5/0.3/0.2) + 30% ritmo atual
- Scheduler: resumo diário às 8h, renovação de assinaturas às 00h05
- Auth: `hmac.compare_digest` (tempo constante, header `X-API-Key`)
- Tailwind v4 exige `postcss.config.js` com `@tailwindcss/postcss` — ausência quebra todo CSS
