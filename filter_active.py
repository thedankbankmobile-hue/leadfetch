import csv
import glob
import os

output_dir = r"C:\Users\17275\leadfetch\output"
csv_files = glob.glob(os.path.join(output_dir, "*.csv"))

for file_path in csv_files:
    if "_active_only" in file_path:
        continue

    active_rows = []
    with open(file_path, mode="r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            status = row.get("Status", "").strip().upper()
            # Keeps 'Active' or 'A'
            if status in ["ACTIVE", "A"]:
                active_rows.append(row)

    clean_file_path = file_path.replace(".csv", "_active_only.csv")
    with open(clean_file_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(active_rows)

    print(f"Filtered {os.path.basename(file_path)}: {len(active_rows)} active records saved.")