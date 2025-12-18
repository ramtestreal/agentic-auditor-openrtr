import streamlit as st
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import pandas as pd
import io
import time
import visuals  # Ensure visuals.py exists in your repo

# --- CONFIGURATION ---
st.set_page_config(page_title="Agentic Readiness Auditor Pro", page_icon="🕵️‍♂️", layout="wide")

# --- SESSION STATE INITIALIZATION ---
if 'audit_data' not in st.session_state:
    st.session_state['audit_data'] = None
if 'recs' not in st.session_state:
    st.session_state['recs'] = None
if 'ai_summary' not in st.session_state:
    st.session_state['ai_summary'] = None
if 'current_url' not in st.session_state:
    st.session_state['current_url'] = ""

# --- FUNCTIONS ---

def detect_tech_stack(soup, headers):
    """Detects if the site is WP, Shopify, Next.js, etc."""
    stack = []
    html = str(soup)
    
    if "wp-content" in html or "WordPress" in str(soup.find("meta", attrs={"name": "generator"})):
        stack.append("WordPress")
    if "cdn.shopify.com" in html or "Shopify" in html:
        stack.append("Shopify")
    if "woocommerce" in html:
        stack.append("WooCommerce")
    if "__NEXT_DATA__" in html:
        stack.append("Next.js")
    if "Wix" in html:
        stack.append("Wix")
    if "Squarespace" in html:
        stack.append("Squarespace")
        
    return ", ".join(stack) if stack else "Custom/Unknown Stack"

def check_security_gates(url):
    domain = url.rstrip('/')
    gates = {}
    
    # 1. Robots.txt
    try:
        r = requests.get(f"{domain}/robots.txt", timeout=3)
        if r.status_code == 200:
            gates['robots.txt'] = "Found"
            if "GPTBot" in r.text and "Disallow" in r.text:
                gates['ai_access'] = "BLOCKED (Critical)"
            else:
                gates['ai_access'] = "Allowed"
        else:
            gates['robots.txt'] = "Missing"
            gates['ai_access'] = "Uncontrolled"
    except:
        gates['robots.txt'] = "Error"
        gates['ai_access'] = "Unknown"

    # 2. Sitemap
    try:
        s_urls = [f"{domain}/sitemap.xml", f"{domain}/sitemaps.xml", f"{domain}/sitemap_index.xml", f"{domain}/wp-sitemap.xml"]
        found_sitemap = False
        for s_url in s_urls:
            try:
                if requests.get(s_url, timeout=2).status_code == 200:
                    gates['sitemap.xml'] = f"Found ({s_url.split('/')[-1]})"
                    found_sitemap = True
                    break
            except:
                continue
        if not found_sitemap:
            gates['sitemap.xml'] = "Missing"
    except:
        gates['sitemap.xml'] = "Error checking"

    # 3. ai.txt
    try:
        if requests.get(f"{domain}/ai.txt", timeout=3).status_code == 200:
            gates['ai.txt'] = "Found"
        else:
            gates['ai.txt'] = "Missing"
    except:
        gates['ai.txt'] = "Error"
        
    return gates

def generate_recommendations(audit_data):
    recs = []
    if "BLOCKED" in audit_data['gates']['ai_access']:
        recs.append("CRITICAL: Update robots.txt to whitelist 'GPTBot' and 'Google-Extended'.")
    if audit_data['schema_count'] == 0:
        recs.append("HIGH PRIORITY: Implement JSON-LD Schema. Agents cannot understand your content structure.")
    if "Missing" in audit_data['gates']['ai.txt']:
        recs.append("OPTIMIZATION: Create an 'ai.txt' file to explicitly grant permission to specific AI models.")
    return recs

