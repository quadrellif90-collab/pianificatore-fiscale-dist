"""Vista Pianificazione Fiscale: motore portato da TaxPlanner Italia (golden truth).

Simula il netto annuo/mensile di un lavoratore dipendente per gli anni
2024-2027 usando le regole fiscali reali (JSON) del motore engine.fiscale.
Include un profilo contribuente salvato localmente per riutilizzare i dati.
"""
from __future__ import annotations

import tkinter as tk
from decimal import Decimal, InvalidOperation
from tkinter import messagebox

import customtkinter as ctk

from engine.fiscale import (
    FakeTaxRuleService,
    IrpefCalculator,
    RegimeFiscale,
    RegimeSpeciale,
    RisultatoSimulazione,
    SimulazioneService,
    TaxRuleService,
)
from engine.fiscale.models import (
    Contribuente,
    CategoriaContributiva,
    Reddito,
    RegimeFiscale as EngineRegimeFiscale,
    RegimeSpeciale as EngineRegimeSpeciale,
    TipoContribuente,
    TipoCreditoImposta,
    TipoDipendenteInps,
    TipoIncentivoContributivo,
    TipoReddito,
)
from models import profilo
from models.theme import C
from views.widgets import CLabel, Card, GhostButton, PrimaryButton, SectionHeader

_ANNI = ["2024", "2025", "2026", "2027"]
_RAL_DEFAULT = ["28000", "30000", "32000", "35000", "40000", "50000", "60000"]
_ALIQUOTA_INPS = Decimal("0.0919")

# Nuovi regimi fiscali disponibili
_REGIMI_CHOICES = [
    ("PersonaFisica", "Persona Fisica · Regime Ordinario"),
    ("PartitaIvaOrdinaria", "Partita IVA · Regime Ordinario"),
    ("PartitaIvaForfettaria", "Partita IVA · Regime Forfettario"),
    ("SocietaDiCapitali", "Società di Capitali (IRES/IRAP)"),
]


def _euro(v) -> str:
    try:
        return f"{float(v):,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "–"


def _pct(v) -> str:
    try:
        return f"{float(v):.2f}%"
    except (TypeError, ValueError):
        return "–"


