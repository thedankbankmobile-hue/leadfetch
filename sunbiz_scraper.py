import csv
import ftplib
import io
import re
import sys
import tempfile
from curl_cffi import requests

# Florida DOS / Sunbiz Daily Files (Lightweight)
# Daily files contain recent entity filings and load in seconds.
FTP_HOST = "sftp.floridados.gov"
FTP_USER = "Public"
FTP_PASS = "PubAccess1845!"

HILLSBOROUGH_CITIES = [
    "TAMPA", "BRANDON", "PLANT CITY", "RIVERVIEW", 
    "TEMPLE TERRACE", "VALRICO", "RUSKIN", "APOLLO BEACH", "SEFFNER"
]

TARGET_KEYWORDS = ["TREE", "ARBOR", "TIMBER", "LANDCLEARING", "LOGGING"]

def fetch_daily_sunbiz():
    """Fetches smaller daily files via standard web endpoints."""
    print("Attempting fast download of daily Sunbiz filings...")
    
    # We target recent daily dumps which process fast
    urls = [
        "https://sftp.floridados.gov/Public/doc/cor/cordata.txt", # Smaller uncompressed daily stream
        "https://sftp.floridados.gov/Public/doc/quarterly/cor/cordata0.zip", # Partition 0 of split archive
    ]
    
    session = requests.Session()
    headers = {"User-Agent": "Mozilla/5.0"}

    for url in urls:
        try:
            print(f"Connecting to: {url}")
            response = session.get(url, auth=(FTP_USER, FTP_PASS), headers=headers, stream=True, timeout=60)
            
            if response.status_code == 200:
                print("Connection established. Creating temporary buffer...")
                temp_file = tempfile.NamedTemporaryFile(delete=False)
                
                # Stream in 512KB chunks to save RAM
                for chunk in response.iter_content(chunk_size=512 * 1024):
                    if chunk:
                        temp_file.write(chunk)
                        
                temp_file.seek(0)
                print("Download completed successfully!")
                return temp_file
            else:
                print(f"Received HTTP {response.status_code} for {url}")
        except Exception as e:
            print(f"Failed to pull {url}: {e}")
            
    print("Direct HTTPS downloads timed out or failed. Falling back to FTP protocol...")
    return fetch_via_ftp()

def fetch_via_ftp():
    """FTP fallback to bypass web server response limits."""
    try:
        ftp = ftplib.FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)
        ftp.cwd('/Public/doc/cor')
        
        filenames = []
        ftp.retrlines('NLST', filenames.append)
        
        # Grab the newest file in directory
        txt_files = [f for f in filenames if f.endswith('.txt')]
        if not txt_files:
            print("No text files found in FTP directory.")
            sys.exit(1)
            
        target_file = txt_files[-1]
        print(f"Downloading active FTP file: {target_file}")
        
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        ftp.retrbinary(f"RETR {target_file}", temp_file.write)
        temp_file.seek(0)
        ftp.quit()
        return temp_file
    except Exception as e:
        print(f"FTP connection failed: {e}")
        sys.exit(1)

def process_file(temp_file):
    print("Parsing records for Hillsborough Tree Service leads...")
    results = []
    
    with open(temp_file.name, 'r', encoding='latin-1', errors='replace') as f:
        for line in f:
            line_upper = line.upper()
            
            # Quick filter for keywords
            if not any(kw in line_upper for kw in TARGET_KEYWORDS):
                continue
                
            # Quick filter for Hillsborough location
            if not any(city in line_upper for city in HILLSBOROUGH_CITIES):
                continue
            
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
            
    return results

def main():
    temp_file = fetch_daily_sunbiz()
    leads = process_file(temp_file)
    temp_file.close()
    
    print(f"\nExtracted {len(leads)} matching records.")
    
    output_filename = "hillsborough_tree_services_sunbiz.csv"
    fieldnames = ["Document Number", "Business Name", "City", "Email", "Raw Record"]
    
    with open(output_filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(leads)
        
    print(f"Saved dataset to {output_filename}")

if __name__ == "__main__":
    main()
