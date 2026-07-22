import os
import psycopg2

NEON_DB_URL = os.getenv("DATABASE_URL")

def init_neondb():
    if not NEON_DB_URL:
        print("Erreur: DATABASE_URL manquante.")
        return

    conn = psycopg2.connect(NEON_DB_URL)
    cur = conn.cursor()

    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS clinical_trials_data (
        id SERIAL PRIMARY KEY,
        doc_id VARCHAR(255) NOT NULL,
        chunk_id VARCHAR(255) NOT NULL,
        condition TEXT,
        medications JSONB,
        criteria TEXT,
        raw_text TEXT,
        embedding vector(1536),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS clinical_trials_data_embedding_idx 
    ON clinical_trials_data USING hnsw (embedding vector_cosine_ops);
    """)

    conn.commit()
    print("Base NeonDB prête (Stack Équipe).")
    cur.close()
    conn.close()

if __name__ == "__main__":
    init_neondb()
