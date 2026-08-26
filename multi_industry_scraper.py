import csv
import os
import sys
import time
from bs4 import BeautifulSoup
from curl_cffi import requests

# Updated Sunbiz Endpoints
BASE_URL = "https://search.sunbiz.org"
SEARCH_URL = f"{BASE_URL}/Inquiry/CorporationSearch/SearchResults"

INDUSTRY_CONFIG = {
    "plumbing": {"output_file": "hillsborough_plumbing_sunbiz.csv", "terms": ["PLUMBING", "PLUMBER"]},
    "hvac": {"output_file": "hillsborough_hvac_sunbiz.csv", "terms": ["HVAC", "AIR CONDITION"]},
    "construction": {"output_file": "hillsborough_construction_sunbiz.csv", "terms": ["CONSTRUCTION", "CONTRACTOR"]},
    "landscape": {"output_file": "hillsborough_landscape_sunbiz.csv", "terms": ["LANDSCAPE", "TREE SERVICE"]},
    "roofing": {"output_file": "hillsborough_roofing_sunbiz.csv", "terms": ["ROOFING", "ROOFER"]},
    "dental": {"output_file": "hillsborough_dental_sunbiz.csv", "terms": ["DENTAL", "DENTISTRY"]},
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
}

def scrape_industry(industry_key):
    if industry_key not in INDUSTRY_CONFIG:
        print(f"[!] Unknown industry: '{industry_key}'.")
        return

    config = INDUSTRY_CONFIG[industry_key]
    print(f"\n==========================================")
    print(f"RUNNING DIRECT TABLE SCRAPER FOR: {industry_key.upper()}")
    print(f"==========================================")

    session = requests.Session()
    results = []
    seen_docs = set()

    for term in config["terms"]:
        print(f"[+] Searching query: '{term}'...")
        params = {
            'searchTerm': term,
            'searchType': 'EntityName'
        }

        try:
            # Fetch the main search results page
            response = session.get(SEARCH_URL, params=params, headers=HEADERS, impersonate="chrome120", timeout=20)
            
            # Detect Cloudflare or Bot Protection Blocks
            if "Cloudflare" in response.text or "Security Check" in response.text:
                 print("    [!] WARNING: GitHub IP blocked by Cloudflare/Bot Protection. Scraping failed.")
                 continue
                 
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the main data table
            table = soup.find('table')
            if not table:
                print(f"    -> HTTP Status {response.status_code}. No data table found in HTML.")
                continue

            rows = table.find_all('tr')[1:]  # Skip the header row
            print(f"    -> Found {len(rows)} potential entity rows.")

            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 3:
                    entity_name = cols[0].text.strip()
                    doc_number = cols[1].text.strip()
                    status = cols[2].text.strip()
                    
                    # Prevent duplicates across search terms
                    if doc_number in seen_docs:
                         continue
                    seen_docs.add(doc_number)

                    print(f"  [+] Match: {entity_name} | {doc_number}")

                    # We save the baseline data directly from the search table
                    results.append({
                        "Document Number": doc_number,
                        "Business Name": entity_name,
                        "Status": status,
                        "Industry Segment": industry_key.upper()
                    })

            time.sleep(2) # Throttle to prevent immediate IP bans

        except Exception as e:
            print(f"[ERROR] Executing search '{term}': {e}")

    output_filename = config["output_file"]
    fieldnames = ["Document Number", "Business Name", "Status", "Industry Segment"]

    with open(output_filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\n[SUMMARY] Finished {industry_key.upper()}: Saved {len(results)} records to {output_filename}")

if __name__ == "__main__":
    target = sys.argv[1].lower() if len(sys.argv) > 1 else "all"
    
    if target == "all":
        for ind in INDUSTRY_CONFIG.keys():
            scrape_industry(ind)
    else:
        scrape_industry(target)
