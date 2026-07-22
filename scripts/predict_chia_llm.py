import os
import glob
import json
from typing import List
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()

class Entity(BaseModel):
    type: str = Field(description="Type d'entité, doit être l'un de : 'Condition', 'Drug', 'Procedure', 'Measurement', 'Observation', 'Person', 'Device', 'Qualifier', 'Multiplier', 'Reference_point', 'Temporal', 'Value'")
    text: str = Field(description="Le texte exact extrait du document source")

class DocumentEntities(BaseModel):
    entities: List[Entity]

llm = ChatGoogleGenerativeAI(temperature=0, model="gemini-flash-lite-latest")
parser = PydanticOutputParser(pydantic_object=DocumentEntities)

prompt = PromptTemplate(
    template="Tu es un expert médical. Extrais toutes les entités nommées cliniques du texte d'éligibilité clinique suivant.\n\nInstructions de formatage:\n{format_instructions}\n\nTexte:\n{text}\n",
    input_variables=["text"],
    partial_variables={"format_instructions": parser.get_format_instructions()},
)

chain = prompt | llm | parser

def process_study(nct_id, text):
    try:
        # truncate text if it's too long, but usually eligibility criteria are short
        ext = chain.invoke({"text": text[:15000]})
        
        entities_list = []
        for ent in ext.entities:
            entities_list.append({
                "type": ent.type,
                "text": ent.text
            })
            
        return {
            "id": nct_id,
            "entities": entities_list
        }
    except Exception as e:
        print(f"Error processing {nct_id}: {e}")
        return {
            "id": nct_id,
            "entities": []
        }

def run_predictions(data_dir, output_file, max_studies=10):
    txt_files = glob.glob(os.path.join(data_dir, "*.txt"))
    
    # Group txt files by study (we have _inc.txt and _exc.txt)
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
            
    # Take a subset if requested
    study_items = list(study_texts.items())[:max_studies]
    print(f"Processing {len(study_items)} studies with GPT-4o-mini...")
    
    predictions = []
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(process_study, nct, text): nct for nct, text in study_items}
        
        for idx, future in enumerate(as_completed(futures), 1):
            result = future.result()
            predictions.append(result)
            print(f"Processed {idx}/{len(study_items)} : {result['id']} ({len(result['entities'])} entities found)")
            
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(predictions, f, indent=4, ensure_ascii=False)
        
    print(f"Predictions saved to {output_file}")

if __name__ == "__main__":
    DATA_DIR = r"d:\AIFS01\PROJET FINAL\stack_equipe\data\chia_pdfs"
    OUTPUT_FILE = r"d:\AIFS01\PROJET FINAL\stack_equipe\data\chia_predictions.json"
    
    # Process 10 studies for the initial benchmark test
    run_predictions(DATA_DIR, OUTPUT_FILE, max_studies=10)
