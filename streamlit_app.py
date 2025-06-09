import streamlit as st
import pandas as pd
import requests
import io

# 🔑 API keys from Streamlit secrets
try:
    HUNTER_API_KEY = st.secrets["HUNTER_API_KEY"]
    APOLLO_API_KEY = st.secrets["APOLLO_API_KEY"]

    
except KeyError as e:
    st.error(f"Missing API key in secrets: {e}")
    st.info("Please add your API keys to the Streamlit secrets configuration.")
    st.stop()

# -------------------------
# 🔍 HUNTER.IO FUNCTION
# -------------------------
def find_hunter_emails(domain, exclude_directors=False, only_verified=False):
    """Find C-suite emails using Hunter.io API"""
    url = f"https://api.hunter.io/v2/domain-search"
    params = {
        "domain": domain,
        "api_key": HUNTER_API_KEY,
        "limit": 100
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        data = response.json()

        if response.status_code != 200:
            error_msg = data.get('errors', [{}])[0].get('details', 'Unknown error')
            return [], f"{domain} → Hunter error: {error_msg}"

        emails = data.get('data', {}).get('emails', [])
        results = []

        for email in emails:
            position = (email.get('position') or '').lower()
            is_verified = email.get('verification', {}).get('result') == 'deliverable'

            # Define C-suite and director roles
            c_suite_roles = ['ceo', 'cfo', 'coo', 'cto', 'cmo', 'chief', 'president', 'founder', 'owner']
            director_roles = ['director', 'dir.', 'vice president', 'vp']
            
            is_c_suite = any(role in position for role in c_suite_roles)
            is_director = any(role in position for role in director_roles)

            # Apply filters
            if exclude_directors:
                should_include = is_c_suite and not is_director
            else:
                should_include = is_c_suite or is_director

            if should_include and (not only_verified or is_verified):
                results.append({
                    'Company Name': domain,
                    'Contact Name': f"{email.get('first_name', '')} {email.get('last_name', '')}".strip(),
                    'Email': email.get('value'),
                    'Position': email.get('position', ''),
                    'Confidence': f"{email.get('confidence', 0)}%",
                    'Verified': 'Yes' if is_verified else 'No',
                    'Source': 'Hunter.io'
                })

        return results, None
    except requests.exceptions.RequestException as e:
        return [], f"{domain} → Hunter connection error: {str(e)}"
    except Exception as e:
        return [], f"{domain} → Hunter error: {str(e)}"


# -------------------------
# 🔍 APOLLO.IO FUNCTION
# -------------------------
def find_apollo_contacts(domain):
    """Find C-suite contacts using Apollo.io API"""
    url = "https://api.apollo.io/v1/mixed_people/search"
    
    headers = {
        "X-Api-Key": APOLLO_API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "q_organization_domains": [domain],
        "person_titles": [
            "CEO", "Chief Executive Officer",
            "CFO", "Chief Financial Officer", 
            "COO", "Chief Operating Officer",
            "CTO", "Chief Technology Officer",
            "CMO", "Chief Marketing Officer",
            "President", "Founder", "Co-Founder",
            "Owner", "Managing Director"
        ],
        "page": 1,
        "per_page": 50
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        data = response.json()

        if response.status_code != 200:
            error_msg = data.get("error", response.text)
            return [], f"{domain} → Apollo error: {error_msg}"

        people = data.get("people", [])
        results = []

        for person in people:
            # Get company name from organization data
            company_name = domain
            if person.get('organization') and person['organization'].get('name'):
                company_name = person['organization']['name']
            
            email = person.get('email')
            if not email or email == '':
                email = 'Not available'
            
            results.append({
                'Company Name': company_name,
                'Contact Name': f"{person.get('first_name', '')} {person.get('last_name', '')}".strip(),
                'Email': email,
                'Position': person.get('title', ''),
                'Confidence': 'N/A',
                'Verified': 'N/A',
                'Source': 'Apollo.io'
            })

        return results, None
    except requests.exceptions.RequestException as e:
        return [], f"{domain} → Apollo connection error: {str(e)}"
    except Exception as e:
        return [], f"{domain} → Apollo error: {str(e)}"


# -------------------------
# 🎯 STREAMLIT UI
# -------------------------
st.set_page_config(
    page_title="C-Suite Email Finder", 
    page_icon="📧",
    layout="wide"
)

st.title("📧 C-Suite Email Finder")
st.markdown("Find executive contacts from company domains using Hunter.io and Apollo.io")

# Sidebar for settings
with st.sidebar:
    st.header("⚙️ Settings")
    
    # Data source selector
    source = st.selectbox(
        "Choose data source:", 
        ["Hunter.io", "Apollo.io", "Both"],
        help="Hunter.io provides email verification, Apollo.io has broader contact data"
    )
    
    # Hunter-specific filters
    if source in ["Hunter.io", "Both"]:
        st.subheader("🎯 Hunter.io Filters")
        exclude_directors = st.checkbox(
            "Exclude Directors", 
            value=False,
            help="Focus only on C-suite roles, exclude director-level positions"
        )
        only_verified = st.checkbox(
            "Only verified emails", 
            value=False,
            help="Show only emails verified as deliverable"
        )
    else:
        exclude_directors = False
        only_verified = False

# Main content area
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("🏢 Company Domains")
    domains_input = st.text_area(
        "Enter company domains (one per line):",
        height=200,
        placeholder="example.com\ncompany.org\nbusiness.net",
        help="Enter domain names without 'www.' or 'https://'"
    )
    
    # Example domains
    if st.button("📝 Load Example Domains"):
        example_domains = "apple.com\nmicrosoft.com\ngoogle.com\namazon.com\ntesla.com"
        st.text_area("Example domains loaded:", value=example_domains, height=100, disabled=True)

with col2:
    st.subheader("📊 Quick Stats")
    if domains_input.strip():
        domain_list = [d.strip() for d in domains_input.splitlines() if d.strip()]
        st.metric("Domains to search", len(domain_list))
        st.metric("Data source", source)
        if source == "Both":
            st.info("Both sources will be searched for maximum coverage")

# Search button and results
if st.button("🔍 Find Emails", type="primary"):
    if not domains_input.strip():
        st.error("Please enter at least one domain.")
    else:
        domains = [d.strip() for d in domains_input.splitlines() if d.strip()]
        all_results = []
        errors = []
        
        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, domain in enumerate(domains):
            status_text.text(f"🔎 Searching: {domain} ({i+1}/{len(domains)})")
            
            # Search based on selected source
            if source == "Hunter.io":
                data, error = find_hunter_emails(domain, exclude_directors, only_verified)
                if error:
                    errors.append(error)
                else:
                    all_results.extend(data)
                    
            elif source == "Apollo.io":
                data, error = find_apollo_contacts(domain)
                if error:
                    errors.append(error)
                else:
                    all_results.extend(data)
                    
            elif source == "Both":
                # Search both sources
                hunter_data, hunter_error = find_hunter_emails(domain, exclude_directors, only_verified)
                apollo_data, apollo_error = find_apollo_contacts(domain)
                
                if hunter_error:
                    errors.append(f"Hunter - {hunter_error}")
                else:
                    all_results.extend(hunter_data)
                    
                if apollo_error:
                    errors.append(f"Apollo - {apollo_error}")
                else:
                    all_results.extend(apollo_data)
            
            progress_bar.progress((i + 1) / len(domains))
        
        # Clear progress indicators
        progress_bar.empty()
        status_text.empty()
        
        # Show results
        if all_results:
            df = pd.DataFrame(all_results)
            
            # Remove duplicates based on email
            df_unique = df.drop_duplicates(subset=['Email'], keep='first')
            
            st.success(f"✅ Found {len(df_unique)} unique contacts from {len(df)} total results")
            
            # Display results with filtering options
            col1, col2, col3 = st.columns(3)
            with col1:
                company_filter = st.multiselect("Filter by company:", df_unique['Company Name'].unique())
            with col2:
                source_filter = st.multiselect("Filter by source:", df_unique['Source'].unique())
            with col3:
                verified_filter = st.selectbox("Filter by verification:", ["All", "Verified only", "Unverified only"])
            
            # Apply filters
            filtered_df = df_unique.copy()
            if company_filter:
                filtered_df = filtered_df[filtered_df['Company Name'].isin(company_filter)]
            if source_filter:
                filtered_df = filtered_df[filtered_df['Source'].isin(source_filter)]
            if verified_filter == "Verified only":
                filtered_df = filtered_df[filtered_df['Verified'] == 'Yes']
            elif verified_filter == "Unverified only":
                filtered_df = filtered_df[filtered_df['Verified'] == 'No']
            
            st.dataframe(filtered_df, use_container_width=True)
            
            # Download options
            col1, col2 = st.columns(2)
            with col1:
                # Excel download
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    filtered_df.to_excel(writer, index=False, sheet_name='Contacts')
                
                st.download_button(
                    "📥 Download Excel",
                    data=output.getvalue(),
                    file_name="c_suite_contacts.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            
            with col2:
                # CSV download
                csv_data = filtered_df.to_csv(index=False)
                st.download_button(
                    "📄 Download CSV",
                    data=csv_data,
                    file_name="c_suite_contacts.csv",
                    mime="text/csv"
                )
        else:
            st.warning("⚠️ No results found. Try different domains or check your API keys.")
        
        # Show errors if any
        if errors:
            with st.expander("⚠️ Errors encountered", expanded=False):
                for error in errors:
                    st.text(error)

# Footer
st.markdown("---")
st.markdown("💡 **Tips:** Use company domain names without 'www' or 'https'. Both Hunter.io and Apollo.io have rate limits - consider upgrading your API plan for higher volumes.")







