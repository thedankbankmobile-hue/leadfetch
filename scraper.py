import csv
import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

def scrape_dbpr():
    print("Launching headless browser to bypass DBPR blocks...")
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Emulate a real desktop browser window
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            # Step 1: Navigate to the DBPR License Search page
            print("Navigating to DBPR portal...")
            page.goto("https://www.myfloridalicense.com/wl11.asp?mode=0&SID=", timeout=30000)
            page.wait_for_selector("select[name='Board']", timeout=10000)

            # Step 2: Select Form Inputs
            # Board 06 = Construction Industry Licensing Board
            page.select_option("select[name='Board']", "06")
            time.sleep(1)

            # License Type CAC = Certified Air Conditioning Contractor
            page.select_option("select[name='LicenseType']", "CAC")
            
            # County 39 = Hillsborough County
            page.select_option("select[name='County']", "39")
            
            # Active Licenses
            page.select_option("select[name='Status']", "ACT")

            # Step 3: Submit Form
            print("Submitting search form...")
            page.click("input[type='submit'][name='Search']")
            page.wait_for_load_state("networkidle", timeout=30000)

            # Step 4: Extract Content
            content = page.content()
            soup = BeautifulSoup(content, 'html.parser')
            rows = soup.find_all('tr')

            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 3:
                    text_cols = [c.get_text(strip=True) for c in cols]
                    if any("CAC" in t or "License" in t for t in text_cols):
                        results.append({
                            "Firm/Name": text_cols[0],
                            "License Number": text_cols[1] if len(text_cols) > 1 else "N/A",
                            "Phone": "N/A",
                            "Email": "N/A"
                        })

            print(f"Successfully retrieved {len(results)} contractor records.")

        except Exception as e:
            print(f"Scraping error encountered: {e}")
        finally:
            browser.close()

    return results

def save_to_csv(data, filename="hillsborough_hvac_contractors.csv"):
    keys = ["Firm/Name", "License Number", "Phone", "Email"]
    # Write file regardless of record count so Git can stage it
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        if data:
            writer.writerows(data)
    print(f"Wrote output file to {filename}")

if __name__ == "__main__":
    data = scrape_dbpr()
    save_to_csv(data)
