# Finance Bot — automated cloud setup script (PowerShell)
# Requires: flyctl (logged in), node/npx (vercel logged in), git, openssl
#Requires -Version 5.1
$ErrorActionPreference = "Stop"

function Banner { Write-Host "`n==> $args" -ForegroundColor Green -NoNewline; Write-Host "" }
function Warn   { Write-Host "[!] $args" -ForegroundColor Yellow }
function Die    { Write-Host "[ERRO] $args" -ForegroundColor Red; exit 1 }

function Ask-Secret {
  param([string]$Prompt)
  Write-Host -NoNewline "${Prompt} " -ForegroundColor White
  $ss = Read-Host -AsSecureString
  [System.Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($ss)
  )
}

function Ask-Plain {
  param([string]$Prompt)
  Write-Host -NoNewline "${Prompt} " -ForegroundColor White
  Read-Host
}

function Require-Command {
  param([string]$Cmd, [string]$Hint)
  if (-not (Get-Command $Cmd -ErrorAction SilentlyContinue)) {
    Die "$Cmd não encontrado. $Hint"
  }
}

# ---------- Preflight ----------
Banner "Verificando pré-requisitos"

Require-Command "fly"     "Instale em https://fly.io/docs/hands-on/install-flyctl/"
Require-Command "node"    "Instale em https://nodejs.org"
Require-Command "git"     "Instale em https://git-scm.com"
Require-Command "openssl" "Instale com: winget install -e --id ShiningLight.OpenSSL"

try { fly auth whoami | Out-Null } catch { Die "Não autenticado no Fly.io. Rode: fly auth login" }
try { npx vercel whoami | Out-Null } catch { Die "Não autenticado no Vercel. Rode: npx vercel login" }

Write-Host "OK — ferramentas encontradas" -ForegroundColor Green

# ---------- Collect secrets ----------
Banner "Configuração — cole as chaves quando solicitado"
Write-Host "(os valores ficam ocultos na tela)"

$SUPABASE_URL  = Ask-Secret "SUPABASE_URL (ex: https://xxxx.supabase.co):"
$SUPABASE_KEY  = Ask-Secret "SUPABASE_SERVICE_ROLE_KEY (começa com eyJ...):"
$TG_TOKEN      = Ask-Secret "TELEGRAM_BOT_TOKEN (ex: 123456:ABC...):"
$TG_IDS        = Ask-Plain  "TELEGRAM_USER_IDS (IDs separados por vírgula):"
$GROQ_KEY      = Ask-Secret "GROQ_API_KEY (começa com gsk_...):"
$BACKEND_APP   = Ask-Plain  "Nome do app backend no Fly.io (ex: meubot-backend):"
$BOT_APP       = Ask-Plain  "Nome do app bot no Fly.io (ex: meubot-worker):"

# Generate random secrets
$API_KEY        = (openssl rand -hex 32).Trim()
$SESSION_SECRET = (openssl rand -hex 32).Trim()
$BACKEND_URL    = "https://${BACKEND_APP}.fly.dev"

Warn "API_SECRET_KEY e SESSION_SECRET gerados aleatoriamente"

do {
  $DASH_PASS  = Ask-Secret "Escolha uma senha para o dashboard web:"
  $DASH_PASS2 = Ask-Secret "Confirme a senha:"
  if ($DASH_PASS -ne $DASH_PASS2) { Warn "Senhas diferentes. Tente novamente." }
} while ($DASH_PASS -ne $DASH_PASS2)

# ---------- Backend deploy ----------
Banner "Deploy do Backend (Fly.io: ${BACKEND_APP})"

Push-Location backend

$existingApps = fly apps list 2>&1
if ($existingApps -notmatch [regex]::Escape($BACKEND_APP)) {
  Write-Host "Criando app '${BACKEND_APP}'..."
  fly apps create $BACKEND_APP
} else {
  Write-Host "App '${BACKEND_APP}' ja existe, continuando..."
}

