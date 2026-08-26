import csv
import os
import random
import sys
import time
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

SEARCH_ENTRY_URL = "https://search.sunbiz.org/Inquiry/CorporationSearch/ByName"

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

INDUSTRY_CONFIG = {
    "plumbing": {"output_file": os.path.join(OUTPUT_DIR, "hillsborough_plumbing_sunbiz.csv"), "terms": ["PLUMBING", "PLUMBER"]},
    "hvac": {"output_file": os.path.join(OUTPUT_DIR, "hillsborough_hvac_sunbiz.csv"), "terms": ["HVAC", "AIR CONDITION"]},
    "construction": {"output_file": os.path.join(OUTPUT_DIR, "hillsborough_construction_sunbiz.csv"), "terms": ["CONSTRUCTION", "CONTRACTOR"]},
    "landscape": {"output_file": os.path.join(OUTPUT_DIR, "hillsborough_landscape_sunbiz.csv"), "terms": ["LANDSCAPE", "TREE SERVICE"]},
    "roofing": {"output_file": os.path.join(OUTPUT_DIR, "hillsborough_roofing_sunbiz.csv"), "terms": ["ROOFING", "ROOFER"]},
    "electrical": {"output_file": os.path.join(OUTPUT_DIR, "hillsborough_electrical_sunbiz.csv"), "terms": ["ELECTRIC", "ELECTRICAL"]},
}

def scrape_industry_form(p, industry_key):
    if industry_key not in INDUSTRY_CONFIG:
        print(f"[!] Unknown industry: '{industry_key}'.")
        return

    config = INDUSTRY_CONFIG[industry_key]
    print(f"\n==========================================")
    print(f"SCRAPING WITH PLAYWRIGHT FORM ACTION: {industry_key.upper()}")
    print(f"==========================================")

    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 800}
    )
    page = context.new_page()

    results = []
    seen_docs = set()

    for term in config["terms"]:
        print(f"[+] Searching query: '{term}'...")

        try:
            # 1. Navigate to main search entry page
            page.goto(SEARCH_ENTRY_URL, wait_until="networkidle", timeout=30000)
            
            # 2. Fill search field and click search
            search_input = page.locator("#SearchTerm")
            search_input.fill(term)
            
            # Submit form
            page.locator("input[type='submit'][value='Search Now']").click()
            page.wait_for_load_state("networkidle")

            time.sleep(random.uniform(1.5, 3.0))

            # 3. Parse rendered table HTML
            html_content = page.content()
            soup = BeautifulSoup(html_content, 'html.parser')

            rows = soup.find_all('tr')
            valid_rows = 0

            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 3:
                    entity_name = cols[0].text.strip()
                    doc_number = cols[1].text.strip()
                    status = cols[2].text.strip()

                    if "Corporate Name" in entity_name or "Document Number" in doc_number:
                        continue
                    
                    if doc_number in seen_docs:
                        continue
                    seen_docs.add(doc_number)

                    valid_rows += 1
                    results.append({
                        "Document Number": doc_number,
                        "Business Name": entity_name,
                        "Status": status,
                        "Industry Segment": industry_key.upper()
                    })

            print(f"    -> Extracted {valid_rows} unique records for '{term}'.")

        except Exception as e:
            print(f"[ERROR] Fetching '{term}': {e}")

    browser.close()

    output_filepath = config["output_file"]
    fieldnames = ["Document Number", "Business Name", "Status", "Industry Segment"]

    with open(output_filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"[SUMMARY] Finished {industry_key.upper()}: Saved {len(results)} records to {output_filepath}")

if __name__ == "__main__":
    target = sys.argv[1].lower() if len(sys.argv) > 1 else "roofing"

    with sync_playwright() as p:
        if target == "all":
            for ind in INDUSTRY_CONFIG.keys():
                scrape_industry_form(p, ind)
        else:
            scrape_industry_form(p, target)
