"""Finestra principale di PianificatoreFiscale (stesso design di HrPayrollGest)."""
from __future__ import annotations

import os
import subprocess
import sys

import customtkinter as ctk

from appinfo import get_app_dir
from models.theme import C, apply_theme
from views.widgets import GhostButton, StatusBar

_VOCE = ("fiscale", "🧮 Pianificazione Fiscale")
_VISTE = [
    ("fiscale", "🧮 Pianificazione Fiscale"),
    ("analytics", "📊 Analytics"),
]


def _versione() -> str:
    p = os.path.join(get_app_dir(), "version.txt")
    if os.path.exists(p):
        try:
            return open(p, "r", encoding="utf-8").read().strip()
        except OSError:
            return ""
    return "dev"


class PianificatoreFiscaleApp:
    def __init__(self) -> None:
        self.root = ctk.CTk()
        self.root.title("PianificatoreFiscale - Pianificazione Fiscale")
        self.root.geometry("1200x780")
        self.root.minsize(1000, 640)
        apply_theme(self.root)
        self._viste: dict[str, ctk.CTkFrame] = {}
        self._nav_buttons: dict[str, ctk.CTkButton] = {}
        self._current = None
        self._build()
        self._show("fiscale")

    def _build(self) -> None:
        self._sidebar = ctk.CTkFrame(self.root, width=230, corner_radius=0,
                                     fg_color=C["sidebar"])
        self._sidebar.pack(side="left", fill="y")
        self._sidebar.pack_propagate(False)

        self._main = ctk.CTkFrame(self.root, fg_color="transparent")
        self._main.pack(side="left", fill="both", expand=True)

        self._content = ctk.CTkFrame(self._main, fg_color="transparent")
        self._content.pack(fill="both", expand=True, padx=20, pady=(18, 8))

        self.status_bar = StatusBar(self._main)
        self.status_bar.pack(fill="x", padx=20, pady=(0, 12))

        self._build_sidebar()

    def _build_sidebar(self) -> None:
        header = ctk.CTkFrame(self._sidebar, fg_color="transparent")
        header.pack(fill="x", pady=(20, 18))
        row = ctk.CTkFrame(header, fg_color="transparent")
        row.pack(fill="x", padx=14)
        logo = ctk.CTkFrame(row, width=42, height=42, corner_radius=12,
                            fg_color=C["chip_bg"])
        logo.pack(side="left")
        logo.pack_propagate(False)
        ctk.CTkLabel(logo, text="🧮", font=ctk.CTkFont(size=20)).pack(expand=True)
        names = ctk.CTkFrame(row, fg_color="transparent")
        names.pack(side="left", padx=(10, 0))
        ctk.CTkLabel(names, text="PianificatoreFiscale", anchor="w",
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=C["sidebar_fg"]).pack(fill="x")
        ctk.CTkLabel(names, text="Fiscale personale 2024-2027", anchor="w",
                     font=ctk.CTkFont(size=11), text_color=C["muted"]).pack(fill="x")

        nav = ctk.CTkFrame(self._sidebar, fg_color="transparent")
        nav.pack(fill="x", padx=12, pady=6)
        key, label = _VOCE
        btn = ctk.CTkButton(
            nav, text=label, anchor="w", height=40,
            fg_color=C["sidebar_active"], text_color=("#ffffff", "#ffffff"),
            hover_color=C["primary_h"], corner_radius=10,
            font=ctk.CTkFont(size=13),
            command=lambda: self._show(key),
        )
        btn.pack(fill="x", pady=3)
        self._nav_buttons[key] = btn

        footer = ctk.CTkFrame(self._sidebar, fg_color="transparent")
        footer.pack(side="bottom", fill="x", padx=12, pady=14)
        self.version_label = ctk.CTkLabel(
            footer, text=f"Versione {_versione()}",
            font=ctk.CTkFont(size=11), text_color=C["muted"])
        self.version_label.pack(pady=(0, 8))
        GhostButton(footer, text="🔄 Aggiorna", height=34,
                    command=self._aggiorna).pack(fill="x", pady=2)
        ctk.CTkButton(footer, text="🚪 Esci", height=34,
                      fg_color="transparent",
                      text_color=C["danger"],
                      hover_color=("#fde8e8", "#3a1d24"),
                      command=self.root.destroy).pack(fill="x", pady=2)

    def _get_vista(self, key: str) -> ctk.CTkFrame:
        if key not in self._viste:
            if key == "fiscale":
                import views.fiscale_view as fv
                self._viste[key] = fv.FiscaleView(self._content)
            elif key == "analytics":
                import views.analytics_view as av
                self._viste[key] = av.AnalyticsView(self._content)
        return self._viste[key]

    def _show(self, key: str) -> None:
        if self._current is not None:
            self._viste[self._current].pack_forget()
        vista = self._get_vista(key)
        vista.pack(fill="both", expand=True)
        try:
            vista.refresh()
        except Exception as e:  # noqa: BLE001
            self.status_bar.set_message(f"Errore vista: {e}")
        self._current = key

    def _aggiorna(self) -> None:
        try:
            if getattr(sys, "frozen", False):
                exe = os.path.join(get_app_dir(), "PianificatoreFiscaleUpdater.exe")
                if os.path.exists(exe):
                    subprocess.Popen([exe], cwd=get_app_dir())
                    return
            subprocess.Popen([sys.executable, os.path.join(get_app_dir(), "updater.py")],
                             cwd=get_app_dir(), creationflags=subprocess.CREATE_NEW_CONSOLE)
        except Exception as e:  # noqa: BLE001
            self.status_bar.set_message(f"Impossibile avviare l'updater: {e}")

    def run(self) -> None:
        self.root.mainloop()
