import csv
import io
import re
import sys
import zipfile
from curl_cffi import requests

# Florida DOS / Sunbiz Public Data Endpoints
SUNBIZ_ZIP_URLS = [
    "https://sftp.floridados.gov/Quarterly/corp_active.zip",
    "https://sftp.floridados.gov/Daily/cordata.zip"
]

SUNBIZ_USER = "Public"
SUNBIZ_PASS = "PubAccess1845!"

HILLSBOROUGH_CITIES = [
    "TAMPA", "BRANDON", "PLANT CITY", "RIVERVIEW", 
    "TEMPLE TERRACE", "VALRICO", "RUSKIN", "APOLLO BEACH", "SEFFNER"
]

TARGET_KEYWORDS = ["TREE", "ARBOR", "TIMBER", "LANDCLEARING", "LOGGING"]

def fetch_sunbiz_data():
    print("Connecting to Sunbiz Public Data Portal...")
    session = requests.Session()
    
    for url in SUNBIZ_ZIP_URLS:
        try:
            print(f"Attempting download from: {url}")
            response = session.get(
                url, 
                auth=(SUNBIZ_USER, SUNBIZ_PASS), 
                stream=True, 
                timeout=180
            )
            
            if response.status_code == 200 and len(response.content) > 1000:
                print(f"Download successful! Size: {len(response.content)} bytes.")
                return response.content
            else:
                print(f"Endpoint returned status code {response.status_code}, trying fallback...")
        except Exception as e:
            print(f"Connection attempt failed for {url}: {e}")

    print("Error: Could not retrieve Sunbiz extract files from any configured endpoint.")
    sys.exit(1)

def parse_and_filter_sunbiz(zip_bytes):
    print("Unpacking data archive in memory...")
    results = []
    
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            for filename in z.namelist():
                print(f"Parsing raw file: {filename}")
                with z.open(filename) as f:
                    for line_bytes in f:
                        line = line_bytes.decode('latin-1', errors='replace')
                        line_upper = line.upper()
                        
                        # 1. Filter by Tree/Arbor keywords
                        if not any(kw in line_upper for kw in TARGET_KEYWORDS):
                            continue
                            
                        # 2. Filter by Hillsborough County cities
                        if not any(city in line_upper for city in HILLSBOROUGH_CITIES):
                            continue
                        
                        # Extract email using regex pattern match
                        email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', line)
                        email = email_match.group(0) if email_match else "N/A"
                        
                        doc_num = line[0:12].strip()
                        entity_name = line[12:192].strip() if len(line) >= 192 else line[12:].strip()
                        city_found = next((city for city in HILLSBOROUGH_CITIES if city in line_upper), "HILLSBOROUGH")
                        
                        results.append({
                            "Document Number": doc_num,
                            "Business Name": entity_name,
                            "City": city_found,
                            "Email": email,
                            "Raw Record": line[:250].strip()
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
