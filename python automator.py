"""
enrich_business_csv.py

Fills in missing "Phone" (and optionally "Principal Address") for a CSV of
businesses using Google's Places API, searching by business name + a
location hint (e.g. county/state) since no street address is available
up front.

SETUP
-----
1. Get a Google Cloud API key with the "Places API" (New) enabled:
   https://console.cloud.google.com/apis/library/places-backend.googleapis.com
   (Billing must be enabled on the project, but Google gives a recurring
   free monthly credit that covers light usage.)

2. Install dependencies:
   pip install requests pandas --break-system-packages

3. Set your API key as an environment variable (safer than hardcoding it):
   export GOOGLE_PLACES_API_KEY="your-key-here"       (Mac/Linux)
   setx GOOGLE_PLACES_API_KEY "your-key-here"          (Windows)

4. Edit the CONFIG section below if your column names differ.

5. Run:
   python enrich_business_csv.py input.csv output.csv
"""

import sys
import os
import time
import requests
import pandas as pd

# ---------------------------------------------------------------------------
# CONFIG — edit these to match your CSV's actual column headers
# ---------------------------------------------------------------------------
NAME_COL = "Business Name"          # column with the business name (used as search input)
PHONE_COL = "Phone"                 # column to fill in with the phone number
ADDRESS_COL = "Principal Address"   # column to fill in with the address (optional)

# Since these rows have no address to search with, we append a location
# hint to the business name to narrow the search. Edit this to match
# where your businesses are actually located.
LOCATION_HINT = "Hillsborough County, FL"

# Values that count as "missing" and should be looked up / overwritten
MISSING_VALUES = {"", "n/a", "na", "none", "nan"}

REQUEST_DELAY_SECONDS = 0.2  # be polite to the API / stay under rate limits

API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY")

FIND_PLACE_URL = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"


def is_missing(value) -> bool:
    if pd.isna(value):
        return True
    return str(value).strip().lower() in MISSING_VALUES


def find_place_id(query: str) -> str | None:
    """Look up a place_id from a free-text query (e.g. 'Business Name, County, State')."""
    params = {
        "input": query,
        "inputtype": "textquery",
        "fields": "place_id",
        "key": API_KEY,
    }
    resp = requests.get(FIND_PLACE_URL, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    candidates = data.get("candidates", [])
    if candidates:
        return candidates[0].get("place_id")
    return None


def get_place_details(place_id: str) -> dict:
    """Fetch phone + formatted address for a given place_id."""
    params = {
        "place_id": place_id,
        "fields": "name,formatted_phone_number,international_phone_number,formatted_address",
        "key": API_KEY,
    }
    resp = requests.get(DETAILS_URL, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return data.get("result", {})


def enrich_row(row: pd.Series) -> pd.Series:
    name = str(row.get(NAME_COL, "")).strip()
    if not name or name.lower() == "nan":
        return row  # nothing to search with

    needs_phone = is_missing(row.get(PHONE_COL))
    needs_address = ADDRESS_COL in row and is_missing(row.get(ADDRESS_COL))

    if not (needs_phone or needs_address):
        return row  # already complete

    query = f"{name}, {LOCATION_HINT}" if LOCATION_HINT else name

    try:
        place_id = find_place_id(query)
        if not place_id:
            print(f"  No match found for: {query}")
            return row

        details = get_place_details(place_id)

        if needs_phone:
            phone = details.get("formatted_phone_number") or details.get(
                "international_phone_number"
            )
            if phone:
                row[PHONE_COL] = phone

        if needs_address and details.get("formatted_address"):
            row[ADDRESS_COL] = details["formatted_address"]

    except requests.RequestException as e:
        print(f"  Request failed for '{query}': {e}")

    return row


def main():
    if not API_KEY:
        sys.exit(
            "ERROR: GOOGLE_PLACES_API_KEY environment variable is not set. "
            "See the setup instructions at the top of this script."
        )

    if len(sys.argv) != 3:
        sys.exit("Usage: python enrich_business_csv.py input.csv output.csv")

    input_path, output_path = sys.argv[1], sys.argv[2]

    df = pd.read_csv(input_path)

    if NAME_COL not in df.columns:
        sys.exit(f"ERROR: expected a name column called '{NAME_COL}' — "
                  f"edit NAME_COL in the CONFIG section to match your CSV.")
    if PHONE_COL not in df.columns:
        df[PHONE_COL] = pd.NA

    total = len(df)
    for i in range(total):
        print(f"[{i + 1}/{total}] {df.iloc[i][NAME_COL]}")
        df.iloc[i] = enrich_row(df.iloc[i])
        time.sleep(REQUEST_DELAY_SECONDS)

    df.to_csv(output_path, index=False)
    print(f"\nDone. Saved enriched CSV to: {output_path}")


if __name__ == "__main__":
    main()