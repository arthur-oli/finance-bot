"""Finance Bot — Setup Wizard"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import subprocess
import threading
import secrets
import webbrowser
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

# ── Palette ───────────────────────────────────────────────────────────────────
BG      = "#0f172a"
PANEL   = "#1e293b"
PANEL2  = "#263348"
BLUE    = "#3b82f6"
BLUE2   = "#2563eb"
GREEN   = "#22c55e"
RED     = "#ef4444"
YELLOW  = "#f59e0b"
TEXT    = "#f1f5f9"
MUTED   = "#cbd5e1"
DIM     = "#64748b"
FONT    = "Calibri"

NO_WIN = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


# ── Helpers ───────────────────────────────────────────────────────────────────
def _refresh_path():
    if sys.platform != "win32":
        return
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment") as k:
            sp = winreg.QueryValueEx(k, "Path")[0]
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as k:
                up = winreg.QueryValueEx(k, "Path")[0]
        except FileNotFoundError:
            up = ""
        os.environ["PATH"] = sp + ";" + up
    except Exception:
        pass


def _check(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=20, creationflags=NO_WIN)
        return r.returncode == 0
    except Exception:
        return False


def _popen(args, cwd=None):
    return subprocess.Popen(
        args, cwd=cwd,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace", creationflags=NO_WIN,
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
    W, H   = 780, 600
    STEPS  = ["Contas", "Ferramentas", "Chaves", "Publicando", "Pronto"]

    def __init__(self):
        super().__init__()
        self.withdraw()
        self.title("Finance Bot — Setup")
        self.geometry(f"{self.W}x{self.H}")
        self.resizable(False, False)
        self.configure(bg=BG)
        self._frame = None
        self._vars  = {}
        self._urls  = {}
        self._show(self._page_welcome)
        self._center()
        self.deiconify()

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

    # ── Step progress bar ─────────────────────────────────────────────────────
    def _step_bar(self, parent, current_step):
        wrap = tk.Frame(parent, bg=BG)
        wrap.pack(fill="x", padx=32, pady=(18, 0))

        c = tk.Canvas(wrap, bg=BG, highlightthickness=0, height=46)
        c.pack(fill="x")

        def _draw(event=None):
            c.delete("all")
            w = c.winfo_width() or (self.W - 64)
            n = len(self.STEPS)
            seg = w / n

            for i, label in enumerate(self.STEPS):
                cx = int(seg * i + seg / 2)
                cy = 16

                # connector line to next
                if i < n - 1:
                    nx = int(seg * (i + 1) + seg / 2)
                    col = GREEN if i < current_step else DIM
                    c.create_line(cx + 13, cy, nx - 13, cy, fill=col, width=2)

                # circle
                if i < current_step:
                    c.create_oval(cx-12, cy-12, cx+12, cy+12, fill=GREEN, outline="")
                    c.create_text(cx, cy, text="✓", font=(FONT, 10, "bold"), fill=BG)
                elif i == current_step:
                    c.create_oval(cx-13, cy-13, cx+13, cy+13, fill=BLUE, outline="")
                    c.create_text(cx, cy, text=str(i+1), font=(FONT, 10, "bold"), fill="white")
                else:
                    c.create_oval(cx-11, cy-11, cx+11, cy+11, fill=BG, outline=DIM, width=2)
                    c.create_text(cx, cy, text=str(i+1), font=(FONT, 9), fill=DIM)

                # label below
                col = TEXT if i == current_step else (MUTED if i < current_step else DIM)
                weight = "bold" if i == current_step else "normal"
                c.create_text(cx, cy + 24, text=label, font=(FONT, 8, weight), fill=col)

        c.bind("<Configure>", _draw)
        self.after(10, _draw)

        ttk.Separator(wrap).pack(fill="x", pady=(8, 0))
        return wrap

    # ── Header (pages with step bar) ──────────────────────────────────────────
    def _header(self, parent, title, sub, step):
        self._step_bar(parent, step)
        f = tk.Frame(parent, bg=BG)
        tk.Label(f, text=title, bg=BG, fg=TEXT,
                 font=(FONT, 18, "bold")).pack(anchor="w", pady=(14, 0))
        if sub:
            tk.Label(f, text=sub, bg=BG, fg=MUTED, font=(FONT, 10)).pack(anchor="w", pady=(2, 0))
        f.pack(fill="x", padx=32, pady=(10, 0))

    # ── Buttons ───────────────────────────────────────────────────────────────
    def _primary_btn(self, parent, label, cmd, **kw):
        return tk.Button(parent, text=label, command=cmd,
                         bg=BLUE, fg="white", activebackground=BLUE2, activeforeground="white",
                         relief="flat", font=(FONT, 11, "bold"),
                         padx=28, pady=11, cursor="hand2",
                         disabledforeground=DIM, **kw)

    def _secondary_btn(self, parent, label, cmd, **kw):
        return tk.Button(parent, text=label, command=cmd,
                         bg=PANEL, fg=MUTED, activebackground=PANEL2, activeforeground=TEXT,
                         relief="flat", font=(FONT, 10),
                         padx=18, pady=9, cursor="hand2", **kw)

    def _small_btn(self, parent, label, cmd, color=PANEL, fg=MUTED, **kw):
        return tk.Button(parent, text=label, command=cmd,
                         bg=color, fg=fg, activebackground=PANEL2, activeforeground=TEXT,
                         relief="flat", font=(FONT, 9, "bold"),
                         padx=10, pady=5, cursor="hand2", **kw)

    # ── Footer ────────────────────────────────────────────────────────────────
    def _footer(self, parent, right_btns, left_btns=None):
        sep = ttk.Separator(parent)
        sep.pack(fill="x", padx=0, side="bottom")
        f = tk.Frame(parent, bg=BG)
        f.pack(fill="x", padx=32, pady=14, side="bottom")
        for b in reversed(right_btns):
            b(f).pack(side="right", padx=4)
        for b in (left_btns or []):
            b(f).pack(side="left", padx=4)

    # ── Popup ─────────────────────────────────────────────────────────────────
    def _popup(self, title, body_text, width=440):
        pop = tk.Toplevel(self)
        pop.title(title)
        pop.configure(bg=BG)
        pop.resizable(False, False)
        pop.grab_set()
        pop.transient(self)

        tk.Label(pop, text=title, bg=BG, fg=TEXT,
                 font=(FONT, 13, "bold"), padx=28, pady=16).pack(anchor="w")
        ttk.Separator(pop).pack(fill="x")
        tk.Label(pop, text=body_text, bg=BG, fg=MUTED,
                 font=(FONT, 10), justify="left", padx=28, pady=18,
                 wraplength=width - 56).pack(anchor="w")
        ttk.Separator(pop).pack(fill="x")
        tk.Button(pop, text="Entendido", command=pop.destroy,
                  bg=BLUE, fg="white", relief="flat", font=(FONT, 10, "bold"),
                  padx=20, pady=8, cursor="hand2").pack(side="right", padx=28, pady=14)

        pop.update_idletasks()
        pw = pop.winfo_reqwidth()
        ph = pop.winfo_reqheight()
        pop.geometry(f"{pw}x{ph}+{self.winfo_x() + (self.W - pw)//2}+{self.winfo_y() + (self.H - ph)//2}")

    # ══════════════════════════════════════════════════════════════════════════
    # Página 1 — Boas-vindas
    # ══════════════════════════════════════════════════════════════════════════
    def _page_welcome(self):
        p = tk.Frame(self, bg=BG)

        body = tk.Frame(p, bg=BG)
        body.pack(fill="both", expand=True)

        # Icon
        c = tk.Canvas(body, width=100, height=100, bg=BG, highlightthickness=0)
        c.pack(pady=(52, 14))
        c.create_oval(4, 4, 96, 96, fill="white", outline="")
        c.create_text(50, 50, text="$", font=(FONT, 46, "bold"), fill=BG)

        tk.Label(body, text="Finance Bot", bg=BG, fg=TEXT,
                 font=(FONT, 32, "bold")).pack()
        tk.Label(body, text="Assistente de setup", bg=BG, fg=BLUE,
                 font=(FONT, 13)).pack(pady=(2, 18))
        tk.Label(body,
                 text="Este assistente vai configurar e publicar o seu bot financeiro.\n"
                      "O processo leva cerca de 15 minutos e não exige conhecimento técnico.",
                 bg=BG, fg=MUTED, font=(FONT, 11), justify="center").pack()

        self._footer(p, [
            lambda f: self._primary_btn(f, "Começar  →",
                                        lambda: self._show(self._page_accounts)),
        ])
        return p

    # ══════════════════════════════════════════════════════════════════════════
    # Página 2 — Criar contas
    # ══════════════════════════════════════════════════════════════════════════
    def _page_accounts(self):
        INSTRUCTIONS = {
            "Supabase": (
                "Criando sua conta no Supabase",
                "O Supabase é onde todas as suas transações ficam guardadas.\n\n"
                "Passo a passo:\n"
                "1. Clique em 'Abrir site' e depois em 'Start your project'\n"
                "2. Crie uma conta — pode usar o GitHub\n"
                "3. Crie um novo projeto, escolha a região São Paulo\n"
                "4. Aguarde o projeto iniciar (leva ~1 minuto)\n"
                "5. Vá em Settings → API e anote dois valores:\n"
                "   • Project URL  (começa com https://)\n"
                "   • service_role key  (chave longa, começa com eyJ...)\n"
                "   Você vai colar esses valores na próxima etapa.\n\n"
                "6. Ainda no Supabase, vá em SQL Editor,\n"
                "   cole o conteúdo do arquivo  schema.sql  (está na pasta\n"
                "   do projeto) e clique em Run para criar as tabelas.",
            ),
            "Fly.io": (
                "Criando sua conta no Fly.io",
                "O Fly.io é onde o bot do Telegram e a API ficam rodando,\n"
                "24 horas por dia, sem precisar deixar o computador ligado.\n\n"
                "Passo a passo:\n"
                "1. Clique em 'Abrir site' e crie uma conta\n"
                "2. O Fly.io vai pedir um cartão de crédito para validar\n\n"
                "⚠️  IMPORTANTE SOBRE O CARTÃO:\n"
                "   O Fly.io exige o cartão para confirmar que você é\n"
                "   uma pessoa real, mas NÃO faz nenhuma cobrança\n"
                "   enquanto você usar o plano gratuito.\n"
                "   Este projeto usa 2 servidores pequenos — dentro do\n"
                "   limite gratuito de 3 servidores.\n\n"
                "Depois de criar a conta, o assistente fará o\n"
                "login automaticamente na próxima etapa.",
            ),
            "Vercel": (
                "Criando sua conta no Vercel",
                "O Vercel hospeda o painel web onde você acompanha\n"
                "seus gastos pelo navegador.\n\n"
                "Passo a passo:\n"
                "1. Clique em 'Abrir site' e crie uma conta\n"
                "2. Recomendamos entrar com o GitHub, é mais fácil\n"
                "3. Escolha o plano Hobby (gratuito)\n\n"
                "O plano gratuito do Vercel cobre este projeto\n"
                "sem nenhum custo.\n\n"
                "Depois de criar a conta, o assistente fará o\n"
                "login automaticamente na próxima etapa.",
            ),
            "Groq": (
                "Criando sua conta no Groq",
                "O Groq fornece a inteligência artificial que entende\n"
                "suas mensagens e lê fotos de comprovantes.\n\n"
                "Passo a passo:\n"
                "1. Clique em 'Abrir site' e crie uma conta\n"
                "2. No menu lateral, clique em 'API Keys'\n"
                "3. Clique em 'Create API Key' e dê um nome qualquer\n"
                "4. Copie a chave gerada — ela começa com  gsk_\n"
                "   Você vai colar essa chave na próxima etapa.\n\n"
                "O plano gratuito tem limite de uso por dia,\n"
                "mas é mais que suficiente para uso pessoal.",
            ),
            "Telegram": (
                "Criando o bot no Telegram",
                "O BotFather é o bot oficial do Telegram para criar bots.\n\n"
                "Passo a passo:\n"
                "1. Abra o Telegram e busque por  @BotFather\n"
                "2. Clique em START e depois envie  /newbot\n"
                "3. Escolha um nome para exibição (ex: Meu Finance)\n"
                "4. Escolha um username — deve terminar em 'bot'\n"
                "   (ex: meu_finance_bot)\n"
                "5. O BotFather vai te enviar um token, como:\n"
                "   7123456789:AAGbeu_xXxXxXxXxXxXxXxX\n"
                "   Copie e guarde esse token.\n\n"
                "Para descobrir seu ID de usuário:\n"
                "   Busque por  @userinfobot  no Telegram e clique START.\n"
                "   Ele vai te mostrar seu ID numérico (ex: 123456789).\n"
                "   Guarde esse número também.",
            ),
        }

        p = tk.Frame(self, bg=BG)
        self._header(p, "Criar contas",
                     "Você precisa de uma conta gratuita em cada serviço abaixo.", step=0)

        body = tk.Frame(p, bg=BG)
        body.pack(fill="both", expand=True, padx=32, pady=(14, 0))

        checks = {}
        providers = [
            ("Supabase",  "Guarda suas transações e dados",    "https://supabase.com",      GREEN,  "Gratuito"),
            ("Fly.io",    "Roda o bot 24h (pede cartão)",      "https://fly.io",             YELLOW, "Gratuito*"),
            ("Vercel",    "Hospeda o painel web",               "https://vercel.com",         GREEN,  "Gratuito"),
            ("Groq",      "Inteligência artificial do bot",     "https://console.groq.com",   GREEN,  "Gratuito"),
            ("Telegram",  "Cria o bot no Telegram",             "https://t.me/BotFather",     GREEN,  "Gratuito"),
        ]

        def _update_btn():
            done = sum(v.get() for v in checks.values())
            if done == len(providers):
                next_btn.config(state="normal", bg=BLUE)
            else:
                next_btn.config(state="normal", bg=PANEL2,
                                text=f"Continuar  ({done}/{len(providers)} contas)  →")
                next_btn.config(fg=MUTED if done < len(providers) else "white")

        for name, desc, url, badge_color, badge in providers:
            row = tk.Frame(body, bg=PANEL, pady=10, padx=16)
            row.pack(fill="x", pady=3)

            # Checkbox
            var = tk.BooleanVar()
            checks[name] = var
            cb = tk.Checkbutton(row, variable=var, command=_update_btn,
                                bg=PANEL, activebackground=PANEL,
                                selectcolor=PANEL, fg=GREEN,
                                relief="flat", cursor="hand2")
            cb.pack(side="left", padx=(0, 6))

            # Info
            info = tk.Frame(row, bg=PANEL)
            info.pack(side="left", fill="x", expand=True)
            tk.Label(info, text=name, bg=PANEL, fg=TEXT,
                     font=(FONT, 11, "bold")).pack(anchor="w")
            tk.Label(info, text=desc, bg=PANEL, fg=MUTED,
                     font=(FONT, 9)).pack(anchor="w")

            # Buttons
            right = tk.Frame(row, bg=PANEL)
            right.pack(side="right")

            tk.Label(right, text=badge, bg=PANEL, fg=badge_color,
                     font=(FONT, 8, "bold")).pack(side="left", padx=(0, 8))

            self._small_btn(right, "Como criar",
                            lambda n=name: self._popup(*INSTRUCTIONS[n]),
                            color=PANEL2, fg=MUTED).pack(side="left", padx=2)

            self._small_btn(right, "Abrir site  →",
                            lambda u=url: webbrowser.open(u),
                            color=BLUE, fg="white").pack(side="left", padx=(4, 0))

        tk.Label(body,
                 text="Marque a caixa de cada serviço conforme for criando a conta.",
                 bg=BG, fg=DIM, font=(FONT, 9)).pack(anchor="w", pady=(10, 0))

        next_btn = self._primary_btn(None, "Continuar  (0/5 contas)  →",
                                     lambda: self._show(self._page_prereqs),
                                     bg=PANEL2, fg=MUTED)
        next_btn.config(state="normal")  # always allow — user may have accounts already

        self._footer(p, [
            lambda f: next_btn if not next_btn.pack_info() else next_btn,
        ], left_btns=[
            lambda f: self._secondary_btn(f, "← Voltar",
                                          lambda: self._show(self._page_welcome)),
        ])
        # Pack next_btn into footer properly
        for w in p.winfo_children():
            pass
        # Simpler approach: rebuild footer with the actual button
        for widget in p.winfo_children():
            widget.destroy()

        self._header(p, "Criar contas",
                     "Você precisa de uma conta gratuita em cada serviço abaixo.", step=0)
        body2 = tk.Frame(p, bg=BG)
        body2.pack(fill="both", expand=True, padx=32, pady=(14, 0))

        checks2 = {}
        next_btn_ref = [None]

        def _update_btn2():
            done = sum(v.get() for v in checks2.values())
            nb = next_btn_ref[0]
            if nb is None:
                return
            if done == len(providers):
                nb.config(bg=BLUE, fg="white", text="Continuar  →")
            else:
                nb.config(bg=PANEL2, fg=MUTED,
                          text=f"Continuar  ({done}/{len(providers)} contas)  →")

        for name, desc, url, badge_color, badge in providers:
            row = tk.Frame(body2, bg=PANEL, pady=10, padx=16)
            row.pack(fill="x", pady=3)

            var = tk.BooleanVar()
            checks2[name] = var
            tk.Checkbutton(row, variable=var, command=_update_btn2,
                           bg=PANEL, activebackground=PANEL,
                           selectcolor=PANEL, fg=GREEN,
                           relief="flat", cursor="hand2").pack(side="left", padx=(0, 6))

            info = tk.Frame(row, bg=PANEL)
            info.pack(side="left", fill="x", expand=True)
            tk.Label(info, text=name, bg=PANEL, fg=TEXT,
                     font=(FONT, 11, "bold")).pack(anchor="w")
            tk.Label(info, text=desc, bg=PANEL, fg=MUTED,
                     font=(FONT, 9)).pack(anchor="w")

            right = tk.Frame(row, bg=PANEL)
            right.pack(side="right")
            tk.Label(right, text=badge, bg=PANEL, fg=badge_color,
                     font=(FONT, 8, "bold")).pack(side="left", padx=(0, 8))
            self._small_btn(right, "Como criar",
                            lambda n=name: self._popup(*INSTRUCTIONS[n]),
                            color=PANEL2, fg=MUTED).pack(side="left", padx=2)
            self._small_btn(right, "Abrir site  →",
                            lambda u=url: webbrowser.open(u),
                            color=BLUE, fg="white").pack(side="left", padx=(4, 0))

        tk.Label(body2,
                 text="Marque cada caixa conforme for criando as contas.",
                 bg=BG, fg=DIM, font=(FONT, 9)).pack(anchor="w", pady=(10, 0))

        sep = ttk.Separator(p)
        sep.pack(fill="x", side="bottom")
        footer = tk.Frame(p, bg=BG)
        footer.pack(fill="x", padx=32, pady=14, side="bottom")

        self._secondary_btn(footer, "← Voltar",
                            lambda: self._show(self._page_welcome)).pack(side="left")

        nb = self._primary_btn(footer, f"Continuar  (0/{len(providers)} contas)  →",
                                lambda: self._show(self._page_prereqs),
                                bg=PANEL2, fg=MUTED)
        nb.pack(side="right")
        next_btn_ref[0] = nb

        return p

    # ══════════════════════════════════════════════════════════════════════════
    # Página 3 — Ferramentas
    # ══════════════════════════════════════════════════════════════════════════
    def _page_prereqs(self):
        p = tk.Frame(self, bg=BG)
        self._header(p, "Ferramentas necessárias",
                     "Vamos instalar e configurar o que falta automaticamente.", step=1)

        body = tk.Frame(p, bg=BG)
        body.pack(fill="both", expand=True, padx=32, pady=(16, 0))

        # Log area (hidden until action)
        log_wrap = tk.Frame(body, bg=BG)
        log_box = scrolledtext.ScrolledText(log_wrap, bg=PANEL, fg=MUTED,
                                            font=("Consolas", 8), relief="flat",
                                            state="disabled", height=5)
        log_box.pack(fill="x")
        log_box.tag_config("ok",  foreground=GREEN)
        log_box.tag_config("err", foreground=RED)

        def _log(text, tag=None):
            log_box.config(state="normal")
            log_box.insert("end", text + "\n", tag or "")
            log_box.see("end")
            log_box.config(state="disabled")

        items = []
        next_ref = [None]

        def _recheck():
            all_ok = True
            for icon, lbl, btn, chk, _ in items:
                ok = chk()
                self.after(0, lambda i=icon, l=lbl, b=btn, o=ok: (
                    i.config(text="✅" if o else "❌",
                             fg=GREEN if o else RED),
                    l.config(text="Instalado" if o else "Pendente",
                             fg=GREEN if o else MUTED),
                    b.config(state="disabled" if o else "normal",
                             bg=DIM if o else BLUE, fg="white"),
                ))
                if not ok:
                    all_ok = False
            if all_ok and next_ref[0]:
                self.after(0, lambda: next_ref[0].config(state="normal", bg=BLUE, fg="white"))

        def _make_row(friendly_name, note, chk_fn, act_fn, act_label):
            row = tk.Frame(body, bg=PANEL, pady=12, padx=18)
            row.pack(fill="x", pady=4)

            left = tk.Frame(row, bg=PANEL)
            left.pack(side="left", fill="x", expand=True)

            icon = tk.Label(left, text="⏳", bg=PANEL, fg=MUTED, font=(FONT, 15), width=3)
            icon.pack(side="left")

            txt = tk.Frame(left, bg=PANEL)
            txt.pack(side="left")
            tk.Label(txt, text=friendly_name, bg=PANEL, fg=TEXT,
                     font=(FONT, 11, "bold")).pack(anchor="w")
            lbl = tk.Label(txt, text="verificando…", bg=PANEL, fg=DIM, font=(FONT, 9))
            lbl.pack(anchor="w")

            def _do(af=act_fn):
                log_wrap.pack(fill="x", pady=(8, 0))
                threading.Thread(target=lambda: (af(_log), _refresh_path(),
                                                 self.after(0, _recheck)), daemon=True).start()

            btn = self._small_btn(row, act_label, _do, color=BLUE, fg="white")
            btn.pack(side="right")

            items.append((icon, lbl, btn, chk_fn, act_fn))

        if note := "":
            pass

        # ── flyctl ───────────────────────────────────────────────────────────
        def _inst_fly(log_fn):
            log_fn("Instalando via winget…")
            r = subprocess.run(
                ["winget", "install", "-e", "--id", "Fly.flyctl",
                 "--accept-source-agreements", "--accept-package-agreements", "--silent"],
                capture_output=True, text=True, encoding="utf-8", creationflags=NO_WIN)
            if r.returncode != 0:
                log_fn("Tentando script oficial do Fly.io…")
                subprocess.run(["powershell", "-NoProfile", "-Command",
                                "iwr https://fly.io/install.ps1 -useb | iex"], creationflags=0)
            log_fn("Ferramenta do Fly.io instalada.", "ok")

        _make_row("Ferramenta do Fly.io",
                  "Necessária para publicar o bot",
                  lambda: _check(["fly", "version"]),
                  _inst_fly, "Instalar agora")

        # ── Node.js ───────────────────────────────────────────────────────────
        def _inst_node(log_fn):
            log_fn("Instalando Node.js via winget…")
            subprocess.run(
                ["winget", "install", "-e", "--id", "OpenJS.NodeJS.LTS",
                 "--accept-source-agreements", "--accept-package-agreements", "--silent"],
                capture_output=True, text=True, encoding="utf-8", creationflags=NO_WIN)
            log_fn("Node.js instalado.", "ok")

        _make_row("Node.js",
                  "Necessário para publicar o painel web",
                  lambda: _check(["node", "--version"]),
                  _inst_node, "Instalar agora")

        # ── Fly.io login ──────────────────────────────────────────────────────
        def _login_fly(log_fn):
            log_fn("Abrindo janela de login no Fly.io…")
            log_fn("Siga as instruções na janela preta e feche-a quando terminar.")
            proc = subprocess.Popen(
                ["cmd.exe", "/k",
                 "fly auth login && echo. && echo Pronto! Pode fechar esta janela."],
                creationflags=subprocess.CREATE_NEW_CONSOLE)
            proc.wait()
            log_fn("Verificando…")

        _make_row("Entrar no Fly.io",
                  "Login na sua conta do Fly.io",
                  lambda: _check(["fly", "auth", "whoami"]),
                  _login_fly, "Entrar com o navegador")

        # ── Vercel login ──────────────────────────────────────────────────────
        def _login_vercel(log_fn):
            log_fn("Abrindo janela de login no Vercel…")
            log_fn("Escolha 'Continue with GitHub' e feche a janela preta quando terminar.")
            proc = subprocess.Popen(
                ["cmd.exe", "/k",
                 "npx vercel login && echo. && echo Pronto! Pode fechar esta janela."],
                creationflags=subprocess.CREATE_NEW_CONSOLE)
            proc.wait()
            log_fn("Verificando…")

        _make_row("Entrar no Vercel",
                  "Login na sua conta do Vercel",
                  lambda: _check(["npx", "vercel", "whoami"]),
                  _login_vercel, "Entrar com o navegador")

        # Initial check
        def _init():
            all_ok = True
            for icon, lbl, btn, chk, _ in items:
                ok = chk()
                self.after(0, lambda i=icon, l=lbl, b=btn, o=ok: (
                    i.config(text="✅" if o else "❌", fg=GREEN if o else RED),
                    l.config(text="Instalado" if o else "Pendente",
                             fg=GREEN if o else MUTED),
                    b.config(state="disabled" if o else "normal",
                             bg=DIM if o else BLUE),
                ))
                if not ok:
                    all_ok = False
            if all_ok and next_ref[0]:
                self.after(0, lambda: next_ref[0].config(state="normal", bg=BLUE, fg="white"))

        threading.Thread(target=_init, daemon=True).start()

        sep = ttk.Separator(p)
        sep.pack(fill="x", side="bottom")
        footer = tk.Frame(p, bg=BG)
        footer.pack(fill="x", padx=32, pady=14, side="bottom")

        self._secondary_btn(footer, "← Voltar",
                            lambda: self._show(self._page_accounts)).pack(side="left")

        nb = self._primary_btn(footer, "Continuar  →",
                                lambda: self._show(self._page_config),
                                state="disabled", bg=DIM)
        nb.pack(side="right")
        next_ref[0] = nb

        return p

    # ══════════════════════════════════════════════════════════════════════════
    # Página 4 — Chaves e configuração
    # ══════════════════════════════════════════════════════════════════════════
    def _page_config(self):
        p = tk.Frame(self, bg=BG)
        self._header(p, "Suas chaves e tokens",
                     "Cole os valores que você anotou ao criar as contas.", step=2)

        outer = tk.Frame(p, bg=BG)
        outer.pack(fill="both", expand=True, padx=32, pady=(12, 0))
        canvas = tk.Canvas(outer, bg=BG, highlightthickness=0)
        sb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        body = tk.Frame(canvas, bg=BG)
        body.bind("<Configure>",
                  lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=body, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        # (key, friendly_label, is_secret, hint_text)
        sections = [
            ("🗄️  Supabase", [
                ("SUPABASE_URL",
                 "Endereço do projeto",
                 False,
                 "Cole aqui o Project URL  —  Supabase → Settings → API → Project URL"),
                ("SUPABASE_SERVICE_ROLE_KEY",
                 "Chave secreta do banco",
                 True,
                 "Cole aqui o service_role key  —  Supabase → Settings → API → service_role (secret)"),
            ]),
            ("💬  Telegram", [
                ("TELEGRAM_BOT_TOKEN",
                 "Token do bot",
                 True,
                 "O token que o @BotFather enviou quando você criou o bot  (ex: 123456:ABC...)"),
                ("TELEGRAM_USER_IDS",
                 "Seu ID de usuário",
                 False,
                 "O número que o @userinfobot te enviou  —  separe com vírgula se tiver mais de um"),
            ]),
            ("🤖  Groq (IA)", [
                ("GROQ_API_KEY",
                 "Chave da IA",
                 True,
                 "A API Key do Groq  —  começa com  gsk_"),
            ]),
            ("✈️  Fly.io  —  escolha nomes para os servidores", [
                ("BACKEND_APP",
                 "Nome do servidor principal",
                 False,
                 "Qualquer nome sem espaços ou acentos  (ex: meubot-api)"),
                ("BOT_APP",
                 "Nome do servidor do bot",
                 False,
                 "Qualquer nome sem espaços ou acentos  (ex: meubot-telegram)"),
            ]),
            ("🌐  Painel web  —  defina uma senha de acesso", [
                ("DASHBOARD_PASSWORD",
                 "Senha de acesso",
                 True,
                 "Você vai usar essa senha para entrar no painel web  —  mínimo 6 caracteres"),
                ("DASHBOARD_PASSWORD2",
                 "Confirme a senha",
                 True,
                 "Digite a mesma senha novamente para confirmar"),
            ]),
        ]

        PH = "#334155"  # placeholder text color

        for section_title, fields in sections:
            tk.Label(body, text=section_title, bg=BG, fg=MUTED,
                     font=(FONT, 10, "bold")).pack(anchor="w", pady=(18, 4))

            for key, label, is_secret, hint in fields:
                block = tk.Frame(body, bg=BG)
                block.pack(fill="x", pady=4)

                tk.Label(block, text=label, bg=BG, fg=TEXT,
                         font=(FONT, 10, "bold")).pack(anchor="w")

                row = tk.Frame(block, bg=BG)
                row.pack(fill="x", pady=(3, 0))

                var = tk.StringVar()
                self._vars[key] = var

                entry = tk.Entry(row, textvariable=var,
                                 show="•" if is_secret else "",
                                 bg=PANEL, fg=TEXT,
                                 insertbackground=TEXT, relief="flat",
                                 font=("Consolas", 10), width=52)
                entry.pack(side="left", ipady=7, padx=(0, 4))

                if is_secret:
                    ev = tk.BooleanVar(value=False)
                    def _toggle(en=entry, sv=ev):
                        sv.set(not sv.get())
                        en.config(show="" if sv.get() else "•")
                    tk.Button(row, text="👁", command=_toggle,
                              bg=PANEL, fg=DIM, relief="flat",
                              cursor="hand2", font=(FONT, 10),
                              padx=8, pady=6).pack(side="left")

                tk.Label(block, text=hint, bg=BG, fg=DIM,
                         font=(FONT, 8), anchor="w").pack(anchor="w", pady=(2, 0))

        DEFAULTS = {
            "BACKEND_APP": "",
            "BOT_APP": "",
        }

        def _validate():
            required = ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY",
                        "TELEGRAM_BOT_TOKEN", "TELEGRAM_USER_IDS",
                        "GROQ_API_KEY", "BACKEND_APP", "BOT_APP",
                        "DASHBOARD_PASSWORD", "DASHBOARD_PASSWORD2"]
            missing = []
            for k in required:
                if not self._vars[k].get().strip():
                    missing.append(k)
            if missing:
                messagebox.showerror(
                    "Campos em branco",
                    "Por favor, preencha todos os campos antes de continuar.\n\n"
                    "Se tiver dúvida sobre onde encontrar algum valor,\n"
                    "volte à etapa 'Criar contas' e clique em 'Como criar'.",
                )
                return False
            pw1 = self._vars["DASHBOARD_PASSWORD"].get()
            pw2 = self._vars["DASHBOARD_PASSWORD2"].get()
            if pw1 != pw2:
                messagebox.showerror("Senhas diferentes",
                                     "As senhas do painel web não conferem.\n"
                                     "Por favor, digite a mesma senha nos dois campos.")
                return False
            if len(pw1) < 6:
                messagebox.showerror("Senha muito curta",
                                     "A senha precisa ter pelo menos 6 caracteres.")
                return False
            return True

        sep = ttk.Separator(p)
        sep.pack(fill="x", side="bottom")
        footer = tk.Frame(p, bg=BG)
        footer.pack(fill="x", padx=32, pady=14, side="bottom")
        self._secondary_btn(footer, "← Voltar",
                            lambda: self._show(self._page_prereqs)).pack(side="left")
        self._primary_btn(footer, "Publicar o bot  →",
                          lambda: _validate() and self._show(self._page_deploy)).pack(side="right")

        return p

    # ══════════════════════════════════════════════════════════════════════════
    # Página 5 — Publicando
    # ══════════════════════════════════════════════════════════════════════════
    def _page_deploy(self):
        p = tk.Frame(self, bg=BG)
        self._header(p, "Publicando o bot…",
                     "Aguarde enquanto tudo é configurado. Não feche a janela.", step=3)

        body = tk.Frame(p, bg=BG)
        body.pack(fill="both", expand=True, padx=32, pady=(16, 0))

        # ── 3 step cards ──────────────────────────────────────────────────────
        step_icons  = ["⏳", "⏳", "⏳"]
        step_labels = ["Servidor principal", "Bot do Telegram", "Painel web"]
        step_notes  = ["Configurando o servidor...", "Iniciando o bot...", "Publicando o painel..."]
        card_lbl    = []
        card_note   = []
        card_icon   = []

        cards_frame = tk.Frame(body, bg=BG)
        cards_frame.pack(fill="x")

        for i, (icon, label, note) in enumerate(zip(step_icons, step_labels, step_notes)):
            card = tk.Frame(cards_frame, bg=PANEL, pady=12, padx=16)
            card.pack(fill="x", pady=3)
            ic = tk.Label(card, text=icon, bg=PANEL, font=(FONT, 16), width=3)
            ic.pack(side="left")
            txt = tk.Frame(card, bg=PANEL)
            txt.pack(side="left")
            lb = tk.Label(txt, text=label, bg=PANEL, fg=TEXT, font=(FONT, 11, "bold"))
            lb.pack(anchor="w")
            nt = tk.Label(txt, text="Aguardando…", bg=PANEL, fg=DIM, font=(FONT, 9))
            nt.pack(anchor="w")
            card_icon.append(ic)
            card_lbl.append(lb)
            card_note.append(nt)

        # ── Log (collapsible) ─────────────────────────────────────────────────
        log_visible = [False]
        log_wrap = tk.Frame(body, bg=BG)

        log = scrolledtext.ScrolledText(log_wrap, bg=PANEL, fg=MUTED,
                                        font=("Consolas", 8), relief="flat",
                                        state="disabled", height=8)
        log.pack(fill="x")
        log.tag_config("ok",  foreground=GREEN)
        log.tag_config("err", foreground=RED)
        log.tag_config("hdr", foreground=YELLOW)

        toggle_btn = tk.Button(body, text="▸  Ver detalhes técnicos",
                               command=lambda: _toggle_log(),
                               bg=BG, fg=DIM, relief="flat",
                               font=(FONT, 9), cursor="hand2", anchor="w")
        toggle_btn.pack(anchor="w", pady=(10, 0))

        def _toggle_log():
            log_visible[0] = not log_visible[0]
            if log_visible[0]:
                log_wrap.pack(fill="x", pady=(4, 0))
                toggle_btn.config(text="▾  Ocultar detalhes técnicos")
            else:
                log_wrap.pack_forget()
                toggle_btn.config(text="▸  Ver detalhes técnicos")

        def _log(text, tag=None):
            log.config(state="normal")
            log.insert("end", text + "\n", tag or "")
            log.see("end")
            log.config(state="disabled")

        def _set_step(i, state):
            # state: "running" | "done" | "error"
            if state == "running":
                ic, fg, note = "⏳", YELLOW, step_notes[i]
            elif state == "done":
                ic, fg, note = "✅", GREEN, "Concluído!"
            else:
                ic, fg, note = "❌", RED, "Erro — veja os detalhes técnicos"
            self.after(0, lambda: (
                card_icon[i].config(text=ic),
                card_note[i].config(text=note, fg=fg),
            ))

        done_btn = self._primary_btn(p, "Ver resultado  →",
                                     lambda: self._show(lambda: self._page_done(self._urls)),
                                     state="disabled", bg=DIM)
        done_btn.pack(side="right", padx=32, pady=14)

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

        def _fly_exists(name):
            r = subprocess.run(["fly", "apps", "list"], capture_output=True,
                               text=True, encoding="utf-8", creationflags=NO_WIN)
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
            self.after(0, lambda: _log(f"  {name}: {'OK' if proc.returncode == 0 else 'ERRO'}"))

        def deploy():
            v         = {k: var.get().strip() for k, var in self._vars.items()}
            api_key   = secrets.token_hex(32)
            sess_key  = secrets.token_hex(32)
            bapp      = v["BACKEND_APP"]
            botapp    = v["BOT_APP"]
            burl      = f"https://{bapp}.fly.dev"

            # Step 1 — backend
            _set_step(0, "running")
            self.after(0, lambda: _log("\n── Servidor principal ──", "hdr"))
            _update_toml(BACKEND_TOML, bapp)
            if not _fly_exists(bapp):
                _run(["fly", "apps", "create", bapp])
            ok, _ = _run([
                "fly", "secrets", "set",
                f"SUPABASE_URL={v['SUPABASE_URL']}",
                f"SUPABASE_SERVICE_ROLE_KEY={v['SUPABASE_SERVICE_ROLE_KEY']}",
                f"API_SECRET_KEY={api_key}",
                "--app", bapp,
            ], cwd=BACKEND_DIR)
            if not ok:
                _set_step(0, "error")
                return
            ok, _ = _run(["fly", "deploy", "--app", bapp, "--wait-timeout", "180"],
                         cwd=BACKEND_DIR)
            _set_step(0, "done" if ok else "error")
            if not ok:
                return

            # Step 2 — bot
            _set_step(1, "running")
            self.after(0, lambda: _log("\n── Bot do Telegram ──", "hdr"))
            _update_toml(BOT_TOML, botapp,
                         [(r'BACKEND_URL\s*=.*', f'BACKEND_URL = "{burl}"')])
            if not _fly_exists(botapp):
                _run(["fly", "apps", "create", botapp])
            ok, _ = _run([
                "fly", "secrets", "set",
                f"TELEGRAM_BOT_TOKEN={v['TELEGRAM_BOT_TOKEN']}",
                f"TELEGRAM_USER_IDS={v['TELEGRAM_USER_IDS']}",
                f"BACKEND_URL={burl}",
                f"API_SECRET_KEY={api_key}",
                f"GROQ_API_KEY={v['GROQ_API_KEY']}",
                "--app", botapp,
            ], cwd=ROOT)
            if not ok:
                _set_step(1, "error")
                return
            ok, _ = _run(["fly", "deploy", "--app", botapp, "--wait-timeout", "180"],
                         cwd=ROOT)
            _set_step(1, "done" if ok else "error")
            if not ok:
                return

            # Step 3 — dashboard
            _set_step(2, "running")
            self.after(0, lambda: _log("\n── Painel web ──", "hdr"))
            with open(os.path.join(DASHBOARD_DIR, "vercel.json"), "w") as f:
                f.write("{}\n")
            for name, val in [
                ("BACKEND_URL",        burl),
                ("API_SECRET_KEY",     api_key),
                ("DASHBOARD_PASSWORD", v["DASHBOARD_PASSWORD"]),
                ("SESSION_SECRET",     sess_key),
            ]:
                _vercel_env(name, val)
            ok, out = _run(["npx", "vercel", "--prod", "--yes"], cwd=DASHBOARD_DIR)
            _set_step(2, "done" if ok else "error")

            match = re.search(r"https://[^\s]+\.vercel\.app", out)
            self._urls = {
                "backend":   burl,
                "dashboard": match.group(0) if match else "(veja vercel.com)",
            }

            self.after(0, lambda: (
                _log("\n✅  Publicação concluída!", "ok"),
                done_btn.config(state="normal", bg=BLUE),
            ))

        threading.Thread(target=deploy, daemon=True).start()
        return p

    # ══════════════════════════════════════════════════════════════════════════
    # Página 6 — Pronto
    # ══════════════════════════════════════════════════════════════════════════
    def _page_done(self, urls):
        p = tk.Frame(self, bg=BG)
        self._header(p, "Tudo pronto! 🎉",
                     "Seu bot está publicado e funcionando.", step=4)

        body = tk.Frame(p, bg=BG)
        body.pack(fill="both", expand=True, padx=32, pady=(16, 0))

        # URL cards
        for icon, label, url in [
            ("🌐", "Endereço do painel web", urls.get("dashboard", "")),
        ]:
            card = tk.Frame(body, bg=PANEL, pady=14, padx=20)
            card.pack(fill="x", pady=4)
            tk.Label(card, text=f"{icon}  {label}", bg=PANEL, fg=MUTED,
                     font=(FONT, 9)).pack(anchor="w")
            tk.Label(card, text=url, bg=PANEL, fg=GREEN,
                     font=("Consolas", 11)).pack(anchor="w", pady=(4, 0))
            tk.Button(card, text="Abrir no navegador",
                      command=lambda u=url: webbrowser.open(u),
                      bg=BLUE, fg="white", relief="flat", font=(FONT, 9, "bold"),
                      padx=10, pady=4, cursor="hand2").pack(anchor="w", pady=(8, 0))

        # Next steps
        tk.Label(body, text="Próximos passos:", bg=BG, fg=TEXT,
                 font=(FONT, 11, "bold")).pack(anchor="w", pady=(20, 6))

        for num, step in [
            ("1", "Abra o Telegram, encontre seu bot pelo nome e clique em START"),
            ("2", "Mande uma mensagem como:  gastei 50 reais no mercado"),
            ("3", "Acesse o painel web e entre com a senha que você definiu"),
            ("4", "Cadastre seus cartões no painel antes de usar"),
        ]:
            row = tk.Frame(body, bg=BG)
            row.pack(anchor="w", pady=2)
            tk.Label(row, text=f"  {num}.", bg=BG, fg=BLUE,
                     font=(FONT, 10, "bold"), width=4).pack(side="left")
            tk.Label(row, text=step, bg=BG, fg=MUTED, font=(FONT, 10)).pack(side="left")

        sep = ttk.Separator(p)
        sep.pack(fill="x", side="bottom")
        footer = tk.Frame(p, bg=BG)
        footer.pack(fill="x", padx=32, pady=14, side="bottom")
        self._primary_btn(footer, "Fechar", self.destroy).pack(side="right")

        return p


if __name__ == "__main__":
    app = Wizard()
    app.mainloop()
