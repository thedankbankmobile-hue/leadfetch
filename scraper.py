import csv
import io
import requests

# DBPR Official Public Licensee Extract for Construction Industry
DBPR_BULK_URL = "https://www2.myfloridalicense.com/sto/file_download/extracts/liccon.csv"

def download_and_filter_hvac_contractors():
    print("Downloading official DBPR construction licensee database...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(DBPR_BULK_URL, headers=headers, stream=True, timeout=60)
        response.raise_for_status()
    except Exception as e:
        print(f"Error downloading state database: {e}")
        return []

    print("Processing state records for Hillsborough County HVAC contractors...")
    results = []
    
    # DBPR File Layout indexes:
    # 0: Board, 1: Rank/Class, 2: License Name, 3: DBA Name, 4: Address 1, 
    # 5: Address 2, 6: City, 7: State, 8: Zip, 9: County Code (39 = Hillsborough), 
    # 12: License Number, 13: Primary Status, 14: Phone, 15: Email
    
    content = response.content.decode('utf-8', errors='ignore')
    reader = csv.reader(io.StringIO(content))

    for row in reader:
        if len(row) < 15:
            continue
            
        rank = row[1].strip().upper() if len(row) > 1 else ""
        county = row[9].strip() if len(row) > 9 else ""
        status = row[13].strip().upper() if len(row) > 13 else ""

        # CAC = Certified Air Conditioning, RAC = Registered Air Conditioning
        # County Code 39 = Hillsborough County
        if ("CAC" in rank or "RAC" in rank or "AIR COND" in rank) and (county == "39" or "HILLSBOROUGH" in row[6].upper()):
            if "ACT" in status or "CURRENT" in status:
                firm_name = row[3].strip() if row[3].strip() else row[2].strip()
                phone = row[14].strip() if len(row) > 14 and row[14].strip() else "N/A"
                email = row[15].strip() if len(row) > 15 and "@" in row[15] else "N/A"
                lic_num = row[12].strip() if len(row) > 12 else "N/A"

                results.append({
                    "Firm/Name": firm_name,
                    "License Number": lic_num,
                    "Phone": phone,
                    "Email": email
                })

    print(f"Extraction complete. Found {len(results)} Hillsborough HVAC contractors.")
    return results

def save_to_csv(data, filename="hillsborough_hvac_contractors.csv"):
    keys = ["Firm/Name", "License Number", "Phone", "Email"]
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        if data:
            writer.writerows(data)
    print(f"Saved populated records to {filename}")

if __name__ == "__main__":
    contractors = download_and_filter_hvac_contractors()
    save_to_csv(contractors)
