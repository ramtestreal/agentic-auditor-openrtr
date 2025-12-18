
import streamlit as st
import requests
from bs4 import BeautifulSoup
from openai import OpenAI  
import pandas as pd
import io
import time
import visuals


# --- UI LAYOUT & STATE MANAGEMENT ---

# 1. Initialize "Memory" (Session State)
if 'audit_data' not in st.session_state:
    st.session_state['audit_data'] = None
if 'recs' not in st.session_state:
    st.session_state['recs'] = None
if 'ai_summary' not in st.session_state:
    st.session_state['ai_summary'] = None
if 'current_url' not in st.session_state:
    st.session_state['current_url'] = ""

st.set_page_config(page_title="Agentic Readiness Auditor Pro", page_icon="🤖", layout="wide")

st.title("🤖 Agentic Readiness Auditor Pro")
st.markdown("### The Standard for Future Commerce")
st.info("Check if your client's website is ready for the **Agent Economy** (Mastercard/Visa Agents, ChatGPT, Gemini).")

# --- FUNCTIONS ---

def detect_tech_stack(soup, headers):
    """Detects if the site is WP, Shopify, Next.js, etc."""
    stack = []
    html = str(soup)
    
    # Check Meta Generators & Script signatures
    if "wp-content" in html or "WordPress" in str(soup.find("meta", attrs={"name": "generator"})):
        stack.append("WordPress")
    if "cdn.shopify.com" in html or "Shopify" in html:
        stack.append("Shopify")
    if "woocommerce" in html:
        stack.append("WooCommerce")
    if "__NEXT_DATA__" in html:
        stack.append("Next.js (React)")
    if "data-reactroot" in html:
        stack.append("React")
    if "Wix" in html or "wix-warmup-data" in html:
        stack.append("Wix")
        
    # Check Headers
    if "X-Powered-By" in headers:
        stack.append(f"Server: {headers['X-Powered-By']}")
        
    return ", ".join(stack) if stack else "Custom/Unknown Stack"

def check_security_gates(url):
    """Checks robots.txt, sitemap, and ai.txt"""
    domain = url.rstrip('/')
    gates = {}
    
    # 1. Robots.txt
    try:
        r = requests.get(f"{domain}/robots.txt", timeout=3)
        if r.status_code == 200:
            gates['robots.txt'] = "Found"
            if "GPTBot" in r.text and "Disallow" in r.text:
                gates['ai_access'] = "BLOCKED (Critical Issue)"
            else:
                gates['ai_access'] = "Allowed"
        else:
            gates['robots.txt'] = "Missing"
            gates['ai_access'] = "Uncontrolled (Risky)"
    except:
        gates['robots.txt'] = "Error"
        gates['ai_access'] = "Unknown"

    # 2. Sitemap (Checks standard, plural, index, and WP native)
    try:
        s1 = requests.get(f"{domain}/sitemap.xml", timeout=3)
        s2 = requests.get(f"{domain}/sitemaps.xml", timeout=3)
        s3 = requests.get(f"{domain}/sitemap_index.xml", timeout=3)
        s4 = requests.get(f"{domain}/wp-sitemap.xml", timeout=3)

        if s1.status_code == 200:
            gates['sitemap.xml'] = "Found (Standard)"
        elif s2.status_code == 200:
            gates['sitemap.xml'] = "Found (sitemaps.xml)"
        elif s3.status_code == 200:
            gates['sitemap.xml'] = "Found (sitemap_index.xml)"
        elif s4.status_code == 200:
            gates['sitemap.xml'] = "Found (wp-sitemap.xml)"
        else:
            gates['sitemap.xml'] = "Missing"
    except:
        gates['sitemap.xml'] = "Error checking"

    # 3. ai.txt (The new standard)
    try:
        a = requests.get(f"{domain}/ai.txt", timeout=3)
        gates['ai.txt'] = "Found (Future Proof!)" if a.status_code == 200 else "Missing"
    except:
        gates['ai.txt'] = "Error"
        
    return gates

