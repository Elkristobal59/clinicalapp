# 🎤 Fiche de Présentation - Soutenance : Standardisation de Protocoles Cliniques

*Cette fiche est structurée comme un "déroulé" (pitch) de gauche à droite. Tu peux la lire ou t'en inspirer directement pour présenter ton architecture au professeur.*

---

## 1. 🌟 Introduction & Contexte Métier
**"Bonjour à tous. Notre projet s'intitule *Clinical Protocols Standardization*."**
*   **Le Problème :** Aujourd'hui, les protocoles d'essais cliniques sont souvent des blocs de texte libre ou des documents PDF complexes. C'est illisible à grande échelle pour des analyses de données.
*   **La Solution :** Nous avons développé une pipeline complète d'Intelligence Artificielle (IA) capable de lire ces essais cliniques, d'extraire les concepts médicaux clés (maladies, critères d'inclusion, traitements) et de les convertir en jeux de données structurés (JSON / CSV).
*   **L'Équipe :** Patrick Mouliom, Christopher Gilleron, Jérémie Becker, Arnaud Hoarau.

---

## 2. 🏗️ La Stack Technique (Vue d'ensemble)
**"Pour répondre à ce besoin, nous avons séparé notre application en 3 gros piliers :"**

1.  **L'Interface Utilisateur (Le Frontend)**
    *   **Techno :** `Streamlit` (Python).
    *   **Hébergement :** `Render` (Cloud public lié à notre GitHub) ou en Local.
    *   **Rôle :** C'est le point d'entrée. L'utilisateur tape la maladie, visionne les extractions, peut télécharger des exports (Excel/CSV), et interagir avec un Chatbot RAG.

2.  **Le Moteur d'Intelligence (Le Backend GPU)**
    *   **Techno :** `FastAPI` (pour créer l'API) + `Uvicorn`.
    *   **Hébergement :** `Lightning.ai` (Serveur Cloud équipé d'un GPU surpuissant). On expose ce serveur à notre Frontend grâce à un pont sécurisé `LocalTunnel`.
    *   **Rôle :** Il réceptionne les données brutes, fait tourner les modèles d'IA lourds sur la carte graphique, et renvoie de la donnée structurée.

3.  **Le Stockage & L'Infrastructure (La Mémoire)**
    *   **Techno :** `Supabase` (Alternative Open-Source à Firebase, basée sur PostgreSQL et de l'Object Storage AWS).
    *   **Rôle :** Archiver les documents lourds (PDFs) et stocker les métadonnées. L'infrastructure de cette base a été conçue comme du code (Infrastructure as Code) grâce à `Terraform`.
    *   **Tracking :** Nous utilisons aussi `MLflow` pour tracer les performances et les temps de réponse de nos modèles.

---

## 3. ⚙️ Le Déroulé Exact du Flux de Données (Le "Pipeline")
**"Voici exactement ce qui se passe sous le capot quand on clique sur *Rechercher* :"**

### Étape 1 : L'Ingestion Hybride (Côté Streamlit)
Quand on tape "Lung Cancer", l'interface fait une requête à l'API du gouvernement américain (ClinicalTrials.gov) pour identifier les essais pertinents. C'est ici que notre architecture devient "intelligente" grâce à une **approche hybride en 2 plans** :
*   **Plan A (Fast-Track) :** Le script vérifie si le JSON officiel contient déjà un bloc texte détaillé pour les *Critères d'Éligibilité* (> 100 caractères). Si oui, on extrait directement ce texte sans rien télécharger d'autre. C'est ultra-rapide.
*   **Plan B (Fallback PDF) :** Si le texte natif est manquant ou trop court, le script déclenche le scraper `Playwright` (un navigateur fantôme). Il navigue sur la page officielle, télécharge le PDF original de l'essai, l'envoie **directement dans notre bucket Cloud Supabase** (dossier `clinical_pdfs`) pour le sauvegarder, puis l'envoie au serveur GPU.

### Étape 2 : L'Inférence IA sur GPU (Côté Lightning.ai)
Le backend (FastAPI) reçoit soit du texte pur, soit le fichier PDF. 
*(Si c'est un PDF, la librairie `PyMuPDF/fitz` le transforme en texte).*

C'est là que la magie de l'IA opère en deux temps (Le RAG) :
1.  **Embedding (BioBERT) :** Le texte brut passe dans le modèle `dmis-lab/biobert-v1.1`. C'est un modèle NLP spécialisé dans le biomédical. Il transforme le texte en vecteurs pour cibler précisément où se cachent les médicaments, pathologies et critères.
2.  **Génération LLM (Qwen) :** On envoie ce contexte ultra-ciblé à `Qwen-1.5-1.8B-Chat`. Ce modèle de langage tourne sur notre GPU accéléré par le moteur d'inférence très haute performance `vLLM`. Qwen a pour directive stricte (prompt) de recracher la donnée sous un format **JSON standardisé**.

### Étape 3 : Restitution au Médecin / Chercheur
Le JSON structuré redescend du GPU vers notre Frontend `Streamlit`. L'interface affiche :
*   Les critères découpés proprement (Âge, Médicaments prescrits, Historique médical).
*   Un lien cliquable vers la source officielle Web.
*   Un lien de téléchargement direct de l'archive PDF depuis notre Cloud Supabase (uniquement si le Plan B a été utilisé).

---

## 4. 📈 Conclusion et Bilan des Outils (DevOps)
**"Pour conclure, nous avons construit bien plus qu'un script Python :"**
*   Nous avons des **Dockerfiles** prêts pour une mise en production en conteneurs de n'importe quel micro-service.
*   Nous utilisons du **Terraform** pour scripter notre Cloud.
*   Le tout versionné sur **Git/GitHub** pour permettre à l'équipe de collaborer sans se marcher sur les pieds.

L'architecture est modulaire, robuste face aux cas limites (PDF vs JSON natif), et optimisée financièrement (délégation du calcul lourd sur un GPU à distance uniquement quand c'est nécessaire).
