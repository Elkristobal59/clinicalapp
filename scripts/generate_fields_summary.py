import requests
import pandas as pd
import argparse
import sys

MODULES = [
    ("protocolSection", "identificationModule", ["nctId", "briefTitle", "officialTitle", "orgStudyIdInfo"]),
    ("protocolSection", "statusModule", ["overallStatus", "startDateStruct", "completionDateStruct"]),
    ("protocolSection", "sponsorCollaboratorsModule", ["leadSponsor", "collaborators", "responsibleParty"]),
    ("protocolSection", "oversightModule", ["oversightHasDmc", "isFdaRegulatedDrug", "isFdaRegulatedDevice"]),
    ("protocolSection", "descriptionModule", ["briefSummary", "detailedDescription"]),
    ("protocolSection", "conditionsModule", ["conditions", "keywords"]),
    ("protocolSection", "designModule", ["studyType", "phases", "designInfo"]),
    ("protocolSection", "armsInterventionsModule", ["armGroups", "interventions"]),
    ("protocolSection", "outcomesModule", ["primaryOutcomes", "secondaryOutcomes"]),
    ("protocolSection", "eligibilityModule", ["eligibilityCriteria", "sex", "minimumAge", "maximumAge"]),
    ("protocolSection", "contactsLocationsModule", ["centralContacts", "overallOfficials", "locations"]),
    ("protocolSection", "referencesModule", ["references", "seeAlsoLinks"]),
    ("resultsSection", "participantFlowModule", ["recruitmentDetails", "preAssignmentDetails", "groups", "periods"]),
    ("resultsSection", "baselineCharacteristicsModule", ["denominators", "measures"]),
    ("resultsSection", "outcomeMeasuresModule", ["outcomeMeasures"]),
    ("resultsSection", "adverseEventsModule", ["timeFrame", "eventGroups", "seriousEvents", "otherEvents"]),
    ("derivedSection", "miscInfoModule", ["versionHolder", "submissionTracking"])
]

def check_module_fields(data, section, module, fields):
    if section not in data:
        return "No"
    
    sec_data = data[section]
    if module not in sec_data:
        return "No"
    
    mod_data = sec_data[module]
    found = 0
    for field in fields:
        if field in mod_data:
            found += 1
            
    if found == len(fields) and len(fields) > 0:
        return "Yes"
    elif found > 0:
        return "Partial"
    else:
        if len(mod_data.keys()) > 0:
            return "Partial"
        return "No"

def main():
    parser = argparse.ArgumentParser(description="Générer une table de résumé des champs ClinicalTrials.gov")
    parser.add_argument("--query", type=str, help="Mot clé de la pathologie (ex: 'Plasma Cell')")
    parser.add_argument("--nct_ids", type=str, help="Liste d'IDs séparés par des virgules (ex: NCT01547806,NCT03047980)")
    parser.add_argument("--output", type=str, default="summary_table.csv", help="Fichier de sortie CSV")
    
    args = parser.parse_args()
    
    if not args.query and not args.nct_ids:
        print("Erreur : Veuillez spécifier --query ou --nct_ids")
        sys.exit(1)
        
    studies = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    if args.query:
        print(f"Recherche des études pour la requête : {args.query}")
        url = f"https://clinicaltrials.gov/api/v2/studies?query.cond={args.query}&pageSize=5"
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code == 200:
                studies_data = resp.json().get("studies", [])
                for s in studies_data:
                    nct_id = s.get("protocolSection", {}).get("identificationModule", {}).get("nctId")
                    if nct_id:
                        studies.append({"id": nct_id, "data": s})
        except Exception as e:
            print(f"Erreur API: {e}")
            sys.exit(1)
            
    elif args.nct_ids:
        ids = [x.strip() for x in args.nct_ids.split(",")]
        for nct_id in ids:
            print(f"Récupération de {nct_id}...")
            url = f"https://clinicaltrials.gov/api/v2/studies/{nct_id}"
            try:
                resp = requests.get(url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    studies.append({"id": nct_id, "data": resp.json()})
            except Exception as e:
                print(f"Erreur API pour {nct_id}: {e}")
                
    if not studies:
        print("Aucune étude trouvée.")
        sys.exit(0)
        
    print(f"{len(studies)} études récupérées. Génération du tableau...")
    df = generate_summary_df(studies)
    df.to_csv(args.output, index=False, sep=";", encoding="utf-8-sig")
    print(f"✅ Tableau généré avec succès dans : {args.output}")

def generate_summary_df(studies):
    """Génère le DataFrame Pandas du résumé des champs à partir d'une liste de dicts {'id': 'NCT...', 'data': JSON}"""
    rows = []
    for section, module, fields in MODULES:
        row = {
            "Section": section,
            "Module": module,
            "Representative Fields": ", ".join(fields)
        }
        for study in studies:
            nct_id = study["id"]
            status = check_module_fields(study["data"], section, module, fields)
            row[nct_id] = status
        rows.append(row)
    return pd.DataFrame(rows)

if __name__ == "__main__":
    main()
