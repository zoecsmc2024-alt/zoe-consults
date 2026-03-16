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
    [data-testid="stSidebar"] { background-color: #1e293b !important; }
    [data-testid="stSidebar"] * { color: white !important; }
    th { background-color: #00acee !important; color: white !important; }
    .report-card { background-color: #ffffff; padding: 25px; border-radius: 12px; border: 1px solid #e2e8f0; color: black; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
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
    # 1. THE BRANDED HEADER
    st.markdown("""
        <div style="text-align: center; padding: 10px;">
            <div style="background-color: white; border-radius: 15px; padding: 10px; display: inline-block; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
    """, unsafe_allow_html=True)
    
    if os.path.exists("logo.jpg"):
        st.image("logo.jpg", width=120)
    else:
        st.markdown("<h1 style='color: #00acc1; margin:0;'>Z</h1>", unsafe_allow_html=True)
    
    st.markdown("""
            </div>
            <h3 style="color: white; margin-top: 15px; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">ZOE LEND IQ <span style="color:#00acc1; font-weight:bold;">PRO</span></h3>
            <p style="color: #94a3b8; font-size: 0.8em; margin-bottom: 20px;">Micro-Lending Management</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<div style='border-top: 1px solid #334155; margin-bottom: 20px;'></div>", unsafe_allow_html=True)
    
    # 2. THE NAVIGATION MENU
    # We use a custom label to make it look cleaner
    st.markdown("<p style='color: #64748b; font-size: 0.7em; font-weight: bold; letter-spacing: 1.5px; margin-left: 5px;'>MAIN MENU</p>", unsafe_allow_html=True)
    choice = st.radio("Navigation", ["📊 Daily Report", "👤 Onboarding", "💰 Payments", "📄 Client Report"], label_visibility="collapsed")
    
    st.markdown("<div style='margin-top: 30px; border-top: 1px solid #334155; margin-bottom: 20px;'></div>", unsafe_allow_html=True)
    
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
    
    if df.empty:
        st.info("Portfolio is empty. Onboard your first client to see analytics.")
    else:
        # 1. TOP SUMMARY METRICS (Styled like your reference image)
        t_principal = df['LOAN_AMOUNT'].sum()
        t_collected = df['AMOUNT_PAID'].sum()
        t_outstanding = df['OUTSTANDING_AMOUNT'].sum()
        
        m1, m2, m3 = st.columns(3)
        with m1:
            st.markdown(f"""<div style="background-color: #00acc1; padding: 20px; border-radius: 10px; color: white;">
                <p style="margin:0; font-size: 0.8em; opacity: 0.8;">TOTAL DISBURSED</p>
                <h2 style="margin:0;">UGX {t_principal:,.0f}</h2>
            </div>""", unsafe_allow_html=True)
        with m2:
            st.markdown(f"""<div style="background-color: #1e293b; padding: 20px; border-radius: 10px; color: white;">
                <p style="margin:0; font-size: 0.8em; opacity: 0.8;">TOTAL COLLECTED</p>
                <h2 style="margin:0;">UGX {t_collected:,.0f}</h2>
            </div>""", unsafe_allow_html=True)
        with m3:
            st.markdown(f"""<div style="background-color: #f8fafc; padding: 20px; border-radius: 10px; color: #1e293b; border: 1px solid #e2e8f0;">
                <p style="margin:0; font-size: 0.8em; color: gray;">OUTSTANDING BALANCE</p>
                <h2 style="margin:0; color: #00acc1;">UGX {t_outstanding:,.0f}</h2>
            </div>""", unsafe_allow_html=True)

        st.write("")

        # 2. COLLECTION TREND CHART
        st.subheader("📈 Business Growth")
        df_sorted = df.copy()
        df_sorted['DATE_OF_ISSUE'] = pd.to_datetime(df_sorted['DATE_OF_ISSUE'])
        df_sorted = df_sorted.sort_values('DATE_OF_ISSUE')
        df_sorted['Cumulative'] = df_sorted['AMOUNT_PAID'].cumsum()
        
        fig = px.area(df_sorted, x='DATE_OF_ISSUE', y='Cumulative', 
                      title="Cumulative Collections (UGX)",
                      color_discrete_sequence=['#00acc1'])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)

       # 3. PREMIUM REGISTRY TABLE (Fixing the NameError)
        st.subheader("📋 Loan Portfolio Registry")

        # This function handles the "Red" for Overdue and "Green" for Cleared
        def registry_style(row):
            try:
                # Get current date and due date
                due_date = pd.to_datetime(row['EXPECTED_DUE_DATE']).date()
                today = datetime.date.today()
                balance = float(row['OUTSTANDING_AMOUNT'])
                
                # RED: Overdue and has balance
                if today > due_date and balance > 0:
                    return ['background-color: #fee2e2; color: #991b1b; font-weight: bold'] * len(row)
                
                # GREEN: Status is Cleared
                if row['STATUS'] == 'Cleared':
                    return ['background-color: #dcfce7; color: #166534'] * len(row)
            except:
                pass
            return [''] * len(row)

        # Filter the columns we want to show
        display_cols = ['SN', 'NAME', 'NIN', 'EXPECTED_DUE_DATE', 'OUTSTANDING_AMOUNT', 'STATUS']
        
        # Display as a styled table (st.table handles colors better than st.dataframe)
        st.table(df[display_cols].style.apply(registry_style, axis=1).format({
            "OUTSTANDING_AMOUNT": "{:,.0f}"
        }))

        # Updated Styling
        styled_registry = df[['SN', 'NAME', 'NIN', 'EXPECTED_DUE_DATE', 'OUTSTANDING_AMOUNT', 'STATUS']].style\
            .apply(apply_premium_styling, axis=1)\
            .format({"OUTSTANDING_AMOUNT": "{:,.0f}"})\
            .set_properties(**{
                'font-family': 'Segoe UI',
                'font-size': '14px',
                'border-collapse': 'collapse',
                'border-bottom': '1px solid #f1f5f9'
            })

        st.dataframe(styled_registry, use_container_width=True, hide_index=True)
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
