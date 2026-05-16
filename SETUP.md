# Finance Bot — Setup Guide

Bot pessoal de finanças com interface no Telegram, API backend e dashboard web.

---

## Pré-requisitos

- Python 3.9+
- Node.js 18+
- Conta no [Supabase](https://supabase.com) (gratuito)
- Conta no [Groq](https://console.groq.com) (gratuito)
- Bot no Telegram (via [@BotFather](https://t.me/BotFather))

---

## 1. Banco de dados (Supabase)

1. Crie um projeto no Supabase
2. Vá em **SQL Editor** e rode o arquivo `supabase/migrations/001_initial_schema.sql`
3. Anote:
   - **Project URL** → `SUPABASE_URL`
   - **service_role key** (em Project Settings > API) → `SUPABASE_SERVICE_ROLE_KEY`

---

## 2. Telegram Bot

1. Fale com [@BotFather](https://t.me/BotFather) → `/newbot` → siga as instruções
2. Anote o token gerado → `TELEGRAM_BOT_TOKEN`
3. Descubra seu Telegram User ID: fale com [@userinfobot](https://t.me/userinfobot) → `TELEGRAM_USER_ID`

---

## 3. Groq API

1. Crie conta em [console.groq.com](https://console.groq.com)
2. Gere uma API Key → `GROQ_API_KEY`

---

## 4. Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
```

Edite `backend/.env`:

```env
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
API_SECRET_KEY=qualquer-string-longa-e-aleatoria
ALLOWED_ORIGINS=http://localhost:3000
```

Inicie:

```bash
python -m uvicorn app.main:app --reload
# Rodando em http://localhost:8000
```

---

## 5. Bot

```bash
cd bot
pip install -r requirements.txt
cp .env.example .env
```

Edite `bot/.env`:

```env
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_USER_ID=123456789
BACKEND_URL=http://localhost:8000
API_SECRET_KEY=mesma-string-do-backend
GROQ_API_KEY=gsk_...
```

Inicie:

```bash
python main.py
```

---

## 6. Dashboard

```bash
cd dashboard
npm install
cp .env.local.example .env.local   # se não existir, crie manualmente
```

Crie `dashboard/.env.local`:

```env
BACKEND_URL=http://localhost:8000
API_SECRET_KEY=mesma-string-do-backend
```

Inicie:

```bash
npm run dev
# Acessível em http://localhost:3000
```

---

## 7. Personalizar o system prompt da IA

O arquivo `bot/services/ai.py` contém dois prompts hardcoded com dados pessoais do dono original. **Você precisa adaptá-los antes de usar.**

Abra o arquivo e edite as duas constantes no topo:

**`_SYSTEM_TPL`** — usado para interpretar mensagens de texto:
- Substitua os estabelecimentos na seção `Estabelecimentos conhecidos:` pelos lugares que você frequenta
- A lista de categorias disponíveis é: `alimentacao | transporte | saude | lazer | compras | salario | investimento | assinatura | moradia | pet | miscelanea`
- A linha `{cards}` é preenchida automaticamente com os cartões cadastrados no Supabase — não altere

**`_RECEIPT_TPL`** — usado para OCR de comprovantes/fotos:
- Mais genérico, normalmente não precisa de grandes alterações

Exemplo da seção a editar:
```python
Estabelecimentos conhecidos:
alimentacao: McDonald's, Subway, iFood
transporte: Uber, 99
assinatura: Spotify, Netflix, Amazon Prime
# ... adicione os seus
```

Os cartões (`{cards}`) são carregados dinamicamente do banco — cadastre-os pelo bot ou dashboard após subir o sistema.

---

## Uso básico

Com os três serviços rodando, abra o Telegram e fale com o seu bot:

- Mande um texto descrevendo um gasto: `"Gastei 45 reais no almoço"`
- Mande uma foto de nota fiscal/recibo para lançamento automático
- Use os comandos do bot para ver saldos, metas e resumos
- Acesse `http://localhost:3000` para o dashboard completo

O bot manda um resumo financeiro diário automaticamente às 8h (horário de Brasília).

---

## Variáveis — resumo rápido

| Variável | Onde pegar |
|---|---|
| `SUPABASE_URL` | Supabase > Project Settings > API |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase > Project Settings > API |
| `TELEGRAM_BOT_TOKEN` | @BotFather no Telegram |
| `TELEGRAM_USER_ID` | @userinfobot no Telegram |
| `GROQ_API_KEY` | console.groq.com |
| `API_SECRET_KEY` | Você mesmo — qualquer string segura, igual nos três serviços |
