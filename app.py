"""
app.py — Formspree → Claude API → Two-Path Email Automation Demo
Auto-transport brokerage carrier-matching and email routing.

Run:  streamlit run app.py
Env:  ANTHROPIC_API_KEY=<your key>
"""

import os
import pathlib
import streamlit as st
import pandas as pd
from carrier_agent import match_carriers

# ─── Config ────────────────────────────────────────────────────────────────────

BASE_DIR = pathlib.Path(__file__).parent
CSV_PATH = BASE_DIR / "sample_data" / "carriers.csv"

VEHICLE_TYPES = ["sedan", "SUV", "truck", "motorcycle", "boat"]

# ─── Page setup ────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Carrier Email Automation",
    page_icon="🚗",
    layout="wide",
)

st.title("Auto-Transport Carrier Email Automation")
st.caption(
    "Formspree booking → Claude carrier match → carrier RFQ or customer notification"
)

api_key = os.environ.get("ANTHROPIC_API_KEY") or st.secrets.get(
    "ANTHROPIC_API_KEY", None
)

st.markdown("---")

# ─── Layout: two columns ───────────────────────────────────────────────────────

left_col, right_col = st.columns([1, 1.6], gap="large")

# ─── Left column: input form ───────────────────────────────────────────────────

with left_col:
    st.subheader("Booking Details")
    st.markdown(
        "_Simulates a Formspree form submission from a customer booking an auto-transport shipment._"
    )

    with st.form("booking_form"):
        customer_name = st.text_input("Customer Name", value="Alex Johnson")
        customer_email = st.text_input(
            "Customer Email", value="alex.johnson@email.com"
        )

        pickup_zip = st.text_input(
            "Pickup ZIP Code",
            value="77002",
            help="Houston, TX area",
            max_chars=5,
        )
        delivery_zip = st.text_input(
            "Delivery ZIP Code",
            value="33101",
            help="Miami, FL area",
            max_chars=5,
        )

        vehicle_type = st.selectbox("Vehicle Type", VEHICLE_TYPES, index=0)

        email_branch = st.radio(
            "Email Branch",
            options=["carrier_rfq", "customer_notification"],
            format_func=lambda x: (
                "Carrier RFQ — ask carriers for rate quotes"
                if x == "carrier_rfq"
                else "Customer Notification — send matched carriers to customer"
            ),
        )

        submitted = st.form_submit_button(
            "Run Carrier Match", type="primary", use_container_width=True
        )

    # Show carrier CSV preview
    with st.expander("View carrier database (30 carriers)"):
        try:
            df_preview = pd.read_csv(CSV_PATH)
            st.dataframe(df_preview, use_container_width=True, height=220)
        except Exception as e:
            st.error(f"Could not load carrier CSV: {e}")

# ─── Right column: results ─────────────────────────────────────────────────────

with right_col:
    st.subheader("Matching Results")

    if not submitted:
        st.info(
            "Fill in the booking details on the left and click **Run Carrier Match** to see results.",
            icon="ℹ️",
        )
        st.markdown(
            """
**How it works:**
1. Customer books via Formspree (ZIP codes + vehicle type)
2. Claude reads the 800+ carrier list and selects best matches
3. System routes to one of two email branches:
   - **Carrier RFQ**: emails matched carriers requesting rate quotes
   - **Customer Notification**: emails the customer their carrier options
"""
        )
    else:
        with st.spinner("Claude is matching carriers to your route..."):
            result = match_carriers(
                pickup_zip=pickup_zip,
                delivery_zip=delivery_zip,
                vehicle_type=vehicle_type,
                csv_path=str(CSV_PATH),
                api_key=api_key,
            )

        pickup_state = result["pickup_state"]
        delivery_state = result["delivery_state"]
        carriers = result.get("matched_carriers", [])
        error = result.get("error")

        # Route summary
        st.markdown(
            f"**Route:** ZIP `{pickup_zip}` ({pickup_state}) → ZIP `{delivery_zip}` ({delivery_state}) "
            f"| **Vehicle:** {vehicle_type}"
        )

        if result.get("demo_mode"):
            st.caption("Sample output — connect your carrier CSV and API key for live matching.")

        if error:
            st.error(f"Error from carrier agent: {error}", icon="🚨")
        elif not carriers:
            st.warning(
                "No carriers matched this route. Try a different ZIP or vehicle type.",
                icon="⚠️",
            )
        else:
            # Matched carriers table
            st.markdown(f"#### {len(carriers)} Matched Carrier(s)")
            df_matched = pd.DataFrame(carriers)
            display_cols = [c for c in ["name", "email", "phone", "reason"] if c in df_matched.columns]
            st.dataframe(
                df_matched[display_cols],
                use_container_width=True,
                hide_index=True,
            )

            st.markdown("---")

            # Email preview
            st.markdown("#### Email Preview")

            if email_branch == "carrier_rfq":
                email_subject = (
                    f"Rate Quote Request — {vehicle_type.title()} "
                    f"from {pickup_state} to {delivery_state}"
                )
                carrier_list_text = "\n".join(
                    f"  - {c['name']} ({c.get('email', 'N/A')})"
                    for c in carriers
                )
                email_body = f"""Subject: {email_subject}

Hi [Carrier Name],

We have a shipment that matches your service area and we'd like to request a rate quote.

Shipment Details:
  - Pickup: ZIP {pickup_zip} ({pickup_state})
  - Delivery: ZIP {delivery_zip} ({delivery_state})
  - Vehicle Type: {vehicle_type.title()}

Please reply with your best rate and estimated transit time. We have a customer ready to book and would appreciate a response within 24 hours.

Carriers receiving this RFQ:
{carrier_list_text}

To submit your quote, reply to this email or call us at (713) 555-0000.

Thank you for your partnership,
Transport Ops Team
Houston Auto Brokerage"""

            else:  # customer_notification
                email_subject = (
                    f"Your Carrier Options — {vehicle_type.title()} Transport"
                )
                carrier_list_text = "\n".join(
                    f"  {i+1}. {c['name']} | {c.get('email', 'N/A')} | {c.get('phone', 'N/A')}"
                    for i, c in enumerate(carriers)
                )
                email_body = f"""Subject: {email_subject}

Hi {customer_name},

We've matched your shipment with the following qualified carriers. Each carrier covers your route and handles {vehicle_type}s.

Your Shipment:
  - Pickup: ZIP {pickup_zip} ({pickup_state})
  - Delivery: ZIP {delivery_zip} ({delivery_state})
  - Vehicle: {vehicle_type.title()}

Matched Carriers:
{carrier_list_text}

We have sent a rate quote request (RFQ) to all carriers above. You can expect quotes to arrive within 24-48 hours. We'll follow up once we have pricing.

Questions? Reply to this email or call (713) 555-0000.

Best regards,
Houston Auto Brokerage"""

            st.markdown(
                f"""
<div style="
    background-color: #f8f9fa;
    border-left: 4px solid #1f77b4;
    border-radius: 4px;
    padding: 16px 20px;
    font-family: monospace;
    font-size: 13px;
    white-space: pre-wrap;
    line-height: 1.6;
    color: #212529;
">{email_body}</div>
""",
                unsafe_allow_html=True,
            )

            st.success(
                f"Ready to send to {'matched carriers' if email_branch == 'carrier_rfq' else customer_email}",
                icon="✅",
            )

# ─── Footer ────────────────────────────────────────────────────────────────────

st.markdown("---")
st.caption(
    "Demo only — no emails are actually sent. "
    "Production system uses Formspree webhooks → n8n → Claude API → SendGrid/Gmail."
)
