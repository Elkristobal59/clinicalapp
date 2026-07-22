import os
import glob
import json
from collections import defaultdict

def parse_ann_file(filepath):
    entities = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or not line.startswith('T'):
                    continue
                
                parts = line.split('\t')
                if len(parts) >= 3:
                    entity_id = parts[0]
                    type_offsets = parts[1].split(' ')
                    entity_type = type_offsets[0]
                    entity_text = parts[2]
                    
                    # Ignore composite types if any, just take the main type
                    entities.append({
                        "type": entity_type,
                        "text": entity_text
                    })
    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
    return entities

def build_gold_standard(data_dir, output_file):
    ann_files = glob.glob(os.path.join(data_dir, "*.ann"))
    
    # Group entities by study NCT ID
    study_entities = defaultdict(list)
    
    for ann_file in ann_files:
        basename = os.path.basename(ann_file)
        # e.g. NCT00050349_exc.ann
        nct_id = basename.split('_')[0]
        
        entities = parse_ann_file(ann_file)
        study_entities[nct_id].extend(entities)
        
    gold_data = []
    for nct_id, entities in study_entities.items():
        gold_data.append({
            "id": nct_id,
            "entities": entities
        })
        
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(gold_data, f, indent=4, ensure_ascii=False)
        
    print(f"Gold standard generated at {output_file} with {len(gold_data)} studies.")

if __name__ == "__main__":
    DATA_DIR = r"d:\AIFS01\PROJET FINAL\stack_equipe\data\chia_pdfs"
    OUTPUT_FILE = r"d:\AIFS01\PROJET FINAL\stack_equipe\data\chia_gold_standard.json"
    
    build_gold_standard(DATA_DIR, OUTPUT_FILE)
