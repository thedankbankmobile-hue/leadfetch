import csv
import os
import re
import sys
import time
from bs4 import BeautifulSoup
from curl_cffi import requests

BASE_URL = "https://search.sunbiz.org"
SEARCH_URL = f"{BASE_URL}/Inquiry/CorporationSearch/ByName"

HILLSBOROUGH_CITIES = [
    "TAMPA", "BRANDON", "PLANT CITY", "RIVERVIEW", 
    "TEMPLE TERRACE", "VALRICO", "RUSKIN", "APOLLO BEACH", 
    "SEFFNER", "LUTZ", "GIBSONTON", "WIMAUMA", "THONOTOSASSA"
]

INDUSTRY_CONFIG = {
    "plumbing": {
        "output_file": "hillsborough_plumbing_sunbiz.csv",
        "terms": ["PLUMBING", "PLUMBER", "DRAIN", "ROOTER"]
    },
    "hvac": {
        "output_file": "hillsborough_hvac_sunbiz.csv",
        "terms": ["HVAC", "AIR CONDITION", "HEATING AND AIR", "COOLING"]
    },
    "construction": {
        "output_file": "hillsborough_construction_sunbiz.csv",
        "terms": ["CONSTRUCTION", "BUILDERS", "CONTRACTOR", "REMODELING"]
    },
    "landscape": {
        "output_file": "hillsborough_landscape_sunbiz.csv",
        "terms": ["LANDSCAPE", "LANDSCAPING", "LAWN CARE", "TREE SERVICE", "IRRIGATION"]
    },
    "roofing": {
        "output_file": "hillsborough_roofing_sunbiz.csv",
        "terms": ["ROOFING", "ROOFER", "ROOF REPAIR"]
    },
    "dental": {
        "output_file": "hillsborough_dental_sunbiz.csv",
        "terms": ["DENTAL", "DENTISTRY", "DENTIST", "ORTHODONTICS"]
    },
    "electrical": {
        "output_file": "hillsborough_electrical_sunbiz.csv",
        "terms": ["ELECTRIC", "ELECTRICAL", "ELECTRICIAN"]
    },
    "pest_control": {
        "output_file": "hillsborough_pest_control_sunbiz.csv",
        "terms": ["PEST CONTROL", "EXTERMINATING", "TERMITE"]
    },
    "cleaning": {
        "output_file": "hillsborough_cleaning_sunbiz.csv",
        "terms": ["CLEANING", "JANITORIAL", "PRESSURE WASHING", "MAID SERVICE"]
    },
    "auto_repair": {
        "output_file": "hillsborough_auto_repair_sunbiz.csv",
        "terms": ["AUTO REPAIR", "AUTOMOTIVE", "COLLISION", "BODY SHOP", "MECHANIC"]
    },
    "painting": {
        "output_file": "hillsborough_painting_sunbiz.csv",
        "terms": ["PAINTING", "PAINTER", "COATINGS"]
    },
    "pool_services": {
        "output_file": "hillsborough_pool_services_sunbiz.csv",
        "terms": ["POOL SERVICE", "POOL CARE", "POOLS"]
    },
    "moving_storage": {
        "output_file": "hillsborough_moving_storage_sunbiz.csv",
        "terms": ["MOVING", "MOVERS", "STORAGE"]
    },
    "chiro_pt": {
        "output_file": "hillsborough_chiro_pt_sunbiz.csv",
        "terms": ["CHIROPRACTIC", "CHIROPRACTOR", "PHYSICAL THERAPY"]
    },
    "veterinary": {
        "output_file": "hillsborough_veterinary_sunbiz.csv",
        "terms": ["VETERINARY", "ANIMAL HOSPITAL", "PET CARE"]
    },
    "solar": {
        "output_file": "hillsborough_solar_sunbiz.csv",
        "terms": ["SOLAR", "SOLAR ENERGY", "GREEN ENERGY"]
    },
    "towing": {
        "output_file": "hillsborough_towing_sunbiz.csv",
        "terms": ["TOWING", "RECOVERY", "WRECKER"]
    },
    "accounting_cpa": {
        "output_file": "hillsborough_accounting_sunbiz.csv",
        "terms": ["ACCOUNTING", "CPA", "BOOKKEEPING", "TAX SERVICE"]
    }
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

def extract_entity_details(detail_url, session):
    """Fetches entity detail page for address and email extraction."""
    try:
        resp = session.get(detail_url, headers=HEADERS, impersonate="chrome120", timeout=15)
        if resp.status_code != 200:
            return "N/A", "N/A"
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', resp.text)
        email = email_match.group(0) if email_match else "N/A"
        
        addr_sections = soup.find_all('div', class_=re.compile(r'detailSection|searchResultDetail'))
        address_text = " ".join([sec.get_text(separator=" ").strip() for sec in addr_sections]) if addr_sections else soup.get_text()
        
        return email, address_text
    except Exception as e:
        return "N/A", "N/A"

def scrape_industry(industry_key):
    if industry_key not in INDUSTRY_CONFIG:
        print(f"[!] Unknown industry: '{industry_key}'. Available: {list(INDUSTRY_CONFIG.keys())}")
        return

    config = INDUSTRY_CONFIG[industry_key]
    print(f"\n==========================================")
    print(f"RUNNING SCRAPER FOR: {industry_key.upper()}")
    print(f"==========================================")

    session = requests.Session()
    results = []
    seen_docs = set()

    for term in config["terms"]:
        print(f"[+] Searching query: '{term}'...")
        params = {"searchTerm": term}

        try:
            response = session.get(SEARCH_URL, params=params, headers=HEADERS, impersonate="chrome120", timeout=20)
            print(f"    -> HTTP Status: {response.status_code} | Length: {len(response.text)}")
            
            if response.status_code != 200:
                continue

            soup = BeautifulSoup(response.text, 'html.parser')
            detail_links = soup.find_all('a', href=re.compile(r'/Inquiry/CorporationSearch/SearchResultDetail|/Search/Corporation/SearchResultDetail', re.IGNORECASE))
            print(f"    -> Found {len(detail_links)} matching detail links.")

            for link_tag in detail_links:
                entity_name = link_tag.text.strip()
                href = link_tag['href']

                doc_match = re.search(r'inquiryNumber=([A-Z0-9]+)', href, re.IGNORECASE)
                doc_num = doc_match.group(1) if doc_match else "N/A"

                if doc_num in seen_docs and doc_num != "N/A":
                    continue
                if doc_num != "N/A":
                    seen_docs.add(doc_num)

                detail_url = f"{BASE_URL}{href}" if href.startswith('/') else href
                email, raw_addr = extract_entity_details(detail_url, session)
                raw_addr_upper = raw_addr.upper()
                entity_name_upper = entity_name.upper()

                matching_city = next((city for city in HILLSBOROUGH_CITIES if city in raw_addr_upper or city in entity_name_upper), None)

                # Accepts exact city matches, county references, or saves as fallback if address parsing is blocked
                if matching_city or "HILLSBOROUGH" in raw_addr_upper:
                    city_label = matching_city if matching_city else "HILLSBOROUGH"
                    print(f"  [+] Match: {entity_name} ({city_label}) | Email: {email}")

                    results.append({
                        "Document Number": doc_num,
                        "Business Name": entity_name,
                        "City": city_label,
                        "Email": email,
                        "Raw Address": raw_addr[:200].replace('\n', ' ')
                    })
                elif len(raw_addr) < 20: # Fallback when detail page fetch fails
                    results.append({
                        "Document Number": doc_num,
                        "Business Name": entity_name,
                        "City": "FLORIDA (GENERAL)",
                        "Email": email,
                        "Raw Address": "Address details pending"
                    })

                time.sleep(0.2)

        except Exception as e:
            print(f"[ERROR] Executing search '{term}': {e}")

    output_filename = config["output_file"]
    fieldnames = ["Document Number", "Business Name", "City", "Email", "Raw Address"]

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
