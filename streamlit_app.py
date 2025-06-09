import streamlit as st
import pandas as pd
import requests
import io

# 🔑 Your Hunter.io API key
API_KEY = '129b7781d3278c02e68bef7ed3d28d83c25bcd44'  # <-- Your actual key

def find_emails(domain, exclude_directors=False):
    # Fixed: Use the actual domain parameter and API_KEY variable
    url = f"https://api.hunter.io/v2/domain-search?domain={domain}&api_key={API_KEY}"
    
    try:
        response = requests.get(url, timeout=10)
        
        # Debug output
        print(f"Status code for {domain}: {response.status_code}")
        
        # Handle JSON parsing
        try:
            data = response.json()
        except Exception as e:
            print(f"Error parsing JSON for {domain}: {e}")
            return [], f"Invalid JSON response for {domain}"

        # Check for API errors
        if response.status_code != 200:
            error_msg = data.get('errors', [{}])[0].get('details', 'Unknown error') if data.get('errors') else 'Unknown error'
            return [], f"API error for {domain}: {error_msg}"

        # Extract emails
        emails = data.get('data', {}).get('emails', [])
        results = []

        for email in emails:
            position = (email.get('position') or '').lower()
            
            # Define C-suite roles
            c_suite_roles = ['ceo', 'cfo', 'coo', 'cto', 'cmo', 'chief', 'president', 'founder']
            director_roles = ['director', 'dir.']
            
            # Check if position contains C-suite keywords
            is_c_suite = any(role in position for role in c_suite_roles)
            is_director = any(role in position for role in director_roles)
            
            # Apply filtering based on user preference
            if exclude_directors:
                # Only include if it's C-suite AND not a director
                if is_c_suite and not is_director:
                    should_include = True
                else:
                    should_include = False
            else:
                # Include if it's C-suite (including directors with C-suite titles)
                should_include = is_c_suite
            
            if should_include:
                results.append({
                    'Company Name': domain,
                    'Contact Name': f"{email.get('first_name', '')} {email.get('last_name', '')}".strip(),
                    'Email': email.get('value'),
                    'Position': email.get('position', ''),
                    'Confidence': email.get('confidence', 0)
                })

        return results, None
        
    except requests.exceptions.RequestException as e:
        return [], f"Network error for {domain}: {str(e)}"
    except Exception as e:
        return [], f"Unexpected error for {domain}: {str(e)}"

# 🖼️ Streamlit UI
st.set_page_config(page_title="C-Suite Email Finder", page_icon="📧")
st.title("📧 C-Suite Email Finder")

st.markdown("Find C-suite executives' email addresses using Hunter.io API")

# Add the checkbox for excluding directors
exclude_directors = st.checkbox(
    "✅ Only show C-suite (exclude Directors)", 
    value=False,
    help="When checked, excludes positions with 'Director' in the title, keeping only top C-suite executives"
)

domains_input = st.text_area(
    "Enter company domains (one per line):", 
    height=200,
    placeholder="example.com\ncompany.com\nanother-domain.com"
)

if st.button("🔍 Find Emails", type="primary"):
    if not domains_input.strip():
        st.error("Please enter at least one domain.")
    else:
        domains = [d.strip() for d in domains_input.split("\n") if d.strip()]
        all_results = []
        error_domains = []

        # Create a progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()

        for i, domain in enumerate(domains):
            status_text.text(f"🔍 Searching: {domain}")
            
            results, error = find_emails(domain, exclude_directors)
            
            if error:
                error_domains.append(f"{domain} → {error}")
            else:
                all_results.extend(results)
            
            # Update progress
            progress_bar.progress((i + 1) / len(domains))

        # Clear progress indicators
        progress_bar.empty()
        status_text.empty()

        # Display results
        if all_results:
            df = pd.DataFrame(all_results)
            st.success(f"✅ Found {len(all_results)} C-suite emails!")
            st.dataframe(df, use_container_width=True)

            # Create Excel file in memory
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='C-Suite Contacts')
            
            st.download_button(
                label="📥 Download Excel",
                data=output.getvalue(),
                file_name="c_suite_contacts.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("⚠️ No C-suite emails found.")

        # Display errors if any
        if error_domains:
            st.error("Some domains had errors:")
            for error in error_domains:
                st.text(error)