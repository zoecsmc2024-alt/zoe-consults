import streamlit as st
import pandas as pd
import datetime
import os
import plotly.express as px

# --- 1. SETTINGS & THEMING ---
st.set_page_config(page_title="ZoeLend IQ Pro", layout="wide")

# This CSS fixes the table headers and the report card look
st.markdown("""
    <style>
    /* 1. THE GRADIENT SIDEBAR */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%) !important;
        border-right: 1px solid #334155 !important;
    }

    /* 2. BLENDING THE TOP BAR */
    [data-testid="stHeader"] {
        background-color: rgba(255, 255, 255, 0.9) !important;
        backdrop-filter: blur(10px); /* Creates a frosted glass effect */
    }

    /* 3. SIDEBAR TEXT & RADIOS */
    [data-testid="stSidebar"] .st-emotion-cache-17l686q, 
    [data-testid="stSidebar"] p {
        color: #cbd5e1 !important;
        font-weight: 500;
    }

    /* 4. ACTIVE NAVIGATION HIGHLIGHT */
    div[data-testid="stMarkdownContainer"] > p:hover {
        color: #00acc1 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
DB_FILE = "zoe_database.csv"

def load_data():
    cols = ['SN','NAME','NIN','CONTACT','LOCATION','EMPLOYER','NEXT_OF_KIN','DATE_OF_ISSUE','EXPECTED_DUE_DATE','LOAN_AMOUNT','INTEREST_RATE','AMOUNT_PAID','OUTSTANDING_AMOUNT','STATUS']
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        for c in cols:
            if c not in df.columns: df[c] = ""
        df['SN'] = df['SN'].astype(str).str.zfill(5)
        # Ensure numbers are numeric
        df['OUTSTANDING_AMOUNT'] = pd.to_numeric(df['OUTSTANDING_AMOUNT'], errors='coerce').fillna(0)
        return df
    return pd.DataFrame(columns=cols)

def save_data(df):
    df.to_csv(DB_FILE, index=False)

df = load_data()

# --- 3. NAVIGATION & BRANDING ---
with st.sidebar:
    # 1. THE LOGO ENCODING
    logo_content = ""
    if os.path.exists("logo.jpg"):
        import base64
        with open("logo.jpg", "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")
        logo_content = f'<img src="data:image/jpeg;base64,{data}" style="width:120px;">'
    else:
        logo_content = '<h1 style="color: #00acc1; margin:0;">Z</h1>'

    # 2. THE BRANDED HEADER (Aligned perfectly)
    st.markdown(f"""
        <div style="text-align: center; padding: 10px;">
            <div style="background-color: white; border-radius: 15px; padding: 15px; display: inline-block; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
                <div style="width: 120px; height: 120px; border-radius: 50%; overflow: hidden; display: flex; justify-content: center; align-items: center; border: 2px solid #e2e8f0;">
                    {logo_content}
                </div>
            </div>
            <h3 style="color: white; margin-top: 15px; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">ZOE LEND IQ <span style="color:#00acc1; font-weight:bold;">PRO</span></h3>
            <p style="color: #94a3b8; font-size: 0.8em; margin-bottom: 20px;">Micro-Lending Management</p>
        </div>
        <div style='border-top: 1px solid #334155; margin-bottom: 20px;'></div>
    """, unsafe_allow_html=True)

    # 3. NAVIGATION (Make sure these are indented 4 spaces from 'with')
    st.markdown("<p style='color: #64748b; font-size: 0.7em; font-weight: bold; letter-spacing: 1.5px; margin-left: 5px;'>MAIN MENU</p>", unsafe_allow_html=True)
    choice = st.radio("Navigation", ["📊 Daily Report", "👤 Onboarding", "💰 Payments", "📄 Client Report"], label_visibility="collapsed")
    
    # 3. THE ACTION HUB
    st.markdown("<p style='color: #64748b; font-size: 0.7em; font-weight: bold; letter-spacing: 1.5px; margin-left: 5px;'>SYSTEM ACTIONS</p>", unsafe_allow_html=True)
    
    if not df.empty:
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 EXPORT DATABASE",
            data=csv,
            file_name=f"Zoe_Lend_DB_{datetime.date.today()}.csv",
            mime="text/csv",
            use_container_width=True
        )

    if st.button("🔓 SECURE LOGOUT", key="sidebar_logout", use_container_width=True):
        st.rerun()

    # 4. ADVANCED BUTTON STYLING (The Final Polish)
    st.markdown("""
        <style>
        /* Sidebar container tweaks */
        section[data-testid="stSidebar"] {
            border-right: 1px solid #334155;
        }
        
        /* Navigation Radio Styling */
        div[data-testid="stSidebarNav"] { display: none; }
        div[data-testid="stWidgetLabel"] { color: #94a3b8 !important; }
        
        /* The Buttons */
        .stDownloadButton button {
            background-color: #00acc1 !important;
            color: white !important;
            border-radius: 8px !important;
            border: none !important;
            font-weight: 600 !important;
            transition: 0.3s !important;
            box-shadow: 0 4px 10px rgba(0, 172, 193, 0.2) !important;
        }
        
        .stButton button {
            background-color: transparent !important;
            color: #ef4444 !important;
            border: 1px solid #ef4444 !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            transition: 0.3s !important;
        }
        
        .stButton button:hover {
            background-color: #ef4444 !important;
            color: white !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # 5. FOOTER
    st.markdown(f"""
        <div style="position: fixed; bottom: 10px; left: 10px; font-size: 0.7em; color: #475569;">
            Zoe Consults Ltd<br>
            March 2026 Release
        </div>
    """, unsafe_allow_html=True)
# --- 4. PAGES ---

if choice == "📊 Daily Report":
    st.title("📊 Portfolio Insights")
    
    if not df.empty:
        # --- PROFIT CALCULATOR LOGIC ---
        # 1. Total interest expected from all loans
        total_expected_interest = (df['LOAN_AMOUNT'] * (df['INTEREST_RATE'] / 100)).sum()
        
        # 2. Interest actually earned (Pro-rated based on payments)
        # We calculate the 'Profit Ratio' for each loan
        df['profit_ratio'] = (df['LOAN_AMOUNT'] * (df['INTEREST_RATE']/100)) / (df['LOAN_AMOUNT'] + (df['LOAN_AMOUNT'] * (df['INTEREST_RATE']/100)))
        total_profit_earned = (df['AMOUNT_PAID'] * df['profit_ratio']).sum()

        # --- METRICS DISPLAY ---
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Principal", f"UGX {df['LOAN_AMOUNT'].sum():,.0f}")
        m2.metric("Total Collected", f"UGX {df['AMOUNT_PAID'].sum():,.0f}")
        m3.metric("Outstanding", f"UGX {df['OUTSTANDING_AMOUNT'].sum():,.0f}")
        # The New "Gold" Metric
        m4.metric("Total Profit", f"UGX {total_profit_earned:,.0f}", help="Total interest earned from payments received so far.")

        # ... (Rest of your registry table code follows)

        # --- 2. BUSINESS GROWTH CHART (Principal vs. Profit) ---
        st.subheader("📈 Business Growth Strategy")
        
        if not df.empty:
            # Prepare the data for a time-series view
            chart_df = df.copy()
            chart_df['DATE_OF_ISSUE'] = pd.to_datetime(chart_df['DATE_OF_ISSUE'])
            chart_df = chart_df.sort_values('DATE_OF_ISSUE')
            
            # Calculate cumulative values
            chart_df['Cumulative_Principal'] = chart_df['LOAN_AMOUNT'].cumsum()
            chart_df['Cumulative_Profit'] = (chart_df['AMOUNT_PAID'] * chart_df['profit_ratio']).cumsum()
            
            # Melt the data so Plotly can understand the two different categories
            plot_df = chart_df.melt(id_vars='DATE_OF_ISSUE', 
                                    value_vars=['Cumulative_Principal', 'Cumulative_Profit'],
                                    var_name='Type', value_name='Amount')
            
            # Create a beautiful Stacked Area Chart
            fig = px.area(plot_df, 
                          x='DATE_OF_ISSUE', 
                          y='Amount', 
                          color='Type',
                          color_discrete_map={
                              'Cumulative_Principal': '#1e293b', # Slate
                              'Cumulative_Profit': '#00acc1'    # Zoe Teal
                          },
                          labels={'Amount': 'Value (UGX)', 'DATE_OF_ISSUE': 'Time'},
                          template="simple_white")
            
            fig.update_layout(hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)

        # 3. CONSOLIDATED PREMIUM REGISTRY (Colors Restored)
        st.subheader("📋 Loan Portfolio Registry")

        def apply_premium_styling(row):
            try:
                due = pd.to_datetime(row['EXPECTED_DUE_DATE']).date()
                balance = float(row['OUTSTANDING_AMOUNT'])
                # Soft Red for Overdue
                if datetime.date.today() > due and balance > 0:
                    return ['background-color: #fee2e2; color: #991b1b; font-weight: bold'] * len(row)
                # Soft Green for Cleared
                if row['STATUS'] == 'Cleared':
                    return ['background-color: #dcfce7; color: #166534'] * len(row)
            except:
                pass
            return [''] * len(row)

        # THE CSS MASTER FIX: Forces Teal Header AND Hides the Index Column
        st.markdown("""
            <style>
                /* Force Teal Header */
                thead tr th {
                    background-color: #00acc1 !important;
                    color: white !important;
                }
                /* Hide the annoying first index column */
                tbody th { display: none; }
                .blank { display: none; }
            </style>
        """, unsafe_allow_html=True)

        display_cols = ['SN', 'NAME', 'DATE_OF_ISSUE', 'EXPECTED_DUE_DATE', 'OUTSTANDING_AMOUNT', 'STATUS']
        
        # Using st.table ensures the row colors (Red/Green) are forced to show
        st.table(df[display_cols].style.apply(apply_premium_styling, axis=1).format({
            "OUTSTANDING_AMOUNT": "{:,.0f}"
        }))

        # 4. QUICK EDIT ACTION (The "Pencil" section)
        with st.expander("✏️ Quick Modify Client"):
            edit_sn = st.selectbox("Select Serial Number:", ["Select..."] + df['SN'].tolist())
            if edit_sn != "Select...":
                idx = df[df['SN'] == edit_sn].index[0]
                with st.form("quick_edit"):
                    st.write(f"Editing **{df.at[idx, 'NAME']}**")
                    new_stat = st.selectbox("Update Status", ["Active", "Risky", "Cleared", "Dormant"], index=["Active", "Risky", "Cleared", "Dormant"].index(df.at[idx, 'STATUS']))
                    if st.form_submit_button("Update Status"):
                        df.at[idx, 'STATUS'] = new_stat
                        save_data(df)
                        st.success("Status Updated!"); st.rerun()
elif choice == "👤 Onboarding":
    st.title("👤 New Loan")
    with st.form("onboard"):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("FULL NAME").upper(); nin = st.text_input("NIN")
            loc = st.text_input("LOCATION"); emp = st.text_input("EMPLOYER")
        with c2:
            amt = st.number_input("LOAN AMOUNT", min_value=1000)
            rate = st.number_input("RATE (%)", value=3); dur = st.number_input("MONTHS", min_value=1, value=1)
            due = datetime.date.today() + datetime.timedelta(days=30*dur)
        if st.form_submit_button("✅ Save"):
            new_sn = str(len(df) + 1).zfill(5)
            new_row = pd.DataFrame([{'SN': new_sn, 'NAME': name, 'NIN': nin, 'LOCATION': loc, 'EMPLOYER': emp, 'DATE_OF_ISSUE': datetime.date.today().strftime('%d-%b-%Y'), 'EXPECTED_DUE_DATE': due.strftime('%d-%b-%Y'), 'LOAN_AMOUNT': amt, 'INTEREST_RATE': rate, 'AMOUNT_PAID': 0, 'OUTSTANDING_AMOUNT': amt+(amt*(rate/100)), 'STATUS': 'Active'}])
            df = pd.concat([df, new_row], ignore_index=True); save_data(df); st.success("Done!"); st.rerun()

elif choice == "💰 Payments":
    st.title("💰 Post Payment")
    with st.form("pay"):
        sn = st.text_input("Enter SN").strip().zfill(5)
        p_amt = st.number_input("Amount", min_value=100)
        if st.form_submit_button("Confirm"):
            idx = df[df['SN'] == sn].index
            if not idx.empty:
                df.at[idx[0], 'AMOUNT_PAID'] += p_amt; df.at[idx[0], 'OUTSTANDING_AMOUNT'] -= p_amt
                if df.at[idx[0], 'OUTSTANDING_AMOUNT'] <= 0: df.at[idx[0], 'STATUS'] = 'Cleared'
                save_data(df); st.success("Paid!"); st.rerun()
            else: st.error("Not found.")

elif choice == "📄 Client Report":
    # 1. TOP PROFILE HEADER (Inspired by your image)
    if not df.empty:
        client_options = df.apply(lambda x: f"{str(x['SN']).zfill(5)} - {x['NAME']}", axis=1).tolist()
        selected_client = st.selectbox("Search Borrower", client_options)
        c = df[df['SN'].astype(str).str.zfill(5) == selected_client.split(" - ")[0]].iloc[0]

        st.markdown(f"""
            <div style="background-color: white; padding: 20px; border-radius: 10px; border-top: 5px solid #00acc1; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <div style="display: flex; justify-content: space-between;">
                    <div>
                        <h2 style="margin:0; color:#1e293b;">{c['NAME']}</h2>
                        <p style="color:#00acc1; font-weight:bold; margin:0;">CL-{c['SN']}</p>
                        <p style="font-size:0.8em; color:gray;">Issued: {c['DATE_OF_ISSUE']}</p>
                    </div>
                    <div style="text-align: right; font-size:0.9em;">
                        <p><b>Address:</b> {c['LOCATION']}</p>
                        <p><b>NIN:</b> {c['NIN']}</p>
                        <p><b>Employer:</b> {c['EMPLOYER']}</p>
                    </div>
                </div>
                <div style="margin-top:15px;">
                    <span style="background-color:#00acc1; color:white; padding:5px 15px; border-radius:5px; font-size:0.8em;">Add Loan</span>
                    <span style="background-color:#1e293b; color:white; padding:5px 15px; border-radius:5px; font-size:0.8em; margin-left:10px;">View All Loans</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

        st.write("")

        # 2. MAIN LOAN SUMMARY BAR (Teal Theme)
        st.markdown("""
            <style>
            .loan-header { background-color: #e0f7fa; color: #00838f; padding: 10px; font-weight: bold; border-bottom: 2px solid #00acc1; display: flex; justify-content: space-between; }
            .loan-row { background-color: white; padding: 15px; display: flex; justify-content: space-between; border-bottom: 1px solid #eee; font-size: 0.9em; }
            </style>
        """, unsafe_allow_html=True)

        st.markdown(f"""
            <div class="loan-header">
                <span>Loan#</span><span>Principal</span><span>Interest</span><span>Due</span><span>Paid</span><span>Balance</span><span>Status</span>
            </div>
            <div class="loan-row">
                <span>LN-{c['SN']}</span>
                <span>{float(c['LOAN_AMOUNT']):,.0f}</span>
                <span>{c['INTEREST_RATE']}%</span>
                <span>{float(c['OUTSTANDING_AMOUNT']) + float(c['AMOUNT_PAID']):,.0f}</span>
                <span>{float(c['AMOUNT_PAID']):,.0f}</span>
                <span style="color:#00838f; font-weight:bold;">{float(c['OUTSTANDING_AMOUNT']):,.0f}</span>
                <span style="background-color:#00acc1; color:white; padding:2px 8px; border-radius:4px; font-size:0.8em;">{c['STATUS']}</span>
            </div>
        """, unsafe_allow_html=True)

        # 3. THE TABBED NAVIGATION (Just like your image!)
        st.write("")
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Repayments", "📝 Loan Terms", "📅 Schedule", "📎 Files"])

        with tab1:
            st.subheader("Repayment History")
            # Creating the ledger table to look like the image
            ledger_df = pd.DataFrame([
                {"Date": c['DATE_OF_ISSUE'], "Description": "Loan Released", "Principal": c['LOAN_AMOUNT'], "Interest": 0, "Total": c['LOAN_AMOUNT']},
                {"Date": "To Date", "Description": "Collections Received", "Principal": 0, "Interest": 0, "Total": f"-{c['AMOUNT_PAID']}"}
            ])
            st.table(ledger_df)
            st.button("➕ Add Repayment")

        with tab2:
            st.info(f"Monthly Interest Rate: {c['INTEREST_RATE']}% | Next of Kin: {c['NEXT_OF_KIN']}")

        with tab3:
            st.write(f"Final Maturity Date: **{c['EXPECTED_DUE_DATE']}**")
