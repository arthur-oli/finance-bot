"""Finance Bot — Setup Wizard"""

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog
import subprocess
import threading
import secrets
import webbrowser
import sys
import os
import re
import time
import json
import urllib.request
from PIL import Image, ImageTk

DEMO = "--demo" in sys.argv

if sys.platform == "win32":
    import ctypes
    _mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "Global\\FinanceBotSetupWizard")
    if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        sys.exit(0)

# ── Project root ──────────────────────────────────────────────────────────────
if getattr(sys, "frozen", False):
    ROOT = os.path.dirname(sys.executable)
else:
    ROOT = os.path.dirname(os.path.abspath(__file__))

BACKEND_DIR   = os.path.join(ROOT, "backend")
DASHBOARD_DIR = os.path.join(ROOT, "dashboard")
BOT_TOML      = os.path.join(ROOT, "fly.toml")
BACKEND_TOML  = os.path.join(BACKEND_DIR, "fly.toml")
SCHEMA_SQL    = os.path.join(ROOT, "schema.sql")
if not os.path.exists(SCHEMA_SQL):
    SCHEMA_SQL = os.path.join(os.path.dirname(ROOT), "schema.sql")

def _asset(name):
    """Resolve caminho de um asset, tanto no exe frozen quanto em dev."""
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, "assets", name)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", name)

# ── Distribution ──────────────────────────────────────────────────────────────
GITHUB_REPO = "arthur-oli/finance-bot"
APPDATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "FinanceBot")
CONFIG_JSON = os.path.join(APPDATA_DIR, "config.json")

# ── Palette ───────────────────────────────────────────────────────────────────
BG     = "#0f172a"
PANEL  = "#1e293b"
PANEL2 = "#263348"
BLUE   = "#3b82f6"
BLUE2  = "#2563eb"
GREEN  = "#22c55e"
RED    = "#ef4444"
YELLOW = "#f59e0b"
TEXT   = "#f1f5f9"
MUTED  = "#cbd5e1"
DIM    = "#64748b"
FONT   = "Calibri"

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


def _check_output(cmd, env=None):
    try:
        e = {**os.environ, "NO_UPDATE_NOTIFIER": "1"}
        if env:
            e.update(env)
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=20, encoding="utf-8", errors="replace",
                           creationflags=NO_WIN, env=e)
        if r.returncode == 0:
            return r.stdout.strip()
        return None
    except Exception:
        return None


