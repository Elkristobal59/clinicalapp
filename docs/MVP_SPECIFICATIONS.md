# Spécifications du Projet — Réunion du 17 Juillet 2026
*Document aligné avec le transcript intégral de la réunion d'équipe et le cahier des charges partagé sur le Drive.*

---

## 1. BACKBONE (Le MVP Officiel)

### 1.1 Objectif
Fournir une **Extraction d'entités standardisées (NER)** de protocoles cliniques, permettant à un clinicien de filtrer les études selon des critères spécifiques.

> **Point clé (Patrick)** : Le MVP doit démontrer que le moteur est **généralisable**. On commence par un sous-domaine de la cardiologie, mais l'architecture doit pouvoir se répliquer à tout domaine médical.

### 1.2 Sources de données
| Source | Rôle | Statut |
|---|---|---|
| **ClinicalTrials.gov** | Source de production (API + téléchargement). 99% en anglais. | ✅ Validé |
| **Chia** | Corpus de référence (taxonomies médicales, JSON pré-formaté). Utilisé pour le benchmark BioBERT vs Qwen. | ✅ Conservé pour les tests |
| **Quaero (EMEA)** | Écarté. Contenu en français, plus proche de notices de médicaments que de protocoles cliniques. | ❌ Abandonné |

### 1.3 Flux de données (I/O)
* **Entrées :** Les protocoles bruts, structurés via un **fichier de configuration JSON (ontologie)** qui définit les critères cliniques à extraire. Ce fichier est donné "à manger" au LLM.
* **Sorties :** Un JSON structuré contenant les entités extraites (médicaments, âge, comorbidités, doses, etc.) et leurs relations.

### 1.4 Modèle IA (Moteur NER) — Benchmark prévu
L'équipe va comparer **deux approches** pour choisir le meilleur rapport performance/coût :
* **Modèle spécialisé (Deep)** : `BioBERT` — Très pointu sur le domaine biomédical, mais lourd en inférence et uniquement en anglais.
* **Modèle généraliste léger (Broad)** : `Qwen` ou équivalent — Moins de paramètres, coût d'inférence réduit. Jérémie et Claude (IA) recommandent cette approche pour un POC.

> **Citation Jérémie** : *"Si les deux réponses sont à peu près équivalentes, on se dira bah Qwen fait aussi bien le boulot et puis ça nous coûtera moins cher en inférence."*

### 1.5 Workflow de l'application
1. **Phase 1 (MVP)** : Charger manuellement **10 protocoles de cardiologie** sélectionnés à la main.
2. **Phase 2** : Intégrer une **API vers ClinicalTrials.gov** pour permettre au médecin de requêter dynamiquement par pathologie.
3. L'orchestrateur (**LangChain**) injecte les protocoles + le JSON d'ontologie dans le LLM.
4. Le LLM extrait les entités et génère un **tableau structuré** (protocoles en lignes, variables en colonnes).
5. Le médecin applique des **filtres a posteriori** de type Excel sur ce tableau (ex : "uniquement patients > 65 ans, obèses, avec diabète").

> **Point clé (Jérémie)** : Le filtrage se fait **a posteriori** sur les données extraites par l'IA, et non via les filtres natifs de ClinicalTrials.gov qui sont jugés insuffisants.

---

## 2. NICE TO HAVE / EXTENSIONS (Post-MVP)

* **RAG (Recherche Augmentée) :** Permettre au médecin de poser des questions ouvertes (chatbot) sur des informations non couvertes par l'extraction initiale. **Attention : le RAG ne s'applique QUE sur les protocoles préalablement filtrés par l'utilisateur** (pas sur toute la base), afin d'éviter les problèmes de latence et d'hallucination.
* **Benchmark des LLM :** Comparer les performances entre différents LLM concurrents (BioBERT vs Qwen vs LLM Prompting classique) sur les mêmes données.
* **Multi-Domaines :** Tester le moteur sur des protocoles hors cardiologie pour prouver la généralisabilité.
* **Fine-Tuning :** Entraîner un modèle sur-mesure à partir de données annotées (protocole → tableau des infos extraites). Patrick précise que c'est une **boucle d'amélioration continue** basée sur les feedbacks utilisateurs.
* **Gestion des Hallucinations :** *LLM as a judge* (modèle adversarial), *System Prompt* robuste, réglage de la *température*.

---

## 3. STACK TECHNIQUE VALIDÉE
| Brique | Technologie |
|---|---|
| Langage | Python |
| Orchestration LLM | LangChain |
| Interface | Streamlit |
| Conteneurisation | Docker |
| Tracking ML | MLflow |
| Stockage brut | Amazon S3 (équipe) / Supabase Storage (POC Chris) |
| Base vectorielle | pgvector (via NeonDB ou Supabase) |
| Infra as Code | Terraform |

---

## 4. RÉPARTITION DES RÔLES (Validée en réunion)

| Qui | Quoi | Quand |
|---|---|---|
| **Chris** | Tester la stack complète en sandbox : LLM prompt via LangChain, Streamlit, Supabase, Lightning AI | Week-end (17-20 juil.) |
| **Jérémie** | Fichier d'ontologie JSON, requêtes API ClinicalTrials.gov, récupérer le corpus Chia | Semaine prochaine |
| **Jérémie + Arnaud** | Benchmark BioBERT vs modèle léger (Qwen) | Lundi matin |
| **Jérémie + Arnaud** | Développer la brique RAG | Lundi après-midi |
| **Jérémie** | Créer un diagramme du flux d'entrée / filtrage / intégration des fonctionnalités | Semaine prochaine |
| **Le groupe** | Dockeriser les briques applicatives | À planifier |
| **Le groupe** | Réserver 1h avec Maleka pour présenter les avancées | Lundi |
