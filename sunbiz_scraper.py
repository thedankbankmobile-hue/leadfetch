import csv
import re
import sys
import time
from bs4 import BeautifulSoup
from curl_cffi import requests

# Base URLs for Florida Division of Corporations Search
BASE_URL = "https://search.sunbiz.org"
SEARCH_URL = f"{BASE_URL}/Search/Corporation/ByName"

HILLSBOROUGH_CITIES = [
    "TAMPA", "BRANDON", "PLANT CITY", "RIVERVIEW", 
    "TEMPLE TERRACE", "VALRICO", "RUSKIN", "APOLLO BEACH", "SEFFNER"
]

TARGET_TERMS = ["TREE SERVICE", "ARBOR", "TREE CARE", "LAND CLEARING"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def extract_entity_details(detail_url, session):
    """Fetches the entity detail page to extract contact info and email."""
    try:
        resp = session.get(detail_url, headers=HEADERS, impersonate="chrome120", timeout=15)
        if resp.status_code != 200:
            return "N/A", "N/A"
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Search raw page HTML for any valid email address pattern
        email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', resp.text)
        email = email_match.group(0) if email_match else "N/A"
        
        # Extract Principal/Mailing Address block text
        addr_section = soup.find('div', class_='detailSection searchResultDetail')
        address_text = addr_section.get_text(separator=" ").strip() if addr_section else "N/A"
        
        return email, address_text
    except Exception as e:
        print(f"Failed to fetch detail page {detail_url}: {e}")
        return "N/A", "N/A"

def scrape_sunbiz_web():
    print("Starting direct web search extraction from Sunbiz portal...")
    session = requests.Session()
    results = []
    
    for term in TARGET_TERMS:
        print(f"\nSearching keyword: '{term}'...")
        params = {"searchTerm": term}
        
        try:
            response = session.get(SEARCH_URL, params=params, headers=HEADERS, impersonate="chrome120", timeout=20)
            if response.status_code != 200:
                print(f"Search query returned HTTP {response.status_code}")
                continue
                
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table')
            if not table:
                print(f"No results table found for query '{term}'.")
                continue
                
            rows = table.find_all('tr')[1:] # Skip table header
            
            for row in rows:
                cols = row.find_all('td')
                if len(cols) < 3:
                    continue
                    
                entity_name = cols[0].text.strip()
                doc_num = cols[1].text.strip()
                status = cols[2].text.strip().upper()
                
                # Filter for Active businesses only
                if "ACT" not in status:
                    continue
                    
                link_tag = cols[0].find('a')
                if not link_tag or 'href' not in link_tag.attrs:
                    continue
                    
                detail_url = f"{BASE_URL}{link_tag['href']}"
                
                # Fetch detailed filing page
                email, raw_addr = extract_entity_details(detail_url, session)
                raw_addr_upper = raw_addr.upper()
                
                # Filter location for Hillsborough County cities
                matching_city = next((city for city in HILLSBOROUGH_CITIES if city in raw_addr_upper), None)
                if matching_city or "HILLSBOROUGH" in raw_addr_upper:
                    city_label = matching_city if matching_city else "HILLSBOROUGH"
                    print(f" Found Lead: {entity_name} ({city_label}) | Email: {email}")
                    
                    results.append({
                        "Document Number": doc_num,
                        "Business Name": entity_name,
                        "City": city_label,
                        "Email": email,
                        "Raw Address": raw_addr[:200].replace('\n', ' ')
                    })
                
                time.sleep(0.5) # Respectful delay
                
        except Exception as e:
            print(f"Error during search execution for '{term}': {e}")

    print(f"\nFinished processing. Extracted {len(results)} Hillsborough Tree Service leads.")
    
    output_filename = "hillsborough_tree_services_sunbiz.csv"
    fieldnames = ["Document Number", "Business Name", "City", "Email", "Raw Address"]
    
    with open(output_filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
        
    print(f"Saved records to {output_filename}")

if __name__ == "__main__":
    scrape_sunbiz_web()
