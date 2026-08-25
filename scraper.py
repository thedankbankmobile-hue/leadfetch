def save_to_csv(data, filename="hillsborough_hvac_contractors.csv"):
    keys = ["Firm/Name", "License Number", "Phone", "Email"]
    
    # Always write at least the headers so Git can stage the file
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        if data:
            writer.writerows(data)
            print(f"Successfully exported {len(data)} records to {filename}")
        else:
            print(f"Warning: Zero records extracted. Created empty CSV structure at {filename}")
