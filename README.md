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
mlflow ui --host 0.0.0.0 --port 5000 --disable-security-middleware
```

**Terminal 4 : Le Pont MLflow (Pour voir le Dashboard)**
```bash
npx localtunnel --port 5000 --subdomain mlflow-clinique-chris
```

✅ **C'est prêt !** 
- L'URL de l'API est fixée sur : `https://protocole-clinique-api.loca.lt` (à insérer dans Streamlit).
- L'URL de l'API est fixée sur : `https://protocole-clinique-api.loca.lt` (à insérer dans Streamlit).
- Vos logs d'extractions en direct sont sur : `https://mlflow-clinique-chris.loca.lt` (cliquez sur "Click to Continue" pour y accéder).

## 💡 FAQ & Pièges classiques (Spécial Soutenance / Démo)

Si un membre du jury vous pose une question piège ou si vous avez un doute pendant la démo, voici les réponses :

> **❓ "Pourquoi MLflow affiche une date *Last modified* d'hier alors que je viens de faire une extraction ?"**
> L'interface de MLflow (page *Experiments*) affiche la date de **création du dossier**, pas la date de la dernière donnée insérée. C'est comme un classeur physique : on ne change pas l'étiquette quand on glisse une nouvelle feuille dedans.
> 👉 **Solution** : Cliquez sur le nom bleu `Clinical_Trials_Extraction` pour entrer dans le dossier. Vos extractions d'aujourd'hui sont bien là !

> **❓ "Je ne vois pas mes données dans MLflow, j'ai une erreur *Failed to load chart data* ou *Request Error* ?"**
> 1. Assurez-vous d'avoir cliqué sur le bouton **"Model training"** en haut à gauche de MLflow (le mode "GenAI" par défaut cherche des données complexes que nous n'utilisons pas).
> 2. Pour voir vos données (`disease`, `document`), cliquez sur le petit bouton **`+` (Show more columns)** à droite du tableau et cochez-les.

> **❓ "Si l'onglet 1 n'utilise que BioBERT, pourquoi l'API charge-t-elle le LLM Qwen au démarrage ?"**
> L'API doit être prête à servir les deux onglets simultanément. Si BioBERT est parfait pour l'extraction (Onglet 1), il est en revanche **incapable de formuler des phrases**. Le modèle Qwen est donc chargé en VRAM car il est le seul à pouvoir lire les résultats de BioBERT et générer une réponse en bon français pour le **Chatbot RAG (Onglet 2)**.

> **❓ "J'ai l'erreur `[Errno 98] Address already in use` quand je lance MLflow ou l'API ?"**
> Cela signifie que vous avez fermé le terminal avec la croix au lieu de faire `Ctrl+C`, le processus tourne donc toujours de manière invisible.
> 👉 **Solution** : Tapez `pkill -f "mlflow"` ou `pkill -f "uvicorn"` pour tuer les processus fantômes, puis relancez.

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
