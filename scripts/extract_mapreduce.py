import os
import psycopg2
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, AutoModel
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# 1. Configuration Modèles & Base de données
# ==========================================
SUPABASE_DB_URL = os.getenv("SUPABASE_DATABASE_URL")
BIOBERT_MODEL = "dmis-lab/biobert-v1.1"

# Modèle Génératif léger (Qwen-1.5-1.8B ou 7B, idéal pour POC GPU)
QWEN_MODEL = "Qwen/Qwen1.5-1.8B-Chat" 

print("Initialisation du pipeline sur GPU...")
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Chargement BioBERT pour l'embedding de la question
print(f"Chargement {BIOBERT_MODEL} (Embeddings)...")
biobert_tokenizer = AutoTokenizer.from_pretrained(BIOBERT_MODEL)
biobert_model = AutoModel.from_pretrained(BIOBERT_MODEL).to(device)

# Chargement Qwen pour la génération (Map-Reduce)
print(f"Chargement {QWEN_MODEL} (LLM Génératif)...")
qwen_tokenizer = AutoTokenizer.from_pretrained(QWEN_MODEL)
qwen_model = AutoModelForCausalLM.from_pretrained(
    QWEN_MODEL, 
    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32, 
    device_map="auto"
)

# ==========================================
# 2. Fonctions de Recherche Vectorielle
# ==========================================
def get_biobert_embedding(text):
    inputs = biobert_tokenizer(text, return_tensors='pt', padding=True, truncation=True, max_length=512)
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        out = biobert_model(**inputs)
    # Mean pooling
    emb = torch.sum(out[0] * inputs['attention_mask'].unsqueeze(-1), 1) / torch.clamp(inputs['attention_mask'].sum(1, keepdim=True), min=1e-9)
    emb = torch.nn.functional.normalize(emb, p=2, dim=1)
    return emb[0].cpu().tolist()

def semantic_search(query, limit=5):
    """Recherche les chunks les plus pertinents dans Supabase"""
    query_emb = get_biobert_embedding(query)
    
    conn = psycopg2.connect(SUPABASE_DB_URL)
    cur = conn.cursor()
    
    # Distance Cosine (<=>) avec pgvector
    cur.execute("""
        SELECT doc_id, chunk_id, raw_text, 1 - (embedding <=> %s::vector) AS similarity
        FROM clinical_trials_data_biobert
        ORDER BY embedding <=> %s::vector
        LIMIT %s;
    """, (query_emb, query_emb, limit))
    
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    return results

# ==========================================
# 3. Fonction Map-Reduce via LLM
# ==========================================
def extract_clinical_info(document_id, target_disease):
    print(f"\n--- Extraction pour la maladie : {target_disease} ---")
    
    # ÉTAPE 1 : MAP (Recherche sémantique ciblée)
    query = f"inclusion criteria medications {target_disease}"
    print("Recherche des passages pertinents via BioBERT...")
    chunks = semantic_search(query, limit=5)
    
    if not chunks:
        print("Aucun texte trouvé dans la base.")
        return
        
    # Assemblage du contexte pour le LLM
    context = "\n\n".join([f"Extrait {c[1]}:\n{c[2]}" for c in chunks])
    print(f"{len(chunks)} extraits fusionnés en contexte.")

    # ÉTAPE 2 : REDUCE (Synthèse générative)
    prompt = f"""You are a clinical trials expert. Extract the medications and patient inclusion criteria for {target_disease} from the following text extracts.
Format your answer in clear JSON format: {{"condition": "...", "medications": [...], "inclusion_criteria": "..."}}

Context Extracts:
{context}

Response (JSON only):
"""
    
    messages = [
        {"role": "system", "content": "You are a helpful and precise medical AI assistant."},
        {"role": "user", "content": prompt}
    ]
    
    text = qwen_tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    model_inputs = qwen_tokenizer([text], return_tensors="pt").to(device)

    print("Génération de l'extraction par Qwen...")
    with torch.no_grad():
        generated_ids = qwen_model.generate(model_inputs.input_ids, max_new_tokens=2048, temperature=0.1)
        
    generated_ids = [
        output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
    ]
    response = qwen_tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
    
    print("\n✅ RÉSULTAT EXTRACTION MAP-REDUCE :")
    print(response)


if __name__ == "__main__":
    # Test d'extraction sur un essai cardiologique
    extract_clinical_info("test_doc", "Cardiomyopathy")
