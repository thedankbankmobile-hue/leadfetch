import csv
import io
import re
import sys
import zipfile
import tempfile
from curl_cffi import requests

# Florida DOS / Sunbiz Public SFTP Endpoints (including /Public/ root)
SUNBIZ_ZIP_URLS = [
    "https://sftp.floridados.gov/Public/doc/quarterly/cor/cordata.zip",
    "https://sftp.floridados.gov/Public/doc/quarterly/fic/ficdata.zip"
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
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "*/*"
    }
    
    for url in SUNBIZ_ZIP_URLS:
        try:
            print(f"Attempting download from: {url}")
            response = session.get(
                url, 
                auth=(SUNBIZ_USER, SUNBIZ_PASS), 
                headers=headers,
                stream=True, 
                timeout=300
            )
            
            if response.status_code == 200:
                print(f"Connected to {url}. Downloading archive payload...")
                temp_file = tempfile.NamedTemporaryFile(delete=False)
                bytes_downloaded = 0
                
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        temp_file.write(chunk)
                        bytes_downloaded += len(chunk)
                
                temp_file.seek(0)
                print(f"Download complete! Total size: {bytes_downloaded} bytes.")
                return temp_file
            else:
                print(f"HTTP Server returned status code {response.status_code} for {url}")
        except Exception as e:
            print(f"Connection error while fetching {url}: {e}")

    print("Error: Failed to retrieve archive from all Sunbiz endpoints.")
    sys.exit(1)

def parse_and_filter_sunbiz(temp_file):
    print("Extracting and filtering records...")
    results = []
    
    try:
        with zipfile.ZipFile(temp_file.name, 'r') as z:
            for filename in z.namelist():
                print(f"Processing inner archive file: {filename}")
                with z.open(filename) as f:
                    for line_bytes in f:
                        line = line_bytes.decode('latin-1', errors='replace')
                        line_upper = line.upper()
                        
                        # Filter by tree service keywords
                        if not any(kw in line_upper for kw in TARGET_KEYWORDS):
                            continue
                            
                        # Filter by Hillsborough County cities
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
        print(f"Error reading or unzipping Sunbiz extract: {e}")
        sys.exit(1)
        
    return results

def main():
    temp_file = fetch_sunbiz_data()
    leads = parse_and_filter_sunbiz(temp_file)
    temp_file.close()
    
    print(f"\nProcessing complete. Found {len(leads)} matching businesses.")
    
    output_filename = "hillsborough_tree_services_sunbiz.csv"
    fieldnames = ["Document Number", "Business Name", "City", "Email", "Raw Record"]
    
    with open(output_filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(leads)
        
    print(f"Saved leads to {output_filename}")

if __name__ == "__main__":
    main()
