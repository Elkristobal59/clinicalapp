import json
import os
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel

MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"
ADAPTER_PATH = r"d:\AIFS01\PROJET FINAL\stack_equipe\models\qwen_chia_finetuned"
GOLD_PATH = r"d:\AIFS01\PROJET FINAL\stack_equipe\data\chia_gold_standard.json"
PDF_DIR = r"d:\AIFS01\PROJET FINAL\stack_equipe\data\chia_pdfs"
OUTPUT_PATH = r"d:\AIFS01\PROJET FINAL\stack_equipe\data\chia_predictions_finetuned.json"

def main():
    print("Loading base model...")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16
    )
    
    # Load base model
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        quantization_config=bnb_config,
        device_map="auto"
    )
    
    # Load LoRA adapter
    print(f"Loading LoRA adapter from {ADAPTER_PATH}...")
    model = PeftModel.from_pretrained(model, ADAPTER_PATH)
    model.eval()
    
    tokenizer = AutoTokenizer.from_pretrained(ADAPTER_PATH)
    
    # Read target dataset
    with open(GOLD_PATH, "r", encoding="utf-8") as f:
        gold_data = json.load(f)
        
    # We will only predict the first 10 for a rapid evaluation benchmark to compare with the previous 10-study baseline
    gold_data = gold_data[:10]
    
    predictions = []
    
    for item in gold_data:
        nct_id = item.get("id")
        
        # Read the text files
        text_content = ""
        inc_path = os.path.join(PDF_DIR, f"{nct_id}_inc.txt")
        exc_path = os.path.join(PDF_DIR, f"{nct_id}_exc.txt")
        
        if os.path.exists(inc_path):
            with open(inc_path, "r", encoding="utf-8") as f:
                text_content += "Inclusion Criteria:\n" + f.read() + "\n\n"
        if os.path.exists(exc_path):
            with open(exc_path, "r", encoding="utf-8") as f:
                text_content += "Exclusion Criteria:\n" + f.read() + "\n\n"
                
        text_content = text_content.strip()
        if not text_content:
            continue
            
        messages = [
            {
                "role": "system",
                "content": "You are a specialized clinical trial AI. Your task is to extract medical entities from clinical trial eligibility criteria exactly matching the CHIA taxonomy (Condition, Drug, Procedure, Measurement, etc.). Provide the output as a JSON object."
            },
            {
                "role": "user",
                "content": f"Extract the medical entities from the following text:\n\n{text_content}"
            }
        ]
        
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(text, return_tensors="pt").to("cuda")
        
        with torch.no_grad():
            outputs = model.generate(**inputs, max_new_tokens=512)
            
        # extract response
        output_ids = outputs[0][len(inputs.input_ids[0]):]
        response = tokenizer.decode(output_ids, skip_special_tokens=True)
        
        print(f"--- Response for {nct_id} ---")
        print(response)
        
        # We need to parse this back to entities array for evaluate_ner.py
        entities = []
        try:
            # Sometime LLM outputs markdown formatting around JSON
            clean_resp = response.strip()
            if clean_resp.startswith("```json"):
                clean_resp = clean_resp[7:]
            if clean_resp.startswith("```"):
                clean_resp = clean_resp[3:]
            if clean_resp.endswith("```"):
                clean_resp = clean_resp[:-3]
            
            data = json.loads(clean_resp.strip())
            for key, values in data.items():
                for val in values:
                    entities.append({
                        "type": key,
                        "text": str(val)
                    })
        except Exception as e:
            print(f"Could not parse JSON for {nct_id}: {e}")
            
        predictions.append({
            "id": nct_id,
            "entities": entities
        })
        
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(predictions, f, indent=4, ensure_ascii=False)
        
    print(f"Predictions saved to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