class FiscaleView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self._rule_service = TaxRuleService()
        self._build()
        self._carica_profilo(avviso=False)

    # --- layout ------------------------------------------------------------
    def _build(self):
        SectionHeader(self, "🧮 Pianificazione Fiscale",
                      "Netto annuo, IRPEF e cuneo fiscale · regole reali 2024-2027 "
                      "(parità golden truth col motore TaxPlanner Italia)")

        form = Card(self)
        form.pack(fill="x", pady=(0, 12))

        # Riga 0: parametri principali
        ctk.CTkLabel(form, text="Anno:", font=ctk.CTkFont(size=12)).grid(
            row=0, column=0, padx=(18, 6), pady=(14, 4), sticky="e")
        self.anno_var = tk.StringVar(value="2026")
        ctk.CTkOptionMenu(form, variable=self.anno_var, width=100,
                          values=_ANNI).grid(row=0, column=1, padx=6, pady=(14, 4))

        ctk.CTkLabel(form, text="RAL annuale (€):", font=ctk.CTkFont(size=12)).grid(
            row=0, column=2, padx=(14, 6), pady=(14, 4), sticky="e")
        self.ral_var = tk.StringVar(value="32000")
        self.ral_entry = ctk.CTkEntry(form, textvariable=self.ral_var, width=130)
        self.ral_entry.grid(row=0, column=3, padx=6, pady=(14, 4))

        ctk.CTkLabel(form, text="Provincia:", font=ctk.CTkFont(size=12)).grid(
            row=0, column=4, padx=(14, 6), pady=(14, 4), sticky="e")
        self.prov_var = tk.StringVar(value="")
        ctk.CTkEntry(form, textvariable=self.prov_var, width=70,
                     placeholder_text="es. MI").grid(row=0, column=5, padx=6, pady=(14, 4))

        ctk.CTkLabel(form, text="Comune:", font=ctk.CTkFont(size=12)).grid(
            row=0, column=6, padx=(14, 6), pady=(14, 4), sticky="e")
        self.comune_var = tk.StringVar(value="")
        ctk.CTkEntry(form, textvariable=self.comune_var, width=150,
                     placeholder_text="es. Milano").grid(row=0, column=7, padx=6, pady=(14, 4))

        # Riga 1: regime fiscale + carichi
        ctk.CTkLabel(form, text="Regime:", font=ctk.CTkFont(size=12)).grid(
            row=1, column=0, padx=(18, 6), pady=(2, 4), sticky="e")
        self.regime_var = tk.StringVar(value="PersonaFisica")
        ctk.CTkOptionMenu(form, variable=self.regime_var, width=180,
                          values=[v[0] for v in _REGIMI_CHOICES]).grid(
                              row=1, column=1, padx=6, pady=(2, 4))

        self.figli_var = tk.BooleanVar(value=False)
        self.coniuge_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(form, text="Figli a carico", variable=self.figli_var,
                        checkbox_width=20, checkbox_height=20).grid(
                            row=1, column=2, padx=6, pady=(2, 4))
        ctk.CTkCheckBox(form, text="Coniuge a carico", variable=self.coniuge_var,
                        checkbox_width=20, checkbox_height=20).grid(
                            row=1, column=3, padx=6, pady=(2, 4))
        PrimaryButton(form, text="Calcola", width=130,
                      command=self._calcola).grid(
                          row=1, column=7, columnspan=2, padx=(16, 18), pady=(2, 10), sticky="e")

        # Riga 2: profilo contribuente
        sep = ctk.CTkFrame(form, height=1, fg_color=C["border"])
        sep.grid(row=2, column=0, columnspan=8, sticky="ew", padx=18, pady=(2, 8))
        ctk.CTkLabel(form, text="Profilo contribuente:", font=ctk.CTkFont(size=12)).grid(
            row=3, column=0, padx=(18, 6), pady=(0, 14), sticky="e")
        self.nome_var = tk.StringVar(value="")
        ctk.CTkEntry(form, textvariable=self.nome_var, width=230,
                     placeholder_text="Nome / etichetta (es. Luca Rossi)").grid(
                         row=3, column=1, columnspan=2, padx=6, pady=(0, 14), sticky="w")
        GhostButton(form, text="💾 Salva profilo", width=140,
                    command=self._salva_profilo).grid(
                            row=3, column=5, columnspan=2, padx=6, pady=(0, 14), sticky="e")
        self.profilo_msg = ctk.CTkLabel(form, text="", font=ctk.CTkFont(size=11),
                                        text_color=C["success"])
        self.profilo_msg.grid(row=3, column=7, padx=(6, 18), pady=(0, 14), sticky="w")

        # Risultato
        self.result_card = Card(self)
        self.result_card.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(self.result_card, text="Risultato", anchor="w",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(fill="x", padx=18, pady=(12, 0))
        self.result_label = ctk.CTkLabel(self.result_card, text="Inserisci RAL e premi Calcola.",
                                          justify="left", anchor="w", font=ctk.CTkFont(size=12))
        self.result_label.pack(fill="both", expand=True, padx=18, pady=(2, 12))

        # Decomposizione cuneo
        ctk.CTkLabel(self, text="Decomposizione del cuneo fiscale", anchor="w",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(fill="x", pady=(0, 4))
        self.cuneo_frame = Card(self)
        self.cuneo_frame.pack(fill="x", pady=(0, 12))
        self.cuneo_inner = ctk.CTkFrame(self.cuneo_frame, fg_color="transparent")
        self.cuneo_inner.pack(fill="x", padx=18, pady=12)

        # Tabella netto per RAL
        ctk.CTkLabel(self, text="Netto annuo al variare della RAL (confronto anni)", anchor="w",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(fill="x", pady=(4, 4))
        table = Card(self)
        table.pack(fill="both", expand=True)
        self.table_frame = ctk.CTkFrame(table, fg_color="transparent")
        self.table_frame.pack(fill="both", padx=12, pady=12)
        self._table_vars: dict = {}
        self._build_tabella()
        self._aggiorna_tabella()

    # --- tabella ------------------------------------------------------------
    def _build_tabella(self):
        for child in self.table_frame.winfo_children():
            child.destroy()
        self._table_vars = {}
        header = [""] + _ANNI
        for col, label in enumerate(header):
            ctk.CTkLabel(self.table_frame, text=label, width=110 if col else 130,
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=C["primary"]).grid(row=0, column=col, padx=2, pady=2)
        for row, ral in enumerate(_RAL_DEFAULT, start=1):
            ctk.CTkLabel(self.table_frame, text=f"{int(ral):,}".replace(",", ".") + " €",
                         width=130, anchor="w", font=ctk.CTkFont(size=12)).grid(
                             row=row, column=0, padx=2, pady=2)
            for col, anno in enumerate(_ANNI, start=1):
                var = tk.StringVar(value="–")
                self._table_vars[(anno, ral)] = var
                CLabel(self.table_frame, textvariable=var, width=110).grid(
                    row=row, column=col, padx=2, pady=2)

    def _aggiorna_tabella(self):
        """Aggiorna la tabella netto al variare della RAL per tutti gli anni."""
        regime_name = self.regime_var.get()
        regime_tipo = self._tipo_from_regime(regime_name)

        for anno in _ANNI:
            for ral in _RAL_DEFAULT:
                c = Contribuente(
                    tipo=regime_tipo,
                    anno_riferimento=int(anno),
                    provincia_residenza=self.prov_var.get().strip().upper() or "MI",
                    comune_residenza=self.comune_var.get().strip() or "Milano",
                    figli_carico=1 if self.figli_var.get() else 0,
                    coniuge_carico=self.coniuge_var.get(),
                    # Valori di default per gli altri campi (non dal form corrente)
                    figli_minori_tre_anni=0,
                    figli_disabili=0,
                    genitore_single=False,
                    usa_cedolare_secca=False,
                    cedolare_concordato=False,
                    numero_immobili_locazione_breve=0,
                    numero_mensilita_extra=0,
                    incremento_retributivo_rinnovo=Decimal("0"),
                    premio_produttivita=Decimal("0"),
                    importo_maggiorazioni_lavoro=Decimal("0"),
                    aderisce_bonus_mamme=False,
                    partita_iva="",
                    codice_ateco="",
                    regime_speciale=EngineRegimeSpeciale.Nessuno,
                    incentivo_contributivo=TipoIncentivoContributivo.Nessuno,
                    anni_residenza_estera=0,
                    anni_attivita_impresa=0,
                    is_startup_innovativa=False,
                    is_pmi_innovativa=False,
                    regione_azienda="",
                    categoria_contributiva=CategoriaContributiva.GestioneSeparata,
                    richiede_riduzione_forfettari=False,
                    is_pensionato_over65=False,
                    perdite_pregresse_imprenditore=Decimal("0"),
                    giorni_buoni_pasto_elettronici=0,
                    giorni_buoni_pasto_cartacei=0,
                    ha_redditi_cripto=False,
                    plusvalenze_cripto=Decimal("0"),
                    minusvalenze_cripto=Decimal("0"),
                    monitoraggio_cripto=False,
                    is_part_time=False,
                    ore_settimanali_part_time=0,
                    ore_settimanali_full_time=40,
                    tipo_dipendente_inps=TipoDipendenteInps.Privato,
                    rimborso_smart_working_mensile=Decimal("0"),
                    ha_auto_aziendale=False,
                    valore_auto_aziendale=Decimal("0"),
                    auto_aziendale_elettrica=False,
                    usa_regime_impatriati=False,
                    spesa_affitto_annua=Decimal("0"),
                    spesa_psicologo_annua=Decimal("0"),
                    spese_mediche_annue=Decimal("0"),
                    spese_istruzione_annue=Decimal("0"),
                    spese_sportive_annue=Decimal("0"),
                    erogazioni_liberali_annue=Decimal("0"),
                    abbonamenti_tpl_annui=Decimal("0"),
                    spese_ristrutturazione_annue=Decimal("0"),
                    spese_efficientamento_annue=Decimal("0"),
                    spese_mobili_annue=Decimal("0"),
                    welfare_annuo=Decimal("0"),
                    reddito_complessivo_ultimo_anno=Decimal("0"),
                    previdenza_complementare_annua=Decimal("0"),
                    contributi_previdenziali_versati=Decimal("0"),
                    ricavi_compensi_annui=Decimal("0"),
                    spese_deducibili_annue=Decimal("0"),
                )
                redditi = [
                    Reddito(tipo=TipoReddito.LavoroDipendente, importo_lordo=Decimal(ral),
                            contributi_previdenziali=(Decimal(ral) * _ALIQUOTA_INPS))
                ]
                try:
                    sim = SimulazioneService(self._rule_service, irpef_calc=IrpefCalculator())
                    out = sim.esegui(c, redditi)
                    self._table_vars[(anno, ral)].set(_euro(out.reddito_netto_stimato))
                except Exception:
                    self._table_vars[(anno, ral)].set("–")

    # --- profilo ------------------------------------------------------------
    def _valori_profilo(self) -> dict:
        return {
            "nome": self.nome_var.get().strip(),
            "anno": self.anno_var.get(),
            "ral": self.ral_var.get().strip(),
            "provincia": self.prov_var.get().strip(),
            "comune": self.comune_var.get().strip(),
            "figli": bool(self.figli_var.get()),
            "coniuge": bool(self.coniuge_var.get()),
            "figli_minori": self.figli_minori_var.get() if hasattr(self, 'figli_minori_var') else 0,
            "figli_disabili": self.figli_disabili_var.get() if hasattr(self, 'figli_disabili_var') else 0,
            "anno_estero": self.anni_estera_var.get() if hasattr(self, 'anni_estera_var') else 0,
            "regime": self.regime_var.get(),
            "is_cedolare": False,
            "is_cedolare_concordato": False,
            "immobili_locazione_breve": 0,
            "mensilita_extra": 0,
            "spese_mediche": Decimal("0"),
            "spese_istruzione": Decimal("0"),
            "spese_ristrutturazione": Decimal("0"),
            "spese_efficientamento": Decimal("0"),
            "spese_mobili": Decimal("0"),
            "welfare": Decimal("0"),
            "previdenza_complementare": Decimal("0"),
            "perdite_pregresse_forfettario": Decimal("0"),
            "ricavi_compensi": Decimal("0"),
            "spese_deducibili": Decimal("0"),
        }

    def _salva_profilo(self):
        try:
            dati = self._valori_profilo()
            profilo.salva_profilo(dati)
        except OSError as e:
            messagebox.showerror("Pianificazione Fiscale", f"Errore nel salvataggio:\n{e}")
            return
        self.profilo_msg.configure(text="✅ Profilo salvato.")
        self.after(2500, lambda: self.profilo_msg.configure(text=""))

    def _carica_profilo(self, avviso: bool = True):
        p = profilo.carica_profilo()
        if not p.get("nome") and not p.get("ral"):
            if avviso:
                messagebox.showinfo("Pianificazione Fiscale", "Nessun profilo salvato.")
            return
        self.nome_var.set(p.get("nome", ""))
        self.anno_var.set(p.get("anno", "2026"))
        self.ral_var.set(str(p.get("ral", "32000")))
        self.prov_var.set(p.get("provincia", ""))
        self.comune_var.set(p.get("comune", ""))
        self.figli_var.set(bool(p.get("figli")))
        self.coniuge_var.set(bool(p.get("coniuge")))
        # TODO: caricare gli altri campi (cedolare, immobili, etc.)
        if avviso:
            messagebox.showinfo("Pianificazione Fiscale", "Profilo caricato.")

    # --- calcolo ------------------------------------------------------------
    def _calcola(self):
        try:
            ral = Decimal(self.ral_var.get().replace(".", "").replace(",", "."))
            if ral <= 0:
                raise InvalidOperation
        except (InvalidOperation, TypeError, ValueError):
            messagebox.showwarning("Pianificazione Fiscale", "RAL non valida.")
            return
        anno = int(self.anno_var.get())

        # Costruisci il Contribuente con tutti i dati del form
        c = Contribuente(
            tipo=self._tipo_from_regime(self.regime_var.get()),
            anno_riferimento=anno,
            provincia_residenza=self.prov_var.get().strip().upper(),
            comune_residenza=self.comune_var.get().strip(),
            figli_carico=1 if self.figli_var.get() else 0,
            coniuge_carico=self.coniuge_var.get(),
            figli_minori_tre_anni=self.figli_minori_var.get() if hasattr(self, 'figli_minori_var') else 0,
            figli_disabili=self.figli_disabili_var.get() if hasattr(self, 'figli_disabili_var') else 0,
            genitore_single=False,  # TODO: aggiungere campo UI
            usa_cedolare_secca=self._is_cedolare(),
            cedolare_concordato=self._is_cedolare_concordato(),
            numero_immobili_locazione_breve=self._get_num_immobili_locazione_breve(),
            numero_mensilita_extra=self._get_mensilita_extra(),
            regime=self._regime_fiscale_from_regime_var(),
            categoria_contributiva=self._get_categoria_contributiva(),
            ricavi_compensi_annui=self._get_ricavi_compensi(),
            spese_deducibili_annue=self._get_spese_deducibili(),
            # Campo opzionali non dal form corrente
            perdite_pregresse_forfettario=Decimal("0"),
            welfare_annuo=Decimal("0"),
            previdenza_complementare_annua=Decimal("0"),
            spese_mediche_annue=Decimal("0"),
            spese_istruzione_annue=Decimal("0"),
            spese_ristrutturazione_annue=Decimal("0"),
            spese_efficientamento_annue=Decimal("0"),
            spese_mobili_annue=Decimal("0"),
        )
        redditi = [
            Reddito(tipo=TipoReddito.LavoroDipendente, importo_lordo=ral,
                    contributi_previdenziali=(ral * _ALIQUOTA_INPS))
        ]
        try:
            sim = SimulazioneService(self._rule_service, irpef_calc=IrpefCalculator())
            out = sim.esegui(c, redditi)
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("Pianificazione Fiscale", f"Errore nel calcolo:\n{e}")
            return

        # Risultati principali
        mensile = out.netto_mensile_base
        tassazione = (out.totale_tasse / ral * 100) if ral > 0 else Decimal(0)
        righe = [
            ("Reddito complessivo", _euro(ral)),
            ("Contributi previdenziali", _euro(out.totale_contributi_previdenziali)),
            ("IRPEF + addizionali (TotaleTasse)", _euro(out.totale_tasse)),
            ("Trattamento integrativo", _euro(out.trattamento_integrativo)),
            ("Bonus cuneo (esente)", _euro(out.bonus_cuneo)),
            ("Ulteriore detrazione cuneo", _euro(out.ulteriore_detrazione_cuneo)),
            ("Netto annuo stimato", _euro(out.reddito_netto_stimato)),
            ("Netto mensile (13 mensilità)", _euro(mensile)),
            ("Tassazione effettiva", _pct(tassazione)),
        ]
        if out.irpef is not None:
            righe.insert(3, (
                "  ·  detrazioni lavoro",
                _euro(out.irpef.detrazioni_lavoro)))
        self.result_label.configure(
            text="\n".join(f"{'• ' if r[0].startswith(' ') else ''}{r[0].strip()}: {r[1]}" for r in righe))

        for v in out.decomposizione_cuneo:
            v.percentuale = float(v.valore / max(out.reddito_netto_stimato, Decimal(1)) * 100)
        self._disegna_cuneo(out)

        # Aggiorna tabella RAL×anni
        self._aggiorna_tabella()

    def _tipo_from_regime(self, regime_name: str) -> TipoContribuente:
        mapping = {
            "PersonaFisica": TipoContribuente.PersonaFisica,
            "PartitaIvaOrdinaria": TipoContribuente.PartitaIvaOrdinaria,
            "PartitaIvaForfettaria": TipoContribuente.PartitaIvaForfettaria,
            "SocietaDiCapitali": TipoContribuente.SocietaDiCapitali,
        }
        return mapping.get(regime_name, TipoContribuente.PersonaFisica)

    def _is_cedolare(self) -> bool:
        return False  # TODO: aggiungere checkbox UI

    def _is_cedolare_concordato(self) -> bool:
        return False  # TODO: aggiungere checkbox UI

    def _get_num_immobili_locazione_breve(self) -> int:
        return 0  # TODO: aggiungere campo UI

    def _get_mensilita_extra(self) -> int:
        return 0  # TODO: aggiungere campo UI

    def _regime_fiscale_from_regime_var(self) -> RegimeFiscale:
        mapping = {
            "PersonaFisica": EngineRegimeFiscale.Ordinario,
            "PartitaIvaOrdinaria": EngineRegimeFiscale.Ordinario,
            "PartitaIvaForfettaria": EngineRegimeFiscale.Forfettario,
            "SocietaDiCapitali": EngineRegimeFiscale.Ordinario,
        }
        return mapping.get(self.regime_var.get(), EngineRegimeFiscale.Ordinario)

    def _get_categoria_contributiva(self) -> CategoriaContributiva:
        return CategoriaContributiva.GestioneSeparata

    def _get_ricavi_compensi(self) -> Decimal:
        return Decimal("0")

    def _get_spese_deducibili(self) -> Decimal:
        return Decimal("0")

    # --- cuneo ------------------------------------------------------------
    def _disegna_cuneo(self, out):
        for child in self.cuneo_inner.winfo_children():
            child.destroy()
        voci = out.decomposizione_cuneo
        if not voci:
            ctk.CTkLabel(self.cuneo_inner, text="Nessun dato.",
                         font=ctk.CTkFont(size=11)).pack(anchor="w")
            return
        massimo = max((abs(v.valore) for v in voci), default=Decimal(1)) or Decimal(1)
        for i, v in enumerate(voci):
            bar = ctk.CTkFrame(self.cuneo_inner, height=22, fg_color="transparent")
            bar.pack(fill="x", pady=2)
            label = ctk.CTkLabel(bar, text=f"{v.etichetta}", width=270, anchor="w",
                                 font=ctk.CTkFont(size=11))
            label.pack(side="left", padx=(0, 8))
            larghezza = abs(v.valore) / massimo
            riempimento = ctk.CTkFrame(bar, width=max(4, int(560 * float(larghezza))),
                                       height=16, corner_radius=4,
                                       fg_color=C["primary"] if v.is_costo else C["success"])
            riempimento.pack(side="left", padx=(0, 8))
            valore = ctk.CTkLabel(bar, text=_euro(v.valore), width=120, anchor="w",
                                  font=ctk.CTkFont(size=11, weight="bold"))
            valore.pack(side="left")

    def refresh(self):
        self._aggiorna_tabella()