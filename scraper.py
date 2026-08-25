import csv
import requests

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Overpass QL query: Find HVAC & climate control contractors in Hillsborough County, FL
OVERPASS_QUERY = """
[out:json][timeout:30];
area["name"="Hillsborough County"]["state"="Florida"]->.boundaryarea;
(
  node["craft"="hvac"](area.boundaryarea);
  way["craft"="hvac"](area.boundaryarea);
  relation["craft"="hvac"](area.boundaryarea);
  node["trade"="hvac"](area.boundaryarea);
  way["trade"="hvac"](area.boundaryarea);
  relation["trade"="hvac"](area.boundaryarea);
  node["shop"="hvac"](area.boundaryarea);
  way["shop"="hvac"](area.boundaryarea);
  relation["shop"="hvac"](area.boundaryarea);
  node["office"="hvac"](area.boundaryarea);
  way["office"="hvac"](area.boundaryarea);
  relation["office"="hvac"](area.boundaryarea);
);
out tags;
"""

def fetch_hvac_contractors():
    print("Fetching HVAC contractor records from Overpass API...")
    headers = {
        "User-Agent": "GitHubActions-HVACScraper/1.0"
    }
    
    try:
        response = requests.post(OVERPASS_URL, data={"data": OVERPASS_QUERY}, headers=headers, timeout=45)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Error requesting contractor data: {e}")
        return []

    elements = data.get("elements", [])
    print(f"Retrieved {len(elements)} raw elements from API query.")
    
    results = []
    seen_names = set()

    for elem in elements:
        tags = elem.get("tags", {})
        name = tags.get("name") or tags.get("operator") or tags.get("brand")
        
        if not name or name in seen_names:
            continue
        
        seen_names.add(name)
        phone = tags.get("phone") or tags.get("contact:phone") or "N/A"
        email = tags.get("email") or tags.get("contact:email") or "N/A"
        website = tags.get("website") or tags.get("contact:website") or "N/A"

        # Construct basic address from tags if available
        street = tags.get("addr:housenumber", "") + " " + tags.get("addr:street", "")
        city = tags.get("addr:city", "Hillsborough County")
        address = f"{street.strip()}, {city}, FL".strip(", ")

        results.append({
            "Firm/Name": name,
            "Phone": phone,
            "Email": email,
            "Address": address,
            "Website": website
        })

    # If OSM contains limited direct entries, fall back to general Tampa Bay climate services
    if not results:
        print("Executing fallback query for wider Hillsborough business coverage...")
        fallback_query = """
        [out:json][timeout:30];
        area["name"="Hillsborough County"]["state"="Florida"]->.searchArea;
        (
          node["name"~"Air|HVAC|Heating|Cooling|AC", i](area.searchArea);
          way["name"~"Air|HVAC|Heating|Cooling|AC", i](area.searchArea);
        );
        out tags;
        """
        try:
            fb_res = requests.post(OVERPASS_URL, data={"data": fallback_query}, headers=headers, timeout=45)
            fb_data = fb_res.json()
            for elem in fb_data.get("elements", []):
                tags = elem.get("tags", {})
                name = tags.get("name")
                if name and name not in seen_names:
                    seen_names.add(name)
                    results.append({
                        "Firm/Name": name,
                        "Phone": tags.get("phone") or tags.get("contact:phone") or "N/A",
                        "Email": tags.get("email") or tags.get("contact:email") or "N/A",
                        "Address": tags.get("addr:city", "Hillsborough County") + ", FL",
                        "Website": tags.get("website") or tags.get("contact:website") or "N/A"
                    })
        except Exception as err:
            print(f"Fallback query error: {err}")

    print(f"Successfully processed {len(results)} contractor entries.")
    return results

def save_to_csv(data, filename="hillsborough_hvac_contractors.csv"):
    keys = ["Firm/Name", "Phone", "Email", "Address", "Website"]
    
    # Force file creation on disk so git add step always finds the file
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        if data:
            writer.writerows(data)
            
    print(f"Saved {len(data)} records to {filename}")

if __name__ == "__main__":
    contractors = fetch_hvac_contractors()
    save_to_csv(contractors)
