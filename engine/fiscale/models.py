"""Modelli di dominio del motore fiscale (port di TaxPlanner Italia).

Tutti gli importi sono Decimal per replicare esattamente il comportamento di
`decimal` + `Math.Round(x, 2)` del motore C# (banker's rounding, ROUND_HALF_EVEN).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import IntEnum, auto
from typing import Optional


class TipoContribuente(IntEnum):
    PersonaFisica = auto()
    SocietaDiCapitali = auto()
    SocietaDiPersone = auto()
    PartitaIvaForfettaria = auto()
    PartitaIvaOrdinaria = auto()


class RegimeFiscale(IntEnum):
    Ordinario = auto()
    Forfettario = auto()
    StartupInnovative = auto()
    Agricolo = auto()
    TonnageTax = auto()


class TipoReddito(IntEnum):
    LavoroDipendente = auto()
    LavoroAutonomo = auto()
    Impresa = auto()
    Capitale = auto()
    Diversi = auto()
    Fondiaria = auto()
    Pensione = auto()


class CategoriaContributiva(IntEnum):
    GestioneSeparata = auto()
    Artigiani = auto()
    Commercianti = auto()


class TipoSpesa(IntEnum):
    SpeseMediche = auto()
    InteressiMutuo = auto()
    AssicurazioneVita = auto()
    SpeseFunebri = auto()
    Istruzione = auto()
    ErogazioniLiberali = auto()
    SpeseSportive = auto()
    SpeseVeterinarie = auto()
    BonusEdilizio = auto()
    RicercaSviluppo = auto()
    InnovazioneTecnologica = auto()
    PrevidenzaComplementare = auto()
    WelfareAziendale = auto()
    SpesePsicologo = auto()
    AffittoGiovaniUnder31 = auto()
    RistrutturazioneEdilizia2026 = auto()
    EfficienzaEnergetica2026 = auto()
    BonusMobilitaSostenibile = auto()
    Design = auto()
    Formazione40 = auto()
    InvestimentiSud = auto()
    BeniStrumentali = auto()


class TipoCreditoImposta(IntEnum):
    RicercaSviluppo = auto()
    InnovazioneTecnologica = auto()
    Formazione40 = auto()
    InvestimentiSud = auto()
    EfficienzaEnergetica = auto()
    BeniStrumentali = auto()
    PatentBox = auto()
    CreditoRistrutturazione2026 = auto()
    CreditoEfficienzaEnergetica2026 = auto()
    CreditoAssunzioniDonne = auto()
    CreditoSud2025 = auto()
    CreditoZESUnica = auto()


class RegimeSpeciale(IntEnum):
    Nessuno = auto()
    Impatriati = auto()
    NeoResidenti = auto()
    StartupInnovativa = auto()
    PMIInnovativa = auto()
    ForfettarioProfessionisti = auto()
    RegimeForfettario2026 = auto()
    PatentBox2025 = auto()
    StartupInnovativa2026 = auto()
    ZESUnicaMezzogiorno = auto()
    ConcordatoPreventivoBiennale = auto()


class TipoIncentivoContributivo(IntEnum):
    Nessuno = auto()
    Under36 = auto()
    DonneSvantaggiate = auto()
    CIGS_NASpI = auto()
    Over50 = auto()
    Apprendistato = auto()
    ZES = auto()


class TipologiaMovimentoIva(IntEnum):
    Vendita = auto()
    Acquisto = auto()


class TipoScadenza(IntEnum):
    Fiscale = auto()
    Contributiva = auto()
    Versamento = auto()
    Dichiarazione = auto()
    Personale = auto()


class TipoDipendenteInps(IntEnum):
    Privato = auto()
    Pubblico = auto()
    Apprendista = auto()


@dataclass
class ScaglioneIrpef:
    minimo: Decimal = Decimal(0)
    massimo: Optional[Decimal] = None
    aliquota: Decimal = Decimal(0)
    detrazione: Decimal = Decimal(0)


@dataclass
class AddizionaleRegionale:
    regione: str = ""
    aliquota_base: Decimal = Decimal(0)
    scaglioni: list = field(default_factory=list)
    aliquote: list = field(default_factory=list)


@dataclass
class AddizionaleComunale:
    comune: str = ""
    codice_catastale: str = ""
    aliquota: Decimal = Decimal(0)
    soglia_esenzione: Decimal = Decimal(0)
    scaglioni: Optional[list] = None
    aliquote: Optional[list] = None


@dataclass
class ZesAliquota2026:
    regione: str = ""
    grandi: Decimal = Decimal(0)
    medie: Decimal = Decimal(0)
    piccole: Decimal = Decimal(0)


@dataclass
class Contribuente:
    id: int = 0
    codice_fiscale: str = ""
    nome: str = ""
    cognome: str = ""
    sesso: str = "M"
    data_nascita: Optional[object] = None  # datetime.date
    comune_residenza: str = ""
    provincia_residenza: str = ""
    tipo: TipoContribuente = TipoContribuente.PersonaFisica
    regime: RegimeFiscale = RegimeFiscale.Ordinario
    anno_riferimento: int = 2026
    coniuge_carico: bool = False
    figli_carico: int = 0
    figli_minori_tre_anni: int = 0
    figli_disabili: int = 0
    genitore_single: bool = False
    usa_cedolare_secca: bool = False
    cedolare_concordato: bool = False
    rendita_catastale_imu: Decimal = Decimal(0)
    aliquota_imu: Decimal = Decimal(0)
    numero_immobili_locazione_breve: int = 0
    numero_mensilita_extra: int = 0
    incremento_retributivo_rinnovo: Decimal = Decimal(0)
    premio_produttivita: Decimal = Decimal(0)
    importo_maggiorazioni_lavoro: Decimal = Decimal(0)
    aderisce_bonus_mamme: bool = False
    ragione_sociale: Optional[str] = None
    partita_iva: Optional[str] = None
    codice_ateco: Optional[str] = None
    data_costituzione: Optional[object] = None
    capitale_sociale: Optional[Decimal] = None
    is_disabile: bool = False
    is_lavoratore_fragile: bool = False
    codice_zes: str = ""
    regime_speciale: RegimeSpeciale = RegimeSpeciale.Nessuno
    incentivo_contributivo: TipoIncentivoContributivo = TipoIncentivoContributivo.Nessuno
    anni_residenza_estera: int = 0
    anni_attivita_impresa: int = 0
    is_startup_innovativa: bool = False
    is_pmi_innovativa: bool = False
    regione_azienda: str = ""
    categoria_contributiva: CategoriaContributiva = CategoriaContributiva.GestioneSeparata
    richiede_riduzione_forfettari: bool = False
    is_pensionato_over65: bool = False
    perdite_pregresse_imprenditore: Decimal = Decimal(0)
    giorni_buoni_pasto_elettronici: int = 0
    giorni_buoni_pasto_cartacei: int = 0
    ha_redditi_cripto: bool = False
    plusvalenze_cripto: Decimal = Decimal(0)
    minusvalenze_cripto: Decimal = Decimal(0)
    monitoraggio_cripto: bool = False
    is_part_time: bool = False
    ore_settimanali_part_time: int = 0
    ore_settimanali_full_time: int = 40
    tipo_dipendente_inps: TipoDipendenteInps = TipoDipendenteInps.Privato
    rimborso_smart_working_mensile: Decimal = Decimal(0)
    ha_auto_aziendale: bool = False
    valore_auto_aziendale: Decimal = Decimal(0)
    auto_aziendale_elettrica: bool = False
    usa_regime_impatriati: bool = False

    # Spese e deduzioni (input per DetrazioniService / StrumentiRisparmio / ForfettarioPrecisione)
    spesa_affitto_annua: Decimal = Decimal(0)
    spesa_psicologo_annua: Decimal = Decimal(0)
    spese_mediche_annue: Decimal = Decimal(0)
    spese_istruzione_annue: Decimal = Decimal(0)
    spese_sportive_annue: Decimal = Decimal(0)
    erogazioni_liberali_annue: Decimal = Decimal(0)
    abbonamenti_tpl_annui: Decimal = Decimal(0)
    spese_ristrutturazione_annue: Decimal = Decimal(0)
    spese_efficientamento_annue: Decimal = Decimal(0)
    spese_mobili_annue: Decimal = Decimal(0)
    welfare_annuo: Decimal = Decimal(0)
    reddito_complessivo_ultimo_anno: Decimal = Decimal(0)
    previdenza_complementare_annua: Decimal = Decimal(0)
    contributi_previdenziali_versati: Decimal = Decimal(0)
    perdite_pregresse_forfettario: Decimal = Decimal(0)
    ricavi_compensi_annui: Decimal = Decimal(0)
    spese_deducibili_annue: Decimal = Decimal(0)

    @property
    def is_under31(self) -> bool:
        return self.eta() < 31

    def eta(self) -> int:
        if self.data_nascita is None:
            return 40
        from datetime import date
        oggi = date.today()
        return oggi.year - self.data_nascita.year - (
            (oggi.month, oggi.day) < (self.data_nascita.month, self.data_nascita.day)
        )


@dataclass
class Reddito:
    tipo: TipoReddito = TipoReddito.LavoroDipendente
    descrizione: str = ""
    importo_lordo: Decimal = Decimal(0)
    importo_netto: Optional[Decimal] = None
    contributi_previdenziali: Decimal = Decimal(0)
    deduzioni_specifiche: Decimal = Decimal(0)
    anno_competenza: int = 0
    is_locazione_breve: bool = False


@dataclass
class SpesaDeducibile:
    descrizione: str = ""
    categoria: str = ""
    importo: Decimal = Decimal(0)
    percentuale_deducibilita: Decimal = Decimal(100)
    is_deducibile_da_reddito_impresa: bool = False
    is_detraibile_irpef: bool = False
    riferimento_normativo: Optional[str] = None
    tipo: TipoSpesa = TipoSpesa.SpeseMediche
    has_iva_detraibile: bool = False


@dataclass
class DetrazioneIrpef:
    codice: str = ""
    descrizione: str = ""
    importo_spesa: Decimal = Decimal(0)
    percentuale_detrazione: Decimal = Decimal(0)
    limite_massimo: Optional[Decimal] = None
    reddito_massimo_accesso: Optional[Decimal] = None
    spetta_per_intero: bool = True
    is_detraibile_irpef: bool = True


@dataclass
class CreditoImposta:
    codice: str = ""
    descrizione: str = ""
    importo: Decimal = Decimal(0)
    is_utilizzabile_in_compensazione: bool = False
    is_rimborsabile: bool = False
    anno_maturazione: int = 0
    tipo: TipoCreditoImposta = TipoCreditoImposta.RicercaSviluppo
    spesa: Decimal = Decimal(0)
    aliquota: Decimal = Decimal(0)
    importo_calcolato: Optional[Decimal] = None


@dataclass
class BilancioSocieta:
    anno: int = 2026
    ricavi_vendite: Decimal = Decimal(0)
    costi_produzione: Decimal = Decimal(0)
    costo_personale: Decimal = Decimal(0)
    ammortamenti: Decimal = Decimal(0)
    oneri_finanziari: Decimal = Decimal(0)
    proventi_finanziari: Decimal = Decimal(0)
    utile_perdita_ante_imposte: Decimal = Decimal(0)
    ires: Decimal = Decimal(0)
    irap: Decimal = Decimal(0)
    utile_netto: Decimal = Decimal(0)
    riserve: Decimal = Decimal(0)
    dividendi_deliberati: Decimal = Decimal(0)
    versamenti_acconto: Decimal = Decimal(0)


@dataclass
class ScaglioneCalcolato:
    da: Decimal = Decimal(0)
    a: Decimal = Decimal(0)
    aliquota: Decimal = Decimal(0)
    imponibile_nel_scaglione: Decimal = Decimal(0)
    imposta_nel_scaglione: Decimal = Decimal(0)


@dataclass
class DetrazioneApplicata:
    codice: str = ""
    descrizione: str = ""
    importo_spesa: Decimal = Decimal(0)
    percentuale: Decimal = Decimal(0)
    importo_detrazione: Decimal = Decimal(0)


@dataclass
class CalcoloIrpef:
    reddito_complessivo: Decimal = Decimal(0)
    reddito_imponibile: Decimal = Decimal(0)
    imposta_lorda: Decimal = Decimal(0)
    detrazioni_lavoro: Decimal = Decimal(0)
    detrazioni_pensione: Decimal = Decimal(0)
    detrazioni_famiglia: Decimal = Decimal(0)
    detrazioni_oneri: Decimal = Decimal(0)
    detrazioni_totali: Decimal = Decimal(0)
    sterilizzazione_detrazioni: Decimal = Decimal(0)
    imposta_netta: Decimal = Decimal(0)
    addizionale_regionale: Decimal = Decimal(0)
    addizionale_comunale: Decimal = Decimal(0)
    totale_irpef: Decimal = Decimal(0)
    trattamento_integrativo: Decimal = Decimal(0)
    dettaglio_scaglioni: list = field(default_factory=list)
    detrazioni_applicate: list = field(default_factory=list)


@dataclass
class CalcoloIres:
    reddito_imponibile: Decimal = Decimal(0)
    aliquota_ires: Decimal = Decimal("0.24")
    ires_lorda: Decimal = Decimal(0)
    crediti_imposta: Decimal = Decimal(0)
    ires_netta: Decimal = Decimal(0)
    acconto_ires: Decimal = Decimal(0)
    saldo_ires: Decimal = Decimal(0)


@dataclass
class CalcoloIrap:
    base_imponibile: Decimal = Decimal(0)
    aliquota_standard: Decimal = Decimal("0.039")
    aliquota_regionale: Decimal = Decimal(0)
    irap_lorda: Decimal = Decimal(0)
    deduzioni_personale: Decimal = Decimal(0)
    irap_netta: Decimal = Decimal(0)
    acconto_irap: Decimal = Decimal(0)
    saldo_irap: Decimal = Decimal(0)


@dataclass
class CalcoloForfettarioPrecisione:
    codice_ateco: str = ""
    settore: str = ""
    coefficiente_applicato: Decimal = Decimal(0)
    coefficiente_da_tabella: bool = False
    ricavi: Decimal = Decimal(0)
    reddito_imponibile: Decimal = Decimal(0)
    aliquota_imposta: Decimal = Decimal(0)
    anni_nuova_attivita: int = 0
    contributi_minimo: Decimal = Decimal(0)
    contributi_eccedenza: Decimal = Decimal(0)
    percentuale_riduzione_contributi: Decimal = Decimal(0)
    riduzione_contributi: Decimal = Decimal(0)
    contributi_totali: Decimal = Decimal(0)
    contributi_deducibili: Decimal = Decimal(0)
    reddito_imponibile_netto: Decimal = Decimal(0)
    imposta_sostitutiva: Decimal = Decimal(0)
    perdite_utilizzate: Decimal = Decimal(0)
    perdite_residue: Decimal = Decimal(0)
    contributi_eccedenza_non_dedotti: Decimal = Decimal(0)
    quota_contributi_rate_fisse: Decimal = Decimal(0)
    quota_contributi_saldo_acconti: Decimal = Decimal(0)
    totale_versare: Decimal = Decimal(0)
    carico_fiscale_totale: Decimal = Decimal(0)
    incidenza_totale: Decimal = Decimal(0)
    fuoriuscita_immediata: bool = False
    nota_fuoriuscita: str = ""
    note: list = field(default_factory=list)


@dataclass
class SuggerimentoOttimizzazione:
    titolo: str = ""
    descrizione: str = ""
    risparmio_stimato: Decimal = Decimal(0)
    categoria: str = ""
    difficolta: str = ""
    riferimento_normativo: str = ""
    richiede_consulente: bool = False


@dataclass
class VoceCuneo:
    etichetta: str = ""
    valore: Decimal = Decimal(0)
    colore: str = ""
    percentuale: float = 0.0
    is_costo: bool = True


@dataclass
class VoceBusta:
    descrizione: str = ""
    importo: Decimal = Decimal(0)
    tipo: str = ""
    esente: bool = False


@dataclass
class RisultatoSimulazione:
    contribuente: Optional[Contribuente] = None
    anno: int = 2026
    irpef: Optional[CalcoloIrpef] = None
    totale_contributi_previdenziali: Decimal = Decimal(0)
    esonero_contributi: Decimal = Decimal(0)
    bonus_cuneo: Decimal = Decimal(0)
    ulteriore_detrazione_cuneo: Decimal = Decimal(0)
    trattamento_integrativo: Decimal = Decimal(0)
    totale_tasse: Decimal = Decimal(0)
    reddito_netto_stimato: Decimal = Decimal(0)
    cedolare_secca: Decimal = Decimal(0)
    imu_stimata: Decimal = Decimal(0)
    presunzione_imprenditorialita: bool = False
    nota_presunzione_impresa: Optional[str] = None
    ritenuta_intermediari_locazioni_brevi: Decimal = Decimal(0)
    imposta_sostitutiva_flat_tax_rinnovi: Decimal = Decimal(0)
    imposta_sostitutiva_premi_produttivita: Decimal = Decimal(0)
    imposta_sostitutiva_maggiorazioni: Decimal = Decimal(0)
    bonus_mamme_annuale: Decimal = Decimal(0)
    totale_imposte_sostitutive_2026: Decimal = Decimal(0)
    netto_mensile_base: Decimal = Decimal(0)
    netto_mensilita_extra: Decimal = Decimal(0)
    netto_part_time_mensile: Decimal = Decimal(0)
    fattore_part_time: Decimal = Decimal(1)
    contributi_inps_dipendente: Decimal = Decimal(0)
    rimborso_smart_working_annuale: Decimal = Decimal(0)
    auto_aziendale_fringe_annuale: Decimal = Decimal(0)
    esenzione_impatriati_annuale: Decimal = Decimal(0)
    ires: Optional[CalcoloIres] = None
    irap: Optional[CalcoloIrap] = None
    utile_netto_dopo_tasse: Decimal = Decimal(0)
    dividendi_netti: Decimal = Decimal(0)
    costo_totale_lavoro: Decimal = Decimal(0)
    forfettario_precisione: Optional[CalcoloForfettarioPrecisione] = None
    nota_fuoriuscita_forfettario: Optional[str] = None
    beneficio_buoni_pasto: Decimal = Decimal(0)
    imposta_cripto: Decimal = Decimal(0)
    ha_redditi_cripto: bool = False
    suggerimenti: list = field(default_factory=list)
    risparmio_stimato: Decimal = Decimal(0)
    decomposizione_cuneo: list = field(default_factory=list)
    voci_busta: list = field(default_factory=list)