def _popen(args, cwd=None, env=None):
    return subprocess.Popen(
        args, cwd=cwd, env=env,
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


def _set_install_path(path):
    global ROOT, BACKEND_DIR, DASHBOARD_DIR, BOT_TOML, BACKEND_TOML, SCHEMA_SQL
    ROOT          = path
    BACKEND_DIR   = os.path.join(ROOT, "backend")
    DASHBOARD_DIR = os.path.join(ROOT, "dashboard")
    BOT_TOML      = os.path.join(ROOT, "fly.toml")
    BACKEND_TOML  = os.path.join(BACKEND_DIR, "fly.toml")
    SCHEMA_SQL    = os.path.join(ROOT, "schema.sql")


# ── Wizard ────────────────────────────────────────────────────────────────────
class Wizard(tk.Tk):
    W, H = 780, 600
    # 5 phases shown in step bar
    PHASES = ["Preparar", "Conectar contas", "Revisar", "Publicar", "Pronto"]
    # sub-steps within "Conectar contas"
    PROVIDERS = ["Supabase", "Telegram", "Groq", "Fly.io", "Vercel"]

    def __init__(self):
        super().__init__()
        self.withdraw()
        self.title("Finance Bot — Setup")
        self.geometry(f"{self.W}x{self.H}")
        self.resizable(False, False)
        self.configure(bg=BG)
        try:
            import tempfile
            _logo_img = Image.open(_asset("finance-bot-logo.png")).convert("RGBA")
            _ico_path = os.path.join(tempfile.gettempdir(), "financebot_icon.ico")
            _logo_img.resize((256, 256), Image.LANCZOS).save(
                _ico_path, format="ICO",
                sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
            )
            self.iconbitmap(_ico_path)
        except Exception:
            pass
        self._frame = None
        self._vars  = {}   # StringVar per field key
        self._info  = {}   # misc runtime info (login emails, etc.)
        if DEMO:
            self._prefill_demo()
            self._show(self._page_deploy)
        else:
            self._show(self._page_welcome)
        self._center()
        self.deiconify()

    def _prefill_demo(self):
        demo_vals = {
            "SUPABASE_URL":              "https://abcdefghij1234567890.supabase.co",
            "SUPABASE_PROJECT_ID":       "abcdefghij1234567890",
            "SUPABASE_DB_PASSWORD":      "demo-password-1234",
            "SUPABASE_SERVICE_ROLE_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.demo",
            "TELEGRAM_BOT_TOKEN":        "123456789:ABCdefGHIjklMNOpqrSTUvwxYZ123456",
            "TELEGRAM_USER_IDS":         "987654321",
            "GROQ_API_KEY":              "gsk_demoKeyForTestingPurposesOnly123456",
            "BACKEND_APP":               "finance-api-demo",
            "BOT_APP":                   "finance-bot-demo",
            "DASHBOARD_PASSWORD":        "demo1234",
            "DASHBOARD_PASSWORD2":       "demo1234",
        }
        for k, v in demo_vals.items():
            self._var(k, v)

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

    def _var(self, key, default=""):
        if key not in self._vars:
            self._vars[key] = tk.StringVar(value=default)
        return self._vars[key]

    # ── Step bar ──────────────────────────────────────────────────────────────
    def _step_bar(self, parent, phase, provider_idx=None):
        """phase: 0-4 (index into PHASES). provider_idx: 0-4 within phase 1."""
        wrap = tk.Frame(parent, bg=BG)
        wrap.pack(fill="x", padx=32, pady=(18, 0))

        c = tk.Canvas(wrap, bg=BG, highlightthickness=0, height=46)
        c.pack(fill="x")

        def _draw(event=None):
            c.delete("all")
            w   = c.winfo_width() or (self.W - 64)
            n   = len(self.PHASES)
            seg = w / n

            for i, label in enumerate(self.PHASES):
                cx = int(seg * i + seg / 2)
                cy = 16

                if i < n - 1:
                    nx  = int(seg * (i + 1) + seg / 2)
                    col = GREEN if i < phase else DIM
                    c.create_line(cx + 13, cy, nx - 13, cy, fill=col, width=2)

                if i < phase:
                    c.create_oval(cx-12, cy-12, cx+12, cy+12, fill=GREEN, outline="")
                    c.create_text(cx, cy, text="✓", font=(FONT, 10, "bold"), fill=BG)
                elif i == phase:
                    c.create_oval(cx-13, cy-13, cx+13, cy+13, fill=BLUE, outline="")
                    c.create_text(cx, cy, text=str(i+1), font=(FONT, 10, "bold"), fill="white")
                else:
                    c.create_oval(cx-11, cy-11, cx+11, cy+11, fill=BG, outline=DIM, width=2)
                    c.create_text(cx, cy, text=str(i+1), font=(FONT, 9), fill=DIM)

                lc = TEXT if i == phase else (MUTED if i < phase else DIM)
                lw = "bold" if i == phase else "normal"
                c.create_text(cx, cy + 24, text=label, font=(FONT, 8, lw), fill=lc)

        c.bind("<Configure>", _draw)
        self.after(10, _draw)

        # sub-progress for "Conectar contas"
        if phase == 1 and provider_idx is not None:
            sub = tk.Frame(wrap, bg=BG)
            sub.pack(fill="x", pady=(4, 0))
            for i, name in enumerate(self.PROVIDERS):
                done = i < provider_idx
                cur  = i == provider_idx
                col  = GREEN if done else (BLUE if cur else DIM)
                wt   = "bold" if cur else "normal"
                tk.Label(sub, text=("✓ " if done else "") + name,
                         bg=BG, fg=col, font=(FONT, 8, wt)).pack(side="left", padx=6)

        ttk.Separator(wrap).pack(fill="x", pady=(8, 0))
        return wrap

    # ── Common layout helpers ─────────────────────────────────────────────────
    def _header(self, parent, title, sub, phase, provider_idx=None):
        self._step_bar(parent, phase, provider_idx)
        f = tk.Frame(parent, bg=BG)
        tk.Label(f, text=title, bg=BG, fg=TEXT,
                 font=(FONT, 18, "bold")).pack(anchor="w", pady=(14, 0))
        if sub:
            tk.Label(f, text=sub, bg=BG, fg=MUTED, font=(FONT, 10)).pack(anchor="w", pady=(2, 0))
        f.pack(fill="x", padx=32, pady=(10, 0))

    def _footer(self, parent, back_fn=None, next_fn=None,
                next_label="Continuar  →", next_enabled=True, extra_btns=None):
        ttk.Separator(parent).pack(fill="x", side="bottom")
        f = tk.Frame(parent, bg=BG)
        f.pack(fill="x", padx=32, pady=14, side="bottom")

        if back_fn:
            tk.Button(f, text="← Voltar", command=back_fn,
                      bg=PANEL2, fg=TEXT, activebackground=PANEL, activeforeground=TEXT,
                      relief="flat", font=(FONT, 10), padx=18, pady=9,
                      cursor="hand2").pack(side="left")

        for label, cmd, color in (extra_btns or []):
            tk.Button(f, text=label, command=cmd,
                      bg=PANEL2, fg=TEXT, activebackground=PANEL, activeforeground=TEXT,
                      relief="flat", font=(FONT, 10), padx=14, pady=9,
                      cursor="hand2").pack(side="left", padx=(8, 0))

        nb_ref = [None]
        bg = BLUE if next_enabled else PANEL2
        fg = "white" if next_enabled else TEXT
        st = "normal" if next_enabled else "disabled"
        nb = tk.Button(f, text=next_label, command=next_fn or (lambda: None),
                       bg=bg, fg=fg, activebackground=BLUE2, activeforeground="white",
                       relief="flat", font=(FONT, 11, "bold"),
                       padx=28, pady=11, cursor="hand2",
                       state=st, disabledforeground=TEXT)
        nb.pack(side="right")
        nb_ref[0] = nb
        return nb

    # ── Field helper with inline validation ───────────────────────────────────
    def _field(self, parent, key, label, hint="", secret=False,
               validate_fn=None, width=52):
        block = tk.Frame(parent, bg=BG)
        block.pack(fill="x", pady=6)

        tk.Label(block, text=label, bg=BG, fg=TEXT,
                 font=(FONT, 10, "bold")).pack(anchor="w")

        row = tk.Frame(block, bg=BG)
        row.pack(fill="x", pady=(3, 0))

        var = self._var(key)
        entry = tk.Entry(row, textvariable=var, show="•" if secret else "",
                         bg=PANEL, fg=TEXT, insertbackground=TEXT,
                         relief="flat", font=("Consolas", 10), width=width)
        entry.pack(side="left", ipady=7, padx=(0, 4))

        if secret:
            show_var = tk.BooleanVar(value=False)
            def _toggle(e=entry, sv=show_var):
                sv.set(not sv.get())
                e.config(show="" if sv.get() else "•")
            tk.Button(row, text="👁", command=_toggle,
                      bg=PANEL, fg=DIM, relief="flat",
                      cursor="hand2", font=(FONT, 10),
                      padx=8, pady=6).pack(side="left")

        status = tk.Label(block, text=hint, bg=BG, fg=DIM,
                          font=(FONT, 8), anchor="w")
        status.pack(anchor="w", pady=(2, 0))

        if validate_fn:
            def _on_change(*_):
                val = var.get()
                if not val:
                    status.config(text=hint, fg=MUTED)
                    return
                ok, msg = validate_fn(val)
                status.config(text=msg, fg=GREEN if ok else RED)
            var.trace_add("write", _on_change)
            status.config(fg=MUTED)

        return var, status, entry

    # ── Login card (for Fly + Vercel) ─────────────────────────────────────────
    def _login_card(self, parent, provider, check_cmd, login_fn, after_login=None):
        """Returns a (card_frame, recheck_fn, status_var) tuple."""
        card = tk.Frame(parent, bg=PANEL, pady=14, padx=18)
        card.pack(fill="x", pady=(8, 0))

        top = tk.Frame(card, bg=PANEL)
        top.pack(fill="x")

        icon  = tk.Label(top, text="⏳", bg=PANEL, font=(FONT, 16), width=3)
        icon.pack(side="left")

        info  = tk.Frame(top, bg=PANEL)
        info.pack(side="left", fill="x", expand=True)
        lbl   = tk.Label(info, text=f"Verificando conexão com {provider}…",
                         bg=PANEL, fg=MUTED, font=(FONT, 11, "bold"))
        lbl.pack(anchor="w")
        sub   = tk.Label(info, text="", bg=PANEL, fg=DIM, font=(FONT, 9))
        sub.pack(anchor="w")

        btn   = tk.Button(top, text=f"Entrar no {provider}",
                          bg=DIM, fg="white", relief="flat",
                          font=(FONT, 10, "bold"), padx=14, pady=8,
                          cursor="hand2", state="disabled")
        btn.pack(side="right")

        logged_in = [False]

        def _recheck(notify_fn=None):
            result = _check_output(check_cmd)
            ok = result is not None
            logged_in[0] = ok
            def _update():
                if ok:
                    icon.config(text="✅", fg=GREEN)
                    lbl.config(text=f"Conectado no {provider}", fg=GREEN)
                    sub.config(text=result or "", fg=DIM)
                    btn.config(text="Trocar conta", bg=PANEL2, state="normal",
                               command=lambda: _do_logout_login())
                else:
                    icon.config(text="❌", fg=RED)
                    lbl.config(text=f"Não conectado no {provider}", fg=MUTED)
                    sub.config(text="Clique no botão para entrar com o navegador", fg=DIM)
                    btn.config(text=f"Entrar no {provider}", bg=BLUE, state="normal",
                               command=_do_login)
                if notify_fn:
                    notify_fn(ok)
            self.after(0, _update)
            return ok

        def _do_login():
            btn.config(state="disabled", bg=DIM, text="Aguardando login…")
            lbl.config(text=f"Faça login no {provider} e aguarde…", fg=YELLOW)
            sub.config(text="A janela preta fechará sozinha quando concluído", fg=DIM)
            threading.Thread(target=lambda: (login_fn(), _refresh_path(),
                                             _recheck(after_login)), daemon=True).start()

        def _do_logout_login():
            _do_login()

        btn.config(state="normal", bg=BLUE, command=_do_login)
        threading.Thread(target=lambda: _recheck(after_login), daemon=True).start()

        return card, _recheck, logged_in

    # ══════════════════════════════════════════════════════════════════════════
    # Tela 0 — Welcome
    # ══════════════════════════════════════════════════════════════════════════
    def _page_welcome(self):
        p = tk.Frame(self, bg=BG)

        body = tk.Frame(p, bg=BG)
        body.pack(fill="both", expand=True)

        try:
            _pil_logo = Image.open(_asset("finance-bot-logo.png")).convert("RGBA")
            _pil_logo = _pil_logo.resize((120, 120), Image.LANCZOS)
            _tk_logo  = ImageTk.PhotoImage(_pil_logo)
            logo_lbl  = tk.Label(body, image=_tk_logo, bg=BG)
            logo_lbl.image = _tk_logo   # mantém referência
            logo_lbl.pack(pady=(44, 10))
        except Exception:
            c = tk.Canvas(body, width=100, height=100, bg=BG, highlightthickness=0)
            c.pack(pady=(52, 14))
            c.create_oval(4, 4, 96, 96, fill="white", outline="")
            c.create_text(50, 50, text="$", font=(FONT, 46, "bold"), fill=BG)

        tk.Label(body, text="Finance Bot", bg=BG, fg=TEXT,
                 font=(FONT, 32, "bold")).pack()
        tk.Label(body, text="Assistente de setup", bg=BG, fg=BLUE,
                 font=(FONT, 13)).pack(pady=(2, 20))

        info = tk.Frame(body, bg=PANEL, padx=28, pady=16)
        info.pack(padx=60, fill="x")
        for icon, line in [
            ("📋", "Você vai criar 5 contas gratuitas, uma por vez"),
            ("⚡", "O assistente faz logins e publicações automaticamente"),
            ("⏱", "Tempo estimado: 15–20 minutos"),
        ]:
            row = tk.Frame(info, bg=PANEL)
            row.pack(anchor="w", pady=3)
            tk.Label(row, text=icon, bg=PANEL, font=(FONT, 11), width=3).pack(side="left")
            tk.Label(row, text=line, bg=PANEL, fg=MUTED, font=(FONT, 10)).pack(side="left")

        self._footer(p, next_fn=lambda: self._show(self._page_prereqs),
                     next_label="Começar  →")
        return p

    # ══════════════════════════════════════════════════════════════════════════
    # Tela 1 — Pré-requisitos
    # ══════════════════════════════════════════════════════════════════════════
    def _page_prereqs(self):
        p = tk.Frame(self, bg=BG)
        self._header(p, "Preparando seu computador",
                     "Vamos instalar as ferramentas necessárias.", phase=0)

        nf = tk.Frame(p, bg=PANEL2)
        nf.pack(fill="x", padx=32, pady=(10, 0))
        tk.Label(nf,
                 text="ℹ️  Novas janelas poderão ser abertas durante as instalações, "
                      "e confirmações poderão ser solicitadas.",
                 bg=PANEL2, fg=MUTED, font=(FONT, 9), pady=8, padx=14,
                 justify="left", wraplength=680).pack(anchor="w")

        nb = self._footer(p,
                          back_fn=lambda: self._show(self._page_welcome),
                          next_fn=lambda: self._show(self._page_clone),
                          next_enabled=False)

        body = tk.Frame(p, bg=BG)
        body.pack(fill="both", expand=True, padx=32, pady=(12, 0))

        # Log bufferizado — popup só abre quando o usuário pede
        _log_buf = []   # lista de (text, tag)
        _popup   = [None]

        def _log(text, tag=None):
            _log_buf.append((text, tag))
            if _popup[0] and _popup[0].winfo_exists():
                box = _popup[0]._log_box
                box.config(state="normal")
                box.insert("end", text + "\n", tag or "")
                box.see("end")
                box.config(state="disabled")

        def _open_logs():
            if _popup[0] and _popup[0].winfo_exists():
                _popup[0].lift()
                return
            win = tk.Toplevel(self)
            win.title("Detalhes da instalação")
            win.geometry("560x300")
            win.configure(bg=BG)
            win.resizable(True, True)
            box = scrolledtext.ScrolledText(win, bg=PANEL, fg=MUTED,
                                            font=("Consolas", 9), relief="flat",
                                            state="disabled")
            box.pack(fill="both", expand=True, padx=10, pady=10)
            box.tag_config("ok",  foreground=GREEN)
            box.tag_config("err", foreground=RED)
            box.config(state="normal")
            for t, tg in _log_buf:
                box.insert("end", t + "\n", tg or "")
            box.see("end")
            box.config(state="disabled")
            win._log_box = box
            _popup[0] = win

        items           = []
        all_do_fns      = []
        verified        = set()
        v_lock          = threading.Lock()
        install_all_ref = [None]   # preenchido depois, referenciado em _mark_verified

        def _mark_verified(chk_fn):
            with v_lock:
                verified.add(chk_fn)
                all_done = len(verified) == len(items)
            if all_done:
                self.after(0, lambda: nb.config(state="normal", bg=BLUE, fg="white"))
                if install_all_ref[0]:
                    self.after(0, lambda: install_all_ref[0].config(
                        state="disabled", bg=DIM,
                        text="✓  Tudo instalado"))

        def _recheck_all(on_done=None):
            pending = [len(items)]
            lock    = threading.Lock()

            def _check_one(icon_lbl, status_lbl, act_btn, chk_fn):
                ok = chk_fn()
                if ok:
                    _mark_verified(chk_fn)
                with lock:
                    pending[0] -= 1
                    finished = pending[0] == 0
                self.after(0, lambda i=icon_lbl, sl=status_lbl, b=act_btn, o=ok: (
                    i.config(text="✅" if o else "❌", fg=GREEN if o else RED),
                    sl.config(text="Instalado" if o else "Pendente",
                              fg=GREEN if o else MUTED),
                    b.config(state="disabled" if o else "normal",
                             bg=DIM if o else BLUE, fg="white"),
                ))
                if finished and on_done:
                    self.after(0, on_done)

            for icon_lbl, status_lbl, act_btn, chk_fn in items:
                threading.Thread(target=_check_one,
                                 args=(icon_lbl, status_lbl, act_btn, chk_fn),
                                 daemon=True).start()

        SPIN_FRAMES = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]

        def _make_row(name, note, chk_fn, act_fn, act_label):
            row = tk.Frame(body, bg=PANEL, pady=8, padx=16)
            row.pack(fill="x", pady=3)

            top = tk.Frame(row, bg=PANEL)
            top.pack(fill="x")

            left = tk.Frame(top, bg=PANEL)
            left.pack(side="left", fill="x", expand=True)
            icon = tk.Label(left, text="⏳", bg=PANEL, fg=MUTED, font=(FONT, 15), width=3)
            icon.pack(side="left")
            txt = tk.Frame(left, bg=PANEL)
            txt.pack(side="left")
            name_lbl = tk.Label(txt, text=name, bg=PANEL, fg=TEXT, font=(FONT, 11, "bold"))
            name_lbl.pack(anchor="w")
            st = tk.Label(txt, text="verificando…", bg=PANEL, fg=DIM, font=(FONT, 9))
            st.pack(anchor="w")

            # Spinner state (um por row)
            spin = {"running": False, "id": None, "frame": 0}

            def _start_spin():
                spin["running"] = True
                spin["frame"]   = 0
                def _tick():
                    if not spin["running"]:
                        return
                    name_lbl.config(
                        text=f"{name}  {SPIN_FRAMES[spin['frame'] % len(SPIN_FRAMES)]}",
                        fg=YELLOW)
                    spin["frame"] += 1
                    spin["id"] = self.after(80, _tick)
                _tick()

            def _stop_spin():
                spin["running"] = False
                if spin["id"]:
                    self.after_cancel(spin["id"])
                    spin["id"] = None
                name_lbl.config(text=name, fg=TEXT)

            btn_ref = [None]

            def _do(af=act_fn, my_chk=chk_fn):
                btn_ref[0].config(state="disabled", bg=DIM, text="Instalando…")
                _start_spin()

                def _run():
                    af(_log)
                    _refresh_path()
                    self.after(0, lambda: st.config(text="Verificando…", fg=YELLOW))
                    ok = my_chk()
                    if ok:
                        _mark_verified(my_chk)
                    self.after(0, lambda o=ok: (
                        _stop_spin(),
                        icon.config(text="✅" if o else "❌", fg=GREEN if o else RED),
                        st.config(text="Instalado" if o else "Erro — tente novamente",
                                  fg=GREEN if o else RED),
                        btn_ref[0].config(state="disabled" if o else "normal",
                                          bg=DIM if o else BLUE, fg="white",
                                          text=act_label),
                    ))

                threading.Thread(target=_run, daemon=True).start()

            btn = tk.Button(top, text=act_label, command=_do,
                            bg=BLUE, fg="white", relief="flat",
                            font=(FONT, 9, "bold"), padx=12, pady=6, cursor="hand2",
                            disabledforeground="white")
            btn.pack(side="right")
            btn_ref[0] = btn
            items.append((icon, st, btn, chk_fn))
            all_do_fns.append(_do)

        def _winget_run(pkg_id, log_fn):
            """Roda winget e loga resultado. Retorna True se sucesso."""
            r = subprocess.run(
                ["winget", "install", "-e", "--id", pkg_id,
                 "--accept-source-agreements", "--accept-package-agreements", "--silent"],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", creationflags=NO_WIN)
            if r.returncode == 0:
                log_fn(f"winget: concluído (código 0).", "ok")
            else:
                log_fn(f"winget: falhou (código {r.returncode}).", "err")
                out = (r.stdout or "").strip()
                if out:
                    for line in out.splitlines()[-6:]:   # últimas 6 linhas do output
                        log_fn(f"  {line}")
            return r.returncode == 0

        def _inst_fly(log_fn):
            log_fn("Instalando Fly CLI via winget…")
            ok = _winget_run("Fly.flyctl", log_fn)
            if not ok:
                log_fn("Método alternativo: script oficial do Fly.io…")
                r2 = subprocess.run(
                    ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command",
                     "iwr https://fly.io/install.ps1 -useb | iex"],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", creationflags=NO_WIN)
                if r2.returncode == 0:
                    log_fn("Script do Fly.io: concluído.", "ok")
                else:
                    log_fn(f"Script do Fly.io: falhou (código {r2.returncode}).", "err")
                    out = (r2.stdout or "").strip()
                    if out:
                        for line in out.splitlines()[-6:]:
                            log_fn(f"  {line}")
            log_fn("Verificando Fly CLI no PATH e em locais de instalação…")

        def _inst_node(log_fn):
            log_fn("Instalando Node.js via winget…")
            ok = _winget_run("OpenJS.NodeJS.LTS", log_fn)
            if ok:
                log_fn("Verificando Node.js…")
                v = _check_output(["node", "--version"])
                log_fn(f"node {v}" if v else "node não encontrado no PATH ainda.", "ok" if v else None)

        def _inst_git(log_fn):
            log_fn("Instalando Git via winget…")
            ok = _winget_run("Git.Git", log_fn)
            if not ok:
                log_fn("Abrindo instalador manual em git-scm.com…")
                webbrowser.open("https://git-scm.com/download/win")
                log_fn("Instale o Git manualmente e clique em 'Instalar agora' para verificar.", "err")
                return
            log_fn("Verificando Git…")
            v = _check_output(["git", "--version"])
            log_fn(v if v else "git não encontrado no PATH ainda.", "ok" if v else None)

        def _chk_fly():
            # 1. Tenta pelo PATH (winget coloca lá)
            if _check(["fly", "version"]) or _check(["flyctl", "version"]):
                return True
            # 2. Script PS instala em ~/.fly/bin — adiciona ao PATH e tenta novamente
            up = os.environ.get("USERPROFILE", "")
            candidates = [
                os.path.join(up, ".fly", "bin"),
                os.path.join(os.environ.get("LOCALAPPDATA", ""), "fly", "bin"),
            ]
            for fly_bin in candidates:
                if os.path.isdir(fly_bin):
                    if fly_bin not in os.environ.get("PATH", ""):
                        os.environ["PATH"] = fly_bin + ";" + os.environ["PATH"]
                    if _check(["fly", "version"]) or _check(["flyctl", "version"]):
                        return True
            # 3. Binário existe no disco mas PATH ainda não atualizado — considera instalado
            for fly_bin in candidates:
                for name in ("fly.exe", "flyctl.exe"):
                    if os.path.isfile(os.path.join(fly_bin, name)):
                        return True
            return False

        _make_row("Fly CLI",  "Publica o backend e o bot",
                  _chk_fly, _inst_fly, "Instalar agora")
        _make_row("Node.js",  "Publica o painel web",
                  lambda: _check(["node", "--version"]), _inst_node, "Instalar agora")
        _make_row("Git",      "Faz o download e as atualizações do bot",
                  lambda: _check(["git", "--version"]), _inst_git, "Instalar agora")

        # ── Botão de logs (abre popup sob demanda) ────────────────────────────
        tk.Button(body, text="▸  Ver logs de instalação",
                  command=_open_logs,
                  bg=BG, fg=DIM, relief="flat",
                  font=(FONT, 9), cursor="hand2", anchor="w",
                  activeforeground=MUTED, activebackground=BG,
                  ).pack(anchor="w", pady=(10, 0))

        # ── Botão "Instalar tudo" ──────────────────────────────────────────────
        # install_all_ref é definido cedo (no topo), _mark_verified já o conhece.

        def _install_all():
            with v_lock:
                pending_indices = [i for i, (_, _, _, chk_fn) in enumerate(items)
                                   if chk_fn not in verified]
            if not pending_indices:
                return
            install_all_ref[0].config(state="disabled", bg=DIM, text="Instalando…")
            # _do() é seguro chamar da thread principal — ela mesma abre bg threads
            for i in pending_indices:
                all_do_fns[i]()

        install_all_ref[0] = tk.Button(
            body, text="⬇  Instalar tudo",
            command=_install_all,
            bg=GREEN, fg="white", activebackground="#16a34a", activeforeground="white",
            relief="flat", font=(FONT, 10, "bold"),
            padx=20, pady=9, cursor="hand2",
            disabledforeground="white",
        )
        install_all_ref[0].pack(anchor="e", pady=(10, 0))

        def _on_initial_check():
            with v_lock:
                all_ok = len(verified) == len(items)
            if install_all_ref[0]:
                install_all_ref[0].config(
                    state="disabled" if all_ok else "normal",
                    bg=DIM if all_ok else GREEN,
                    text="✓  Tudo instalado" if all_ok else "⬇  Instalar tudo",
                )

        _recheck_all(on_done=_on_initial_check)
        return p

    # ══════════════════════════════════════════════════════════════════════════
    # Tela 1b — Clone do repositório
    # ══════════════════════════════════════════════════════════════════════════
    def _page_clone(self):
        p = tk.Frame(self, bg=BG)
        self._header(p, "Baixando o Finance Bot",
                     "Escolha onde instalar — vamos buscar a versão mais recente.", phase=0)

        nb = self._footer(p,
                          back_fn=lambda: self._show(self._page_prereqs),
                          next_fn=lambda: None,
                          next_label="Baixar e instalar  →",
                          next_enabled=False)

        body = tk.Frame(p, bg=BG)
        body.pack(fill="both", expand=True, padx=32, pady=(14, 0))

        # Folder picker card
        folder_card = tk.Frame(body, bg=PANEL, pady=14, padx=16)
        folder_card.pack(fill="x")
        tk.Label(folder_card, text="Pasta de instalação", bg=PANEL, fg=TEXT,
                 font=(FONT, 10, "bold")).pack(anchor="w")

        row = tk.Frame(folder_card, bg=PANEL)
        row.pack(fill="x", pady=(6, 0))

        path_var = tk.StringVar(value=r"C:\Program Files\FinanceBot")

        path_entry = tk.Entry(row, textvariable=path_var, bg=PANEL2, fg=TEXT,
                              insertbackground=TEXT, relief="flat",
                              font=("Consolas", 10), width=42)
        path_entry.pack(side="left", ipady=7, padx=(0, 8))

        def _browse():
            d = filedialog.askdirectory(initialdir="C:\\",
                                        title="Escolha a pasta de instalação")
            if d:
                path_var.set(os.path.normpath(d))
            _validate()

        browse_btn = tk.Button(row, text="Escolher…", command=_browse,
                               bg=PANEL2, fg=TEXT, activebackground=PANEL, activeforeground=TEXT,
                               relief="flat", font=(FONT, 10), padx=12, pady=6,
                               cursor="hand2")
        browse_btn.pack(side="left")

        status_lbl = tk.Label(folder_card,
                               text="A pasta deve estar vazia ou não existir.",
                               bg=PANEL, fg=DIM, font=(FONT, 8))
        status_lbl.pack(anchor="w", pady=(4, 0))

        # Progress log (hidden until download starts)
        log_wrap = tk.Frame(body, bg=BG)
        log_box = scrolledtext.ScrolledText(log_wrap, bg=PANEL, fg=MUTED,
                                            font=("Consolas", 8), relief="flat",
                                            state="disabled", height=7)
        log_box.pack(fill="x")
        log_box.tag_config("ok",  foreground=GREEN)
        log_box.tag_config("err", foreground=RED)

        def _log(text, tag=None):
            log_box.config(state="normal")
            log_box.insert("end", text + "\n", tag or "")
            log_box.see("end")
            log_box.config(state="disabled")

        def _validate(*_):
            path = path_var.get().strip()
            if not path:
                status_lbl.config(text="Informe um caminho.", fg=MUTED)
                nb.config(state="disabled", bg=PANEL2, fg=TEXT)
                return
            if os.path.exists(path) and os.listdir(path):
                status_lbl.config(text="✗  Pasta já existe e não está vazia.", fg=RED)
                nb.config(state="disabled", bg=PANEL2, fg=TEXT)
            else:
                status_lbl.config(text="✓  Pronto para instalar.", fg=GREEN)
                nb.config(state="normal", bg=BLUE, fg="white")

        def _do_clone():
            path = path_var.get().strip()
            nb.config(state="disabled", bg=PANEL2, fg=TEXT, text="Baixando…")
            path_entry.config(state="disabled")
            log_wrap.pack(fill="x", pady=(12, 0))

            def _thread():
                self.after(0, lambda: _log("Verificando versão mais recente…"))
                try:
                    req = urllib.request.Request(
                        f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest",
                        headers={"Accept": "application/vnd.github+json",
                                 "User-Agent": "FinanceBotSetup/1.0"},
                    )
                    with urllib.request.urlopen(req, timeout=15) as r:
                        data = json.loads(r.read().decode())
                    tag     = data["tag_name"]
                    version = tag.lstrip("v")
                    self.after(0, lambda: _log(f"Versão mais recente: {tag}", "ok"))
                except Exception as e:
                    self.after(0, lambda: (
                        _log(f"Erro ao buscar versão: {e}", "err"),
                        nb.config(state="normal", bg=BLUE, fg="white",
                                  text="Tentar novamente  →"),
                        path_entry.config(state="normal"),
                    ))
                    return

                self.after(0, lambda: _log("Clonando repositório (pode levar alguns minutos)…"))
                try:
                    proc = _popen(
                        ["git", "-c", "advice.detachedHead=false",
                         "clone", "--branch", tag,
                         f"https://github.com/{GITHUB_REPO}", path]
                    )
                    for line in proc.stdout:
                        line = line.rstrip()
                        self.after(0, lambda l=line: _log(l))
                    proc.wait()
                    ok = proc.returncode == 0
                except Exception as e:
                    ok = False
                    self.after(0, lambda: _log(f"Erro: {e}", "err"))

                if ok:
                    _set_install_path(path)
                    self._info["version"]      = version
                    self._info["install_path"] = path
                    self.after(0, lambda: (
                        _log(f"✓  Finance Bot {tag} instalado em {path}", "ok"),
                        browse_btn.config(state="disabled", bg=DIM),
                        nb.config(state="normal", bg=BLUE, fg="white",
                                  text="Continuar  →",
                                  command=lambda: self._show(self._page_supabase)),
                    ))
                else:
                    self.after(0, lambda: (
                        _log("Falha no download. Verifique sua conexão e tente novamente.", "err"),
                        nb.config(state="normal", bg=BLUE, fg="white",
                                  text="Tentar novamente  →",
                                  command=_do_clone),
                        path_entry.config(state="normal"),
                        browse_btn.config(state="normal", bg=PANEL2),
                    ))

            threading.Thread(target=_thread, daemon=True).start()

        path_var.trace_add("write", _validate)
        nb.config(command=_do_clone)
        _validate()
        return p

    # ══════════════════════════════════════════════════════════════════════════
    # Tela 2a — Supabase: Project URL
    # ══════════════════════════════════════════════════════════════════════════
    def _page_supabase(self):
        p = tk.Frame(self, bg=BG)
        self._header(p, "Supabase — banco de dados",
                     "Siga o passo a passo abaixo para criar o projeto.",
                     phase=1, provider_idx=0)

        def _val_url(v):
            v = v.strip().rstrip("/")
            if re.match(r'^https://[a-z0-9]{16,26}\.supabase\.co$', v):
                return True, "✓  URL válida"
            return False, "✗  Cole a URL do projeto — ex:  https://abcdefghij.supabase.co"

        def _val_pass(v):
            v = v.strip()
            if len(v) >= 8:
                return True, "✓  Senha registrada"
            return False, "✗  Cole a senha gerada no passo 5"

        nb = self._footer(p,
                          back_fn=lambda: self._show(self._page_clone),
                          next_fn=lambda: self._show(self._page_supabase_keys),
                          next_enabled=False)

        def _refresh_nb(*_):
            raw = self._var("SUPABASE_URL").get().strip().rstrip("/")
            ok_url, _ = _val_url(raw)
            ok_pass, _ = _val_pass(self._var("SUPABASE_DB_PASSWORD").get())
            ok = ok_url and ok_pass
            nb.config(state="normal" if ok else "disabled",
                      bg=BLUE if ok else PANEL2,
                      fg="white" if ok else TEXT)
            if ok_url:
                m = re.match(r'^https://([a-z0-9]+)\.supabase\.co$', raw)
                if m:
                    self._var("SUPABASE_PROJECT_ID").set(m.group(1))

        body = tk.Frame(p, bg=BG)
        body.pack(fill="both", expand=True, padx=32, pady=(14, 0))

        instr = tk.Frame(body, bg=PANEL, pady=10, padx=16)
        instr.pack(fill="x")

        for num, text, url, btn_label in [
            ("1.", "Abra o supabase.com", "https://supabase.com/dashboard/sign-in", "Abrir supabase.com"),
            ("2.", "Clique em  Start your project  (botão verde)", None, None),
            ("3.", "Clique em  Sign Up  e crie suas credenciais\nConfirme o e-mail (pode estar no lixo eletrônico)", None, None),
            ("4.", "Clique em  Create organization  (botão verde)", None, None),
            ("5.", "Clique em  Generate a password  em  Database password\nClique em  Copy  ao lado da senha e guarde-a — você vai precisar dela na próxima tela\nEm  Region, escolha  South America (São Paulo)\nClique em  Create new project  (botão verde)", None, None),
            ("6.", "Aguarde ~1 minuto para o projeto inicializar", None, None),
            ("7.", "Clique em  Copy  ao lado de  Project URL  e cole abaixo", None, None),
        ]:
            row = tk.Frame(instr, bg=PANEL)
            row.pack(anchor="w", pady=3, fill="x")
            tk.Label(row, text=num, bg=PANEL, fg=BLUE,
                     font=(FONT, 10, "bold"), width=3).pack(side="left", anchor="n")
            col = tk.Frame(row, bg=PANEL)
            col.pack(side="left", fill="x")
            tk.Label(col, text=text, bg=PANEL, fg=MUTED,
                     font=(FONT, 10), justify="left").pack(anchor="w")
            if url and btn_label:
                tk.Button(col, text=btn_label + "  →",
                          command=lambda u=url: webbrowser.open(u),
                          bg=PANEL2, fg="white", relief="flat",
                          font=(FONT, 9, "bold"), padx=10, pady=4,
                          cursor="hand2").pack(anchor="w", pady=(5, 0))

        v, _, _ = self._field(body, "SUPABASE_URL", "URL do projeto",
                               hint="Exemplo:  https://abcdefghij.supabase.co",
                               validate_fn=_val_url)
        v.trace_add("write", _refresh_nb)

        v2, _, _ = self._field(body, "SUPABASE_DB_PASSWORD", "Senha do banco (passo 5)",
                                hint="A senha que você copiou ao clicar em  Generate a password",
                                secret=True, validate_fn=_val_pass)
        v2.trace_add("write", _refresh_nb)
        _refresh_nb()
        return p

    # ══════════════════════════════════════════════════════════════════════════
    # Tela 2b — Supabase: API Key
    # ══════════════════════════════════════════════════════════════════════════
    def _page_supabase_keys(self):
        p = tk.Frame(self, bg=BG)
        self._header(p, "Supabase — chave secreta",
                     "Copie a chave service_role para o assistente acessar o banco.",
                     phase=1, provider_idx=0)

        def _val_key(v):
            v = v.strip()
            if v.startswith("eyJ") and len(v) > 100:
                return True, "✓  Formato correto"
            return False, "✗  Começa com  eyJ  e é bem longa — use a  service_role,  não a  anon"

        nb = self._footer(p,
                          back_fn=lambda: self._show(self._page_supabase),
                          next_fn=lambda: self._show(self._page_supabase_sql),
                          next_enabled=False)

        def _refresh_nb(*_):
            ok, _ = _val_key(self._var("SUPABASE_SERVICE_ROLE_KEY").get())
            nb.config(state="normal" if ok else "disabled",
                      bg=BLUE if ok else PANEL2,
                      fg="white" if ok else TEXT)

        body = tk.Frame(p, bg=BG)
        body.pack(fill="both", expand=True, padx=32, pady=(14, 0))

        # Auto-open button using saved project ID
        proj_id = self._var("SUPABASE_PROJECT_ID").get().strip()
        api_url = f"https://supabase.com/dashboard/project/{proj_id}/settings/api-keys"

        info = tk.Frame(body, bg=PANEL, pady=14, padx=16)
        info.pack(fill="x")
        info_top = tk.Frame(info, bg=PANEL)
        info_top.pack(fill="x")
        col = tk.Frame(info_top, bg=PANEL)
        col.pack(side="left", fill="x", expand=True)
        tk.Label(col, text="1.  Abra a página de chaves do seu projeto",
                 bg=PANEL, fg=MUTED, font=(FONT, 10, "bold")).pack(anchor="w")
        tk.Label(col, text="A página vai abrir direto no seu projeto.",
                 bg=PANEL, fg=DIM, font=(FONT, 9)).pack(anchor="w", pady=(3, 0))
        tk.Button(info_top, text="Abrir API Keys  →",
                  command=lambda: webbrowser.open(api_url),
                  bg=BLUE, fg="white", relief="flat",
                  font=(FONT, 9, "bold"), padx=12, pady=6,
                  cursor="hand2").pack(side="right")

        tk.Frame(info, bg=PANEL2, height=1).pack(fill="x", pady=10)

        tk.Label(info,
                 text="2.  Abra a aba  Legacy anon, service_role API keys\n"
                      "    clique em  Reveal  na  service_role  e a copie",
                 bg=PANEL, fg=MUTED, font=(FONT, 10, "bold"), justify="left").pack(anchor="w")

        v, _, _ = self._field(body, "SUPABASE_SERVICE_ROLE_KEY", "Chave service_role",
                               hint="Começa com  eyJ  e é bem longa",
                               secret=True, validate_fn=_val_key)
        v.trace_add("write", _refresh_nb)
        _refresh_nb()
        return p

    # ══════════════════════════════════════════════════════════════════════════
    # Tela 2c — Supabase: Executar SQL
    # ══════════════════════════════════════════════════════════════════════════
    def _page_supabase_sql(self):
        p = tk.Frame(self, bg=BG)
        self._header(p, "Supabase — tabelas automáticas",
                     "Não é necessária nenhuma ação manual.",
                     phase=1, provider_idx=0)

        self._footer(p,
                     back_fn=lambda: self._show(self._page_supabase_keys),
                     next_fn=lambda: self._show(self._page_telegram_bot))

        body = tk.Frame(p, bg=BG)
        body.pack(fill="both", expand=True, padx=32, pady=(14, 0))

        info = tk.Frame(body, bg=PANEL, pady=20, padx=20)
        info.pack(fill="x")

        tk.Label(info, text="✅  Tudo certo!", bg=PANEL, fg=GREEN,
                 font=(FONT, 14, "bold")).pack(anchor="w")
        tk.Label(info,
                 text="Quando o servidor iniciar pela primeira vez,\n"
                      "as tabelas serão criadas automaticamente no seu banco.\n\n"
                      "Você não precisa abrir o SQL Editor nem colar nenhum código.",
                 bg=PANEL, fg=MUTED, font=(FONT, 10), justify="left").pack(anchor="w", pady=(8, 0))

        return p

    # ══════════════════════════════════════════════════════════════════════════
    # Tela 3a — Telegram: criar bot
    # ══════════════════════════════════════════════════════════════════════════
    def _page_telegram_bot(self):
        p = tk.Frame(self, bg=BG)
        self._header(p, "Telegram — criar o bot",
                     "Vamos criar seu bot via @BotFather e salvar o token.",
                     phase=1, provider_idx=1)

        def _val_token(v):
            v = v.strip()
            if re.match(r'^\d{8,12}:[A-Za-z0-9_-]{30,}$', v):
                return True, "✓  Formato correto"
            return False, "✗  Formato: 123456789:ABCdefGHIjkl..."

        nb = self._footer(p,
                          back_fn=lambda: self._show(self._page_supabase),
                          next_fn=lambda: self._show(self._page_telegram_id),
                          next_enabled=False)

        def _refresh_nb(*_):
            ok, _ = _val_token(self._var("TELEGRAM_BOT_TOKEN").get())
            nb.config(state="normal" if ok else "disabled",
                      bg=BLUE if ok else PANEL2,
                      fg="white" if ok else TEXT)

        body = tk.Frame(p, bg=BG)
        body.pack(fill="both", expand=True, padx=32, pady=(14, 0))

        instr = tk.Frame(body, bg=PANEL, pady=14, padx=16)
        instr.pack(fill="x")

        for num, text, url, btn_label in [
            ("1.", "Abra o @BotFather no Telegram", "https://t.me/BotFather", "Abrir BotFather"),
            ("2.", "Envie  /newbot  e siga as instruções\nEscolha qualquer nome de exibição\nO username deve terminar em  bot", None, None),
            ("3.", "O BotFather vai te enviar um token.\nCopie e cole abaixo.", None, None),
        ]:
            row = tk.Frame(instr, bg=PANEL)
            row.pack(anchor="w", pady=5, fill="x")
            tk.Label(row, text=num, bg=PANEL, fg=BLUE,
                     font=(FONT, 10, "bold"), width=3).pack(side="left", anchor="n")
            col = tk.Frame(row, bg=PANEL)
            col.pack(side="left", fill="x")
            tk.Label(col, text=text, bg=PANEL, fg=MUTED,
                     font=(FONT, 10), justify="left").pack(anchor="w")
            if url and btn_label:
                tk.Button(col, text=btn_label + "  →",
                          command=lambda u=url: webbrowser.open(u),
                          bg=PANEL2, fg="white", relief="flat",
                          font=(FONT, 9, "bold"), padx=10, pady=4,
                          cursor="hand2").pack(anchor="w", pady=(5, 0))

        v, _, _ = self._field(body, "TELEGRAM_BOT_TOKEN", "Token do bot",
                               hint="Formato:  123456789:ABCdefGHIjklMNOpqr...",
                               secret=True, validate_fn=_val_token)
        v.trace_add("write", _refresh_nb)
        _refresh_nb()

        # Dica de uso em grupo
        tip = tk.Frame(body, bg=PANEL2, pady=10, padx=14)
        tip.pack(fill="x", pady=(12, 0))
        tk.Label(tip,
                 text="💡  Quer usar o bot em um grupo do Telegram com vários usuários?",
                 bg=PANEL2, fg=TEXT, font=(FONT, 9, "bold"), justify="left").pack(anchor="w")
        tk.Label(tip,
                 text="No @BotFather, selecione seu bot e acesse:\n"
                      "Bot Settings  →  Group Privacy  →  Turn off\n"
                      "Assim o bot consegue ler mensagens dentro de grupos.",
                 bg=PANEL2, fg=MUTED, font=(FONT, 9), justify="left").pack(anchor="w", pady=(4, 0))

        return p

    # ══════════════════════════════════════════════════════════════════════════
    # Tela 3b — Telegram: descobrir ID
    # ══════════════════════════════════════════════════════════════════════════
    def _page_telegram_id(self):
        p = tk.Frame(self, bg=BG)
        self._header(p, "Telegram — seu ID de usuário",
                     "Descubra o número que identifica sua conta no Telegram.",
                     phase=1, provider_idx=1)

        def _val_uid(v):
            v = v.strip()
            if re.match(r'^\d+(\s*,\s*\d+)*$', v):
                return True, "✓  Formato correto"
            return False, "✗  Apenas números — vírgula para múltiplos usuários"

        nb = self._footer(p,
                          back_fn=lambda: self._show(self._page_telegram_bot),
                          next_fn=lambda: self._show(self._page_groq),
                          next_enabled=False)

        def _refresh_nb(*_):
            ok, _ = _val_uid(self._var("TELEGRAM_USER_IDS").get())
            nb.config(state="normal" if ok else "disabled",
                      bg=BLUE if ok else PANEL2,
                      fg="white" if ok else TEXT)

        body = tk.Frame(p, bg=BG)
        body.pack(fill="both", expand=True, padx=32, pady=(14, 0))

        instr = tk.Frame(body, bg=PANEL, pady=14, padx=16)
        instr.pack(fill="x")

        for num, text, url, btn_label in [
            ("1.", "Abra o @userinfobot no Telegram", "https://t.me/userinfobot", "Abrir userinfobot"),
            ("2.", "Envie qualquer mensagem ou clique em START", None, None),
            ("3.", "Ele vai te responder com seu ID numérico.\nCopie e cole abaixo.", None, None),
        ]:
            row = tk.Frame(instr, bg=PANEL)
            row.pack(anchor="w", pady=5, fill="x")
            tk.Label(row, text=num, bg=PANEL, fg=BLUE,
                     font=(FONT, 10, "bold"), width=3).pack(side="left", anchor="n")
            col = tk.Frame(row, bg=PANEL)
            col.pack(side="left", fill="x")
            tk.Label(col, text=text, bg=PANEL, fg=MUTED,
                     font=(FONT, 10), justify="left").pack(anchor="w")
            if url and btn_label:
                tk.Button(col, text=btn_label + "  →",
                          command=lambda u=url: webbrowser.open(u),
                          bg=PANEL2, fg="white", relief="flat",
                          font=(FONT, 9, "bold"), padx=10, pady=4,
                          cursor="hand2").pack(anchor="w", pady=(5, 0))

        tip = tk.Frame(body, bg=PANEL2, pady=10, padx=14)
        tip.pack(fill="x", pady=(12, 0))
        tk.Label(tip,
                 text="⚠️  Somente os IDs listados aqui conseguem usar o bot.",
                 bg=PANEL2, fg=TEXT, font=(FONT, 9, "bold"), justify="left").pack(anchor="w")
        tk.Label(tip,
                 text="Se outra pessoa tentar mandar mensagem e o ID dela não estiver na lista,\n"
                      "o bot simplesmente não vai responder.\n"
                      "Adicione todos os usuários agora, separando os IDs por vírgula.",
                 bg=PANEL2, fg=MUTED, font=(FONT, 9), justify="left").pack(anchor="w", pady=(4, 0))

        v, _, _ = self._field(body, "TELEGRAM_USER_IDS", "IDs de usuário (todos que vão usar o bot)",
                               hint="Apenas números, ex: 123456789",
                               validate_fn=_val_uid)
        v.trace_add("write", _refresh_nb)
        _refresh_nb()
        return p

    # ══════════════════════════════════════════════════════════════════════════
    # Tela 4 — Groq
    # ══════════════════════════════════════════════════════════════════════════
    def _page_groq(self):
        p = tk.Frame(self, bg=BG)
        self._header(p, "Groq — inteligência artificial",
                     "A IA que lê suas mensagens e identifica gastos automaticamente.",
                     phase=1, provider_idx=2)

        def _val_key(v):
            v = v.strip()
            if v.startswith("gsk_") and len(v) > 40:
                return True, "✓  Formato correto"
            return False, "✗  Deve começar com  gsk_"

        nb = self._footer(p,
                          back_fn=lambda: self._show(self._page_telegram_id),
                          next_fn=lambda: self._show(self._page_fly),
                          next_enabled=False)

        def _refresh_nb(*_):
            ok, _ = _val_key(self._var("GROQ_API_KEY").get())
            nb.config(state="normal" if ok else "disabled",
                      bg=BLUE if ok else PANEL2,
                      fg="white" if ok else MUTED)

        body = tk.Frame(p, bg=BG)
        body.pack(fill="both", expand=True, padx=32, pady=(14, 0))

        instr = tk.Frame(body, bg=PANEL, pady=12, padx=16)
        instr.pack(fill="x")

        for num, text, url, btn_label in [
            ("1.", "Crie sua conta gratuita", "https://console.groq.com", "Abrir console.groq.com"),
            ("2.", "No menu lateral, clique em  API Keys", "https://console.groq.com/keys", "Abrir API Keys"),
            ("3.", "Clique em  Create API Key, dê um nome (ex: finance-bot)\n"
                   "No campo de validade, selecione  No expiration\n"
                   "⚠️  A chave aparece UMA VEZ SÓ — copie antes de fechar", None, None),
        ]:
            row = tk.Frame(instr, bg=PANEL)
            row.pack(anchor="w", pady=3, fill="x")
            tk.Label(row, text=num, bg=PANEL, fg=BLUE,
                     font=(FONT, 9, "bold"), width=3).pack(side="left", anchor="n")
            col = tk.Frame(row, bg=PANEL)
            col.pack(side="left")
            tk.Label(col, text=text, bg=PANEL, fg=MUTED,
                     font=(FONT, 9), justify="left").pack(anchor="w")
            if url and btn_label:
                tk.Button(col, text=btn_label + "  →",
                          command=lambda u=url: webbrowser.open(u),
                          bg=PANEL2, fg="white", relief="flat",
                          font=(FONT, 8, "bold"), padx=8, pady=3,
                          cursor="hand2").pack(anchor="w", pady=(3, 0))

        v, _, _ = self._field(body, "GROQ_API_KEY", "Chave da API",
                               hint="Começa com  gsk_...  (bem longa)",
                               secret=True, validate_fn=_val_key)
        v.trace_add("write", _refresh_nb)
        _refresh_nb()

        return p

    # ══════════════════════════════════════════════════════════════════════════
    # Tela 5 — Fly.io
    # ══════════════════════════════════════════════════════════════════════════
    def _page_fly(self):
        p = tk.Frame(self, bg=BG)
        self._header(p, "Fly.io — onde o bot vai rodar",
                     "Hospedagem 24/7 do backend e do bot Telegram. Gratuito.",
                     phase=1, provider_idx=3)

        def _val_name(v):
            v = v.strip()
            if re.match(r'^[a-z0-9][a-z0-9-]{2,28}[a-z0-9]$', v):
                return True, "✓  Nome válido"
            return False, "✗  Use letras minúsculas, números e hífen (4–30 caracteres)"

        fly_ok = [False]
        nb = self._footer(p,
                          back_fn=lambda: self._show(self._page_groq),
                          next_fn=lambda: self._show(self._page_vercel_login),
                          next_enabled=False)

        def _refresh_nb(*_):
            ok1, _ = _val_name(self._var("BACKEND_APP").get())
            ok2, _ = _val_name(self._var("BOT_APP").get())
            ok = fly_ok[0] and ok1 and ok2
            nb.config(state="normal" if ok else "disabled",
                      bg=BLUE if ok else PANEL2,
                      fg="white" if ok else MUTED)

        body = tk.Frame(p, bg=BG)
        body.pack(fill="both", expand=True, padx=32, pady=(14, 0))

        # Zone 1 — criar conta
        zone1 = tk.Frame(body, bg=PANEL, pady=10, padx=14)
        zone1.pack(fill="x")
        row1 = tk.Frame(zone1, bg=PANEL)
        row1.pack(fill="x")
        col1 = tk.Frame(row1, bg=PANEL)
        col1.pack(side="left", fill="x", expand=True)
        tk.Label(col1, text="1.  Crie sua conta gratuita no Fly.io", bg=PANEL, fg=MUTED,
                 font=(FONT, 10, "bold")).pack(anchor="w")
        tk.Label(col1,
                 text="⚠️  O Fly.io pede cartão de crédito para confirmar que você é uma pessoa real.\n"
                      "Não há cobrança no plano gratuito — usamos 2 máquinas (limite: 3).\n"
                      "💡  Prefere mais segurança? Crie um cartão virtual com limite de R$ 1 no seu banco.",
                 bg=PANEL, fg=DIM, font=(FONT, 9), justify="left", wraplength=460).pack(anchor="w", pady=(4, 0))
        tk.Button(row1, text="Abrir fly.io  →",
                  command=lambda: webbrowser.open("https://fly.io"),
                  bg=BLUE, fg="white", relief="flat",
                  font=(FONT, 9, "bold"), padx=10, pady=6, cursor="hand2").pack(side="right")

        # Zone 2 — login
        tk.Label(body, text="2.  Conectar o assistente à sua conta",
                 bg=BG, fg=MUTED, font=(FONT, 10, "bold")).pack(anchor="w", pady=(14, 0))

        def _login_fly():
            subprocess.Popen(["cmd.exe", "/c", "fly auth login"],
                             creationflags=subprocess.CREATE_NEW_CONSOLE).wait()

        def _after_fly_login(ok):
            fly_ok[0] = ok
            _refresh_nb()

        self._login_card(body, "Fly.io",
                         ["fly", "auth", "whoami"],
                         _login_fly, _after_fly_login)

        # Zone 3 — app names
        tk.Label(body, text="3.  Escolha nomes para os servidores",
                 bg=BG, fg=MUTED, font=(FONT, 10, "bold")).pack(anchor="w", pady=(14, 0))

        suffix = secrets.token_hex(2)
        self._var("BACKEND_APP", f"finance-api-{suffix}")
        self._var("BOT_APP",     f"finance-bot-{suffix}")

        v1, _, _ = self._field(body, "BACKEND_APP", "Servidor principal (backend)",
                                hint="Endereço: https://NOME.fly.dev",
                                validate_fn=_val_name, width=38)
        v2, _, _ = self._field(body, "BOT_APP", "Servidor do bot Telegram",
                                hint="Endereço: https://NOME.fly.dev",
                                validate_fn=_val_name, width=38)
        v1.trace_add("write", _refresh_nb)
        v2.trace_add("write", _refresh_nb)
        _refresh_nb()

        return p

    # ══════════════════════════════════════════════════════════════════════════
    # Tela 6a — Vercel: login
    # ══════════════════════════════════════════════════════════════════════════
    def _page_vercel_login(self):
        p = tk.Frame(self, bg=BG)
        self._header(p, "Vercel — o painel web",
                     "Onde você acompanha seus gastos pelo navegador. Gratuito.",
                     phase=1, provider_idx=4)

        vercel_ok = [False]
        nb = self._footer(p,
                          back_fn=lambda: self._show(self._page_fly),
                          next_fn=lambda: self._show(self._page_vercel_password),
                          next_enabled=False)

        def _refresh_nb(ok=None):
            if ok is not None:
                vercel_ok[0] = ok
            nb.config(state="normal" if vercel_ok[0] else "disabled",
                      bg=BLUE if vercel_ok[0] else PANEL2,
                      fg="white" if vercel_ok[0] else MUTED)

        body = tk.Frame(p, bg=BG)
        body.pack(fill="both", expand=True, padx=32, pady=(14, 0))

        # Zone 1 — criar conta
        zone1 = tk.Frame(body, bg=PANEL, pady=10, padx=14)
        zone1.pack(fill="x")
        row1 = tk.Frame(zone1, bg=PANEL)
        row1.pack(fill="x")
        col1 = tk.Frame(row1, bg=PANEL)
        col1.pack(side="left", fill="x", expand=True)
        tk.Label(col1, text="1.  Crie sua conta gratuita no Vercel", bg=PANEL, fg=MUTED,
                 font=(FONT, 10, "bold")).pack(anchor="w")
        tk.Label(col1, text="Recomendamos entrar com GitHub. Escolha o plano Hobby (gratuito).",
                 bg=PANEL, fg=DIM, font=(FONT, 9)).pack(anchor="w", pady=(4, 0))
        tk.Button(row1, text="Abrir vercel.com  →",
                  command=lambda: webbrowser.open("https://vercel.com"),
                  bg=BLUE, fg="white", relief="flat",
                  font=(FONT, 9, "bold"), padx=10, pady=6, cursor="hand2").pack(side="right")

        # Zone 2 — login
        tk.Label(body, text="2.  Conectar o assistente à sua conta",
                 bg=BG, fg=MUTED, font=(FONT, 10, "bold")).pack(anchor="w", pady=(14, 0))

        def _login_vercel():
            subprocess.Popen(
                ["cmd.exe", "/c", "npx vercel login"],
                env={**os.environ, "NO_UPDATE_NOTIFIER": "1"},
                creationflags=subprocess.CREATE_NEW_CONSOLE
            ).wait()

        self._login_card(body, "Vercel",
                         ["cmd.exe", "/c", "npx vercel whoami"],
                         _login_vercel, _refresh_nb)

        tk.Label(body,
                 text="Siga as instruções no navegador para fazer login.\n"
                      "Se a janela preta perguntar sobre atualização, pressione  N  e  Enter.",
                 bg=BG, fg=DIM, font=(FONT, 9), justify="left").pack(anchor="w", pady=(8, 0))

        return p

    # ══════════════════════════════════════════════════════════════════════════
    # Tela 6b — Vercel: senha de acesso
    # ══════════════════════════════════════════════════════════════════════════
    def _page_vercel_password(self):
        p = tk.Frame(self, bg=BG)
        self._header(p, "Vercel — senha do painel",
                     "Defina a senha para acessar o painel web.",
                     phase=1, provider_idx=4)

        def _val_pw(v):
            if len(v) >= 8:
                return True, "✓  Senha forte"
            if len(v) >= 6:
                return True, "✓  Tamanho OK"
            return False, "✗  Mínimo 6 caracteres"

        nb = self._footer(p,
                          back_fn=lambda: self._show(self._page_vercel_login),
                          next_fn=lambda: self._show(self._page_review),
                          next_enabled=False)

        def _refresh_nb(*_):
            pw1 = self._var("DASHBOARD_PASSWORD").get()
            pw2 = self._var("DASHBOARD_PASSWORD2").get()
            ok = len(pw1) >= 6 and pw1 == pw2
            nb.config(state="normal" if ok else "disabled",
                      bg=BLUE if ok else PANEL2,
                      fg="white" if ok else MUTED)

        body = tk.Frame(p, bg=BG)
        body.pack(fill="both", expand=True, padx=32, pady=(14, 0))

        # Security note
        note = tk.Frame(body, bg=PANEL, pady=12, padx=16)
        note.pack(fill="x")
        tk.Label(note,
                 text="🔐  Use uma senha segura e guarde-a em local seguro.",
                 bg=PANEL, fg=TEXT, font=(FONT, 10, "bold")).pack(anchor="w")
        tk.Label(note,
                 text="Você vai precisar dela toda vez que acessar o painel. Não há recuperação automática.",
                 bg=PANEL, fg=DIM, font=(FONT, 9), wraplength=640, justify="left").pack(anchor="w", pady=(4, 0))

        # Generate button
        gen_btn = [None]

        def _gen_pw():
            pw = secrets.token_urlsafe(16)
            self._var("DASHBOARD_PASSWORD").set(pw)
            self._var("DASHBOARD_PASSWORD2").set(pw)
            self.clipboard_clear()
            self.clipboard_append(pw)
            if gen_btn[0]:
                gen_btn[0].config(text="✓  Copiada para a área de transferência!", fg=GREEN, bg=PANEL2)
                self.after(3000, lambda: gen_btn[0].config(
                    text="⚡  Gerar senha segura e copiar", fg="white", bg=PANEL2))
            _refresh_nb()

        btn_row = tk.Frame(body, bg=BG)
        btn_row.pack(anchor="w", pady=(10, 4))
        gb = tk.Button(btn_row, text="⚡  Gerar senha segura e copiar",
                       command=_gen_pw,
                       bg=PANEL2, fg="white", relief="flat",
                       font=(FONT, 9, "bold"), padx=12, pady=6, cursor="hand2")
        gb.pack(side="left")
        gen_btn[0] = gb

        def _val_match(v):
            pw1 = self._var("DASHBOARD_PASSWORD").get()
            if v == pw1 and len(v) >= 6:
                return True, "✓  Senhas conferem"
            if v and v != pw1:
                return False, "✗  As senhas não conferem"
            return False, ""

        v1, _, _ = self._field(body, "DASHBOARD_PASSWORD", "Senha de acesso",
                                hint="Mínimo 6 caracteres — recomendamos usar o botão acima",
                                secret=True, validate_fn=_val_pw)
        v2, _, _ = self._field(body, "DASHBOARD_PASSWORD2", "Confirmar senha",
                                hint="",
                                secret=True, validate_fn=_val_match)
        v1.trace_add("write", _refresh_nb)
        v2.trace_add("write", _refresh_nb)
        _refresh_nb()

        return p

    # ══════════════════════════════════════════════════════════════════════════
    # Tela 7 — Revisão
    # ══════════════════════════════════════════════════════════════════════════
    def _page_review(self):
        p = tk.Frame(self, bg=BG)
        self._header(p, "Confira antes de publicar",
                     "Tudo certo? Você pode editar qualquer item antes de continuar.",
                     phase=2)

        nb = self._footer(p,
                          back_fn=lambda: self._show(self._page_vercel_password),
                          next_fn=lambda: self._show(self._page_deploy),
                          next_label="Publicar tudo agora  →")
        nb.config(bg="#16a34a", activebackground="#15803d")  # green for final action

        body = tk.Frame(p, bg=BG)
        body.pack(fill="both", expand=True, padx=32, pady=(14, 0))

        def _mask(v, show_last=4):
            if not v:
                return "(não preenchido)"
            if len(v) <= show_last:
                return "•" * len(v)
            return "•" * (len(v) - show_last) + v[-show_last:]

        sections = [
            ("✅  Supabase", lambda: self._show(self._page_supabase), [
                ("Project ID", lambda: self._var("SUPABASE_PROJECT_ID").get() or "(vazio)"),
                ("URL",        lambda: self._var("SUPABASE_URL").get() or "(vazio)"),
                ("Chave",      lambda: _mask(self._var("SUPABASE_SERVICE_ROLE_KEY").get())),
            ]),
            ("✅  Telegram", lambda: self._show(self._page_telegram_bot), [
                ("Token",  lambda: _mask(self._var("TELEGRAM_BOT_TOKEN").get())),
                ("Seu ID", lambda: self._var("TELEGRAM_USER_IDS").get() or "(vazio)"),
            ]),
            ("✅  Groq", lambda: self._show(self._page_groq), [
                ("Chave",  lambda: _mask(self._var("GROQ_API_KEY").get())),
            ]),
            ("✅  Fly.io", lambda: self._show(self._page_fly), [
                ("Backend", lambda: self._var("BACKEND_APP").get() or "(vazio)"),
                ("Bot",     lambda: self._var("BOT_APP").get() or "(vazio)"),
            ]),
            ("✅  Vercel", lambda: self._show(self._page_vercel_login), [
                ("Senha do painel", lambda: _mask(self._var("DASHBOARD_PASSWORD").get())),
            ]),
        ]

        for title, edit_fn, fields in sections:
            card = tk.Frame(body, bg=PANEL, pady=10, padx=16)
            card.pack(fill="x", pady=3)
            top  = tk.Frame(card, bg=PANEL)
            top.pack(fill="x")
            tk.Label(top, text=title, bg=PANEL, fg=TEXT,
                     font=(FONT, 10, "bold")).pack(side="left")
            tk.Button(top, text="Editar", command=edit_fn,
                      bg=PANEL2, fg=MUTED, relief="flat",
                      font=(FONT, 9), padx=10, pady=3, cursor="hand2").pack(side="right")
            for label, val_fn in fields:
                row = tk.Frame(card, bg=PANEL)
                row.pack(anchor="w", pady=1)
                tk.Label(row, text=f"  {label}:", bg=PANEL, fg=DIM,
                         font=(FONT, 9), width=14, anchor="w").pack(side="left")
                tk.Label(row, text=val_fn(), bg=PANEL, fg=MUTED,
                         font=("Consolas", 9)).pack(side="left")

        return p

    # ══════════════════════════════════════════════════════════════════════════
    # Tela 8 — Deploy
    # ══════════════════════════════════════════════════════════════════════════
    def _page_deploy(self):
        p = tk.Frame(self, bg=BG)
        self._header(p, "Publicando o Finance Bot…",
                     "Isso leva entre 3 e 8 minutos. Não feche a janela.", phase=3)

        done_btn = self._footer(p,
                                next_fn=lambda: self._show(lambda: self._page_done(self._info.get("urls", {}))),
                                next_label="Ver resultado  →",
                                next_enabled=False)

        body = tk.Frame(p, bg=BG)
        body.pack(fill="both", expand=True, padx=32, pady=(16, 0))

        step_labels = ["Servidor principal", "Bot do Telegram", "Painel web"]
        step_notes  = ["Configurando o servidor…", "Iniciando o bot…", "Publicando o painel…"]
        card_icon, card_note = [], []

        cards_frame = tk.Frame(body, bg=BG)
        cards_frame.pack(fill="x")

        for i, (label, note) in enumerate(zip(step_labels, step_notes)):
            card = tk.Frame(cards_frame, bg=PANEL, pady=12, padx=16)
            card.pack(fill="x", pady=3)
            ic = tk.Label(card, text="⏳", bg=PANEL, font=(FONT, 16), width=3)
            ic.pack(side="left")
            txt = tk.Frame(card, bg=PANEL)
            txt.pack(side="left", fill="x", expand=True)
            tk.Label(txt, text=label, bg=PANEL, fg=TEXT,
                     font=(FONT, 11, "bold")).pack(anchor="w")
            nt = tk.Label(txt, text="Aguardando…", bg=PANEL, fg=DIM, font=(FONT, 9))
            nt.pack(anchor="w")
            card_icon.append(ic)
            card_note.append(nt)

        # Log
        log_visible = [False]
        log_wrap = tk.Frame(body, bg=BG)
        log = scrolledtext.ScrolledText(log_wrap, bg=PANEL, fg=MUTED,
                                        font=("Consolas", 8), relief="flat",
                                        state="disabled", height=7)
        log.pack(fill="x")
        log.tag_config("ok",  foreground=GREEN)
        log.tag_config("err", foreground=RED)
        log.tag_config("hdr", foreground=YELLOW)

        toggle_btn = tk.Button(body, text="▸  Ver detalhes técnicos",
                               command=lambda: _toggle_log(),
                               bg=BG, fg=DIM, relief="flat",
                               font=(FONT, 9), cursor="hand2", anchor="w")
        toggle_btn.pack(anchor="w", pady=(8, 0))

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
            if DEMO:
                for i in range(3):
                    _set_step(i, "running")
                    self.after(0, lambda i=i: _log(f"\n── [DEMO] Passo {i+1} ──", "hdr"))
                    time.sleep(2)
                    self.after(0, lambda i=i: _log(f"  Simulando deploy do passo {i+1}…"))
                    time.sleep(1)
                    _set_step(i, "done")
                self._info["urls"] = {
                    "backend":   "https://finance-api-demo.fly.dev",
                    "dashboard": "https://finance-bot-demo.vercel.app",
                    "bot":       "finance-bot-demo",
                }
                self.after(0, lambda: (
                    _log("\n✅  [DEMO] Publicação simulada concluída!", "ok"),
                    done_btn.config(state="normal", bg=BLUE),
                ))
                return
            v        = {k: var.get().strip() for k, var in self._vars.items()}
            api_key  = secrets.token_hex(32)
            sess_key = secrets.token_hex(32)
            bapp     = v["BACKEND_APP"]
            botapp   = v["BOT_APP"]
            burl     = f"https://{bapp}.fly.dev"

            _set_step(0, "running")
            self.after(0, lambda: _log("\n── Servidor principal ──", "hdr"))
            _update_toml(BACKEND_TOML, bapp)
            if not _fly_exists(bapp):
                _run(["fly", "apps", "create", bapp])
            # Copy schema.sql into backend dir so Docker COPY picks it up
            import shutil as _shutil
            if os.path.exists(SCHEMA_SQL):
                _shutil.copy2(SCHEMA_SQL, os.path.join(BACKEND_DIR, "schema.sql"))
            proj_ref = v.get("SUPABASE_PROJECT_ID", "").strip()
            db_password = v.get("SUPABASE_DB_PASSWORD", "").strip()
            db_url = f"postgresql://postgres:{db_password}@db.{proj_ref}.supabase.co:5432/postgres"
            ok, _ = _run([
                "fly", "secrets", "set",
                f"SUPABASE_URL={v['SUPABASE_URL']}",
                f"SUPABASE_SERVICE_ROLE_KEY={v['SUPABASE_SERVICE_ROLE_KEY']}",
                f"DATABASE_URL={db_url}",
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
            dash_url = match.group(0) if match else "(veja vercel.com)"
            self._info["urls"] = {"backend": burl, "dashboard": dash_url,
                                  "bot": v.get("BOT_APP", "")}

            try:
                os.makedirs(APPDATA_DIR, exist_ok=True)
                cfg = {
                    "version":      self._info.get("version", "1.0.0"),
                    "install_path": self._info.get("install_path", ROOT),
                }
                with open(CONFIG_JSON, "w", encoding="utf-8") as _cf:
                    json.dump(cfg, _cf, indent=2)
            except Exception:
                pass

            self.after(0, lambda: (
                _log("\n✅  Publicação concluída!", "ok"),
                done_btn.config(state="normal", bg=BLUE),
            ))

        threading.Thread(target=deploy, daemon=True).start()
        return p

    # ══════════════════════════════════════════════════════════════════════════
    # Tela 9 — Pronto
    # ══════════════════════════════════════════════════════════════════════════
    def _page_done(self, urls):
        p = tk.Frame(self, bg=BG)
        self._header(p, "Tudo pronto! 🎉",
                     "Seu Finance Bot está no ar.", phase=4)

        self._footer(p,
                     next_fn=lambda: webbrowser.open(urls.get("dashboard", "")) or None,
                     next_label="Abrir painel web  →",
                     extra_btns=[("Fechar", self.destroy, PANEL)])

        body = tk.Frame(p, bg=BG)
        body.pack(fill="both", expand=True, padx=32, pady=(16, 0))

        for icon, label, url_key in [
            ("🌐", "Painel web", "dashboard"),
            ("⚙️", "Backend (raramente necessário)", "backend"),
        ]:
            url = urls.get(url_key, "")
            if not url:
                continue
            card = tk.Frame(body, bg=PANEL, pady=12, padx=18)
            card.pack(fill="x", pady=3)
            tk.Label(card, text=f"{icon}  {label}", bg=PANEL, fg=MUTED,
                     font=(FONT, 9)).pack(anchor="w")
            row = tk.Frame(card, bg=PANEL)
            row.pack(anchor="w", pady=(4, 0), fill="x")
            tk.Label(row, text=url, bg=PANEL, fg=GREEN,
                     font=("Consolas", 10)).pack(side="left")
            def _copy(u=url):
                self.clipboard_clear()
                self.clipboard_append(u)
            tk.Button(row, text="Copiar", command=_copy,
                      bg=PANEL2, fg=MUTED, relief="flat",
                      font=(FONT, 8), padx=8, pady=3, cursor="hand2").pack(side="right")
            tk.Button(card, text="Abrir no navegador",
                      command=lambda u=url: webbrowser.open(u),
                      bg=BLUE, fg="white", relief="flat",
                      font=(FONT, 9, "bold"), padx=10, pady=4,
                      cursor="hand2").pack(anchor="w", pady=(6, 0))

        tk.Label(body, text="Próximos passos:", bg=BG, fg=TEXT,
                 font=(FONT, 11, "bold")).pack(anchor="w", pady=(16, 6))
        for num, step in [
            ("1", "Abra o Telegram, encontre seu bot pelo nome e clique em START"),
            ("2", "Mande uma mensagem como:  gastei 50 reais no mercado"),
            ("3", "Acesse o painel web e entre com a senha que você definiu"),
            ("4", "Cadastre seus cartões no painel antes de usar"),
            ("5", "Para atualizar no futuro, execute o  FinanceBotUpdate.exe"),
        ]:
            row = tk.Frame(body, bg=BG)
            row.pack(anchor="w", pady=2)
            tk.Label(row, text=f"  {num}.", bg=BG, fg=BLUE,
                     font=(FONT, 10, "bold"), width=4).pack(side="left")
            tk.Label(row, text=step, bg=BG, fg=MUTED, font=(FONT, 10)).pack(side="left")

        return p


if __name__ == "__main__":
    app = Wizard()
    app.mainloop()
