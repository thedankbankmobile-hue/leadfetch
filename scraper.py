import csv
import io
import requests

# Official Florida DBPR Construction License Extract Endpoint
DBPR_URL = "https://www2.myfloridalicense.com/sto/file_download/extracts/liccon.csv"

def run_scraper():
    print("Initiating DBPR Data Download...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    results = []

    try:
        response = requests.get(DBPR_URL, headers=headers, timeout=30)
        print(f"DBPR Response Status Code: {response.status_code}")
        
        if response.status_code == 200:
            content = response.content.decode('utf-8', errors='ignore')
            reader = csv.reader(io.StringIO(content))
            
            for row in reader:
                if len(row) < 14:
                    continue
                
                rank = row[1].strip().upper() if len(row) > 1 else ""
                county = row[9].strip() if len(row) > 9 else ""
                
                # Filter for HVAC (CAC/RAC) in Hillsborough County (County Code 39)
                if ("CAC" in rank or "RAC" in rank or "AIR" in rank) and county == "39":
                    results.append({
                        "Firm/Name": row[3].strip() if len(row) > 3 and row[3].strip() else (row[2].strip() if len(row) > 2 else "N/A"),
                        "License Number": row[12].strip() if len(row) > 12 else "N/A",
                        "Phone": row[14].strip() if len(row) > 14 and row[14].strip() else "N/A",
                        "Email": row[15].strip() if len(row) > 15 and "@" in row[15] else "N/A"
                    })
            print(f"Successfully processed {len(results)} contractor entries.")
        else:
            print(f"Warning: Received HTTP {response.status_code} from DBPR server.")

    except Exception as e:
        print(f"Execution Error during fetch: {e}")

    # Fallback mock row to verify file creation if API is blocked by DBPR firewall
    if not results:
        print("Adding diagnostic entry to verify GitHub workflow tracking...")
        results.append({
            "Firm/Name": "DBPR Direct Connection Blocked (Check Action Logs)",
            "License Number": "N/A",
            "Phone": "N/A",
            "Email": "N/A"
        })

    save_to_csv(results)

def save_to_csv(data, filename="hillsborough_hvac_contractors.csv"):
    keys = ["Firm/Name", "License Number", "Phone", "Email"]
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)
    print(f"Saved output file: {filename}")

if __name__ == "__main__":
    run_scraper()
