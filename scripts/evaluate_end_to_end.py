import os
import glob
import json
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel
from tqdm import tqdm
from pathlib import Path

from scripts.pdf_parser.pipeline import locate_section
from scripts.remap_offsets import remap_document

MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"
ADAPTER_DIR = "Elkristobal59/qwen-7b-chia-ner"
TEST_DIR = os.path.join("data", "test", "testset")
PRED_DIR = os.path.join("data", "test_predictions_end2end")
TEMP_DIR = os.path.join("data", "temp_chunks")

def build_prompt(text):
    return [
        {"role": "system", "content": "You are a medical AI assistant specialized in clinical trial named entity recognition (NER). You extract key entities precisely and format them in JSON."},
        {"role": "user", "content": f"Extract all relevant clinical entities from the following text and format them as JSON. The allowed entity types are: Condition, Drug, Procedure, Measurement, Value, Temporal, Observation, Person, Device.\n\nText: {text}"}
    ]

def find_offsets_naive(text, entity_str):
    idx = text.find(entity_str)
    if idx != -1:
        return idx, idx + len(entity_str)
    lower_text = text.lower()
    lower_ent = entity_str.lower()
    idx = lower_text.find(lower_ent)
    if idx != -1:
        return idx, idx + len(entity_str)
    return -1, -1

def get_pdf_path(nct_id):
    pdf_files = glob.glob(os.path.join(TEST_DIR, f"{nct_id}_Prot_*.pdf"))
    return pdf_files[0] if pdf_files else None

def main():
    os.makedirs(PRED_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)

    print("Loading tokenizer and model...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16
    )
    
    base_model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        quantization_config=bnb_config if device == "cuda:0" else None,
        device_map={"": device}
    )
    
    try:
        model = PeftModel.from_pretrained(base_model, ADAPTER_DIR)
    except Exception:
        print("Adapter not found. Using base model.")
        model = base_model
        
    model.eval()

    gold_files = glob.glob(os.path.join(TEST_DIR, "*_inc.txt")) + glob.glob(os.path.join(TEST_DIR, "*_exc.txt"))
    
    for gold_path in tqdm(gold_files):
        filename = os.path.basename(gold_path)
        nct_id = filename.split('_')[0]
        
        pdf_path = get_pdf_path(nct_id)
        if not pdf_path:
            continue
            
        # 1. TF-IDF Localization
        result = locate_section(pdf_path)
        chunk_text = result.section.text
        
        # Save chunk text to temp file
        temp_txt_path = os.path.join(TEMP_DIR, f"{filename}_chunk.txt")
        with open(temp_txt_path, 'w', encoding='utf-8') as f:
            f.write(chunk_text)
            
        # 2. Qwen NER Extraction on chunk
        messages = build_prompt(chunk_text)
        prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer([prompt], return_tensors="pt").to(model.device)
        
        with torch.no_grad():
            outputs = model.generate(**inputs, max_new_tokens=1024, do_sample=False, pad_token_id=tokenizer.eos_token_id)
            
        response = tokenizer.decode(outputs[0][len(inputs.input_ids[0]):], skip_special_tokens=True)
        
        try:
            clean = response.strip()
            if clean.startswith("```json"): clean = clean[7:]
            if clean.endswith("```"): clean = clean[:-3]
            entities = json.loads(clean)
        except json.JSONDecodeError:
            entities = []

        # Write naive ANN on chunk
        temp_ann_path = os.path.join(TEMP_DIR, f"{filename}_chunk.ann")
        with open(temp_ann_path, 'w', encoding='utf-8') as f:
            for i, ent in enumerate(entities):
                if isinstance(ent, dict):
                    ent_text = ent.get("entity", "")
                    label = ent.get("label", "")
                    if not ent_text or not label: continue
                    start, end = find_offsets_naive(chunk_text, ent_text)
                    if start != -1:
                        f.write(f"T{i+1}\t{label} {start} {end}\t{ent_text}\n")
                    
        # 3. Remap offsets to gold snippet using remap_offsets.py
        out_ann_path = os.path.join(PRED_DIR, filename.replace(".txt", ".ann"))
        try:
            remap_document(temp_txt_path, temp_ann_path, gold_path, out_ann_path)
        except Exception as e:
            print(f"Error remapping {filename}: {e}")

if __name__ == "__main__":
    main()
