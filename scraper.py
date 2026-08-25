import csv
import time
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

def scrape_hvac_contractors():
    print("Starting Playwright browser for HVAC search...")
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Use realistic user agent and viewport
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()

        try:
            # Targeted query: HVAC contractors in Hillsborough County / Tampa FL
            target_url = "https://www.yelp.com/search?find_desc=HVAC+Contractors&find_loc=Hillsborough+County%2C+FL"
            print(f"Navigating to: {target_url}")
            
            page.goto(target_url, wait_until="domcontentloaded", timeout=45000)
            time.sleep(3)  # Allow dynamic content to load

            # Scroll down to trigger lazy-loaded listings
            page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2);")
            time.sleep(2)

            soup = BeautifulSoup(page.content(), 'html.parser')
            
            # Find business listings
            listings = soup.find_all('div', class_=lambda c: c and 'container' in c.lower() or 'business' in c.lower())
            
            # Parse main headings and business details
            cards = soup.select("div[data-testid='serp-ia-card']") or soup.find_all('h3')

            for card in cards:
                # Find business title links
                title_elem = card.find('a') if card.name != 'a' else card
                if title_elem:
                    name = title_elem.get_text(strip=True)
                    # Filter out non-business text headers
                    if name and not any(skip in name.lower() for skip in ["yelp", "filter", "sponsored", "results"]):
                        
                        # Look for phone number pattern if present on card
                        card_text = card.get_text()
                        phone = "N/A"
                        
                        results.append({
                            "Firm/Name": name,
                            "License Number": "N/A (Yelp Listing)",
                            "Phone": phone,
                            "Email": "N/A"
                        })

            print(f"Retrieved {len(results)} contractor listings.")

        except Exception as e:
            print(f"Scraping exception: {e}")
        finally:
            browser.close()

    # Deduplicate results by business name
    unique_results = {r['Firm/Name']: r for r in results}.values()
    return list(unique_results)

def save_to_csv(data, filename="hillsborough_hvac_contractors.csv"):
    keys = ["Firm/Name", "License Number", "Phone", "Email"]
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        if data:
            writer.writerows(data)
    print(f"Successfully saved {len(data)} records to {filename}")

if __name__ == "__main__":
    contractors = scrape_hvac_contractors()
    save_to_csv(contractors)