def generate_recommendations(audit_data):
    """Generates hard-coded logic recommendations"""
    recs = []
    
    if "BLOCKED" in audit_data['gates']['ai_access']:
        recs.append("CRITICAL: Update robots.txt to whitelist 'GPTBot', 'CCBot', and 'Google-Extended'.")
    
    if audit_data['schema_count'] == 0:
        recs.append("HIGH PRIORITY: Implement JSON-LD Schema. The Agent cannot see your products/prices.")
        
    if "Missing" in audit_data['gates']['ai.txt']:
        recs.append("OPTIMIZATION: Create an 'ai.txt' file to explicitly grant permission to specific AI models.")
        
    if "Next.js" in audit_data['stack'] and audit_data['schema_count'] == 0:
        recs.append("TECH FIX: Your Next.js site might be client-side rendering. Ensure Schema is injected via Server Side Rendering (SSR).")

    return recs

 def perform_audit(url, api_key):
    # --- OPENROUTER CONFIGURATION ---
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
    
    # THE "TANK" STRATEGY: List of Free Models to try in order
    # If #1 fails, it automatically tries #2, then #3.
    model_list = [
        "google/gemini-2.0-flash-exp:free",        # Plan A: Google (Fastest)
        "meta-llama/llama-3.2-11b-vision-instruct:free", # Plan B: Meta (New Llama)
        "microsoft/phi-3-medium-128k-instruct:free",    # Plan C: Microsoft (Reliable)
        "qwen/qwen-2-7b-instruct:free"             # Plan D: Qwen (Good backup)
    ]
    
    status_text = st.empty()
    status_text.text("Connecting to website...")
    
    try:
        # Fetch Page
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; AgenticAuditor/1.0)'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # --- EXTRACT SITE CONTEXT ---
        page_title = soup.title.string if soup.title else "No Title"
        meta_desc = soup.find("meta", attrs={"name": "description"})
        meta_desc_text = meta_desc["content"] if meta_desc else "No Description"
        body_text = soup.body.get_text(separator=' ', strip=True)[:2000] if soup.body else ""
        
        site_context = f"Title: {page_title}\nDescription: {meta_desc_text}\nPage Content: {body_text}"
        
        # 1. Tech Stack
        status_text.text("Detecting Technology Stack...")
        stack = detect_tech_stack(soup, response.headers)
        
        # 2. Security Gates
        status_text.text("Checking Security Gates (robots.txt, ai.txt)...")
        gates = check_security_gates(url)
        
        # 3. Schema Check
        status_text.text("Extracting Semantic Data...")
        schemas = soup.find_all('script', type='application/ld+json')
        schema_sample = schemas[0].string[:500] if schemas else "None"
        
        # 4. Manifest / Identity Check
        status_text.text("Verifying Identity Files...")
        domain = url.rstrip('/')
        
        plugin_res = requests.get(f"{domain}/.well-known/ai-plugin.json", timeout=3)
        web_manifest_res = requests.get(f"{domain}/manifest.json", timeout=3)
        html_manifest = soup.find("link", rel="manifest")
        
        if plugin_res.status_code == 200:
            manifest_status = "Found (AI Plugin)"
        elif web_manifest_res.status_code == 200:
            manifest_status = "Found (Web Manifest)"
        elif html_manifest:
            manifest_status = "Found (Linked in HTML)"
        else:
            manifest_status = "Missing"

        # Compile Data
        audit_data = {
            "url": url,
            "stack": stack,
            "gates": gates,
            "schema_count": len(schemas),
            "schema_sample": schema_sample,
            "manifest": manifest_status
        }
        
        recs = generate_recommendations(audit_data)
        
        # 5. OpenRouter AI Analysis (MULTI-MODEL BACKUP LOGIC)
        status_text.text("Generative AI is formatting the report...")
        
        prompt = f"""
        You are a Senior Technical Consultant. Analyze this website for 'Agentic Readiness'.
        
        TARGET DATA:
        - URL: {url}
        - Tech Stack: {stack}
        - Security Gates: {gates}
        - Schema Found: {len(schemas)} items.
        - Manifest Status: {manifest_status}
        
        WEBSITE CONTEXT:
        {site_context}
        
        YOUR TASK:
        1. Detect the Business Type (E-commerce, SaaS, B2B, Blog, etc.) based on the context.
        
        2. GENERATE A REPORT IN STRICT MARKDOWN FORMAT:
        
        ### 1. Executive Summary
        - Write exactly 3 short, punchy sentences.
        - Use **Bold** for key terms.
        - Tailor language to the business type (e.g., "Buying" for stores, "Lead Gen" for B2B).
            
        ### 2. Business Impact Analysis
        - Provide exactly 3 Bullet Points.
        - Each bullet must start with a **Bold Issue**.
        - Keep each bullet under 25 words. Focus on risk/money.
        """
        
        ai_summary = "Error: Could not generate report."
        
        # Loop through models until one works
        for model_id in model_list:
            try:
                status_text.text(f"Trying AI Model: {model_id.split('/')[1]}...")
                completion = client.chat.completions.create(
                    model=model_id,
                    messages=[{"role": "user", "content": prompt}]
                )
                ai_summary = completion.choices[0].message.content
                status_text.text("Report Generated Successfully!")
                break # It worked! Exit the loop.
            except Exception as e:
                # If this model fails, print error to log (console) and try next
                print(f"Model {model_id} failed: {e}")
                continue # Try the next model in the list
        
        status_text.empty()
        return audit_data, recs, ai_summary

    except Exception as e:
        st.error(f"Audit Failed: {str(e)}")
        return None, None, None
		
       

