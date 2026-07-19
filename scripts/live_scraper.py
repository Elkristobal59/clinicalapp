import os
from playwright.sync_api import sync_playwright
import time

def run_scraper(condition: str, max_results: int = 5) -> str:
    """
    Scrape en direct les PDFs de ClinicalTrials.gov pour une condition donnée.
    Retourne le chemin du dossier contenant les PDFs téléchargés.
    """
    output_dir = os.path.abspath(f"d:\\AIFS01\\PROJET FINAL\\poc_solo\\data\\live_pdfs_{condition.replace(' ', '_')}")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Note: Dans un environnement réel, on utiliserait l'API de ClinicalTrials.
    # Ici, nous simulons la logique d'extraction furtive avec Playwright
    # (Adaptation du script original pour la démo temps réel)
    
    if condition.lower() == "cardiology":
        print("Scraping simulé (utilisation du cache existant pour la rapidité)")
        return "d:\\AIFS01\\PROJET FINAL\\data\\real_pdfs\\playwright_cardio_100"
    
    import threading
    if threading.current_thread() != threading.main_thread():
        # Streamlit lance les callbacks dans des threads séparés, ce qui fait planter l'asyncio de Playwright
        print(f"Lancement de Playwright via subprocess pour '{condition}'...")
        import subprocess, sys
        subprocess.run([sys.executable, __file__, condition, str(max_results)])
        return output_dir

    print(f"Lancement de Playwright pour scrapper {max_results} essais sur '{condition}'...")
    
    import requests
    downloaded_count = 0
    page_token = None
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            url = f"https://clinicaltrials.gov/api/v2/studies?query.cond={condition}&pageSize=100&fields=NCTId,DocumentSection"
            
            while downloaded_count < max_results:
                current_url = url
                if page_token:
                    current_url += f"&pageToken={page_token}"
                    
                print("Recherche de protocoles avec PDF via l'API...")
                try:
                    response = requests.get(current_url, timeout=10)
                    data = response.json()
                except Exception as e:
                    print(f"Erreur API: {e}")
                    break
                    
                studies = data.get("studies", [])
                if not studies:
                    break
                    
                for study in studies:
                    nct_id = study.get("protocolSection", {}).get("identificationModule", {}).get("nctId")
                    docs = study.get("documentSection", {}).get("largeDocumentModule", {}).get("largeDocs", [])
                    
                    has_pdf = False
                    for doc in docs:
                        filename = doc.get("filename", "")
                        if filename.lower().endswith(".pdf"):
                            has_pdf = True
                            break
                            
                    if not has_pdf:
                        continue
                        
                    study_url = f"https://clinicaltrials.gov/study/{nct_id}"
                    print(f"[{downloaded_count+1}/{max_results}] Téléchargement du PDF pour l'essai {nct_id}...")
                    
                    try:
                        page.goto(study_url, wait_until="networkidle", timeout=30000)
                        links = page.locator("a")
                        count = links.count()
                        
                        pdf_downloaded = False
                        for i in range(count):
                            href = links.nth(i).get_attribute("href")
                            if href and (".pdf" in href.lower() or "large-docs" in href.lower()):
                                try:
                                    with page.expect_download(timeout=15000) as download_info:
                                        links.nth(i).click(force=True)
                                    download = download_info.value
                                    
                                    safe_name = download.suggested_filename
                                    if not safe_name.endswith(".pdf"):
                                        safe_name += ".pdf"
                                        
                                    filepath = os.path.join(output_dir, f"{nct_id}_{safe_name}")
                                    download.save_as(filepath)
                                    
                                    pdf_downloaded = True
                                    downloaded_count += 1
                                    break 
                                except Exception:
                                    pass 
                                    
                        if downloaded_count >= max_results:
                            break
                            
                    except Exception as e:
                        print(f"Erreur chargement page {nct_id}: {e}")
                        
                if downloaded_count >= max_results:
                    break
                    
                page_token = data.get("nextPageToken")
                if not page_token:
                    break
        
            browser.close()
    except Exception as e:
        print(f"Erreur globale scraping : {e}")

    return output_dir

if __name__ == "__main__":
    import sys
    cond = sys.argv[1] if len(sys.argv) > 1 else "Breast Cancer"
    m_res = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    run_scraper(cond, m_res)
