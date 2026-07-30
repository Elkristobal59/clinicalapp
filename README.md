# Clinical Protocols Standardization (AI-Powered) 🔬

Ce projet est une application complète (Data Engineering & Data Science) permettant l'ingestion, le traitement, l'indexation vectorielle, et l'extraction sémantique d'entités depuis des protocoles cliniques (fichiers PDF).

## 🏗️ Architecture du Projet (Pipeline Hybride Asynchrone)

L'application suit une architecture hautement optimisée (FinOps) séparant drastiquement la recherche rapide (CPU) de l'extraction lourde (GPU) :

- **Branche A (Recherche Instantanée & Gratuite)** : L'application interroge l'API officielle ClinicalTrials V2 via des requêtes ciblées. Les résultats (Titre, Phase, Maladie) sont immédiatement affichés dans un tableau Streamlit. **Cette étape ne consomme aucune ressource IA.**
- **Branche B (Extraction & RAG Hybride via GPU)** : Uniquement lorsque l'utilisateur sélectionne une étude spécifique ou pose une question, le pipeline IA est déclenché sur un serveur distant (Lightning AI).
  - **Le Retriever (BioBERT)** : Fragmente le texte de l'essai et isole uniquement les paragraphes pertinents par similarité vectorielle.
  - **Le Generator NER (Qwen-7B + LoRA via vLLM)** : Notre LLM "In-House" (optimisé via QLoRA sur le dataset CHIA) lit le paragraphe ciblé et extrait un fichier JSON structuré des entités médicales à la vitesse de l'éclair.
  - **Le Chatbot RAG (Qwen-7B Instruct)** : Un agent conversationnel capable de répondre à des questions libres en s'appuyant sur les paragraphes vectorisés de la base, sans l'adaptateur LoRA pour garantir une réponse fluide.
  - *(Voir le détail des interactions dans [architecture_data_flow.md](docs/architecture_data_flow.md))*
- **Stockage Cloud (Supabase Storage & DB)** : Les PDF bruts sont sauvegardés dans un bucket public sur Supabase (`clinical_pdfs`). Les vecteurs mathématiques sont indexés via l'extension `pgvector`.
- **⚡ Cache Intelligent (Supabase)** : Si un essai clinique a déjà été extrait par le passé, son résultat est stocké en base (`clinical_ner_cache`). L'application l'affiche instantanément (0.1s), esquivant ainsi tout traitement GPU coûteux.
- **Monitoring** : `MLflow` pour le suivi des performances en temps réel (latence, prompts, JSON de sortie, Cache Hits).

## 📂 Rôle des Scripts de Machine Learning & Données (`scripts/`)

Pour garantir une rigueur scientifique totale (pas de *Data Leakage*), l'équipe a développé une suite de scripts stricts pour gérer la donnée CHIA :

