"""Finance Bot — Setup Wizard (compile with build_wizard.bat)"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import subprocess
import threading
import secrets
import sys
import os
import re

# ── Project root ──────────────────────────────────────────────────────────────
if getattr(sys, "frozen", False):
    ROOT = os.path.dirname(sys.executable)
else:
    ROOT = os.path.dirname(os.path.abspath(__file__))

BACKEND_DIR   = os.path.join(ROOT, "backend")
DASHBOARD_DIR = os.path.join(ROOT, "dashboard")
BOT_TOML      = os.path.join(ROOT, "fly.toml")
BACKEND_TOML  = os.path.join(BACKEND_DIR, "fly.toml")

# ── Theme ─────────────────────────────────────────────────────────────────────
BG      = "#0f172a"
PANEL   = "#1e293b"
BLUE    = "#3b82f6"
GREEN   = "#4ade80"
RED     = "#f87171"
YELLOW  = "#fbbf24"
TEXT    = "#e2e8f0"
SUBTEXT = "#94a3b8"
FONT    = "Calibri"

NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


# ── PATH refresh after installs ───────────────────────────────────────────────
def _refresh_path():
    """Re-read PATH from Windows registry so newly installed tools are found."""
    if sys.platform != "win32":
        return
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment") as k:
            sys_path = winreg.QueryValueEx(k, "Path")[0]
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as k:
                usr_path = winreg.QueryValueEx(k, "Path")[0]
        except FileNotFoundError:
            usr_path = ""
        os.environ["PATH"] = sys_path + ";" + usr_path
    except Exception:
        pass


# ── Low-level helpers ─────────────────────────────────────────────────────────
def _check(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=20, creationflags=NO_WINDOW)
        return r.returncode == 0
    except Exception:
        return False


def _popen(args, cwd=None):
    return subprocess.Popen(
        args, cwd=cwd,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace", creationflags=NO_WINDOW,
    )


def _update_toml(path, app_name, replacements=None):
    with open(path, encoding="utf-8") as f:
        content = f.read()
    content = re.sub(r'^app\s*=.*', f'app = "{app_name}"', content, flags=re.M)
    for pattern, repl in (replacements or []):
        content = re.sub(pattern, repl, content, flags=re.M)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


# ── Wizard ────────────────────────────────────────────────────────────────────
class Wizard(tk.Tk):
    W, H = 760, 580

    def __init__(self):
        super().__init__()
        self.withdraw()  # hide until centered
        self.title("Finance Bot — Setup")
        self.geometry(f"{self.W}x{self.H}")
        self.resizable(False, False)
        self.configure(bg=BG)
        self._frame = None
        self._vars  = {}
        self._urls  = {}
        self._show(self._page_welcome)
        self._center()
        self.deiconify()  # show centered

    def _center(self):
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - self.W) // 2
        y = (self.winfo_screenheight() - self.H) // 2
        self.geometry(f"{self.W}x{self.H}+{x}+{y}")

    def _show(self, fn):
        if self._frame:
            self._frame.destroy()
        self._frame = fn()
        self._frame.pack(fill="both", expand=True)

    # ── Shared widgets ────────────────────────────────────────────────────────
    def _header(self, parent, title, sub=""):
        f = tk.Frame(parent, bg=BG)
        tk.Label(f, text="💰  Finance Bot", bg=BG, fg=BLUE, font=(FONT, 10)).pack(anchor="w")
        tk.Label(f, text=title, bg=BG, fg=TEXT, font=(FONT, 17, "bold")).pack(anchor="w", pady=(2, 0))
        if sub:
            tk.Label(f, text=sub, bg=BG, fg=SUBTEXT, font=(FONT, 10)).pack(anchor="w")
        ttk.Separator(f).pack(fill="x", pady=10)
        f.pack(fill="x", padx=28, pady=(20, 0))

    def _btn(self, parent, label, cmd, primary=False, small=False, **kw):
        bg = BLUE if primary else PANEL
        fg = "white" if primary else TEXT
        px, py = (10, 4) if small else (18, 7)
        fs = 9 if small else 10
        return tk.Button(parent, text=label, command=cmd,
                         bg=bg, fg=fg, activebackground=bg, activeforeground=fg,
                         relief="flat", font=(FONT, fs, "bold" if primary else "normal"),
                         padx=px, pady=py, cursor="hand2", **kw)

    def _footer(self, parent, right_btns, left_btns=None):
        f = tk.Frame(parent, bg=BG)
        f.pack(fill="x", padx=28, pady=14, side="bottom")
        for b in reversed(right_btns):
            b(f).pack(side="right", padx=4)
        for b in (left_btns or []):
            b(f).pack(side="left", padx=4)

    # ══════════════════════════════════════════════════════════════════════════
    # Page 1 — Welcome
    # ══════════════════════════════════════════════════════════════════════════
    def _page_welcome(self):
        p = tk.Frame(self, bg=BG)

        body = tk.Frame(p, bg=BG)
        body.pack(fill="both", expand=True)

        # Icon: white circle with $ drawn on canvas
        c = tk.Canvas(body, width=96, height=96, bg=BG, highlightthickness=0)
        c.pack(pady=(52, 16))
        c.create_oval(4, 4, 92, 92, fill="white", outline="")
        c.create_text(48, 48, text="$", font=(FONT, 42, "bold"), fill=BG)

        tk.Label(body, text="Finance Bot", bg=BG, fg=TEXT,
                 font=(FONT, 30, "bold")).pack()
        tk.Label(body, text="Setup Wizard", bg=BG, fg=BLUE,
                 font=(FONT, 13)).pack(pady=(2, 16))
        tk.Label(body,
                 text="Bot financeiro no Telegram com IA para registrar\n"
                      "gastos por texto ou foto, e dashboard web para acompanhar tudo.",
                 bg=BG, fg=SUBTEXT, font=(FONT, 11), justify="center").pack()

        self._footer(p, [
            lambda f: self._btn(f, "Iniciar →",
                                lambda: self._show(self._page_accounts), primary=True),
        ])
        return p

    # ══════════════════════════════════════════════════════════════════════════
    # Page 1b — Create accounts
    # ══════════════════════════════════════════════════════════════════════════
    def _page_accounts(self):
        import webbrowser

        INSTRUCTIONS = {
            "Supabase": (
                "Como criar sua conta no Supabase",
                "1. Acesse supabase.com e clique em 'Start your project'\n"
                "2. Crie uma conta (GitHub recomendado)\n"
                "3. Crie um novo projeto — escolha a região São Paulo\n"
                "4. Aguarde o projeto iniciar (~1 min)\n"
                "5. Vá em Settings → API\n"
                "6. Anote o Project URL e o service_role key\n"
                "   (você vai precisar deles mais pra frente)\n\n"
                "7. Vá em SQL Editor e cole o conteúdo do arquivo\n"
                "   schema.sql (está na raiz do projeto) e execute.\n"
                "   Isso cria as tabelas do banco de dados.",
            ),
            "Fly.io": (
                "Como criar sua conta no Fly.io",
                "1. Acesse fly.io e clique em 'Sign Up'\n"
                "2. Crie uma conta com GitHub ou e-mail\n\n"
                "⚠️  CARTÃO DE CRÉDITO OBRIGATÓRIO\n"
                "   O Fly.io exige um cartão para validar a conta,\n"
                "   mas NÃO cobra enquanto você ficar dentro do\n"
                "   plano gratuito (até 3 máquinas pequenas).\n"
                "   Este projeto usa 2 máquinas — dentro do limite.\n\n"
                "3. Após criar a conta, o wizard fará o login\n"
                "   automaticamente na próxima etapa.",
            ),
            "Vercel": (
                "Como criar sua conta no Vercel",
                "1. Acesse vercel.com e clique em 'Sign Up'\n"
                "2. Crie uma conta com GitHub (recomendado)\n"
                "3. Escolha o plano Hobby (gratuito)\n\n"
                "O Vercel hospeda o dashboard web do Finance Bot.\n"
                "O plano gratuito cobre totalmente este projeto.\n\n"
                "4. Após criar a conta, o wizard fará o login\n"
                "   automaticamente na próxima etapa.",
            ),
            "Groq": (
                "Como criar sua conta no Groq",
                "1. Acesse console.groq.com\n"
                "2. Crie uma conta (GitHub recomendado)\n"
                "3. Vá em API Keys no menu lateral\n"
                "4. Clique em 'Create API Key'\n"
                "5. Dê um nome e copie a chave gerada\n"
                "   (começa com 'gsk_...')\n\n"
                "O Groq fornece a IA que interpreta as mensagens\n"
                "e fotos de comprovantes enviadas ao bot.\n"
                "O plano gratuito tem limite de uso, mas é mais\n"
                "do que suficiente para uso pessoal.",
            ),
            "Telegram": (
                "Como criar o bot no Telegram",
                "1. Abra o Telegram e busque por @BotFather\n"
                "2. Envie o comando /newbot\n"
                "3. Escolha um nome para o bot (ex: Meu Finance Bot)\n"
                "4. Escolha um username (ex: meufinance_bot)\n"
                "5. O BotFather vai te enviar um token\n"
                "   (ex: 123456:ABC-DEF...)\n"
                "   Guarde esse token — você vai precisar depois.\n\n"
                "6. Para saber seu User ID:\n"
                "   Fale com @userinfobot no Telegram.\n"
                "   Ele responde com seu ID numérico.\n"
                "   Guarde esse número também.",
            ),
        }

        def _show_instructions(name):
            title, body_text = INSTRUCTIONS[name]
            popup = tk.Toplevel(self)
            popup.title(title)
            popup.configure(bg=BG)
            popup.resizable(False, False)
            popup.grab_set()  # modal

            tk.Label(popup, text=title, bg=BG, fg=TEXT,
                     font=(FONT, 13, "bold"), pady=16, padx=24).pack(anchor="w")

            ttk.Separator(popup).pack(fill="x", padx=24)

            tk.Label(popup, text=body_text, bg=BG, fg=SUBTEXT,
                     font=(FONT, 10), justify="left",
                     padx=24, pady=16).pack(anchor="w")

            ttk.Separator(popup).pack(fill="x", padx=24)

            tk.Button(popup, text="Fechar", command=popup.destroy,
                      bg=PANEL, fg=TEXT, relief="flat", font=(FONT, 10),
                      padx=18, pady=7, cursor="hand2").pack(side="right", padx=24, pady=12)

            # Center popup over wizard
            popup.update_idletasks()
            pw, ph = popup.winfo_reqwidth(), popup.winfo_reqheight()
            px = self.winfo_x() + (self.W - pw) // 2
            py = self.winfo_y() + (self.H - ph) // 2
            popup.geometry(f"+{px}+{py}")

        p = tk.Frame(self, bg=BG)
        self._header(p, "Criar contas",
                     "Crie uma conta em cada serviço — clique em '?' para instruções")

        body = tk.Frame(p, bg=BG)
        body.pack(fill="both", expand=True, padx=28)

        providers = [
            ("Supabase",  "Banco de dados",                      "https://supabase.com",      "Gratuito"),
            ("Fly.io",    "Hospedagem do bot e API  ⚠️ pede cartão", "https://fly.io",         "Gratuito*"),
            ("Vercel",    "Hospedagem do dashboard",              "https://vercel.com",         "Gratuito"),
            ("Groq",      "Inteligência artificial",              "https://console.groq.com",   "Gratuito"),
            ("Telegram",  "Criar o bot (@BotFather)",             "https://t.me/BotFather",     "Gratuito"),
        ]

        for name, desc, url, badge in providers:
            row = tk.Frame(body, bg=PANEL, pady=8, padx=14)
            row.pack(fill="x", pady=3)

            # Left: info
            info = tk.Frame(row, bg=PANEL)
            info.pack(side="left", fill="x", expand=True)
            tk.Label(info, text=name, bg=PANEL, fg=TEXT,
                     font=(FONT, 11, "bold")).pack(anchor="w")
            tk.Label(info, text=desc, bg=PANEL, fg=SUBTEXT,
                     font=(FONT, 9)).pack(anchor="w")

            # Right: badge + buttons
            right = tk.Frame(row, bg=PANEL)
            right.pack(side="right")

            tk.Label(right, text=badge, bg=PANEL, fg=GREEN,
                     font=(FONT, 8, "bold")).pack(side="left", padx=(0, 6))

            tk.Button(right, text="?",
                      command=lambda n=name: _show_instructions(n),
                      bg="#334155", fg=SUBTEXT, activebackground="#475569",
                      relief="flat", font=(FONT, 9, "bold"),
                      padx=8, pady=4, cursor="hand2").pack(side="left", padx=2)

            tk.Button(right, text="Abrir site →",
                      command=lambda u=url: webbrowser.open(u),
                      bg=BLUE, fg="white", activebackground=BLUE,
                      relief="flat", font=(FONT, 9, "bold"),
                      padx=10, pady=4, cursor="hand2").pack(side="left", padx=2)

        self._footer(p, [
            lambda f: self._btn(f, "Já criei todas →",
                                lambda: self._show(self._page_prereqs), primary=True),
        ], left_btns=[
            lambda f: self._btn(f, "← Voltar", lambda: self._show(self._page_welcome)),
        ])
        return p

    # ══════════════════════════════════════════════════════════════════════════
    # Page 2 — Prerequisites (with auto-install)
    # ══════════════════════════════════════════════════════════════════════════
    def _page_prereqs(self):
        p = tk.Frame(self, bg=BG)
        self._header(p, "Ferramentas", "Instalando e configurando tudo automaticamente")

        body = tk.Frame(p, bg=BG)
        body.pack(fill="both", expand=True, padx=28)

        # ── Install log (hidden until needed) ────────────────────────────────
        log_frame = tk.Frame(body, bg=BG)
        log = scrolledtext.ScrolledText(log_frame, bg=PANEL, fg=TEXT, font=("Consolas", 8),
                                        relief="flat", state="disabled", height=6)
        log.pack(fill="x")
        log.tag_config("ok",  foreground=GREEN)
        log.tag_config("err", foreground=RED)

        def _log(text, tag=None):
            log.config(state="normal")
            log.insert("end", text + "\n", tag or "")
            log.see("end")
            log.config(state="disabled")

        # ── Per-item state ────────────────────────────────────────────────────
        items = []   # (icon_lbl, status_lbl, action_btn, check_fn, install_fn)
        next_btn_holder = [None]

        def _recheck_all():
            all_ok = True
            for icon, status, abtn, check_fn, _ in items:
                ok = check_fn()
                icon.config(text="✅" if ok else "❌")
                if ok:
                    status.config(text="OK", fg=GREEN)
                    abtn.config(state="disabled", text="OK")
                else:
                    all_ok = False
            if all_ok and next_btn_holder[0]:
                next_btn_holder[0].config(state="normal")

        def _make_row(label, check_fn, install_fn, action_label):
            row = tk.Frame(body, bg=PANEL, pady=8, padx=14)
            row.pack(fill="x", pady=3)

            icon = tk.Label(row, text="⏳", bg=PANEL, font=(FONT, 13), width=3)
            icon.pack(side="left")

            tk.Label(row, text=label, bg=PANEL, fg=TEXT,
                     font=(FONT, 10, "bold")).pack(side="left")

            status = tk.Label(row, text="aguardando…", bg=PANEL, fg=SUBTEXT, font=(FONT, 9))
            status.pack(side="left", padx=8)

            def _do_action(il=install_fn, ik=icon, st=status):
                ik.config(text="⏳")
                st.config(text="instalando…", fg=YELLOW)
                log_frame.pack(fill="x", pady=(8, 0))

                def run():
                    il(_log)
                    _refresh_path()
                    self.after(0, _recheck_all)

                threading.Thread(target=run, daemon=True).start()

            abtn = self._btn(row, action_label, _do_action, small=True)
            abtn.pack(side="right", padx=4)

            items.append((icon, status, abtn, check_fn, install_fn))
            return icon, status, abtn

        # ── flyctl ───────────────────────────────────────────────────────────
        def _install_fly(log_fn):
            log_fn("Instalando flyctl via winget…")
            r = subprocess.run(
                ["winget", "install", "-e", "--id", "Fly.flyctl",
                 "--accept-source-agreements", "--accept-package-agreements", "--silent"],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                creationflags=NO_WINDOW,
            )
            if r.returncode != 0:
                log_fn("winget falhou, tentando script oficial…")
                subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     "iwr https://fly.io/install.ps1 -useb | iex"],
                    creationflags=0,  # precisa de janela para o PS script
                )
            log_fn("flyctl instalado.", "ok")

        _make_row("flyctl",
                  lambda: _check(["fly", "version"]),
                  _install_fly, "Instalar")

        # ── Node.js ───────────────────────────────────────────────────────────
        def _install_node(log_fn):
            log_fn("Instalando Node.js LTS via winget…")
            r = subprocess.run(
                ["winget", "install", "-e", "--id", "OpenJS.NodeJS.LTS",
                 "--accept-source-agreements", "--accept-package-agreements", "--silent"],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                creationflags=NO_WINDOW,
            )
            out = (r.stdout or "") + (r.stderr or "")
            log_fn(out.strip()[-200:] if out.strip() else "Concluído.", "ok")

        _make_row("Node.js / npm",
                  lambda: _check(["node", "--version"]),
                  _install_node, "Instalar")

        # ── Fly.io login ──────────────────────────────────────────────────────
        def _login_fly(log_fn):
            log_fn("Abrindo janela de terminal para login no Fly.io…")
            log_fn("Complete o login e FECHE a janela preta quando terminar.")
            proc = subprocess.Popen(
                ["cmd.exe", "/k",
                 "fly auth login && echo. && echo Login concluido! Pode fechar esta janela."],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
            proc.wait()
            log_fn("Verificando login…")

        _make_row("Fly.io — login",
                  lambda: _check(["fly", "auth", "whoami"]),
                  _login_fly, "Fazer Login")

        # ── Vercel login ──────────────────────────────────────────────────────
        def _login_vercel(log_fn):
            log_fn("Abrindo janela de terminal para login no Vercel…")
            log_fn("Escolha o método (GitHub recomendado) e FECHE a janela preta quando terminar.")
            proc = subprocess.Popen(
                ["cmd.exe", "/k",
                 "npx vercel login && echo. && echo Login concluido! Pode fechar esta janela."],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
            proc.wait()
            log_fn("Verificando login…")

        _make_row("Vercel — login",
                  lambda: _check(["npx", "vercel", "whoami"]),
                  _login_vercel, "Fazer Login")

        # ── Initial check ─────────────────────────────────────────────────────
        def _initial_check():
            all_ok = True
            for icon, status, abtn, check_fn, _ in items:
                ok = check_fn()
                self.after(0, lambda i=icon, s=status, b=abtn, o=ok: (
                    i.config(text="✅" if o else "❌"),
                    s.config(text="OK" if o else "necessário", fg=GREEN if o else SUBTEXT),
                    b.config(state="disabled" if o else "normal"),
                ))
                if not ok:
                    all_ok = False
            if all_ok:
                self.after(0, lambda: next_btn_holder[0] and next_btn_holder[0].config(state="normal"))

        threading.Thread(target=_initial_check, daemon=True).start()

        self._footer(p, [
            lambda f: self._btn(f, "Continuar →",
                                lambda: self._show(self._page_config),
                                primary=True, state="disabled") if not (
                lambda b: next_btn_holder.__setitem__(0, b) or b)(None) else None,
        ], left_btns=[
            lambda f: self._btn(f, "← Voltar", lambda: self._show(self._page_accounts)),
        ])

        # find the Continuar button after footer renders
        def _grab_btn():
            for widget in p.winfo_children():
                for child in widget.winfo_children():
                    if isinstance(child, tk.Button) and "Continuar" in str(child.cget("text")):
                        next_btn_holder[0] = child
        self.after(100, _grab_btn)

        return p

    # ══════════════════════════════════════════════════════════════════════════
    # Page 3 — Configuration form
    # ══════════════════════════════════════════════════════════════════════════
    def _page_config(self):
        p = tk.Frame(self, bg=BG)
        self._header(p, "Configuração", "Cole suas chaves — nada é salvo no disco")

        outer = tk.Frame(p, bg=BG)
        outer.pack(fill="both", expand=True, padx=28)
        canvas = tk.Canvas(outer, bg=BG, highlightthickness=0)
        sb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        body = tk.Frame(canvas, bg=BG)
        body.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=body, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        sections = [
            ("Supabase  (Settings → API)", [
                ("SUPABASE_URL",             "Project URL",       False, "https://xxxx.supabase.co"),
                ("SUPABASE_SERVICE_ROLE_KEY", "Service Role Key", True,  "eyJ…"),
            ]),
            ("Telegram", [
                ("TELEGRAM_BOT_TOKEN", "Bot Token",   True,  "123456:ABC…"),
                ("TELEGRAM_USER_IDS",  "User ID(s)",  False, "Separe com vírgula para múltiplos usuários"),
            ]),
            ("Groq  (console.groq.com)", [
                ("GROQ_API_KEY", "API Key", True, "gsk_…"),
            ]),
            ("Fly.io — escolha os nomes dos apps", [
                ("BACKEND_APP", "Nome do backend", False, "meubot-backend"),
                ("BOT_APP",     "Nome do bot",     False, "meubot-worker"),
            ]),
            ("Dashboard — senha de acesso ao painel web", [
                ("DASHBOARD_PASSWORD",  "Senha",           True, ""),
                ("DASHBOARD_PASSWORD2", "Confirmar senha", True, ""),
            ]),
        ]

        PH_COLOR = "#475569"

        for section, fields in sections:
            tk.Label(body, text=section, bg=BG, fg=BLUE,
                     font=(FONT, 10, "bold")).pack(anchor="w", pady=(14, 3))

            for key, label, is_secret, placeholder in fields:
                row = tk.Frame(body, bg=BG)
                row.pack(fill="x", pady=3)
                tk.Label(row, text=label, bg=BG, fg=SUBTEXT,
                         font=(FONT, 9), width=20, anchor="w").pack(side="left")

                var = tk.StringVar()
                self._vars[key] = var

                entry = tk.Entry(row, textvariable=var,
                                 show="•" if is_secret else "",
                                 bg=PANEL, fg=TEXT if not placeholder else PH_COLOR,
                                 insertbackground=TEXT, relief="flat",
                                 font=("Consolas", 10), width=40)
                entry.pack(side="left", ipady=5, padx=(4, 2))

                if placeholder and not is_secret:
                    entry.insert(0, placeholder)
                    entry.config(fg=PH_COLOR)

                    def _fi(e, en=entry, ph=placeholder):
                        if en.get() == ph:
                            en.delete(0, "end")
                            en.config(fg=TEXT)

                    def _fo(e, en=entry, ph=placeholder, v=var):
                        if not en.get().strip():
                            en.insert(0, ph)
                            en.config(fg=PH_COLOR)
                            v.set("")

                    entry.bind("<FocusIn>", _fi)
                    entry.bind("<FocusOut>", _fo)

                if is_secret:
                    ev = tk.BooleanVar(value=False)

                    def _toggle(en=entry, sv=ev):
                        sv.set(not sv.get())
                        en.config(show="" if sv.get() else "•")

                    tk.Button(row, text="👁", command=_toggle,
                              bg=PANEL, fg=SUBTEXT, relief="flat",
                              cursor="hand2", font=(FONT, 9)).pack(side="left")

        placeholders_map = {
            "SUPABASE_URL":      "https://xxxx.supabase.co",
            "TELEGRAM_USER_IDS": "Separe com vírgula para múltiplos usuários",
            "BACKEND_APP":       "meubot-backend",
            "BOT_APP":           "meubot-worker",
        }

        def _validate():
            errors = []
            for k in ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY",
                      "TELEGRAM_BOT_TOKEN", "TELEGRAM_USER_IDS",
                      "GROQ_API_KEY", "BACKEND_APP", "BOT_APP",
                      "DASHBOARD_PASSWORD", "DASHBOARD_PASSWORD2"]:
                v = self._vars[k].get().strip()
                if not v or v == placeholders_map.get(k, ""):
                    errors.append(f"• {k.replace('_', ' ').title()}")
            pw1 = self._vars["DASHBOARD_PASSWORD"].get()
            pw2 = self._vars["DASHBOARD_PASSWORD2"].get()
            if pw1 and pw2 and pw1 != pw2:
                errors.append("• Senhas do dashboard não conferem")
            if pw1 and len(pw1) < 6:
                errors.append("• Senha precisa ter ao menos 6 caracteres")
            if errors:
                messagebox.showerror("Campos obrigatórios",
                                     "Preencha os campos:\n" + "\n".join(errors))
                return False
            return True

        self._footer(p, [
            lambda f: self._btn(f, "Iniciar Deploy →",
                                lambda: _validate() and self._show(self._page_deploy),
                                primary=True),
        ], left_btns=[
            lambda f: self._btn(f, "← Voltar", lambda: self._show(self._page_prereqs)),
        ])
        return p

    # ══════════════════════════════════════════════════════════════════════════
    # Page 4 — Deploy
    # ══════════════════════════════════════════════════════════════════════════
    def _page_deploy(self):
        p = tk.Frame(self, bg=BG)
        self._header(p, "Deployando…", "Isso leva 5–10 minutos. Não feche a janela.")

        body = tk.Frame(p, bg=BG)
        body.pack(fill="both", expand=True, padx=28)

        status = tk.Label(body, text="Iniciando…", bg=BG, fg=YELLOW,
                          font=(FONT, 10, "bold"), anchor="w")
        status.pack(anchor="w", pady=(0, 6))

        log = scrolledtext.ScrolledText(body, bg=PANEL, fg=TEXT, font=("Consolas", 9),
                                        relief="flat", state="disabled", height=17)
        log.pack(fill="both", expand=True)
        log.tag_config("ok",  foreground=GREEN)
        log.tag_config("err", foreground=RED)
        log.tag_config("hdr", foreground=YELLOW)

        done_btn = self._btn(p, "✅  Concluído →",
                             lambda: self._show(lambda: self._page_done(self._urls)),
                             primary=True, state="disabled")
        done_btn.pack(side="right", padx=28, pady=12)

        def _log(text, tag=None):
            log.config(state="normal")
            log.insert("end", text + "\n", tag or "")
            log.see("end")
            log.config(state="disabled")

        def _run(args, cwd=None, stdin_val=None):
            proc = _popen(args, cwd=cwd)
            out_lines = []
            if stdin_val is not None:
                try:
                    proc.stdin.write(stdin_val)
                    proc.stdin.close()
                except Exception:
                    pass
            for line in proc.stdout:
                line = line.rstrip()
                out_lines.append(line)
                tag = "err" if re.search(r"\b(error|failed|fatal)\b", line, re.I) else None
                self.after(0, lambda l=line, t=tag: _log(l, t))
            proc.wait()
            return proc.returncode == 0, "\n".join(out_lines)

        def _fly_app_exists(name):
            r = subprocess.run(["fly", "apps", "list"], capture_output=True,
                               text=True, encoding="utf-8", errors="replace",
                               creationflags=NO_WINDOW)
            return name in r.stdout

        def _vercel_env(name, value):
            proc = _popen(["npx", "vercel", "env", "add", name, "production", "--force"],
                          cwd=DASHBOARD_DIR)
            try:
                proc.stdin.write(value)
                proc.stdin.close()
            except Exception:
                pass
            proc.stdout.read()
            proc.wait()
            self.after(0, lambda: _log(f"  env {name}: {'OK' if proc.returncode == 0 else 'ERRO'}"))

        def deploy():
            v = {k: var.get().strip() for k, var in self._vars.items()}
            api_key     = secrets.token_hex(32)
            sess_secret = secrets.token_hex(32)
            backend_app = v["BACKEND_APP"]
            bot_app     = v["BOT_APP"]
            backend_url = f"https://{backend_app}.fly.dev"

            # ── Backend ───────────────────────────────────────────────────
            self.after(0, lambda: status.config(text="[1/3]  Deploy do Backend…"))
            self.after(0, lambda: _log("\n══ BACKEND ══", "hdr"))
            _update_toml(BACKEND_TOML, backend_app)
            if not _fly_app_exists(backend_app):
                _run(["fly", "apps", "create", backend_app])
            ok, _ = _run([
                "fly", "secrets", "set",
                f"SUPABASE_URL={v['SUPABASE_URL']}",
                f"SUPABASE_SERVICE_ROLE_KEY={v['SUPABASE_SERVICE_ROLE_KEY']}",
                f"API_SECRET_KEY={api_key}",
                "--app", backend_app,
            ], cwd=BACKEND_DIR)
            if not ok:
                self.after(0, lambda: status.config(text="❌  Erro nos secrets do backend", fg=RED))
                return
            ok, _ = _run(["fly", "deploy", "--app", backend_app, "--wait-timeout", "180"],
                         cwd=BACKEND_DIR)
            if not ok:
                self.after(0, lambda: status.config(text="❌  Erro no deploy do backend", fg=RED))
                return

            # ── Bot ────────────────────────────────────────────────────────
            self.after(0, lambda: status.config(text="[2/3]  Deploy do Bot…"))
            self.after(0, lambda: _log("\n══ BOT ══", "hdr"))
            _update_toml(BOT_TOML, bot_app, [
                (r'BACKEND_URL\s*=.*', f'BACKEND_URL = "{backend_url}"'),
            ])
            if not _fly_app_exists(bot_app):
                _run(["fly", "apps", "create", bot_app])
            ok, _ = _run([
                "fly", "secrets", "set",
                f"TELEGRAM_BOT_TOKEN={v['TELEGRAM_BOT_TOKEN']}",
                f"TELEGRAM_USER_IDS={v['TELEGRAM_USER_IDS']}",
                f"BACKEND_URL={backend_url}",
                f"API_SECRET_KEY={api_key}",
                f"GROQ_API_KEY={v['GROQ_API_KEY']}",
                "--app", bot_app,
            ], cwd=ROOT)
            if not ok:
                self.after(0, lambda: status.config(text="❌  Erro nos secrets do bot", fg=RED))
                return
            ok, _ = _run(["fly", "deploy", "--app", bot_app, "--wait-timeout", "180"], cwd=ROOT)
            if not ok:
                self.after(0, lambda: status.config(text="❌  Erro no deploy do bot", fg=RED))
                return

            # ── Dashboard ─────────────────────────────────────────────────
            self.after(0, lambda: status.config(text="[3/3]  Deploy do Dashboard…"))
            self.after(0, lambda: _log("\n══ DASHBOARD ══", "hdr"))

            vercel_json = os.path.join(DASHBOARD_DIR, "vercel.json")
            with open(vercel_json, "w") as f:
                f.write("{}\n")

            for name, val in [
                ("BACKEND_URL",        backend_url),
                ("API_SECRET_KEY",     api_key),
                ("DASHBOARD_PASSWORD", v["DASHBOARD_PASSWORD"]),
                ("SESSION_SECRET",     sess_secret),
            ]:
                _vercel_env(name, val)

            ok, out = _run(["npx", "vercel", "--prod", "--yes"], cwd=DASHBOARD_DIR)
            match = re.search(r"https://[^\s]+\.vercel\.app", out)
            dashboard_url = match.group(0) if match else "(veja vercel.com)"

            self._urls = {"backend": backend_url, "dashboard": dashboard_url}
            self.after(0, lambda: (
                status.config(text="✅  Tudo deployado!", fg=GREEN),
                _log("\n✅  Deploy concluído!", "ok"),
                done_btn.config(state="normal"),
            ))

        threading.Thread(target=deploy, daemon=True).start()
        return p

    # ══════════════════════════════════════════════════════════════════════════
    # Page 5 — Done
    # ══════════════════════════════════════════════════════════════════════════
    def _page_done(self, urls):
        p = tk.Frame(self, bg=BG)
        self._header(p, "Tudo pronto! 🎉", "Seu bot está rodando em cloud")

        body = tk.Frame(p, bg=BG)
        body.pack(fill="both", expand=True, padx=28, pady=8)

        for label, url in [
            ("🔧  Backend API",   urls.get("backend", "")),
            ("🌐  Dashboard Web", urls.get("dashboard", "")),
        ]:
            card = tk.Frame(body, bg=PANEL, pady=12, padx=18)
            card.pack(fill="x", pady=5)
            tk.Label(card, text=label, bg=PANEL, fg=SUBTEXT, font=(FONT, 9)).pack(anchor="w")
            tk.Label(card, text=url, bg=PANEL, fg=GREEN, font=("Consolas", 11)).pack(anchor="w", pady=(2, 0))

        tk.Label(body,
                 text="\nPróximos passos:\n"
                      "  1. Abra o Telegram e mande uma mensagem pro bot: gastei 50 no mercado\n"
                      "  2. Acesse o dashboard com a senha que você definiu\n"
                      "  3. Cadastre seus cartões no dashboard antes de usar",
                 bg=BG, fg=SUBTEXT, font=(FONT, 10), justify="left").pack(anchor="w", pady=14)

        self._footer(p, [
            lambda f: self._btn(f, "Fechar", self.destroy, primary=True),
        ])
        return p


if __name__ == "__main__":
    app = Wizard()
    app.mainloop()
