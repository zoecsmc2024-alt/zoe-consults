import streamlit as st
import pandas as pd

# --- 1. CONFIG & UPDATED THEME ---
st.set_page_config(page_title="ZoeLend IQ Pro", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    /* 1. App Background - Very Light Blue/Off-White */
    .stApp { background-color: #f8fafc; }

    /* 2. Admin Box Cards - Clean White with Soft Shadows */
    .box-card {
        background: white;
        border: 1px solid #e2e8f0;
        padding: 25px;
        border-radius: 6px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    .box-title { color: #94a3b8; font-size: 0.8em; text-transform: uppercase; margin-bottom: 10px; font-weight: 600; }
    .box-value { color: #1e293b; font-size: 1.8em; font-weight: 800; }

    /* Hide Sidebar things */
    [data-testid="stSidebar"] {display: none;}
    [data-testid="collapsedControl"] {display: none;}
    </style>
""", unsafe_allow_html=True)

# --- 3. UPDATED ERP NAVIGATION HEADER ---
# Deep Navy Top Bar (Tier 1)
st.markdown("""
    <div style="background-color: #0f172a; padding: 12px 25px; display: flex; justify-content: space-between; align-items: center; color: white; border-bottom: 2px solid #00acc1;">
        <div style="display: flex; gap: 20px; align-items: center;">
            <span style="opacity: 0.8; font-size: 0.9em;">👤 Evans Ahuura</span>
            <b style="font-size: 1.3em; letter-spacing: 0.5px;">Zoe Consults</b>
            <span style="background: #00acc1; padding: 2px 10px; border-radius: 20px; font-size: 0.8em;">Branch #1</span>
        </div>
        <div style="display: flex; gap: 20px; font-size: 0.85em; opacity: 0.9;">
            <span>⚙️ Admin</span><span>🔗 Settings</span><span>🔌 API</span><span style="color: #fbbf24;">❓ Help</span>
        </div>
    </div>
""", unsafe_allow_html=True)

# Secondary Navigation (The Tabs)
menu_tabs = st.tabs(["👥 Borrowers", "⚖️ Loans", "💰 Repayments", "📑 Collateral", "📅 Calendar"])
        # THE NEW PORTFOLIO TABLE
        st.markdown("<br><h4 style='color: #555;'>📋 Loan Portfolio Registry</h4>", unsafe_allow_html=True)
        
        # Select specific columns to show
        cols_to_show = ['SN', 'CUSTOMER_NAME', 'LOAN_AMOUNT', 'AMOUNT_PAID', 'STATUS']
        
        # Display as a clean, interactive dataframe
        st.dataframe(
            df[cols_to_show].sort_values('SN', ascending=False),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("System Ready. Please upload 'zoe_database.csv' to populate records.")