def generate_fallback_summary(audit_data, page_title=""):
    """FAIL-SAFE: Writes a report manually if AI fails."""
    
    # 1. SMARTER DETECTION LOGIC
    # Convert title to lowercase for checking
    title_lower = page_title.lower() if page_title else ""
    
    # Keywords that suggest a SERVICE even if they use WooCommerce
    service_keywords = ["service", "laundry", "cleaner", "consulting", "agency", "solution", "manpower", "booking", "repair"]
    
    is_service = any(word in title_lower for word in service_keywords)
    has_shop_tech = "Shopify" in audit_data['stack'] or "WooCommerce" in audit_data['stack']
    
    # It is E-commerce ONLY if it has shop tech AND is NOT a service
    is_ecommerce = has_shop_tech and not is_service
       
    status_text = st.empty()
    status_text.text("Connecting to website...")

    if is_ecommerce:
        summary = f"""
### 1. Executive Summary
This **E-commerce** site using {audit_data['stack']} is accessible but lacks key Agentic protocols. The absence of an **ai.txt** file means AI buyers have no clear rules. Without specific permissions, automated **transactions** and product discovery may be unreliable.

### 2. Business Impact Analysis
* **Missing ai.txt:** Agents cannot verify permissions, leading to abandoned **autonomous carts**.
* **Schema Gaps:** Products may be invisible to price-comparison bots, causing lost **sales**.
* **Risk:** Competitors with optimized 'Agent Ready' sites will capture the AI-driven market share.
"""
    else:
        # Default to Service/Content for everything else
        summary = f"""
### 1. Executive Summary
This **Service/Content** site runs on {audit_data['stack']} and lacks essential **Agentic** standards. The absence of an **ai.txt** file prevents controlled **content retrieval** by AI systems. This limits the site's ability to be accurately cited by LLMs for **lead generation** and answers.

### 2. Business Impact Analysis
* **Missing ai.txt:** AI agents may scrape irrelevant data or ignore the site, reducing **brand visibility**.
* **Schema Gaps:** Services cannot be machine-read, leading to **hallucinated** answers about your business.
* **Risk:** Reduced organic traffic from AI-powered search engines like SearchGPT.
"""
    return summary + "\n\n*(Note: Generated by Fallback Logic due to AI Service Congestion)*"

def perform_audit(url, api_key):
    # OPENROUTER CONNECTION
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
    
    models = [
        "google/gemini-2.0-flash-exp:free",        
        "meta-llama/llama-3.2-11b-vision-instruct:free", 
        "microsoft/phi-3-medium-128k-instruct:free",    
        "huggingfaceh4/zephyr-7b-beta:free"             
    ]
    
    status_msg = st.empty()
    status_msg.text("🔍 Scanning website structure...")
    
    try:
        # --- ROBUST CONNECTION HANDLER ---
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; AgenticAuditor/1.0)'}
        try:
            response = requests.get(url, headers=headers, timeout=15)
        except requests.exceptions.RequestException:
            status_msg.error(f"Could not connect to {url}. Please check spelling.")
            return None, None, None

        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Gather Context
        title = soup.title.string if soup.title else "No Title"
        body = soup.body.get_text(separator=' ', strip=True)[:1000] if soup.body else ""
        context = f"Title: {title}\nContent: {body}"
        
        # Run Checks
        stack = detect_tech_stack(soup, response.headers)
        gates = check_security_gates(url)
        schemas = soup.find_all('script', type='application/ld+json')
        
        # Manifest Check
        domain = url.rstrip('/')
        manifest = "Missing"
        try:
            if requests.get(f"{domain}/manifest.json", timeout=2).status_code == 200:
                manifest = "Found"
            elif soup.find("link", rel="manifest"):
                manifest = "Found (Linked)"
        except:
            pass

        audit_data = {
            "url": url,
            "stack": stack,
            "gates": gates,
            "schema_count": len(schemas),
            "schema_sample": "",
            "manifest": manifest
        }
        recs = generate_recommendations(audit_data)
        
        # AI Generation
        status_text.text("Generative AI is reading the content to identify business type...")
        prompt = f"""
           You are a Senior Technical Consultant specializing in AI Agents, Autonomous Transactions, and Machine-Readable Web Infrastructure.

        Your task is to evaluate the following website for **Agentic Readiness** — the ability for AI agents (LLMs, commerce agents, discovery agents) to correctly understand, retrieve, and act on this website’s content.

 TARGET DATA:
- URL: {url}
- Detected Tech Stack:
{stack}
- Access & Control Signals & Security Gates: {gates}
- Manifest Status: {manifest}
- Structured Data:
 JSON-LD Objects Detected: {len(schemas)}  items.

  WEBSITE CONTEXT:
        {context}

CRITICAL ANALYSIS RULES (DO NOT IGNORE)

• Do NOT assume business type based only on tech stack.
• WooCommerce / Shopify does NOT automatically mean E-commerce.
• Classify based on **what the business sells or offers**, not how it is built.
• Prefer content intent, wording, services, offerings, and audience signals.
• If multiple models apply, choose the **primary revenue model**.


TASK 1 — BUSINESS MODEL CLASSIFICATION

Identify the **primary business type** from the list below (choose ONE):

B2B Service  
B2C Service  
SaaS / Software Platform  
E-commerce / DTC  
Marketplace / Aggregator  
Training / Education  
AI Platform / AI Tool  
Content Publisher / Blog / Media  
Corporate / Enterprise Website  
Hybrid (specify dominant model)

Return ONLY:
Business Type: <type>
Primary Offering: <1 short phrase>


TASK 2 — EXECUTIVE SUMMARY (MAX 3 SENTENCES):
Write a concise executive summary explaining this site’s **current Agentic Readiness**.

Language rules:
• Match vocabulary to the business type
• Be factual, not promotional
• No buzzwords unless technically relevant

Guidance:
• E-commerce → autonomous buying, product discovery, transactions
• B2B / Services → service discovery, lead qualification, trust signals
• SaaS / AI Tools → API discoverability, feature comprehension, onboarding
• Training / Content → citation accuracy, retrieval quality, semantic clarity


TASK 3 — BUSINESS-IMPACT ANALYSIS (BULLETS ONLY):
Explain how missing or weak elements affect **AI agent behavior**, not SEO.

Focus on:
• ai.txt absence → permission ambiguity / agent avoidance
• Schema gaps → misunderstanding, hallucination, invisibility
• Access controls → blocked agents, partial retrieval
• Manifest gaps → poor agent execution or task continuity

Write 3–5 bullets.
Each bullet must:
• Start with the missing element
• End with a **real business consequence**


OUTPUT CONSTRAINTS:
• No headings outside requested sections
• No markdown tables
• No recommendations (handled elsewhere)
• No future speculation beyond current signals
• Be deterministic and precise
"""
        
        ai_summary = None
        for model in models:
            try:
                completion = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}]
                )
                ai_summary = completion.choices[0].message.content
                if ai_summary: break
            except:
                continue 
        
        # FAIL-SAFE: If AI failed, use Smart Fallback
        if not ai_summary:
            # We pass the PAGE TITLE to help the fallback guess correctly
            page_title_str = soup.title.string if soup.title else ""
            ai_summary = generate_fallback_summary(audit_data, page_title_str)
            
        status_msg.empty()
        return audit_data, recs, ai_summary

    except Exception as e:
        status_msg.error(f"Analysis Error: {str(e)}")
        return None, None, None

