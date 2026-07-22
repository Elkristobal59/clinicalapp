import os
import zipfile
import glob
import re
import io
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

def get_chia_ncts(zip_path):
    chia_ncts = set()
    try:
        with zipfile.ZipFile(zip_path, 'r') as outer_zip:
            # We want chia_without_scope to avoid duplicates if possible, or just parse both
            inner_zip_name = 'chia_without_scope.zip'
            if inner_zip_name in outer_zip.namelist():
                inner_zip_data = outer_zip.read(inner_zip_name)
                with zipfile.ZipFile(io.BytesIO(inner_zip_data), 'r') as inner_zip:
                    for file_info in inner_zip.infolist():
                        basename = os.path.basename(file_info.filename)
                        match = re.search(r"(NCT\d+)", basename)
                        if match:
                            chia_ncts.add(match.group(1))
    except Exception as e:
        print(f"Error reading zip: {e}")
    return list(chia_ncts)

def fetch_study_pdf(nct, output_dir):
    try:
        url = f"https://clinicaltrials.gov/api/v2/studies/{nct}"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return nct, False, f"API Error: {resp.status_code}"
            
        data = resp.json()
        doc_section = data.get("documentSection", {}).get("largeDocumentModule", {})
        large_docs = doc_section.get("largeDocs", [])
        
        # Find a protocol document
        target_doc = None
        for doc in large_docs:
            if doc.get("hasProtocol", False) or "Prot" in doc.get("typeAbbrev", ""):
                target_doc = doc
                break
                
        if not target_doc:
            return nct, False, "No protocol document found"
            
        filename = target_doc.get("filename")
        if not filename:
            return nct, False, "Document has no filename"
            
        # Download the document
        last_two = nct[-2:]
        download_url = f"https://clinicaltrials.gov/ProvidedDocs/{last_two}/{nct}/{filename}"
        
        pdf_path = os.path.join(output_dir, f"{nct}_{filename}")
        if os.path.exists(pdf_path):
            return nct, True, "Already downloaded"
            
        doc_resp = requests.get(download_url, stream=True, allow_redirects=True, timeout=15)
        if doc_resp.status_code == 200:
            with open(pdf_path, 'wb') as f:
                for chunk in doc_resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            return nct, True, "Downloaded successfully"
        else:
            return nct, False, f"Download failed: {doc_resp.status_code}"
            
    except Exception as e:
        return nct, False, f"Exception: {e}"

def main():
    zip_path = r"d:\AIFS01\PROJET FINAL\stack_equipe\docs\11855817.zip"
    output_dir = r"d:\AIFS01\PROJET FINAL\stack_equipe\data\chia_pdfs"
    
    os.makedirs(output_dir, exist_ok=True)
    
    ncts = get_chia_ncts(zip_path)
    print(f"Total NCTs in CHIA: {len(ncts)}")
    
    success_count = 0
    fail_count = 0
    
    print("Fetching metadata and PDFs. This will take a moment...")
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(fetch_study_pdf, nct, output_dir): nct for nct in ncts}
        
        for i, future in enumerate(as_completed(futures), 1):
            nct, success, msg = future.result()
            if success:
                success_count += 1
                if "Already downloaded" not in msg:
                    print(f"[{i}/{len(ncts)}] {nct} -> SUCCESS")
            else:
                fail_count += 1
                # print(f"[{i}/{len(ncts)}] {nct} -> skipped ({msg})")
                
            if i % 50 == 0:
                print(f"Progress: {i}/{len(ncts)} processed. Found {success_count} PDFs so far.")
                
    print(f"\nFinished! Downloaded {success_count} PDFs out of {len(ncts)} CHIA studies.")

if __name__ == "__main__":
    main()
