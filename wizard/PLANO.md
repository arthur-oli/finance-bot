# Plano de implementação — Wizard (Groups restantes)

> Última atualização: 2026-05-19
> Status dos groups concluídos: 1 ✅ 2 ✅ 3 ✅ 4 ✅ (shortcut) · 5 em andamento

---

## Group 5 — Mensagem de teste pelo Telegram  *(próximo)*

**Tela:** `_page_done`  
**Posição:** card após health check, antes da faixa laranja de senha  
**Objetivo:** confirmar ao usuário que o bot está recebendo mensagens

### O que fazer
1. Ao abrir `_page_done`, enviar automaticamente uma mensagem de teste via Telegram Bot API:
   - `GET https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage`
   - `chat_id` = primeiro ID em `TELEGRAM_USER_IDS` (split por vírgula, strip)
   - `text` = `"✅ Finance Bot configurado com sucesso! Esta mensagem confirma que o bot está funcionando."`
2. Card visual (igual ao health check):
   - `⏳ Enviando mensagem de teste…` → `✅ Mensagem enviada! Verifique o Telegram.` / `⚠️ Não foi possível enviar`
   - Botão "↺ Reenviar" para tentar novamente
3. Em modo DEMO: simular delay 1.2s + sucesso

### Implementação técnica
```python
import urllib.request, urllib.parse, json as _json

token   = self._var("TELEGRAM_BOT_TOKEN").get().strip()
chat_id = self._var("TELEGRAM_USER_IDS").get().strip().split(",")[0].strip()
url     = f"https://api.telegram.org/bot{token}/sendMessage"
data    = urllib.parse.urlencode({"chat_id": chat_id, "text": "..."}).encode()
req     = urllib.request.urlopen(url, data=data, timeout=10)
ok      = req.status == 200
```

### Casos de erro tratados
- Token inválido → `401 Unauthorized`
- User ID inválido → `400 Bad Request` (mensagem específica)
- Timeout → `⚠️ Bot demorou a responder`
- Em todos os casos: mostrar `⚠️` com `detail` da exceção e botão "Reenviar"

---

## Group 6 — Exportar backup de credenciais

**Tela:** `_page_done`  
**Posição:** botão secundário no footer ("Exportar credenciais") ou ao lado do botão "Copiar senha"  
**Objetivo:** salvar em texto legível todas as configurações para o usuário guardar

### O que fazer
1. Criar arquivo `FinanceBot-credenciais-{data}.txt` no Desktop do usuário
2. Conteúdo:
   ```
   Finance Bot — Credenciais (geradas em DD/MM/YYYY HH:MM)
   ─────────────────────────────────────────────────────
   Painel web:         https://xxx.vercel.app
   Senha do painel:    xxxx
   Backend:            https://xxx.fly.dev
   Bot Telegram:       https://xxx.fly.dev

   Supabase URL:       https://...
   Supabase Project:   ...
   Telegram Bot Token: ...
   Telegram User IDs:  ...
   Groq API Key:       gsk_...
   ```
3. Abrir o arquivo no Bloco de Notas automaticamente após salvar
4. Exibir toast/mensagem "Arquivo salvo no Desktop" por 3 segundos

### Implementação técnica
```python
from datetime import datetime
desktop = os.path.join(os.path.expanduser("~"), "Desktop")
fname   = f"FinanceBot-credenciais-{datetime.now():%Y%m%d}.txt"
path    = os.path.join(desktop, fname)
with open(path, "w", encoding="utf-8") as f:
    f.write(conteudo)
subprocess.Popen(["notepad.exe", path])
```

### Cuidados
- Não sobrescrever se arquivo já existe (adicionar sufixo `-2`, `-3`, etc.)
- Em DEMO: salvar com dados de exemplo (`demo1234`, URLs demo)

---

## Group 7 — UX da tela de deploy

**Tela:** `_page_deploy`  
**Objetivo:** tornar a espera menos ansiosa e o erro mais acionável

### 7a — Tempo estimado por etapa
Mostrar quanto tempo cada passo costuma levar abaixo do ícone do passo:

| Passo | Estimativa |
|-------|-----------|
| Servidor principal | ~3 min |
| Bot do Telegram | ~2 min |
| Painel web | ~1 min |

Implementar como `tk.Label` adicional na card de cada step, com texto inicial "~X min" e que some quando o step termina.

### 7b — Link do arquivo de log no estado de erro
Quando `_set_step(i, "error")` for chamado, além de abrir o log, mostrar:
```
"Arquivo completo: C:\Users\...\AppData\Roaming\FinanceBot\wizard.log"
```
como label clicável que abre o arquivo no Bloco de Notas.

### 7c — Mensagem de erro mais específica para Fly.io
Atualmente: `"Erro — veja os detalhes técnicos"`  
Melhorar para detectar padrões comuns no `out`:
- `"You've exceeded your free machines limit"` → "Limite de máquinas gratuitas atingido. Apague apps antigos em fly.io/dashboard."
- `"region not available"` → "Região indisponível. Tente novamente em alguns minutos."
- Genérico: manter atual

---

## Group 8 — Melhorias na tela de revisão

**Tela:** `_page_review`  
**Objetivo:** permitir edição inline sem voltar tela a tela

### O que fazer
1. Cada item da revisão ter um botão "Editar" que navega diretamente para a tela correspondente
2. Ao voltar da tela editada, retornar para a revisão (não para o próximo passo)

### Implementação técnica
- Adicionar parâmetro `return_to_review=False` em cada `_page_*`
- Quando `True`, o footer "Continuar →" navega para `_page_review` em vez do próximo passo
- Cada linha da revisão tem `tk.Button("Editar", command=lambda: self._show(lambda: _page_xxx(return_to_review=True)))`

---

## Passo final — Publicar nova build

Depois que todos os groups estiverem prontos:

```powershell
# 1. Buildar localmente (não rodar pelo Claude — trava)
tools\build.bat

# 2. Aguardar conclusão
$b = (Get-Item "dist\FinanceBotSetup.exe").LastWriteTime
while ((Get-Item "dist\FinanceBotSetup.exe").LastWriteTime -eq $b) { Start-Sleep 5 }

# 3. Mover tag v1.0.0 para HEAD e acionar CI
git tag -d v1.0.0
git push origin :refs/tags/v1.0.0
git tag v1.0.0
git push origin master --tags
# CI dispara automaticamente → assina + faz upload para GitHub Release v1.0.0
```

> Nota: o CI faz sign com `CN=Arthur Oliveira` (autoassinado) + upload para `arthur-oli/finance-bot` release `v1.0.0`.
> UAC mostra barra amarela — comportamento esperado.
