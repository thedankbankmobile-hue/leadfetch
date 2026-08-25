import csv
import io
import time
from seleniumbase import SB

DBPR_URL = "https://www2.myfloridalicense.com/sto/file_download/extracts/liccon.csv"

def scrape_with_stealth():
    # Launches Google Chrome in Undetected Mode (uc=True)
    with SB(uc=True, headless=True) as sb:
        print("Opening DBPR extract link with stealth browser...")
        sb.uc_open_with_reconnect(DBPR_URL, reconnect_time=4)
        
        # Wait out Cloudflare verification if triggered
        time.sleep(5)
        
        # Retrieve the page content/download stream
        content = sb.get_page_source()
        
        if "Just a moment..." in content or "403 Forbidden" in content:
            print("Cloudflare challenge failed to auto-solve on this runner.")
            return

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

        print(f"Successfully scraped {len(results)} records.")
        with open("hillsborough_hvac_contractors.csv", 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["Firm/Name", "License Number", "Phone", "Email"])
            writer.writeheader()
            writer.writerows(results)

if __name__ == "__main__":
    scrape_with_stealth()
