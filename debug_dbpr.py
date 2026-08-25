import csv
import io
from curl_cffi import requests

DBPR_URL = "https://www2.myfloridalicense.com/sto/file_download/extracts/liccon.csv"

def debug_dbpr():
    print("Downloading DBPR file...")
    res = requests.get(DBPR_URL, impersonate="chrome120", timeout=60)
    
    if res.status_code != 200:
        print(f"Failed with status code: {res.status_code}")
        return

    content = res.content.decode('utf-8', errors='ignore')
    reader = csv.reader(io.StringIO(content))

    print("\n--- FIRST 5 RAW ROWS IN FILE ---")
    for i, row in enumerate(reader):
        if i >= 5:
            break
        print(f"Row {i} ({len(row)} cols): {row[:10]}")

    # Reset reader
    reader = csv.reader(io.StringIO(content))
    
    hillsborough_matches = 0
    hvac_matches = 0
    combined_matches = 0

    for row in reader:
        row_str = " ".join(row).upper()
        
        # Track broad occurrences across the whole row string
        is_hillsborough = "39" in row or "HILLSBOROUGH" in row_str
        is_hvac = any(k in row_str for k in ["CAC", "RAC", "AIR CONDITION", "CONDITIONING"])
        
        if is_hillsborough:
            hillsborough_matches += 1
        if is_hvac:
            hvac_matches += 1
        if is_hillsborough and is_hvac:
            combined_matches += 1

    print("\n--- MATCH SUMMARY ---")
    print(f"Total rows matching Hillsborough criteria: {hillsborough_matches}")
    print(f"Total rows matching HVAC criteria: {hvac_matches}")
    print(f"Total rows matching BOTH: {combined_matches}")

if __name__ == "__main__":
    debug_dbpr()
