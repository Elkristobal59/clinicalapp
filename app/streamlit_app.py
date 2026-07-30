import os
import sys
import time
import json
import re
import requests
from dotenv import load_dotenv

load_dotenv()

import streamlit as st
import pandas as pd

# Composant de persistance navigateur (localStorage) — optionnel : si absent,
# l'app tourne normalement, juste sans survie au refresh.
try:
    from streamlit_local_storage import LocalStorage
except ImportError:
    LocalStorage = None

# Ajouter le dossier parent au PATH pour les imports (scripts/…)
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from scripts.live_scraper import download_pdf_for_nctid
except ImportError:
    download_pdf_for_nctid = None

# Favicon de l'onglet : emblème seul (croix + cœur) = cliner_logo2.png,
# sinon le logo complet (avec texte), sinon l'emoji.
_fav = os.path.join(os.path.dirname(__file__), "assets", "cliner_logo2.png")
_logo_ico = os.path.join(os.path.dirname(__file__), "assets", "cliner_logo.png")
_page_icon = _fav if os.path.exists(_fav) else (_logo_ico if os.path.exists(_logo_ico) else "🫀")
st.set_page_config(page_title="CliNER — Clinical NER", page_icon=_page_icon, layout="wide")

# --------------------------------------------------------------------------- #
# Thème visuel CliNER — dark néon (cyan/teal + bleu nuit), style logo.
# config.toml gère les couleurs de base ; ce CSS ajoute la touche néon
# (police Orbitron, glow des titres, boutons, onglets).
# --------------------------------------------------------------------------- #
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@600;800&family=Rajdhani:wght@500;600&display=swap');

