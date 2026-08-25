import csv
import io
from curl_cffi import requests

DBPR_URL = "https://www2.myfloridalicense.com/sto/file_download/extracts/liccon.csv"

def fetch_dbpr_data():
    print("Initiating TLS-impersonated fetch for DBPR data...")
    
    # impersonate="chrome120" spoof-authenticates the TLS fingerprint
    response = requests.get(DBPR_URL, impersonate="chrome120", timeout=60)
    
    print(f"HTTP Status Code: {response.status_code}")
    
    if response.status_code != 200:
        print(f"Blocked or Failed. Response preview:\n{response.text[:200]}")
        return

    content = response.content.decode('utf-8', errors='ignore')
    reader = csv.reader(io.StringIO(content))

    results = []
    for row in reader:
        if len(row) < 14:
            continue
        
        rank = row[1].strip().upper() if len(row) > 1 else ""
        county = row[9].strip() if len(row) > 9 else ""
        
        # Filter for HVAC in Hillsborough (County 39)
        if ("CAC" in rank or "RAC" in rank or "AIR" in rank) and county == "39":
            results.append({
                "Firm/Name": row[3].strip() if len(row) > 3 and row[3].strip() else row[2].strip(),
                "License Number": row[12].strip() if len(row) > 12 else "N/A",
                "Phone": row[14].strip() if len(row) > 14 and row[14].strip() else "N/A",
                "Email": row[15].strip() if len(row) > 15 and "@" in row[15] else "N/A"
            })

    print(f"Extracted {len(results)} records.")
    
    with open("hillsborough_hvac_contractors.csv", 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["Firm/Name", "License Number", "Phone", "Email"])
        writer.writeheader()
        writer.writerows(results)

if __name__ == "__main__":
    fetch_dbpr_data()
