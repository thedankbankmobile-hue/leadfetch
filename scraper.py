import csv
import io
import requests
import os

SCRAPERAPI_KEY = os.getenv("SCRAPERAPI_KEY")

def run_scraper():
    # Route through ScraperAPI to bypass Cloudflare IP blocks
    target_url = "https://www2.myfloridalicense.com/sto/file_download/extracts/liccon.csv"
    proxy_url = f"http://api.scraperapi.com?api_key={SCRAPERAPI_KEY}&url={target_url}"

    print("Fetching DBPR extract via Residential Proxy...")
    response = requests.get(proxy_url, timeout=120)

    if response.status_code == 200:
        content = response.content.decode('utf-8', errors='ignore')
        reader = csv.reader(io.StringIO(content))
        
        results = []
        for row in reader:
            if len(row) < 14:
                continue
            rank = row[1].strip().upper() if len(row) > 1 else ""
            county = row[9].strip() if len(row) > 9 else ""
            
            if ("CAC" in rank or "RAC" in rank or "AIR" in rank) and county == "39":
                results.append({
                    "Firm/Name": row[3].strip() if len(row) > 3 and row[3].strip() else row[2].strip(),
                    "License Number": row[12].strip() if len(row) > 12 else "N/A",
                    "Phone": row[14].strip() if len(row) > 14 and row[14].strip() else "N/A",
                    "Email": row[15].strip() if len(row) > 15 and "@" in row[15] else "N/A"
                })
        
        with open("hillsborough_hvac_contractors.csv", 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["Firm/Name", "License Number", "Phone", "Email"])
            writer.writeheader()
            writer.writerows(results)
        print(f"Successfully generated CSV with {len(results)} rows.")
    else:
        print(f"Proxy request failed with status: {response.status_code}")

if __name__ == "__main__":
    run_scraper()
