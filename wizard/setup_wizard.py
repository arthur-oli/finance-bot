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
from PIL import Image, ImageDraw, ImageTk

DEMO = "--demo" in sys.argv
_DEMO_PAGE = next((sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == "--demo" and i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith("-")), None)
DEMO_FULL = DEMO and _DEMO_PAGE == "full"

_APPDATA = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "FinanceBot")
_PROGRESS_FILE = os.path.join(_APPDATA, "wizard_progress.json")

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


def _parse_cred_file(path):
    """Parse a Finance Bot credentials .txt file and return wizard var dict."""
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except Exception:
        return None
    if "Finance Bot — Credenciais" not in text:
        return None

    def _get(label):
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith(label):
                return stripped[len(label):].strip()
        return ""

    result = {}
    for label, key in [
        ("Senha do painel:",    "DASHBOARD_PASSWORD"),
        ("Supabase URL:",       "SUPABASE_URL"),
        ("Supabase Project:",   "SUPABASE_PROJECT_ID"),
        ("Telegram Bot Token:", "TELEGRAM_BOT_TOKEN"),
        ("Telegram User IDs:",  "TELEGRAM_USER_IDS"),
        ("Groq API Key:",       "GROQ_API_KEY"),
    ]:
        v = _get(label)
        if v:
            result[key] = v

    if "DASHBOARD_PASSWORD" in result:
        result["DASHBOARD_PASSWORD2"] = result["DASHBOARD_PASSWORD"]

    for label, key, pattern in [
        ("Backend:",       "BACKEND_APP", r"https?://([^.]+)\.fly\.dev"),
        ("Bot Telegram:",  "BOT_APP",     r"https?://([^.]+)\.fly\.dev"),
        ("Painel web:",    "VERCEL_APP",  r"https?://([^.]+)\.vercel\.app"),
    ]:
        url = _get(label)
        m = re.match(pattern, url)
        if m:
            result[key] = m.group(1)

    return result if result else None


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
    W, H = 780, 640
    # 5 phases shown in step bar
    PHASES = ["Preparar", "Conectar contas", "Revisar", "Publicar", "Pronto"]
    # sub-steps within "Conectar contas"
    PROVIDERS = ["Supabase", "Telegram", "Groq", "Fly.io", "Vercel"]

    _LOG_CANDIDATES = [
        os.path.join(APPDATA_DIR, "wizard.log"),
        os.path.join(os.path.dirname(sys.executable)
                     if getattr(sys, "frozen", False)
                     else os.path.dirname(os.path.abspath(__file__)), "wizard.log"),
    ]

    def _wlog(self, msg):
        import datetime as _wdt
        ts = _wdt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for path in self._LOG_CANDIDATES:
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "a", encoding="utf-8") as f:
                    f.write(f"[{ts}] {msg}\n")
                break
            except Exception:
                continue

    def __init__(self):
        super().__init__()
        self.withdraw()
        self.title("Finance Bot — Setup")
        self.geometry(f"{self.W}x{self.H}")
        self.resizable(False, False)
        self.configure(bg=BG)
        try:
            _logo = Image.open(_asset("finance-bot-logo.png")).convert("RGBA")
            _icon_imgs = [ImageTk.PhotoImage(_logo.resize((s, s), Image.LANCZOS))
                          for s in (16, 32, 48, 64, 128, 256)]
            self.iconphoto(True, *_icon_imgs)
            self._icon_refs = _icon_imgs
        except Exception:
            pass
        self._frame = None
        self._vars  = {}   # StringVar per field key
        self._info  = {}   # misc runtime info (login emails, etc.)
        import datetime as _idt
        self._wlog("=" * 60)
        self._wlog(f"Wizard iniciado — {_idt.datetime.now():%Y-%m-%d %H:%M:%S}")
        self._wlog(f"ROOT={ROOT}  APPDATA={APPDATA_DIR}")
        self._wlog(f"Log em: {self._LOG_CANDIDATES[0]}")
        if DEMO:
            _demo_bar = tk.Frame(self, bg="#7c3aed", height=22)
            _demo_bar.pack(side="bottom", fill="x")
            _demo_bar.pack_propagate(False)
            tk.Label(_demo_bar, text="VERSÃO DEMO — não preencher dados reais",
                     bg="#7c3aed", fg="white", font=(FONT, 8, "bold")).pack(expand=True)
        if DEMO:
            self._prefill_demo()
            _pages = {
                "welcome":          self._page_welcome,
                "prereqs":          self._page_prereqs,
                "clone":            self._page_clone,
                "supabase":         self._page_supabase,
                "supabase_keys":    self._page_supabase_keys,
                "telegram":         self._page_telegram_bot,
                "telegram_id":      self._page_telegram_id,
                "groq":             self._page_groq,
                "fly":              self._page_fly,
                "vercel":           self._page_vercel_login,
                "vercel_password":  self._page_vercel_password,
                "review":           self._page_review,
                "deploy":           self._page_deploy,
                "done":             lambda: self._page_done({
                                        "backend":   "https://finance-api-demo.fly.dev",
                                        "dashboard": "https://finance-bot-demo.vercel.app",
                                    }),
            }
            page_fn = _pages.get(_DEMO_PAGE, self._page_deploy) if _DEMO_PAGE and not DEMO_FULL else self._page_welcome
            self._show(page_fn)
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
            "GROQ_API_KEY":              "gsk_demoKeyForTestingPurposesOnly1234567890",
            "BACKEND_APP":               "finance-api-demo",
            "BOT_APP":                   "finance-bot-demo",
            "DASHBOARD_PASSWORD":        "demo1234",
            "DASHBOARD_PASSWORD2":       "demo1234",
        }
        for k, v in demo_vals.items():
            self._var(k, v)

    # ── Progress persistence ───────────────────────────────────────────────────
    def _save_progress(self, page_key):
        if DEMO or page_key == "<lambda>":
            return
        try:
            os.makedirs(_APPDATA, exist_ok=True)
            data = {
                "page": page_key,
                "root": ROOT,
                "vars": {k: v.get() for k, v in self._vars.items()},
            }
            with open(_PROGRESS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception:
            pass

    def _load_progress(self):
        try:
            with open(_PROGRESS_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def _clear_progress(self):
        try:
            os.remove(_PROGRESS_FILE)
        except Exception:
            pass

    def _resume(self, saved):
        self._wlog(f"Retomando da página: {saved.get('page', '?')}")
        if "root" in saved:
            _set_install_path(saved["root"])
            self._wlog(f"ROOT restaurado: {saved['root']}")
        for k, v in saved.get("vars", {}).items():
            self._var(k, v)
        _page_map = {
            "_page_prereqs":       self._page_prereqs,
            "_page_clone":         self._page_clone,
            "_page_supabase":      self._page_supabase,
            "_page_supabase_keys": self._page_supabase_keys,
            "_page_telegram_bot":  self._page_telegram_bot,
            "_page_telegram_id":   self._page_telegram_id,
            "_page_groq":          self._page_groq,
            "_page_fly":           self._page_fly,
            "_page_vercel_login":  self._page_vercel_login,
            "_page_vercel_password": self._page_vercel_password,
            "_page_review":        self._page_review,
            "_page_deploy":        self._page_deploy,
        }
        fn = _page_map.get(saved.get("page"), self._page_prereqs)
        self._show(fn)

    def _center(self):
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - self.W) // 2
        y = (self.winfo_screenheight() - self.H) // 2
        self.geometry(f"{self.W}x{self.H}+{x}+{y}")

    def _show(self, fn):
        if self._frame:
            self._frame.destroy()
        self._wlog(f"→ {fn.__name__}")
        self._frame = fn()
        self._frame.pack(fill="both", expand=True)
        self._save_progress(fn.__name__)

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
            c._imgs = []
            w   = c.winfo_width() or (self.W - 64)
            n   = len(self.PHASES)
            seg = w / n

            def _h(hex_color):
                return tuple(int(hex_color[j:j+2], 16) for j in (1, 3, 5))

            def _aa_circle(radius, fill, border_color=None, border_px=0):
                S, D = 4, radius * 2
                img = Image.new("RGB", (D*S, D*S), _h(BG))
                draw = ImageDraw.Draw(img)
                if border_color and border_px:
                    draw.ellipse([0, 0, D*S-1, D*S-1], fill=_h(border_color))
                    bw = border_px * S
                    draw.ellipse([bw, bw, D*S-1-bw, D*S-1-bw], fill=_h(fill))
                else:
                    draw.ellipse([0, 0, D*S-1, D*S-1], fill=_h(fill))
                return ImageTk.PhotoImage(img.resize((D, D), Image.LANCZOS))

            for i, label in enumerate(self.PHASES):
                cx = int(seg * i + seg / 2)
                cy = 16

                if i < n - 1:
                    nx  = int(seg * (i + 1) + seg / 2)
                    col = GREEN if i < phase else DIM
                    c.create_line(cx + 13, cy, nx - 13, cy, fill=col, width=2)

                if i < phase:
                    img = _aa_circle(12, GREEN)
                    c._imgs.append(img)
                    c.create_image(cx, cy, image=img, anchor="center")
                    c.create_text(cx, cy, text="✓", font=(FONT, 10, "bold"), fill=BG)
                elif i == phase:
                    img = _aa_circle(13, BLUE)
                    c._imgs.append(img)
                    c.create_image(cx, cy, image=img, anchor="center")
                    c.create_text(cx, cy, text=str(i+1), font=(FONT, 10, "bold"), fill="white")
                else:
                    img = _aa_circle(11, BG, border_color=DIM, border_px=2)
                    c._imgs.append(img)
                    c.create_image(cx, cy, image=img, anchor="center")
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
        _enabled = next_enabled or DEMO_FULL
        bg = BLUE if _enabled else PANEL2
        fg = "white" if _enabled else TEXT
        st = "normal" if _enabled else "disabled"
        nb = tk.Button(f, text=next_label, command=next_fn or (lambda: None),
                       bg=bg, fg=fg, activebackground=BLUE2, activeforeground="white",
                       relief="flat", font=(FONT, 11, "bold"),
                       padx=28, pady=11, cursor="hand2",
                       state=st, disabledforeground=TEXT)
        nb.pack(side="right")
        if DEMO_FULL:
            _real_config = nb.config
            def _unlocked_config(*a, **kw):
                kw.pop("state", None)
                kw.pop("disabledforeground", None)
                if kw: _real_config(**kw)
            nb.config = _unlocked_config
            nb.configure = _unlocked_config
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

        _saved = self._load_progress() if not DEMO else None
        if _saved:
            resume_card = tk.Frame(body, bg="#1e3a5f", padx=28, pady=12)
            resume_card.pack(padx=60, fill="x", pady=(10, 0))
            tk.Label(resume_card,
                     text="Instalação anterior encontrada — seus dados foram preservados.",
                     bg="#1e3a5f", fg="#93c5fd", font=(FONT, 9)).pack(anchor="w")
            tk.Button(resume_card, text="Retomar onde parei  →",
                      command=lambda: self._resume(_saved),
                      bg=BLUE, fg="white", activebackground=BLUE2, activeforeground="white",
                      relief="flat", font=(FONT, 10, "bold"),
                      padx=16, pady=7, cursor="hand2").pack(anchor="w", pady=(8, 0))

        # ── Importar credenciais exportadas ───────────────────────────────────
        def _do_import():
            path = filedialog.askopenfilename(
                title="Selecione o arquivo de credenciais do Finance Bot",
                filetypes=[("Arquivo de texto", "*.txt"), ("Todos os arquivos", "*.*")],
                initialdir=os.path.join(os.path.expanduser("~"), "Desktop"),
                parent=self,
            )
            if not path:
                return
            parsed = _parse_cred_file(path)
            if not parsed:
                from tkinter import messagebox
                messagebox.showerror(
                    "Arquivo inválido",
                    "Não foi possível ler as credenciais do arquivo.\n"
                    "Verifique se é um arquivo exportado pelo Finance Bot.",
                    parent=self,
                )
                return
            for k, v in parsed.items():
                self._var(k).set(v)
            self._show(self._page_prereqs)

        import_row = tk.Frame(body, bg=BG)
        import_row.pack(padx=60, fill="x", pady=(12, 0))
        tk.Button(import_row, text="📂  Importar credenciais existentes",
                  command=_do_import,
                  bg=PANEL, fg=MUTED, activebackground=PANEL2, activeforeground=TEXT,
                  relief="flat", font=(FONT, 9), padx=14, pady=7,
                  cursor="hand2").pack(side="left")
        tk.Label(import_row,
                 text="  Reinstalando em outro computador?",
                 bg=BG, fg=DIM, font=(FONT, 8)).pack(side="left")

        self._footer(p, next_fn=lambda: self._show(self._page_prereqs),
                     next_label="Começar do zero  →" if _saved else "Começar  →")
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
                            bg=DIM, fg="white", relief="flat",
                            font=(FONT, 9, "bold"), padx=12, pady=6, cursor="hand2",
                            state="disabled", disabledforeground="white")
            btn.pack(side="right")
            btn_ref[0] = btn
            items.append((icon, st, btn, chk_fn))
            all_do_fns.append(_do)

        def _winget_run(pkg_id, log_fn):
            self._wlog(f"winget install {pkg_id}")
            try:
                r = subprocess.run(
                    ["winget", "install", "-e", "--id", pkg_id,
                     "--accept-source-agreements", "--accept-package-agreements", "--silent"],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", creationflags=NO_WIN, timeout=300)
                if r.returncode == 0:
                    log_fn(f"winget: concluído (código 0).", "ok")
                else:
                    log_fn(f"winget: falhou (código {r.returncode}).", "err")
                    out = (r.stdout or "").strip()
                    if out:
                        for line in out.splitlines()[-6:]:
                            log_fn(f"  {line}")
                self._wlog(f"winget {pkg_id} rc={r.returncode}")
                return r.returncode == 0
            except subprocess.TimeoutExpired:
                log_fn("winget: tempo esgotado após 5 min. Verifique sua conexão e tente novamente.", "err")
                self._wlog(f"winget {pkg_id} timeout")
                return False

        def _inst_fly(log_fn):
            self._wlog("_inst_fly: iniciando")
            log_fn("Instalando Fly CLI via script oficial do Fly.io…")
            try:
                r2 = subprocess.run(
                    ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command",
                     "iwr https://fly.io/install.ps1 -useb | iex"],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", creationflags=NO_WIN, timeout=300)
                if r2.returncode == 0:
                    log_fn("Script do Fly.io: concluído.", "ok")
                else:
                    log_fn(f"Script do Fly.io: falhou (código {r2.returncode}).", "err")
                    out = (r2.stdout or "").strip()
                    if out:
                        for line in out.splitlines()[-6:]:
                            log_fn(f"  {line}")
                self._wlog(f"_inst_fly: rc={r2.returncode}")
            except subprocess.TimeoutExpired:
                log_fn("Script do Fly.io: tempo esgotado após 5 min. Verifique sua conexão.", "err")
                self._wlog("_inst_fly: timeout")
            log_fn("Verificando Fly CLI no PATH e em locais de instalação…")

        def _inst_node(log_fn):
            self._wlog("_inst_node: iniciando")
            log_fn("Instalando Node.js via winget…")
            ok = _winget_run("OpenJS.NodeJS.LTS", log_fn)
            if ok:
                _refresh_path()
                for d in [r"C:\Program Files\nodejs",
                          os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "nodejs")]:
                    if os.path.isdir(d) and d not in os.environ.get("PATH", ""):
                        os.environ["PATH"] = d + ";" + os.environ["PATH"]
                log_fn("Verificando Node.js…")
                v = _check_output(["node", "--version"])
                log_fn(f"node {v}" if v else "node não encontrado no PATH ainda.", "ok" if v else None)
                self._wlog(f"_inst_node: node version={v}")

        def _inst_git(log_fn):
            self._wlog("_inst_git: iniciando")
            log_fn("Instalando Git via winget…")
            ok = _winget_run("Git.Git", log_fn)
            if not ok:
                log_fn("Abrindo instalador manual em git-scm.com…")
                webbrowser.open("https://git-scm.com/download/win")
                log_fn("Instale o Git manualmente e clique em 'Instalar agora' para verificar.", "err")
                return
            _refresh_path()
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

        _clone_next = (lambda: self._show(self._page_supabase)) if DEMO else (lambda: None)
        nb = self._footer(p,
                          back_fn=lambda: self._show(self._page_prereqs),
                          next_fn=_clone_next,
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

        # Info card: what gets downloaded
        info_dl = tk.Frame(body, bg=PANEL, pady=12, padx=16)
        info_dl.pack(fill="x", pady=(10, 0))
        tk.Label(info_dl, text="📦  O que será baixado", bg=PANEL, fg=TEXT,
                 font=(FONT, 10, "bold")).pack(anchor="w")
        for _item in [
            "Código-fonte do Finance Bot (backend + bot + painel web)",
            f"Origem: github.com/{GITHUB_REPO}",
            "Tamanho estimado: ~30 MB",
            "Tempo estimado: ~1 minuto (depende da conexão)",
        ]:
            tk.Label(info_dl, text=f"  • {_item}", bg=PANEL, fg=MUTED,
                     font=(FONT, 9), anchor="w").pack(anchor="w", pady=1)

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
                status_lbl.config(text="✗  Pasta já existe e não está vazia. Apague-a ou escolha outro destino.", fg=RED)
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

        if DEMO:
            nb.config(command=lambda: self._show(self._page_supabase))
            return p
        path_var.trace_add("write", _validate)
        nb.config(command=_do_clone)
        _validate()
        return p

    # ══════════════════════════════════════════════════════════════════════════
    # Tela 2a — Supabase: Project URL
    # ══════════════════════════════════════════════════════════════════════════
    def _page_supabase(self, return_to_review=False):
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
            return False, "✗  Cole a senha gerada no passo 4"

        _next = self._page_review if return_to_review else self._page_supabase_keys
        _back = self._page_review if return_to_review else self._page_clone
        nb = self._footer(p,
                          back_fn=lambda: self._show(_back),
                          next_fn=lambda: self._show(_next),
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
        body.pack(fill="both", expand=True, padx=32, pady=(6, 0))

        instr = tk.Frame(body, bg=PANEL, pady=5, padx=12)
        instr.pack(fill="x")

        for num, text, url, btn_label in [
            ("1.", "Abra o supabase.com", "https://supabase.com/dashboard/sign-in", "Abrir supabase.com"),
            ("2.", "Clique em  Sign Up  e crie suas credenciais — confirme o e-mail (pode estar no lixo eletrônico)", None, None),
            ("3.", "Clique em  Create organization  (botão verde)", None, None),
            ("4.", "Em  Database password, clique em  Generate  ou crie uma senha segura → cole no campo abaixo\nEm  Region, escolha  South America (São Paulo)  •  Clique em  Create new project", None, None),
            ("5.", "Clique em  Copy  ao lado da URL do projeto (começa com  https)  e selecione  Project URL  → cole no campo abaixo", None, None),
        ]:
            row = tk.Frame(instr, bg=PANEL)
            row.pack(anchor="w", pady=1, fill="x")
            tk.Label(row, text=num, bg=PANEL, fg=BLUE,
                     font=(FONT, 9, "bold"), width=3).pack(side="left", anchor="n")
            col = tk.Frame(row, bg=PANEL)
            col.pack(side="left", fill="x")
            tk.Label(col, text=text, bg=PANEL, fg=MUTED,
                     font=(FONT, 9), justify="left").pack(anchor="w")
            if url and btn_label:
                tk.Button(col, text=btn_label + "  →",
                          command=lambda u=url: webbrowser.open(u),
                          bg=PANEL2, fg="white", relief="flat",
                          font=(FONT, 8, "bold"), padx=8, pady=2,
                          cursor="hand2").pack(anchor="w", pady=(3, 0))

        v2, _, _ = self._field(body, "SUPABASE_DB_PASSWORD", "Senha do banco (passo 4)",
                                hint="A senha gerada em  Database password  no passo 4",
                                secret=True, validate_fn=_val_pass)
        v2.trace_add("write", _refresh_nb)

        v, _, _ = self._field(body, "SUPABASE_URL", "URL do projeto (passo 5)",
                               hint="Exemplo:  https://abcdefghij.supabase.co",
                               validate_fn=_val_url)
        v.trace_add("write", _refresh_nb)
        _refresh_nb()
        return p

    # ══════════════════════════════════════════════════════════════════════════
    # Tela 2b — Supabase: API Key
    # ══════════════════════════════════════════════════════════════════════════
    def _page_supabase_keys(self, return_to_review=False):
        p = tk.Frame(self, bg=BG)
        self._header(p, "Supabase — chave secreta",
                     "Copie a chave service_role para o assistente acessar o banco.",
                     phase=1, provider_idx=0)

        def _val_key(v):
            v = v.strip()
            if v.startswith("eyJ") and len(v) > 100:
                return True, "✓  Formato correto"
            return False, "✗  Começa com  eyJ  e é bem longa — use a  service_role,  não a  anon"

        _next = self._page_review if return_to_review else self._page_telegram_bot
        _back = self._page_review if return_to_review else self._page_supabase
        nb = self._footer(p,
                          back_fn=lambda: self._show(_back),
                          next_fn=lambda: self._show(_next),
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
        api_url = (f"https://supabase.com/dashboard/project/{proj_id}/settings/api-keys"
                   if proj_id else "https://supabase.com/dashboard")

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
    # ══════════════════════════════════════════════════════════════════════════
    # Tela 3a — Telegram: criar bot
    # ══════════════════════════════════════════════════════════════════════════
    def _page_telegram_bot(self, return_to_review=False):
        p = tk.Frame(self, bg=BG)
        self._header(p, "Telegram — criar o bot",
                     "Vamos criar seu bot via @BotFather e salvar o token.",
                     phase=1, provider_idx=1)

        def _val_token(v):
            v = v.strip()
            if re.match(r'^\d{8,12}:[A-Za-z0-9_-]{30,}$', v):
                return True, "✓  Formato correto"
            return False, "✗  Formato: 123456789:ABCdefGHIjkl..."

        _next = self._page_review if return_to_review else self._page_telegram_id
        _back = self._page_review if return_to_review else self._page_supabase_keys
        nb = self._footer(p,
                          back_fn=lambda: self._show(_back),
                          next_fn=lambda: self._show(_next),
                          next_enabled=False)

        def _refresh_nb(*_):
            ok, _ = _val_token(self._var("TELEGRAM_BOT_TOKEN").get())
            nb.config(state="normal" if ok else "disabled",
                      bg=BLUE if ok else PANEL2,
                      fg="white" if ok else TEXT)

        body = tk.Frame(p, bg=BG)
        body.pack(fill="both", expand=True, padx=32, pady=(8, 0))

        # instruções + QR code lado a lado
        top = tk.Frame(body, bg=BG)
        top.pack(fill="x")

        instr = tk.Frame(top, bg=PANEL, pady=8, padx=12)
        instr.pack(side="left", fill="both", expand=True)

        for num, text, url, btn_label in [
            ("1.", "Abra o @BotFather no Telegram, ou procure no aplicativo de celular", "https://t.me/BotFather", "Abrir BotFather"),
            ("2.", "Envie  /newbot  e siga as instruções\nEscolha um nome.\nEscolha um username, ele deve terminar em  bot", None, None),
            ("3.", "O BotFather vai te enviar um token — copie e cole abaixo", None, None),
        ]:
            row = tk.Frame(instr, bg=PANEL)
            row.pack(anchor="w", pady=2, fill="x")
            tk.Label(row, text=num, bg=PANEL, fg=BLUE,
                     font=(FONT, 9, "bold"), width=3).pack(side="left", anchor="n")
            col = tk.Frame(row, bg=PANEL)
            col.pack(side="left", fill="x")
            tk.Label(col, text=text, bg=PANEL, fg=MUTED,
                     font=(FONT, 9), justify="left").pack(anchor="w")
            if url and btn_label:
                tk.Button(col, text=btn_label + "  →",
                          command=lambda u=url: webbrowser.open(u),
                          bg=PANEL2, fg="white", relief="flat",
                          font=(FONT, 8, "bold"), padx=8, pady=2,
                          cursor="hand2").pack(anchor="w", pady=(3, 0))

        # QR code
        qr_frame = tk.Frame(top, bg="white", padx=10, pady=8)
        qr_frame.pack(side="left", padx=(6, 0))
        try:
            _qr_raw = Image.open(_asset("qr_botfather.png")).convert("RGBA")
            _qr_raw.thumbnail((130, 130), Image.LANCZOS)
            _canvas = Image.new("RGBA", (130, 130), (255, 255, 255, 255))
            _ox = (130 - _qr_raw.width) // 2
            _oy = (130 - _qr_raw.height) // 2
            _canvas.paste(_qr_raw, (_ox, _oy))
            _qr_tk = ImageTk.PhotoImage(_canvas)
            lbl = tk.Label(qr_frame, image=_qr_tk, bg="white")
            lbl.image = _qr_tk
            lbl.pack()
        except Exception:
            pass
        tk.Label(qr_frame, text="Escanear\ncom o celular", bg="white", fg=DIM,
                 font=(FONT, 8), justify="center").pack(pady=(4, 0))

        v, _, _ = self._field(body, "TELEGRAM_BOT_TOKEN", "Token do bot",
                               hint="Formato:  123456789:ABCdefGHIjklMNOpqr...",
                               secret=True, validate_fn=_val_token)
        v.trace_add("write", _refresh_nb)
        _refresh_nb()

        # Dica de uso em grupo
        tip = tk.Frame(body, bg=PANEL2, pady=6, padx=14)
        tip.pack(fill="x", pady=(8, 0))
        tk.Label(tip,
                 text="💡  Quer usar o bot em grupo com vários usuários?",
                 bg=PANEL2, fg=TEXT, font=(FONT, 9, "bold"), justify="left").pack(anchor="w")
        tk.Label(tip,
                 text="No @BotFather: /mybots  →  Bot Settings  →  Group Privacy  →  Turn off",
                 bg=PANEL2, fg=MUTED, font=(FONT, 9), justify="left").pack(anchor="w", pady=(2, 0))

        return p

    # ══════════════════════════════════════════════════════════════════════════
    # Tela 3b — Telegram: descobrir ID
    # ══════════════════════════════════════════════════════════════════════════
    def _page_telegram_id(self, return_to_review=False):
        p = tk.Frame(self, bg=BG)
        self._header(p, "Telegram — seu ID de usuário",
                     "Descubra o número que identifica sua conta no Telegram.",
                     phase=1, provider_idx=1)

        def _val_uid(v):
            v = v.strip()
            if re.match(r'^\d+(\s*,\s*\d+)*$', v):
                return True, "✓  Formato correto"
            return False, "✗  Apenas números — vírgula para múltiplos usuários"

        _next = self._page_review if return_to_review else self._page_groq
        _back = self._page_review if return_to_review else self._page_telegram_bot
        nb = self._footer(p,
                          back_fn=lambda: self._show(_back),
                          next_fn=lambda: self._show(_next),
                          next_enabled=False)

        def _refresh_nb(*_):
            ok, _ = _val_uid(self._var("TELEGRAM_USER_IDS").get())
            nb.config(state="normal" if ok else "disabled",
                      bg=BLUE if ok else PANEL2,
                      fg="white" if ok else TEXT)

        body = tk.Frame(p, bg=BG)
        body.pack(fill="both", expand=True, padx=32, pady=(8, 0))

        # instruções + QR code lado a lado
        top = tk.Frame(body, bg=BG)
        top.pack(fill="x")

        instr = tk.Frame(top, bg=PANEL, pady=8, padx=12)
        instr.pack(side="left", fill="both", expand=True)

        for num, text, url, btn_label in [
            ("1.", "Abra o @userinfobot no Telegram, ou procure no aplicativo de celular", "https://t.me/userinfobot", "Abrir userinfobot"),
            ("2.", "Digite  /start", None, None),
            ("3.", "Ele vai te responder com seu ID numérico — copie e cole abaixo", None, None),
            ("4.", "Repita: clique em  User  e escolha cada usuário que deve ter acesso ao bot", None, None),
        ]:
            row = tk.Frame(instr, bg=PANEL)
            row.pack(anchor="w", pady=2, fill="x")
            tk.Label(row, text=num, bg=PANEL, fg=BLUE,
                     font=(FONT, 9, "bold"), width=3).pack(side="left", anchor="n")
            col = tk.Frame(row, bg=PANEL)
            col.pack(side="left", fill="x")
            tk.Label(col, text=text, bg=PANEL, fg=MUTED,
                     font=(FONT, 9), justify="left").pack(anchor="w")
            if url and btn_label:
                tk.Button(col, text=btn_label + "  →",
                          command=lambda u=url: webbrowser.open(u),
                          bg=PANEL2, fg="white", relief="flat",
                          font=(FONT, 8, "bold"), padx=8, pady=2,
                          cursor="hand2").pack(anchor="w", pady=(3, 0))

        # QR code
        qr_frame = tk.Frame(top, bg="white", padx=10, pady=8)
        qr_frame.pack(side="left", padx=(6, 0))
        try:
            _qr_raw = Image.open(_asset("qr_userinfobot.png")).convert("RGBA")
            _qr_raw.thumbnail((130, 130), Image.LANCZOS)
            _canvas = Image.new("RGBA", (130, 130), (255, 255, 255, 255))
            _ox = (130 - _qr_raw.width) // 2
            _oy = (130 - _qr_raw.height) // 2
            _canvas.paste(_qr_raw, (_ox, _oy))
            _qr_tk = ImageTk.PhotoImage(_canvas)
            lbl = tk.Label(qr_frame, image=_qr_tk, bg="white")
            lbl.image = _qr_tk
            lbl.pack()
        except Exception:
            pass
        tk.Label(qr_frame, text="Escanear\ncom o celular", bg="white", fg=DIM,
                 font=(FONT, 8), justify="center").pack(pady=(4, 0))

        v, _, _ = self._field(body, "TELEGRAM_USER_IDS", "IDs de usuário (todos que vão usar o bot)",
                               hint="Um ou mais IDs separados por vírgula, ex: 123456789,987654321",
                               validate_fn=_val_uid)
        v.trace_add("write", _refresh_nb)
        _refresh_nb()

        tip = tk.Frame(body, bg=PANEL2, pady=6, padx=14)
        tip.pack(fill="x", pady=(8, 0))
        tk.Label(tip,
                 text="💡  Para usar o bot em grupo: peça o ID de cada pessoa no @userinfobot e separe por vírgula.",
                 bg=PANEL2, fg=MUTED, font=(FONT, 9), justify="left").pack(anchor="w")

        return p

    # ══════════════════════════════════════════════════════════════════════════
    # Tela 4 — Groq
    # ══════════════════════════════════════════════════════════════════════════
    def _page_groq(self, return_to_review=False):
        p = tk.Frame(self, bg=BG)
        self._header(p, "Groq — inteligência artificial",
                     "A IA que lê suas mensagens e identifica gastos automaticamente.",
                     phase=1, provider_idx=2)

        def _val_key(v):
            v = v.strip()
            if v.startswith("gsk_") and len(v) > 40:
                return True, "✓  Formato correto"
            return False, "✗  Deve começar com  gsk_"

        _next = self._page_review if return_to_review else self._page_fly
        _back = self._page_review if return_to_review else self._page_telegram_id
        nb = self._footer(p,
                          back_fn=lambda: self._show(_back),
                          next_fn=lambda: self._show(_next),
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
            ("1.", "Crie sua conta gratuita — confirme o e-mail de verificação\n"
                   "(verifique o lixo eletrônico se não receber)", "https://console.groq.com", "Abrir console.groq.com"),
            ("2.", "No menu superior, clique em  API Keys", "https://console.groq.com/keys", "Abrir API Keys"),
            ("3.", "Clique em  Create API Key, dê um nome (ex: finance-bot)\n"
                   "No campo de validade, selecione  No expiration\n"
                   "Clique em  Submit\n"
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
    def _page_fly(self, return_to_review=False):
        p = tk.Frame(self, bg=BG)
        self._header(p, "Fly.io — onde o bot vai rodar",
                     "Hospedagem 24/7 do backend e do bot Telegram. Gratuito.",
                     phase=1, provider_idx=3)

        def _val_name(v):
            v = v.strip()
            if re.match(r'^[a-z0-9][a-z0-9-]{2,28}[a-z0-9]$', v):
                return True, "✓  Nome válido"
            return False, "✗  Use letras minúsculas, números e hífen (4–30 caracteres)"

        fly_ok    = [False]
        # None = não verificado, True = disponível/próprio, False = conflito
        avail     = [None, None]
        deb_ids   = [None, None]
        avail_lbl = [None, None]

        _next = self._page_review if return_to_review else self._page_vercel_login
        _back = self._page_review if return_to_review else self._page_groq
        nb = self._footer(p,
                          back_fn=lambda: self._show(_back),
                          next_fn=lambda: self._show(_next),
                          next_enabled=False)

        def _refresh_nb(*_):
            ok1, _ = _val_name(self._var("BACKEND_APP").get())
            ok2, _ = _val_name(self._var("BOT_APP").get())
            avail_ok = all(a is not False for a in avail)
            ok = fly_ok[0] and ok1 and ok2 and avail_ok
            nb.config(state="normal" if ok else "disabled",
                      bg=BLUE if ok else PANEL2,
                      fg="white" if ok else MUTED)

        def _check_avail(idx, name):
            """Verifica se o nome já existe na conta do usuário (pode ser reutilizado)."""
            name = name.strip()
            if not fly_ok[0] or not re.match(r'^[a-z0-9][a-z0-9-]{2,28}[a-z0-9]$', name):
                return
            self.after(0, lambda: avail_lbl[idx].config(text="⏳ verificando…", fg=DIM))
            try:
                r = subprocess.run(["fly", "apps", "list"], capture_output=True,
                                    text=True, encoding="utf-8", creationflags=NO_WIN, timeout=15)
                if name in (r.stdout or ""):
                    msg, col = "✓  App existente na sua conta — será reutilizado", GREEN
                else:
                    msg, col = "✓  Disponível — será criado no deploy", GREEN
            except (subprocess.TimeoutExpired, Exception):
                msg, col = "⚠  Não verificado (Fly.io lento) — será criado no deploy", DIM
            avail[idx] = True
            self.after(0, lambda m=msg, c=col: (
                avail_lbl[idx].config(text=m, fg=c),
                _refresh_nb(),
            ))

        def _schedule_check(idx, var):
            def _on_change(*_):
                if deb_ids[idx]:
                    self.after_cancel(deb_ids[idx])
                avail[idx] = None
                avail_lbl[idx].config(text="", fg=DIM)
                _refresh_nb()
                name = var.get().strip()
                ok, _ = _val_name(name)
                if ok and fly_ok[0]:
                    deb_ids[idx] = self.after(900, lambda: threading.Thread(
                        target=_check_avail, args=(idx, name), daemon=True).start())
            return _on_change

        body = tk.Frame(p, bg=BG)
        body.pack(fill="both", expand=True, padx=32, pady=(14, 0))

        # Zone 1 — criar conta
        zone1 = tk.Frame(body, bg=PANEL, pady=6, padx=14)
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
                  command=lambda: webbrowser.open("https://fly.io/app/sign-up"),
                  bg=BLUE, fg="white", relief="flat",
                  font=(FONT, 9, "bold"), padx=10, pady=6, cursor="hand2").pack(side="right")

        # Zone 2 — login
        tk.Label(body, text="2.  Conectar o assistente à sua conta",
                 bg=BG, fg=MUTED, font=(FONT, 10, "bold")).pack(anchor="w", pady=(8, 0))

        def _login_fly():
            subprocess.Popen(["cmd.exe", "/c", "fly auth login"],
                             creationflags=subprocess.CREATE_NEW_CONSOLE).wait()

        def _after_fly_login(ok):
            fly_ok[0] = ok
            _refresh_nb()
            if ok:
                for i, var in enumerate([self._var("BACKEND_APP"), self._var("BOT_APP")]):
                    threading.Thread(target=_check_avail, args=(i, var.get()), daemon=True).start()

        self._login_card(body, "Fly.io",
                         ["fly", "auth", "whoami"],
                         _login_fly, _after_fly_login)

        # Zone 3 — app names
        tk.Label(body, text="3.  Escolha nomes para os servidores",
                 bg=BG, fg=MUTED, font=(FONT, 10, "bold")).pack(anchor="w", pady=(6, 0))

        suffix = secrets.token_hex(2)
        self._var("BACKEND_APP", f"finance-api-{suffix}")
        self._var("BOT_APP",     f"finance-bot-{suffix}")

        fields_row = tk.Frame(body, bg=BG)
        fields_row.pack(fill="x")

        col_left = tk.Frame(fields_row, bg=BG)
        col_left.pack(side="left", fill="x", expand=True, padx=(0, 12))
        v1, _, _ = self._field(col_left, "BACKEND_APP", "Servidor principal (backend)",
                                hint="https://NOME.fly.dev",
                                validate_fn=_val_name, width=26)
        avail_lbl[0] = tk.Label(col_left, text="", bg=BG, fg=DIM, font=(FONT, 8))
        avail_lbl[0].pack(anchor="w")

        col_right = tk.Frame(fields_row, bg=BG)
        col_right.pack(side="left", fill="x", expand=True)
        v2, _, _ = self._field(col_right, "BOT_APP", "Servidor do bot Telegram",
                                hint="https://NOME.fly.dev",
                                validate_fn=_val_name, width=26)
        avail_lbl[1] = tk.Label(col_right, text="", bg=BG, fg=DIM, font=(FONT, 8))
        avail_lbl[1].pack(anchor="w")

        v1.trace_add("write", _schedule_check(0, v1))
        v2.trace_add("write", _schedule_check(1, v2))
        _refresh_nb()

        return p

    # ══════════════════════════════════════════════════════════════════════════
    # Tela 6a — Vercel: login
    # ══════════════════════════════════════════════════════════════════════════
    def _page_vercel_login(self, return_to_review=False):
        p = tk.Frame(self, bg=BG)
        self._header(p, "Vercel — o painel web",
                     "Onde você acompanha seus gastos pelo navegador. Gratuito.",
                     phase=1, provider_idx=4)

        vercel_ok = [False]
        _next = self._page_review if return_to_review else self._page_vercel_password
        _back = self._page_review if return_to_review else self._page_fly
        nb = self._footer(p,
                          back_fn=lambda: self._show(_back),
                          next_fn=lambda: self._show(_next),
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
                  command=lambda: webbrowser.open("https://vercel.com/signup"),
                  bg=BLUE, fg="white", relief="flat",
                  font=(FONT, 9, "bold"), padx=10, pady=6, cursor="hand2").pack(side="right")

        # Zone 2 — login
        tk.Label(body, text="2.  Conectar o assistente à sua conta",
                 bg=BG, fg=MUTED, font=(FONT, 10, "bold")).pack(anchor="w", pady=(14, 0))

        def _login_vercel():
            subprocess.Popen(
                ["cmd.exe", "/c", "npx --yes vercel login"],
                env={**os.environ, "NO_UPDATE_NOTIFIER": "1"},
                creationflags=subprocess.CREATE_NEW_CONSOLE
            ).wait()

        self._login_card(body, "Vercel",
                         ["cmd.exe", "/c", "npx --yes vercel whoami"],
                         _login_vercel, _refresh_nb)

        tk.Label(body,
                 text="Siga as instruções no navegador para fazer login.\n"
                      "Se a janela preta perguntar sobre atualização, pressione  N  e  Enter.",
                 bg=BG, fg=DIM, font=(FONT, 9), justify="left").pack(anchor="w", pady=(8, 0))

        return p

    # ══════════════════════════════════════════════════════════════════════════
    # Tela 6b — Vercel: senha de acesso
    # ══════════════════════════════════════════════════════════════════════════
    def _page_vercel_password(self, return_to_review=False):
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

        _back = self._page_review if return_to_review else self._page_vercel_login
        nb = self._footer(p,
                          back_fn=lambda: self._show(_back),
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
                 text="Você vai precisar dela quando acessar o painel, de tempos em tempos. Não há recuperação automática.",
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
        body.pack(fill="both", expand=True, padx=32, pady=(6, 0))

        def _mask(v, show_last=4):
            if not v:
                return "(não preenchido)"
            if len(v) <= show_last:
                return "•" * len(v)
            dots = min(len(v) - show_last, 26)
            return "•" * dots + v[-show_last:]

        sections = [
            ("✅  Supabase", lambda: self._show(lambda: self._page_supabase(return_to_review=True)), [
                ("Project ID", lambda: self._var("SUPABASE_PROJECT_ID").get() or "(vazio)"),
                ("URL",        lambda: self._var("SUPABASE_URL").get() or "(vazio)"),
                ("Chave",      lambda: _mask(self._var("SUPABASE_SERVICE_ROLE_KEY").get())),
            ]),
            ("✅  Telegram", lambda: self._show(lambda: self._page_telegram_bot(return_to_review=True)), [
                ("Token",  lambda: _mask(self._var("TELEGRAM_BOT_TOKEN").get())),
                ("Seu ID", lambda: self._var("TELEGRAM_USER_IDS").get() or "(vazio)"),
            ]),
            ("✅  Groq", lambda: self._show(lambda: self._page_groq(return_to_review=True)), [
                ("Chave",  lambda: _mask(self._var("GROQ_API_KEY").get())),
            ]),
            ("✅  Fly.io", lambda: self._show(lambda: self._page_fly(return_to_review=True)), [
                ("Backend", lambda: self._var("BACKEND_APP").get() or "(vazio)"),
                ("Bot",     lambda: self._var("BOT_APP").get() or "(vazio)"),
            ]),
            ("✅  Vercel", lambda: self._show(lambda: self._page_vercel_password(return_to_review=True)), [
                ("Senha do painel", lambda: _mask(self._var("DASHBOARD_PASSWORD").get())),
            ]),
        ]

        # Two-column layout: left = Supabase + Telegram, right = Groq + Fly.io + Vercel
        cols_frame = tk.Frame(body, bg=BG)
        cols_frame.pack(fill="both", expand=True)
        col_left  = tk.Frame(cols_frame, bg=BG)
        col_left.pack(side="left", fill="both", expand=True, padx=(0, 5))
        col_right = tk.Frame(cols_frame, bg=BG)
        col_right.pack(side="left", fill="both", expand=True, padx=(5, 0))

        def _build_card(parent, title, edit_fn, fields):
            card = tk.Frame(parent, bg=PANEL, pady=10, padx=12)
            card.pack(fill="x", pady=3)
            top = tk.Frame(card, bg=PANEL)
            top.pack(fill="x")
            tk.Label(top, text=title, bg=PANEL, fg=TEXT,
                     font=(FONT, 10, "bold")).pack(side="left")
            tk.Button(top, text="Editar", command=edit_fn,
                      bg=PANEL2, fg=MUTED, relief="flat",
                      font=(FONT, 9), padx=8, pady=3, cursor="hand2").pack(side="right")
            for label, val_fn in fields:
                row = tk.Frame(card, bg=PANEL)
                row.pack(anchor="w", pady=1)
                tk.Label(row, text=f"  {label}:", bg=PANEL, fg=DIM,
                         font=(FONT, 9), anchor="w").pack(side="left")
                tk.Label(row, text=val_fn(), bg=PANEL, fg=MUTED,
                         font=("Consolas", 9), wraplength=280, justify="left").pack(side="left", anchor="w")

        for sec in sections[:2]:
            _build_card(col_left, *sec)
        for sec in sections[2:]:
            _build_card(col_right, *sec)

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
        step_times  = ["~3 min", "~2 min", "~1 min"]
        card_icon, card_note, card_time = [], [], []

        # Banner de sucesso (escondido até deploy terminar)
        deploy_banner = tk.Frame(body, bg="#14532d", pady=8, padx=16)
        tk.Label(deploy_banner,
                 text="✅  Publicação concluída! Clique em 'Ver resultado →' para continuar.",
                 bg="#14532d", fg="#86efac", font=(FONT, 10, "bold")).pack(anchor="w")

        cards_frame = tk.Frame(body, bg=BG)
        cards_frame.pack(fill="x")

        for i, (label, note, est) in enumerate(zip(step_labels, step_notes, step_times)):
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
            tm = tk.Label(txt, text=est, bg=PANEL, fg=DIM, font=(FONT, 8))
            tm.pack(anchor="w")
            card_icon.append(ic)
            card_note.append(nt)
            card_time.append(tm)

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

        retry_btn_ref = [None]

        def _toggle_log():
            log_visible[0] = not log_visible[0]
            if log_visible[0]:
                log_wrap.pack(fill="x", pady=(4, 0))
                toggle_btn.config(text="▾  Ocultar detalhes técnicos")
            else:
                log_wrap.pack_forget()
                toggle_btn.config(text="▸  Ver detalhes técnicos")

        def _do_retry():
            retry_btn_ref[0].pack_forget()
            log_link.pack_forget()
            deploy_banner.pack_forget()
            log.config(state="normal")
            log.delete("1.0", "end")
            log.config(state="disabled")
            if log_visible[0]:
                _toggle_log()
            for i in range(len(step_labels)):
                card_icon[i].config(text="⏳")
                card_note[i].config(text="Aguardando…", fg=DIM)
                card_time[i].config(text=step_times[i])
                card_time[i].pack(anchor="w")
            done_btn.config(state="disabled", bg=PANEL2)
            threading.Thread(target=deploy, daemon=True).start()

        retry_btn = tk.Button(body, text="↺  Tentar novamente",
                              command=_do_retry,
                              bg=YELLOW, fg="#1c1917", activebackground="#d97706",
                              relief="flat", font=(FONT, 10, "bold"),
                              padx=18, pady=9, cursor="hand2")
        retry_btn_ref[0] = retry_btn

        _log_path = self._LOG_CANDIDATES[0]
        log_link = tk.Label(body,
                            text=f"Arquivo completo: {_log_path}",
                            bg=BG, fg=BLUE, font=(FONT, 8), cursor="hand2", anchor="w")
        log_link.bind("<Button-1>",
                      lambda e, p=_log_path: subprocess.Popen(["notepad.exe", p]))

        def _log(text, tag=None):
            log.config(state="normal")
            log.insert("end", text + "\n", tag or "")
            log.see("end")
            log.config(state="disabled")

        def _set_step(i, state, out=""):
            if state == "running":
                ic, fg, note = "⏳", YELLOW, step_notes[i]
            elif state == "done":
                ic, fg, note = "✅", GREEN, "Concluído!"
            else:
                if "You've exceeded your free machines limit" in out:
                    note = "Limite de máquinas gratuitas atingido. Apague apps antigos em fly.io/dashboard."
                elif "region not available" in out:
                    note = "Região indisponível. Tente novamente em alguns minutos."
                else:
                    note = "Erro — veja os detalhes técnicos"
                ic, fg = "❌", RED
            def _update():
                card_icon[i].config(text=ic)
                card_note[i].config(text=note, fg=fg)
                if state in ("done", "error"):
                    card_time[i].pack_forget()
                if state == "error":
                    if not log_visible[0]:
                        _toggle_log()
                    retry_btn_ref[0].pack(anchor="w", pady=(10, 0))
                    log_link.pack(anchor="w", pady=(2, 0))
            self.after(0, _update)

        def _dlog(msg, tag=None, _ui=True):
            self._wlog(msg)
            if _ui:
                self.after(0, lambda m=msg, t=tag: _log(m, t))

        self._wlog(f"BACKEND_DIR={BACKEND_DIR}")
        self._wlog(f"DASHBOARD_DIR={DASHBOARD_DIR}")
        self.after(0, lambda: _log(f"  [LOG] {self._LOG_CANDIDATES[0]}"))

        def _run(args, cwd=None, stdin_val=None, timeout=None):
            cmd_str = " ".join(str(a) for a in args)
            _dlog(f"  [CMD] {cmd_str}")
            proc = _popen(args, cwd=cwd)
            _timed_out = [False]
            _timer = None
            if timeout:
                def _kill():
                    _timed_out[0] = True
                    _dlog(f"  [DBG] timeout após {timeout}s — encerrando processo", "err")
                    try:
                        proc.kill()
                    except Exception:
                        pass
                _timer = threading.Timer(timeout, _kill)
                _timer.start()
            out_lines = []
            try:
                if stdin_val is not None:
                    proc.stdin.write(stdin_val)
                proc.stdin.close()
            except Exception:
                pass
            for line in proc.stdout:
                line = line.rstrip()
                out_lines.append(line)
                tag = "err" if re.search(r"\b(error|failed|fatal)\b", line, re.I) else None
                _dlog(line, tag)
            proc.wait()
            if _timer:
                _timer.cancel()
            if _timed_out[0]:
                out_lines.append("ERRO: comando excedeu o tempo limite.")
            _dlog(f"  [RET] código={proc.returncode}")
            return proc.returncode == 0 and not _timed_out[0], "\n".join(out_lines)

        def _fly_exists(name):
            _dlog(f"  [DBG] verificando se app '{name}' existe no Fly…")
            try:
                r = subprocess.run(["fly", "apps", "list"], capture_output=True,
                                   text=True, encoding="utf-8", creationflags=NO_WIN, timeout=20)
                _dlog(f"  [DBG] fly apps list rc={r.returncode}, found={name in r.stdout}")
                return name in r.stdout
            except (subprocess.TimeoutExpired, Exception) as _e:
                _dlog(f"  [DBG] fly apps list erro: {_e} — assumindo que não existe")
                return False

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
                    deploy_banner.pack(fill="x", pady=(0, 8), before=cards_frame),
                ))
                return
            v        = {k: var.get().strip() for k, var in self._vars.items()}
            api_key  = secrets.token_hex(32)
            sess_key = secrets.token_hex(32)
            bapp     = v["BACKEND_APP"]
            botapp   = v["BOT_APP"]
            burl     = f"https://{bapp}.fly.dev"

            _dlog(f"  [DBG] ROOT={ROOT}")
            _dlog(f"  [DBG] BACKEND_DIR={BACKEND_DIR}")
            _dlog(f"  [DBG] DASHBOARD_DIR={DASHBOARD_DIR}")
            _dlog(f"  [DBG] bapp={bapp}  botapp={botapp}")

            _set_step(0, "running")
            _dlog("\n── Servidor principal ──", "hdr")
            _dlog(f"  [DBG] atualizando {BACKEND_TOML}…")
            try:
                _update_toml(BACKEND_TOML, bapp)
            except Exception as _e:
                _dlog(f"  ERRO: fly.toml do backend não encontrado — {_e}", "err")
                _set_step(0, "error", out=str(_e))
                return
            _dlog("  [DBG] toml atualizado")
            exists = _fly_exists(bapp)
            if not exists:
                ok_c, out_c = _run(["fly", "apps", "create", bapp])
                if not ok_c:
                    _dlog(f"  ERRO: não foi possível criar o app '{bapp}' no Fly.io.", "err")
                    _dlog("  Verifique se o nome já está em uso globalmente ou tente outro nome.", "err")
                    _set_step(0, "error", out=out_c)
                    return
            # Copy schema.sql into backend dir so Docker COPY picks it up
            import shutil as _shutil
            schema_copied = os.path.exists(SCHEMA_SQL)
            _dlog(f"  [DBG] schema.sql existe={schema_copied}")
            if schema_copied:
                _shutil.copy2(SCHEMA_SQL, os.path.join(BACKEND_DIR, "schema.sql"))
            proj_ref = v.get("SUPABASE_PROJECT_ID", "").strip()
            db_password = v.get("SUPABASE_DB_PASSWORD", "").strip()
            db_url = f"postgresql://postgres:{db_password}@db.{proj_ref}.supabase.co:5432/postgres"
            _dlog(f"  [DBG] proj_ref={proj_ref!r}  db_url_prefix=postgresql://postgres:***@db.{proj_ref}…")
            _dlog("  [DBG] rodando fly secrets set (backend)…")
            ok, out = _run([
                "fly", "secrets", "set",
                f"SUPABASE_URL={v['SUPABASE_URL']}",
                f"SUPABASE_SERVICE_ROLE_KEY={v['SUPABASE_SERVICE_ROLE_KEY']}",
                f"DATABASE_URL={db_url}",
                f"API_SECRET_KEY={api_key}",
                "--app", bapp,
            ], cwd=BACKEND_DIR)
            _dlog(f"  [DBG] secrets set backend ok={ok}")
            if not ok:
                if "503" in out:
                    _dlog("  ⚠️  Fly.io retornou 503 (instabilidade temporária). Aguarde ~1 min e use 'Tentar novamente'.", "err")
                _set_step(0, "error", out=out)
                return
            _dlog("  [DBG] rodando fly deploy (backend)…")
            ok, out = _run(["fly", "deploy", "--app", bapp, "--wait-timeout", "180"],
                         cwd=BACKEND_DIR)
            _dlog(f"  [DBG] fly deploy backend ok={ok}")
            _set_step(0, "done" if ok else "error", out=out)
            if not ok:
                if "503" in out:
                    _dlog("  ⚠️  Fly.io retornou 503. Aguarde ~1 min e use 'Tentar novamente'.", "err")
                return

            _set_step(1, "running")
            _dlog("\n── Bot do Telegram ──", "hdr")
            _dlog(f"  [DBG] atualizando {BOT_TOML}…")
            try:
                _update_toml(BOT_TOML, botapp,
                             [(r'BACKEND_URL\s*=.*', f'BACKEND_URL = "{burl}"')])
            except Exception as _e:
                _dlog(f"  ERRO: fly.toml do bot não encontrado — {_e}", "err")
                _set_step(1, "error", out=str(_e))
                return
            _dlog("  [DBG] toml bot atualizado")
            if not _fly_exists(botapp):
                ok_c, out_c = _run(["fly", "apps", "create", botapp])
                if not ok_c:
                    _dlog(f"  ERRO: não foi possível criar o app '{botapp}' no Fly.io.", "err")
                    _dlog("  Verifique se o nome já está em uso globalmente ou tente outro nome.", "err")
                    _set_step(1, "error", out=out_c)
                    return
            _dlog("  [DBG] rodando fly secrets set (bot)…")
            ok, out = _run([
                "fly", "secrets", "set",
                f"TELEGRAM_BOT_TOKEN={v['TELEGRAM_BOT_TOKEN']}",
                f"TELEGRAM_USER_IDS={v['TELEGRAM_USER_IDS']}",
                f"BACKEND_URL={burl}",
                f"API_SECRET_KEY={api_key}",
                f"GROQ_API_KEY={v['GROQ_API_KEY']}",
                "--app", botapp,
            ], cwd=ROOT)
            _dlog(f"  [DBG] secrets set bot ok={ok}")
            if not ok:
                if "503" in out:
                    _dlog("  ⚠️  Fly.io retornou 503. Aguarde ~1 min e use 'Tentar novamente'.", "err")
                _set_step(1, "error", out=out)
                return
            _dlog("  [DBG] rodando fly deploy (bot)…")
            ok, out = _run(["fly", "deploy", "--app", botapp, "--wait-timeout", "180"],
                         cwd=ROOT)
            _dlog(f"  [DBG] fly deploy bot ok={ok}")
            _set_step(1, "done" if ok else "error", out=out)
            if not ok:
                if "503" in out:
                    _dlog("  ⚠️  Fly.io retornou 503. Aguarde ~1 min e use 'Tentar novamente'.", "err")
                return

            _set_step(2, "running")
            _dlog("\n── Painel web ──", "hdr")
            _dlog(f"  [DBG] escrevendo vercel.json em {DASHBOARD_DIR}…")
            with open(os.path.join(DASHBOARD_DIR, "vercel.json"), "w") as f:
                f.write("{}\n")

            # Ler token de auth do Vercel CLI ANTES do deploy (evita travamento por seleção de scope)
            import glob as _glob

            def _find_vercel_token():
                _sys_drive = os.environ.get("SystemDrive", "C:")
                _candidates = []
                # Paths conhecidos via variáveis de ambiente
                for _env in ("LOCALAPPDATA", "APPDATA", "USERPROFILE"):
                    _val = os.environ.get(_env, "")
                    if _val:
                        _candidates += [
                            os.path.join(_val, "com.vercel.cli", "auth.json"),
                            os.path.join(_val, "AppData", "Local", "com.vercel.cli", "auth.json"),
                            os.path.join(_val, "AppData", "Roaming", "com.vercel.cli", "auth.json"),
                            os.path.join(_val, ".vercel", "auth.json"),
                        ]
                # Busca ampla em todos os perfis de usuário do sistema
                _candidates += _glob.glob(f"{_sys_drive}\\Users\\*\\AppData\\Local\\com.vercel.cli\\auth.json")
                _candidates += _glob.glob(f"{_sys_drive}\\Users\\*\\AppData\\Roaming\\com.vercel.cli\\auth.json")
                _candidates += _glob.glob(f"{_sys_drive}\\Users\\*\\.vercel\\auth.json")
                # Deduplicar preservando ordem
                seen = set()
                for _tp in _candidates:
                    _tp = os.path.normpath(_tp)
                    if _tp in seen:
                        continue
                    seen.add(_tp)
                    _exists = os.path.exists(_tp)
                    _dlog(f"  [DBG] testando: {_tp} — {'EXISTE' if _exists else 'nao existe'}")
                    if _exists:
                        try:
                            with open(_tp) as _f:
                                _tok = json.load(_f).get("token")
                            if _tok:
                                _dlog(f"  [DBG] token Vercel lido de {_tp}")
                                return _tok
                        except Exception as _e:
                            _dlog(f"  [DBG] erro ao ler {_tp}: {_e}")
                return None

            vercel_token = _find_vercel_token()
            if not vercel_token:
                _dlog("  ⚠️  Login do Vercel necessário — uma janela vai abrir.", "err")
                _dlog("  → Faça login com GitHub no navegador e aguarde a janela fechar sozinha.")
                _lproc = subprocess.Popen(
                    ["cmd.exe", "/c", "(echo.&echo.&echo.&echo.&echo.&echo.&echo.&echo.&echo.&echo.) | npx --yes vercel login"],
                    env={**os.environ, "NO_UPDATE_NOTIFIER": "1"},
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
                _lproc.wait()
                vercel_token = _find_vercel_token()
                if not vercel_token:
                    _dlog("  [DBG] token ainda não encontrado após login", "err")

            _vcmd = ["npx", "--yes", "vercel", "--prod", "--yes"]
            if vercel_token:
                _vcmd += ["--token", vercel_token]

            # 1ª etapa: deploy inicial para criar/linkar o projeto no Vercel
            _dlog("  [DBG] 1º deploy — criando projeto no Vercel…")
            ok1, out1 = _run(_vcmd, cwd=DASHBOARD_DIR, timeout=300)
            _dlog(f"  [DBG] 1º deploy ok={ok1}")

            # Ler projectId do .vercel/project.json criado pelo deploy
            _proj_json = os.path.join(DASHBOARD_DIR, ".vercel", "project.json")
            project_id = None
            if os.path.exists(_proj_json):
                try:
                    with open(_proj_json) as _f:
                        _pdata = json.load(_f)
                    project_id = _pdata.get("projectId")
                    _dlog(f"  [DBG] projectId={project_id}")
                except Exception as _e:
                    _dlog(f"  [DBG] erro ao ler project.json: {_e}")
            else:
                _dlog("  [DBG] .vercel/project.json NAO encontrado")

            # Setar env vars via REST API (sem CLI, sem travamento)
            if project_id and vercel_token:
                _dlog("  [DBG] configurando env vars via API…")
                env_vars = [
                    ("BACKEND_URL",        burl),
                    ("API_SECRET_KEY",     api_key),
                    ("DASHBOARD_PASSWORD", v["DASHBOARD_PASSWORD"]),
                    ("SESSION_SECRET",     sess_key),
                ]
                for _name, _val in env_vars:
                    try:
                        _url = f"https://api.vercel.com/v10/projects/{project_id}/env"
                        _body = json.dumps([{
                            "key": _name, "value": _val,
                            "target": ["production"], "type": "plain"
                        }]).encode()
                        _req = urllib.request.Request(_url, data=_body, method="POST")
                        _req.add_header("Authorization", f"Bearer {vercel_token}")
                        _req.add_header("Content-Type", "application/json")
                        with urllib.request.urlopen(_req, timeout=15) as _resp:
                            _dlog(f"  {_name}: OK (HTTP {_resp.status})")
                    except urllib.error.HTTPError as _he:
                        _rbody = _he.read().decode(errors="replace")
                        if _he.code == 409:
                            # Já existe — atualizar via PATCH
                            try:
                                _gurl = f"https://api.vercel.com/v9/projects/{project_id}/env"
                                _greq = urllib.request.Request(_gurl)
                                _greq.add_header("Authorization", f"Bearer {vercel_token}")
                                with urllib.request.urlopen(_greq, timeout=15) as _gr:
                                    _envs = json.loads(_gr.read()).get("envs", [])
                                _eid = next((e["id"] for e in _envs if e["key"] == _name), None)
                                if _eid:
                                    _purl = f"https://api.vercel.com/v9/projects/{project_id}/env/{_eid}"
                                    _pbody = json.dumps({"value": _val, "target": ["production"]}).encode()
                                    _preq = urllib.request.Request(_purl, data=_pbody, method="PATCH")
                                    _preq.add_header("Authorization", f"Bearer {vercel_token}")
                                    _preq.add_header("Content-Type", "application/json")
                                    with urllib.request.urlopen(_preq, timeout=15) as _pr:
                                        _dlog(f"  {_name}: atualizado (HTTP {_pr.status})")
                                else:
                                    _dlog(f"  {_name}: 409 mas ID nao encontrado")
                            except Exception as _pe:
                                _dlog(f"  {_name}: erro no PATCH — {_pe}")
                        else:
                            _dlog(f"  {_name}: ERRO HTTP {_he.code} — {_rbody[:200]}", "err")
                    except Exception as _ex:
                        _dlog(f"  {_name}: ERRO — {_ex}", "err")

                # 2ª etapa: redeploy com as env vars já configuradas
                _dlog("  [DBG] 2º deploy — com env vars configuradas…")
                ok, out = _run(_vcmd, cwd=DASHBOARD_DIR, timeout=300)
                _dlog(f"  [DBG] 2º deploy ok={ok}")
            else:
                ok, out = ok1, out1

            _set_step(2, "done" if ok else "error", out=out)

            match = re.search(r"https://[^\s]+\.vercel\.app", out)
            dash_url = match.group(0) if match else "https://vercel.com/dashboard"
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
                deploy_banner.pack(fill="x", pady=(0, 8), before=cards_frame),
            ))

        threading.Thread(target=deploy, daemon=True).start()
        return p

    # ══════════════════════════════════════════════════════════════════════════
    # Tela 9 — Pronto
    # ══════════════════════════════════════════════════════════════════════════
    def _page_done(self, urls):
        self._clear_progress()

        def _create_shortcut():
            try:
                update_exe = os.path.join(ROOT, "FinanceBotUpdate.exe")
                if not os.path.exists(update_exe) or DEMO:
                    return
                desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                lnk = os.path.join(desktop, "Atualizar Finance Bot.lnk")
                ps = (
                    f'$ws = New-Object -ComObject WScript.Shell; '
                    f'$s = $ws.CreateShortcut("{lnk}"); '
                    f'$s.TargetPath = "{update_exe}"; '
                    f'$s.WorkingDirectory = "{ROOT}"; '
                    f'$s.Description = "Atualizar Finance Bot"; '
                    f'$s.Save()'
                )
                subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                               capture_output=True, creationflags=NO_WIN, timeout=10)
            except Exception:
                pass

        threading.Thread(target=_create_shortcut, daemon=True).start()

        p = tk.Frame(self, bg=BG)
        self._header(p, "Tudo pronto! 🎉",
                     "Seu Finance Bot está no ar.", phase=4)

        _dash_url = urls.get("dashboard", "") or ("https://finance-bot-demo.vercel.app" if DEMO else "")
        _backend_url = urls.get("backend", "")
        _pw = self._var("DASHBOARD_PASSWORD").get()

        def _copy_pw():
            self.clipboard_clear()
            self.clipboard_append(_pw)

        # Toast notification
        toast_ref = [None]
        def _show_toast(msg, color=GREEN):
            if toast_ref[0] and toast_ref[0].winfo_exists():
                toast_ref[0].place_forget()
            t = tk.Label(p, text=msg, bg=color, fg="white",
                         font=(FONT, 9, "bold"), pady=6, padx=14)
            t.place(relx=0.5, y=self.H - 68, anchor="center")
            toast_ref[0] = t
            self.after(3000, lambda: t.place_forget() if t.winfo_exists() else None)

        def _do_export():
            from datetime import datetime as _dt
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            if DEMO:
                _b   = "https://finance-api-demo.fly.dev"
                _d   = "https://finance-bot-demo.vercel.app"
                _bot = "finance-bot-demo"
                _sub = "https://abcdefghij1234567890.supabase.co"
                _pro = "abcdefghij1234567890"
                _tok = "123456789:ABCdefGHIjklMNOpqrSTUvwxYZ123456"
                _ids = "987654321"
                _grq = "gsk_demoKeyForTestingPurposesOnly1234567890"
                _pw2 = "demo1234"
            else:
                _b   = urls.get("backend", "")
                _d   = urls.get("dashboard", "")
                _bot = urls.get("bot", "")
                _sub = self._var("SUPABASE_URL").get()
                _pro = self._var("SUPABASE_PROJECT_ID").get()
                _tok = self._var("TELEGRAM_BOT_TOKEN").get()
                _ids = self._var("TELEGRAM_USER_IDS").get()
                _grq = self._var("GROQ_API_KEY").get()
                _pw2 = _pw
            now = _dt.now()
            content = (
                f"Finance Bot — Credenciais (geradas em {now:%d/%m/%Y %H:%M})\n"
                f"{'─' * 53}\n"
                f"Painel web:         {_d}\n"
                f"Senha do painel:    {_pw2}\n"
                f"Backend:            {_b}\n"
                f"Bot Telegram:       {_bot}\n"
                f"\n"
                f"Supabase URL:       {_sub}\n"
                f"Supabase Project:   {_pro}\n"
                f"Telegram Bot Token: {_tok}\n"
                f"Telegram User IDs:  {_ids}\n"
                f"Groq API Key:       {_grq}\n"
            )
            base = f"FinanceBot-credenciais-{now:%Y%m%d}"
            path = os.path.join(desktop, base + ".txt")
            if os.path.exists(path):
                for n in range(2, 100):
                    candidate = os.path.join(desktop, f"{base}-{n}.txt")
                    if not os.path.exists(candidate):
                        path = candidate
                        break
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                subprocess.Popen(["notepad.exe", path])
                self.after(0, lambda: _show_toast("✓  Arquivo salvo no Desktop"))
            except Exception as e:
                self.after(0, lambda err=e: _show_toast(f"Erro: {err}", RED))

        _exported = [False]

        def _export_credentials():
            _exported[0] = True
            threading.Thread(target=_do_export, daemon=True).start()

        def _confirm_close():
            if not _exported[0]:
                from tkinter import messagebox
                if not messagebox.askyesno(
                    "Fechar sem exportar?",
                    "Você ainda não exportou as credenciais.\n\n"
                    "Sem elas, não será possível recuperar a senha do painel "
                    "ou reconfigurar o bot no futuro.\n\n"
                    "Fechar mesmo assim?",
                    icon="warning",
                ):
                    return
            self.destroy()

        self._footer(p,
                     next_fn=lambda: webbrowser.open(_dash_url) or None,
                     next_label="Abrir painel web  →",
                     extra_btns=[
                         ("Exportar credenciais", _export_credentials, PANEL2),
                         ("Fechar", _confirm_close, PANEL),
                     ])

        body = tk.Frame(p, bg=BG)
        body.pack(fill="both", expand=True, padx=32, pady=(10, 0))

        # ── Status cards (backend + telegram) — lado a lado ──────────────────
        _tg_token   = self._var("TELEGRAM_BOT_TOKEN").get().strip()
        _tg_user_id = self._var("TELEGRAM_USER_IDS").get().strip().split(",")[0].strip()

        status_row = tk.Frame(body, bg=BG)
        status_row.pack(fill="x", pady=(0, 6))

        def _make_status_card(parent, init_text, retry_label, side_pad):
            col = tk.Frame(parent, bg=BG)
            col.pack(side="left", fill="x", expand=True, padx=side_pad)
            card = tk.Frame(col, bg=PANEL, pady=6, padx=12)
            card.pack(fill="x")
            row = tk.Frame(card, bg=PANEL)
            row.pack(fill="x")
            icon  = tk.Label(row, text="⏳", bg=PANEL, font=(FONT, 12), width=3)
            icon.pack(side="left")
            info  = tk.Frame(row, bg=PANEL)
            info.pack(side="left", fill="x", expand=True)
            title = tk.Label(info, text=init_text, bg=PANEL, fg=MUTED,
                             font=(FONT, 9, "bold"), wraplength=240, justify="left")
            title.pack(anchor="w")
            sub   = tk.Label(info, text="", bg=PANEL, fg=DIM, font=(FONT, 8))
            sub.pack(anchor="w")
            btn   = tk.Button(row, text=retry_label, bg=PANEL2, fg=MUTED,
                              relief="flat", font=(FONT, 8), padx=6, pady=3,
                              cursor="hand2")
            btn.pack(side="right")
            return icon, title, sub, btn

        if _backend_url:
            h_icon, h_title, h_sub, h_retry = _make_status_card(
                status_row, "Verificando backend…", "↺ Testar", (0, 6))

            def _do_health():
                h_icon.config(text="⏳"); h_title.config(text="Verificando backend…", fg=MUTED)
                h_retry.config(state="disabled")
                def _check():
                    try:
                        import urllib.request
                        url = (_backend_url.rstrip("/") + "/health") if not DEMO else None
                        if DEMO:
                            import time; time.sleep(1.2)
                            ok, detail = True, "200 OK"
                        else:
                            req = urllib.request.urlopen(url, timeout=12)
                            ok, detail = req.status == 200, f"{req.status} OK"
                    except Exception as e:
                        ok, detail = False, str(e)[:50]
                    def _upd():
                        if ok:
                            h_icon.config(text="✅", fg=GREEN)
                            h_title.config(text="Backend online", fg=GREEN)
                            h_sub.config(text=detail, fg=DIM)
                        else:
                            h_icon.config(text="⚠️", fg=YELLOW)
                            h_title.config(text="Backend não respondeu", fg=YELLOW)
                            h_sub.config(text=detail or "Pode levar ~1 min após o deploy", fg=DIM)
                        h_retry.config(state="normal")
                    self.after(0, _upd)
                threading.Thread(target=_check, daemon=True).start()

            h_retry.config(command=_do_health)
            self.after(800, _do_health)

        if _tg_token and _tg_user_id:
            t_icon, t_title, t_sub, t_retry = _make_status_card(
                status_row, "Enviando teste…", "↺ Reenviar", (6, 0))

            def _do_tg_test():
                t_icon.config(text="⏳")
                t_title.config(text="Enviando teste…", fg=MUTED)
                t_retry.config(state="disabled")
                def _send():
                    try:
                        if DEMO:
                            import time; time.sleep(1.0)
                            ok, detail = True, f"Chat ID {_tg_user_id}"
                        else:
                            import urllib.request, urllib.parse
                            msg = "✅ Finance Bot configurado com sucesso! Esta mensagem confirma que o bot está funcionando."
                            data = urllib.parse.urlencode({
                                "chat_id": _tg_user_id, "text": msg
                            }).encode()
                            req = urllib.request.urlopen(
                                f"https://api.telegram.org/bot{_tg_token}/sendMessage",
                                data=data, timeout=10)
                            ok = req.status == 200
                            detail = f"Chat ID {_tg_user_id}"
                    except Exception as e:
                        ok, detail = False, str(e)[:50]
                    def _upd():
                        if ok:
                            t_icon.config(text="✅", fg=GREEN)
                            t_title.config(text="Telegram funcionando!", fg=GREEN)
                            t_sub.config(text=detail, fg=DIM)
                        else:
                            t_icon.config(text="⚠️", fg=YELLOW)
                            t_title.config(text="Falha no envio", fg=YELLOW)
                            t_sub.config(text=detail or "Verifique token e ID", fg=DIM)
                        t_retry.config(state="normal")
                    self.after(0, _upd)
                threading.Thread(target=_send, daemon=True).start()

            t_retry.config(command=_do_tg_test)
            self.after(1600, _do_tg_test)

        url_row = tk.Frame(body, bg=BG)
        url_row.pack(fill="x", pady=(0, 4))
        for col_idx, (icon, label, url_key) in enumerate([
            ("🌐", "Painel web", "dashboard"),
            ("⚙️", "Backend", "backend"),
        ]):
            url = urls.get(url_key, "")
            if not url:
                continue
            col = tk.Frame(url_row, bg=BG)
            col.pack(side="left", fill="x", expand=True,
                     padx=(0, 8) if col_idx == 0 else (8, 0))
            card = tk.Frame(col, bg=PANEL, pady=10, padx=14)
            card.pack(fill="x")
            tk.Label(card, text=f"{icon}  {label}", bg=PANEL, fg=MUTED,
                     font=(FONT, 9)).pack(anchor="w")
            url_lbl = tk.Label(card, text=url, bg=PANEL, fg=GREEN,
                               font=("Consolas", 9), wraplength=290, justify="left")
            url_lbl.pack(anchor="w", pady=(3, 0))
            btns = tk.Frame(card, bg=PANEL)
            btns.pack(anchor="w", pady=(6, 0))
            def _copy(u=url):
                self.clipboard_clear(); self.clipboard_append(u)
            tk.Button(btns, text="Abrir  →",
                      command=lambda u=url: webbrowser.open(u),
                      bg=BLUE, fg="white", relief="flat",
                      font=(FONT, 9, "bold"), padx=10, pady=4,
                      cursor="hand2").pack(side="left", padx=(0, 6))
            tk.Button(btns, text="Copiar", command=_copy,
                      bg=PANEL2, fg=MUTED, relief="flat",
                      font=(FONT, 8), padx=8, pady=4, cursor="hand2").pack(side="left")

        # ── Senha do painel ───────────────────────────────────────────────────
        pw_bar = tk.Frame(body, bg="#7c2d12", pady=8, padx=14)
        pw_bar.pack(fill="x", pady=(8, 0))
        pw_left = tk.Frame(pw_bar, bg="#7c2d12")
        pw_left.pack(side="left", fill="x", expand=True)
        tk.Label(pw_left,
                 text="🔑  Senha do painel:",
                 bg="#7c2d12", fg="#fed7aa", font=(FONT, 9, "bold")).pack(anchor="w")
        tk.Label(pw_left,
                 text="Armazene em local seguro — o painel pode requisitá-la de forma esporádica.",
                 bg="#7c2d12", fg="#fed7aa", font=(FONT, 8)).pack(anchor="w")
        tk.Button(pw_bar, text="Copiar senha", command=_copy_pw,
                  bg="#9a3412", fg="#fed7aa", activebackground="#7c2d12",
                  activeforeground="white", relief="flat",
                  font=(FONT, 9, "bold"), padx=12, pady=6,
                  cursor="hand2").pack(side="right", padx=(8, 0))

        tk.Label(body, text="Próximos passos:", bg=BG, fg=TEXT,
                 font=(FONT, 11, "bold")).pack(anchor="w", pady=(10, 4))
        for num, step in [
            ("1", "Abra o Telegram, encontre seu bot pelo nome e clique em START."),
            ("2", "Mande uma mensagem como:  gastei 50 reais no mercado."),
            ("3", "Acesse o painel web e entre com a senha que você definiu."),
            ("4", "Cadastre seus cartões no painel antes de usar."),
            ("5", "Para atualizar no futuro, execute o  FinanceBotUpdate.exe."),
        ]:
            row = tk.Frame(body, bg=BG)
            row.pack(anchor="w", pady=1)
            tk.Label(row, text=f"  {num}.", bg=BG, fg=BLUE,
                     font=(FONT, 9, "bold"), width=4).pack(side="left")
            tk.Label(row, text=step, bg=BG, fg=MUTED, font=(FONT, 9)).pack(side="left")

        return p


if __name__ == "__main__":
    if sys.platform == "win32":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor DPI
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass
    app = Wizard()
    app.mainloop()
