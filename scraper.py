import csv
import io
from curl_cffi import requests

DBPR_URL = "https://www2.myfloridalicense.com/sto/file_download/extracts/liccon.csv"

def run_broad_scraper():
    print("Fetching DBPR file...")
    res = requests.get(DBPR_URL, impersonate="chrome120", timeout=60)
    
    if res.status_code != 200:
        print(f"Fetch failed with HTTP {res.status_code}")
        return

    content = res.content.decode('utf-8', errors='ignore')
    reader = csv.reader(io.StringIO(content))
    
    results = []
    
    for row in reader:
        if len(row) < 5:
            continue
            
        row_upper = [str(cell).strip().upper() for cell in row]
        row_text = " ".join(row_upper)
        
        # Check for Hillsborough (code 39, padded 039, or explicit county name)
        in_hillsborough = ("39" in row_upper) or ("039" in row_upper) or ("HILLSBOROUGH" in row_text)
        
        # Check for HVAC rank/license identifiers
        is_hvac = any(term in row_text for term in ["CAC", "RAC", "AIR CONDITIONING", "AIR COND"])
        
        if in_hillsborough and is_hvac:
            # Safely grab fields across variable column layouts
            name = row[3].strip() if len(row) > 3 and row[3].strip() else (row[2].strip() if len(row) > 2 else "N/A")
            lic_num = row[12].strip() if len(row) > 12 else "N/A"
            phone = row[14].strip() if len(row) > 14 and row[14].strip() else "N/A"
            email = row[15].strip() if len(row) > 15 and "@" in row[15] else "N/A"
            
            results.append({
                "Firm/Name": name,
                "License Number": lic_num,
                "Phone": phone,
                "Email": email
            })

    print(f"Successfully matched and saved {len(results)} contractors.")

    with open("hillsborough_hvac_contractors.csv", 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["Firm/Name", "License Number", "Phone", "Email"])
        writer.writeheader()
        writer.writerows(results)

if __name__ == "__main__":
    run_broad_scraper()
