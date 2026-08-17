"""Vista Pianificazione Fiscale: motore portato da TaxPlanner Italia (golden truth).

Simula il netto annuo/mensile di un lavoratore dipendente per gli anni
2024-2027 usando le regole fiscali reali (JSON) del motore engine.fiscale.
Include un profilo contribuente salvato localmente per riutilizzare i dati.
"""
from __future__ import annotations

import tkinter as tk
from decimal import Decimal, InvalidOperation
from tkinter import messagebox, filedialog
import datetime
import threading

import customtkinter as ctk
import csv
import json

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
        self.regime_sociale_var = tk.StringVar(value="")
        self.categoria_contributiva_var = tk.StringVar(value="Gestione Separata")
        self.anni_residenza_estera_var = tk.StringVar(value="0")
        self.partita_iva_var = tk.StringVar(value="")
        ctk.CTkOptionMenu(form, variable=self.regime_var, width=180,
                          values=[v[0] for v in _REGIMI_CHOICES]).grid(
                              row=1, column=1, padx=6, pady=(2, 4))
        ctk.CTkLabel(form, text="Ragione sociale:", font=ctk.CTkFont(size=12)).grid(
            row=2, column=0, padx=(18, 6), pady=(2, 4), sticky="e")
        ctk.CTkEntry(form, textvariable=self.regime_sociale_var, width=200,
                    placeholder_text="es. Luca Rossi").grid(
                        row=2, column=1, padx=6, pady=(2, 4))
        ctk.CTkLabel(form, text="Partita IVA:", font=ctk.CTkFont(size=12)).grid(
            row=2, column=2, padx=(14, 6), pady=(2, 4), sticky="e")
        ctk.CTkEntry(form, textvariable=self.partita_iva_var, width=130).grid(
            row=2, column=3, padx=6, pady=(2, 4))
        ctk.CTkLabel(form, text="Settore ATECO:", font=ctk.CTkFont(size=12)).grid(
            row=2, column=4, padx=(14, 6), pady=(2, 4), sticky="e")
        ctk.CTkEntry(form, textvariable=self.categoria_contributiva_var, width=130).grid(
            row=2, column=5, padx=6, pady=(2, 4))

        self.figli_var = tk.BooleanVar(value=False)
        self.coniuge_var = tk.BooleanVar(value=False)
        self.cedolare_var = tk.BooleanVar(value=False)
        self.impatriati_var = tk.BooleanVar(value=False)
        self.part_time_var = tk.BooleanVar(value=False)
        self.auto_aziendale_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(form, text="Figli a carico", variable=self.figli_var,
                        checkbox_width=20, checkbox_height=20).grid(
                            row=1, column=2, padx=6, pady=(2, 4))
        ctk.CTkCheckBox(form, text="Coniuge a carico", variable=self.coniuge_var,
                        checkbox_width=20, checkbox_height=20).grid(
                            row=1, column=3, padx=6, pady=(2, 4))
        ctk.CTkCheckBox(form, text="Ced. Secca", variable=self.cedolare_var,
                        checkbox_width=20, checkbox_height=20).grid(
                            row=1, column=4, padx=6, pady=(2, 4))
        ctk.CTkCheckBox(form, text="Impatriati", variable=self.impatriati_var,
                        checkbox_width=20, checkbox_height=20).grid(
                            row=1, column=5, padx=6, pady=(2, 4))
        ctk.CTkCheckBox(form, text="Part-time", variable=self.part_time_var,
                        checkbox_width=20, checkbox_height=20).grid(
                            row=1, column=6, padx=6, pady=(2, 4))
        ctk.CTkCheckBox(form, text="Auto aziendale", variable=self.auto_aziendale_var,
                        checkbox_width=20, checkbox_height=20).grid(
                            row=1, column=7, padx=6, pady=(2, 4))
        ctk.CTkCheckBox(form, text="Part. IVA", variable=self.partita_iva_var,
                        checkbox_width=20, checkbox_height=20).grid(
                            row=1, column=8, padx=6, pady=(2, 4))
        PrimaryButton(form, text="Calcola", width=130,
                      command=self._calcola).grid(
                          row=1, column=7, columnspan=2, padx=(16, 18), pady=(2, 10), sticky="e")
        GhostButton(form, text="🔍 Compara Regimi", width=130,
                   command=self._comparazione_regimi).grid(
                           row=1, column=9, padx=6, pady=(2, 10), sticky="e")
        GhostButton(form, text="🔮 What-If", width=110,
                   command=self._simulazione_what_if).grid(
                           row=1, column=10, padx=6, pady=(2, 10), sticky="e")
        GhostButton(form, text="💬 NL Query", width=110,
                   command=self._nl_query).grid(
                           row=1, column=11, padx=6, pady=(2, 10), sticky="e")

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
        GhostButton(form, text="📊 Esporta CSV", width=120,
                    command=self.export_csv).grid(
                            row=3, column=9, padx=6, pady=(0, 14), sticky="e")
        GhostButton(form, text="📥 Importa CSV", width=120,
                    command=self.import_csv).grid(
                            row=3, column=10, padx=6, pady=(0, 14), sticky="e")
        GhostButton(form, text="🤖 AI Suggerimenti", width=140,
                    command=self._ai_suggerimenti).grid(
                            row=3, column=11, padx=6, pady=(0, 14), sticky="e")

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
            "regime_sociale": self.regime_sociale_var.get() if hasattr(self, 'regime_sociale_var') else "",
            "categoria_contributiva": self.categoria_contributiva_var.get() if hasattr(self, 'categoria_contributiva_var') else "Gestione Separata",
            "partita_iva": self.partita_iva_var.get().strip() if hasattr(self, 'partita_iva_var') else "",
            "anni_residenza_estera": self.anni_residenza_estera_var.get() if hasattr(self, 'anni_residenza_estera_var') else "0",
            "is_cedolare": self.cedolare_var.get() if hasattr(self, 'cedolare_var') else False,
            "is_cedolare_concordato": False,  # TODO: checkbox non più visibile nell'UI principale
            "immobili_locazione_breve": 0,
            "mensilita_extra": 0,
            # Campi part-time e auto aziendale (nuovi campi UI)
            "is_part_time": self.part_time_var.get() if hasattr(self, 'part_time_var') else False,
            "ore_settimanali_part_time": 0,  # TODO: collegare a campo UI ore part-time
            "ore_settimanali_full_time": 40,
            "ha_auto_aziendale": self.auto_aziendale_var.get() if hasattr(self, 'auto_aziendale_var') else False,
            "valore_auto_aziendale": Decimal("0"),  # TODO: collegare a campo UI valore au
            "auto_aziendale_elettrica": False,  # TODO: collegare a checkbox auto elettric
            # Partita IVA management
            "partita_iva": self.partita_iva_var.get().strip() if hasattr(self, 'partita_iva_var') else "",
            # Vecchi campi (mantenuti per compatibilità, valore di default)
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
            # Nuovi campi engine (valori di default, da collegare a campi UI specifici in seguito)
            "usa_regime_impatriati": False,
            "giorni_buoni_pasto_elettronici": 0,
            "giorni_buoni_pasto_cartacei": 0,
            "ha_redditi_cripto": False,
            "plusvalenze_cripto": Decimal("0"),
            "minusvalenze_cripto": Decimal("0"),
            "monitoraggio_cripto": False,
            "aderisce_bonus_mamme": False,
            "patrimonio_netto": Decimal("0"),
            "patrimonio_immobiliare": Decimal("0"),
            "patrimonio_finanziario": Decimal("0"),
            "mutui_pendenti": Decimal("0"),
            "investimenti_azionari": Decimal("0"),
            "investimenti_obbligazionari": Decimal("0"),
            "eredita_ricevuta": Decimal("0"),
            "eredità_pendente": Decimal("0"),
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
            genitore_single=False,
            usa_cedolare_secca=self._is_cedolare(),
            cedolare_concordato=self._is_cedolare_concordato(),
            numero_immobili_locazione_breve=self._get_num_immobili_locazione_breve(),
            numero_mensilita_extra=self._get_mensilita_extra(),
            regime=self._regime_fiscale_from_regime_var(),
            categoria_contributiva=self._get_categoria_contributiva(),
            ricavi_compensi_annui=self._get_ricavi_compensi(),
            spese_deducibili_annue=self._get_spese_deducibili(),
            partita_iva=self._valori_profilo().get("partita_iva", ""),
            ragione_sociale=self._valori_profilo().get("regime_sociale", ""),
            anni_residenza_estera=int(self._valori_profilo().get("anni_residenza_estera", 0)),
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

    def export_csv(self):
        """Esporta i dati del profilo e della tabella in CSV."""
        try:
            filepath = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.csv")],
                title="Esporta dati fiscali"
            )
            if not filepath:
                return
            
            # Raccogli dati dal profilo
            profilo_dati = self._valori_profilo()
            
            # Raccogli dati dalla tabella
            righe_tabella = []
            for anno in _ANNI:
                for ral in _RAL_DEFAULT:
                    key = (anno, ral)
                    if key in self._table_vars:
                        valore = self._table_vars[key].get()
                        righe_tabella.append({
                            "anno": anno,
                            "ral": ral,
                            "netto": valore
                        })
            
            # Scrivi CSV
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Tipo", "Dato"])
                writer.writerow(["Profilo", ""])
                writer.writerow(["Nome", profilo_dati.get("nome", "")])
                writer.writerow(["Anno", profilo_dati.get("anno", "")])
                writer.writerow(["RAL", profilo_dati.get("ral", "")])
                writer.writerow(["Partita IVA", profilo_dati.get("partita_iva", "")])
                writer.writerow(["Regime", profilo_dati.get("regime", "")])
                writer.writerow(["Cedolare", str(profilo_dati.get("is_cedolare", ""))])
                writer.writerow(["Impatriati", str(profilo_dati.get("usa_regime_impatriati", ""))])
                writer.writerow(["Part-time", str(profilo_dati.get("is_part_time", ""))])
                writer.writerow(["Auto aziendale", str(profilo_dati.get("ha_auto_aziendale", ""))])
                writer.writerow(["", ""])
                writer.writerow(["Tabella Netto", ""])
                writer.writerow(["Anno", "RAL", "Netto"])
                for riga in righe_tabella:
                    writer.writerow([riga["anno"], riga["ral"], riga["netto"]])
            
            messagebox.showinfo("Esportazione CSV", f"Dati esportati in:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Errore esportazione", f"Errore durante l'esportazione CSV:\n{e}")

    def import_csv(self):
        """Importa dati da file CSV al profilo corrente."""
        try:
            filepath = filedialog.askopenfilename(
                filetypes=[("CSV files", "*.csv"), ("All files", "*.csv")],
                title="Importa dati fiscali"
            )
            if not filepath:
                return
            
            # Leggi CSV
            dati = {}
            with open(filepath, "r", encoding="utf-8") as f:
                letta = csv.reader(f)
                for row in letta:
                    if len(row) >= 2:
                        dati[row[0].strip()] = row[1].strip()
            
            # Aggiorna campi del form
            if "Nome" in dati:
                self.nome_var.set(dati["Nome"])
            if "Anno" in dati:
                self.anno_var.set(dati["Anno"])
            if "RAL" in dati:
                self.ral_var.set(dati["RAL"])
            if "Partita IVA" in dati:
                self.partita_iva_var.set(dati["Partita IVA"])
            if "Regime" in dati:
                if dati["Regime"] in [v[0] for v in _REGIMI_CHOICES]:
                    self.regime_var.set(dati["Regime"])
            
            # Aggiorna variabili UI
            if "Cedolare" in dati:
                self.cedolare_var.set(dati["Cedolare"] == "True")
            if "Impatriati" in dati:
                self.impatriati_var.set(dati["Impatriati"] == "True")
            if "Part-time" in dati:
                self.part_time_var.set(dati["Part-time"] == "True")
            if "Auto aziendale" in dati:
                self.auto_aziendale_var.set(dati["Auto aziendale"] == "True")
            
            # Ricarica i calcoli
            self._carica_profilo(avviso=False)
            self._aggiorna_tabella()
            self._calcola()
            
            messagebox.showinfo("Importazione CSV", f"Dati importati da:\n{filepath}")
        except Exception as e:
            messagebox.showinfo("Importazione CSV", f"Dati importati da:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Errore importazione", f"Errore durante l'importazione CSV:\n{e}")

    def _comparazione_regimi(self):
        """Apri finestra di comparazione regimi fiscali."""
        try:
            ral = Decimal(self.ral_var.get().replace(".", "").replace(",", "."))
            if ral <= 0:
                raise InvalidOperation
        except (InvalidOperation, TypeError, ValueError):
            messagebox.showwarning("Pianificazione Fiscale", "RAL non valida per la comparazione.")
            return
        
        anno = int(self.anno_var.get())
        provincia = self.prov_var.get().strip().upper()
        comune = self.comune_var.get().strip()
        figli = 1 if self.figli_var.get() else 0
        coniuge = self.coniuge_var.get()
        
        # Calcola per tutti i regimi
        risultati = {}
        for regime_key, regime_label in _REGIMI_CHOICES:
            tipo = self._tipo_from_regime(regime_key)
            c = Contribuente(
                tipo=tipo,
                anno_riferimento=anno,
                provincia_residenza=provincia,
                comune_residenza=comune,
                figli_carico=figli,
                coniuge_carico=coniuge,
                partita_iva=self._valori_profilo().get("partita_iva", ""),
                ragione_sociale=self._valori_profilo().get("regime_sociale", ""),
                anni_residenza_estera=int(self._valori_profilo().get("anni_residenza_estera", 0)),
            )
            redditi = [Reddito(tipo=TipoReddito.LavoroDipendente, importo_lordo=ral,
                            contributi_previdenziali=(ral * _ALIQUOTA_INPS))]
            try:
                sim = SimulazioneService(self._rule_service, irpef_calc=IrpefCalculator())
                out = sim.esegui(c, redditi)
                risultati[regime_label] = out.reddito_netto_stimato
            except Exception:
                risultati[regime_label] = Decimal("0")
        
        # Mostra finestra comparazione
        self._mostra_finestra_comparazione(risultati, ral)

    def _mostra_finestra_comparazione(self, risultati: dict, ral: Decimal):
        """Mostra finestra di comparazione regimi."""
        win = ctk.CTkToplevel(self)
        win.title("Comparazione Regimi Fiscali")
        win.geometry("500x400")
        win.transient(self.winfo_toplevel())
        win.grab_set()
        
        ctk.CTkLabel(win, text=f"Comparazione Regimi per RAL {_euro(ral)}",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=16)
        
        # Tabella comparazione
        frame = ctk.CTkFrame(win)
        frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        headers = ["Regime", "Netto Annuo", "Risparmio vs Ordinario", "% Risparmio"]
        for col, header in enumerate(headers):
            ctk.CTkLabel(win, text=header, font=ctk.CTkFont(size=12, weight="bold")).grid(
                row=0, column=col, padx=10, pady=8, sticky="w")
        
        # Trova il netto ordinario come baseline
        netto_ordinario = risultati.get("Persona Fisica · Regime Ordinario", Decimal("0"))
        
        for row, (regime, netto) in enumerate(risultati.items(), start=1):
            risparmio = netto - netto_ordinario
            pct_risparmio = (risparmio / netto_ordinario * 100) if netto_ordinario > 0 else Decimal("0")
            
            ctk.CTkLabel(win, text=regime, font=ctk.CTkFont(size=11)).grid(
                row=row, column=0, padx=10, pady=4, sticky="w")
            ctk.CTkLabel(win, text=_euro(netto), font=ctk.CTkFont(size=11, weight="bold")).grid(
                row=row, column=1, padx=10, pady=4)
            ctk.CTkLabel(win, text=_euro(risparmio), font=ctk.CTkFont(size=11),
                         text_color=C["success"] if risparmio > 0 else C["danger"]).grid(
                row=row, column=2, padx=10, pady=4)
            ctk.CTkLabel(win, text=_pct(pct_risparmio), font=ctk.CTkFont(size=11)).grid(
                row=row, column=3, padx=10, pady=4)
        
        ctk.CTkButton(win, text="Chiudi", command=win.destroy, width=100).pack(pady=16)

    def _simulazione_what_if(self):
        """Simulazione what-if: variazione RAL, figli, regime."""
        try:
            ral_base = Decimal(self.ral_var.get().replace(".", "").replace(",", "."))
            if ral_base <= 0:
                raise InvalidOperation
        except (InvalidOperation, TypeError, ValueError):
            messagebox.showwarning("Pianificazione Fiscale", "RAL non valida.")
            return
        
        # Crea finestra what-if
        win = ctk.CTkToplevel(self)
        win.title("Simulazione What-If")
        win.geometry("600x500")
        win.transient(self.winfo_toplevel())
        win.grab_set()
        
        ctk.CTkLabel(win, text="🔮 Simulazione What-If",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=16)
        
        # Parametri what-if
        frame = ctk.CTkFrame(win)
        frame.pack(fill="x", padx=20, pady=10)
        
        # Variazione RAL
        ctk.CTkLabel(frame, text="Variazione RAL (%):").grid(row=0, column=0, padx=10, pady=8, sticky="e")
        ral_var = tk.StringVar(value="0")
        ctk.CTkEntry(frame, textvariable=ral_var, width=80).grid(row=0, column=1, padx=10, pady=8)
        
        # Aggiunta figli
        ctk.CTkLabel(frame, text="Figli aggiuntivi:").grid(row=1, column=0, padx=10, pady=8, sticky="e")
        figli_var = tk.StringVar(value="0")
        ctk.CTkEntry(frame, textvariable=figli_var, width=80).grid(row=1, column=1, padx=10, pady=8)
        
        # Cambio regime
        ctk.CTkLabel(frame, text="Regime alternativo:").grid(row=2, column=0, padx=10, pady=8, sticky="e")
        regime_var = tk.StringVar(value=self.regime_var.get())
        ctk.CTkOptionMenu(frame, variable=regime_var, width=200,
                          values=[v[0] for v in _REGIMI_CHOICES]).grid(row=2, column=1, padx=10, pady=8)
        
        def calcola_what_if():
            try:
                ral_pct = Decimal(ral_var.get().replace(",", "."))
                figli_agg = int(figli_var.get() or 0)
                ral_nuova = ral_base * (Decimal("1") + ral_pct / Decimal("100"))
                
                if ral_nuova <= 0:
                    raise InvalidOperation
            except (InvalidOperation, TypeError, ValueError):
                messagebox.showwarning("What-If", "Parametri non validi.")
                return
            
            # Calcola scenario base
            c_base = Contribuente(
                tipo=self._tipo_from_regime(self.regime_var.get()),
                anno_riferimento=int(self.anno_var.get()),
                provincia_residenza=self.prov_var.get().strip().upper(),
                comune_residenza=self.comune_var.get().strip(),
                figli_carico=1 if self.figli_var.get() else 0,
                coniuge_carico=self.coniuge_var.get(),
                partita_iva=self._valori_profilo().get("partita_iva", ""),
                ragione_sociale=self._valori_profilo().get("regime_sociale", ""),
                anni_residenza_estera=int(self._valori_profilo().get("anni_residenza_estera", 0)),
            )
            redditi_base = [Reddito(tipo=TipoReddito.LavoroDipendente, importo_lordo=ral_base,
                               contributi_previdenziali=(ral_base * _ALIQUOTA_INPS))]
            sim = SimulazioneService(self._rule_service, irpef_calc=IrpefCalculator())
            out_base = sim.esegui(c_base, redditi_base)
            
            # Calcola scenario what-if
            c_new = Contribuente(
                tipo=self._tipo_from_regime(regime_var.get()),
                anno_riferimento=int(self.anno_var.get()),
                provincia_residenza=self.prov_var.get().strip().upper(),
                comune_residenza=self.comune_var.get().strip(),
                figli_carico=(1 if self.figli_var.get() else 0) + figli_agg,
                coniuge_carico=self.coniuge_var.get(),
                partita_iva=self._valori_profilo().get("partita_iva", ""),
                ragione_sociale=self._valori_profilo().get("regime_sociale", ""),
                anni_residenza_estera=int(self._valori_profilo().get("anni_residenza_estera", 0)),
            )
            redditi_new = [Reddito(tipo=TipoReddito.LavoroDipendente, importo_lordo=ral_nuova,
                               contributi_previdenziali=(ral_nuova * _ALIQUOTA_INPS))]
            out_new = sim.esegui(c_new, redditi_new)
            
            # Mostra risultati
            diff_netto = out_new.reddito_netto_stimato - out_base.reddito_netto_stimato
            diff_tasse = out_new.totale_tasse - out_base.totale_tasse
            
            risultato_text = (
                f"BASE (RAL {_euro(ral_base)}, regime {self.regime_var.get()}):\n"
                f"  Netto annuo: {_euro(out_base.reddito_netto_stimato)}\n"
                f"  Tasse totali: {_euro(out_base.totale_tasse)}\n\n"
                f"WHAT-IF (RAL {_euro(ral_nuova)}, regime {regime_var.get()}, +{figli_agg} figli):\n"
                f"  Netto annuo: {_euro(out_new.reddito_netto_stimato)}\n"
                f"  Tasse totali: {_euro(out_new.totale_tasse)}\n\n"
                f"Δ NETTO: {_euro(diff_netto)} ({_pct(diff_netto / out_base.reddito_netto_stimato * 100) if out_base.reddito_netto_stimato > 0 else 'N/A'})\n"
                f"Δ TASSE: {_euro(diff_tasse)}"
            )
            
            result_text.delete("1.0", "end")
            result_text.insert("end", risultato_text)
        
        # Frame parametri
        param_frame = ctk.CTkFrame(win)
        param_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(param_frame, text="Parametri What-If", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=8)
        
        ctk.CTkLabel(param_frame, text="Variazione RAL (%):").grid(row=0, column=0, padx=10, pady=8, sticky="e")
        ral_pct_var = tk.StringVar(value="0")
        ctk.CTkEntry(param_frame, textvariable=ral_pct_var, width=80).grid(row=0, column=1, padx=10, pady=8)
        
        ctk.CTkLabel(param_frame, text="Figli aggiuntivi:").grid(row=1, column=0, padx=10, pady=8, sticky="e")
        figli_agg_var = tk.StringVar(value="0")
        ctk.CTkEntry(param_frame, textvariable=figli_agg_var, width=80).grid(row=1, column=1, padx=10, pady=8)
        
        ctk.CTkLabel(param_frame, text="Regime alternativo:").grid(row=2, column=0, padx=10, pady=8, sticky="e")
        regime_alt_var = tk.StringVar(value=self.regime_var.get())
        ctk.CTkOptionMenu(param_frame, variable=regime_alt_var, width=200,
                          values=[v[0] for v in _REGIMI_CHOICES]).grid(row=2, column=1, padx=10, pady=8)
        
        # Pulsante calcola
        ctk.CTkButton(win, text="🔮 Calcola What-If", width=150, command=calcola_what_if).pack(pady=10)
        
        # Area risultati
        result_text = ctk.CTkTextbox(win, height=200, wrap="word")
        result_text.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        result_text.insert("end", "Imposta i parametri e premi 'Calcola What-If' per vedere l'impatto delle variazioni.")
        
        ctk.CTkButton(win, text="Chiudi", command=win.destroy, width=100).pack(pady=10)

    def _nl_query(self):
        """Interfaccia query linguaggio naturale per domande fiscali."""
        win = ctk.CTkToplevel(self)
        win.title("💬 Query Linguaggio Naturale - Fisco")
        win.geometry("700x500")
        win.transient(self.winfo_toplevel())
        win.grab_set()
        
        ctk.CTkLabel(win, text="💬 Query Linguaggio Naturale - Consulente Fiscale AI",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=16)
        
        ctk.CTkLabel(win, text="Fai una domanda in linguaggio naturale su tasse, regimi, deduzioni, ecc.",
                     font=ctk.CTkFont(size=11), text_color=C["muted"]).pack(pady=(0, 10))
        
        input_frame = ctk.CTkFrame(win)
        input_frame.pack(fill="x", padx=20, pady=10)
        
        self.nl_query_var = tk.StringVar()
        entry = ctk.CTkEntry(input_frame, textvariable=self.nl_query_var, width=500,
                            placeholder_text="Es: 'Quali deduzioni posso fare con 2 figli a carico?'")
        entry.pack(side="left", fill="x", expand=True, padx=(10, 6), pady=10)
        entry.bind("<Return>", lambda _: self._execute_nl_query())
        
        ctk.CTkButton(input_frame, text="🔍 Chiedi", width=100,
                     command=self._execute_nl_query).pack(side="right", padx=(0, 10), pady=10)
        
        self.nl_result_text = ctk.CTkTextbox(win, height=350, wrap="word")
        self.nl_result_text.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        self.nl_result_text.insert("end", 
            "💬 Consulente Fiscale AI - Query Linguaggio Naturale\n\n"
            "Esempi di domande:\n"
            "• 'Quanto risparmio passando al regime forfettario con 35k €?'\n"
            "• 'Quali spese mediche posso dedurre al 19%?'\n"
            "• 'Come funziona il regime impatriati per 5 anni?'\n"
            "• 'Cosa cambia nel 2025 per gli scaglioni IRPEF?'\n"
            "• 'Conviene auto aziendale o rimborso chilometrico?'\n\n"
            "Scrivi la tua domanda e premi Invio o 'Chiedi'.\n\n"
            "⚠️ L'AI risponde basandosi su regole fiscali 2024-2027. "
            "Verifica sempre con un commercialista."
        )
        
        ctk.CTkButton(win, text="Chiudi", command=win.destroy, width=100).pack(pady=10)
    
    def _execute_nl_query(self):
        """Esegue query linguaggio naturale."""
        query = self.nl_query_var.get().strip()
        if not query:
            return
        
        self.nl_result_text.delete("1.0", "end")
        self.nl_result_text.insert("end", "🤖 Elaborando...\n\n")
        
        def execute():
            try:
                from ai_services import get_ai_manager
                manager = get_ai_manager()
                
                if not manager.default_provider:
                    self.winfo_toplevel().after(0, lambda: self.nl_result_text.delete("1.0", "end"))
                    self.winfo_toplevel().after(0, lambda: self.nl_result_text.insert("end", 
                        "⚠️ AI non configurato.\n\n"
                        "Configura un provider AI (OpenAI, Anthropic, Ollama) per usare le query naturali."
                    ))
                    return
                
                context = f"""
Profilo utente: RAL {self.ral_var.get()} €, Regime {self.regime_var.get()}, 
Figli: {'Sì' if self.figli_var.get() else 'No'}, Coniuge: {'Sì' if self.coniuge_var.get() else 'No'},
Provincia: {self.prov_var.get()}, Comune: {self.comune_var.get()}
Regime: {self.regime_var.get()}, Part-time: {'Sì' if self.part_time_var.get() else 'No'},
Auto aziendale: {'Sì' if self.auto_aziendale_var.get() else 'No'}
"""
                
                prompt = f"""
Sei un consulente fiscale italiano. Rispondi alla domanda dell'utente basandoti sulle 
regole fiscali italiane 2024-2027.

CONTESTO UTENTE:
{context}

DOMANDA: {self.nl_query_var.get()}

Rispondi in italiano, in modo chiaro e pratico. Cita articoli di legge se pertinenti.
Indica se la risposta è certa, probabile o incerta. Consiglia di verificare con commercialista.
"""
                
                response = manager.ask_stream(prompt)
                
                for chunk in response:
                    self.winfo_toplevel().after(0, lambda c=chunk: self.nl_result_text.insert("end", c))
                    self.winfo_toplevel().after(0, lambda: self.nl_result_text.see("end"))
                
            except Exception as e:
                self.winfo_toplevel().after(0, lambda: self.nl_result_text.delete("1.0", "end"))
                self.winfo_toplevel().after(0, lambda: self.nl_result_text.insert("end", f"❌ Errore: {e}"))
        
        threading.Thread(target=execute, daemon=True).start()

    def export_json(self):
        """Esporta tutti i dati in JSON per integrazione con altri strumenti."""
        try:
            filepath = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.json")],
                title="Esporta dati fiscali (JSON)"
            )
            if not filepath:
                return
            
            dati = {
                "version": "1.0",
                "timestamp": datetime.datetime.now().isoformat(),
                "profilo": self._valori_profilo(),
                "tabella_netto": {}
            }
            
            for anno in _ANNI:
                for ral in _RAL_DEFAULT:
                    key = (anno, ral)
                    if key in self._table_vars:
                        if anno not in dati["tabella_netto"]:
                            dati["tabella_netto"][anno] = {}
                        dati["tabella_netto"][anno][ral] = self._table_vars[key].get()
            
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(dati, f, indent=2, ensure_ascii=False, default=str)
            
            messagebox.showinfo("Esportazione JSON", f"Dati esportati in:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Errore esportazione", f"Errore durante l'esportazione JSON:\n{e}")

    def import_json(self):
        """Importa dati da file JSON per integrazione."""
        try:
            filepath = filedialog.askopenfilename(
                filetypes=[("JSON files", "*.json"), ("All files", "*.json")],
                title="Importa dati fiscali (JSON)"
            )
            if not filepath:
                return
            
            with open(filepath, "r", encoding="utf-8") as f:
                dati = json.load(f)
            
            if "profilo" in dati:
                profilo_dati = dati["profilo"]
                if "Nome" in profilo_dati or "nome" in profilo_dati:
                    self.nome_var.set(profilo_dati.get("Nome", profilo_dati.get("nome", "")))
                if "Anno" in profilo_dati or "anno" in profilo_dati:
                    self.anno_var.set(profilo_dati.get("Anno", profilo_dati.get("anno", "2026")))
                if "RAL" in profilo_dati or "ral" in profilo_dati:
                    self.ral_var.set(str(profilo_dati.get("RAL", profilo_dati.get("ral", "32000"))))
                if "Partita IVA" in profilo_dati or "partita_iva" in profilo_dati:
                    self.partita_iva_var.set(profilo_dati.get("Partita IVA", profilo_dati.get("partita_iva", "")))
                if "Regime" in profilo_dati or "regime" in profilo_dati:
                    regime = profilo_dati.get("Regime", profilo_dati.get("regime", "PersonaFisica"))
                    if regime in [v[0] for v in _REGIMI_CHOICES]:
                        self.regime_var.set(regime)
                if "Cedolare" in profilo_dati:
                    self.cedolare_var.set(str(profilo_dati.get("Cedolare", "False")).lower() == "true")
                if "Impatriati" in profilo_dati:
                    self.impatriati_var.set(str(profilo_dati.get("Impatriati", "False")).lower() == "true")
                if "Part-time" in profilo_dati:
                    self.part_time_var.set(str(profilo_dati.get("Part-time", "False")).lower() == "true")
                if "Auto aziendale" in profilo_dati:
                    self.auto_aziendale_var.set(str(profilo_dati.get("Auto aziendale", "False")).lower() == "true")
                
                self._carica_profilo(avviso=False)
                self._aggiorna_tabella()
                self._calcola()
                messagebox.showinfo("Importazione JSON", f"Dati importati da:\n{filepath}")
            else:
                messagebox.showwarning("Importazione JSON", "Formato JSON non riconosciuto.")
        except Exception as e:
            messagebox.showerror("Errore importazione", f"Errore durante l'importazione JSON:\n{e}")

    def _ai_suggerimenti(self):
        """Genera suggerimenti di ottimizzazione fiscale usando AI."""
        # Verifica dati profilo
        ral = self.ral_var.get().strip()
        if not ral:
            messagebox.showwarning("AI Suggerimenti", "Inserisci prima una RAL valida.")
            return
        
        try:
            ral_val = float(ral.replace(".", "").replace(",", "."))
            if ral_val <= 0:
                messagebox.showwarning("AI Suggerimenti", "RAL non valida.")
                return
        except ValueError:
            messagebox.showwarning("AI Suggerimenti", "RAL non valida.")
            return
        
        # Crea finestra suggerimenti
        win = ctk.CTkToplevel(self)
        win.title("🤖 AI Suggerimenti Ottimizzazione Fiscale")
        win.geometry("800x600")
        win.transient(self.winfo_toplevel())
        win.grab_set()
        
        ctk.CTkLabel(win, text="🤖 AI Suggerimenti Ottimizzazione Fiscale",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=16)
        
        # Info profilo corrente
        info_frame = ctk.CTkFrame(win)
        info_frame.pack(fill="x", padx=20, pady=10)
        
        regime = self.regime_var.get()
        figli = "Sì" if self.figli_var.get() else "No"
        coniuge = "Sì" if self.coniuge_var.get() else "No"
        
        ctk.CTkLabel(info_frame, 
                     text=f"RAL: {ral} € | Regime: {regime} | Figli: {figli} | Coniuge: {coniuge}",
                     font=ctk.CTkFont(size=12)).pack(pady=10)
        
        # Area risultati
        result_text = ctk.CTkTextbox(win, height=400, wrap="word")
        result_text.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        result_text.insert("end", "🤖 Generando suggerimenti AI...\n\n")
        
        def genera_suggerimenti():
            try:
                from ai_services import get_ai_manager, AIManager
                
                manager = get_ai_manager()
                
                # Verifica se AI è configurato
                if not manager.default_provider:
                    result_text.delete("1.0", "end")
                    result_text.insert("end", 
                        "⚠️ AI non configurato.\n\n"
                        "Per utilizzare i suggerimenti AI, configura un provider:\n"
                        "1. OpenAI: imposta OPENAI_API_KEY nelle variabili d'ambiente\n"
                        "2. Anthropic: imposta ANTHROPIC_API_KEY\n"
                        "3. Ollama: avvia ollama serve in locale\n\n"
                        "Poi riavvia l'applicazione."
                    )
                    return
                
                # Costruisci prompt
                prompt = f"""
Sei un consulente fiscale italiano esperto. Analizza questo profilo e fornisci 
suggerimenti concreti di ottimizzazione fiscale per il 2024-2027.

PROFILO CONTRIBUENTE:
- RAL: {ral} €
- Regime fiscale: {self.regime_var.get()}
- Figli a carico: {'Sì' if self.figli_var.get() else 'No'}
- Coniuge a carico: {'Sì' if self.coniuge_var.get() else 'No'}
- Part-time: {'Sì' if self.part_time_var.get() else 'No'}
- Auto aziendale: {'Sì' if self.auto_aziendale_var.get() else 'No'}
- Cedolare secca: {'Sì' if self.cedolare_var.get() else 'No'}
- Impatriati: {'Sì' if self.impatriati_var.get() else 'No'}
- Partita IVA: {self.partita_iva_var.get() or 'No'}
- Anni residenza estera: {self.anni_residenza_estera_var.get()}
- Provincia: {self.prov_var.get()}
- Comune: {self.comune_var.get()}

Fornisci suggerimenti concreti e prioritizzati per:
1. Riduzione imposte (IRPEF, addizionali)
2. Ottimizzazione contributi previdenziali
3. Benefit aziendali (fringe benefit, welfare, auto)
4. Regimi agevolati applicabili
5. Pianificazione pluriennale 2024-2027

Formato: elenco puntato, priorità alta/media/bassa, risparmio stimato in €.
Lingua: italiano.
"""
                
                response = manager.ask(prompt)
                
                # Update UI in main thread
                win.after(0, lambda: result_text.delete("1.0", "end"))
                win.after(0, lambda: result_text.insert("end", response))
                
            except Exception as e:
                win.after(0, lambda: result_text.delete("1.0", "end"))
                win.after(0, lambda: result_text.insert("end", f"❌ Errore: {e}"))
        
        # Pulsante genera
        ctk.CTkButton(win, text="🚀 Genera Suggerimenti", width=180,
                     command=lambda: threading.Thread(target=genera_suggerimenti, daemon=True).start()
                     ).pack(pady=10)
        
        # Area risultati
        result_text = ctk.CTkTextbox(win, height=400, wrap="word")
        result_text.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        result_text.insert("end", "Premi 'Genera Suggerimenti' per ottenere consigli AI personalizzati.\n\n"
            "L'AI analizzerà il tuo profilo fiscale e fornirà suggerimenti concreti per:\n"
            "• Riduzione IRPEF e addizionali\n"
            "• Ottimizzazione contributi previdenziali\n"
            "• Benefit aziendali ottimali\n"
            "• Regimi agevolati applicabili\n"
            "• Pianificazione 2024-2027\n\n"
            "⚠️ Nota: I suggerimenti sono orientativi. Consulta sempre un commercialista.")
        
        ctk.CTkButton(win, text="Chiudi", command=win.destroy, width=100).pack(pady=10)