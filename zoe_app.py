elif choice == "📄 Client Report":
    st.title("📄 Client Statement & Schedule")
    if not df.empty:
        # Create a search list that shows both Name and SN for clarity
        client_options = df.apply(lambda x: f"{x['NAME']} (SN: {x['SN']})", axis=1).tolist()
        selected_option = st.selectbox("Select Client", client_options)
        
        # Extract the SN from the selection to find the right data
        selected_sn = selected_option.split("(SN: ")[1].replace(")", "")
        c = df[df['SN'] == selected_sn].iloc[0]
        
        st.markdown(f"""
        <div style="padding:30px; border:1px solid #e2e8f0; border-radius:10px; background-color: white; color: black;">
            <h2 style="text-align:center; color: #1e293b;">ZOE CONSULTS LIMITED</h2>
            <p style="text-align:center; border-bottom: 2px solid #00acee; padding-bottom:10px;">OFFICIAL LOAN STATEMENT</p>
            
            <div style="display: flex; justify-content: space-between;">
                <div>
                    <p><b>Client Name:</b> {c['NAME']}</p>
                    <p><b>Contact:</b> {c['CONTACT']}</p>
                    <p><b>Status:</b> <span style="color: {'#10b981' if c['STATUS'] == 'Active' else '#ef4444'}; font-weight: bold;">{c['STATUS']}</span></p>
                </div>
                <div style="text-align: right;">
                    <p><b>SN:</b> {c['SN']}</p>
                    <p><b>Issue Date:</b> {pd.to_datetime(c['DATE_OF_ISSUE']).strftime('%d-%b-%Y')}</p>
                    <p><b>Offer No:</b> {c['OFFER_NO']}</p>
                </div>
            </div>
            
            <hr style="border: 0.5px solid #eee;">
            
            <div style="display: flex; justify-content: space-around; background-color: #f8fafc; padding: 15px; border-radius: 5px;">
                <div style="text-align: center;">
                    <small>PRINCIPAL</small><br><b>UGX {c['LOAN_AMOUNT']:,.0f}</b>
                </div>
                <div style="text-align: center;">
                    <small>TOTAL PAID</small><br><b style="color: #10b981;">UGX {c['AMOUNT_PAID']:,.0f}</b>
                </div>
                <div style="text-align: center;">
                    <small>OUTSTANDING</small><br><b style="color: #ef4444;">UGX {c['OUTSTANDING_AMOUNT']:,.0f}</b>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 📅 Repayment Schedule")
        # Reuse the schedule engine
        try:
            sched = generate_schedule(c['LOAN_AMOUNT'], c['INTEREST_RATE'], c['DURATION_MONTHS'])
            st.table(sched.style.format("{:,.0f}").set_properties(**{'text-align': 'center'}))
        except Exception as e:
            st.warning("Could not generate schedule. Please check if 'Duration' and 'Rate' are set correctly for this client.")
    else:
        st.info("Registry is empty. Onboard a client first.")
