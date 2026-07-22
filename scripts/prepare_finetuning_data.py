import json
import os

GOLD_STANDARD_PATH = r"d:\AIFS01\PROJET FINAL\stack_equipe\data\chia_gold_standard.json"
PDF_DIR = r"d:\AIFS01\PROJET FINAL\stack_equipe\data\chia_pdfs"
OUTPUT_PATH = r"d:\AIFS01\PROJET FINAL\stack_equipe\data\chia_finetuning_dataset.jsonl"

def build_dataset():
    if not os.path.exists(GOLD_STANDARD_PATH):
        print(f"File not found: {GOLD_STANDARD_PATH}")
        return
        
    with open(GOLD_STANDARD_PATH, "r", encoding="utf-8") as f:
        gold_data = json.load(f)
        
    dataset = []
    
    for item in gold_data:
        nct_id = item.get("id")
        if not nct_id:
            continue
            
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
            
        # Format the target entities as a grouped JSON
        entities = item.get("entities", [])
        grouped_entities = {}
        for ent in entities:
            cat = ent["type"]
            text = ent["text"]
            if cat not in grouped_entities:
                grouped_entities[cat] = []
            if text not in grouped_entities[cat]:
                grouped_entities[cat].append(text)
                
        # Create the conversational format
        messages = [
            {
                "role": "system",
                "content": "You are a specialized clinical trial AI. Your task is to extract medical entities from clinical trial eligibility criteria exactly matching the CHIA taxonomy (Condition, Drug, Procedure, Measurement, etc.). Provide the output as a JSON object."
            },
            {
                "role": "user",
                "content": f"Extract the medical entities from the following text:\n\n{text_content}"
            },
            {
                "role": "assistant",
                "content": json.dumps(grouped_entities, ensure_ascii=False)
            }
        ]
        
        dataset.append({"messages": messages})
        
    # Write to jsonl
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        for ds in dataset:
            f.write(json.dumps(ds, ensure_ascii=False) + "\n")
            
    print(f"Generated {len(dataset)} examples in {OUTPUT_PATH}")

if __name__ == "__main__":
    build_dataset()
