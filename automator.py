import os
import time
import re
import pandas as pd
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from duckduckgo_search import DDGS

WATCH_DIR = r"C:\Users\17275\leadfetch\incoming"
PROCESSED_DIR = r"C:\Users\17275\leadfetch\output"

os.makedirs(WATCH_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

class CSVHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory or not event.src_path.endswith(".csv"):
            return
        
        print(f"\nNew CSV detected: {event.src_path}")
        time.sleep(1)  # Ensure file copy completes
        self.process_csv(event.src_path)

    def process_csv(self, file_path):
        try:
            df = pd.read_csv(file_path)
            if "Business Name" not in df.columns:
                print("Skipping: CSV missing 'Business Name' column.")
                return

            phones, emails = [], []

            for idx, row in df.iterrows():
                name = str(row["Business Name"])
                print(f"Enriching [{idx+1}/{len(df)}]: {name}...")
                
                phone, email = self.lookup_contact_info(name)
                phones.append(phone)
                emails.append(email)
                time.sleep(1) # Polite delay between web searches

            df["Phone"] = phones
            df["Email"] = emails

            base_name = os.path.basename(file_path)
            output_path = os.path.join(PROCESSED_DIR, f"enriched_{base_name}")
            df.to_csv(output_path, index=False)
            print(f"Finished processing! Output saved to: {output_path}")

        except Exception as e:
            print(f"Error processing file {file_path}: {e}")

    def lookup_contact_info(self, business_name):
        phone, email = "N/A", "N/A"
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(f'"{business_name}" Florida phone email', max_results=3))
                
                for res in results:
                    snippet = res.get("body", "")
                    
                    # Regex match standard US phone numbers
                    if phone == "N/A":
                        phone_match = re.search(r'(\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})', snippet)
                        if phone_match:
                            phone = phone_match.group(1)
                        
                    # Regex match emails
                    if email == "N/A":
                        email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', snippet)
                        if email_match:
                            email = email_match.group(0)
                        
                    if phone != "N/A" and email != "N/A":
                        break
        except Exception as e:
            print(f"Search lookup failed for {business_name}: {e}")
            
        return phone, email

if __name__ == "__main__":
    event_handler = CSVHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCH_DIR, recursive=False)
    observer.start()
    print(f"Watching directory: {WATCH_DIR}...")
    print("Drop any CSV with a 'Business Name' column into 'incoming' to test.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()