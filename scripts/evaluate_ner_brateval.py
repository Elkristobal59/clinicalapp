import os
import glob
import json
import re
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
from tqdm import tqdm

MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"
ADAPTER_DIR = "models/qwen_0.5b_chia_finetuned"
TEST_DIR = os.path.join("data", "test", "testset")
PRED_DIR = os.path.join("data", "test_predictions")

def build_prompt(text):
    return [
        {"role": "system", "content": "You are a medical AI assistant specialized in clinical trial named entity recognition (NER). You extract key entities precisely and format them in JSON."},
        {"role": "user", "content": f"Extract all relevant clinical entities from the following text and format them as JSON. The allowed entity types are: Condition, Drug, Procedure, Measurement, Value, Temporal, Observation, Person, Device.\n\nText: {text}"}
    ]

def find_offsets(text, entity_str):
    """Find start and end character offsets of entity_str in text."""
    # Simple approach: find the first occurrence.
    # A more robust approach would track already found entities, but this is a baseline.
    idx = text.find(entity_str)
    if idx != -1:
        return idx, idx + len(entity_str)
    
    # Try case-insensitive search if exact match fails
    lower_text = text.lower()
    lower_ent = entity_str.lower()
    idx = lower_text.find(lower_ent)
    if idx != -1:
        return idx, idx + len(entity_str)
        
    return -1, -1

def main():
    if not os.path.exists(PRED_DIR):
        os.makedirs(PRED_DIR)

    print("Loading tokenizer and base model...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    
    base_model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        device_map="auto",
        torch_dtype=torch.float16
    )
    
    if os.path.exists(ADAPTER_DIR):
        print(f"Loading fine-tuned adapter from {ADAPTER_DIR}...")
        model = PeftModel.from_pretrained(base_model, ADAPTER_DIR)
    else:
        print(f"⚠️ Adapter not found at {ADAPTER_DIR}. Using base model.")
        model = base_model
        
    model.eval()

    txt_files = glob.glob(os.path.join(TEST_DIR, "*.txt"))
    print(f"Found {len(txt_files)} test documents.")

    for txt_path in tqdm(txt_files):
        with open(txt_path, 'r', encoding='utf-8') as f:
            text = f.read()
            
        messages = build_prompt(text)
        prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer([prompt], return_tensors="pt").to(model.device)
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=1024,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id
            )
            
        response = tokenizer.decode(outputs[0][len(inputs.input_ids[0]):], skip_special_tokens=True)
        
        # Parse JSON
        try:
            # Sometime LLMs wrap json in ```json ... ```
            clean_response = response.strip()
            if clean_response.startswith("```json"):
                clean_response = clean_response[7:]
            if clean_response.endswith("```"):
                clean_response = clean_response[:-3]
                
            entities = json.loads(clean_response)
        except Exception as e:
            # Failed to parse
            entities = []
            
        # Write to .ann file
        base_name = os.path.basename(txt_path).replace(".txt", ".ann")
        pred_path = os.path.join(PRED_DIR, base_name)
        
        with open(pred_path, 'w', encoding='utf-8') as f:
            t_id = 1
            for ent in entities:
                ent_text = ent.get("entity", "")
                label = ent.get("label", "")
                if not ent_text or not label:
                    continue
                    
                start, end = find_offsets(text, ent_text)
                if start != -1:
                    # Format: T1\tCondition 39 63\thepatocellular carcinoma
                    f.write(f"T{t_id}\t{label} {start} {end}\t{ent_text}\n")
                    t_id += 1

    print(f"\n✅ Evaluation complete. Predictions saved to {PRED_DIR}")
    print("👉 Next step: Run brateval to compare the ground truth (.ann in testset) vs predictions.")

if __name__ == "__main__":
    main()
