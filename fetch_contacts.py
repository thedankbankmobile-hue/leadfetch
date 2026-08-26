import os
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup

# Output file path in current workspace
OUTPUT_CSV = "hillsborough_plumbing_contacts.csv"

# Optional: Place Google Places API key here for phone numbers/websites
GOOGLE_PLACES_API_KEY = ""

# Hardcoded entity list from your CSV dataset to avoid file loading issues
COMPANIES = [
    {"doc": "P25000013085", "name": "PLUMBING CORP.", "status": "Active", "segment": "PLUMBING"},
    {"doc": "P22000047573", "name": "PLUMBING 1 CORP", "status": "Active", "segment": "PLUMBING"},
    {"doc": "L25000393550", "name": "PLUMBING 101, LLC", "status": "Active", "segment": "PLUMBING"},
    {"doc": "P25000014635", "name": "PLUMBING 24 SERVICE, INC.", "status": "Active", "segment": "PLUMBING"},
    {"doc": "L25000134305", "name": "PLUMBING 25 LLC", "status": "Active", "segment": "PLUMBING"},
    {"doc": "M26000005466", "name": "PLUMBING 2 PERFECTION, LLC", "status": "Active", "segment": "PLUMBING"},
    {"doc": "L25000099109", "name": "PLUMBING305 LLC", "status": "Active", "segment": "PLUMBING"},
    {"doc": "P20000075762", "name": "PLUMBING 411, CORP.", "status": "Active", "segment": "PLUMBING"},
    {"doc": "L15000053807", "name": 'THE PLUMB E.R. "LLC"', "status": "Active", "segment": "PLUMBING"},
    {"doc": "L23000135672", "name": "THE PLUMBER, LLC", "status": "Active", "segment": "PLUMBING"},
    {"doc": "L21000165095", "name": "PLUMBER 24/7, LLC", "status": "Active", "segment": "PLUMBING"},
    {"doc": "L22000509242", "name": "PLUMBER941 LLC", "status": "Active", "segment": "PLUMBING"},
    {"doc": "L26000175460", "name": "PLUMBER AROUND ME LLC", "status": "Active", "segment": "PLUMBING"},
    {"doc": "L15000012570", "name": "PLUMBER DAVE LLC", "status": "Active", "segment": "PLUMBING"},
    {"doc": "L26000429009", "name": "PLUMB-ER OF FLORIDA LLC", "status": "Active", "segment": "PLUMBING"},
    {"doc": "L25000079431", "name": "THE PLUMBER GUYS LLC", "status": "Active", "segment": "PLUMBING"}
]

def scrape_sunbiz_by_doc_num(doc_num):
    sunbiz_url = f"https://search.sunbiz.org/Inquiry/CorporationSearch/SearchResultDetail?inquiryType=DocumentNumber&searchTerm={doc_num}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(sunbiz_url, headers=headers, timeout=10)
        if response.status_code != 200:
            return {}
        
        soup = BeautifulSoup(response.text, 'html.parser')
        data = {}

        addr_headers = soup.find_all('span', class_='detail-section-header')
        for header in addr_headers:
            header_text = header.get_text(strip=True).upper()
            
            if 'PRINCIPAL ADDRESS' in header_text:
                addr_div = header.find_next_sibling('div', class_='detail-section')
                if addr_div:
                    data['Principal Address'] = " ".join(addr_div.get_text(separator=" ", strip=True).split())
            
            elif 'MAILING ADDRESS' in header_text:
                addr_div = header.find_next_sibling('div', class_='detail-section')
                if addr_div:
                    data['Mailing Address'] = " ".join(addr_div.get_text(separator=" ", strip=True).split())

            elif 'REGISTERED AGENT' in header_text:
                agent_div = header.find_next_sibling('div', class_='detail-section')
                if agent_div:
                    data['Registered Agent'] = " ".join(agent_div.get_text(separator=" ", strip=True).split())

        return data
    except Exception as e:
        print(f"Error fetching {doc_num}: {e}")
        return {}

def fetch_google_places_info(business_name, api_key):
    if not api_key:
        return {}
    endpoint = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {"query": f"{business_name} Hillsborough County FL", "key": api_key}
    try:
        res = requests.get(endpoint, params=params).json()
        if res.get("results"):
            place_id = res["results"][0].get("place_id")
            details_endpoint = "https://maps.googleapis.com/maps/api/place/details/json"
            details_params = {"place_id": place_id, "fields": "formatted_phone_number,website", "key": api_key}
            details_res = requests.get(details_endpoint, params=details_params).json()
            result = details_res.get("result", {})
            return {
                "Phone": result.get("formatted_phone_number", ""),
                "Website": result.get("website", "")
            }
    except Exception as e:
        print(f"Google Places lookup failed for {business_name}: {e}")
    return {}

def main():
    records = []
    total = len(COMPANIES)
    print(f"Processing {total} business records...")

    for idx, item in enumerate(COMPANIES, 1):
        doc_num = item["doc"]
        name = item["name"]
        print(f"[{idx}/{total}] Fetching Sunbiz details for: {name} ({doc_num})...")
        
        sunbiz_info = scrape_sunbiz_by_doc_num(doc_num)
        places_info = fetch_google_places_info(name, GOOGLE_PLACES_API_KEY)
        
        row = {
            "Document Number": doc_num,
            "Business Name": name,
            "Status": item["status"],
            "Industry Segment": item["segment"],
            "Principal Address": sunbiz_info.get("Principal Address", "N/A"),
            "Mailing Address": sunbiz_info.get("Mailing Address", "N/A"),
            "Registered Agent": sunbiz_info.get("Registered Agent", "N/A")
        }

        if GOOGLE_PLACES_API_KEY:
            row["Phone"] = places_info.get("Phone", "")
            row["Website"] = places_info.get("Website", "")

        records.append(row)
        time.sleep(1)

    out_df = pd.DataFrame(records)
    out_df.to_csv(OUTPUT_CSV, index=False)
    print(f"\nSuccessfully generated '{OUTPUT_CSV}'.")

if __name__ == "__main__":
    main()