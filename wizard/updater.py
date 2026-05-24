"""Finance Bot — Updater"""

import sys
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog
import json
import os
import re
import subprocess
import threading
import urllib.request

from PIL import Image, ImageTk

GITHUB_REPO = "arthur-oli/finance-bot"
APPDATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "FinanceBot")
CONFIG_JSON = os.path.join(APPDATA_DIR, "config.json")


def _asset(name):
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, "assets", name)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", name)

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

NO_WIN = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def _check_cmd(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=10, creationflags=NO_WIN)
        return r.returncode == 0
    except Exception:
        return False


def _popen(args, cwd=None):
    env = {**os.environ, "NO_UPDATE_NOTIFIER": "1"}
    return subprocess.Popen(
        args, cwd=cwd, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace", creationflags=NO_WIN,
    )


def _read_toml_app(toml_path):
    """Extrai o nome do app de um fly.toml."""
    try:
        with open(toml_path, encoding="utf-8") as f:
            m = re.search(r'^app\s*=\s*["\']?([A-Za-z0-9_-]+)', f.read(), re.MULTILINE)
            return m.group(1) if m else ""
    except Exception:
        return ""


def _parse_credentials(path):
    """Extrai campos do arquivo de credenciais exportado pelo wizard."""
    fields = {}
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        patterns = {
            "backend_app":  r"Backend:\s+https://([A-Za-z0-9_-]+)\.fly\.dev",
            "bot_app":      r"Bot Telegram:\s+([A-Za-z0-9_-]+)",
            "database_url": r"Database URL:\s+(postgresql://\S+)",
            "install_path": r"Pasta local:\s+(.+)",
        }
        for key, pat in patterns.items():
            m = re.search(pat, text)
            if m:
                fields[key] = m.group(1).strip()
    except Exception:
        pass
    return fields


def _changed_components(install_path, old_tag, new_tag):
    """Retorna set de componentes alterados entre duas tags: schema, backend, bot, dashboard."""
    try:
        r = subprocess.run(
            ["git", "-C", install_path, "diff", "--name-only", old_tag, new_tag],
            capture_output=True, text=True, timeout=30, creationflags=NO_WIN,
        )
        if r.returncode != 0:
            raise RuntimeError(r.stderr)
        files = set(r.stdout.strip().splitlines())
        out = set()
        for f in files:
            if f == "schema.sql":
                out.add("schema")
            if f.startswith("backend/"):
                out.add("backend")
            if f.startswith(("bot/", "Dockerfile.bot")) or f in ("fly.toml", "requirements.txt"):
                out.add("bot")
            if f.startswith("dashboard/") and "node_modules" not in f:
                out.add("dashboard")
        # Se nenhum componente de código mudou, atualiza apenas a versão
        return out
    except Exception:
        # Se não conseguir diff, atualiza tudo por segurança
        return {"schema", "backend", "bot", "dashboard"}


