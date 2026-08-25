import csv
import re
import time
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

EMAIL_REGEX = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

def enrich_contractor_emails(input_csv="hillsborough_hvac_contractors.csv"):
    print(f"Reading records from {input_csv} to search for emails...")
    
    records = []
    try:
        with open(input_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            records = list(reader)
    except FileNotFoundError:
        print(f"Error: {input_csv} not found. Run scraper.py first.")
        return

    print(f"Loaded {len(records)} records. Searching YellowPages detail pages...")

    for idx, row in enumerate(records):
        # Skip if email is already present
        if row.get("Email") and row["Email"] != "N/A":
            continue

        firm_name = row.get("Firm/Name", "").strip()
        if not firm_name:
            continue

        print(f"[{idx+1}/{len(records)}] Processing: {firm_name}")
        
        # Search YellowPages for company detail page
        search_url = f"https://www.yellowpages.com/search?search_terms={requests.utils.quote(firm_name)}&geo_location_terms=Tampa%2C+FL"
        email_found = "N/A"

        try:
            res = requests.get(search_url, headers=HEADERS, timeout=10)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                
                # Look for direct mailto links on the detail page or listing card
                mailto_link = soup.find('a', href=re.compile(r'^mailto:', re.I))
                if mailto_link:
                    email_found = mailto_link['href'].replace('mailto:', '').strip()
                else:
                    # Alternative: Regex scan page content for plain text email matches
                    matches = re.findall(EMAIL_REGEX, res.text)
                    valid_emails = [e for e in matches if not any(x in e.lower() for x in ['yellowpages', 'ypcdn', 'schema', 'example'])]
                    if valid_emails:
                        email_found = valid_emails[0]

                # Extract business website link if present for external checking
                website_link = soup.find('a', class_='website-link')
                if website_link and email_found == "N/A" and 'href' in website_link.attrs:
                    target_site = website_link['href']
                    email_found = scrape_external_site_email(target_site)

        except Exception as e:
            print(f"Error fetching detail page for {firm_name}: {e}")

        row["Email"] = email_found
        time.sleep(1) # Delay between requests to prevent throttling

    # Overwrite CSV with enriched email details
    keys = ["Firm/Name", "Phone", "Address", "Email"]
    with open(input_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(records)

    print(f"Email enrichment complete. Updated {input_csv}.")

def scrape_external_site_email(site_url):
    """Fallback: Visit contractor's external website homepage to find email."""
    try:
        res = requests.get(site_url, headers=HEADERS, timeout=7)
        matches = re.findall(EMAIL_REGEX, res.text)
        valid_emails = [e for e in matches if not any(x in e.lower() for x in ['png', 'jpg', 'sentry', 'wix', 'domain'])]
        return valid_emails[0] if valid_emails else "N/A"
    except Exception:
        return "N/A"

if __name__ == "__main__":
    enrich_contractor_emails()
