# 🎤 Débriefing des Avancées - Projet CliNER
**Période : Du Vendredi 9h00 au Lundi 9h00 (Sprint Weekend Démo Day)**  
**À destination de :** Aurélie (Professeure / Coordinatrice Jedha Bootcamp)  
**Équipe AIFS01 :** Patrick Mouliom, Christopher Gilleron, Jérémie Becker, Arnaud Hoarau, Karim Atebata  

---

## 🌟 Résumé Exécutif pour le Point de 9h00
Ce week-end a été consacré au **polish final, à l'industrialisation technique et à la préparation millimétrée de la soutenance (Demo Day)**. Nous avons fait converger l'ensemble des briques techniques (ETL, IA, Frontend, Infrastructure) vers un produit fini, stable, visuellement impressionnant et scientifiquement irréprochable.

---

## 1. 🎨 Refonte & Alignement Design (UI/UX & Présentation de Soutenance)
* **Présentation Interactive Reveal.js (`demoday_soutenance.html`) :**
  * Création d'un slide deck autonome et dynamique (transitions zoom/fade, thème sombre médical haut de gamme `#000b18`, encadrés en verre acrylique *Glassmorphism*).
  * **Centrage absolu en Flexbox (Slide 1) :** Élimination des défauts de chevauchement HTML. Le logo CliNER est désormais positionné en véritable **Hero Graphic central** (agrandi à 310px de haut, cadre lumineux, ombre portée néon), suivi d'une typographie raffinée pour le sous-titre et l'équipe.
  * **Autonomie totale de la démo :** Encodage de tous les visuels et logos en Base64 directement dans le HTML. La présentation ne dépend d'aucun CDN externe et fonctionnera à 100% hors-ligne ou sur n'importe quel poste lundi matin.
* **Mise à jour de l'Application Streamlit :**
  * Remplacement des anciens titres par la nouvelle identité **CliNER — AI-Powered Medical Intelligence**.
  * Intégration du nouveau visuel de l'application sur la slide de démo ("DÉMO EN DIRECT / Découvrez CliNER") et alignement des couleurs.
  * Implémentation d'un **Cache Frontend (en mémoire vive)** : les requêtes identiques s'affichent instantanément (< 0.01s) sans resolliciter le GPU.

---

## 2. 🏗️ Pipeline ETL Hybride & Haute Disponibilité (La Double Branche)
* **Ingestion Hybride (Plan A & Plan B) :**
  * **Branche A (Fast-Track Gratuite) :** Interrogation directe de l'API officielle *ClinicalTrials.gov*. Extraction instantanée des critères d'éligibilité natifs sans surcoût IA.
  * **Branche B (Fallback PDF intelligent) :** Si le texte natif est absent du JSON officiel, l'orchestrateur bascule automatiquement sur le téléchargement du PDF officiel depuis le CDN américain vers notre stockage Cloud **Supabase**, puis extrait le texte via `PyMuPDF`.
* **Résilience de l'ETL (Zone de Rejet / Dead Letter Queue) :**
  * Implémentation d'un filet de sécurité anti-crash : si un PDF officiel est corrompu ou illisible, il est automatiquement envoyé dans une **Zone de Rejet** avec log d'erreur. Le pipeline n'est jamais interrompu et passe immédiatement au protocole suivant.

---

## 3. 🧠 Moteur IA : RAG BioBERT x Fine-Tuning Qwen (Zéro Data Leakage)
* **Fine-Tuning QLoRA optimisé (Qwen2.5-0.5B-Instruct) :**
  * Spécialisation du modèle sur l'extraction stricte d'entités nommées (NER) médicales sous format JSON standardisé, permettant de faire tourner le modèle localement (Edge AI) avec une empreinte VRAM minimale (~1 Go).
* **Rigueur Scientifique & Défense face au Jury (Anti Data Leakage) :**
  * Le corpus standard CHIA (1000 études) a été scindé **strictement par identifiant d'étude (`NCT`)** : 800 études en entraînement (Train Set) et 200 en validation (Test Set). Le modèle n'a jamais appris sur des phrases du set d'évaluation.
  * **Holdout Set Démo Day :** Sélection de **5 études cliniques inédites** (prouvées mathématiquement exclues du dataset CHIA) pour la démonstration en direct devant le jury, démontrant la capacité de généralisation parfaite de notre IA sur les ~500 000 études de la base mondiale.
* **Convergence et performances mathématiques :**
  * Perte (`loss`) divisée par deux durant l'entraînement (de 1.66 à 0.84).
  * Précision mot à mot (`mean_token_accuracy`) atteignant **85.7%** avec une stabilité parfaite du gradient (`grad_norm` ~ 0.5) et un learning rate maintenu à `0.0002`.
* **Inférence Très Haute Vitesse (`vLLM` sur Lightning AI) :**
  * Atteinte de **75 tokens/seconde** sur GPU (L4), réduisant le temps d'extraction complet d'un essai à 2-4 secondes.

---

## 4. ☁️ Stockage, Ops & Perspectives (FinOps)
* **Persistance RAG Supabase (PostgreSQL / pgvector) :**
  * Contrairement au cache Frontend qui est éphémère pour la vitesse, la base de données vectorielle s'enrichit de manière persistante à chaque document ingéré. Le Chatbot RAG devient donc exponentiellement plus pertinent après chaque utilisation.
* **Industrialisation Ops :**
  * Code dockerisé, base de données provisionnée via **Terraform (IaC)**, suivi des latences et des métriques via **MLflow**, et scripts d'automatisation CRON prêts pour l'aspiration autonome des futurs essais cliniques publiés.

---

## 🎯 Statut pour la Réunion avec Aurélie
* ✅ **Dépôt GitHub (`Elkristobal59/clinicalapp`) :** 100% à jour, synchronisé et nettoyé sur la branche `main`.
* ✅ **Slide Deck Reveal.js :** Prêt, testé, parfaitement centré et sublime visuellement.
* ✅ **Application Streamlit / FastAPI :** Déployée, connectée aux modèles et opérationnelle pour le live démo.
* ✅ **Fiche de Pitch & Arguments de Défense :** Rédigés et prêts pour anticiper toutes les questions techniques du jury.
