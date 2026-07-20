# Clinical Protocols Standardization (AI-Powered) 🔬

Ce projet est une application complète (Data Engineering & Data Science) permettant l'ingestion, le traitement, l'indexation vectorielle, et l'extraction sémantique d'entités depuis des protocoles cliniques (fichiers PDF).

## 🏗️ Architecture du Projet (Pipeline Hybride)

L'application suit une architecture hautement optimisée, séparant les tâches de compréhension et de génération :

- **Extraction d'Entités (Onglet 1 - Full BioBERT)** : La standardisation des données (NER) est désormais **100% basée sur BioBERT** (`biobert-chia-ner`). Contrairement à une extraction classique par LLM, ce modèle de classification de tokens extrait les entités (Condition, Drug, Measurement) quasi instantanément et sans hallucination. Le modèle Qwen a été *totalement retiré* de cette étape pour des raisons de performance.
- **Assistant Conversationnel RAG (Onglet 2 - BioBERT + Qwen)** : Le Chatbot RAG utilise une architecture hybride. **BioBERT** agit comme encodeur pour créer les vecteurs (embeddings) et trouver les informations dans la base. Le LLM léger **Qwen-1.5B** prend ensuite le relais *uniquement* pour générer la réponse en langage naturel à partir de ces extraits.
- **Base Vectorielle** : Supabase avec l'extension `pgvector` et un index HNSW.
- **Serveur d'Inférence** : API FastAPI hébergée sur **Lightning AI** (GPU).
- **Monitoring** : `MLflow` pour le suivi des performances (latence, prompts, JSON de sortie).

## 🚀 Utilisation de vLLM (Accélération GPU)

Pour l'onglet RAG, la génération de texte par le LLM (Qwen-1.5B) est propulsée par **vLLM**, un moteur d'inférence ultra-rapide.

- **Smart Fallback** : L'API détecte automatiquement votre matériel au lancement. Si un GPU est présent, vLLM est activé. Sinon, l'API bascule sur la librairie `transformers` native (plus lente mais fonctionnelle sur CPU).
- **Gestion de la VRAM** : vLLM est paramétré pour utiliser `70%` de la mémoire vidéo (`gpu_memory_utilization=0.7`). Cela garantit qu'il reste toujours `30%` de VRAM disponible pour faire tourner BioBERT en parallèle sans crash (OOM).
- **Bénéfice** : vLLM utilise la technique du *PagedAttention* pour gérer le cache KV de manière optimale, rendant les réponses du Chatbot fluides et instantanées.

## 🚀 Démarrage Rapide (Sainte Trinité des Terminaux)

Lors du démarrage de votre instance Lightning AI, vous devez lancer l'infrastructure backend (API + GPU) et l'outil de monitoring (MLflow).
Ouvrez 4 terminaux différents et lancez ces 4 commandes. **Il vous suffit de copier-coller, aucune URL n'est à modifier !**

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
mlflow ui --host 0.0.0.0 --port 5000 --allowed-hosts "*"
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
Le projet utilise un fichier `requirements-frontend.txt` allégé pour le conteneur Docker afin d'éviter l'installation des librairies GPU lourdes sur le frontend.

```bash
docker-compose up --build
```
L'application sera accessible sur le port `8501`.

> 🛠️ **Dépannage Render (Déploiement Cloud)** :
> - **Redémarrages intempestifs (`Stopping...`)** : Fixez le port en ajoutant la variable d'environnement `PORT=8501` sur Render.
> - **Erreur `[Errno 24] inotify instance limit reached`** : Désactivez la surveillance en ajoutant la variable `STREAMLIT_SERVER_FILE_WATCHER_TYPE=none`.

### Infrastructure as Code (Terraform)
Le dossier `terraform/` contient les scripts pour générer la structure de la base de données Supabase automatiquement (`main.tf`, `schema.sql`).
```bash
cd terraform
terraform init
terraform apply
```
