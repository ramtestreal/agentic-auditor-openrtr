import streamlit as st
import plotly.graph_objects as go

def calculate_score(audit_data):
    """Calculates a score out of 100 based on findings"""
    score = 0
    
    # 1. Robots.txt (Foundation)
    if audit_data['gates']['robots.txt'] == "Found":
        score += 20
        
    # 2. AI Access (Critical)
    if "Allowed" in audit_data['gates']['ai_access']:
        score += 20
        
    # 3. Sitemap (Discovery)
    if "Found" in audit_data['gates']['sitemap.xml']:
        score += 20
        
    # 4. Schema (Understanding)
    if audit_data['schema_count'] > 0:
        score += 20
        
    # 5. AI.txt OR Manifest (Bonus points/Future Proofing)
    if "Found" in audit_data['gates']['ai.txt'] or "Found" in audit_data['manifest']:
        score += 20
        
    return score

def get_score_color(score):
    """Returns color hex code based on score"""
    if score <= 20:
        return "#d90429" # Deep Red
    elif score <= 40:
        return "#ef233c" # Red
    elif score <= 60:
        return "#ff8c00" # Dark Orange
    elif score <= 80:
        return "#ffb703" # Amber
    else:
        return "#008000" # Green

def create_gauge_chart(score):
    """Creates a beautified rounded gauge chart"""
    score_color = get_score_color(score)

    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = score,
        number = {'font': {'color': score_color, 'size': 40}},
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Agentic Readiness Score", 'font': {'size': 24}},
        gauge = {
            'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': score_color, 'thickness': 0.2},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 20], 'color': "#d90429"},
                {'range': [20, 40], 'color': "#ef233c"},
                {'range': [40, 60], 'color': "#ff8c00"},
                {'range': [60, 80], 'color': "#ffb703"},
                {'range': [80, 100], 'color': "#008000"}
            ],
            'threshold': {
                'line': {'color': "black", 'width': 4},
                'thickness': 0.75,
                'value': score
            }
        }
    ))
    fig.update_layout(height=350, margin=dict(l=30, r=30, t=80, b=30), font={'family': "Arial"})
    return fig

def display_dashboard(audit_data):
    """Main function to display the graphics"""
    
    # 1. Calculate Score
    score = calculate_score(audit_data)
    
    # 2. Display Top Section (Gauge + Stack)
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.plotly_chart(create_gauge_chart(score), use_container_width=True)
        
    with col2:
        # Renamed from "Tech Stack" to "Digital Infrastructure"
        st.markdown("### 🏗️ Digital Infrastructure")
        st.info(f"{audit_data['stack']}")
        
        # Universal Messages
      if score < 50:
            st.error("❌ High Risk: AI Agents/LLMs will likely ignore this site.")
        elif score < 80:
            st.warning("⚠️ Partial Access: Agents might struggle to purchase.")
        else:
            st.success("✅ Certified: Website Ready for AI Agents/LLMs Discoverable and Retrievable!")

    st.divider()

    # 3. Status Grid (The "Vertical Cards")
    # Renamed Header to Abstract "Access Protocols"
    st.markdown("### 🛡️ AI Access Protocols")
    
    def get_status_visual(status, label):
        if "Found" in status or "Allowed" in status:
            return "✅", "ACTIVE", status
        elif "Missing" in status:
            return "❌", "INACTIVE", "Missing"
        else:
            return "⚠️", "WARN", status

    # Create 4 columns for metrics
    m1, m2, m3, m4 = st.columns(4)
    
    # 1. Robots.txt -> "Crawlability Status"
    icon, state, desc = get_status_visual(audit_data['gates']['robots.txt'], "")
    m1.metric(label="1. Crawlability Status", value=state, delta=icon)
    
    # 2. AI Access -> "AI Model Permission"
    icon, state, desc = get_status_visual(audit_data['gates']['ai_access'], "")
    m2.metric(label="2. AI Model Permission", value=state, delta=icon)
    
    # 3. ai.txt -> "Agent Directives"
    icon, state, desc = get_status_visual(audit_data['gates']['ai.txt'], "")
    m3.metric(label="3. Agent Directives", value=state, delta=icon)
    
    # 4. Sitemap -> "Content Discovery"
    icon, state, desc = get_status_visual(audit_data['gates']['sitemap.xml'], "")
    m4.metric(label="4. Content Discovery", value=state, delta=icon)
    
    st.divider()
    
    # 4. Data Layer (Schema & Manifest)
    c1, c2 = st.columns(2)
    
    with c1:
        # Renamed "Semantic Data (Schema)" to "Contextual Intelligence"
        st.markdown("#### 🧠 Contextual Intelligence")
        if audit_data['schema_count'] > 0:
            # Renamed "Schema Objects" to "Data Layers"
            st.metric(label="Data Layers Detected", value=audit_data['schema_count'], delta="Active")
            st.progress(100, text="Content is machine-readable")
        else:
            st.metric(label="Data Layers Detected", value="0", delta="- Critical")
            st.progress(0, text="Content is unstructured/invisible")
            
    with c2:
        # Renamed "App Identity (Manifest)" to "Commerce Identity"
        st.markdown("#### 🆔 Commerce Identity")
        if "Found" in audit_data['manifest']:
            st.metric(label="Platform Status", value="Verified", delta="Active")
            st.progress(100, text="Verified Digital Asset")
        else:
            st.metric(label="Platform Status", value="Unverified", delta="- Warning")
            st.progress(0, text="Identity file missing")

    st.divider()
