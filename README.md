# Finance Bot

<p align="center">
  <img src="assets/finance-bot-logo.png" width="120" alt="Finance Bot">
</p>

<p align="center">
  Bot pessoal de finanças no Telegram com dashboard web.<br>
  Registre gastos por mensagem ou foto de nota fiscal — a IA classifica automaticamente.<br>
  Roda 100% em cloud gratuita, sem precisar deixar o PC ligado.
</p>

---

## Como funciona

Mande uma mensagem para o bot no Telegram:

> `gastei 50 no mercado`  
> `paguei 120 de farmácia`

Ou tire uma foto de uma nota fiscal — o bot lê os itens e registra tudo automaticamente.

Acesse o dashboard pelo navegador para ver gráficos, histórico e exportar suas transações em CSV.

## Instalação

Baixe o `FinanceBotSetup.exe` na página de [Releases](https://github.com/arthur-oli/finance-bot/releases) e siga o assistente. Ele cria todas as contas necessárias, configura e publica tudo automaticamente — sem precisar saber programar.

**Tempo estimado: ~15 minutos.**

Para atualizar uma instalação existente, use o `FinanceBotUpdate.exe` da mesma página.

## Funcionalidades

- Registro por texto ou foto de nota fiscal
- Classificação automática por categoria via IA
- Dashboard com gráficos por categoria e evolução mensal
- Histórico completo de transações
- Suporte a múltiplos usuários
- Exportação em CSV

## Stack

| Componente | Onde roda | Custo |
|---|---|---|
| Bot Telegram + Backend API | [Fly.io](https://fly.io) | Gratuito |
| Dashboard web | [Vercel](https://vercel.com) | Gratuito |
| Banco de dados | [Supabase](https://supabase.com) | Gratuito |
| IA (texto + OCR) | [Groq](https://console.groq.com) | Gratuito |
