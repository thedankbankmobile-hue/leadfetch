import csv
import time
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

def scrape_yellowpages_hvac():
    print("Fetching HVAC contractors from YellowPages for Hillsborough County / Tampa...")
    results = []
    
    # Query: HVAC contractors in Tampa, FL (Hillsborough County seat)
    url = "https://www.yellowpages.com/tampa-fl/hvac-contractors"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Locate search result cards
        cards = soup.find_all('div', class_='result') or soup.find_all('div', class_='v-card')
        print(f"Found {len(cards)} listing elements on page.")

        for card in cards:
            # Extract business name
            name_elem = card.find('a', class_='business-name')
            name = name_elem.get_text(strip=True) if name_elem else None
            
            # Extract phone number
            phone_elem = card.find('div', class_='phones') or card.find('div', class_='phone')
            phone = phone_elem.get_text(strip=True) if phone_elem else "N/A"
            
            # Extract street address
            address_elem = card.find('div', class_='street-address')
            locality_elem = card.find('div', class_='locality')
            street = address_elem.get_text(strip=True) if address_elem else ""
            locality = locality_elem.get_text(strip=True) if locality_elem else ""
            address = f"{street}, {locality}".strip(", ") if (street or locality) else "Hillsborough County, FL"

            if name:
                results.append({
                    "Firm/Name": name,
                    "Phone": phone,
                    "Address": address,
                    "Email": "N/A"
                })

    except Exception as e:
        print(f"Extraction error: {e}")

    # Fallback default records if site structure changes
    if not results:
        print("Warning: Standard card elements missing, running fallback selector...")
        for a_tag in soup.find_all('a', class_='business-name'):
            results.append({
                "Firm/Name": a_tag.get_text(strip=True),
                "Phone": "N/A",
                "Address": "Hillsborough County, FL",
                "Email": "N/A"
            })

    print(f"Extracted total of {len(results)} contractor records.")
    return results

def save_to_csv(data, filename="hillsborough_hvac_contractors.csv"):
    keys = ["Firm/Name", "Phone", "Address", "Email"]
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        if data:
            writer.writerows(data)
    print(f"Saved CSV file: {filename}")

if __name__ == "__main__":
    contractors = scrape_yellowpages_hvac()
    save_to_csv(contractors)
