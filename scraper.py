import csv
import io
import sys
from curl_cffi import requests

# DBPR Construction Board Extract URL
DBPR_URL = "https://www2.myfloridalicense.com/sto/file_download/extracts/liccon.csv"

def run_scraper():
    print("Initiating DBPR download via impersonated TLS...")
    
    try:
        # DBPR server requires browser impersonation to pass Cloudflare TLS checks
        response = requests.get(DBPR_URL, impersonate="chrome120", timeout=120)
        print(f"Server response code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Error: DBPR endpoint returned status {response.status_code}")
            sys.exit(1)

    except Exception as e:
        print(f"Network request failed: {e}")
        sys.exit(1)

    # DBPR files use CP1252/Latin-1 encoding, NOT UTF-8
    try:
        content = response.content.decode('latin-1', errors='replace')
    except Exception as e:
        print(f"Decoding failed: {e}")
        sys.exit(1)

    reader = csv.reader(io.StringIO(content))
    results = []

    print("Processing CSV data...")
    
    for row_idx, row in enumerate(reader):
        if not row or len(row) < 5:
            continue
            
        # Convert all fields to upper string for search checks
        row_str = " ".join([str(cell).upper() for cell in row])
        
        # Hillsborough County checks: County code '39', '039', or text 'HILLSBOROUGH'
        in_hillsborough = ("39" in row) or ("039" in row) or ("HILLSBOROUGH" in row_str)
        
        # HVAC checks: Ranks CAC, RAC, or text match
        is_hvac = any(keyword in row_str for keyword in ["CAC", "RAC", "AIR CONDITIONING", "AIR COND"])
        
        if in_hillsborough and is_hvac:
            # Safe extraction with fallback indices
            firm_name = row[3].strip() if len(row) > 3 and row[3].strip() else (row[2].strip() if len(row) > 2 else "N/A")
            lic_num = row[12].strip() if len(row) > 12 else "N/A"
            phone = row[14].strip() if len(row) > 14 and row[14].strip() else "N/A"
            
            # Find email by scanning row for '@' symbol dynamically
            email = "N/A"
            for cell in row:
                if "@" in cell and "." in cell:
                    email = cell.strip()
                    break

            results.append({
                "Firm/Name": firm_name,
                "License Number": lic_num,
                "Phone": phone,
                "Email": email
            })

    print(f"Extraction complete. Matches found: {len(results)}")

    # Write output file safely
    output_filename = "hillsborough_hvac_contractors.csv"
    fieldnames = ["Firm/Name", "License Number", "Phone", "Email"]

    try:
        with open(output_filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        print(f"Successfully saved {len(results)} records to {output_filename}")
    except Exception as e:
        print(f"Failed writing CSV file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_scraper()
