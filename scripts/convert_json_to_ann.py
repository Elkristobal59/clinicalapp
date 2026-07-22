import json
import os
import argparse

def convert_json_to_ann(json_file, output_dir):
    """
    Convertit un fichier de prédictions JSON (format Qwen) en fichiers .ann (BRAT)
    pour permettre à Jérémie de comparer visuellement ou avec d'autres outils.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    for item in data:
        nct_id = item['id']
        full_text = item.get('text', '')
        entities = item.get('entities', [])
        
        ann_filepath = os.path.join(output_dir, f"{nct_id}.ann")
        txt_filepath = os.path.join(output_dir, f"{nct_id}.txt")
        
        # Sauvegarde du texte original (requis par BRAT)
        if full_text:
            with open(txt_filepath, 'w', encoding='utf-8') as f_txt:
                f_txt.write(full_text)
                
        with open(ann_filepath, 'w', encoding='utf-8') as f_ann:
            t_id = 1
            for ent in entities:
                ent_type = ent['type']
                ent_text = ent['text']
                
                # Recherche grossière de la position (offset)
                # LLM ne donne pas les offsets, on doit les retrouver dans le texte
                start_idx = full_text.find(ent_text)
                
                if start_idx != -1:
                    end_idx = start_idx + len(ent_text)
                    # Format BRAT : T1\tCondition 12 25\tLung Cancer\n
                    f_ann.write(f"T{t_id}\t{ent_type} {start_idx} {end_idx}\t{ent_text}\n")
                    t_id += 1
                else:
                    # Si le LLM a halluciné un mot ou changé la casse, on le met avec offset 0 0 
                    # pour qu'il apparaisse quand même dans les logs
                    f_ann.write(f"T{t_id}\t{ent_type} 0 0\t{ent_text}\n")
                    t_id += 1
                    
    print(f"✅ Conversion terminée ! Les fichiers .ann sont dans : {output_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convertir JSON en .ann (BRAT)")
    parser.add_argument("--input", "-i", required=True, help="Fichier JSON des prédictions (ex: predictions_qwen.json)")
    parser.add_argument("--output", "-o", default="data/brat_outputs", help="Dossier de sortie des .ann")
    args = parser.parse_args()
    
    convert_json_to_ann(args.input, args.output)
