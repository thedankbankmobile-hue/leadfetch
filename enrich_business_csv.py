"""
enrich_business_csv.py

Scans a FOLDER of CSVs (each with columns like "Document Number" and
"Business Name"), looks up each business on Sunbiz.org by document number
to fill in address/registered agent, and optionally enriches with
phone/website via the Google Places API if a key is provided.

Writes one combined output CSV with all rows from every input file.

SETUP
-----
pip install requests pandas beautifulsoup4 --break-system-packages

USAGE
-----
python enrich_business_csv.py /path/to/folder/of/csvs
(or just edit INPUT_FOLDER below and run with no arguments)
"""

import os
import sys
import glob
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
INPUT_FOLDER = "./input_csvs"          # folder containing your CSV files
OUTPUT_CSV = "hillsborough_plumbing_contacts_combined.csv"

# Column names to look for in each input CSV (edit if yours differ)
DOC_NUM_COL = "Document Number"
NAME_COL = "Business Name"
STATUS_COL = "Status"
SEGMENT_COL = "Industry Segment"

# Optional: set this to enable phone/website lookups via Google Places API.
# Leave blank to skip Google entirely and only pull Sunbiz data.
GOOGLE_PLACES_API_KEY = ""

REQUEST_DELAY_SECONDS = 1  # be polite to Sunbiz / Google


def scrape_sunbiz_by_doc_num(doc_num: str) -> dict:
    sunbiz_url = (
        "https://search.sunbiz.org/Inquiry/CorporationSearch/SearchResultDetail"
        f"?inquiryType=DocumentNumber&searchTerm={doc_num}"
    )
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        )
    }
    try:
        response = requests.get(sunbiz_url, headers=headers, timeout=10)
        if response.status_code != 200:
            return {}

        soup = BeautifulSoup(response.text, "html.parser")
        data = {}

        for header in soup.find_all("span", class_="detail-section-header"):
            header_text = header.get_text(strip=True).upper()

            if "PRINCIPAL ADDRESS" in header_text:
                addr_div = header.find_next_sibling("div", class_="detail-section")
                if addr_div:
                    data["Principal Address"] = " ".join(
                        addr_div.get_text(separator=" ", strip=True).split()
                    )
            elif "MAILING ADDRESS" in header_text:
                addr_div = header.find_next_sibling("div", class_="detail-section")
                if addr_div:
                    data["Mailing Address"] = " ".join(
                        addr_div.get_text(separator=" ", strip=True).split()
                    )
            elif "REGISTERED AGENT" in header_text:
                agent_div = header.find_next_sibling("div", class_="detail-section")
                if agent_div:
                    data["Registered Agent"] = " ".join(
                        agent_div.get_text(separator=" ", strip=True).split()
                    )

        return data
    except Exception as e:
        print(f"  Sunbiz lookup failed for {doc_num}: {e}")
        return {}


def fetch_google_places_info(business_name: str, api_key: str) -> dict:
    if not api_key:
        return {}
    endpoint = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {"query": f"{business_name} Hillsborough County FL", "key": api_key}
    try:
        res = requests.get(endpoint, params=params, timeout=10).json()
        if res.get("results"):
            place_id = res["results"][0].get("place_id")
            details_endpoint = "https://maps.googleapis.com/maps/api/place/details/json"
            details_params = {
                "place_id": place_id,
                "fields": "formatted_phone_number,website",
                "key": api_key,
            }
            details_res = requests.get(details_endpoint, params=details_params, timeout=10).json()
            result = details_res.get("result", {})
            return {
                "Phone": result.get("formatted_phone_number", ""),
                "Website": result.get("website", ""),
            }
    except Exception as e:
        print(f"  Google Places lookup failed for {business_name}: {e}")
    return {}


def load_companies_from_folder(folder: str) -> list[dict]:
    """Read every CSV in the folder and pull out the columns we need."""
    csv_paths = sorted(glob.glob(os.path.join(folder, "*.csv")))
    if not csv_paths:
        sys.exit(f"ERROR: no .csv files found in '{folder}'")

    companies = []
    for path in csv_paths:
        print(f"Reading {path}...")
        df = pd.read_csv(path)

        missing = [c for c in (DOC_NUM_COL, NAME_COL) if c not in df.columns]
        if missing:
            print(f"  Skipping {path} — missing column(s): {missing}")
            continue

        for _, row in df.iterrows():
            companies.append({
                "doc": str(row.get(DOC_NUM_COL, "")).strip(),
                "name": str(row.get(NAME_COL, "")).strip(),
                "status": row.get(STATUS_COL, "") if STATUS_COL in df.columns else "",
                "segment": row.get(SEGMENT_COL, "") if SEGMENT_COL in df.columns else "",
                "source_file": os.path.basename(path),
            })
    return companies


def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else INPUT_FOLDER
    companies = load_companies_from_folder(folder)

    records = []
    total = len(companies)
    print(f"Processing {total} business records from {folder}...")

    for idx, item in enumerate(companies, 1):
        doc_num, name = item["doc"], item["name"]
        print(f"[{idx}/{total}] {name} ({doc_num}) — from {item['source_file']}")

        sunbiz_info = scrape_sunbiz_by_doc_num(doc_num) if doc_num else {}
        places_info = fetch_google_places_info(name, GOOGLE_PLACES_API_KEY)

        row = {
            "Document Number": doc_num,
            "Business Name": name,
            "Status": item["status"],
            "Industry Segment": item["segment"],
            "Principal Address": sunbiz_info.get("Principal Address", "N/A"),
            "Mailing Address": sunbiz_info.get("Mailing Address", "N/A"),
            "Registered Agent": sunbiz_info.get("Registered Agent", "N/A"),
            "Source File": item["source_file"],
        }
        if GOOGLE_PLACES_API_KEY:
            row["Phone"] = places_info.get("Phone", "")
            row["Website"] = places_info.get("Website", "")

        records.append(row)
        time.sleep(REQUEST_DELAY_SECONDS)

    pd.DataFrame(records).to_csv(OUTPUT_CSV, index=False)
    print(f"\nDone. Combined {total} records from {len(set(c['source_file'] for c in companies))} file(s) into '{OUTPUT_CSV}'.")


if __name__ == "__main__":
    main()
