"""Widget riutilizzabili condivisi (CustomTkinter, design system comune)."""
import tkinter as tk
import customtkinter as ctk
from typing import Optional, Callable

from models.theme import C


class CLabel(ctk.CTkLabel):
    """CTkLabel che supporta textvariable (CTk non lo supporta nativamente)."""

    def __init__(self, master, textvariable: tk.StringVar = None, **kwargs):
        kwargs.pop("textvariable", None)
        super().__init__(master, **kwargs)
        self._tv = textvariable
        if textvariable is not None:
            self.configure(text=textvariable.get())
            textvariable.trace_add("write", self._on_var)

    def _on_var(self, *args):
        try:
            self.configure(text=self._tv.get())
        except Exception:
            pass


def SectionHeader(master, title: str, subtitle: str = "") -> ctk.CTkFrame:
    """Intestazione di sezione coerente: titolo + sottotitolo."""
    head = ctk.CTkFrame(master, fg_color="transparent")
    ctk.CTkLabel(head, text=title, anchor="w",
                 font=ctk.CTkFont(size=22, weight="bold")).pack(fill="x")
    if subtitle:
        ctk.CTkLabel(head, text=subtitle, anchor="w", justify="left",
                     font=ctk.CTkFont(size=12),
                     text_color=C["muted"]).pack(fill="x", pady=(2, 0))
    head.pack(fill="x", pady=(0, 16))
    return head


def Card(master, **kwargs) -> ctk.CTkFrame:
    """Card standard: bordo sottile + angoli arrotondati."""
    kw = dict(corner_radius=14, border_width=1, fg_color=C["surface"],
              border_color=C["border"])
    kw.update(kwargs)
    return ctk.CTkFrame(master, **kw)


def PrimaryButton(master, text: str, command=None, **kwargs) -> ctk.CTkButton:
    kw = dict(fg_color=C["primary"], hover_color=C["primary_h"],
              text_color=("#ffffff", "#ffffff"))
    kw.update(kwargs)
    return ctk.CTkButton(master, text=text, command=command, **kw)


def GhostButton(master, text: str, command=None, **kwargs) -> ctk.CTkButton:
    """Pulsante secondario su sfondo neutro."""
    kw = dict(fg_color="transparent", hover_color=C["surface2"],
              text_color=C["fg"], border_width=1, border_color=C["border"])
    kw.update(kwargs)
    return ctk.CTkButton(master, text=text, command=command, **kw)


def SuccessButton(master, text: str, command=None, **kwargs) -> ctk.CTkButton:
    kw = dict(fg_color=C["success"], hover_color=C["success_h"],
              text_color=("#ffffff", "#ffffff"))
    kw.update(kwargs)
    return ctk.CTkButton(master, text=text, command=command, **kw)


def DangerButton(master, text: str, command=None, **kwargs) -> ctk.CTkButton:
    kw = dict(fg_color=C["danger"], hover_color=C["danger_h"],
              text_color=("#ffffff", "#ffffff"))
    kw.update(kwargs)
    return ctk.CTkButton(master, text=text, command=command, **kw)


_BADGE_STYLES = {
    "success": (C["success"], ("#ffffff", "#ffffff")),
    "muted":   (("#e5e7eb", "#2b3448"), C["muted"]),
    "danger":  (C["danger"], ("#ffffff", "#ffffff")),
    "info":    (("#dbeafe", "#1e3a8a"), C["link"]),
}


def Badge(master, text: str, kind: str = "muted") -> ctk.CTkLabel:
    """Pill di stato colorato."""
    bg, fg = _BADGE_STYLES.get(kind, _BADGE_STYLES["muted"])
    return ctk.CTkLabel(master, text=text, fg_color=bg, text_color=fg,
                        corner_radius=12, height=24,
                        font=ctk.CTkFont(size=11, weight="bold"))


class SearchBar(ctk.CTkFrame):
    """Barra di ricerca compatta con icona e debounce 300ms."""
    def __init__(self, parent, on_search: Callable[[str], None],
                 placeholder: str = "Cerca...", **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._on_search = on_search
        self.var = ctk.StringVar()
        self._timer_id = None

        search_icon = ctk.CTkLabel(self, text="🔍",
                                   font=ctk.CTkFont(size=13),
                                   text_color=C["muted"])
        search_icon.grid(row=0, column=0, padx=(0, 6))

        self.entry = ctk.CTkEntry(
            self, textvariable=self.var, width=260, height=34,
            placeholder_text=placeholder,
            border_color=C["border"],
            border_width=1,
            font=ctk.CTkFont(size=12))
        self.entry.grid(row=0, column=1, sticky="ew")
        self.columnconfigure(1, weight=1)

        clear = ctk.CTkButton(
            self, text="✕", width=30, height=30,
            font=ctk.CTkFont(size=12),
            fg_color=C["border"],
            hover_color=C["muted"],
            text_color=("#ffffff", "#ffffff"),
            command=self._clear)
        clear.grid(row=0, column=2, padx=(6, 0))

        self.var.trace_add("write", lambda *_: self._schedule())

    def _schedule(self):
        if self._timer_id is not None:
            self.after_cancel(self._timer_id)
        self._timer_id = self.after(300, self._fire)

    def _fire(self):
        self._timer_id = None
        try:
            self._on_search(self.var.get())
        except Exception:
            pass

    def _clear(self):
        self.var.set("")
        if self._timer_id is not None:
            self.after_cancel(self._timer_id)
            self._timer_id = None
        self._fire()
        self.entry.focus_set()

    def get(self) -> str:
        return self.var.get()

    def focus_set(self):
        self.entry.focus_set()


class StatusBar(ctk.CTkLabel):
    """Barra di stato in basso minimal e professionale."""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, text="✅ Pronto", anchor="w",
                         height=28, fg_color=C["surface2"],
                         corner_radius=10, font=ctk.CTkFont(size=11),
                         text_color=C["muted"],
                         border_width=1,
                         border_color=C["border"],
                         **kwargs)
        self._msg = "✅ Pronto"

    def set_message(self, msg: str):
        self._msg = msg or "✅ Pronto"
        self.configure(text=self._msg)


class ToggleBar(ctk.CTkFrame):
    """Barra di comando (toolbar) sotto l'intestazione della vista."""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

    def add_left(self, widget):
        widget.pack(side="left", padx=(0, 8))
        return widget

    def add_right(self, widget):
        widget.pack(side="right", padx=(8, 0))
        return widget
