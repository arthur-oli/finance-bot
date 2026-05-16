#!/usr/bin/env bash
# Finance Bot — automated cloud setup script
# Requires: flyctl (logged in), node/npx (vercel logged in), git
set -euo pipefail

BOLD="\033[1m"
GREEN="\033[32m"
YELLOW="\033[33m"
RED="\033[31m"
RESET="\033[0m"

banner() { echo -e "\n${BOLD}${GREEN}==> $1${RESET}"; }
warn()   { echo -e "${YELLOW}[!] $1${RESET}"; }
die()    { echo -e "${RED}[ERRO] $1${RESET}" >&2; exit 1; }
ask()    { echo -e -n "${BOLD}$1${RESET} "; read -r "$2"; }
ask_secret() {
  echo -e -n "${BOLD}$1${RESET} "
  read -rs "$2"
  echo
}

# ---------- Preflight checks ----------
banner "Verificando pré-requisitos"

command -v fly    >/dev/null 2>&1 || die "flyctl não encontrado. Instale em https://fly.io/docs/hands-on/install-flyctl/"
command -v node   >/dev/null 2>&1 || die "Node.js não encontrado. Instale em https://nodejs.org"
command -v git    >/dev/null 2>&1 || die "git não encontrado."
command -v openssl>/dev/null 2>&1 || die "openssl não encontrado."

fly auth whoami >/dev/null 2>&1 || die "Não autenticado no Fly.io. Rode: fly auth login"
npx vercel whoami >/dev/null 2>&1 || die "Não autenticado no Vercel. Rode: npx vercel login"

echo "OK — ferramentas encontradas"

# ---------- Collect secrets ----------
banner "Configuração — cole as chaves quando solicitado"
echo "(os valores não aparecem na tela)"
echo

ask_secret "SUPABASE_URL (ex: https://xxxx.supabase.co):" SUPABASE_URL
ask_secret "SUPABASE_SERVICE_ROLE_KEY (começa com eyJ...):"  SUPABASE_KEY
ask_secret "TELEGRAM_BOT_TOKEN (ex: 123456:ABC...):"        TG_TOKEN
ask        "TELEGRAM_USER_IDS (IDs separados por vírgula):" TG_IDS
ask_secret "GROQ_API_KEY (começa com gsk_...):"             GROQ_KEY
ask        "Nome do app backend no Fly.io (ex: meubot-backend):" BACKEND_APP
ask        "Nome do app bot no Fly.io (ex: meubot-worker):"      BOT_APP

# Generate internal secrets
API_KEY=$(openssl rand -hex 32)
SESSION_SECRET=$(openssl rand -hex 32)
BACKEND_URL="https://${BACKEND_APP}.fly.dev"

echo
warn "API_SECRET_KEY e SESSION_SECRET gerados aleatoriamente (não precisam ser anotados)"

# ---------- Ask for dashboard password ----------
while true; do
  ask_secret "Escolha uma senha para o dashboard web:" DASH_PASS
  ask_secret "Confirme a senha:" DASH_PASS2
  [ "$DASH_PASS" = "$DASH_PASS2" ] && break
  warn "Senhas diferentes. Tente novamente."
done

# ---------- Backend deploy ----------
banner "Deploy do Backend (Fly.io: ${BACKEND_APP})"

cd backend

if ! fly apps list 2>/dev/null | grep -q "^${BACKEND_APP}"; then
  echo "Criando app '${BACKEND_APP}'..."
  fly apps create "${BACKEND_APP}"
else
  echo "App '${BACKEND_APP}' já existe, continuando..."
fi

# Update fly.toml app name
sed -i "s/^app = .*/app = \"${BACKEND_APP}\"/" fly.toml

fly secrets set \
  SUPABASE_URL="${SUPABASE_URL}" \
  SUPABASE_SERVICE_ROLE_KEY="${SUPABASE_KEY}" \
  API_SECRET_KEY="${API_KEY}" \
  --app "${BACKEND_APP}"

fly deploy --app "${BACKEND_APP}" --wait-timeout 120

cd ..
echo -e "${GREEN}Backend OK → ${BACKEND_URL}${RESET}"

# ---------- Bot deploy ----------
banner "Deploy do Bot (Fly.io: ${BOT_APP})"

if ! fly apps list 2>/dev/null | grep -q "^${BOT_APP}"; then
  echo "Criando app '${BOT_APP}'..."
  fly apps create "${BOT_APP}"
else
  echo "App '${BOT_APP}' já existe, continuando..."
fi

# Update fly.toml app name and backend URL
sed -i "s/^app = .*/app = \"${BOT_APP}\"/" fly.toml
sed -i "s|BACKEND_URL = .*|BACKEND_URL = \"${BACKEND_URL}\"|" fly.toml

fly secrets set \
  TELEGRAM_BOT_TOKEN="${TG_TOKEN}" \
  TELEGRAM_USER_IDS="${TG_IDS}" \
  BACKEND_URL="${BACKEND_URL}" \
  API_SECRET_KEY="${API_KEY}" \
  GROQ_API_KEY="${GROQ_KEY}" \
  --app "${BOT_APP}"

fly deploy --app "${BOT_APP}" --wait-timeout 120

echo -e "${GREEN}Bot OK${RESET}"

# ---------- Dashboard deploy ----------
banner "Deploy do Dashboard (Vercel)"

cd dashboard

# Remove alias for financebot-tutur (user's own alias) so Vercel doesn't conflict
if [ -f vercel.json ]; then
  echo '{}' > vercel.json
fi

# Link or create Vercel project
if [ ! -f .vercel/project.json ]; then
  echo "Vinculando projeto no Vercel (responda as perguntas interativamente)..."
  npx vercel link
fi

# Set env vars (production only)
printf '%s' "${BACKEND_URL}"   | npx vercel env add BACKEND_URL       production --force 2>/dev/null || true
printf '%s' "${API_KEY}"       | npx vercel env add API_SECRET_KEY    production --force 2>/dev/null || true
printf '%s' "${DASH_PASS}"     | npx vercel env add DASHBOARD_PASSWORD production --force 2>/dev/null || true
printf '%s' "${SESSION_SECRET}"| npx vercel env add SESSION_SECRET    production --force 2>/dev/null || true

DASHBOARD_URL=$(npx vercel --prod --yes 2>&1 | grep -E "https://.+\.vercel\.app" | tail -1)

cd ..

# ---------- Summary ----------
banner "Setup concluído!"
echo
echo -e "  Backend:   ${BOLD}${BACKEND_URL}${RESET}"
echo -e "  Dashboard: ${BOLD}${DASHBOARD_URL:-https://vercel.com (veja o link no painel)}${RESET}"
echo
echo "Próximos passos:"
echo "  1. Abra o Telegram e mande uma mensagem pro seu bot"
echo "  2. Acesse o dashboard e faça login com a senha que definiu"
echo "  3. Cadastre seus cartões no dashboard antes de usar"