# --- SIDEBAR & INPUTS ---

# Sidebar for API Key
st.sidebar.title("🕵️‍♂️ Audit Controls")
st.sidebar.markdown("This tool uses **OpenRouter** for free/low-cost AI access.")
api_key = st.sidebar.text_input("Enter OpenRouter API Key", type="password", help="Get a free key at openrouter.ai")

# Main Input
url_input = st.text_input("Enter Client Website URL", value=st.session_state['current_url'], placeholder="https://www.example.com")

# The "Run" Logic
if st.button("🚀 Run Full Audit"):
    if not api_key or not url_input:
        st.error("Please provide both API Key and URL.")
    else:
        # Save URL to memory so it persists
        st.session_state['current_url'] = url_input
        
        # Run the Audit
        data, recommendations, summary = perform_audit(url_input, api_key)
        
        if data:
            st.session_state['audit_data'] = data
            st.session_state['recs'] = recommendations
            st.session_state['ai_summary'] = summary

# 4. Display Logic (Reads from Memory)
if st.session_state['audit_data']:
    st.success("✅ Audit Complete! Report Loaded.")
    
    # --- DISPLAY GRAPHICAL DASHBOARD ---
    visuals.display_dashboard(st.session_state['audit_data'])
    
    # --- DOWNLOAD BUTTONS & TEXT REPORT ---
    st.divider()
    
    st.subheader("📝 Executive Summary")
    st.write(st.session_state['ai_summary'])
    
    st.subheader("🔧 Priority Recommendations")
    for rec in st.session_state['recs']:
        st.warning(rec)
        
    # --- EXCEL REPORT GENERATION ---
    report_dict = {
        "Metric": ["Target URL", "Tech Stack", "Robots.txt Status", "AI.txt Status", "Schema Objects", "AI Manifest"],
        "Status": [
            st.session_state['audit_data']['url'],
            st.session_state['audit_data']['stack'],
            st.session_state['audit_data']['gates']['robots.txt'],
            st.session_state['audit_data']['gates']['ai.txt'],
            f"{st.session_state['audit_data']['schema_count']} found",
            st.session_state['audit_data']['manifest']
        ]
    }
    df_report = pd.DataFrame(report_dict)
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df_report.to_excel(writer, sheet_name='Audit Summary', index=False)
        df_recs = pd.DataFrame(st.session_state['recs'], columns=["Actionable Recommendations"])
        df_recs.to_excel(writer, sheet_name='Action Plan', index=False)
        
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="📥 Download Excel Report",
            data=buffer,
            file_name=f"Agentic_Audit_{int(time.time())}.xlsx",
            mime="application/vnd.ms-excel"
        )
    with col2:
        # The "New Audit" Button (Clears everything)
        if st.button("🔄 Start New Audit"):
            st.session_state['audit_data'] = None
            st.session_state['recs'] = None
            st.session_state['ai_summary'] = None
            st.session_state['current_url'] = "" # Clear the URL box
            st.rerun()
			
			
