"""Tema grafico condiviso (CustomTkinter) per HrPayrollGest e PianificatoreFiscale.

Design system moderno "SaaS": palette indigo/slate, sidebar pannellata,
card arrotondate, font Segoe UI. Due modalità: 'beach' (light) e 'dark'.
"""
import os

# --- Palette (chiavi condivise light/dark) ---
_BEACH = {
    "bg":        "#f2f4f8",   # sfondo area contenuto
    "surface":   "#ffffff",   # card / sidebar / superfici
    "surface2":  "#eef1f8",   # bande header / campi secondari
    "fg":        "#111827",   # testo principale
    "muted":     "#6b7280",   # testo secondario
    "primary":   "#4f46e5",   # indigo (accento principale)
    "primary_h": "#4338ca",   # indigo hover
    "accent":    "#0e7490",   # teal (accento secondario)
    "success":   "#059669",   # verde
    "success_h": "#047857",
    "danger":    "#dc2626",   # rosso
    "danger_h":  "#b91c1c",
    "tree_bg":   "#ffffff",
    "tree_fg":   "#111827",
    "tree_sel":  "#e0e7ff",
    "head_bg":   "#eef1f8",
    "head_fg":   "#374151",
    "entry_bg":  "#ffffff",
    "border":    "#e4e8f0",
    "sidebar":   "#ffffff",
    "sidebar_fg": "#1f2937",
    "sidebar_active": "#4f46e5",
    "sidebar_hover": "#eef1f8",
    "chip_bg":   "#eef2ff",
    "link":      "#2563eb",
}

_DARK = {
    "bg":        "#0b1220",
    "surface":   "#141d30",
    "surface2":  "#1b2639",
    "fg":        "#e6edf7",
    "muted":     "#93a4bd",
    "primary":   "#6366f1",
    "primary_h": "#4f46e5",
    "accent":    "#22d3ee",
    "success":   "#34d399",
    "success_h": "#2dd4bf",
    "danger":    "#f87171",
    "danger_h":  "#ef4444",
    "tree_bg":   "#141d30",
    "tree_fg":   "#e6edf7",
    "tree_sel":  "#31406b",
    "head_bg":   "#1b2639",
    "head_fg":   "#cbd5e1",
    "entry_bg":  "#0e1626",
    "border":    "#273248",
    "sidebar":   "#111827",
    "sidebar_fg": "#e6edf7",
    "sidebar_active": "#6366f1",
    "sidebar_hover": "#1b2639",
    "chip_bg":   "#26314f",
    "link":      "#60a5fa",
}

THEMES = {"beach": _BEACH, "dark": _DARK}

# Colori diretti per i widget CTk: nome -> (colore_light, colore_dark)
C = {k: (_BEACH[k], _DARK[k]) for k in _BEACH}


def get_theme_name() -> str:
    from models.config import carica_config
    return carica_config().get("tema", "beach")


def ttk_color(key: str) -> str:
    """Colore singolo (niente tuple) per widget ttk (Treeview/tag)."""
    return C[key][1] if get_theme_name() == "dark" else C[key][0]


def set_theme_name(name: str):
    from models.config import carica_config, salva_config
    cfg = carica_config()
    cfg["tema"] = name
    salva_config(cfg)


def _ctk_mode(name: str) -> str:
    return "dark" if name == "dark" else "light"