# Update fly.toml
(Get-Content fly.toml) -replace '^app = .*', "app = `"${BACKEND_APP}`"" | Set-Content fly.toml -Encoding utf8

fly secrets set `
  "SUPABASE_URL=${SUPABASE_URL}" `
  "SUPABASE_SERVICE_ROLE_KEY=${SUPABASE_KEY}" `
  "API_SECRET_KEY=${API_KEY}" `
  --app $BACKEND_APP

fly deploy --app $BACKEND_APP --wait-timeout 120

Pop-Location
Write-Host "Backend OK -> ${BACKEND_URL}" -ForegroundColor Green

# ---------- Bot deploy ----------
Banner "Deploy do Bot (Fly.io: ${BOT_APP})"

$existingApps = fly apps list 2>&1
if ($existingApps -notmatch [regex]::Escape($BOT_APP)) {
  Write-Host "Criando app '${BOT_APP}'..."
  fly apps create $BOT_APP
} else {
  Write-Host "App '${BOT_APP}' ja existe, continuando..."
}

# Update root fly.toml
(Get-Content fly.toml) -replace '^app = .*', "app = `"${BOT_APP}`"" |
  ForEach-Object { $_ -replace 'BACKEND_URL = .*', "BACKEND_URL = `"${BACKEND_URL}`"" } |
  Set-Content fly.toml -Encoding utf8

fly secrets set `
  "TELEGRAM_BOT_TOKEN=${TG_TOKEN}" `
  "TELEGRAM_USER_IDS=${TG_IDS}" `
  "BACKEND_URL=${BACKEND_URL}" `
  "API_SECRET_KEY=${API_KEY}" `
  "GROQ_API_KEY=${GROQ_KEY}" `
  --app $BOT_APP

fly deploy --app $BOT_APP --wait-timeout 120

Write-Host "Bot OK" -ForegroundColor Green

# ---------- Dashboard deploy ----------
Banner "Deploy do Dashboard (Vercel)"

Push-Location dashboard

# Reset vercel.json alias so it doesn't conflict with owner's project
if (Test-Path vercel.json) {
  '{}' | Set-Content vercel.json -Encoding utf8
}

if (-not (Test-Path .vercel/project.json)) {
  Write-Host "Vinculando projeto no Vercel (responda as perguntas interativamente)..."
  npx vercel link
}

# Set env vars via printf equivalent (avoid CRLF)
foreach ($pair in @(
  @{ Name = "BACKEND_URL";        Value = $BACKEND_URL },
  @{ Name = "API_SECRET_KEY";     Value = $API_KEY },
  @{ Name = "DASHBOARD_PASSWORD"; Value = $DASH_PASS },
  @{ Name = "SESSION_SECRET";     Value = $SESSION_SECRET }
)) {
  $tmp = [System.IO.Path]::GetTempFileName()
  [System.IO.File]::WriteAllText($tmp, $pair.Value, [System.Text.Encoding]::UTF8)
  Get-Content $tmp -Raw | npx vercel env add $pair.Name production --force 2>&1 | Out-Null
  Remove-Item $tmp
}

$deployOut = npx vercel --prod --yes 2>&1
$DASHBOARD_URL = ($deployOut | Select-String -Pattern "https://[^ ]+\.vercel\.app" | Select-Object -Last 1).Matches.Value

Pop-Location

# ---------- Summary ----------
Banner "Setup concluido!"
Write-Host ""
Write-Host "  Backend:   $BACKEND_URL" -ForegroundColor Cyan
Write-Host "  Dashboard: $DASHBOARD_URL" -ForegroundColor Cyan
Write-Host ""
Write-Host "Proximos passos:"
Write-Host "  1. Abra o Telegram e mande uma mensagem pro seu bot"
Write-Host "  2. Acesse o dashboard e faca login com a senha que definiu"
Write-Host "  3. Cadastre seus cartoes no dashboard antes de usar"
