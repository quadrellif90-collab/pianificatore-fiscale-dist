"""E2E live autonomo - percorso completo dell'app PianificatoreFiscale.

Esegue in un sandbox dati temporaneo (nessun profilo preesistente).
PATCHA tkinter.messagebox per non bloccare su dialoghi modali.
Alla fine stampa PASS/FAIL per ogni step.

Uso:
    python tests/e2e_live.py
Exit code 0 = tutti PASS.
"""
from __future__ import annotations

import os
import sys
import shutil
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# --- Sandbox dati: patch PRIMA di importare i moduli app ---
import appinfo

SANDBOX = tempfile.mkdtemp(prefix="pf_e2e_")
appinfo.get_data_dir = lambda: SANDBOX

import models.config as config
config.get_data_dir = appinfo.get_data_dir

import models.profilo as profilo
profilo.get_data_dir = appinfo.get_data_dir

# --- Patch messagebox (nessun dialogo bloccante) ---
import tkinter.messagebox as _mb

_CALLS: list[tuple] = []


def _fake_box(kind):
    def _w(*args, **kwargs):
        _CALLS.append((kind, args))
    return _w


for _k in ("showinfo", "showwarning", "showerror"):
    setattr(_mb, _k, _fake_box(_k))

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, cond: bool, extra: str = ""):
    RESULTS.append((name, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" | {extra}" if extra else ""))


def main() -> int:
    # ------------------------------------- Avvio (nessuna licenza richiesta)
    import views.main_window as mw

    captured: dict = {}
    orig_app = mw.PianificatoreFiscaleApp

    class AppSpy(orig_app):
        def run(self):
            captured["app"] = self
            self.root.after(1200, self.root.destroy)
            self.root.mainloop()

    mw.PianificatoreFiscaleApp = AppSpy
    marker = len(_CALLS)
    import main as entry
    entry.main()
    mw.PianificatoreFiscaleApp = orig_app
    app = captured.get("app")
    check("1. app avviata senza licenza/attivazione", app is not None)
    errs = [c for c in _CALLS[marker:] if c[0] == "showerror"]
    check("2. avvio senza errori", not errs, str(errs[:1]))

    # ------------------------------------------------------- Vista fiscale
    app = mw.PianificatoreFiscaleApp()
    app.root.update()
    fv = app._viste["fiscale"]
    cells = [v.get() for v in fv._table_vars.values()]
    ok_cells = sum(1 for c in cells if c != "–")
    check("3. tabella netto popolata (28 celle)",
          len(cells) == 28 and ok_cells == 28, f"{ok_cells}/28")
    check("4. nessun profilo al primo avvio (RAL default)",
          fv.ral_var.get() == "32000", fv.ral_var.get())

    fv.ral_var.set("32000")
    fv.anno_var.set("2026")
    fv.figli_var.set(True)
    before = len(_CALLS)
    fv._calcola()
    app.root.update()
    res = fv.result_label.cget("text")
    check("5. calcolo fiscale ok (regole reali)",
          "Netto annuo stimato" in res and "IRPEF" in res,
          res[:120].replace("\n", " | "))
    check("6. calcolo senza errori",
          all(c[0] != "showerror" for c in _CALLS[before:]))
    n_voci = len(fv.cuneo_inner.winfo_children())
    check("7. decomposizione cuneo disegnata", n_voci >= 5, f"{n_voci} voci")

    # ---------------------------------------------------- Profilo contribuente
    fv.nome_var.set("Luca Rossi")
    fv.anno_var.set("2027")
    fv.ral_var.set("45000")
    fv.prov_var.set("MI")
    fv.comune_var.set("Milano")
    fv.figli_var.set(True)
    fv.coniuge_var.set(True)
    fv._salva_profilo()
    app.root.update()
    saved = profilo.carica_profilo()
    check("8. profilo salvato su file locale",
          saved["nome"] == "Luca Rossi" and saved["anno"] == "2027" and
          saved["figli"] is True, str(saved))

    fv.nome_var.set("")
    fv.ral_var.set("")
    fv.figli_var.set(False)
    fv._carica_profilo(avviso=False)
    app.root.update()
    check("9. profilo ricaricato (autofill)",
          fv.nome_var.get() == "Luca Rossi" and fv.ral_var.get() == "45000" and
          fv.figli_var.get() is True,
          f"{fv.nome_var.get()} · {fv.ral_var.get()} · figli={fv.figli_var.get()}")
    check("10. anno profilo applicato", fv.anno_var.get() == "2027", fv.anno_var.get())

    # --------------------------------------------------- Versione / updater
    check("11. etichetta versione v1.0.0", "v1.0.0" in app.version_label.cget("text"),
          app.version_label.cget("text"))
    import updater
    check("12. updater punta al repo dedicato",
          updater.ASSET_NAME == "PianificatoreFiscale.exe" and
          "pianificatore-fiscale-dist" in updater.DIST_REPO,
          updater.DIST_REPO)
    tag, url = updater.get_latest()
    check("13. updater raggiunge GitHub (release pubblicata)",
          tag is not None, str(tag))
    cur = updater._current_version()
    check("14. app già alla versione pubblicata",
          tag is not None and tag == cur, f"{cur} vs {tag}")

    app.root.destroy()

    failed = [r for r in RESULTS if not r[1]]
    print("\n=== E2E LIVE (PianificatoreFiscale): %d/%d PASS ===" % (
        len(RESULTS) - len(failed), len(RESULTS)))
    if failed:
        print("FAILED:")
        for name, cond in failed:
            print(f"  - {name}")
        return 1
    return 0


if __name__ == "__main__":
    try:
        rc = main()
    finally:
        shutil.rmtree(SANDBOX, ignore_errors=True)
    sys.exit(rc)
