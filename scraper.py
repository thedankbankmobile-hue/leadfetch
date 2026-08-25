import csv
import io
import re
import sys
import zipfile
from curl_cffi import requests

# Florida DOS / Sunbiz Public SFTP Web Portal Endpoint
SUNBIZ_PORTAL_URL = "https://sftp.floridados.gov"
# Standard public credentials provided by FL DOS
SUNBIZ_USER = "Public"
SUNBIZ_PASS = "PubAccess1845!"

# Hillsborough County Cities & Top Target Keywords
HILLSBOROUGH_CITIES = [
    "TAMPA", "BRANDON", "PLANT CITY", "RIVERVIEW", 
    "TEMPLE TERRACE", "VALRICO", "RUSKIN", "APOLLO BEACH", "SEFFNER"
]

TARGET_KEYWORDS = ["TREE", "ARBOR", "TIMBER", "LANDCLEARING", "LOGGING"]

def fetch_sunbiz_data():
    print("Connecting to Sunbiz Public Data Portal...")
    session = requests.Session()
    
    # 1. Direct file link for active corporate entity data extract
    # Alternate direct HTTP stream path hosted by DOS for public automated dumps:
    direct_file_url = "https://sftp.floridados.gov/Quarterly/corp_active.zip"
    
    try:
        response = session.get(
            direct_file_url, 
            auth=(SUNBIZ_USER, SUNBIZ_PASS), 
            stream=True, 
            timeout=120
        )
        
        if response.status_code != 200:
            # Fallback to daily incremental file if quarterly zip is undergoing maintenance
            print("Quarterly archive unavailable, trying daily active batch...")
            direct_file_url = "https://sftp.floridados.gov/Daily/cordata.zip"
            response = session.get(direct_file_url, auth=(SUNBIZ_USER, SUNBIZ_PASS), stream=True, timeout=120)
            
        print(f"Download stream established. Status code: {response.status_code}")
        return response.content
    except Exception as e:
        print(f"Failed to retrieve file from Sunbiz: {e}")
        sys.exit(1)

def parse_and_filter_sunbiz(zip_bytes):
    print("Unpacking data archive in memory...")
    results = []
    
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            for filename in z.namelist():
                print(f"Parsing raw text file: {filename}")
                with z.open(filename) as f:
                    # Sunbiz data files use CP1252/Latin-1 encoding
                    for line_bytes in f:
                        line = line_bytes.decode('latin-1', errors='replace')
                        line_upper = line.upper()
                        
                        # Step 1: Fast string scan for Tree keywords
                        if not any(kw in line_upper for kw in TARGET_KEYWORDS):
                            continue
                            
                        # Step 2: Ensure location matches Hillsborough County cities
                        if not any(city in line_upper for city in HILLSBOROUGH_CITIES):
                            continue
                        
                        # Extract email using pattern match on the fixed record line
                        email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', line)
                        email = email_match.group(0) if email_match else "N/A"
                        
                        # Sunbiz Fixed-Width Standard Layout Parsing:
                        # Document ID: [0:12], Entity Name: [12:192], Status: [192:198]
                        doc_num = line[0:12].strip()
                        entity_name = line[12:192].strip() if len(line) >= 192 else line[12:].strip()
                        
                        # Extract city/zip context from tail of record line
                        city_found = next((city for city in HILLSBOROUGH_CITIES if city in line_upper), "HILLSBOROUGH")
                        
                        results.append({
                            "Document Number": doc_num,
                            "Business Name": entity_name,
                            "City": city_found,
                            "Email": email,
                            "Raw Record": line[:250].strip() # Backup preview of address fields
                        })
                        
    except Exception as e:
        print(f"Error parsing Sunbiz zip extract: {e}")
        sys.exit(1)
        
    return results

def main():
    zip_bytes = fetch_sunbiz_data()
    leads = parse_and_filter_sunbiz(zip_bytes)
    
    print(f"\nProcessing finished. Found {len(leads)} matching tree service businesses in Hillsborough.")
    
    output_filename = "hillsborough_tree_services_sunbiz.csv"
    fieldnames = ["Document Number", "Business Name", "City", "Email", "Raw Record"]
    
    with open(output_filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(leads)
        
    print(f"Saved results to {output_filename}")

if __name__ == "__main__":
    main()
