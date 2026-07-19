# Résumé des Travaux & Résultats — Projet Essais Cliniques
**Dernière mise à jour : 17 Juillet 2026, 23h57**

---

## Phase 2 — Validation de l'Architecture Cloud GPU

### 🎯 Objectif
Passer d'un POC local basé sur un LLM commercial (Gemini) à une infrastructure Open Source déployable sur le Cloud, utilisant l'accélération matérielle (GPU) pour des modèles spécialisés.

### 🏗️ Architecture Déployée (Lightning AI)
1. **Base de données Vectorielle (Supabase) :** Configuration d'une table `pgvector` avec 768 dimensions et un index HNSW pour la recherche sémantique ultra-rapide.
2. **Ingestion et Vectorisation (BioBERT) :** Déploiement d'un script utilisant le modèle HuggingFace `dmis-lab/biobert-v1.1`. Ce modèle, pré-entraîné sur de la littérature biomédicale, a été utilisé pour découper et encoder nos PDF d'essais cliniques directement depuis le GPU.
3. **Extraction Sémantique Map-Reduce (Qwen) :** Déploiement du modèle LLM génératif `Qwen1.5-1.8B-Chat`. Le pipeline interroge Supabase pour récupérer les 5 meilleurs blocs de texte (Retrieval) puis demande à Qwen de consolider ces informations (Reduce) sous forme de JSON structuré.

### 🚀 Résultats Phase 2
- **Rapidité :** L'ingestion des embeddings par BioBERT s'est faite à très haute vitesse grâce à l'utilisation de `PyTorch` et `CUDA` sur GPU NVIDIA L4 (24Go VRAM).
- **Qualité de l'Extraction :** Le LLM Qwen a démontré une excellente capacité de compréhension du contexte médical.
- **Robustesse du Format :** JSON complet, bien formaté, réduction drastique des hallucinations grâce à la méthode Map-Reduce.

---

## Phase 3 — Automatisation Client-Serveur ✅ VALIDÉE

### 🎯 Objectif
Relier l'interface utilisateur (Streamlit) tournant en local avec l'architecture GPU distante via une API REST, pour permettre un traitement entièrement automatisé des PDF en temps réel.

### 🏗️ Architecture Mise en Place

```
🖥️ PC Local (Client)             🌐 Internet               ⚡ Lightning AI (Serveur GPU)
┌─────────────────────┐       ┌──────────────┐        ┌───────────────────────────────┐
│ Streamlit           │       │              │        │ FastAPI (Uvicorn)             │
│  ├─ Playwright      │──PDF─→│  localtunnel  │──PDF─→ │  ├─ PyMuPDF (Lecture PDF)     │
│  │  (Scraping Web)  │       │  (loca.lt)   │        │  ├─ BioBERT (Embedding 768d)  │
│  └─ Affichage JSON  │←JSON──│              │←JSON── │  ├─ Supabase (Recherche Vect.)│
└─────────────────────┘       └──────────────┘        │  └─ Qwen 1.5B (Extraction)   │
                                                       └───────────────────────────────┘
```

| Composant | Technologie | Rôle |
|-----------|-------------|------|
| **Scraping** | Playwright + ClinicalTrials.gov API | Téléchargement furtif des PDF de protocoles |
| **API Serveur** | FastAPI + Uvicorn | Reçoit les PDF, orchestre le pipeline IA |
| **Embedding** | BioBERT (`dmis-lab/biobert-v1.1`) | Encode chaque chunk en vecteur 768 dimensions |
| **Base Vectorielle** | Supabase (pgvector + HNSW) | Stocke et recherche les vecteurs par similarité cosinus |
| **Extraction LLM** | Qwen 1.5B Chat | Génère le JSON structuré à partir des passages pertinents |
| **Tunnel Réseau** | localtunnel (`loca.lt`) | Expose le port GPU publiquement sans authentification |
| **Interface** | Streamlit | Saisie utilisateur + affichage des résultats |

### 🚀 Résultats Phase 3 — Test de bout en bout réussi !

**Test effectué le 17/07/2026 à 23h57 :**
- Requête : `Cardiology`
- 2 PDF envoyés automatiquement au serveur GPU via le tunnel
- Temps total d'inférence : **115.9 secondes** (embedding + recherche + génération)

**Extractions obtenues :**

| Essai Clinique | Médicaments Extraits | Critères d'Inclusion |
|----------------|---------------------|----------------------|
| **NCT00935012** | Tafamidis (traitement TTR-CM), Placebo (comparateur) | Âge ≥ 18 ans, absence d'insuffisance cardiaque préalable, signes vitaux normaux |
| **NCT01045460** | Albumin (régulation du volume sanguin) | Documentation des médicaments concomitants, suivi des événements indésirables |

### 🐛 Bugs Rencontrés et Résolus

| Problème | Cause Racine | Correction |
|----------|-------------|------------|
| `WinError 10049` | `0.0.0.0` n'est pas routable depuis Windows | Utilisation de localtunnel (`loca.lt`) |
| `ConnectionResetError` | URL native Lightning AI exige auth navigateur | Bypass via localtunnel + header `Bypass-Tunnel-Reminder` |
| `ON CONFLICT` PostgreSQL | Contrainte `UNIQUE(chunk_id)` manquante | Ajoutée dans `init_supabase.py` et en base |
| `transaction aborted` | Connexion PG polluée après erreur | Ajout de `conn.rollback()` dans `api/main.py` |

---

## ⏭️ Perspectives d'Amélioration
- **Performance :** Paralléliser l'envoi des PDF pour traiter plus de documents simultanément
- **Modèle :** Tester un LLM plus puissant (Qwen 7B, Mistral 7B) pour des extractions plus précises
- **Sécurité :** Remplacer localtunnel par un déploiement permanent avec certificat SSL
- **Monitoring :** Ajouter MLflow pour tracer la qualité des extractions au fil du temps
