# Finance Bot

<p align="center">
  <img src="assets/finance-bot-logo.png" width="120" alt="Finance Bot">
</p>

Bot pessoal de finanças no Telegram com dashboard web. Registre gastos por mensagem ou foto de nota fiscal — a IA classifica automaticamente.

Roda 100% em cloud, sem precisar deixar o PC ligado.

## Stack

| Componente | Onde roda | Custo |
|---|---|---|
| Bot Telegram + Backend API | [Fly.io](https://fly.io) | Gratuito |
| Dashboard web | [Vercel](https://vercel.com) | Gratuito |
| Banco de dados | [Supabase](https://supabase.com) | Gratuito |
| IA (texto + OCR) | [Groq](https://console.groq.com) | Gratuito |

## Instalação

Baixe o wizard na página de [Releases](https://github.com/arthur-oli/finance-bot/releases) e siga as instruções. O assistente cria todas as contas, configura e publica tudo automaticamente (~15 min).

Para atualizar uma instalação existente, use o `FinanceBotUpdate.exe` da mesma página.

## Funcionalidades

- Registro de gastos por texto (`gastei 50 no mercado`) ou foto de nota fiscal
- Classificação automática por categoria via IA
- Dashboard com gráficos, metas e histórico
- Suporte a múltiplos usuários e cartões
- Exportação de transações em CSV
