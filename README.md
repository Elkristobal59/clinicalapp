# Clinical Protocols Standardization (AI-Powered) 🔬

Ce projet est une application complète (Data Engineering & Data Science) permettant l'ingestion, le traitement, l'indexation vectorielle, et l'extraction sémantique (LLM) de protocoles cliniques (fichiers PDF) depuis ClinicalTrials.gov.

## 🏗️ Architecture du Projet

L'application suit une architecture Client/Serveur découplée :
- **Scraping** : Playwright (local) pour la récupération automatisée des PDF de protocoles cliniques.
- **Base Vectorielle** : Supabase avec l'extension `pgvector` et un index HNSW pour la recherche de similarité ultra-rapide.
- **Inférence & RAG (Serveur)** : API FastAPI hébergée sur **Lightning AI** (GPU). Encode les données avec `BioBERT` et génère les réponses via le LLM `Qwen-1.5B`.
- **Monitoring** : `MLflow` pour tracer les performances, les requêtes (temps, modèle, prompt, json de sortie).
- **Interface Client** : `Streamlit` dockerisé pour interagir avec le serveur.

## 🚀 Fonctionnalités

1. **Onglet 1 : Ingestion & Extraction**
   - Entrez une maladie (ex: *Cardiology*, *Breast Cancer*).
   - L'application scrape automatiquement ClinicalTrials, télécharge les PDF, les envoie au serveur GPU, génère les embeddings et extrait les informations cibles (Condition, Médicaments, Critères d'inclusion) dans un format JSON structuré.
2. **Onglet 2 : Chatbot RAG (Retrieval-Augmented Generation)**
   - Posez des questions en langage naturel sur la base de connaissances constituée des protocoles cliniques.
   - Les réponses générées sont basées **uniquement** sur les extraits sémantiques trouvés (affichage des sources de décision).

## 🛠️ Stack Technique

- **Backend / Serveur** : FastAPI, PyTorch, Transformers, Uvicorn.
- **Modèles IA** : `dmis-lab/biobert-v1.1` (Embeddings), `Qwen/Qwen1.5-1.8B-Chat` (LLM).
- **Frontend / Client** : Streamlit, Playwright.
- **Data & Ops** : PostgreSQL (Supabase), MLflow, Docker, Terraform.

## 📂 Déploiement

### Déploiement du Client (Docker)
L'interface utilisateur est entièrement dockerisée et prête à être déployée (Render, Heroku, DigitalOcean...) :
```bash
docker-compose up --build
```
L'application sera accessible sur le port `8501`.

### Déploiement Serveur (Lightning AI)
1. Installez les dépendances (`requirements.txt`).
2. Démarrez l'API :
   ```bash
   uvicorn api.main:app --host 0.0.0.0 --port 8000
   ```
   > 💡 **Smart Fallback (vLLM)** : L'API détecte automatiquement votre matériel au lancement. 
   > - **Si un GPU est détecté** : Le serveur active le moteur haute-performance **vLLM** (paramétré pour prendre 70% de la VRAM, laissant 30% pour BioBERT), garantissant des vitesses de génération fulgurantes.
   > - **Si vous êtes sur CPU** : L'API bascule silencieusement sur la librairie `transformers` native pour permettre le développement et les tests locaux sans planter (en contournant les bugs liés à la librairie `accelerate`).

   > 🛠️ **Dépannage (Troubleshooting)** :
   > Si vous rencontrez une erreur `ValueError: numpy.dtype size changed` (généralement liée à **MLflow** ou **Pandas**), c'est un conflit de versions. Résolvez-le simplement en forçant la version 1.x de Numpy :
   > ```bash
   > pip install "numpy<2"
   > ```

3. Exposez le port (via localtunnel ou proxy) et renseignez l'URL dans la variable d'environnement `LIGHTNING_AI_API_URL` du client.

### Infrastructure as Code (Terraform)
Le dossier `terraform/` contient les scripts pour générer la structure de la base de données Supabase automatiquement (`main.tf`, `schema.sql`).
```bash
cd terraform
terraform init
terraform apply
```