# --- UI LAYOUT ---

st.sidebar.title("🕵️‍♂️ Audit Controls")
user_input_key = st.sidebar.text_input("OpenRouter API Key", type="password", help="Leave empty to use system key")

if user_input_key:
    api_key = user_input_key
else:
    api_key = "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" # PASTE YOUR KEY HERE IF NEEDED

st.title("🤖 Agentic Readiness Auditor Pro")
st.markdown("### The Standard for Future Commerce")
st.info("Check if your client's website is ready for the **Agent Economy** (Mastercard/Visa Agents, ChatGPT, Gemini).")

# Main Input
if 'current_url' not in st.session_state:
    st.session_state['current_url'] = ""

# --- FORM FOR 'ENTER' KEY SUPPORT ---
with st.form(key='audit_form'):
    url_input_raw = st.text_input("Enter Client Website URL", placeholder="example.com")
    submit_button = st.form_submit_button("🚀 Run Full Audit")

# --- LOGIC HANDLING ---
if submit_button:
    if not api_key:
        st.error("Please provide an API Key in the sidebar.")
    elif not url_input_raw:
        st.error("Please provide a URL.")
    else:
        # --- SMART URL CLEANER ---
        clean_url = url_input_raw.strip()
        if not clean_url.startswith(("http://", "https://")):
            clean_url = "https://" + clean_url
            
        # Clear & Save
        st.session_state['audit_data'] = None
        st.session_state['recs'] = None
        st.session_state['ai_summary'] = None
        st.session_state['current_url'] = clean_url
        
        # Run Audit
        data, recommendations, summary = perform_audit(clean_url, api_key)
        
        if data:
            st.session_state['audit_data'] = data
            st.session_state['recs'] = recommendations
            st.session_state['ai_summary'] = summary

# --- REPORT DISPLAY ---
report_view = st.empty()

if st.session_state['audit_data']:
    with report_view.container():
        st.success(f"✅ Audit Complete for {st.session_state['audit_data']['url']}")
        
        visuals.display_dashboard(st.session_state['audit_data'])

        st.divider()  
        
        st.subheader("📝 Executive Summary")
        st.write(st.session_state['ai_summary'])
        
        st.subheader("🔧 Priority Recommendations")
        for rec in st.session_state['recs']:
            st.warning(rec)
            
        # Excel Report
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
            if st.button("🔄 Start New Audit"):
                st.session_state['audit_data'] = None
                st.session_state['recs'] = None
                st.session_state['ai_summary'] = None
                st.session_state['current_url'] = ""
                st.rerun()