def apply_theme(root, name: str = None) -> str:
    """Applica il tema a root e ai figli (CTk + ttk.Style)."""
    try:
        import customtkinter as ctk
    except ImportError:
        ctk = None

    name = name or get_theme_name()
    t = THEMES.get(name, _BEACH)
    mode = _ctk_mode(name)

    if ctk is not None:
        ctk.set_appearance_mode(mode)
        try:
            tema = ctk.ThemeManager.theme
            for widget, props in _build_ctk_theme(t).items():
                if widget in tema:
                    tema[widget].update(props)
                else:
                    tema[widget] = props
        except Exception:
            pass

    try:
        style = __import__("tkinter.ttk").Style(root)
        style.theme_use("clam")
        style.configure("TFrame", background=t["bg"])
        style.configure("TLabel", background=t["bg"], foreground=t["fg"])
        style.configure("TButton", background=t["surface"], foreground=t["fg"])
        style.configure("TNotebook", background=t["bg"])
        style.configure("TNotebook.Tab", background=t["surface2"],
                       foreground=t["muted"])
        style.configure("Treeview", background=t["tree_bg"],
                       foreground=t["tree_fg"], fieldbackground=t["tree_bg"],
                       selectbackground=t["tree_sel"], bordercolor=t["border"],
                       lightcolor=t["bg"], darkcolor=t["bg"], rowheight=30,
                       font=("Segoe UI", 11))
        style.configure("Treeview.Heading", background=t["head_bg"],
                       foreground=t["head_fg"], relief="flat",
                       font=("Segoe UI", 11, "bold"))
        style.configure("TCombobox", fieldbackground=t["entry_bg"],
                       foreground=t["fg"], background=t["surface"])
        style.configure("TEntry", fieldbackground=t["entry_bg"],
                       foreground=t["fg"])
        style.map("Treeview", background=[("selected", t["tree_sel"])],
                  foreground=[("selected", t["fg"])])
        style.map("TNotebook.Tab",
                  background=[("selected", t["primary"]),
                              ("active", t["surface2"])],
                  foreground=[("selected", "#ffffff")])
        style.map("Treeview.Heading", background=[("active", t["head_bg"])])
        root.configure(background=t["bg"])
        _apply_to_children(root, t)
    except Exception:
        pass
    try:
        normalize_widgets(root)
    except Exception:
        pass
    return name


def _apply_to_children(widget, t):
    try:
        cls = widget.winfo_class()
        if cls in ("Frame", "Labelframe", "Canvas", "TFrame"):
            try:
                widget.configure(background=t["bg"])
            except Exception:
                pass
    except Exception:
        pass
    try:
        for child in widget.winfo_children():
            _apply_to_children(child, t)
    except Exception:
        pass


def apply_theme_to_window(win, name: str = None):
    return apply_theme(win, name)


# --- Normalizzazione dimensioni (font/altezza uniformi) ---
try:
    import customtkinter as _ctk_mod
except ImportError:
    _ctk_mod = None

_WIDGET_HEIGHTS = {
    "CTkButton": 38,
    "CTkEntry": 36,
    "CTkComboBox": 36,
    "CTkOptionMenu": 36,
    "CTkTextbox": None,
    "CTkScrollbar": None,
    "CTkSlider": 16,
    "CTkProgressBar": 14,
}

_SKIP_CLASSES = {"CTkTabview", "CTkFrame", "CTkLabel", "CTkCheckBox",
                  "CTkRadioButton", "CTkSwitch", "CTkCanvas", "CTkToplevel",
                  "CTk", "CTkSegmentedButton"}


def normalize_widgets(root):
    """Applica font/altezze standard a tutti i widget CTk discendenti."""
    if _ctk_mod is None:
        return
    try:
        default_font = _ctk_mod.CTkFont(family="Segoe UI", size=13)
    except Exception:
        default_font = None
    _normalize(root, default_font, set())


def _normalize(widget, default_font, seen):
    try:
        if id(widget) in seen:
            return
        seen.add(id(widget))
    except Exception:
        return

    cls = widget.winfo_class()
    try:
        if cls not in _SKIP_CLASSES:
            if default_font is not None:
                try:
                    cur = widget.cget("font")
                    if cur in (None, "TkDefaultFont", "TkTextFont",
                               "TkMenuFont", "", "None"):
                        widget.configure(font=default_font)
                except Exception:
                    pass
            h = _WIDGET_HEIGHTS.get(cls)
            if h is not None:
                try:
                    cur_h = widget.cget("height")
                    if not cur_h or cur_h <= 0:
                        widget.configure(height=h)
                except Exception:
                    pass
    except Exception:
        pass

    try:
        for child in widget.winfo_children():
            _normalize(child, default_font, seen)
    except Exception:
        pass


