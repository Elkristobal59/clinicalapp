-- Activation de l'extension pgvector si elle n'existe pas
CREATE EXTENSION IF NOT EXISTS vector;

-- Création de la table principale
CREATE TABLE IF NOT EXISTS clinical_trials_data_biobert (
    id SERIAL PRIMARY KEY,
    doc_id VARCHAR(255) NOT NULL,
    chunk_id VARCHAR(255) UNIQUE NOT NULL,
    raw_text TEXT NOT NULL,
    embedding vector(768)
);

-- Création de l'index HNSW pour optimiser la recherche par similarité cosinus
CREATE INDEX IF NOT EXISTS clinical_trials_biobert_embedding_idx 
ON clinical_trials_data_biobert 
USING hnsw (embedding vector_cosine_ops);
