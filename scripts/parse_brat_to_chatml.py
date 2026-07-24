import os
import json
import glob

TARGET_ENTITIES = {
    "Condition", "Drug", "Procedure", "Measurement", 
    "Value", "Temporal", "Observation", "Person", "Device"
}

def parse_ann_file(ann_path):
    entities = []
    if not os.path.exists(ann_path):
        return entities
        
    with open(ann_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('T'):
                # Format: T1\tCondition 39 63\thepatocellular carcinoma
                parts = line.strip().split('\t')
                if len(parts) >= 3:
                    entity_info = parts[1].split(' ')
                    label = entity_info[0]
                    text = parts[2]
                    
                    if label in TARGET_ENTITIES:
                        entities.append({
                            "entity": text,
                            "label": label
                        })
    return entities

def convert_to_chatml(text, entities):
    user_prompt = f"Extract all relevant clinical entities from the following text and format them as JSON. The allowed entity types are: Condition, Drug, Procedure, Measurement, Value, Temporal, Observation, Person, Device.\n\nText: {text}"
    assistant_response = json.dumps(entities, ensure_ascii=False)
    
    chat_format = {
        "messages": [
            {"role": "system", "content": "You are a medical AI assistant specialized in clinical trial named entity recognition (NER). You extract key entities precisely and format them in JSON."},
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": assistant_response}
        ]
    }
    return chat_format

def main():
    train_dir = os.path.join("data", "train", "trainset")
    output_path = os.path.join("data", "train_dataset.jsonl")
    
    if not os.path.exists(train_dir):
        print(f"Error: {train_dir} not found.")
        return
        
    txt_files = glob.glob(os.path.join(train_dir, "*.txt"))
    print(f"Found {len(txt_files)} .txt files in {train_dir}")
    
    chatml_data = []
    for txt_path in txt_files:
        ann_path = txt_path.replace('.txt', '.ann')
        
        with open(txt_path, 'r', encoding='utf-8') as f:
            text = f.read()
            
        entities = parse_ann_file(ann_path)
        if len(entities) > 0:
            chatml_data.append(convert_to_chatml(text, entities))
            
    with open(output_path, 'w', encoding='utf-8') as f:
        for item in chatml_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
            
    print(f"Successfully generated {output_path} with {len(chatml_data)} examples.")

if __name__ == "__main__":
    main()
