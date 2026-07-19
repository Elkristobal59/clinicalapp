import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Configuration Supabase
SUPABASE_DB_URL = os.getenv("SUPABASE_DATABASE_URL")

def init_supabase_db():
    if not SUPABASE_DB_URL:
        print("Erreur: La variable d'environnement SUPABASE_DATABASE_URL n'est pas définie.")
        print("Récupérez la Transaction Pooling URL depuis le dashboard Supabase (Database -> Settings).")
        return

    try:
        print("Connexion à Supabase PostgreSQL...")
        conn = psycopg2.connect(SUPABASE_DB_URL)
        cur = conn.cursor()

        print("1. Activation de l'extension pgvector...")
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

        print("2. Création de la table des extractions cliniques (BioBERT 768 dimensions)...")
        create_table_query = """
        CREATE TABLE IF NOT EXISTS clinical_trials_data_biobert (
            id SERIAL PRIMARY KEY,
            doc_id VARCHAR(255) NOT NULL,
            chunk_id VARCHAR(255) UNIQUE NOT NULL,
            raw_text TEXT,
            embedding vector(768),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """
        cur.execute(create_table_query)

        print("3. Création de l'index vectoriel HNSW...")
        cur.execute("""
        CREATE INDEX IF NOT EXISTS clinical_trials_data_biobert_embedding_idx 
        ON clinical_trials_data_biobert USING hnsw (embedding vector_cosine_ops);
        """)

        conn.commit()
        print("Succès ! La base Supabase est prête avec pgvector.")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"Erreur d'initialisation Supabase : {e}")

if __name__ == "__main__":
    init_supabase_db()
