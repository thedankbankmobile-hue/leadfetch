import csv
import io
import requests

# DBPR Official Bulk Extracts Endpoint
DBPR_URL = "https://www2.myfloridalicense.com/sto/file_download/extracts/liccon.csv"

def download_hvac_contractors():
    print("Downloading DBPR database locally...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    res = requests.get(DBPR_URL, headers=headers)
    print(f"Status: {res.status_code}")
    
    if res.status_code != 200:
        print("Failed to access DBPR.")
        return

    content = res.content.decode('utf-8', errors='ignore')
    reader = csv.reader(io.StringIO(content))

    results = []
    for row in reader:
        if len(row) < 14:
            continue
        
        rank = row[1].strip().upper() if len(row) > 1 else ""
        county = row[9].strip() if len(row) > 9 else ""
        
        # Filter: Air Conditioning Contractors (CAC/RAC) in Hillsborough (County 39)
        if ("CAC" in rank or "RAC" in rank or "AIR" in rank) and county == "39":
            results.append({
                "Firm/Name": row[3].strip() if len(row) > 3 and row[3].strip() else row[2].strip(),
                "License Number": row[12].strip() if len(row) > 12 else "N/A",
                "Phone": row[14].strip() if len(row) > 14 and row[14].strip() else "N/A",
                "Email": row[15].strip() if len(row) > 15 and "@" in row[15] else "N/A"
            })

    print(f"Found {len(results)} Hillsborough HVAC records.")
    
    with open("hillsborough_hvac_contractors.csv", 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["Firm/Name", "License Number", "Phone", "Email"])
        writer.writeheader()
        writer.writerows(results)
    
    print("Saved to hillsborough_hvac_contractors.csv!")

if __name__ == "__main__":
    download_hvac_contractors()
