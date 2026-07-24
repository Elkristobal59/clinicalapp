import os
import glob
import sys
from collections import defaultdict

def parse_ann(file_path):
    entities = set()
    if not os.path.exists(file_path):
        return entities
        
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('T'):
                parts = line.strip().split('\t')
                if len(parts) >= 3:
                    # e.g. "Condition 39 63"
                    entity_info = parts[1].split(' ')
                    label = entity_info[0]
                    # Handle discontinuous spans in Brat (e.g. "39 45;50 63") 
                    # We just take the exact string for simplicity
                    span = parts[1].replace(label + ' ', '') 
                    text = parts[2]
                    
                    # Store as tuple (label, span, text) for EXACT matching
                    entities.add((label, span, text))
    return entities

def evaluate(gold_dir, pred_dir):
    gold_files = glob.glob(os.path.join(gold_dir, "*.ann"))
    
    tp_total = 0
    fp_total = 0
    fn_total = 0
    
    per_type_metrics = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
    
    for gold_path in gold_files:
        base_name = os.path.basename(gold_path)
        pred_path = os.path.join(pred_dir, base_name)
        
        gold_entities = parse_ann(gold_path)
        pred_entities = parse_ann(pred_path)
        
        # Calculate TP, FP, FN for this document
        tp = gold_entities.intersection(pred_entities)
        fp = pred_entities - gold_entities
        fn = gold_entities - pred_entities
        
        tp_total += len(tp)
        fp_total += len(fp)
        fn_total += len(fn)
        
        for label, span, text in tp:
            per_type_metrics[label]["tp"] += 1
        for label, span, text in fp:
            per_type_metrics[label]["fp"] += 1
        for label, span, text in fn:
            per_type_metrics[label]["fn"] += 1

    precision = tp_total / (tp_total + fp_total) if (tp_total + fp_total) > 0 else 0
    recall = tp_total / (tp_total + fn_total) if (tp_total + fn_total) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    print("\n" + "="*50)
    print("BRATEVAL (Python Equivalent) - EXACT MATCHING")
    print("="*50)
    print(f"Total True Positives (TP) : {tp_total}")
    print(f"Total False Positives (FP): {fp_total}")
    print(f"Total False Negatives (FN): {fn_total}")
    print("-" * 50)
    print(f"OVERALL Precision : {precision:.4f}")
    print(f"OVERALL Recall    : {recall:.4f}")
    print(f"OVERALL F1-Score  : {f1:.4f}")
    print("="*50)
    
    print("\nMetrics per Entity Type:")
    for label, metrics in sorted(per_type_metrics.items()):
        tp = metrics["tp"]
        fp = metrics["fp"]
        fn = metrics["fn"]
        p = tp / (tp + fp) if (tp + fp) > 0 else 0
        r = tp / (tp + fn) if (tp + fn) > 0 else 0
        f = 2 * (p * r) / (p + r) if (p + r) > 0 else 0
        print(f" - {label:<15} | P: {p:.4f} | R: {r:.4f} | F1: {f:.4f} | (TP:{tp} FP:{fp} FN:{fn})")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Evaluate BRAT annotations.")
    parser.add_argument("-g", "--gold", required=True, help="Directory with Gold Standard annotations")
    parser.add_argument("-p", "--pred", required=True, help="Directory with Predicted annotations")
    
    args = parser.parse_args()
    evaluate(args.gold, args.pred)
