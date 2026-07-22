import os
import glob
import json
import torch
from transformers import AutoTokenizer

# Essayons d'importer vllm pour l'inférence rapide
try:
    from vllm import LLM, SamplingParams
    USE_VLLM = True
except ImportError:
    from transformers import AutoModelForCausalLM
    USE_VLLM = False

QWEN_MODEL = "Qwen/Qwen1.5-7B-Chat"
DATA_DIR = r"d:\AIFS01\PROJET FINAL\stack_equipe\data\chia_pdfs"
OUTPUT_FILE = r"d:\AIFS01\PROJET FINAL\stack_equipe\data\chia_predictions_qwen.json"

def main():
    print(f"Chargement du tokenizer {QWEN_MODEL}...")
    tokenizer = AutoTokenizer.from_pretrained(QWEN_MODEL)
    
    if USE_VLLM and torch.cuda.is_available():
        print(f"Chargement de {QWEN_MODEL} avec vLLM...")
        llm = LLM(model=QWEN_MODEL, gpu_memory_utilization=0.90, max_model_len=4096)
        sampling_params = SamplingParams(temperature=0.0, max_tokens=2048, stop=["```"])
    else:
        print(f"Chargement de {QWEN_MODEL} avec Transformers (Fallback)...")
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = AutoModelForCausalLM.from_pretrained(
            QWEN_MODEL, 
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto"
        )
        model.eval()

    txt_files = glob.glob(os.path.join(DATA_DIR, "*.txt"))
    
    # Group txt files by study
    study_texts = {}
    for filepath in txt_files:
        basename = os.path.basename(filepath)
        nct_id = basename.split('_')[0]
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if nct_id not in study_texts:
            study_texts[nct_id] = content
        else:
            study_texts[nct_id] += "\n" + content
            
    # Process 2 studies to save time on CPU
    max_studies = 2
    study_items = list(study_texts.items())[:max_studies]
    print(f"Lancement des prédictions sur {len(study_items)} études...")
    
    prompts = []
    nct_ids = []
    
    system_prompt = "You are a clinical trials expert. Extract all clinical named entities from the text. The entities must be one of: 'Condition', 'Drug', 'Procedure', 'Measurement', 'Observation', 'Person', 'Device', 'Qualifier', 'Multiplier', 'Reference_point', 'Temporal', 'Value'. Output ONLY a JSON list of objects, each with 'type' and 'text'."
    
    for nct_id, text in study_items:
        # Truncate text to avoid exceeding context
        text_trunc = text[:12000] 
        user_prompt = f"Text:\n{text_trunc}\n\nExtract the entities in JSON format like this:\n[\n  {{\"type\": \"Condition\", \"text\": \"diabetes\"}}\n]\n\nOutput only the raw JSON array without markdown blocks."
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        text_prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        prompts.append(text_prompt)
        nct_ids.append(nct_id)
        
    predictions = []
    
    if USE_VLLM and torch.cuda.is_available():
        outputs = llm.generate(prompts, sampling_params)
        for i, out in enumerate(outputs):
            response_text = out.outputs[0].text.strip()
            # Clean up potential markdown formatting
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
                
            try:
                entities = json.loads(response_text)
                if not isinstance(entities, list):
                    entities = []
            except Exception as e:
                print(f"Error parsing JSON for {nct_ids[i]}: {e}")
                entities = []
                
            predictions.append({"id": nct_ids[i], "entities": entities})
            print(f"Processed {nct_ids[i]} ({len(entities)} entities)")
    else:
        for i, prompt in enumerate(prompts):
            inputs = tokenizer(prompt, return_tensors="pt").to(device)
            with torch.no_grad():
                generated_ids = model.generate(**inputs, max_new_tokens=2048, do_sample=False)
            
            gen_ids = generated_ids[0][inputs.input_ids.shape[1]:]
            response_text = tokenizer.decode(gen_ids, skip_special_tokens=True).strip()
            
            # Clean up potential markdown formatting
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
                
            try:
                entities = json.loads(response_text)
                if not isinstance(entities, list):
                    entities = []
            except Exception as e:
                print(f"Error parsing JSON for {nct_ids[i]}: {e}")
                entities = []
                
            predictions.append({"id": nct_ids[i], "entities": entities})
            print(f"Processed {nct_ids[i]} ({len(entities)} entities)")
            
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(predictions, f, indent=4, ensure_ascii=False)
        
    print(f"\nPrédictions sauvegardées dans {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
