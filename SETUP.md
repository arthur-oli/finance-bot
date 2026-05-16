# Finance Bot — Setup Guide

Bot pessoal de finanças com interface no Telegram, API backend e dashboard web — rodando 100% em cloud (sem precisar deixar o PC ligado).

---

## Visão geral

| Componente | Onde roda | Custo |
|-----------|-----------|-------|
| Banco de dados | [Supabase](https://supabase.com) | Gratuito |
| Backend API | [Fly.io](https://fly.io) | Gratuito (free allowance: 3 VMs 256MB) |
| Bot Telegram | [Fly.io](https://fly.io) | Gratuito (incluso no mesmo allowance) |
| Dashboard web | [Vercel](https://vercel.com) | Gratuito |
| IA (OCR/texto) | [Groq](https://console.groq.com) | Gratuito |

---

## Etapa 1 — Instalar ferramentas (uma vez só)

- [Node.js 18+](https://nodejs.org)
- [flyctl](https://fly.io/docs/hands-on/install-flyctl/) — CLI do Fly.io
- [Git](https://git-scm.com)
- openssl (já vem no Mac/Linux; no Windows: `winget install -e --id ShiningLight.OpenSSL`)

---

## Etapa 2 — Criar contas (~15 min, tudo gratuito exceto Fly.io)

### 2.1 Supabase
1. Acesse [supabase.com](https://supabase.com) → **Start your project**
2. Crie um projeto (região: South America)
3. Vá em **SQL Editor** e cole + execute o conteúdo do arquivo `schema.sql` (raiz do projeto)
4. Anote em **Settings → API**:
   - **Project URL** → será pedido como `SUPABASE_URL`
   - **service_role** key → será pedido como `SUPABASE_SERVICE_ROLE_KEY`

### 2.2 Telegram Bot
1. Abra o Telegram → busque **@BotFather** → envie `/newbot`
2. Siga as instruções e anote o token → `TELEGRAM_BOT_TOKEN`
3. Para descobrir seu user ID: fale com **@userinfobot** → `TELEGRAM_USER_IDS`
   - Múltiplos usuários: separe por vírgula (`123456,789012`)

### 2.3 Groq (IA)
1. Acesse [console.groq.com](https://console.groq.com) → crie conta
2. **API Keys → Create API Key** → anote → `GROQ_API_KEY`

### 2.4 Fly.io
1. Acesse [fly.io](https://fly.io) → **Sign Up** (pede cartão)
2. No terminal: `fly auth login`

### 2.5 Vercel
1. Acesse [vercel.com](https://vercel.com) → **Sign Up**
2. No terminal: `npx vercel login`

---

## Etapa 3 — Rodar o script de setup

Com todas as chaves em mãos, rode **uma vez**:

**Linux / Mac / WSL:**
```bash
bash setup.sh
```

**Windows (PowerShell):**
```powershell
.\setup.ps1
```

O script vai:
1. Pedir cada chave interativamente (sem exibir na tela)
2. Gerar senhas internas aleatórias automaticamente
3. Fazer deploy do backend, bot e dashboard
4. Exibir as URLs finais

Tempo estimado: 10-15 min (maioria é tempo de build no Fly.io).

---

## Etapa 4 — Testar

1. Abra o Telegram, encontre seu bot pelo nome que escolheu
2. Envie: `gastei 50 no mercado` — deve responder com confirmação
3. Acesse o dashboard na URL que o script exibiu

---

## Personalizar a IA

O arquivo `bot/services/ai.py` contém prompts com estabelecimentos do dono original. Edite a seção **"Estabelecimentos conhecidos"** para adicionar os lugares que você frequenta.

Categorias disponíveis: `alimentacao | transporte | saude | lazer | compras | salario | investimento | assinatura | moradia | pet | miscelanea`

---

## Referência de variáveis

| Variável | Onde pegar |
|----------|-----------|
| `SUPABASE_URL` | Supabase → Settings → API |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase → Settings → API |
| `TELEGRAM_BOT_TOKEN` | @BotFather no Telegram |
| `TELEGRAM_USER_IDS` | @userinfobot no Telegram |
| `GROQ_API_KEY` | console.groq.com |
| `API_SECRET_KEY` | Gerado automaticamente pelo script |
| `SESSION_SECRET` | Gerado automaticamente pelo script |
| `DASHBOARD_PASSWORD` | Você escolhe durante o script |
