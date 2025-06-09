import requests
import pandas as pd

# Replace this with your actual Hunter.io API key
API_KEY = '42a0ad10c23d079fb0eebe90211172d855c9e4a4'

def find_emails(domain):
    url = f"https://api.hunter.io/v2/domain-search?domain={{stripe.com}}&api_key={{42a0ad10c23d079fb0eebe90211172d855c9e4a4}}"
    response = requests.get(url)
    
    if response.status_code != 200:
        print(f"Failed to fetch data for {domain}")
        return []
    
    data = response.json()
    emails = data.get('data', {}).get('emails', [])
    
    results = []
    for email in emails:
        position = email.get('position', '').lower()
        if any(role in position for role in ['ceo', 'cfo', 'coo', 'cto', 'cmo']):
            results.append({
                'Company Name': domain,
                'Contact Name': f"{email.get('first_name', '')} {email.get('last_name', '')}",
                'Email': email.get('value')
            })
    
    return results

# 🔹 Example list of company domains — you can change these
company_domains = ['apple.com', 'tesla.com', 'meta.com']

all_results = []
for domain in company_domains:
    print(f"Searching: {domain}")
    results = find_emails(domain)
    all_results.extend(results)

# Save to Excel
df = pd.DataFrame(all_results)
df.to_excel("c_suite_contacts.xlsx", index=False)
print("✅ Saved to c_suite_contacts.xlsx")
