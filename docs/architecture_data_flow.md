# Parcours de la Donnée (Architecture Hybride ETL) - CliNER

Ce document explique pas à pas le circuit de la donnée illustré sur le schéma d'architecture de CliNER, en décomposant les étapes clés : **Extract**, **Load** et **Transform**.

---

## 1. EXTRACT (Extraction de la donnée brute)

**🎯 Objectif : Récupérer les données primaires (JSON & PDF) depuis la source clinique.**

*   **Flèche : `Query` (Tab 1 → ClinicalTrials.gov API)**
    *   **Outils :** Streamlit (Front-end)
    *   **Parcours :** L'utilisateur saisit ses critères de ciblage (maladie, âge, phase de l'essai, etc.) depuis l'interface. L'application construit dynamiquement une requête formatée pour interroger l'API publique (v2) de ClinicalTrials.gov.

*   **Flèche : `download json+pdf` (ClinicalTrials.gov API → Supabase & Tab 2)**
    *   **Outils :** ClinicalTrials API
    *   **Parcours :** L'API renvoie les résultats bruts. Le flux se sépare naturellement en deux : les textes (métadonnées JSON) sont utilisés immédiatement pour affichage, et les fichiers lourds (PDF) subissent l'étape de Load.

---

## 2. LOAD (Stockage et Archivage)

**🎯 Objectif : Stocker la donnée brute de manière durable et sécurisée avant traitement.**

*   **Flèche implicite (au sein du bloc vert) : Sauvegarde dans le `S3 Bucket`**
    *   **Outils :** Supabase (Storage S3)
    *   **Parcours :** Les documents PDF volumineux téléchargés ne sont jamais stockés sur le disque local du serveur API (par mesure de sécurité et de scalabilité). Ils sont immédiatement archivés dans un Bucket S3 hébergé par Supabase.

*   **Flèche : `show protocols` (Supabase → Tab 2)**
    *   **Outils :** Streamlit (Local Storage)
    *   **Parcours :** Les métadonnées texte (JSON) sont chargées dans le navigateur de l'utilisateur pour peupler le tableau récapitulatif (Summary Table) de l'onglet 2. L'état persiste dans le navigateur grâce au LocalStorage (sans engorger le serveur).

---

## 3. TRANSFORM (Traitement IA, Vectorisation et Extraction)

**🎯 Objectif : Nettoyer la donnée, la vectoriser, et en extraire la quintessence par LLM.**

*   **Flèche : `extraction txt + chunking` (Tab 2 → Lightning AI)**
    *   **Outils :** Serveur Lightning AI / LangChain / PyMuPDF
    *   **Parcours :** L'utilisateur valide une ou plusieurs études. Le texte brut est envoyé au serveur GPU. Il y subit un nettoyage puis un **Chunking** (découpage intelligent via LangChain en morceaux de 1000 caractères avec chevauchement) pour éviter de saturer la mémoire des modèles d'IA.

*   **Flèche : `save vectors` (Chunking & Vectorization → PostgreSQL)**
    *   **Outils :** BioBERT / Supabase (pgvector)
    *   **Parcours :** Chaque "chunk" de texte est avalé par le modèle **BioBERT** qui le transforme en une matrice mathématique de 768 dimensions (embedding). Ces vecteurs sont sauvegardés de manière pérenne dans la base PostgreSQL via l'extension **pgvector**.

*   **Flèche : `Eligibility paragraph` (Chunking & Vectorization → NER Qwen)**
    *   **Outils :** BioBERT
    *   **Parcours :** Parmi tous les morceaux de texte de l'essai, le système isole intelligemment LE paragraphe spécifique correspondant aux critères d'éligibilité (grâce à une recherche sémantique / calcul de similarité). C'est ce paragraphe concentré qui est envoyé à l'étape suivante.

*   **Flèche : `results (named entities)` (NER Qwen → Tab 3)**
    *   **Outils :** Qwen 2.5 7B (Fine-Tuned) / vLLM + LoRA
    *   **Parcours :** C'est le cœur du réacteur. Le modèle Qwen 7B est appelé. Grâce à **vLLM**, un adaptateur LoRA spécialisé en extraction d'entités nommées cliniques (NER) lui est greffé à la volée. Qwen lit le paragraphe d'éligibilité, extrait les pathologies, traitements et dosages, et recrache un JSON strict qui vient peupler le tableau de l'onglet 3.

---

## 4. RAG (Retrieval-Augmented Generation / Chatbot)

**🎯 Objectif : Permettre à l'utilisateur de dialoguer naturellement avec les données médicales.**

*   **Flèche : `query vectors` (PostgreSQL → RAG Chatbot)**
    *   **Outils :** BioBERT / Supabase (pgvector)
    *   **Parcours :** Lorsque l'utilisateur pose une question dans l'onglet 4 (ex: "Y a-t-il un risque cardiaque ?"), cette question est vectorisée par BioBERT. Le vecteur interroge Supabase qui renvoie quasi-instantanément les 5 à 15 paragraphes les plus pertinents (similarité cosinus).

*   **Flèche : `send prompt, retrieve response` (Tab 4 ↔ RAG Chatbot)**
    *   **Outils :** Qwen 2.5 7B Instruct (Base Model) / vLLM
    *   **Parcours :** La question de l'utilisateur ET les paragraphes de contexte récupérés sont injectés dans le prompt. Contrairement au NER, le modèle Qwen est utilisé ici dans sa version **Instruct de base** (sans l'adaptateur LoRA hyper-strict), ce qui lui permet de formuler une réponse nuancée, naturelle et fluide en français. La réponse est envoyée au Chatbot de l'onglet 4.