1.  **`extract_full_chia.py` (La Collecte)** : Se connecte aux sources (Drive/HuggingFace), rassemble les PDF et les annotations BRAT, et génère la base de données brute consolidée (`chia_gold_standard_v2.json`).
2.  **`split_dataset.py` (La Répartition)** : Sépare intelligemment la base brute. Il met de côté 5 études secrètes (Le *Holdout Set* dans un coffre-fort pour le jour J), puis coupe le reste en deux fichiers : `train_dataset.jsonl` (le cahier d'exercices) et `test_dataset.jsonl` (l'examen blanc).
3.  **`finetune_qwen.py` (L'Entraînement)** : Le script de MLOps ! Il prend le modèle Qwen-0.5B brut, le fait réviser sur le `train_dataset.jsonl` via la méthode optimisée **QLoRA** (4-bit), et sauvegarde son "cerveau médical" dans le dossier `models/`.
4.  **`inference_qwen.py` (L'Évaluation)** : Le script d'examen. Il charge le modèle fine-tuné et le fait travailler à l'aveugle sur le `test_dataset.jsonl`. Il calcule ensuite mathématiquement le Score F1, la Précision et le Rappel pour le Benchmark officiel de la soutenance.

## 🚀 Démarrage Rapide

**1. Cloner le projet**
```bash
git clone https://github.com/Elkristobal59/clinicalapp.git
cd clinicalapp
```

**2. Lancer la Sainte Trinité des Terminaux (Lightning AI)**
Lors du démarrage de votre instance Lightning AI, vous devez lancer l'infrastructure backend (API + GPU) et l'outil de monitoring (MLflow).
Ouvrez 4 terminaux différents et lancez ces 4 commandes. **Il vous suffit de copier-coller, aucune URL n'est à modifier !**

**Avant de lancer Uvicorn, configurez la connexion Supabase :**

```bash
echo 'SUPABASE_DATABASE_URL="postgresql://postgres.<PROJECT_REF>:<PASSWORD_URL_ENCODED>@<SUPABASE_POOLER_HOST>:6543/postgres"' > .env
```

Remplacez `<PROJECT_REF>`, `<PASSWORD_URL_ENCODED>` et `<SUPABASE_POOLER_HOST>` par les paramètres fournis dans Supabase.


**Terminal 1 : Le Cerveau (API & Modèles GPU)**
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

**Terminal 2 : Le Pont API (Pour communiquer avec Streamlit)**
```bash
npx localtunnel --port 8000 --subdomain protocole-clinique-api
```

**Terminal 3 : L'Observatoire (Dashboard MLflow)**
```bash
mlflow ui --host 0.0.0.0 --port 5000 --disable-security-middleware
```

**Terminal 4 : Le Pont MLflow (Pour voir le Dashboard)**
```bash
npx localtunnel --port 5000 --subdomain mlflow-clinique-chris
```

✅ **C'est prêt !** 
- L'URL de l'API est fixée sur : `https://protocole-clinique-api.loca.lt` (à insérer dans Streamlit).
- Vos logs d'extractions en direct sont sur : `https://mlflow-clinique-chris.loca.lt` (cliquez sur "Click to Continue" pour y accéder).



## 📂 Déploiement de l'Interface Web (Render / Docker)

L'interface client (Streamlit) est dockerisée pour être déployée sur Render, Heroku, etc.
Le projet utilise un fichier `requirements-frontend.txt` allégé pour le conteneur Docker afin d'éviter l'installation des librairies GPU lourdes (torch, vllm, transformers) sur le frontend Streamlit. Tout le calcul GPU reste centralisé sur Lightning AI.

```bash
docker-compose up --build
```
L'application sera accessible sur le port `8501`.

> 🛠️ **Configuration & Variables d'Environnement sur Render** :
> Pour que Streamlit communique avec Lightning AI et Supabase, ajoutez impérativement ces variables dans votre dashboard Render :
> - `LIGHTNING_AI_API_URL` : L'URL de votre pont LocalTunnel (ex: `https://protocole-clinique-api.loca.lt`)
> - `SUPABASE_URL` et `SUPABASE_KEY` : Vos clés publiques d'API Supabase.
> 
> 🛠️ **Dépannage Render** :
> - **Redémarrages intempestifs (`Stopping...`)** : Fixez le port en ajoutant la variable d'environnement `PORT=8501`.
> - **Erreur `[Errno 24] inotify instance limit reached`** : Désactivez la surveillance locale en ajoutant `STREAMLIT_SERVER_FILE_WATCHER_TYPE=none`.

### Infrastructure as Code (Terraform)
Le dossier `terraform/` contient les scripts pour générer la structure de la base de données Supabase automatiquement (`main.tf`, `schema.sql`).
```bash
cd terraform
terraform init
terraform apply
```

## 🛠️ Améliorations Futures

### 1. Stratégie de Lutte contre le Drift (Dérive)
Pour garantir la pérennité de notre modèle en production, nous avons prévu une stratégie de lutte contre le **Drift** (Dérive des données et du concept) :
- **Data Drift** : Si les textes des protocoles cliniques (ClinicalTrials) changent de format ou de vocabulaire dans 2 ans, les performances du modèle vont baisser.
- **Concept Drift** : De nouvelles maladies ou de nouveaux types de traitements (ex: thérapies géniques, Covid) peuvent apparaître, rendant le modèle obsolète.
- **Notre Solution (Human-in-the-Loop)** : L'interface permet aux experts médicaux de signaler une erreur d'extraction. Ces corrections sont sauvegardées dans une base de données de "Feedback". Tous les 3 mois, un script MLOps utilisera ces nouvelles données corrigées pour déclencher un **Ré-entraînement Automatique (Fine-Tuning Continu)** du modèle Qwen, assurant ainsi sa résilience face au temps.

### 2. Améliorations Techniques
- **Traitement Multi-modal (CNN / ViT)** : Analyser directement les images, graphiques et scanners encapsulés dans les PDF grâce à des réseaux de neurones convolutifs (CNN) ou des Vision Transformers.
- **Scalabilité Cloud** : Architecture distribuée pour l'ingestion massive d'essais cliniques mondiaux.
- **Modèles SLM** : Fine-tuning d'un petit modèle (Small Language Model) spécialisé pour réduire considérablement les coûts d'inférence en production.
- **Auto-suppression Supabase (TTL / CRON)** : Routines de purge automatique pour effacer régulièrement les PDF temporaires stockés dans le Cloud, afin d'optimiser les coûts de stockage et de garantir la conformité RGPD.
