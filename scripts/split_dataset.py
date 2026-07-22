import json
import random
import os

# Reproductibilité du split
random.seed(42)

def convert_to_chatml(doc_dict):
    """
    Convertit un dictionnaire document (text + entities) au format conversationnel (ChatML).
    """
    text = doc_dict["text"]
    entities = doc_dict["entities"]
    
    # Prompt utilisateur (instruction + texte source)
    user_prompt = f"Extract all relevant clinical entities from the following text and format them as JSON. The allowed entity types are: Condition, Drug, Procedure, Measurement, Value, Temporal, Observation, Person, Device.\n\nText: {text}"
    
    # Formatage de la réponse attendue en JSON propre
    expected_output = []
    for ent in entities:
        expected_output.append({
            "entity": ent["text"],
            "label": ent["label"]
        })
        
    assistant_response = json.dumps(expected_output, ensure_ascii=False)
    
    # Structure ChatML (OpenAI/Qwen)
    chat_format = {
        "messages": [
            {"role": "system", "content": "You are a medical AI assistant specialized in clinical trial named entity recognition (NER). You extract key entities precisely and format them in JSON."},
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": assistant_response}
        ]
    }
    
    return chat_format

def main():
    input_path = os.path.join("data", "chia_gold_standard_v2.json")
    
    if not os.path.exists(input_path):
        print(f"❌ Erreur : {input_path} est introuvable. Lancez extract_full_chia.py d'abord.")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        dataset_v2 = json.load(f)
        
    print(f"Chargement de {len(dataset_v2)} blocs de texte (chunks).")
    
    # Il est CRUCIAL de faire le split par 'NCT ID' et non par bloc de texte (chunk).
    # Si on split par chunk, des paragraphes de la même étude pourraient se retrouver 
    # à la fois dans le Train et le Test, créant une fuite de données (Data Leakage).
    
    studies = {} # Dictionnaire { "NCT_ID": [liste_des_chunks] }
    for doc in dataset_v2:
        # doc["file"] ressemble souvent à "NCT01410890_exc" ou "NCT01410890_inc"
        nct_id = doc["file"].split("_")[0]
        if nct_id not in studies:
            studies[nct_id] = []
        studies[nct_id].append(doc)
        
    unique_nct = list(studies.keys())
    print(f"Nombre total d'études uniques (NCT IDs) : {len(unique_nct)}")
    
    # Mélange aléatoire (seed fixé pour reproductibilité)
    random.shuffle(unique_nct)
    
    # Split 80% / 20%
    split_index = int(len(unique_nct) * 0.8)
    train_ncts = unique_nct[:split_index]
    test_ncts = unique_nct[split_index:]
    
    print(f"Répartition : {len(train_ncts)} études pour le Train, {len(test_ncts)} études pour le Test.")
    
    # Rassembler les chunks et les convertir en ChatML
    train_chatml = []
    for nct in train_ncts:
        for chunk in studies[nct]:
            train_chatml.append(convert_to_chatml(chunk))
            
    test_chatml = []
    for nct in test_ncts:
        for chunk in studies[nct]:
            test_chatml.append(convert_to_chatml(chunk))
            
    # Sauvegarde des fichiers JSONL
    train_path = os.path.join("data", "train_dataset.jsonl")
    test_path = os.path.join("data", "test_dataset.jsonl")
    
    with open(train_path, "w", encoding="utf-8") as f:
        for item in train_chatml:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            
    with open(test_path, "w", encoding="utf-8") as f:
        for item in test_chatml:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            
    print("\n✅ Fichiers JSONL générés avec succès :")
    print(f" - {train_path} ({len(train_chatml)} exemples)")
    print(f" - {test_path} ({len(test_chatml)} exemples)")

if __name__ == "__main__":
    main()