.stApp {
  background: radial-gradient(1200px 600px at 50% -10%, #0e2a3a 0%, #0A1420 55%);
}

/* Bannière collée en haut (moins d'espace vide au-dessus) */
.block-container { padding-top: 1.5rem; }

/* Bannière CliNER — wordmark néon (texte = net à toute taille) */
.cliner-hero {
  text-align: center;
  padding: 22px 0 16px;
  margin: 0 0 8px;
  background: radial-gradient(700px 240px at 50% 0%, rgba(34,211,238,.10), transparent 70%);
  border-bottom: 1px solid #16324a;
}
.cliner-word {
  font-family: 'Orbitron', sans-serif; font-weight: 800;
  font-size: clamp(44px, 7vw, 96px); line-height: 1; letter-spacing: 2px;
}
.cliner-word .cli {
  background: linear-gradient(180deg,#8fe3ff,#22D3EE 55%,#0ea5e9);
  -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent; color: transparent;
  filter: drop-shadow(0 0 18px rgba(34,211,238,.55));
}
.cliner-word .ner {
  background: linear-gradient(180deg,#9af5b8,#22c55e 55%,#16a34a);
  -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent; color: transparent;
  filter: drop-shadow(0 0 18px rgba(34,197,94,.5));
}
.cliner-tag {
  font-family: 'Rajdhani', sans-serif; font-weight: 600;
  letter-spacing: 6px; font-size: clamp(11px, 1.4vw, 16px);
  color: #9fd0da; margin-top: 8px;
}

/* Titres façon logo */
h1, h2, h3 {
  font-family: 'Orbitron', sans-serif !important;
  color: #7FF7EC !important;
  letter-spacing: .5px;
  text-shadow: 0 0 10px rgba(34,211,238,.45);
}

/* Texte courant */
.stMarkdown, label, p { font-family: 'Rajdhani', sans-serif; }

/* Boutons néon */
.stButton > button {
  background: linear-gradient(90deg,#06B6D4,#3B82F6);
  color:#03141c; border:1px solid #22D3EE; border-radius:10px;
  font-weight:700; letter-spacing:.3px;
  box-shadow:0 0 12px rgba(34,211,238,.35);
  transition: box-shadow .2s ease;
}
.stButton > button:hover { box-shadow:0 0 20px rgba(34,211,238,.75); border-color:#7FF7EC; }

/* Onglets — plus espacés + police plus grande */
.stTabs [data-baseweb="tab-list"] { gap: 22px; border-bottom: 1px solid #16324a; }
.stTabs [data-baseweb="tab"] {
  background:#10202E; border:1px solid #163247; border-radius:10px 10px 0 0; color:#9fd6df;
  padding: 12px 26px;                 /* espace interne = onglets plus larges */
}
.stTabs [data-baseweb="tab"] p {
  font-size: 1.18rem !important;      /* taille des libellés */
  font-weight: 600;
}
.stTabs [aria-selected="true"] {
  background:#0d2a3f; color:#7FF7EC !important;
  box-shadow: inset 0 -2px 0 #22D3EE, 0 0 10px rgba(34,211,238,.25);
}
.stTabs [aria-selected="true"] p { color:#7FF7EC !important; }

/* Sidebar */
section[data-testid="stSidebar"] {
  background:#0A1826; border-right:1px solid #14364e;
}

/* Cartes / metrics / alertes */
[data-testid="stMetric"], .stAlert {
  border:1px solid #163247; border-radius:10px;
  box-shadow: 0 0 10px rgba(34,211,238,.08);
}

/* Focus des champs */
input:focus, textarea:focus {
  border-color:#22D3EE !important; box-shadow:0 0 8px rgba(34,211,238,.4) !important;
}

/* ============ 1. SIDEBAR : métriques en cartes néon ============ */
section[data-testid="stSidebar"] [data-testid="stMetric"] {
  background:#0d2033; border:1px solid #1b3f5c; border-radius:10px;
  padding:10px 12px; margin-bottom:8px;
  box-shadow:0 0 10px rgba(34,211,238,.10);
}
section[data-testid="stSidebar"] [data-testid="stMetricLabel"] p {
  color:#7fb9c9 !important; font-size:.72rem !important;
  letter-spacing:.5px; text-transform:uppercase;
}
section[data-testid="stSidebar"] [data-testid="stMetricValue"] {
  color:#7FF7EC !important; font-size:.88rem !important; font-weight:700;
  white-space:normal !important; overflow:visible !important;
  text-overflow:clip !important; line-height:1.25;
}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 { font-size:1.05rem !important; }

/* ============ 2. TABLEAUX : contour néon ============ */
[data-testid="stDataFrame"], [data-testid="stDataEditor"] {
  border:1px solid #1b3f5c; border-radius:10px; overflow:hidden;
  box-shadow:0 0 12px rgba(34,211,238,.08);
}

/* ============ 3. CHAMPS DE SAISIE : accents cyan + focus ============ */
[data-baseweb="select"] > div, .stTextInput input, .stNumberInput input {
  background:#0d1c2b !important; border:1px solid #1b3f5c !important; border-radius:8px !important;
}
[data-baseweb="select"] > div:focus-within {
  border-color:#22D3EE !important; box-shadow:0 0 8px rgba(34,211,238,.4) !important;
}
/* chips du multiselect en cyan */
[data-baseweb="tag"] {
  background:linear-gradient(90deg,#0e7490,#0369a1) !important;
  border:1px solid #22D3EE !important; color:#e6feff !important;
}
/* slider cyan */
.stSlider [role="slider"] { box-shadow:0 0 8px rgba(34,211,238,.6) !important; }
.stSlider [data-baseweb="slider"] div[data-testid="stTickBar"] { background:transparent !important; }

/* ============ 4. MESSAGES : couleurs natives conservées (succès=vert, warning=ambre,
   erreur=rouge, info=bleu), juste arrondis. Les verrous 🔒 ont leur propre carte cyan. */
[data-testid="stAlert"] {
  border-radius:10px !important;
  box-shadow:0 0 10px rgba(0,0,0,.25);
}
.cliner-lock {
  background:#0d2233; border:1px solid #1b3f5c; border-left:4px solid #22D3EE;
  border-radius:10px; padding:14px 18px; color:#CDEFF4; font-size:1rem;
  box-shadow:0 0 12px rgba(34,211,238,.12);
}

/* ============ 6. EXPANDERS ============ */
[data-testid="stExpander"] { border:1px solid #163247 !important; border-radius:10px; }
[data-testid="stExpander"] summary { color:#7FF7EC !important; font-weight:600; }

/* ============ 7. BOUTONS TÉLÉCHARGEMENT : contour (distincts du primaire) ============ */
[data-testid="stDownloadButton"] button {
  background:transparent !important; color:#7FF7EC !important;
  border:1px solid #22D3EE !important; box-shadow:none !important; font-weight:600;
}
[data-testid="stDownloadButton"] button:hover { box-shadow:0 0 12px rgba(34,211,238,.4) !important; }

/* ============ 8. BULLES DU CHAT RAG ============ */
[data-testid="stChatMessage"] {
  background:#0d1c2b; border:1px solid #163247; border-radius:12px;
}

/* ============ 9. SCROLLBAR CYAN ============ */
::-webkit-scrollbar { width:10px; height:10px; }
::-webkit-scrollbar-track { background:#0A1420; }
::-webkit-scrollbar-thumb { background:#1b3f5c; border-radius:6px; }
::-webkit-scrollbar-thumb:hover { background:#22D3EE; }

/* ============ 5. TITRES DE SECTION : barre d'accent + espace ============ */
.stTabs h2 {
  border-left:4px solid #22D3EE; padding-left:14px; margin-top:.3rem;
}
.stTabs h3 { margin-top:.6rem; }

/* ============ 10. KPIs (badges sous la bannière) ============ */
.cliner-kpis {
  display:flex; justify-content:center; gap:14px; flex-wrap:wrap; margin:14px 0 6px;
}
.cliner-kpis span {
  background:#0d2033; border:1px solid #1b3f5c; border-radius:10px;
  padding:8px 18px; text-align:center; min-width:120px;
  color:#9fd0da; font-size:.78rem; box-shadow:0 0 10px rgba(34,211,238,.10);
}
.cliner-kpis b { color:#7FF7EC; font-size:1.15rem; font-family:'Orbitron',sans-serif; }

/* ============ 11. FOOTER ============ */
.cliner-footer {
  text-align:center; color:#5f8ea0; font-size:.82rem; line-height:1.6;
  padding:22px 0 8px; margin-top:34px; border-top:1px solid #14364e;
}

/* ============ 12. SPINNER cyan ============ */
.stSpinner p, .stSpinner > div > div { color:#7FF7EC !important; }
</style>
""", unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Summary table : logique autonome (champs de Jérémie)
# Construite à partir du JSON déjà récupéré à la recherche -> AUCUNE 2e requête.
# --------------------------------------------------------------------------- #
def _safe_get(d, *keys):
    cur = d
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return None
    return cur


def study_summary_row(sj):
    ps = "protocolSection"
    inters = _safe_get(sj, ps, "armsInterventionsModule", "interventions") or []
    int_names = " | ".join(i.get("name") for i in inters if i.get("name")) or "N/A"
    int_types = " | ".join(i.get("type") for i in inters if i.get("type")) or "N/A"
    outcomes = _safe_get(sj, ps, "outcomesModule", "primaryOutcomes") or []
    outcome = " | ".join(o.get("measure") for o in outcomes if o.get("measure")) or "N/A"
    phases = _safe_get(sj, ps, "designModule", "phases")
    return {
        "NCT_ID": _safe_get(sj, ps, "identificationModule", "nctId"),
        "Official Title": _safe_get(sj, ps, "identificationModule", "officialTitle") or "N/A",
        "Study Type": _safe_get(sj, ps, "designModule", "studyType") or "N/A",
        "Phase": ", ".join(phases) if phases else "N/A",
        "Primary Purpose": _safe_get(sj, ps, "designModule", "designInfo", "primaryPurpose") or "N/A",
        "Enrollment Count": _safe_get(sj, ps, "designModule", "enrollmentInfo", "count") or "N/A",
        "Eligibility Criteria": "Présent" if _safe_get(sj, ps, "eligibilityModule", "eligibilityCriteria") else "Absent",
        "Intervention Type": int_types,
        "Intervention Name": int_names,
        "Primary Outcome Measure": outcome,
    }

# --------------------------------------------------------------------------- #
# Définition des champs (table de Jérémie)
# --------------------------------------------------------------------------- #
# Champs proposés dans les menus déroulants de recherche (onglet 1)
QUERY_FIELDS = ["Condition", "MinimumAge", "MaximumAge", "Sex", "HealthyVolunteers",
                "InterventionType", "Phase", "StudyType", "DesignPrimaryPurpose"]

# Valeurs fixes -> vrai menu déroulant (moins de 10 options)
ENUM_OPTIONS = {
    "Sex": ["ALL", "FEMALE", "MALE"],
    "HealthyVolunteers": ["Yes", "No"],
    "InterventionType": ["DRUG", "DEVICE", "BIOLOGICAL", "PROCEDURE", "RADIATION",
                          "BEHAVIORAL", "GENETIC", "DIETARY_SUPPLEMENT",
                          "COMBINATION_PRODUCT", "DIAGNOSTIC_TEST", "OTHER"],
    "Phase": ["EARLY_PHASE1", "PHASE1", "PHASE2", "PHASE3", "PHASE4", "NA"],
    "StudyType": ["INTERVENTIONAL", "OBSERVATIONAL", "EXPANDED_ACCESS"],
    "DesignPrimaryPurpose": ["TREATMENT", "PREVENTION", "DIAGNOSTIC", "SUPPORTIVE_CARE",
                             "SCREENING", "HEALTH_SERVICES_RESEARCH", "BASIC_SCIENCE",
                             "DEVICE_FEASIBILITY", "OTHER"],
}
# Champs du filtre "post-JSON" (onglet 3, appliqué sur les résultats)
FILTER_FIELDS = ["EligibilityCriteria", "PrimaryOutcomeMeasure",
                 "InterventionName", "Phase", "StudyType"]

# Libellés francisés à afficher (comme Christopher : "Maladie (Condition)").
# Les autres champs gardent leur nom API en anglais.
FIELD_LABELS = {"Condition": "Maladie (Condition)"}

# --------------------------------------------------------------------------- #
# État de session
# --------------------------------------------------------------------------- #
for k, v in {"search_done": False, "analysis_done": False,
             "found_studies": [], "force_pdf": False, "latest_query": "",
             "latest_results": [], "extracted_docs": [],
             "chat_history": [], "demo_cache": {}, "selected_ncts": []}.items():
    st.session_state.setdefault(k, v)

# --------------------------------------------------------------------------- #
# Persistance navigateur (localStorage) — option 1 validée par l'équipe.
# Survit au refresh (F5), rien n'est stocké côté serveur : tout reste dans le
# navigateur du médecin (Privacy by Design). Restaure table, sélection,
# résultats, graph et chat. Le stockage DURABLE (JSON, chunks, vecteurs) reste
# côté Supabase Postgres — ce sont deux couches distinctes.
# --------------------------------------------------------------------------- #
PERSIST_KEYS = ["search_done", "analysis_done", "found_studies", "force_pdf",
                "latest_query", "latest_results", "extracted_docs", "chat_history",
                "selected_ncts"]
_LS_KEY = "cliner_state_v1"
_ls = LocalStorage() if LocalStorage is not None else None

# Réhydratation : dès que le composant a chargé la valeur, on la réinjecte une
# seule fois (le flag _hydrated évite d'écraser les modifs faites en session).
if _ls is not None:
    _raw = _ls.getItem(_LS_KEY)
    if _raw and not st.session_state.get("_hydrated"):
        try:
            for _k, _v in json.loads(_raw).items():
                st.session_state[_k] = _v
        except Exception:
            pass
        st.session_state["_hydrated"] = True

# --------------------------------------------------------------------------- #
# En-tête + sidebar
# --------------------------------------------------------------------------- #
# Bannière CliNER — wordmark néon en CSS (net à toute taille, aucun fichier requis)
st.markdown(
    '<div class="cliner-hero">'
    '<div class="cliner-word"><span class="cli">Cli</span><span class="ner">NER</span></div>'
    '<div class="cliner-tag">AI-POWERED MEDICAL INTELLIGENCE</div>'
    '</div>',
    unsafe_allow_html=True)

# Barre de KPIs (badges statiques sous la bannière)
st.markdown(
    "<div class='cliner-kpis'>"
    "<span><b>58.3%</b><br>F1-Score (CHIA)</span>"
    "<span><b>63%</b><br>Précision</span>"
    "<span><b>75 tok/s</b><br>Inférence GPU</span>"
    "<span><b>Qwen 7B + LoRA</b><br>Modèle NER</span>"
    "</div>",
    unsafe_allow_html=True)

# Titre supprimé : redondant avec la bannière CliNER ci-dessus.

st.sidebar.title("🫀 CliNER")
st.sidebar.markdown("*AI-Powered Medical Intelligence & End-to-End Clinical Named Entity Recognition engine.*")
st.sidebar.markdown("**Projet Jedha - Bootcamp AIFS01**")
st.sidebar.markdown("---")
st.sidebar.subheader("👨‍💻 L'Équipe")
st.sidebar.markdown("Patrick Mouliom, Christopher Gilleron, Jérémie Becker, Arnaud Hoarau, Karim Atebata")
st.sidebar.markdown("---")
st.sidebar.header("Architecture & Stack")
st.sidebar.metric(label="Serveur Inférence", value="Lightning AI (L4 GPU)")
st.sidebar.metric(label="Moteurs (NER & RAG)", value="Qwen 2.5 7B + BioBERT")
st.sidebar.metric(label="Stockage Durable", value="Supabase (Postgres & S3)")
st.sidebar.metric(label="MLOps & Tracking", value="MLflow")
api_url = st.sidebar.text_input(
    "URL du FastAPI Orchestrateur (Lightning AI):",
    value=os.getenv("LIGHTNING_AI_API_URL", "https://protocole-clinique-api.loca.lt"),
    key="api_url_input")
if st.session_state.api_url_input:
    os.environ["LIGHTNING_AI_API_URL"] = st.session_state.api_url_input


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _lock_card(msg):
    """Carte de verrouillage stylée (cyan) au lieu du bandeau st.info bleu."""
    st.markdown(f"<div class='cliner-lock'>🔒 {msg}</div>", unsafe_allow_html=True)


def lock_need_search():
    """Onglet 2 : tant qu'aucune recherche n'a été lancée."""
    _lock_card("Lancez d'abord une recherche dans l'onglet « 🔎 Critères de sélection ».")


def lock_need_analysis():
    """Onglets 3 & 4 : tant que la Summary table n'a pas généré l'extraction GPU."""
    _lock_card("Cochez des études dans « 📑 Summary table » puis cliquez "
               "« 🚀 Analyser (GPU) » pour débloquer cet onglet.")


def build_api_query(values):
    """Construit l'URL de requête ClinicalTrials v2 à partir des critères choisis.
    - Condition -> query.cond (recherche textuelle)
    - champs à valeurs fixes -> filter.advanced (syntaxe Essie AREA[...])
    - Age -> géré en post-filtre (voir age_ok)
    Retourne (query_string, label_lisible)."""
    parts, adv, label = [], [], ""
    for f, val in values.items():
        if not val:
            continue
        if f == "Condition":
            parts.append(f"query.cond={requests.utils.quote(str(val))}")
            label = str(val)
        elif f in ENUM_OPTIONS:
            vals = val if isinstance(val, list) else [val]
            sub = []
            for v in vals:
                if f == "HealthyVolunteers":
                    v = "true" if v == "Yes" else "false"
                sub.append(f"AREA[{f}]{v}")
            if sub:
                adv.append("(" + " OR ".join(sub) + ")")
        # MinimumAge / MaximumAge : post-filtre, pas dans l'URL
    if adv:
        parts.append("filter.advanced=" + requests.utils.quote(" AND ".join(adv)))
    if not parts:
        parts.append("query.cond=cancer")   # défaut de secours
    return "&".join(parts), (label or "recherche")


def parse_age_years(age_str):
    """'18 Years' -> 18 ; None si non parsable."""
    if not age_str:
        return None
    m = re.search(r"(\d+)", str(age_str))
    return int(m.group(1)) if m else None


def age_ok(study, user_min, user_max):
    """Garde l'étude si sa tranche d'âge chevauche [user_min, user_max]."""
    if not user_min and not user_max:
        return True
    elig = study.get("protocolSection", {}).get("eligibilityModule", {})
    s_min = parse_age_years(elig.get("minimumAge")) or 0
    s_max = parse_age_years(elig.get("maximumAge")) or 120
    if user_min and s_max < user_min:
        return False
    if user_max and s_min > user_max:
        return False
    return True


def build_rag_text(study):
    """Transforme le JSON ClinicalTrials en document texte structuré contenant
    TOUTES les sections utiles au RAG/NER (pas seulement l'éligibilité).
    Retourne "" si le JSON n'a aucun contenu exploitable -> fallback PDF."""
    protocol = study.get("protocolSection", {})
    identification = protocol.get("identificationModule", {})
    description = protocol.get("descriptionModule", {})
    conditions = protocol.get("conditionsModule", {})
    design = protocol.get("designModule", {})
    arms = protocol.get("armsInterventionsModule", {})
    eligibility = protocol.get("eligibilityModule", {})
    outcomes = protocol.get("outcomesModule", {})

    sections = []

    def field(label, value):
        if value is None or value == "" or value == []:
            return ""
        if isinstance(value, list):
            value = ", ".join(str(item) for item in value)
        return f"{label}: {value}"

    def add_section(title, lines):
        clean = [str(l).strip() for l in lines if l is not None and str(l).strip()]
        if clean:
            sections.append(f"## {title}\n" + "\n".join(clean))

    add_section("Study identification", [
        field("NCT ID", identification.get("nctId")),
        field("Brief title", identification.get("briefTitle")),
        field("Official title", identification.get("officialTitle")),
    ])
    add_section("Study description", [
        field("Brief summary", description.get("briefSummary")),
        field("Detailed description", description.get("detailedDescription")),
    ])
    add_section("Conditions and keywords", [
        field("Conditions", conditions.get("conditions")),
        field("Keywords", conditions.get("keywords")),
    ])
    design_info = design.get("designInfo", {})
    add_section("Study design", [
        field("Study type", design.get("studyType")),
        field("Phases", design.get("phases")),
        field("Primary purpose", design_info.get("primaryPurpose")),
        field("Allocation", design_info.get("allocation")),
        field("Intervention model", design_info.get("interventionModel")),
        field("Observational model", design_info.get("observationalModel")),
    ])
    intervention_lines = []
    for idx, itv in enumerate(arms.get("interventions", []), start=1):
        intervention_lines.extend([
            field(f"Intervention {idx} type", itv.get("type")),
            field(f"Intervention {idx} name", itv.get("name")),
            field(f"Intervention {idx} description", itv.get("description")),
            field(f"Intervention {idx} arm labels", itv.get("armGroupLabels")),
        ])
    add_section("Interventions and treatments", intervention_lines)
    arm_lines = []
    for idx, arm in enumerate(arms.get("armGroups", []), start=1):
        arm_lines.extend([
            field(f"Arm {idx} label", arm.get("label")),
            field(f"Arm {idx} type", arm.get("type")),
            field(f"Arm {idx} description", arm.get("description")),
            field(f"Arm {idx} intervention names", arm.get("interventionNames")),
        ])
    add_section("Study arms", arm_lines)
    add_section("Eligibility", [
        field("Sex", eligibility.get("sex")),
        field("Minimum age", eligibility.get("minimumAge")),
        field("Maximum age", eligibility.get("maximumAge")),
        field("Healthy volunteers", eligibility.get("healthyVolunteers")),
        field("Eligibility criteria", eligibility.get("eligibilityCriteria")),
    ])
    outcome_lines = []
    for otype, olist in [("Primary outcome", outcomes.get("primaryOutcomes", [])),
                         ("Secondary outcome", outcomes.get("secondaryOutcomes", []))]:
        for idx, o in enumerate(olist, start=1):
            outcome_lines.extend([
                field(f"{otype} {idx} measure", o.get("measure")),
                field(f"{otype} {idx} description", o.get("description")),
                field(f"{otype} {idx} time frame", o.get("timeFrame")),
            ])
    add_section("Study outcomes", outcome_lines)

    # Garde-fou : au moins un contenu exploitable au-delà de l'identification
    has_useful_content = bool(
        description.get("briefSummary")
        or description.get("detailedDescription")
        or conditions.get("conditions")
        or arms.get("interventions")
        or eligibility.get("eligibilityCriteria")
        or outcomes.get("primaryOutcomes")
        or outcomes.get("secondaryOutcomes")
    )
    if not has_useful_content:
        return ""
    return "\n\n".join(sections)


def build_task(study, force_pdf):
    """Construit la tâche envoyée au backend. En mode 'text', on envoie le
    document complet reconstruit depuis le JSON (build_rag_text). Le PDF sert
    de fallback si l'utilisateur le force ou si le JSON n'a aucun contenu utile."""
    nct_id = _safe_get(study, "protocolSection", "identificationModule", "nctId")
    docs = _safe_get(study, "documentSection", "largeDocumentModule", "largeDocs") or []
    has_pdf = any(str(d.get("filename", "")).lower().endswith(".pdf") for d in docs)

    if force_pdf and has_pdf:
        return {"type": "pdf", "nct_id": nct_id}

    rag_text = build_rag_text(study)
    if rag_text:
        return {"type": "text", "nct_id": nct_id, "text": rag_text}

    return {"type": "pdf", "nct_id": nct_id}


def run_gpu_extraction(tasks, label, api_url, output_dir):
    """Envoie les études sélectionnées au serveur GPU (vLLM). Retourne les résultats."""
    results = []
    for task in tasks:
        nct_id = task["nct_id"]
        if nct_id in st.session_state.demo_cache:
            results.append(st.session_state.demo_cache[nct_id])
            continue
        try:
            if task["type"] == "text":
                resp = requests.post(
                    f"{api_url}/process_text",
                    data={"disease": label, "document_id": nct_id,
                          "text_content": task["text"]},
                    headers={"Bypass-Tunnel-Reminder": "true"})
            else:
                pdf_path = (download_pdf_for_nctid(nct_id, output_dir)
                            if download_pdf_for_nctid else None)
                if pdf_path and os.path.exists(pdf_path):
                    with open(pdf_path, "rb") as fh:
                        resp = requests.post(
                            f"{api_url}/process_pdf",
                            files={"file": (f"{nct_id}.pdf", fh, "application/pdf")},
                            data={"disease": label},
                            headers={"Bypass-Tunnel-Reminder": "true"})
                else:
                    st.warning(f"Ni texte ni PDF pour {nct_id}")
                    continue
            if resp.status_code == 200:
                data = resp.json()
                raw = data.get("extraction", "")
                if isinstance(raw, str):
                    m = re.search(r'(\{.*\})', raw.strip(), re.DOTALL)
                    try:
                        data["extraction"] = json.loads(m.group(1)) if m else {"raw": raw}
                    except Exception:
                        data["extraction"] = {"parse_error": "JSON invalide", "raw": raw}
                results.append(data)
                st.session_state.demo_cache[nct_id] = data
                st.session_state.extracted_docs.append(data.get("document", nct_id))
            else:
                st.error(f"Erreur API ({resp.status_code}) pour {nct_id}")
        except Exception as e:
            st.error(f"Impossible de traiter {nct_id} : {e}")
    return results


def _study_metadata_by_nct():
    """Construit un dict NCT_ID -> métadonnées depuis found_studies (session)."""
    lookup = {}
    for s in st.session_state.get("found_studies", []):
        ps = s.get("protocolSection", {})
        nct = _safe_get(s, "protocolSection", "identificationModule", "nctId")
        if not nct:
            continue
        elig = ps.get("eligibilityModule", {})
        design = ps.get("designModule", {})
        design_info = design.get("designInfo", {})
        conds = _safe_get(s, "protocolSection", "conditionsModule", "conditions")
        phases = design.get("phases")
        inters = _safe_get(s, "protocolSection", "armsInterventionsModule", "interventions") or []
        int_types = " | ".join(i.get("type") for i in inters if i.get("type")) or "N/A"
        lookup[nct] = {
            "NCT_ID": nct,
            "Condition (API)": ", ".join(conds) if conds else "N/A",
            "MinimumAge": elig.get("minimumAge", "N/A"),
            "MaximumAge": elig.get("maximumAge", "N/A"),
            "Sex": elig.get("sex", "N/A"),
            "HealthyVolunteers": "Yes" if elig.get("healthyVolunteers") else "No",
            "InterventionType": int_types,
            "Phase": ", ".join(phases) if phases else "N/A",
            "StudyType": design.get("studyType", "N/A"),
            "DesignPrimaryPurpose": design_info.get("primaryPurpose", "N/A"),
        }
    return lookup


def results_to_df(results):
    """Fusionne les métadonnées ClinicalTrials (onglet 2) avec les extractions
    NER du GPU (onglet 3) pour un tableau de bord clinique complet."""
    meta = _study_metadata_by_nct()
    rows = []
    for res in results:
        ext = res.get("extraction", {})
        nct_id = res.get("document", "N/A")
        meds = ext.get("medications", []) if isinstance(ext, dict) else []
        meds = ", ".join(str(m.get("name", m.get("description", ""))) if isinstance(m, dict)
                         else str(m) for m in meds)
        crit = ext.get("inclusion_criteria", []) if isinstance(ext, dict) else []
        crit = ", ".join(str(c.get("description", c.get("category", ""))) if isinstance(c, dict)
                         else str(c) for c in crit)

        # Métadonnées officielles ClinicalTrials.gov
        m = meta.get(nct_id, {})
        rows.append({
            "NCT_ID": nct_id,
            "Condition (API)": m.get("Condition (API)", "N/A"),
            "Condition (NER)": ext.get("condition", "") if isinstance(ext, dict) else "",
            "Médicaments (Drug)": meds,
            "Critères d'éligibilité": crit,
            "MinimumAge": m.get("MinimumAge", "N/A"),
            "MaximumAge": m.get("MaximumAge", "N/A"),
            "Sex": m.get("Sex", "N/A"),
            "HealthyVolunteers": m.get("HealthyVolunteers", "N/A"),
            "InterventionType": m.get("InterventionType", "N/A"),
            "Phase": m.get("Phase", "N/A"),
            "StudyType": m.get("StudyType", "N/A"),
            "DesignPrimaryPurpose": m.get("DesignPrimaryPurpose", "N/A"),
        })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Onglets
# --------------------------------------------------------------------------- #
tab1, tab2, tab3, tab4 = st.tabs([
    "🔎 Critères de sélection",
    "📑 Summary table",
    "📊 Visualisation + filtre",
    "💬 Chatbot RAG",
])

# ============================ ONGLET 1 : RECHERCHE ========================= #
# Une seule requête ClinicalTrials. On stocke le JSON complet des études
# (found_studies) pour la Summary table -> pas de 2e requête. Aucune IA ici.
with tab1:
    st.header("1. Sélection des critères")

    # ⚡ Démo rapide : préremplit "Breast Cancer" et lance la recherche.
    # Placé AVANT les widgets pour pouvoir écrire dans st.session_state["val_Condition"].
    dcol, _ = st.columns([1, 2])
    if dcol.button("⚡ Démo rapide — Breast Cancer"):
        st.session_state["val_Condition"] = "Breast Cancer"
        st.session_state["_run_search"] = True
        st.rerun()

    st.markdown("Choisis **un ou plusieurs** critères, puis renseigne leurs valeurs.")

    label_to_field = {FIELD_LABELS.get(f, f): f for f in QUERY_FIELDS}
    sel_labels = st.multiselect(
        "Critères de recherche :", list(label_to_field.keys()),
        default=["Maladie (Condition)"],
        help="Ajoute un ou plusieurs filtres (maladie, phase, âge, sexe…). "
             "La maladie est le plus courant pour démarrer.")
    selected = [label_to_field[l] for l in sel_labels]

    values = {}
    cols = st.columns(2)
    for i, f in enumerate(selected):
        disp = FIELD_LABELS.get(f, f)
        with cols[i % 2]:
            if f in ENUM_OPTIONS:
                values[f] = st.multiselect(disp, ENUM_OPTIONS[f], key=f"val_{f}")
            elif f in ("MinimumAge", "MaximumAge"):
                values[f] = st.number_input(disp + " (années)", min_value=0, max_value=120,
                                            value=0, key=f"val_{f}")
            else:  # Condition (texte libre)
                values[f] = st.text_input(disp + " (ex: Breast Cancer)", key=f"val_{f}")
                if f == "Condition":
                    st.caption("📋 **Exemples (à copier-coller) :** Breast Cancer, Type 2 Diabetes, Alzheimer's Disease, Rheumatoid Arthritis, Major Depressive Disorder, Multiple Sclerosis, Asthma")

    c1, c2 = st.columns(2)
    max_results = c1.slider("Nombre d'essais à récupérer :", 1, 20, 5,
                            help="Nombre maximum d'essais renvoyés par ClinicalTrials.")
    force_pdf = c2.checkbox("📥 Forcer le scraping PDF (Plan B)",
                            help="Force le téléchargement du PDF complet au lieu du texte de l'API.")

    if st.button("🚀 Lancer la recherche", type="primary") or st.session_state.pop("_run_search", False):
        api_query, label = build_api_query(values)
        user_min = values.get("MinimumAge") or 0
        user_max = values.get("MaximumAge") or 0

        with st.spinner("Interrogation de l'API ClinicalTrials..."):
            t0 = time.time()
            kept = []
            url_ct = (f"https://clinicaltrials.gov/api/v2/studies?{api_query}"
                      f"&pageSize=50&fields=NCTId,ProtocolSection,DocumentSection")
            try:
                studies = requests.get(url_ct, timeout=15).json().get("studies", [])
                for study in studies:
                    if not age_ok(study, user_min, user_max):
                        continue
                    kept.append(study)
                    if len(kept) >= max_results:
                        break
            except Exception as e:
                st.error(f"Erreur API ClinicalTrials : {e}")
            elapsed = time.time() - t0

        if not kept:
            st.warning("Aucun essai trouvé pour ces critères.")
        else:
            # Nouvelle recherche -> on réinitialise l'analyse GPU précédente.
            st.session_state.found_studies = kept
            st.session_state.force_pdf = force_pdf
            st.session_state.latest_query = label
            st.session_state.search_done = True
            st.session_state.analysis_done = False
            st.session_state.latest_results = []
            st.session_state.extracted_docs = []
            st.session_state.selected_ncts = []
            st.session_state.chat_history = []  # 🧹 Purge automatique du Chat sur nouvelle recherche
            st.success(f"✅ {len(kept)} essai(s) récupéré(s) en {elapsed:.1f}s. "
                       "Va dans l'onglet « 📑 Summary table ».")


# ============================ ONGLET 2 : SUMMARY TABLE ===================== #
# 100% ClinicalTrials, aucun GPU. C'est ici qu'on coche les études à analyser,
# puis qu'on déclenche l'extraction GPU (qui débloque les onglets 3 & 4).
with tab2:
    st.header("2. Summary table (champs source ClinicalTrials)")
    if not st.session_state.search_done:
        lock_need_search()
    else:
        rows = [study_summary_row(s) for s in st.session_state.found_studies]
        df_sum = pd.DataFrame(rows)
        # Pré-coche les études déjà sélectionnées (restaurées au refresh)
        _prev = set(st.session_state.get("selected_ncts", []))
        df_sum.insert(0, "Analyser", df_sum["NCT_ID"].isin(_prev))
        # Colonne lien cliquable vers la fiche officielle ClinicalTrials.gov
        df_sum["🔗 Fiche"] = "https://clinicaltrials.gov/study/" + df_sum["NCT_ID"].astype(str)

        st.caption("Coche les études à envoyer au modèle, puis clique « Analyser (GPU) ».")
        edited = st.data_editor(
            df_sum, hide_index=True, use_container_width=True,
            column_config={
                "Analyser": st.column_config.CheckboxColumn(
                    "Analyser", help="Cocher pour envoyer cette étude au GPU"),
                "🔗 Fiche": st.column_config.LinkColumn(
                    "🔗 Fiche", help="Ouvrir la fiche officielle ClinicalTrials.gov",
                    display_text="Ouvrir ↗"),
            },
            disabled=[c for c in df_sum.columns if c != "Analyser"],
            key="summary_editor")

        selected_ncts = edited.loc[edited["Analyser"] == True, "NCT_ID"].tolist()
        st.session_state.selected_ncts = selected_ncts

        st.download_button("📥 Exporter la table (CSV)",
                           df_sum.drop(columns=["Analyser", "🔗 Fiche"]).to_csv(index=False, sep=';').encode('utf-8-sig'),
                           file_name="summary_table.csv", mime="text/csv")

        st.markdown("---")
        launch = st.button(f"🚀 Analyser {len(selected_ncts)} étude(s) cochée(s) (GPU)",
                           type="primary", disabled=not selected_ncts)
        st.markdown(
            "<div style='text-align:center; color:#9fd0da; font-size:.9rem; margin-top:6px;'>"
            "Nécessite le serveur GPU allumé. Débloque les onglets 3 &amp; 4.</div>",
            unsafe_allow_html=True)

        if launch:
            label = st.session_state.latest_query
            output_dir = os.path.abspath(f"data/live_pdfs_{label.replace(' ', '_')}")
            os.makedirs(output_dir, exist_ok=True)
            sel_studies = [s for s in st.session_state.found_studies
                           if _safe_get(s, "protocolSection", "identificationModule", "nctId") in selected_ncts]
            tasks = [build_task(s, st.session_state.force_pdf) for s in sel_studies]
            with st.spinner(f"Envoi de {len(tasks)} protocole(s) au GPU (vLLM)..."):
                t0 = time.time()
                results = run_gpu_extraction(tasks, label, api_url, output_dir)
                st.session_state.latest_results = results
                st.session_state.extracted_docs = list(set(st.session_state.extracted_docs))
                if results:
                    st.session_state.analysis_done = True
                    st.success(f"✅ Extraction terminée en {time.time() - t0:.1f}s — "
                               "onglets 3 & 4 débloqués.")
                else:
                    st.warning("Aucun résultat renvoyé par le GPU (serveur éteint ?).")

        if st.session_state.analysis_done and st.session_state.latest_results:
            with st.expander("🔎 Aperçu des extractions générées"):
                for res in st.session_state.latest_results:
                    st.markdown(f"**{res.get('document', 'N/A')}** — {res.get('disease', 'N/A')}")
                    st.json(res.get("extraction", {}))


# ============================ ONGLET 3 : VISUALISATION ===================== #
with tab3:
    st.header("3. Visualisation & filtre des résultats")
    if not st.session_state.analysis_done:
        lock_need_analysis()
    else:
        df = results_to_df(st.session_state.latest_results)

        # --- Filtre post-JSON (champs de Jérémie) ---
        with st.expander("🔎 Filtrer les résultats (filtre post-JSON)", expanded=True):
            st.caption("Champs de filtre : " + ", ".join(FILTER_FIELDS))
            txt = st.text_input("Filtre texte (cherche dans Condition / Médicaments / Critères) :")
        if txt:
            mask = df.apply(lambda row: txt.lower() in " ".join(row.astype(str)).lower(), axis=1)
            df = df[mask]

        st.subheader("📊 Tableau de bord clinique")
        st.dataframe(df, use_container_width=True)
        st.download_button("📥 Exporter les extractions (CSV)",
                           df.to_csv(index=False, sep=';').encode('utf-8-sig'),
                           file_name="extractions.csv", mime="text/csv")

        # --- Petit graphique : nb d'entités par type ---
        counts = {"Condition": 0, "Médicaments": 0, "Critères": 0}
        for _, row in df.iterrows():
            counts["Condition"] += 1 if row["Condition (NER)"] else 0
            counts["Médicaments"] += len([m for m in str(row["Médicaments (Drug)"]).split(",") if m.strip()])
            counts["Critères"] += len([c for c in str(row["Critères d'éligibilité"]).split(",") if c.strip()])
        st.subheader("Répartition des entités extraites")
        st.bar_chart(pd.DataFrame({"Nombre": counts}), color="#22D3EE")

        st.markdown("---")
        st.info("💬 **Envie d'aller plus loin ?** L'extraction NER a généré les vecteurs BioBERT dans la base de données ! Vous pouvez maintenant accéder à l'onglet **« 💬 Chatbot RAG »** pour poser vos questions complexes sur ces essais en langage naturel.")


# ============================ ONGLET 4 : RAG =============================== #
with tab4:
    st.header("4. Assistant Chatbot RAG")
    
    c_clear, c_space = st.columns([1, 4])
    if c_clear.button("🗑️ Vider le Chat"):
        st.session_state.chat_history = []
        st.rerun()
        
    if not st.session_state.analysis_done:
        lock_need_analysis()
    else:
        doc_filter = st.selectbox("Filtrer par essai (Optionnel) :",
                                  ["Toute la base"] + st.session_state.extracted_docs)

        # Questions suggérées : libellé FR affiché, mais requête EN envoyée au
        # retrieval (BioBERT est anglophone -> meilleurs extraits). Clic = envoi.
        suggestions = [
            ("💊 Quels médicaments / traitements sont utilisés ?",
             "What drugs, medications, or specific therapies are used in those studies?"),
            ("🧪 Y a-t-il des essais contrôlés par placebo ?",
             "Are there any placebo-controlled trials mentioned in the context? If yes, describe them."),
            ("🎂 Âge minimum et maximum pour participer ?",
             "What is the minimum and maximum age required to participate in these studies?"),
            ("🤰 Femmes enceintes / allaitantes admises ? Pourquoi ?",
             "Are pregnant or breastfeeding women allowed to participate? Explain why."),
            ("🚫 Conditions médicales qui excluent un patient ?",
             "List all the medical conditions that would exclude a patient from participating."),
            ("🎯 Critères de jugement principaux (outcomes) ?",
             "What are the main endpoints or primary outcomes being measured in these studies?"),
            ("📄 Combien de documents utilisés ? Liste leurs ID.",
             "How many distinct clinical trials or documents did you use to answer? List their ID or name."),
            ("📝 Résume l'objectif des essais en un paragraphe.",
             "Can you summarize the main goal of the trials in one short paragraph?"),
        ]
        st.caption("💡 Questions suggérées (cliquables) :")
        clicked = None
        scols = st.columns(2)
        for i, (label_fr, query_en) in enumerate(suggestions):
            if scols[i % 2].button(label_fr, key=f"sugg_{i}", use_container_width=True):
                clicked = (label_fr, query_en)

        # Historique
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        typed = st.chat_input("Posez votre question clinique...")
        if clicked:
            display_q, query_q = clicked          # FR affiché / EN envoyé à l'API
        elif typed:
            display_q = query_q = typed
        else:
            display_q = query_q = None

        if query_q:
            st.session_state.chat_history.append({"role": "user", "content": display_q})
            with st.chat_message("user"):
                st.markdown(display_q)
            with st.chat_message("assistant"):
                ph = st.empty()
                ph.markdown("🧠 Recherche vectorielle + génération...")
                try:
                    sel = None if doc_filter == "Toute la base" else doc_filter
                    # En mode "Toute la base", on passe la liste des NCT de la session
                    # pour éviter la contamination cross-session (fix bug RAG scope)
                    session_doc_ids = ",".join(st.session_state.extracted_docs) if not sel else None
                    r = requests.post(f"{api_url}/chat_rag",
                                      data={"question": query_q, "doc_id": sel,
                                            "doc_ids": session_doc_ids},
                                      headers={"Bypass-Tunnel-Reminder": "true"})
                    if r.status_code == 200:
                        ans = r.json().get("answer", "Erreur de génération.")
                        ph.markdown(ans)
                        st.session_state.chat_history.append({"role": "assistant", "content": ans})
                    else:
                        ph.error(f"Erreur API ({r.status_code})")
                except Exception as e:
                    ph.error(f"Impossible de joindre l'API : {e}")


# --------------------------------------------------------------------------- #
# Footer
# --------------------------------------------------------------------------- #
st.markdown(
    "<div class='cliner-footer'>"
    "<b>CliNER</b> · AI-Powered Medical Intelligence — Projet Jedha Bootcamp AIFS01<br>"
    "Patrick Mouliom · Christopher Gilleron · Jérémie Becker · Arnaud Hoarau · Karim Atebata"
    "</div>",
    unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Sauvegarde dans le localStorage — uniquement si l'état a changé (évite les
# boucles de rerun). Appelé en fin d'exécution, après le rendu des onglets.
# --------------------------------------------------------------------------- #
if _ls is not None:
    try:
        _payload = json.dumps({k: st.session_state.get(k) for k in PERSIST_KEYS}, default=str)
        if _payload != st.session_state.get("_last_saved"):
            _ls.setItem(_LS_KEY, _payload, key="_ls_save")
            st.session_state["_last_saved"] = _payload
    except Exception:
        pass
