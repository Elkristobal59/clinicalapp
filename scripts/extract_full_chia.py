import json
import re
import os
from datasets import load_dataset

# Liste des 5 études du Holdout annotées par Arnaud (A NE PAS INCLURE)
HOLDOUT_NCT = {"NCT02145403", "NCT02541383", "NCT03346538", "NCT04676152", "NCT04915729"}

# Les 9 entités "Cœur métier" que nous voulons extraire
TARGET_ENTITIES = {
    "Condition", "Drug", "Procedure", "Measurement", 
    "Value", "Temporal", "Observation", "Person", "Device"
}

def main():
    print("Chargement du dataset CHIA depuis HuggingFace (bigbio/chia)...")
    try:
        ds = load_dataset("bigbio/chia", "chia_bigbio_kb", split="train", trust_remote_code=True)
    except TypeError:
        ds = load_dataset("bigbio/chia", "chia_bigbio_kb", split="train")

    dataset_v2 = []
    
    print("Filtrage des études et extraction des entités...")
    for ex in ds:
        # Récupération de l'ID du document
        doc_id = ex.get("document_id") or ex.get("id") or ""
        
        # Trouver le NCT ID (ex: NCT01410890)
        m = re.search(r"NCT\d+", doc_id)
        if not m:
            continue
            
        nct_id = m.group(0)
        
        # SÉCURITÉ ANTI-LEAKAGE : On ignore l'étude si elle fait partie du Holdout d'Arnaud
        if nct_id in HOLDOUT_NCT:
            print(f"⚠️  Étude {nct_id} ignorée (Réservée pour le Holdout Set d'Arnaud)")
            continue

        # BIGBIO FIX : Le texte est dans "passages" et non dans "text"
        passages = ex.get("passages", [])
        text_list = passages[0].get("text") if passages else ex.get("text")
        
        if not text_list:
            continue
            
        # Parfois text est une liste de chaînes de caractères
        source_text = " ".join(text_list) if isinstance(text_list, list) else text_list

        entities = []
        for e in ex.get("entities", []):
            label_raw = e.get("type")
            label = label_raw[0] if isinstance(label_raw, list) and len(label_raw) > 0 else label_raw
            
            if label not in TARGET_ENTITIES:
                continue
                
            # Les offsets sont souvent sous forme de liste de listes dans bigbio : [[start, end]]
            offsets = e.get("offsets", [])
            if not offsets:
                continue
            
            start_offset = offsets[0][0]
            end_offset = offsets[0][1]
            
            # Le texte de l'entité
            ent_text_list = e.get("text", [])
            ent_text = " ".join(ent_text_list) if isinstance(ent_text_list, list) else ent_text_list
            
            entities.append({
                "id": e.get("id"),
                "label": label,
                "text": ent_text,
                "start_offset": start_offset,
                "end_offset": end_offset
            })
            
        # Ne garder que les documents qui ont au moins une entité cible
        if entities:
            dataset_v2.append({
                "file": doc_id,
                "text": source_text,
                "entities": entities
            })

    output_path = os.path.join("data", "chia_gold_standard_v2.json")
    print(f"\nExtraction terminée. {len(dataset_v2)} sous-documents conservés (hors Holdout).")
    
    # Création du dossier si inexistant
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dataset_v2, f, indent=4, ensure_ascii=False)
        
    print(f"✅ Fichier sauvegardé : {output_path}")

if __name__ == "__main__":
    main()
