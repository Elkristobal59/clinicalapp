import os
import glob
import json
import psycopg2
from typing import List
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

INPUT_DIR = r"d:\AIFS01\PROJET FINAL\data\processed\chunks_cardio"
NEON_DB_URL = os.getenv("DATABASE_URL")

class ClinicalTrialExtraction(BaseModel):
    condition: str = Field(description="La maladie ciblée.")
    medications: List[str] = Field(description="Médicaments testés.")
    criteria: str = Field(description="Critères d'inclusion/exclusion.")

llm = ChatOpenAI(temperature=0, model_name="gpt-4o-mini")
embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")
parser = PydanticOutputParser(pydantic_object=ClinicalTrialExtraction)

prompt = PromptTemplate(
    template="Extrais les infos:\n{format_instructions}\nTexte:\n{text}\n",
    input_variables=["text"],
    partial_variables={"format_instructions": parser.get_format_instructions()},
)
chain = prompt | llm | parser

def run_extraction():
    if not NEON_DB_URL: return
    conn = psycopg2.connect(NEON_DB_URL)
    cur = conn.cursor()

    for filepath in glob.glob(os.path.join(INPUT_DIR, "*.json"))[:1]:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for chunk in data["chunks"][:5]:
                try:
                    ext = chain.invoke({"text": chunk["text"]})
                    emb = embeddings_model.embed_query(chunk["text"])
                    cur.execute("""
                        INSERT INTO clinical_trials_data 
                        (doc_id, chunk_id, condition, medications, criteria, raw_text, embedding)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (data["document_id"], chunk["chunk_id"], ext.condition, json.dumps(ext.medications), ext.criteria, chunk["text"], emb))
                    conn.commit()
                except Exception as e:
                    conn.rollback()
    cur.close()
    conn.close()

if __name__ == "__main__":
    run_extraction()
