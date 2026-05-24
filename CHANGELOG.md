# Changelog

## v1.0.0 — Lançamento inicial

> **Versão inicial de uso pessoal.** O bot está funcional no dia a dia, mas ainda em desenvolvimento ativo — podem existir bugs e comportamentos inesperados. Feedbacks, sugestões de features e reporte de bugs são bem-vindos.

### Funcionalidades

- **Registro por texto** — mande mensagens como "gastei 50 no mercado" e o bot classifica automaticamente
- **Registro por foto** — fotografe notas fiscais e a IA extrai os itens e valores via OCR
- **Classificação automática** — categorias detectadas por IA (alimentação, transporte, saúde, lazer e mais)
- **Dashboard web** — gráficos de gastos por categoria, evolução mensal e histórico completo
- **Cartões** — cadastre cartões de crédito e débito; defina padrão por tipo para o bot usar automaticamente
- **Múltiplos usuários** — suporte a mais de um usuário no mesmo bot
- **Exportação CSV** — baixe todas as transações direto pelo painel
- **Wizard de instalação** — configura e publica tudo automaticamente em ~15 minutos, sem precisar saber programar *(Windows only)*
- **Atualizador** — `FinanceBotUpdate.exe` atualiza o bot para a versão mais recente com um clique *(Windows only)*

### Stack

Roda 100% em cloud gratuita: Fly.io (backend + bot), Vercel (dashboard), Supabase (banco), Groq (IA).
