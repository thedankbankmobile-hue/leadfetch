import os
import csv
import time
import requests
from bs4 import BeautifulSoup
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ==========================================
# CONFIGURATION
# ==========================================
# Google Drive Settings
TARGET_FOLDER_ID = 'YOUR_TARGET_FOLDER_ID_HERE'
SERVICE_ACCOUNT_FILE = 'credentials.json'  # Path to Service Account JSON key

# Sunbiz Multi-Search Targets
INDUSTRIES = [
    'HVAC',
    'PLUMBING',
    'ROOFING',
    'TREE SERVICE',
    'LANDSCAPING',
    'DENTAL'
]

OUTPUT_FILENAME = 'sunbiz_service_firms_leads.csv'

# ==========================================
# 1. GOOGLE DRIVE UPLOAD FUNCTION
# ==========================================
def upload_to_google_drive(file_path, folder_id, credentials_path):
    """Uploads local file directly to specified Google Drive folder."""
    print(f"\n[+] Connecting to Google Drive API...")
    
    scopes = ['https://www.googleapis.com/auth/drive.file']
    creds = Credentials.from_service_account_file(credentials_path, scopes=scopes)
    drive_service = build('drive', 'v3', credentials=creds)

    file_metadata = {
        'name': os.path.basename(file_path),
        'parents': [folder_id]
    }
    media = MediaFileUpload(file_path, mimetype='text/csv', resumable=True)

    print(f"[+] Uploading {file_path} to Folder ID: {folder_id}...")
    uploaded_file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()

    print(f"[SUCCESS] Upload complete! Drive File ID: {uploaded_file.get('id')}")

# ==========================================
# 2. SUNBIZ MULTI-SEARCH SCRAPER
# ==========================================
def scrape_sunbiz_multi_search(industries):
    """Searches Sunbiz across multiple industries and compiles results."""
    base_url = "https://search.sunbiz.org/Inquiry/CorporationSearch/SearchResults"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    all_leads = []

    for industry in industries:
        print(f"[+] Scraping Sunbiz for industry: {industry}...")
        
        # Query Sunbiz search endpoint
        params = {
            'searchTerm': industry,
            'searchType': 'EntityName'
        }

        try:
            response = requests.get(base_url, params=params, headers=headers, timeout=15)
            if response.status_code != 200:
                print(f"[!] Server returned status {response.status_code} for {industry}. Skipping...")
                continue

            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table')

            if not table:
                print(f"[!] No table found for {industry}.")
                continue

            rows = table.find_all('tr')[1:]  # Skip table header
            count = 0

            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 3:
                    entity_name = cols[0].text.strip()
                    doc_number = cols[1].text.strip()
                    status = cols[2].text.strip()

                    all_leads.append({
                        'Industry_Search': industry,
                        'Entity_Name': entity_name,
                        'Document_Number': doc_number,
                        'Status': status
                    })
                    count += 1

            print(f"[+] Extracted {count} records for {industry}.")

        except Exception as e:
            print(f"[ERROR] Failed searching {industry}: {e}")

        # Pause between queries to prevent IP throttling
        time.sleep(2)

    return all_leads

# ==========================================
# 3. MAIN PIPELINE EXECUTION
# ==========================================
def main():
    # Step A: Scrape leads
    leads = scrape_sunbiz_multi_search(INDUSTRIES)

    if not leads:
        print("[!] No leads gathered. Aborting file upload.")
        return

    # Step B: Save locally to CSV
    print(f"\n[+] Writing {len(leads)} leads to {OUTPUT_FILENAME}...")
    fieldnames = ['Industry_Search', 'Entity_Name', 'Document_Number', 'Status']
    
    with open(OUTPUT_FILENAME, mode='w', newline='', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(leads)

    print("[+] Local CSV saved successfully.")

    # Step C: Upload directly to Google Drive folder
    try:
        upload_to_google_drive(OUTPUT_FILENAME, TARGET_FOLDER_ID, SERVICE_ACCOUNT_FILE)
    except Exception as e:
        print(f"[ERROR] Google Drive upload failed: {e}")

if __name__ == "__main__":
    main()
