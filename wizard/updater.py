"""Finance Bot — Updater"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import json
import os
import re
import subprocess
import threading
import urllib.request

GITHUB_REPO = "arthur-oli/finance-bot"
APPDATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "FinanceBot")
CONFIG_JSON = os.path.join(APPDATA_DIR, "config.json")

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


class Updater(tk.Tk):
    W, H = 640, 500

    def __init__(self):
        super().__init__()
        self.title("Finance Bot — Atualização")
        self.geometry(f"{self.W}x{self.H}")
        self.resizable(False, False)
        self.configure(bg=BG)
        self._config  = {}
        self._release = {}
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
        c = tk.Canvas(hdr, width=48, height=48, bg=BG, highlightthickness=0)
        c.pack(side="left", padx=(0, 14))
        c.create_oval(2, 2, 46, 46, fill="white", outline="")
        c.create_text(24, 24, text="$", font=(FONT, 22, "bold"), fill=BG)
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
        self._sub_lbl = tk.Label(col2, text="", bg=PANEL, fg=DIM, font=(FONT, 9))
        self._sub_lbl.pack(anchor="w")

        # Changelog (hidden until update is available)
        self._changelog_frame = tk.Frame(self, bg=BG)
        tk.Label(self._changelog_frame, text="O que há de novo:",
                 bg=BG, fg=TEXT, font=(FONT, 10, "bold")).pack(
            anchor="w", padx=32, pady=(12, 4))
        self._changelog_box = scrolledtext.ScrolledText(
            self._changelog_frame, bg=PANEL, fg=MUTED,
            font=("Consolas", 9), relief="flat", state="disabled",
            height=7, wrap="word")
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
            bg=BLUE, fg="white", activebackground=BLUE2, activeforeground="white",
            relief="flat", font=(FONT, 11, "bold"), padx=28, pady=11,
            cursor="hand2", state="disabled")
        self._action_btn.pack(side="right")

    def _log(self, text, tag=None):
        self._log_box.config(state="normal")
        self._log_box.insert("end", text + "\n", tag or "")
        self._log_box.see("end")
        self._log_box.config(state="disabled")

    def _set_status(self, icon, title, sub, error=False):
        self._icon_lbl.config(text=icon)
        self._title_lbl.config(text=title, fg=RED if error else TEXT)
        self._sub_lbl.config(text=sub)

    def _show_changelog(self, text):
        self._changelog_box.config(state="normal")
        self._changelog_box.delete("1.0", "end")
        self._changelog_box.insert("end", text or "(sem notas de versão)")
        self._changelog_box.config(state="disabled")
        self._changelog_frame.pack(fill="x", after=self._status_card)

    def _check(self):
        try:
            with open(CONFIG_JSON, encoding="utf-8") as f:
                self._config = json.load(f)
        except Exception as e:
            self.after(0, lambda: self._set_status(
                "❌", "Configuração não encontrada",
                f"Execute o FinanceBotSetup.exe primeiro.\n({e})", error=True))
            return

        current = self._config.get("version", "0.0.0")
        self.after(0, lambda: self._sub_lbl.config(text=f"Versão atual: v{current}"))

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
                self._action_btn.config(state="normal"),
            ))

    def _do_update(self):
        self._action_btn.config(state="disabled", text="Atualizando…")
        self._changelog_frame.pack_forget()
        self._log_frame.pack(fill="x", after=self._status_card)
        self._set_status("⏳", "Atualizando…", "Não feche esta janela.")

        tag          = self._release.get("tag_name", "")
        version      = tag.lstrip("v")
        install_path = self._config.get("install_path", "")
        backend_dir  = os.path.join(install_path, "backend")
        dashboard_dir = os.path.join(install_path, "dashboard")

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
                                        command=self._do_update),
            ))

        def _thread():
            self.after(0, lambda: self._log("\n── Verificando ferramentas ──", "hdr"))
            if not _check_cmd(["fly", "version"]):
                _fail("Fly CLI não encontrado. Reinstale em fly.io/docs/flyctl/install")
                return
            if not _check_cmd(["node", "--version"]):
                _fail("Node.js não encontrado. Reinstale em nodejs.org")
                return
            self.after(0, lambda: self._log("  Fly CLI e Node.js OK", "ok"))

            self.after(0, lambda: self._log(f"\n── Baixando v{version} ──", "hdr"))
            if not _run(["git", "-C", install_path, "fetch", "--all", "--tags"]):
                _fail("Erro no git fetch. Verifique sua conexão.")
                return
            if not _run(["git", "-C", install_path, "checkout", tag]):
                _fail("Erro no git checkout.")
                return
            self.after(0, lambda: self._log(f"  Código v{version} baixado.", "ok"))

            self.after(0, lambda: self._log("\n── Atualizando backend ──", "hdr"))
            if not _run(["fly", "deploy", "--wait-timeout", "180"], cwd=backend_dir):
                _fail("Erro no deploy do backend.")
                return

            self.after(0, lambda: self._log("\n── Atualizando bot ──", "hdr"))
            if not _run(["fly", "deploy", "--wait-timeout", "180"], cwd=install_path):
                _fail("Erro no deploy do bot.")
                return

            self.after(0, lambda: self._log("\n── Atualizando painel ──", "hdr"))
            if not _run(["npx", "vercel", "--prod", "--yes"], cwd=dashboard_dir):
                _fail("Erro no deploy do dashboard.")
                return

            self._config["version"] = version
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
                self._action_btn.config(state="disabled"),
                self._close_btn.config(text="Fechar", bg=BLUE, fg="white"),
            ))

        threading.Thread(target=_thread, daemon=True).start()


if __name__ == "__main__":
    app = Updater()
    app.mainloop()
