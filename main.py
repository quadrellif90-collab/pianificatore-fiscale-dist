"""PianificatoreFiscale - avvio applicazione (gratuita, nessuna licenza)."""
from __future__ import annotations

import sys


def main() -> None:
    from views.main_window import PianificatoreFiscaleApp
    app = PianificatoreFiscaleApp()
    app.run()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        try:
            import tkinter.messagebox as _mb
            _mb.showerror("PianificatoreFiscale",
                          f"Errore all'avvio:\n{e}\n\n"
                          "Se il problema persiste ripristina i dati (cartella ~\\PianificatoreFiscale).")
        except Exception:
            sys.stderr.write(f"Errore all'avvio: {e}\n")
        sys.exit(1)
