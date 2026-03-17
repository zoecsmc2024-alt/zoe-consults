import streamlit as st
import pandas as pd

# --- 1. CONFIG & ADMIN THEME ---
st.set_page_config(page_title="ZoeLend IQ Pro", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    /* Hide the Sidebar entirely */
    [data-testid="stSidebar"] {display: none;}
    [data-testid="collapsedControl"] {display: none;}
    
    /* Main Content Background */
    .stApp { background-color: #ffffff; }

    /* Admin Header Style */
    .admin-header {
        background-color: #f7f7f7;
        border: 1px solid #e0e0e0;
        padding: 10px 15px;
        margin-bottom: 25px;
        font-weight: bold;
        color: #555;
        border-radius: 4px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    /* Box Cards (Matching your Admin design) */
    .box-card {
        background: white;
        border: 1px solid #e0e0e0;
        padding: 25px;
        border-radius: 4px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .box-title { color: #888; font-size: 0.85em; text-transform: uppercase; margin-bottom: 10px; letter-spacing: 1px; }
    .box-value { color: #333; font-size: 1.8em; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
def load_data():
    try:
        # Try to read your real file
        df = pd.read_csv("zoe_database.csv")
        
        # Clean up column names (remove any accidental spaces)
        df.columns = df.columns.str.strip()
        
        for col in ['LOAN_AMOUNT', 'AMOUNT_PAID', 'INTEREST_RATE']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except Exception as e:
        # If the file is missing, we return a "Mock" row for testing
        data = {
            'SN': [1],
            'CUSTOMER_NAME': ['System Test'],
            'LOAN_AMOUNT': [1000000],
            'AMOUNT_PAID': [200000],
            'STATUS': ['Active']
        }
        return pd.DataFrame(data)

df = load_data()

# --- 3. ERP NAVIGATION HEADER ---
# Top Blue Bar (Tier 1)
st.markdown("""
    <div style="background-color: #3498db; padding: 10px 20px; display: flex; justify-content: space-between; align-items: center; color: white; font-family: sans-serif;">
        <div style="display: flex; gap: 20px; align-items: center;">
            <span>👤 Evans Ahuura</span>
            <b style="font-size: 1.2em;">Zoe Consults</b>
            <span style="background: rgba(255,255,255,0.2); padding: 2px 8px; border-radius: 4px;">🔵 Branch #1</span>
            <span>🏠 Home Branch</span>
        </div>
        <div style="display: flex; gap: 15px; font-size: 0.9em;">
            <span>⚙️ Admin</span><span>🔗 Settings</span><span>🔌 API</span><span>❓ Help</span>
        </div>
    </div>
""", unsafe_allow_html=True)

# Dark Blue Menu Bar (Tier 2)
# We use st.tabs to mimic the look of the "Borrowers", "Loans", "Repayments" menu
menu_tabs = st.tabs(["👥 Borrowers", "⚖️ Loans", "💰 Repayments", "📑 Collateral", "📅 Calendar"])

with menu_tabs[0]: # Borrowers/Dashboard View
    st.write("") # Padding
    
    if not df.empty:
        # 4-Column Summary Row (Boxes)
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f'<div class="box-card"><div class="box-title">Total Borrowers</div><div class="box-value">{len(df)}</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="box-card"><div class="box-title">Principal Released</div><div class="box-value">UGX {df["LOAN_AMOUNT"].sum():,.0f}</div></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="box-card"><div class="box-title">Collections</div><div class="box-value">UGX {df["AMOUNT_PAID"].sum():,.0f}</div></div>', unsafe_allow_html=True)
        with c4:
            active = len(df[df['AMOUNT_PAID'] < df['LOAN_AMOUNT']])
            st.markdown(f'<div class="box-card"><div class="box-title">Active Loans</div><div class="box-value">{active}</div></div>', unsafe_allow_html=True)

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
