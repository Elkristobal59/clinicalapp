import os
import json
import torch
import numpy as np
from transformers import AutoTokenizer, AutoModel, AutoModelForCausalLM
from langchain_text_splitters import RecursiveCharacterTextSplitter

BIOBERT_MODEL = "dmis-lab/biobert-v1.1"
QWEN_MODEL = "Qwen/Qwen1.5-7B-Chat"
DATA_DIR = r"d:\AIFS01\PROJET FINAL\stack_equipe\data\chia_pdfs"
GOLD_FILE = r"d:\AIFS01\PROJET FINAL\stack_equipe\data\chia_gold_standard.json"

print("Loading Models on CPU...")
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

bio_tokenizer = AutoTokenizer.from_pretrained(BIOBERT_MODEL)
bio_model = AutoModel.from_pretrained(BIOBERT_MODEL).to(device)

qwen_tokenizer = AutoTokenizer.from_pretrained(QWEN_MODEL)
qwen_model = AutoModelForCausalLM.from_pretrained(
    QWEN_MODEL, 
    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
    device_map="auto"
)
qwen_model.eval()

def get_biobert_embedding(text):
    encoded_input = bio_tokenizer(text, padding=True, truncation=True, return_tensors='pt', max_length=512)
    encoded_input = {k: v.to(device) for k, v in encoded_input.items()}
    with torch.no_grad():
        out = bio_model(**encoded_input)
    emb = torch.sum(out[0] * encoded_input['attention_mask'].unsqueeze(-1), 1) / torch.clamp(encoded_input['attention_mask'].sum(1, keepdim=True), min=1e-9)
    emb = torch.nn.functional.normalize(emb, p=2, dim=1)
    return emb[0].cpu().numpy()

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def main():
    with open(GOLD_FILE, 'r', encoding='utf-8') as f:
        gold_data = json.load(f)
        
    # We evaluate RAG pipeline on 2 studies due to CPU slowness
    studies_to_eval = gold_data[:2]
    
    tp_total = 0
    fp_total = 0
    fn_total = 0
    
    query_emb = get_biobert_embedding("inclusion criteria medications")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200, length_function=len)
    
    for study in studies_to_eval:
        nct_id = study["id"]
        
        # We only evaluate Drug extraction because the API only asks for medications
        gold_drugs = set([ent["text"].lower().strip() for ent in study["entities"] if ent["type"] == "Drug"])
        
        inc_file = os.path.join(DATA_DIR, f"{nct_id}_inc.txt")
        exc_file = os.path.join(DATA_DIR, f"{nct_id}_exc.txt")
        text = ""
        if os.path.exists(inc_file):
            with open(inc_file, "r", encoding="utf-8") as f:
                text += f.read() + "\n"
        if os.path.exists(exc_file):
            with open(exc_file, "r", encoding="utf-8") as f:
                text += f.read() + "\n"
                
        chunks = text_splitter.split_text(text)
        chunk_embs = [get_biobert_embedding(c) for c in chunks]
        similarities = [cosine_similarity(query_emb, emb) for emb in chunk_embs]
        
        top_k = min(5, len(chunks))
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        context = "\n\n".join([f"Extrait:\n{chunks[i]}" for i in top_indices])
        
        prompt = f"""You are a clinical trials expert. Extract the medications and patient inclusion criteria from the following text extracts.
Format your answer in clear JSON format: {{"condition": "...", "medications": ["drug1", "drug2"], "inclusion_criteria": "..."}}

Context Extracts:
{context}

Response (JSON only):
"""
        messages = [
            {"role": "system", "content": "You are a helpful and precise medical AI assistant."},
            {"role": "user", "content": prompt}
        ]
        
        text_prompt = qwen_tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = qwen_tokenizer(text_prompt, return_tensors="pt").to(device)
        
        with torch.no_grad():
            generated_ids = qwen_model.generate(**inputs, max_new_tokens=512, do_sample=False)
            
        gen_ids = generated_ids[0][inputs.input_ids.shape[1]:]
        response_text = qwen_tokenizer.decode(gen_ids, skip_special_tokens=True).strip()
        
        if response_text.startswith("```json"): response_text = response_text[7:]
        if response_text.startswith("```"): response_text = response_text[3:]
        if response_text.endswith("```"): response_text = response_text[:-3]
        
        try:
            parsed = json.loads(response_text.strip())
            pred_drugs = set([str(d).lower().strip() for d in parsed.get("medications", [])])
        except Exception as e:
            print(f"Error parsing JSON for {nct_id}: {e}")
            pred_drugs = set()
            
        tp = len(gold_drugs.intersection(pred_drugs))
        fp = len(pred_drugs - gold_drugs)
        fn = len(gold_drugs - pred_drugs)
        
        tp_total += tp
        fp_total += fp
        fn_total += fn
        print(f"{nct_id} processed. Found {len(pred_drugs)} drugs. TP:{tp} FP:{fp} FN:{fn}")
        
    precision = tp_total / (tp_total + fp_total) if (tp_total + fp_total) > 0 else 0
    recall = tp_total / (tp_total + fn_total) if (tp_total + fn_total) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    print(f"\n--- RAG Pipeline Evaluation (BioBERT + Qwen) on 2 studies ---")
    print(f"TP: {tp_total}, FP: {fp_total}, FN: {fn_total}")
    print(f"Precision : {precision:.4f}")
    print(f"Recall    : {recall:.4f}")
    print(f"F1 Score  : {f1:.4f}")

if __name__ == "__main__":
    main()
