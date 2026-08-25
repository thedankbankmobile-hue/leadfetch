import csv
import time
import requests
from bs4 import BeautifulSoup

# Setup session and browser headers to match standard state portal requests
session = requests.Session()
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.myfloridalicense.com/wl11.asp",
    "Origin": "https://www.myfloridalicense.com",
    "Content-Type": "application/x-www-form-urlencoded"
}

# --- SEARCH CONFIGURATION PARAMETERS ---
SEARCH_URL = "https://www.myfloridalicense.com/wl11.asp?mode=0&SID="

# County Code: 39 = Hillsborough County (DBPR internal mapping)
# Board/License Category: 06 = Construction Industry Licensing Board (HVAC / Air Conditioning)
PAYLOAD = {
    "Board": "06",
    "LicenseType": "CAC",  # Certified Air Conditioning Contractor
    "County": "39",         # Hillsborough County Code
    "State": "FL",
    "Status": "ACT",        # Active licenses only
    "Search": "Search"
}

def fetch_dbpr_contractors(payload):
    print("Initiating DBPR search request...")
    try:
        response = session.post(SEARCH_URL, data=payload, headers=headers, timeout=20)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Failed to connect to DBPR: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    results = []

    # Parse search results table rows
    rows = soup.find_all('tr')
    print(f"Parsing response data...")

    for row in rows:
        cols = row.find_all('td')
        # Typical DBPR table layout for licensee records
        if len(cols) >= 4:
            text_cols = [c.get_text(strip=True) for c in cols]
            
            # Check if row matches target format (Firm/Name, License #, Primary Detail)
            if "License" in text_cols[1] or "CAC" in text_cols[1]:
                firm_name = text_cols[0]
                license_num = text_cols[1]
                
                # Extract embedded profile links to grab email and phone numbers
                link = cols[0].find('a')
                phone = "N/A"
                email = "N/A"
                
                if link and 'href' in link.attrs:
                    detail_url = "https://www.myfloridalicense.com/" + link['href']
                    phone, email = fetch_licensee_contact_details(detail_url)
                    time.sleep(0.5) # Polite request delay to prevent IP throttling
                
                results.append({
                    "Firm/Name": firm_name,
                    "License Number": license_num,
                    "Phone": phone,
                    "Email": email
                })

    return results

def fetch_licensee_contact_details(detail_url):
    """Navigates into the specific licensee detail page to extract contact data."""
    try:
        res = session.get(detail_url, headers=headers, timeout=10)
        sub_soup = BeautifulSoup(res.text, 'html.parser')
        
        phone = "N/A"
        email = "N/A"
        
        # Look for Email & Phone labels within the detail container
        page_text = sub_soup.get_text()
        for tr in sub_soup.find_all('tr'):
            tds = tr.find_all('td')
            if len(tds) >= 2:
                label = tds[0].get_text(strip=True).lower()
                val = tds[1].get_text(strip=True)
                
                if "phone" in label:
                    phone = val
                elif "email" in label:
                    email = val

        return phone, email
    except Exception:
        return "N/A", "N/A"

def save_to_csv(data, filename="hillsborough_hvac_contractors.csv"):
    if not data:
        print("No records extracted. The search returned empty or encountered a block.")
        return

    keys = ["Firm/Name", "License Number", "Phone", "Email"]
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)
    
    print(f"Successfully exported {len(data)} records to {filename}")

if __name__ == "__main__":
    contractors = fetch_dbpr_contractors(PAYLOAD)
    save_to_csv(contractors)
