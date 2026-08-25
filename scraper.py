import csv
import time
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

def scrape_dbpr():
    print("Starting Playwright browser...")
    results = []

    with sync_playwright() as p:
        # Launch Chromium headless browser
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            # Direct search URL for DBPR Board/Category searches
            search_url = "https://www.myfloridalicense.com/wl11.asp?mode=1&SID="
            print(f"Navigating to DBPR portal: {search_url}")
            page.goto(search_url, wait_until="networkidle", timeout=60000)

            # Wait for form select elements to load
            page.wait_for_selector("form", timeout=15000)

            # Select Board (06 = Construction Industry Licensing Board)
            page.select_option("select[name='Board']", value="06")
            time.sleep(1)

            # Select License Type (CAC = Certified Air Conditioning Contractor)
            if page.locator("select[name='LicenseType']").count() > 0:
                page.select_option("select[name='LicenseType']", value="CAC")

            # Select County (39 = Hillsborough County)
            if page.locator("select[name='County']").count() > 0:
                page.select_option("select[name='County']", value="39")

            # Click Submit button
            print("Submitting search parameters...")
            submit_button = page.locator("input[type='submit'][value='Search'], input[type='submit'][name='Search']").first
            submit_button.click()

            # Wait for results table to load
            page.wait_for_selector("table", timeout=30000)
            time.sleep(3)

            # Extract data from the page
            soup = BeautifulSoup(page.content(), 'html.parser')
            rows = soup.find_all('tr')

            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 3:
                    text_cols = [c.get_text(strip=True) for c in cols]
                    # Check if row contains license record patterns
                    if any("CAC" in t or "Lic" in t for t in text_cols):
                        results.append({
                            "Firm/Name": text_cols[0],
                            "License Number": text_cols[1] if len(text_cols) > 1 else "N/A",
                            "Phone": "N/A",
                            "Email": "N/A"
                        })

            print(f"Successfully scraped {len(results)} contractor records.")

        except Exception as e:
            print(f"Error during scraping execution: {e}")
        finally:
            browser.close()

    return results

def save_to_csv(data, filename="hillsborough_hvac_contractors.csv"):
    keys = ["Firm/Name", "License Number", "Phone", "Email"]
    # Write file out regardless of record count so Git recognizes the file path
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        if data:
            writer.writerows(data)
    print(f"File output saved to: {filename}")

if __name__ == "__main__":
    contractors_data = scrape_dbpr()
    save_to_csv(contractors_data)
