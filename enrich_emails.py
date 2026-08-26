import csv
import re
import time
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

# Regex to match valid email addresses while ignoring static web assets
EMAIL_REGEX = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
IGNORE_TERMS = ['yellowpages', 'ypcdn', 'schema', 'example', 'png', 'jpg', 'jpeg', 'sentry', 'wix', 'domain', 'github', 'bootstrap']

def find_email_via_search(firm_name):
    """Searches public web records for emails associated with the firm name."""
    clean_name = re.sub(r'[^a-zA-Z0-9\s]', '', firm_name)
    query = f'"{clean_name}" "Hillsborough" OR "Tampa" email OR "contact"'
    search_url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"

    try:
        response = requests.get(search_url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            text_content = soup.get_text()
            
            # Find all matching email patterns
            matches = re.findall(EMAIL_REGEX, text_content)
            
            # Filter out junk/system emails
            valid_emails = [
                e.lower() for e in matches 
                if not any(term in e.lower() for term in IGNORE_TERMS)
            ]
            
            if valid_emails:
                return valid_emails[0]
    except Exception as e:
        print(f"Search query error for {firm_name}: {e}")

    return "N/A"

def enrich_contractor_emails(input_csv="hillsborough_hvac_contractors.csv"):
    print(f"Reading records from {input_csv} to enrich with emails...")
    
    records = []
    try:
        with open(input_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            records = list(reader)
    except FileNotFoundError:
        print(f"Error: {input_csv} not found. Run scraper.py first.")
        return

    print(f"Processing {len(records)} records for email extraction...")

    found_count = 0
    for idx, row in enumerate(records):
        firm_name = row.get("Firm/Name", "").strip()
        
        # Skip empty names or already enriched records
        if not firm_name or (row.get("Email") and row["Email"] != "N/A"):
            continue

        print(f"[{idx+1}/{len(records)}] Searching email for: {firm_name}")
        email = find_email_via_search(firm_name)
        row["Email"] = email
        
        if email != "N/A":
            found_count += 1
            print(f"  -> Found: {email}")

        time.sleep(1.5) # Polite delay to avoid search throttle

    # Update the CSV file
    keys = ["Firm/Name", "Phone", "Address", "Email"]
    with open(input_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(records)

    print(f"Done! Successfully enriched {found_count} email addresses in {input_csv}.")

if __name__ == "__main__":
    enrich_contractor_emails()
