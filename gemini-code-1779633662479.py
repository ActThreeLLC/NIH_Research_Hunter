import os
import csv
from datetime import datetime, timedelta
from Bio import Entrez

# --- CONFIGURATION ---
# NCBI requires an email address. If a script causes traffic spikes, they alert you instead of blocking your IP.
Entrez.email = "your.email@act-three.net" 
# Optional: Get a free NCBI API Key to increase speed limits from 3 to 10 requests/second
Entrez.api_key = os.getenv("NCBI_API_KEY") 

DB_FILE = "research_log.csv"

def build_search_query():
    """Generates a dynamic query targeting newly indexed creatine studies relevant to older adults."""
    # Target standard creatine monohydrate terms
    base_terms = '("creatine" OR "creatine monohydrate" OR "phosphocreatine")'
    
    # Target senior-specific wellness vectors
    health_vectors = '("sarcopenia" OR "cognitive" OR "memory" OR "brain energy" OR "aging" OR "older adults" OR "menopause" OR "bone density" OR "frailty")'
    
    # Calculate yesterday's date to catch newly indexed files
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y/%m/%d")
    date_filter = f'"{yesterday}"[EDAT]' # Entrez Date filter
    
    return f"{base_terms} AND {health_vectors} AND {date_filter}"

def initialize_database():
    """Creates the storage log if it doesn't exist."""
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Date Found", "PMID", "Title", "Journal", "Year", "URL"])

def get_logged_pmids():
    """Reads existing database to prevent duplicate alerts."""
    if not os.path.exists(DB_FILE):
        return set()
    with open(DB_FILE, mode='r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader, None) # Skip header
        return {row[1] for row in reader if row}

def fetch_new_research():
    initialize_database()
    logged_pmids = get_logged_pmids()
    query = build_search_query()
    
    print(f"[{datetime.now()}] Running daily scan: {query}")
    
    # Step 1: Search for matching PubMed IDs (PMIDs)
    try:
        search_handle = Entrez.esearch(db="pubmed", term=query, retmax=50)
        search_results = Entrez.read(search_handle)
        search_handle.close()
        
        pmid_list = search_results.get("IdList", [])
        
        # Filter for IDs we haven't seen yet
        new_pmids = [pmid for pmid in pmid_list if pmid not in logged_pmids]
        
        if not new_pmids:
            print("No new studies published in the last 24 hours.")
            return

        print(f"Found {len(new_pmids)} new clinical studies! Fetching details...")
        
        # Step 2: Fetch full metadata for new PMIDs
        fetch_handle = Entrez.efetch(db="pubmed", id=",".join(new_pmids), retmode="xml")
        records = Entrez.read(fetch_handle)
        fetch_handle.close()
        
        # Step 3: Parse and Log Results
        with open(DB_FILE, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            for article in records.get("PubmedArticle", []):
                medline = article["MedlineCitation"]
                pmid = str(medline["PMID"])
                
                # Extract clean strings
                title = medline["Article"]["ArticleTitle"]
                journal = medline["Article"]["Journal"]["Title"]
                year = medline["Article"]["Journal"]["JournalIssue"]["PubDate"].get("Year", "N/A")
                url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                
                # Append to database
                writer.writerow([datetime.now().strftime("%Y-%m-%d"), pmid, title, journal, year, url])
                print(f"Logged: {title} ({journal})")
                
                # ALERT TRIGGER (Optional): Integrate Slack, Discord, or Email webhook here
                
    except Exception as e:
        print(f"Error during execution: {e}")

if __name__ == "__main__":
    fetch_new_research()