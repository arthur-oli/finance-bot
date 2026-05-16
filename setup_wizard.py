"""Finance Bot — Setup Wizard (compile with build_wizard.bat)"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import subprocess
import threading
import secrets
import sys
import os
import re

# ── Project root (works both as .py and compiled .exe) ───────────────────────
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
FONT    = "Segoe UI"


# ── Helpers ───────────────────────────────────────────────────────────────────
def _popen_no_window(args, cwd=None):
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    return subprocess.Popen(
        args, cwd=cwd,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        stdin=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace",
        creationflags=flags,
    )


def _run_check(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=15,
                           creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
        return r.returncode == 0
    except Exception:
        return False


def _update_toml(path, app_name, replacements=None):
    with open(path, encoding="utf-8") as f:
        content = f.read()
    content = re.sub(r'^app\s*=.*', f'app = "{app_name}"', content, flags=re.M)
    for pattern, repl in (replacements or []):
        content = re.sub(pattern, repl, content, flags=re.M)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


# ── Main wizard window ────────────────────────────────────────────────────────
class Wizard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Finance Bot — Setup")
        self.geometry("740x560")
        self.resizable(False, False)
        self.configure(bg=BG)
        self._center()
        self._frame = None
        self._vars = {}
        self._urls = {}
        self._show(self._page_welcome)

    def _center(self):
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - 740) // 2
        y = (self.winfo_screenheight() - 560) // 2
        self.geometry(f"740x560+{x}+{y}")

    def _show(self, page_fn):
        if self._frame:
            self._frame.destroy()
        self._frame = page_fn()
        self._frame.pack(fill="both", expand=True)

    # ── Reusable widgets ──────────────────────────────────────────────────────
    def _header(self, parent, title, sub=""):
        f = tk.Frame(parent, bg=BG)
        tk.Label(f, text="💰  Finance Bot", bg=BG, fg=BLUE,
                 font=(FONT, 10)).pack(anchor="w")
        tk.Label(f, text=title, bg=BG, fg=TEXT,
                 font=(FONT, 17, "bold")).pack(anchor="w", pady=(2, 0))
        if sub:
            tk.Label(f, text=sub, bg=BG, fg=SUBTEXT,
                     font=(FONT, 10)).pack(anchor="w")
        ttk.Separator(f).pack(fill="x", pady=10)
        f.pack(fill="x", padx=28, pady=(20, 0))

    def _btn(self, parent, label, cmd, primary=False, **kw):
        bg = BLUE if primary else PANEL
        fg = "white" if primary else TEXT
        return tk.Button(parent, text=label, command=cmd,
                         bg=bg, fg=fg, activebackground=bg, activeforeground=fg,
                         relief="flat", font=(FONT, 10, "bold" if primary else "normal"),
                         padx=18, pady=7, cursor="hand2", **kw)

    def _footer(self, parent, right_btns, left_btns=None):
        f = tk.Frame(parent, bg=BG)
        f.pack(fill="x", padx=28, pady=14, side="bottom")
        for btn in reversed(right_btns):
            btn(f).pack(side="right", padx=4)
        for btn in (left_btns or []):
            btn(f).pack(side="left", padx=4)

    # ══════════════════════════════════════════════════════════════════════════
    # Page 1 — Welcome
    # ══════════════════════════════════════════════════════════════════════════
    def _page_welcome(self):
        p = tk.Frame(self, bg=BG)
        self._header(p, "Setup Wizard", "Configure e faça deploy em cloud — sem digitar nada no terminal")

        body = tk.Frame(p, bg=BG)
        body.pack(fill="both", expand=True, padx=28)

        tk.Label(body, text="O que este wizard vai fazer:", bg=BG, fg=TEXT,
                 font=(FONT, 10, "bold")).pack(anchor="w", pady=(4, 6))

        for num, desc in [
            ("1", "Verificar pré-requisitos (flyctl, Node.js, vercel)"),
            ("2", "Coletar suas chaves e tokens"),
            ("3", "Deploy do backend no Fly.io"),
            ("4", "Deploy do bot no Fly.io"),
            ("5", "Deploy do dashboard no Vercel"),
        ]:
            row = tk.Frame(body, bg=BG)
            row.pack(anchor="w", pady=1)
            tk.Label(row, text=f"  {num}.", bg=BG, fg=BLUE,
                     font=(FONT, 10, "bold"), width=4).pack(side="left")
            tk.Label(row, text=desc, bg=BG, fg=SUBTEXT,
                     font=(FONT, 10)).pack(side="left")

        tk.Label(body,
                 text="\nAntes de continuar, crie suas contas em:\n"
                      "  • supabase.com   • fly.io   • vercel.com   • console.groq.com\n"
                      "  • Telegram @BotFather (para criar o bot)\n\n"
                      "Consulte SETUP.md para o passo a passo de cada conta.",
                 bg=BG, fg=SUBTEXT, font=(FONT, 9), justify="left").pack(anchor="w", pady=12)

        self._footer(p, [
            lambda f: self._btn(f, "Verificar pré-requisitos →",
                                lambda: self._show(self._page_prereqs), primary=True),
        ])
        return p

    # ══════════════════════════════════════════════════════════════════════════
    # Page 2 — Prerequisites
    # ══════════════════════════════════════════════════════════════════════════
    def _page_prereqs(self):
        p = tk.Frame(self, bg=BG)
        self._header(p, "Pré-requisitos", "Verificando ferramentas necessárias…")

        body = tk.Frame(p, bg=BG)
        body.pack(fill="both", expand=True, padx=28)

        checks = [
            ("flyctl",         ["fly", "version"],        "fly.io/docs/hands-on/install-flyctl/"),
            ("Node.js / npm",  ["node", "--version"],     "nodejs.org"),
            ("Fly.io login",   ["fly", "auth", "whoami"], "Abra um terminal e rode:  fly auth login"),
            ("Vercel login",   ["npx", "vercel", "whoami"], "Abra um terminal e rode:  npx vercel login"),
        ]

        rows = []
        for label, cmd, hint in checks:
            row = tk.Frame(body, bg=PANEL, pady=9, padx=14)
            row.pack(fill="x", pady=3)
            icon = tk.Label(row, text="⏳", bg=PANEL, font=(FONT, 13), width=3)
            icon.pack(side="left")
            tk.Label(row, text=label, bg=PANEL, fg=TEXT,
                     font=(FONT, 10, "bold")).pack(side="left")
            hint_lbl = tk.Label(row, text="verificando…", bg=PANEL, fg=SUBTEXT,
                                font=(FONT, 9))
            hint_lbl.pack(side="right", padx=8)
            rows.append((icon, hint_lbl, cmd, hint))

        next_btn_ref = [None]

        self._footer(p, [
            lambda f: self._btn(f, "Continuar →",
                                lambda: self._show(self._page_config),
                                primary=True, state="disabled") if not next_btn_ref[0]
            else next_btn_ref[0],
        ], left_btns=[
            lambda f: self._btn(f, "← Voltar", lambda: self._show(self._page_welcome)),
        ])

        # find the next button and keep reference
        for w in p.winfo_children():
            for c in w.winfo_children():
                if isinstance(c, tk.Button) and "Continuar" in str(c.cget("text")):
                    next_btn_ref[0] = c

        def run_checks():
            all_ok = True
            for icon, lbl, cmd, hint in rows:
                ok = _run_check(cmd)
                tag = "✅" if ok else "❌"
                color = GREEN if ok else RED
                text = "OK" if ok else hint
                self.after(0, lambda i=icon, l=lbl, t=tag, c=color, x=text: (
                    i.config(text=t),
                    l.config(text=x, fg=c),
                ))
                if not ok:
                    all_ok = False

            if all_ok:
                def enable():
                    for w in p.winfo_children():
                        for c in w.winfo_children():
                            if isinstance(c, tk.Button) and "Continuar" in str(c.cget("text")):
                                c.config(state="normal")
                self.after(0, enable)

        threading.Thread(target=run_checks, daemon=True).start()
        return p

    # ══════════════════════════════════════════════════════════════════════════
    # Page 3 — Configuration form
    # ══════════════════════════════════════════════════════════════════════════
    def _page_config(self):
        p = tk.Frame(self, bg=BG)
        self._header(p, "Configuração", "Cole suas chaves — nada é salvo no disco")

        # Scrollable area
        outer = tk.Frame(p, bg=BG)
        outer.pack(fill="both", expand=True, padx=28)
        canvas = tk.Canvas(outer, bg=BG, highlightthickness=0)
        sb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        body = tk.Frame(canvas, bg=BG)
        body.bind("<Configure>",
                  lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=body, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # Mousewheel scroll
        def _scroll(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _scroll)

        sections = [
            ("Supabase  (Settings → API)", [
                ("SUPABASE_URL",             "Project URL",        False, "https://xxxx.supabase.co"),
                ("SUPABASE_SERVICE_ROLE_KEY", "Service Role Key",  True,  "eyJ…"),
            ]),
            ("Telegram", [
                ("TELEGRAM_BOT_TOKEN", "Bot Token",    True,  "123456:ABC…"),
                ("TELEGRAM_USER_IDS",  "User ID(s)",   False, "Separe com vírgula para múltiplos usuários"),
            ]),
            ("Groq  (console.groq.com)", [
                ("GROQ_API_KEY", "API Key", True, "gsk_…"),
            ]),
            ("Fly.io — escolha os nomes dos apps", [
                ("BACKEND_APP", "Nome do backend", False, "meubot-backend"),
                ("BOT_APP",     "Nome do bot",     False, "meubot-worker"),
            ]),
            ("Dashboard — senha de acesso ao painel web", [
                ("DASHBOARD_PASSWORD",  "Senha",          True, ""),
                ("DASHBOARD_PASSWORD2", "Confirmar senha", True, ""),
            ]),
        ]

        PLACEHOLDER_COLOR = "#475569"

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
                                 bg=PANEL, fg=TEXT if not placeholder else PLACEHOLDER_COLOR,
                                 insertbackground=TEXT, relief="flat",
                                 font=("Consolas", 10), width=40)
                entry.pack(side="left", ipady=5, padx=(4, 2))

                # Placeholder logic for non-secret fields
                if placeholder and not is_secret:
                    entry.insert(0, placeholder)
                    entry.config(fg=PLACEHOLDER_COLOR)

                    def _fi(e, en=entry, ph=placeholder, v=var):
                        if en.get() == ph:
                            en.delete(0, "end")
                            en.config(fg=TEXT)

                    def _fo(e, en=entry, ph=placeholder, v=var):
                        if not en.get().strip():
                            en.insert(0, ph)
                            en.config(fg=PLACEHOLDER_COLOR)
                            v.set("")

                    entry.bind("<FocusIn>", _fi)
                    entry.bind("<FocusOut>", _fo)

                # Eye toggle for secrets
                if is_secret:
                    eye_var = tk.BooleanVar(value=False)

                    def _toggle(en=entry, ev=eye_var):
                        ev.set(not ev.get())
                        en.config(show="" if ev.get() else "•")

                    tk.Button(row, text="👁", command=_toggle,
                              bg=PANEL, fg=SUBTEXT, relief="flat",
                              cursor="hand2", font=(FONT, 9)).pack(side="left")

        placeholders_map = {
            "SUPABASE_URL":    "https://xxxx.supabase.co",
            "TELEGRAM_USER_IDS": "Separe com vírgula para múltiplos usuários",
            "BACKEND_APP":     "meubot-backend",
            "BOT_APP":         "meubot-worker",
        }

        def _validate():
            errors = []
            for k in ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY",
                      "TELEGRAM_BOT_TOKEN", "TELEGRAM_USER_IDS",
                      "GROQ_API_KEY", "BACKEND_APP", "BOT_APP",
                      "DASHBOARD_PASSWORD", "DASHBOARD_PASSWORD2"]:
                val = self._vars[k].get().strip()
                if not val or val == placeholders_map.get(k, ""):
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

        log = scrolledtext.ScrolledText(
            body, bg=PANEL, fg=TEXT, font=("Consolas", 9),
            relief="flat", state="disabled", height=16,
        )
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
            proc = _popen_no_window(args, cwd=cwd)
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
                               creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
            return name in r.stdout

        def _vercel_env(name, value):
            proc = _popen_no_window(
                ["npx", "vercel", "env", "add", name, "production", "--force"],
                cwd=DASHBOARD_DIR,
            )
            try:
                proc.stdin.write(value)
                proc.stdin.close()
            except Exception:
                pass
            out = proc.stdout.read()
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
            self.after(0, lambda: status.config(text="[1/3]  Deploy do Backend no Fly.io…"))
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
                self.after(0, lambda: status.config(text="❌  Erro no backend secrets", fg=RED))
                return

            ok, _ = _run(["fly", "deploy", "--app", backend_app, "--wait-timeout", "180"],
                         cwd=BACKEND_DIR)
            if not ok:
                self.after(0, lambda: status.config(text="❌  Erro no deploy do backend", fg=RED))
                return

            # ── Bot ────────────────────────────────────────────────────────
            self.after(0, lambda: status.config(text="[2/3]  Deploy do Bot no Fly.io…"))
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
                self.after(0, lambda: status.config(text="❌  Erro no bot secrets", fg=RED))
                return

            ok, _ = _run(["fly", "deploy", "--app", bot_app, "--wait-timeout", "180"],
                         cwd=ROOT)
            if not ok:
                self.after(0, lambda: status.config(text="❌  Erro no deploy do bot", fg=RED))
                return

            # ── Dashboard (Vercel) ─────────────────────────────────────────
            self.after(0, lambda: status.config(text="[3/3]  Deploy do Dashboard no Vercel…"))
            self.after(0, lambda: _log("\n══ DASHBOARD ══", "hdr"))

            # Clear alias so new users don't get financebot-tutur conflict
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

            self._urls = {
                "backend":   backend_url,
                "dashboard": dashboard_url,
            }

            self.after(0, lambda: (
                status.config(text="✅  Tudo deployado!", fg=GREEN),
                _log("\n✅  Deploy concluído com sucesso!", "ok"),
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
            tk.Label(card, text=label, bg=PANEL, fg=SUBTEXT,
                     font=(FONT, 9)).pack(anchor="w")
            tk.Label(card, text=url, bg=PANEL, fg=GREEN,
                     font=("Consolas", 11)).pack(anchor="w", pady=(2, 0))

        tk.Label(body,
                 text="\nPróximos passos:\n"
                      "  1. Abra o Telegram e mande uma mensagem pro bot (ex: gastei 50 no mercado)\n"
                      "  2. Acesse o dashboard com a senha que você definiu\n"
                      "  3. Cadastre seus cartões no dashboard antes de usar",
                 bg=BG, fg=SUBTEXT, font=(FONT, 10), justify="left").pack(anchor="w", pady=14)

        self._footer(p, [
            lambda f: self._btn(f, "Fechar", self.destroy, primary=True),
        ])
        return p


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = Wizard()
    app.mainloop()
