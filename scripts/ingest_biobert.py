import os
import glob
import psycopg2
import fitz
import torch
from transformers import AutoTokenizer, AutoModel
from langchain_text_splitters import RecursiveCharacterTextSplitter
from dotenv import load_dotenv

load_dotenv()

# Configuration Supabase
SUPABASE_DB_URL = os.getenv("SUPABASE_DATABASE_URL")

# Modèle BioBERT
MODEL_NAME = "dmis-lab/biobert-v1.1"

print(f"Chargement du tokenizer et du modèle {MODEL_NAME}...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModel.from_pretrained(MODEL_NAME)

# Si un GPU est dispo, on l'utilise (sinon CPU local)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)
print(f"Modèle chargé sur : {device}")

def mean_pooling(model_output, attention_mask):
    """Effectue un Mean Pooling pour obtenir un seul vecteur par chunk de texte"""
    token_embeddings = model_output[0] 
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)

def get_biobert_embedding(text):
    """Retourne l'embedding BioBERT (768 dimensions) pour un texte donné."""
    encoded_input = tokenizer(text, padding=True, truncation=True, return_tensors='pt', max_length=512)
    encoded_input = {k: v.to(device) for k, v in encoded_input.items()}
    
    with torch.no_grad():
        model_output = model(**encoded_input)
        
    sentence_embeddings = mean_pooling(model_output, encoded_input['attention_mask'])
    # Normalisation optionnelle
    sentence_embeddings = torch.nn.functional.normalize(sentence_embeddings, p=2, dim=1)
    
    return sentence_embeddings[0].cpu().tolist()

def process_and_ingest(pdf_path):
    # Extraction texte brut
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page_num in range(len(doc)):
            text += doc.load_page(page_num).get_text() + "\n"
        doc.close()
    except Exception as e:
        print(f"Erreur PDF {pdf_path}: {e}")
        return

    # Chunking sémantique
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, # BioBERT a une limite de 512 tokens, on réduit un peu le texte
        chunk_overlap=200,
        length_function=len
    )
    chunks = text_splitter.split_text(text)
    
    filename = os.path.basename(pdf_path).replace(".pdf", "")
    
    print(f"Document {filename} découpé en {len(chunks)} chunks. Ingestion Supabase en cours...")
    
    conn = psycopg2.connect(SUPABASE_DB_URL)
    cur = conn.cursor()
    
    for idx, chunk_text in enumerate(chunks):
        embedding = get_biobert_embedding(chunk_text)
        
        # Insertion dans Supabase
        cur.execute("""
            INSERT INTO clinical_trials_data_biobert (doc_id, chunk_id, raw_text, embedding)
            VALUES (%s, %s, %s, %s)
        """, (
            filename,
            f"{filename}_chunk_{idx}",
            chunk_text,
            embedding
        ))
        
    conn.commit()
    cur.close()
    conn.close()
    print(f"✅ Ingestion terminée pour {filename}")

if __name__ == "__main__":
    # Test avec un seul PDF au hasard pour valider la pipeline (on prend 1 vrai PDF de cardiologie)
    test_pdf_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'real_pdfs', 'playwright_cardio_100'))
    pdfs = glob.glob(os.path.join(test_pdf_dir, "*.pdf"))
    
    if pdfs:
        # On ingère juste le premier pour tester
        process_and_ingest(pdfs[0])
    else:
        print(f"Aucun PDF trouvé dans {test_pdf_dir}")
