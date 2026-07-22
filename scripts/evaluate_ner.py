import json

def load_data(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def evaluate(gold_file, pred_file):
    gold_data = load_data(gold_file)
    pred_data = load_data(pred_file)
    
    # Map by NCT ID
    gold_map = {item['id']: item['entities'] for item in gold_data}
    
    tp_total = 0
    fp_total = 0
    fn_total = 0
    
    evaluated_studies = 0
    
    for pred_item in pred_data:
        nct_id = pred_item['id']
        
        if nct_id not in gold_map:
            print(f"Warning: {nct_id} not in Gold Standard. Skipping.")
            continue
            
        evaluated_studies += 1
        
        # Convert to sets of (type, text.lower()) for exact match comparison
        # We lowercase the text because LLMs sometimes change casing
        
        gold_set = set()
        for ent in gold_map[nct_id]:
            gold_set.add((ent['type'].lower(), ent['text'].lower().strip()))
            
        pred_set = set()
        for ent in pred_item['entities']:
            pred_set.add((ent['type'].lower(), ent['text'].lower().strip()))
            
        tp = len(gold_set.intersection(pred_set))
        fp = len(pred_set - gold_set)
        fn = len(gold_set - pred_set)
        
        tp_total += tp
        fp_total += fp
        fn_total += fn

    if (tp_total + fp_total) > 0:
        precision = tp_total / (tp_total + fp_total)
    else:
        precision = 0.0
        
    if (tp_total + fn_total) > 0:
        recall = tp_total / (tp_total + fn_total)
    else:
        recall = 0.0
        
    if (precision + recall) > 0:
        f1 = 2 * (precision * recall) / (precision + recall)
    else:
        f1 = 0.0
        
    print(f"--- Evaluation Results on {evaluated_studies} studies ---")
    print(f"True Positives (TP) : {tp_total}")
    print(f"False Positives (FP): {fp_total}")
    print(f"False Negatives (FN): {fn_total}")
    print("------------------------------------------")
    print(f"Precision : {precision:.4f}")
    print(f"Recall    : {recall:.4f}")
    print(f"F1 Score  : {f1:.4f}")
    
    return precision, recall, f1

import sys

if __name__ == "__main__":
    GOLD = r"d:\AIFS01\PROJET FINAL\stack_equipe\data\chia_gold_standard.json"
    if len(sys.argv) > 1:
        PRED = sys.argv[1]
    else:
        PRED = r"d:\AIFS01\PROJET FINAL\stack_equipe\data\chia_predictions.json"
    
    print(f"Evaluating {PRED}...")
    evaluate(GOLD, PRED)