class Updater(tk.Tk):
    W, H = 640, 540

    def __init__(self):
        super().__init__()
        self.title("Finance Bot — Atualização")
        self.geometry(f"{self.W}x{self.H}")
        self.resizable(False, False)
        self.configure(bg=BG)
        self._config  = {}
        self._release = {}
        try:
            _logo = Image.open(_asset("finance-bot-logo.png")).convert("RGBA")
            _icon_imgs = [ImageTk.PhotoImage(_logo.resize((s, s), Image.LANCZOS))
                          for s in (16, 32, 48, 64, 128, 256)]
            self.iconphoto(True, *_icon_imgs)
            self._icon_refs = _icon_imgs
        except Exception:
            pass
        self._center()
        self._build_ui()
        threading.Thread(target=self._check, daemon=True).start()

    def _center(self):
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - self.W) // 2
        y = (self.winfo_screenheight() - self.H) // 2
        self.geometry(f"{self.W}x{self.H}+{x}+{y}")

    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg=BG, pady=20, padx=32)
        hdr.pack(fill="x")
        try:
            _pil = Image.open(_asset("finance-bot-logo.png")).convert("RGBA")
            self._hdr_logo = ImageTk.PhotoImage(_pil.resize((48, 48), Image.LANCZOS))
            tk.Label(hdr, image=self._hdr_logo, bg=BG).pack(side="left", padx=(0, 14))
        except Exception:
            pass
        col = tk.Frame(hdr, bg=BG)
        col.pack(side="left")
        tk.Label(col, text="Finance Bot", bg=BG, fg=TEXT,
                 font=(FONT, 18, "bold")).pack(anchor="w")
        tk.Label(col, text="Verificador de atualizações", bg=BG, fg=MUTED,
                 font=(FONT, 10)).pack(anchor="w")

        # Status card
        self._status_card = tk.Frame(self, bg=PANEL, pady=18, padx=20)
        self._status_card.pack(fill="x", padx=32)

        self._icon_lbl = tk.Label(self._status_card, text="⏳", bg=PANEL,
                                   font=(FONT, 22), width=3)
        self._icon_lbl.pack(side="left")

        col2 = tk.Frame(self._status_card, bg=PANEL)
        col2.pack(side="left", fill="x", expand=True)
        self._title_lbl = tk.Label(col2, text="Verificando atualizações…",
                                    bg=PANEL, fg=TEXT, font=(FONT, 12, "bold"))
        self._title_lbl.pack(anchor="w")
        self._sub_lbl = tk.Label(col2, text="", bg=PANEL, fg=DIM, font=(FONT, 9),
                                  wraplength=420, justify="left")
        self._sub_lbl.pack(anchor="w")

        # Import credentials panel (hidden until needed)
        self._import_frame = tk.Frame(self, bg=BG)
        tk.Label(self._import_frame,
                 text="Importe o arquivo de credenciais exportado pelo wizard para continuar.",
                 bg=BG, fg=MUTED, font=(FONT, 9), wraplength=560, justify="left").pack(
            anchor="w", padx=32, pady=(10, 4))
        import_row = tk.Frame(self._import_frame, bg=BG)
        import_row.pack(anchor="w", padx=32)
        self._import_path_lbl = tk.Label(import_row, text="Nenhum arquivo selecionado",
                                          bg=BG, fg=DIM, font=("Consolas", 8))
        self._import_path_lbl.pack(side="left")
        tk.Button(import_row, text="Selecionar credenciais…",
                  command=self._pick_credentials,
                  bg=PANEL2, fg=TEXT, activebackground=PANEL, activeforeground=TEXT,
                  relief="flat", font=(FONT, 9), padx=10, pady=6,
                  cursor="hand2").pack(side="right")

        folder_row = tk.Frame(self._import_frame, bg=BG)
        folder_row.pack(anchor="w", padx=32, pady=(6, 0))
        self._folder_lbl = tk.Label(folder_row, text="Nenhuma pasta selecionada",
                                     bg=BG, fg=DIM, font=("Consolas", 8))
        self._folder_lbl.pack(side="left")
        tk.Button(folder_row, text="Selecionar pasta do bot…",
                  command=self._pick_folder,
                  bg=PANEL2, fg=TEXT, activebackground=PANEL, activeforeground=TEXT,
                  relief="flat", font=(FONT, 9), padx=10, pady=6,
                  cursor="hand2").pack(side="right")

        self._import_apply_btn = tk.Button(
            self._import_frame, text="Salvar e verificar atualizações",
            command=self._apply_import,
            bg=PANEL2, fg=TEXT, activebackground=BLUE, activeforeground="white",
            disabledforeground=DIM,
            relief="flat", font=(FONT, 10, "bold"), padx=16, pady=9,
            cursor="hand2", state="disabled")
        self._import_apply_btn.pack(anchor="w", padx=32, pady=(8, 0))

        self._import_data = {}   # parsed from credentials file
        self._import_folder = tk.StringVar()

        # Changelog (hidden until update is available)
        self._changelog_frame = tk.Frame(self, bg=BG)
        tk.Label(self._changelog_frame, text="O que há de novo:",
                 bg=BG, fg=TEXT, font=(FONT, 10, "bold")).pack(
            anchor="w", padx=32, pady=(12, 4))
        self._changelog_box = scrolledtext.ScrolledText(
            self._changelog_frame, bg=PANEL, fg=MUTED,
            font=("Consolas", 9), relief="flat", state="disabled",
            height=6, wrap="word")
        self._changelog_box.pack(fill="x", padx=32)

        # Log area (hidden until update runs)
        self._log_frame = tk.Frame(self, bg=BG)
        tk.Label(self._log_frame, text="Progresso:", bg=BG, fg=TEXT,
                 font=(FONT, 10, "bold")).pack(anchor="w", padx=32, pady=(12, 4))
        self._log_box = scrolledtext.ScrolledText(
            self._log_frame, bg=PANEL, fg=MUTED,
            font=("Consolas", 8), relief="flat", state="disabled", height=8)
        self._log_box.pack(fill="x", padx=32)
        self._log_box.tag_config("ok",  foreground=GREEN)
        self._log_box.tag_config("err", foreground=RED)
        self._log_box.tag_config("hdr", foreground=YELLOW)

        # Footer
        ttk.Separator(self).pack(fill="x", side="bottom")
        footer = tk.Frame(self, bg=BG)
        footer.pack(fill="x", padx=32, pady=14, side="bottom")

        self._close_btn = tk.Button(
            footer, text="Fechar", command=self.destroy,
            bg=PANEL2, fg=TEXT, activebackground=PANEL, activeforeground=TEXT,
            relief="flat", font=(FONT, 10), padx=18, pady=9, cursor="hand2")
        self._close_btn.pack(side="left")

        self._action_btn = tk.Button(
            footer, text="Atualizar agora",
            command=self._do_update,
            bg=PANEL2, fg=TEXT, activebackground=BLUE2, activeforeground="white",
            disabledforeground=DIM,
            relief="flat", font=(FONT, 11, "bold"), padx=28, pady=11,
            cursor="hand2", state="disabled")
        self._action_btn.pack(side="right")

    # ── Credentials import ────────────────────────────────────────────────────

    def _pick_credentials(self):
        path = filedialog.askopenfilename(
            title="Selecionar arquivo de credenciais",
            filetypes=[("Arquivo de texto", "*.txt"), ("Todos os arquivos", "*.*")],
            initialdir=os.path.expanduser("~\\Desktop"),
        )
        if not path:
            return
        self._import_data = _parse_credentials(path)
        self._import_path_lbl.config(text=os.path.basename(path), fg=MUTED)
        self._refresh_import_btn()

    def _pick_folder(self):
        path = filedialog.askdirectory(
            title="Selecionar pasta de instalação do Finance Bot",
            initialdir=os.path.expanduser("~"),
        )
        if not path:
            return
        self._import_folder.set(path)
        self._folder_lbl.config(text=path, fg=MUTED)
        self._refresh_import_btn()

    def _refresh_import_btn(self):
        has_folder = bool(self._import_folder.get())
        if has_folder:
            self._import_apply_btn.config(state="normal", bg=BLUE, fg="white")
        else:
            self._import_apply_btn.config(state="disabled", bg=PANEL2, fg=TEXT)

    def _apply_import(self):
        install_path = self._import_folder.get()
        if not install_path:
            return

        cfg = dict(self._config)  # keep existing fields if any
        cfg["install_path"] = install_path
        if not cfg.get("version"):
            cfg["version"] = "0.0.0"

        for key in ("backend_app", "bot_app", "database_url"):
            val = self._import_data.get(key, "")
            if val:
                cfg[key] = val

        try:
            os.makedirs(APPDATA_DIR, exist_ok=True)
            with open(CONFIG_JSON, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
        except Exception as e:
            self._set_status("❌", "Erro ao salvar configuração", str(e), error=True)
            return

        self._import_frame.pack_forget()
        self._config = cfg
        threading.Thread(target=self._check, daemon=True).start()

    # ── Status helpers ────────────────────────────────────────────────────────

    def _log(self, text, tag=None):
        self._log_box.config(state="normal")
        self._log_box.insert("end", text + "\n", tag or "")
        self._log_box.see("end")
        self._log_box.config(state="disabled")

    def _set_status(self, icon, title, sub="", error=False):
        self._icon_lbl.config(text=icon)
        self._title_lbl.config(text=title, fg=RED if error else TEXT)
        self._sub_lbl.config(text=sub)

    def _show_changelog(self, text):
        self._changelog_box.config(state="normal")
        self._changelog_box.delete("1.0", "end")
        self._changelog_box.insert("end", text or "(sem notas de versão)")
        self._changelog_box.config(state="disabled")
        self._changelog_frame.pack(fill="x", after=self._status_card)

    # ── Check ─────────────────────────────────────────────────────────────────

    def _check(self):
        # Reset UI state for re-check after import
        self.after(0, lambda: (
            self._set_status("⏳", "Verificando atualizações…"),
            self._action_btn.config(state="disabled", text="Atualizar agora", bg=PANEL2, fg=TEXT),
            self._changelog_frame.pack_forget(),
            self._log_frame.pack_forget(),
        ))

        try:
            with open(CONFIG_JSON, encoding="utf-8") as f:
                self._config = json.load(f)
        except Exception:
            self.after(0, lambda: (
                self._set_status("⚠️", "Configuração não encontrada",
                                  "Importe o arquivo de credenciais exportado pelo wizard."),
                self._import_frame.pack(fill="x", after=self._status_card),
            ))
            return

        install_path = self._config.get("install_path", "")
        if not install_path or not os.path.isdir(install_path):
            self.after(0, lambda: (
                self._set_status("⚠️", "Pasta de instalação não encontrada",
                                  "Selecione a pasta onde o Finance Bot foi instalado."),
                self._import_frame.pack(fill="x", after=self._status_card),
            ))
            return

        current = self._config.get("version", "0.0.0")
        notes = []
        if not self._config.get("database_url"):
            notes.append("migração de schema manual necessária")
        sub = f"Versão atual: v{current}"
        if notes:
            sub += f"  —  {', '.join(notes)}"
        self.after(0, lambda: self._sub_lbl.config(text=sub))

        try:
            req = urllib.request.Request(
                f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest",
                headers={"Accept": "application/vnd.github+json",
                         "User-Agent": "FinanceBotUpdater/1.0"},
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                self._release = json.loads(r.read().decode())
        except Exception as e:
            self.after(0, lambda: self._set_status(
                "❌", "Erro ao verificar atualizações",
                f"Verifique sua conexão com a internet.\n({e})", error=True))
            return

        tag      = self._release.get("tag_name", "")
        latest   = tag.lstrip("v")
        changelog = self._release.get("body", "")

        if latest == current:
            self.after(0, lambda: self._set_status(
                "✅", "Você já tem a versão mais recente",
                f"v{current} — Finance Bot está atualizado."))
        else:
            self.after(0, lambda: (
                self._set_status(
                    "🔄", f"Nova versão disponível: v{latest}",
                    f"Você tem v{current}. Clique em Atualizar agora para instalar v{latest}."),
                self._show_changelog(changelog),
                self._action_btn.config(state="normal", bg=BLUE, fg="white"),
            ))

    # ── Update ────────────────────────────────────────────────────────────────

    def _do_update(self):
        self._action_btn.config(state="disabled", text="Atualizando…", bg=PANEL2, fg=TEXT)
        self._changelog_frame.pack_forget()
        self._log_frame.pack(fill="x", after=self._status_card)
        self._set_status("⏳", "Atualizando…", "Não feche esta janela.")

        tag           = self._release.get("tag_name", "")
        version       = tag.lstrip("v")
        current       = self._config.get("version", "0.0.0")
        old_tag       = f"v{current}"
        install_path  = self._config.get("install_path", "")
        database_url  = self._config.get("database_url", "")
        backend_dir   = os.path.join(install_path, "backend")
        dashboard_dir = os.path.join(install_path, "dashboard")

        # Lê app names do config; se ausentes, tenta fly.toml ANTES do checkout
        backend_app = self._config.get("backend_app", "") or \
                      _read_toml_app(os.path.join(backend_dir, "fly.toml"))
        bot_app     = self._config.get("bot_app", "") or \
                      _read_toml_app(os.path.join(install_path, "fly.toml"))

        def _run(args, cwd=None):
            proc = _popen(args, cwd=cwd)
            for line in proc.stdout:
                line = line.rstrip()
                tag_ = "err" if re.search(r"\b(error|failed|fatal)\b", line, re.I) else None
                self.after(0, lambda l=line, t=tag_: self._log(l, t))
            proc.wait()
            return proc.returncode == 0

        def _fail(msg):
            self.after(0, lambda: (
                self._log(msg, "err"),
                self._set_status("❌", "Erro na atualização", msg, error=True),
                self._action_btn.config(state="normal", text="Tentar novamente",
                                        bg=BLUE, fg="white", command=self._do_update),
            ))

        def _thread():
            # ── 1. Verificar ferramentas ──────────────────────────────────────
            self.after(0, lambda: self._log("\n── Verificando ferramentas ──", "hdr"))
            if not _check_cmd(["fly", "version"]):
                _fail("Fly CLI não encontrado. Reinstale em fly.io/docs/flyctl/install")
                return
            if not _check_cmd(["node", "--version"]):
                _fail("Node.js não encontrado. Reinstale em nodejs.org")
                return
            self.after(0, lambda: self._log("  Fly CLI e Node.js OK", "ok"))

            if not _check_cmd(["fly", "auth", "whoami"]):
                _fail("Você não está logado no Fly.io.\nAbra um terminal e execute: fly auth login")
                return
            if not _check_cmd(["npx", "vercel", "whoami"]):
                _fail("Você não está logado na Vercel.\nAbra um terminal e execute: npx vercel login")
                return
            self.after(0, lambda: self._log("  Autenticação OK", "ok"))

            # ── 2. Baixar código novo ─────────────────────────────────────────
            self.after(0, lambda: self._log(f"\n── Baixando v{version} ──", "hdr"))
            if not _run(["git", "-C", install_path, "fetch", "--all", "--tags"]):
                _fail("Erro no git fetch. Verifique sua conexão.")
                return

            # Detecta o que mudou ANTES de resetar o working tree
            components = _changed_components(install_path, old_tag, tag)
            if components:
                self.after(0, lambda c=components: self._log(
                    f"  Componentes alterados: {', '.join(sorted(c))}", "ok"))
            else:
                self.after(0, lambda: self._log(
                    "  Nenhum componente de código alterado — apenas versão será atualizada.", "ok"))

            # --force descarta alterações locais em fly.toml (modificadas pelo wizard)
            if not _run(["git", "-C", install_path, "checkout", tag, "--force"]):
                _fail("Erro no git checkout.")
                return
            self.after(0, lambda: self._log(f"  Código v{version} baixado.", "ok"))

            # ── 3. Schema migration ───────────────────────────────────────────
            if "schema" in components:
                self.after(0, lambda: self._log("\n── Atualizando banco de dados ──", "hdr"))
                if database_url:
                    schema_path = os.path.join(install_path, "schema.sql")
                    if os.path.exists(schema_path):
                        try:
                            import psycopg2
                            with open(schema_path, encoding="utf-8") as f:
                                sql = f.read()
                            conn = psycopg2.connect(database_url, connect_timeout=15)
                            conn.autocommit = True
                            with conn.cursor() as cur:
                                cur.execute(sql)
                            conn.close()
                            self.after(0, lambda: self._log("  Schema aplicado com sucesso.", "ok"))
                        except Exception as e:
                            self.after(0, lambda err=e: self._log(
                                f"  ⚠️  Falha ao aplicar schema: {err}", "err"))
                            self.after(0, lambda: self._log(
                                "  Continuando — o backend pode ter erros se houver novas tabelas.", "err"))
                    else:
                        self.after(0, lambda: self._log("  schema.sql não encontrado.", "err"))
                else:
                    self.after(0, lambda: self._log(
                        "  ⚠️  database_url ausente — aplique schema.sql manualmente no Supabase.", "err"))

            # ── 4. Backend API ────────────────────────────────────────────────
            if "backend" in components:
                self.after(0, lambda: self._log("\n── Atualizando backend ──", "hdr"))
                args = ["fly", "deploy", "--wait-timeout", "180"]
                if backend_app:
                    args += ["--app", backend_app]
                if not _run(args, cwd=backend_dir):
                    _fail("Erro no deploy do backend.")
                    return
            else:
                self.after(0, lambda: self._log("\n  Backend sem alterações — deploy ignorado.", "ok"))

            # ── 5. Bot Telegram ───────────────────────────────────────────────
            if "bot" in components:
                self.after(0, lambda: self._log("\n── Atualizando bot ──", "hdr"))
                args = ["fly", "deploy", "--wait-timeout", "180"]
                if bot_app:
                    args += ["--app", bot_app]
                if not _run(args, cwd=install_path):
                    _fail("Erro no deploy do bot.")
                    return
            else:
                self.after(0, lambda: self._log("  Bot sem alterações — deploy ignorado.", "ok"))

            # ── 6. Dashboard ──────────────────────────────────────────────────
            if "dashboard" in components:
                self.after(0, lambda: self._log("\n── Atualizando painel ──", "hdr"))
                if not _run(["npx", "vercel", "--prod", "--yes"], cwd=dashboard_dir):
                    _fail("Erro no deploy do dashboard.")
                    return
            else:
                self.after(0, lambda: self._log("  Painel sem alterações — deploy ignorado.", "ok"))

            # ── 7. Salvar versão ──────────────────────────────────────────────
            self._config["version"] = version
            if backend_app and not self._config.get("backend_app"):
                self._config["backend_app"] = backend_app
            if bot_app and not self._config.get("bot_app"):
                self._config["bot_app"] = bot_app
            try:
                os.makedirs(APPDATA_DIR, exist_ok=True)
                with open(CONFIG_JSON, "w", encoding="utf-8") as f:
                    json.dump(self._config, f, indent=2)
            except Exception:
                pass

            self.after(0, lambda: (
                self._log(f"\n✅  Atualização para v{version} concluída!", "ok"),
                self._set_status("✅", f"Finance Bot v{version} instalado!",
                                 "Seu bot já está rodando a versão mais recente."),
                self._action_btn.config(state="disabled", bg=PANEL2, fg=TEXT),
                self._close_btn.config(text="Fechar", bg=BLUE, fg="white"),
            ))

        threading.Thread(target=_thread, daemon=True).start()


if __name__ == "__main__":
    app = Updater()
    app.mainloop()