def _build_ctk_theme(t: dict) -> dict:
    return {
        "CTk": {
            "FG_COLOR": (t["bg"], t["bg"]),
            "TEXT_COLOR": (t["fg"], t["fg"]),
            "BACKGROUND": (t["bg"], t["bg"]),
        },
        "CTkButton": {
            "FG_COLOR": (t["primary"], t["primary"]),
            "HOVER_COLOR": (t["primary_h"], t["primary_h"]),
            "TEXT_COLOR": ("#ffffff", "#ffffff"),
            "BORDER_COLOR": (t["border"], t["border"]),
            "BORDER_WIDTH": (0, 0),
            "CORNER_RADIUS": (10, 10),
            "HEIGHT": (38, 38),
            "FONT": ("Segoe UI", 13),
        },
        "CTkEntry": {
            "FG_COLOR": (t["entry_bg"], t["entry_bg"]),
            "TEXT_COLOR": (t["fg"], t["fg"]),
            "PLACEHOLDER_TEXT_COLOR": (t["muted"], t["muted"]),
            "BORDER_COLOR": (t["border"], t["border"]),
            "BORDER_WIDTH": (1, 1),
            "CORNER_RADIUS": (10, 10),
            "FONT": ("Segoe UI", 13),
        },
        "CTkLabel": {
            "TEXT_COLOR": (t["fg"], t["fg"]),
            "FONT": ("Segoe UI", 13),
        },
        "CTkFrame": {
            "FG_COLOR": (t["surface"], t["surface"]),
            "BORDER_COLOR": (t["border"], t["border"]),
            "BORDER_WIDTH": (0, 0),
            "CORNER_RADIUS": (14, 14),
        },
        "CTkComboBox": {
            "FG_COLOR": (t["entry_bg"], t["entry_bg"]),
            "TEXT_COLOR": (t["fg"], t["fg"]),
            "BUTTON_COLOR": (t["primary"], t["primary"]),
            "BUTTON_HOVER_COLOR": (t["primary_h"], t["primary_h"]),
            "BORDER_COLOR": (t["border"], t["border"]),
            "CORNER_RADIUS": (10, 10),
            "FONT": ("Segoe UI", 13),
        },
        "CTkOptionMenu": {
            "FG_COLOR": (t["entry_bg"], t["entry_bg"]),
            "TEXT_COLOR": (t["fg"], t["fg"]),
            "BUTTON_COLOR": (t["primary"], t["primary"]),
            "BUTTON_HOVER_COLOR": (t["primary_h"], t["primary_h"]),
            "BORDER_COLOR": (t["border"], t["border"]),
            "CORNER_RADIUS": (10, 10),
            "FONT": ("Segoe UI", 13),
        },
        "CTkCheckBox": {
            "FG_COLOR": (t["primary"], t["primary"]),
            "HOVER_COLOR": (t["primary_h"], t["primary_h"]),
            "BORDER_COLOR": (t["border"], t["border"]),
            "TEXT_COLOR": (t["fg"], t["fg"]),
            "CORNER_RADIUS": (6, 6),
            "FONT": ("Segoe UI", 13),
        },
        "CTkRadioButton": {
            "FG_COLOR": (t["primary"], t["primary"]),
            "HOVER_COLOR": (t["primary_h"], t["primary_h"]),
            "BORDER_COLOR": (t["border"], t["border"]),
            "TEXT_COLOR": (t["fg"], t["fg"]),
            "FONT": ("Segoe UI", 13),
        },
        "CTkTabview": {
            "FG_COLOR": (t["bg"], t["bg"]),
            "SEGMENTED_BUTTON_FG_COLOR": (t["surface2"], t["surface2"]),
            "SEGMENTED_BUTTON_SELECTED_COLOR": (t["primary"], t["primary"]),
            "SEGMENTED_BUTTON_SELECTED_HOVER_COLOR": (t["primary_h"], t["primary_h"]),
            "SEGMENTED_BUTTON_UNSELECTED_COLOR": (t["surface2"], t["surface2"]),
            "SEGMENTED_BUTTON_UNSELECTED_HOVER_COLOR": (t["border"], t["border"]),
            "TEXT_COLOR": (t["fg"], t["fg"]),
            "CORNER_RADIUS": (12, 12),
            "FONT": ("Segoe UI", 13),
        },
        "CTkScrollbar": {
            "FG_COLOR": (t["border"], t["border"]),
            "HOVER_COLOR": (t["muted"], t["muted"]),
            "CORNER_RADIUS": (8, 8),
            "BORDER_SPACING": (3, 3),
        },
        "CTkProgressBar": {
            "FG_COLOR": (t["primary"], t["primary"]),
            "PROGRESS_COLOR": (t["accent"], t["accent"]),
            "BORDER_COLOR": (t["bg"], t["bg"]),
            "CORNER_RADIUS": (6, 6),
        },
        "CTkTextbox": {
            "FG_COLOR": (t["entry_bg"], t["entry_bg"]),
            "TEXT_COLOR": (t["fg"], t["fg"]),
            "BORDER_COLOR": (t["border"], t["border"]),
            "BORDER_WIDTH": (1, 1),
            "CORNER_RADIUS": (10, 10),
            "FONT": ("Segoe UI", 13),
        },
    }
