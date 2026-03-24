import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import gspread
from google.oauth2.service_account import Credentials
import json
import os
import io
import base64
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
from twilio.rest import Client
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# ==============================
# LOGIN SYSTEM
# ==============================
def login():
    st.title("🔐 Login")
    users = load(sheet, "Users")

    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        user = users[(users.Username==u)&(users.Password==p)]
        if not user.empty:
            st.session_state.logged_in=True
            st.session_state.user=u
            st.session_state.role=user.iloc[0]["Role"]
            st.rerun()
        else:
            st.error("Invalid credentials")

if "logged_in" not in st.session_state:
    st.session_state.logged_in=False

if not st.session_state.logged_in:
    login()
    st.stop()


st.set_page_config(page_title="Zoe Fintech", layout="wide")

# ==============================
# CUSTOM UI STYLE
# ==============================
st.markdown("""
<style>

/* MAIN BACKGROUND */
body {
    background-color: #0B0F19;
}

/* SIDEBAR */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0B0F19, #111827);
}

/* TITLE */
h1, h2, h3 {
    color: #E5E7EB;
}

/* METRIC CARDS */
.metric-card {
    background: linear-gradient(135deg, #1E3A8A, #2563EB);
    padding: 18px;
    border-radius: 12px;
    color: white;
    box-shadow: 0px 4px 15px rgba(0,0,0,0.3);
}

/* BUTTONS */
.stButton>button {
    background: linear-gradient(135deg, #2563EB, #1E40AF);
    color: white;
    border-radius: 10px;
    border: none;
    height: 42px;
    font-weight: 600;
}

/* INPUTS */
input, textarea {
    border-radius: 8px !important;
}

/* TABLE */
[data-testid="stDataFrame"] {
    border-radius: 10px;
    overflow: hidden;
}
st.markdown("""
<style>
[data-testid="stDialog"] {
    border-radius: 12px;
    padding: 20px;
}
</style>
""", unsafe_allow_html=True)


# ==============================
# GOOGLE SHEETS
# ==============================
@st.cache_resource
def connect_to_gsheets():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)

    return client

def open_sheet(sheet_name):
    client = connect_to_gsheets()
    sheet = client.open(sheet_name)
    return sheet

def open_sheet(sheet_name):
    client = connect_to_gsheets()
    sheet = client.open(sheet_name)
    return sheet

def save_data(sheet, worksheet_name, dataframe):
    worksheet = sheet.worksheet(worksheet_name)
    worksheet.clear()
    worksheet.update([dataframe.columns.values.tolist()] + dataframe.values.tolist())
sheet = connect().open("Zoe_Data")


# ==============================
# ROLE-BASED SIDEBAR
# ==============================
def sidebar():

    role = st.session_state.get("role", "Staff")

    st.sidebar.markdown("## ZOE ADMIN 💼")
    st.sidebar.markdown(f"👤 {st.session_state.user} ({role})")
    st.sidebar.markdown("---")

    # ALL PAGES
    menu = {
        "Overview": "📊",
        "Borrowers": "👥",
        "Collateral": "🛡️",
        "Calendar": "📅",
        "Ledger": "📄",
        "Overdue Tracker": "⏰",
        "Payments": "💵",
        "Expenses": "📁",
        "PettyCash": "💵",
        "Payroll": "🧾",
        "Reports": "📊",
        "Settings": "⚙️"
    }

    # RESTRICTED PAGES
    restricted = ["Settings", "Reports", "Payroll"]

    if "page" not in st.session_state:
        st.session_state.page = "Overview"

    for item, icon in menu.items():

        # Hide restricted pages for staff
        if role != "Admin" and item in restricted:
            continue

        if st.session_state.page == item:
            st.sidebar.markdown(
                f"""<div style="background:#2B3F87;padding:10px;border-radius:8px;color:white;">
                {icon} {item}
                </div>""",
                unsafe_allow_html=True
            )
        else:
            if st.sidebar.button(f"{icon} {item}"):
                st.session_state.page = item

    st.sidebar.markdown("---")

    # LOGOUT
    if st.sidebar.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.rerun()

    st.sidebar.markdown(
        "<p style='color:red; font-size:12px;'>● System Offline (Check Connection)</p>",
        unsafe_allow_html=True
    )

# ==============================
# PAGE ROUTING
# ==============================
if st.session_state.page == "Overview":
    st.title("Overview Page")

elif st.session_state.page == "Borrowers":
    st.title("Borrowers Page")

elif st.session_state.page == "Collateral":
    st.title("Collateral Page")

elif st.session_state.page == "Calendar":
    st.title("Calendar Page")

elif st.session_state.page == "Ledger":
    st.title("Ledger Page")

elif st.session_state.page == "Overdue Tracker":
    st.title("Overdue Tracker Page")

elif st.session_state.page == "Expenses":
    st.title("Expenses Page")

elif st.session_state.page == "PettyCash":
    st.title("Petty Cash Page")

elif st.session_state.page == "Payroll":
    st.title("Payroll Page")

elif st.session_state.page == "Add Payment":
    st.title("Add Payment Page")

elif st.session_state.page == "Settings":
    st.title("Settings Page")

elif st.session_state.page == "Reports":
    st.title("Report Page")
# ==============================
# IMPROVED LOAN PAGE
# ==============================
elif st.session_state.page == "Add Payment":

    st.title("💳 Loan Management")

    sheet = open_sheet("Zoe_Data")

    borrowers_df = load_data(sheet, "Borrowers")
    loans_df = load_data(sheet, "Loans")

    if loans_df.empty:
        loans_df = pd.DataFrame(columns=[
            "Loan_ID", "Borrower", "Amount", "Interest",
            "Total_Repayable", "Amount_Paid",
            "Start_Date", "End_Date", "Status"
        ])


# ==============================
# EXCEL-LIKE TABLE EDITOR
# ==============================
def excel_editor(df, sheet, sheet_name, id_col):

    st.subheader(f"📊 {sheet_name} Editor")

    if df.empty:
        st.info("No data available")
        return

    # Ensure ID column exists
    if id_col not in df.columns:
        df[id_col] = range(1, len(df) + 1)

    # Editable table
    edited_df = st.data_editor(
        df,
        num_rows="dynamic",  # allows adding rows
        use_container_width=True,
        key=f"{sheet_name}_editor"
    )

    # ==============================
    # SAVE CHANGES
    # ==============================
    if st.button(f"💾 Save Changes ({sheet_name})"):

        # Clean empty rows
        edited_df = edited_df.dropna(how="all")

        # Reassign IDs (important after adding/deleting)
        edited_df[id_col] = range(1, len(edited_df) + 1)

        save(sheet, sheet_name, edited_df)

        st.success(f"{sheet_name} updated successfully ✅")
        st.rerun()

# ==============================
# WHATSAPP
# ==============================
def send_whatsapp(phone,msg):
    client=Client(st.secrets["TWILIO_SID"],st.secrets["TWILIO_TOKEN"])
    client.messages.create(
        from_='whatsapp:+14155238886',
        body=msg,
        to=f'whatsapp:{phone}'
    )

# ==============================
# RECEIPT
# ==============================
def make_receipt(data,file):
    doc=SimpleDocTemplate(file)
    styles=getSampleStyleSheet()
    content=[
        Paragraph("ZOE LENDING SERVICES",styles['Title']),
        Spacer(1,10),
        Paragraph(f"Borrower: {data['b']}",styles['Normal']),
        Paragraph(f"Amount: {data['a']}",styles['Normal']),
        Paragraph(f"Date: {data['d']}",styles['Normal'])
    ]
    doc.build(content)

# ==============================
# HEADER
# ==============================
st.markdown(f"### Welcome {st.session_state.user} 👋")

# ==============================
# GENERIC CRUD TABLE COMPONENT
# ==============================
def interactive_table(df, sheet, sheet_name, id_col):

    st.dataframe(df, use_container_width=True)

    if df.empty:
        return

    selected_id = st.selectbox(f"Select {sheet_name}", df[id_col])

    row = df[df[id_col] == selected_id].iloc[0]

    col1, col2, col3 = st.columns(3)

    # ==============================
    # VIEW
    # ==============================
    with col1:
        if st.button("👁️ View"):
            with st.dialog("View Record"):
                for col in df.columns:
                    st.write(f"**{col}:** {row[col]}")

    # ==============================
    # EDIT
    # ==============================
    with col2:
        if st.button("✏️ Edit"):
            with st.dialog("Edit Record"):

                updated = {}

                for col in df.columns:
                    if col == id_col:
                        updated[col] = row[col]
                    else:
                        updated[col] = st.text_input(col, str(row[col]))

                if st.button("Save Changes"):
                    for col in updated:
                        df.loc[df[id_col] == selected_id, col] = updated[col]

                    save(sheet, sheet_name, df)
                    st.success("Updated ✅")
                    st.rerun()

    # ==============================
    # DELETE
    # ==============================
    with col3:
        if st.button("❌ Delete"):
            with st.dialog("Confirm Delete"):

                st.warning("Are you sure you want to delete this record?")

                if st.button("Yes, Delete"):
                    df = df[df[id_col] != selected_id]
                    save(sheet, sheet_name, df)
                    st.success("Deleted ✅")
                    st.rerun()

# ==============================
# PAGES
# ==============================

# ==============================
# UPGRADED OVERVIEW PAGE
# ==============================
if st.session_state.page == "Overview":

    st.title("📊 Financial Dashboard")

    sheet = open_sheet("Zoe_Data")
    df = load_data(sheet, "Loans")

    if df.empty:
        st.warning("No data available")
    else:
        # ==============================
        # CLEAN DATA
        # ==============================
        df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
        df["Interest"] = pd.to_numeric(df["Interest"], errors="coerce")
        df["Amount_Paid"] = pd.to_numeric(df.get("Amount_Paid", 0), errors="coerce")

        df["Start_Date"] = pd.to_datetime(df["Start_Date"], errors="coerce")
        df["End_Date"] = pd.to_datetime(df["End_Date"], errors="coerce")

        today = pd.Timestamp.today()

        # ==============================
        # AUTO OVERDUE DETECTION
        # ==============================
        df["Auto_Status"] = df["Status"]
        df.loc[
            (df["End_Date"] < today) & (df["Amount_Paid"] < df["Amount"] + df["Interest"]),
            "Auto_Status"
        ] = "Overdue"

        # ==============================
        # METRICS
        # ==============================
        total_loans = df["Amount"].sum()
        total_interest = df["Interest"].sum()
        total_expected = total_loans + total_interest

        total_paid = df["Amount_Paid"].sum()

        active_loans = df[df["Auto_Status"] == "Active"].shape[0]
        overdue_loans = df[df["Auto_Status"] == "Overdue"].shape[0]

        default_rate = (overdue_loans / len(df)) * 100 if len(df) > 0 else 0

        # ==============================
        # TODAY COLLECTIONS
        # ==============================
        today_collections = df[
            df["Start_Date"].dt.date == today.date()
        ]["Amount_Paid"].sum()

        # ==============================
        # METRIC CARDS
        # ==============================
        col1, col2, col3, col4 = st.columns(4)

        col1.metric("💰 Total Issued", f"{total_loans:,.0f}")
        col2.metric("📈 Expected Profit", f"{total_interest:,.0f}")
        col3.metric("💵 Collected", f"{total_paid:,.0f}")
        col4.metric("⚠️ Overdue Loans", overdue_loans)

        col5, col6 = st.columns(2)
        col5.metric("📊 Default Rate", f"{default_rate:.1f}%")
        col6.metric("📅 Today’s Collections", f"{today_collections:,.0f}")

        st.markdown("---")

        # ==============================
        # STATUS PIE CHART
        # ==============================
        status_counts = df["Auto_Status"].value_counts().reset_index()
        status_counts.columns = ["Status", "Count"]

        fig = px.pie(
            status_counts,
            names="Status",
            values="Count",
            title="Loan Status Distribution"
        )

        st.plotly_chart(fig, use_container_width=True)

        # ==============================
        # MONTHLY INCOME TREND
        # ==============================
        df["Month"] = df["Start_Date"].dt.to_period("M").astype(str)

        monthly_income = df.groupby("Month")["Amount_Paid"].sum().reset_index()

        fig2 = px.line(
            monthly_income,
            x="Month",
            y="Amount_Paid",
            title="Monthly Collections Trend"
        )

        st.plotly_chart(fig2, use_container_width=True)

        # ==============================
        # OVERDUE TABLE (IMPORTANT)
        # ==============================
        st.subheader("⚠️ Overdue Loans")

        overdue_df = df[df["Auto_Status"] == "Overdue"]

        if overdue_df.empty:
            st.success("No overdue loans 🎉")
        else:
            st.dataframe(
                overdue_df[[
                    "Borrower",
                    "Amount",
                    "Interest",
                    "End_Date",
                    "Amount_Paid"
                ]],
                use_container_width=True
            )

        # ==============================
        # RECENT ACTIVITY
        # ==============================
        st.subheader("📅 Recent Loans")

        recent = df.sort_values(by="Start_Date", ascending=False).head(5)
        st.dataframe(recent, use_container_width=True)


# ==============================
# IMPROVED BORROWERS PAGE
# ==============================
elif st.session_state.page == "Borrowers":

    st.title("👥 Borrowers Management")

    sheet = open_sheet("Zoe_Data")
    df = load_data(sheet, "Borrowers")

    if df.empty:
        df = pd.DataFrame(columns=[
            "Borrower_ID", "Name", "Phone",
            "National_ID", "Address", "Status", "Date_Added"
        ])

    # ==============================
    # SEARCH & FILTER
    # ==============================
    st.subheader("🔍 Search & Filter")

    col1, col2 = st.columns(2)

    search = col1.text_input("Search (Name or Phone)")
    status_filter = col2.selectbox("Filter by Status", ["All", "Active", "Inactive"])

    filtered_df = df.copy()

    if search:
        filtered_df = filtered_df[
            filtered_df["Name"].str.contains(search, case=False, na=False) |
            filtered_df["Phone"].str.contains(search, case=False, na=False)
        ]

    if status_filter != "All":
        filtered_df = filtered_df[filtered_df["Status"] == status_filter]

    # ==============================
    # DISPLAY BORROWERS
    # ==============================
    st.subheader("📋 Borrowers List")
    st.dataframe(filtered_df, use_container_width=True)

    st.markdown("---")

    # ==============================
    # ADD BORROWER
    # ==============================
    st.subheader("➕ Add Borrower")

    with st.form("add_borrower", clear_on_submit=True):
        col1, col2 = st.columns(2)

        name = col1.text_input("Full Name")
        phone = col2.text_input("Phone Number")

        national_id = col1.text_input("National ID")
        address = col2.text_input("Address")

        submitted = st.form_submit_button("Add Borrower")

        if submitted:
            new_id = int(df["Borrower_ID"].max() + 1) if not df.empty else 1

            new_data = pd.DataFrame([{
                "Borrower_ID": new_id,
                "Name": name,
                "Phone": phone,
                "National_ID": national_id,
                "Address": address,
                "Status": "Active",
                "Date_Added": datetime.now().strftime("%Y-%m-%d")
            }])

            df = pd.concat([df, new_data], ignore_index=True)
            save_data(sheet, "Borrowers", df)

            st.success("Borrower added ✅")

    st.markdown("---")

    # ==============================
    # SELECT BORROWER (FOR ACTIONS)
    # ==============================
    st.subheader("⚙️ Manage Borrower")

    if not df.empty:
        selected_id = st.selectbox(
            "Select Borrower",
            filtered_df["Borrower_ID"]
        )

        borrower = df[df["Borrower_ID"] == selected_id].iloc[0]

        # ==============================
        # BORROWER SUMMARY
        # ==============================
        loans_df = load_data(sheet, "Loans")

        if not loans_df.empty:
            loans_df["Amount"] = pd.to_numeric(loans_df["Amount"], errors="coerce")
            loans_df["Amount_Paid"] = pd.to_numeric(loans_df.get("Amount_Paid", 0), errors="coerce")

            user_loans = loans_df[loans_df["Borrower"] == borrower["Name"]]

            total_loans = user_loans.shape[0]
            total_borrowed = user_loans["Amount"].sum()
            total_paid = user_loans["Amount_Paid"].sum()
        else:
            total_loans, total_borrowed, total_paid = 0, 0, 0

        col1, col2, col3 = st.columns(3)
        col1.metric("Loans", total_loans)
        col2.metric("Borrowed", f"{total_borrowed:,.0f}")
        col3.metric("Paid", f"{total_paid:,.0f}")

        st.markdown("---")

        # ==============================
        # EDIT BORROWER
        # ==============================
        st.subheader("✏️ Edit Borrower")

        col1, col2 = st.columns(2)

        new_name = col1.text_input("Name", borrower["Name"])
        new_phone = col2.text_input("Phone", borrower["Phone"])

        new_nid = col1.text_input("National ID", borrower["National_ID"])
        new_address = col2.text_input("Address", borrower["Address"])

        new_status = st.selectbox(
            "Status",
            ["Active", "Inactive"],
            index=0 if borrower["Status"] == "Active" else 1
        )

        if st.button("Update"):
            df.loc[df["Borrower_ID"] == selected_id, [
                "Name", "Phone", "National_ID", "Address", "Status"
            ]] = [
                new_name, new_phone, new_nid, new_address, new_status
            ]

            save_data(sheet, "Borrowers", df)
            st.success("Updated successfully ✅")

        # ==============================
        # SAFE DELETE (DEACTIVATE)
        # ==============================
        st.subheader("⚠️ Deactivate Borrower")

        if borrower["Status"] == "Active":
            if st.button("Deactivate"):
                df.loc[df["Borrower_ID"] == selected_id, "Status"] = "Inactive"
                save_data(sheet, "Borrowers", df)
                st.warning("Borrower deactivated ⚠️")
        else:
            st.info("Borrower already inactive")



    # ==============================
    # ISSUE LOAN
    # ==============================
    st.subheader("➕ Issue Loan")

    active_borrowers = borrowers_df[borrowers_df["Status"] == "Active"]

    borrower = st.selectbox(
        "Select Borrower",
        active_borrowers["Name"].unique()
    )

    amount = st.number_input("Loan Amount", min_value=0.0)
    interest_rate = st.number_input("Interest Rate (%)", min_value=0.0)
    duration = st.number_input("Duration (Days)", min_value=1)

    # ==============================
    # LIVE LOAN PREVIEW
    # ==============================
    if amount > 0 and interest_rate > 0:
        interest = (interest_rate / 100) * amount
        total = amount + interest
        end_date = datetime.now() + timedelta(days=int(duration))

        col1, col2, col3 = st.columns(3)
        col1.metric("Interest", f"{interest:,.0f}")
        col2.metric("Total Repayable", f"{total:,.0f}")
        col3.metric("End Date", end_date.strftime("%Y-%m-%d"))

    # ==============================
    # RISK CHECK
    # ==============================
    risky_loans = loans_df[
        (loans_df["Borrower"] == borrower) &
        (loans_df["Status"] == "Active")
    ]

    if not risky_loans.empty:
        st.warning("⚠️ This borrower has an active loan!")

    # ==============================
    # ISSUE BUTTON
    # ==============================
    if st.button("Issue Loan"):

        if amount <= 0 or interest_rate <= 0:
            st.error("Enter valid loan details")

        elif borrower not in active_borrowers["Name"].values:
            st.error("Borrower is inactive")

        else:
            interest = (interest_rate / 100) * amount
            total = amount + interest

            start_date = datetime.now()
            end_date = start_date + timedelta(days=int(duration))

            new_id = int(loans_df["Loan_ID"].max() + 1) if not loans_df.empty else 1

            new_loan = pd.DataFrame([{
                "Loan_ID": new_id,
                "Borrower": borrower,
                "Amount": amount,
                "Interest": interest,
                "Total_Repayable": total,
                "Amount_Paid": 0,
                "Start_Date": start_date.strftime("%Y-%m-%d"),
                "End_Date": end_date.strftime("%Y-%m-%d"),
                "Status": "Active"
            }])

            loans_df = pd.concat([loans_df, new_loan], ignore_index=True)
            save_data(sheet, "Loans", loans_df)

            st.success(f"Loan issued ✅ Total: {total:,.0f}")

    st.markdown("---")

    # ==============================
    # AUTO STATUS UPDATE
    # ==============================
    loans_df["End_Date"] = pd.to_datetime(loans_df["End_Date"], errors="coerce")
    today = pd.Timestamp.today()

    loans_df.loc[
        (loans_df["End_Date"] < today) &
        (loans_df["Amount_Paid"] < loans_df["Total_Repayable"]),
        "Status"
    ] = "Overdue"

    # ==============================
    # LOAN TABLE WITH INSIGHTS
    # ==============================
    st.subheader("📋 Loan Portfolio")

    loans_df["Outstanding"] = loans_df["Total_Repayable"] - loans_df["Amount_Paid"]
    loans_df["Progress (%)"] = (
        loans_df["Amount_Paid"] / loans_df["Total_Repayable"] * 100
    ).fillna(0)

    st.dataframe(loans_df, use_container_width=True)

    # ==============================
    # LOAN PROGRESS VISUAL
    # ==============================
    st.subheader("📊 Loan Progress")

    selected_loan = st.selectbox("Select Loan ID", loans_df["Loan_ID"])

    loan = loans_df[loans_df["Loan_ID"] == selected_loan].iloc[0]

    progress = loan["Progress (%)"]

    st.progress(min(int(progress), 100))

    col1, col2, col3 = st.columns(3)
    col1.metric("Paid", f"{loan['Amount_Paid']:,.0f}")
    col2.metric("Outstanding", f"{loan['Outstanding']:,.0f}")
    col3.metric("Status", loan["Status"])

# ==============================
# PAYMENTS PAGE
# ==============================
elif st.session_state.page == "Payments":

    st.title("💵 Payments Management")

    sheet = open_sheet("Zoe_Data")

    loans_df = load_data(sheet, "Loans")
    payments_df = load_data(sheet, "Payments")

    if payments_df.empty:
        payments_df = pd.DataFrame(columns=[
            "Payment_ID", "Loan_ID", "Borrower",
            "Amount", "Date", "Method", "Recorded_By"
        ])

    # ==============================
    # SELECT LOAN
    # ==============================
    st.subheader("➕ Record Payment")

    active_loans = loans_df[loans_df["Status"] != "Closed"]

    if active_loans.empty:
        st.info("No active loans")
    else:
        loan_id = st.selectbox("Select Loan", active_loans["Loan_ID"])

        loan = active_loans[active_loans["Loan_ID"] == loan_id].iloc[0]

        outstanding = loan["Total_Repayable"] - loan["Amount_Paid"]

        # ==============================
        # LOAN DETAILS
        # ==============================
        col1, col2, col3 = st.columns(3)
        col1.metric("Borrower", loan["Borrower"])
        col2.metric("Outstanding", f"{outstanding:,.0f}")
        col3.metric("Status", loan["Status"])

        # ==============================
        # PAYMENT INPUT
        # ==============================
        amount = st.number_input("Payment Amount", min_value=0.0)
        method = st.selectbox("Payment Method", ["Cash", "Mobile Money", "Bank"])
        recorded_by = st.text_input("Recorded By")

        # ==============================
        # VALIDATION + SAVE
        # ==============================
        if st.button("Record Payment"):

            if amount <= 0:
                st.error("Enter valid amount")

            elif amount > outstanding:
                st.error("Payment exceeds outstanding balance")

            else:
                new_id = int(payments_df["Payment_ID"].max() + 1) if not payments_df.empty else 1

                new_payment = pd.DataFrame([{
                    "Payment_ID": new_id,
                    "Loan_ID": loan_id,
                    "Borrower": loan["Borrower"],
                    "Amount": amount,
                    "Date": datetime.now().strftime("%Y-%m-%d"),
                    "Method": method,
                    "Recorded_By": recorded_by
                }])

                payments_df = pd.concat([payments_df, new_payment], ignore_index=True)
                save_data(sheet, "Payments", payments_df)

                # ==============================
                # UPDATE LOAN
                # ==============================
                idx = loans_df[loans_df["Loan_ID"] == loan_id].index[0]

                loans_df.loc[idx, "Amount_Paid"] += amount

                if loans_df.loc[idx, "Amount_Paid"] >= loans_df.loc[idx, "Total_Repayable"]:
                    loans_df.loc[idx, "Status"] = "Closed"

                save_data(sheet, "Loans", loans_df)

                st.success("Payment recorded ✅")

    st.markdown("---")

    # ==============================
    # PAYMENT HISTORY
    # ==============================
    st.subheader("📜 Payment History")

    st.dataframe(payments_df.sort_values(by="Date", ascending=False), use_container_width=True)

    st.markdown("---")

    # ==============================
    # DAILY COLLECTIONS
    # ==============================
    st.subheader("📊 Daily Collections")

    payments_df["Date"] = pd.to_datetime(payments_df["Date"], errors="coerce")

    daily = payments_df.groupby(payments_df["Date"].dt.date)["Amount"].sum().reset_index()

    daily.columns = ["Date", "Total"]

    st.dataframe(daily, use_container_width=True)

# ==============================
# COLLATERAL PAGE
# ==============================
elif st.session_state.page == "Collateral":

    st.title("🛡️ Collateral Management")

    sheet = open_sheet("Zoe_Data")

    borrowers_df = load_data(sheet, "Borrowers")
    loans_df = load_data(sheet, "Loans")
    collateral_df = load_data(sheet, "Collateral")

    if collateral_df.empty:
        collateral_df = pd.DataFrame(columns=[
            "Collateral_ID", "Borrower", "Loan_ID",
            "Type", "Description", "Value",
            "Status", "Date_Added"
        ])

    # ==============================
    # ADD COLLATERAL
    # ==============================
    st.subheader("➕ Register Collateral")

    active_loans = loans_df[loans_df["Status"] == "Active"]

    if active_loans.empty:
        st.info("No active loans to attach collateral")
    else:
        with st.form("collateral_form", clear_on_submit=True):

            col1, col2 = st.columns(2)

            loan_id = col1.selectbox("Select Loan", active_loans["Loan_ID"])

            borrower_name = loans_df[
                loans_df["Loan_ID"] == loan_id
            ]["Borrower"].values[0]

            col1.markdown(f"**Borrower:** {borrower_name}")

            ctype = col2.selectbox("Collateral Type", ["Car", "Land", "Electronics", "Other"])

            description = st.text_input("Description (e.g. Toyota Prado UBA123X)")

            value = st.number_input("Estimated Value", min_value=0.0)

            submitted = st.form_submit_button("Save Collateral")

            if submitted:

                if value <= 0 or description == "":
                    st.error("Fill all fields correctly")
                else:
                    new_id = int(collateral_df["Collateral_ID"].max() + 1) if not collateral_df.empty else 1

                    new_data = pd.DataFrame([{
                        "Collateral_ID": new_id,
                        "Borrower": borrower_name,
                        "Loan_ID": loan_id,
                        "Type": ctype,
                        "Description": description,
                        "Value": value,
                        "Status": "Held",
                        "Date_Added": datetime.now().strftime("%Y-%m-%d")
                    }])

                    collateral_df = pd.concat([collateral_df, new_data], ignore_index=True)
                    save_data(sheet, "Collateral", collateral_df)

                    st.success("Collateral added ✅")

    st.markdown("---")

    # ==============================
    # VIEW COLLATERAL
    # ==============================
    st.subheader("📋 All Collateral")

    st.dataframe(collateral_df, use_container_width=True)

    st.markdown("---")

    # ==============================
    # EDIT / UPDATE STATUS
    # ==============================
    st.subheader("⚙️ Manage Collateral")

    if not collateral_df.empty:

        selected_id = st.selectbox(
            "Select Collateral",
            collateral_df["Collateral_ID"]
        )

        item = collateral_df[collateral_df["Collateral_ID"] == selected_id].iloc[0]

        col1, col2 = st.columns(2)

        new_type = col1.selectbox(
            "Type",
            ["Car", "Land", "Electronics", "Other"],
            index=["Car", "Land", "Electronics", "Other"].index(item["Type"])
        )

        new_desc = col2.text_input("Description", item["Description"])
        new_value = col1.number_input("Value", value=float(item["Value"]))

        new_status = col2.selectbox(
            "Status",
            ["Held", "Released"],
            index=0 if item["Status"] == "Held" else 1
        )

        if st.button("Update Collateral"):
            collateral_df.loc[collateral_df["Collateral_ID"] == selected_id, [
                "Type", "Description", "Value", "Status"
            ]] = [
                new_type, new_desc, new_value, new_status
            ]

            save_data(sheet, "Collateral", collateral_df)
            st.success("Updated ✅")

    st.markdown("---")

    # ==============================
    # COLLATERAL SUMMARY
    # ==============================
    st.subheader("📊 Collateral Summary")

    total_value = collateral_df["Value"].astype(float).sum()
    held = collateral_df[collateral_df["Status"] == "Held"].shape[0]
    released = collateral_df[collateral_df["Status"] == "Released"].shape[0]

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Value", f"{total_value:,.0f}")
    col2.metric("Held", held)
    col3.metric("Released", released)

# ==============================
# ADVANCED OVERDUE TRACKER
# ==============================
elif st.session_state.page == "Overdue Tracker":

    st.title("🔴 Collections Dashboard")

    sheet = open_sheet("Zoe_Data")
    loans_df = load_data(sheet, "Loans")

    if loans_df.empty:
        st.info("No loan data available")
    else:
        # ==============================
        # CLEAN DATA
        # ==============================
        loans_df["End_Date"] = pd.to_datetime(loans_df["End_Date"], errors="coerce")
        loans_df["Amount_Paid"] = pd.to_numeric(loans_df["Amount_Paid"], errors="coerce")
        loans_df["Total_Repayable"] = pd.to_numeric(loans_df["Total_Repayable"], errors="coerce")

        today = pd.Timestamp.today()

        # ==============================
        # DETECT OVERDUE
        # ==============================
        overdue_df = loans_df[
            (loans_df["End_Date"] < today) &
            (loans_df["Amount_Paid"] < loans_df["Total_Repayable"])
        ].copy()

        if overdue_df.empty:
            st.success("No overdue loans 🎉")
        else:
            # ==============================
            # CALCULATIONS
            # ==============================
            overdue_df["Days_Overdue"] = (today - overdue_df["End_Date"]).dt.days
            overdue_df["Outstanding"] = overdue_df["Total_Repayable"] - overdue_df["Amount_Paid"]

            # ==============================
            # SEVERITY LEVEL
            # ==============================
            def severity(days):
                if days <= 7:
                    return "Mild"
                elif days <= 30:
                    return "Moderate"
                else:
                    return "Critical"

            overdue_df["Severity"] = overdue_df["Days_Overdue"].apply(severity)

            # ==============================
            # RISK SCORE (PER BORROWER)
            # ==============================
            risk_df = overdue_df.groupby("Borrower").agg({
                "Outstanding": "sum",
                "Days_Overdue": "max"
            }).reset_index()

            risk_df["Risk_Score"] = (
                risk_df["Outstanding"] * 0.5 +
                risk_df["Days_Overdue"] * 100
            )

            overdue_df = overdue_df.merge(risk_df[["Borrower", "Risk_Score"]], on="Borrower", how="left")

            # ==============================
            # FILTERS
            # ==============================
            st.subheader("🔍 Filter")

            col1, col2 = st.columns(2)
            search = col1.text_input("Search Borrower")
            severity_filter = col2.selectbox("Severity", ["All", "Mild", "Moderate", "Critical"])

            filtered = overdue_df.copy()

            if search:
                filtered = filtered[
                    filtered["Borrower"].str.contains(search, case=False, na=False)
                ]

            if severity_filter != "All":
                filtered = filtered[filtered["Severity"] == severity_filter]

            # ==============================
            # PRIORITY SORT
            # ==============================
            filtered = filtered.sort_values(by="Risk_Score", ascending=False)

            # ==============================
            # METRICS
            # ==============================
            total_overdue = filtered["Outstanding"].sum()
            critical_cases = filtered[filtered["Severity"] == "Critical"].shape[0]

            col1, col2 = st.columns(2)
            col1.metric("💰 Total At Risk", f"{total_overdue:,.0f}")
            col2.metric("🔴 Critical Cases", critical_cases)

            st.markdown("---")

            # ==============================
            # TABLE
            # ==============================
            st.subheader("📋 Priority List")

            st.dataframe(filtered[[
                "Loan_ID",
                "Borrower",
                "Outstanding",
                "Days_Overdue",
                "Severity",
                "Risk_Score"
            ]], use_container_width=True)

            st.markdown("---")

            # ==============================
            # FOLLOW-UP ACTION
            # ==============================
            st.subheader("📞 Follow-Up Action")

            selected_loan = st.selectbox("Select Loan", filtered["Loan_ID"])

            loan = filtered[filtered["Loan_ID"] == selected_loan].iloc[0]

            # SMART MESSAGE
            if loan["Severity"] == "Mild":
                msg = f"Hello {loan['Borrower']}, your loan is slightly overdue. Kindly clear {loan['Outstanding']:,.0f}."
            elif loan["Severity"] == "Moderate":
                msg = f"Reminder: Your loan is overdue by {loan['Days_Overdue']} days. Pay {loan['Outstanding']:,.0f} ASAP."
            else:
                msg = f"URGENT: Your loan is {loan['Days_Overdue']} days overdue. Immediate payment of {loan['Outstanding']:,.0f} required."

            st.text_area("Message", msg)

            # ==============================
            # UPDATE FOLLOW-UP STATUS
            # ==============================
            follow_status = st.selectbox(
                "Follow-Up Status",
                ["Pending", "Contacted", "Promised", "Ignored"]
            )

            if st.button("Update Follow-Up"):

                idx = loans_df[loans_df["Loan_ID"] == selected_loan].index[0]

                loans_df.loc[idx, "Follow_Up_Status"] = follow_status
                loans_df.loc[idx, "Last_Contact_Date"] = datetime.now().strftime("%Y-%m-%d")

                save_data(sheet, "Loans", loans_df)

                st.success("Follow-up updated ✅")

# ==============================
# ACTIVITY CALENDAR PAGE
# ==============================
elif st.session_state.page == "Calendar":

    st.title("📅 Activity Calendar")

    sheet = open_sheet("Zoe_Data")
    loans_df = load_data(sheet, "Loans")

    if loans_df.empty:
        st.info("No data available")
    else:
        loans_df["End_Date"] = pd.to_datetime(loans_df["End_Date"], errors="coerce")

        today = pd.Timestamp.today().normalize()

        # ==============================
        # DUE TODAY
        # ==============================
        due_today = loans_df[
            loans_df["End_Date"].dt.date == today.date()
        ]

        st.subheader("📌 Due Today")

        if due_today.empty:
            st.success("No loans due today 🎉")
        else:
            st.dataframe(due_today[[
                "Loan_ID", "Borrower", "Total_Repayable"
            ]], use_container_width=True)

        # ==============================
        # UPCOMING (NEXT 7 DAYS)
        # ==============================
        upcoming = loans_df[
            (loans_df["End_Date"] > today) &
            (loans_df["End_Date"] <= today + pd.Timedelta(days=7))
        ]

        st.subheader("⏳ Upcoming (Next 7 Days)")

        st.dataframe(upcoming[[
            "Loan_ID", "Borrower", "End_Date"
        ]], use_container_width=True)

        # ==============================
        # OVERDUE FOLLOW-UPS
        # ==============================
        overdue = loans_df[
            (loans_df["End_Date"] < today) &
            (loans_df["Status"] != "Closed")
        ]

        st.subheader("🔴 Needs Follow-Up")

        st.dataframe(overdue[[
            "Loan_ID", "Borrower", "End_Date", "Follow_Up_Status"
        ]], use_container_width=True)


elif st.session_state.page == "Expenses":

    st.title("📁 Expenses")

    sheet = open_sheet("Zoe_Data")
    df = load_data(sheet, "Expenses")

    if df.empty:
        df = pd.DataFrame(columns=["Expense_ID","Category","Amount","Date","Description"])

    # ADD EXPENSE
    st.subheader("➕ Add Expense")

    category = st.selectbox("Category", ["Rent","Transport","Utilities","Other"])
    amount = st.number_input("Amount", min_value=0.0)
    desc = st.text_input("Description")

    if st.button("Save Expense"):
        new_id = int(df["Expense_ID"].max()+1) if not df.empty else 1

        new = pd.DataFrame([{
            "Expense_ID": new_id,
            "Category": category,
            "Amount": amount,
            "Date": datetime.now().strftime("%Y-%m-%d"),
            "Description": desc
        }])

        df = pd.concat([df, new], ignore_index=True)
        save_data(sheet, "Expenses", df)

        st.success("Saved ✅")

    st.dataframe(df, use_container_width=True)

elif st.session_state.page == "PettyCash":

    st.title("💵 Petty Cash")

    sheet = open_sheet("Zoe_Data")
    df = load_data(sheet, "PettyCash")

    if df.empty:
        df = pd.DataFrame(columns=["Transaction_ID","Type","Amount","Date","Description"])

    st.subheader("➕ Record Transaction")

    ttype = st.selectbox("Type", ["In","Out"])
    amount = st.number_input("Amount", min_value=0.0)
    desc = st.text_input("Description")

    if st.button("Save"):
        new_id = int(df["Transaction_ID"].max()+1) if not df.empty else 1

        new = pd.DataFrame([{
            "Transaction_ID": new_id,
            "Type": ttype,
            "Amount": amount,
            "Date": datetime.now().strftime("%Y-%m-%d"),
            "Description": desc
        }])

        df = pd.concat([df, new], ignore_index=True)
        save_data(sheet, "PettyCash", df)

        st.success("Recorded ✅")

    # BALANCE
    inflow = df[df["Type"]=="In"]["Amount"].astype(float).sum()
    outflow = df[df["Type"]=="Out"]["Amount"].astype(float).sum()
    balance = inflow - outflow

    st.metric("Balance", f"{balance:,.0f}")

    st.dataframe(df, use_container_width=True)

elif st.session_state.page == "Payroll":
  if st.session_state.role != "Admin":
    st.error("Access denied 🔒")
    st.stop()

    st.title("🧾 Payroll")

    sheet = open_sheet("Zoe_Data")
    df = load_data(sheet, "Payroll")

    if df.empty:
        df = pd.DataFrame(columns=["Payroll_ID","Employee","Salary","Date","Status"])

    st.subheader("➕ Pay Employee")

    name = st.text_input("Employee Name")
    salary = st.number_input("Salary", min_value=0.0)

    if st.button("Pay"):
        new_id = int(df["Payroll_ID"].max()+1) if not df.empty else 1

        new = pd.DataFrame([{
            "Payroll_ID": new_id,
            "Employee": name,
            "Salary": salary,
            "Date": datetime.now().strftime("%Y-%m-%d"),
            "Status": "Paid"
        }])

        df = pd.concat([df, new], ignore_index=True)
        save_data(sheet, "Payroll", df)

        st.success("Payment done ✅")

    st.dataframe(df, use_container_width=True)


elif st.session_state.page == "Settings":
  if st.session_state.role != "Admin":
    st.error("Access denied 🔒")
    st.stop()

    st.title("⚙️ Settings")

    st.subheader("System Settings")

    business_name = st.text_input("Business Name", "Zoe Lending")
    currency = st.selectbox("Currency", ["UGX","USD"])

    if st.button("Save Settings"):
        st.success("Settings saved ✅")

    st.markdown("---")

    st.subheader("Danger Zone")

    if st.button("Reset System"):
        st.warning("System reset not yet implemented")
        # ==============================
# LOGO HANDLING
# ==============================
import base64

def save_logo(sheet, image_file):
    settings = load(sheet, "Settings")

    # Convert image to base64
    encoded = base64.b64encode(image_file.read()).decode()

    if settings.empty:
        settings = pd.DataFrame([{"Key": "logo", "Value": encoded}])
    else:
        if "logo" in settings["Key"].values:
            settings.loc[settings["Key"]=="logo","Value"] = encoded
        else:
            settings = pd.concat([settings, pd.DataFrame([{"Key":"logo","Value":encoded}])])

    save(sheet, "Settings", settings)


def get_logo(sheet):
    settings = load(sheet, "Settings")

    if settings.empty:
        return None

    row = settings[settings["Key"]=="logo"]

    if row.empty:
        return None

    return row.iloc[0]["Value"]


# ==============================
# ADVANCED ANALYTICS
# ==============================
elif st.session_state.page == "Reports":

    st.title("📊 Advanced Analytics")

    sheet = open_sheet("Zoe_Data")

    loans = load_data(sheet, "Loans")
    payments = load_data(sheet, "Payments")
    expenses = load_data(sheet, "Expenses")

    # CLEAN
    loans["Amount"] = pd.to_numeric(loans["Amount"], errors="coerce")
    loans["Interest"] = pd.to_numeric(loans["Interest"], errors="coerce")
    payments["Amount"] = pd.to_numeric(payments["Amount"], errors="coerce")
    expenses["Amount"] = pd.to_numeric(expenses["Amount"], errors="coerce")

    # ==============================
    # KPIs
    # ==============================
    total_issued = loans["Amount"].sum()
    total_interest = loans["Interest"].sum()
    total_collected = payments["Amount"].sum()
    total_expenses = expenses["Amount"].sum()

    profit = total_collected - total_expenses

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Issued", f"{total_issued:,.0f}")
    col2.metric("Interest", f"{total_interest:,.0f}")
    col3.metric("Collected", f"{total_collected:,.0f}")
    col4.metric("Profit", f"{profit:,.0f}")

    st.markdown("---")

    # ==============================
    # DEFAULT RATE
    # ==============================
    overdue = loans[loans["Status"] == "Overdue"].shape[0]
    default_rate = (overdue / len(loans)) * 100 if len(loans) > 0 else 0

    st.metric("Default Rate", f"{default_rate:.2f}%")

    # ==============================
    # TOP BORROWERS
    # ==============================
    top = loans.groupby("Borrower")["Amount"].sum().reset_index()
    top = top.sort_values(by="Amount", ascending=False).head(5)

    st.subheader("🏆 Top Borrowers")
    st.dataframe(top)

    # ==============================
    # CASHFLOW TREND
    # ==============================
    payments["Date"] = pd.to_datetime(payments["Date"], errors="coerce")

    trend = payments.groupby(
        payments["Date"].dt.to_period("M")
    )["Amount"].sum().reset_index()

    trend["Date"] = trend["Date"].astype(str)

    fig = px.line(trend, x="Date", y="Amount", title="Cashflow Trend")

    st.plotly_chart(fig, use_container_width=True)

    # ==============================
    # EXPENSE VS INCOME
    # ==============================
    monthly_exp = expenses.groupby(
        pd.to_datetime(expenses["Date"]).dt.to_period("M")
    )["Amount"].sum().reset_index()

    monthly_exp["Date"] = monthly_exp["Date"].astype(str)

    merged = pd.merge(trend, monthly_exp, on="Date", how="left").fillna(0)
    merged.columns = ["Month", "Income", "Expenses"]

    fig2 = px.bar(merged, x="Month", y=["Income", "Expenses"], barmode="group")

    st.plotly_chart(fig2, use_container_width=True)
