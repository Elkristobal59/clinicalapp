import os
import json
import torch
import numpy as np
from transformers import AutoTokenizer, AutoModel
from langchain_text_splitters import RecursiveCharacterTextSplitter

BIOBERT_MODEL = "dmis-lab/biobert-v1.1"
DATA_DIR = r"d:\AIFS01\PROJET FINAL\stack_equipe\data\chia_pdfs"
GOLD_FILE = r"d:\AIFS01\PROJET FINAL\stack_equipe\data\chia_gold_standard.json"

print("Loading BioBERT on CPU...")
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
tokenizer = AutoTokenizer.from_pretrained(BIOBERT_MODEL)
model = AutoModel.from_pretrained(BIOBERT_MODEL).to(device)

def get_biobert_embedding(text):
    encoded_input = tokenizer(text, padding=True, truncation=True, return_tensors='pt', max_length=512)
    encoded_input = {k: v.to(device) for k, v in encoded_input.items()}
    with torch.no_grad():
        out = model(**encoded_input)
    # Mean pooling
    emb = torch.sum(out[0] * encoded_input['attention_mask'].unsqueeze(-1), 1) / torch.clamp(encoded_input['attention_mask'].sum(1, keepdim=True), min=1e-9)
    emb = torch.nn.functional.normalize(emb, p=2, dim=1)
    return emb[0].cpu().numpy()

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def load_gold_standard(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def main():
    gold_data = load_gold_standard(GOLD_FILE)
    
    # We will evaluate on the first 10 studies
    studies_to_eval = gold_data[:10]
    
    total_entities = 0
    found_entities = 0
    
    query = "inclusion criteria medications"
    query_emb = get_biobert_embedding(query)
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200, length_function=len)
    
    for study in studies_to_eval:
        nct_id = study["id"]
        entities = study["entities"]
        
        # Load text (inc and exc)
        inc_file = os.path.join(DATA_DIR, f"{nct_id}_inc.txt")
        exc_file = os.path.join(DATA_DIR, f"{nct_id}_exc.txt")
        
        text = ""
        if os.path.exists(inc_file):
            with open(inc_file, "r", encoding="utf-8") as f:
                text += f.read() + "\n"
        if os.path.exists(exc_file):
            with open(exc_file, "r", encoding="utf-8") as f:
                text += f.read() + "\n"
                
        if not text.strip():
            continue
            
        chunks = text_splitter.split_text(text)
        
        if not chunks:
            continue
            
        # Get embeddings for all chunks
        chunk_embs = [get_biobert_embedding(chunk) for chunk in chunks]
        
        # Calculate similarities
        similarities = [cosine_similarity(query_emb, emb) for emb in chunk_embs]
        
        # Get top 5 indices
        top_k = min(5, len(chunks))
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        retrieved_text = " ".join([chunks[i].lower() for i in top_indices])
        
        # Evaluate Recall of retrieved context
        study_found = 0
        for ent in entities:
            # We check if the exact text is in the retrieved chunks
            if ent["text"].lower().strip() in retrieved_text:
                study_found += 1
                
        total_entities += len(entities)
        found_entities += study_found
        
        print(f"{nct_id}: BioBERT retrieved {study_found}/{len(entities)} entities (Recall: {study_found/max(1, len(entities)):.2f})")
        
    final_recall = found_entities / total_entities if total_entities > 0 else 0
    print("\n--- BioBERT Retrieval Evaluation ---")
    print(f"Total Entities in Gold Standard: {total_entities}")
    print(f"Entities present in Top-5 Chunks: {found_entities}")
    print(f"BioBERT Recall Score: {final_recall:.4f}")

if __name__ == "__main__":
    main()
