"""Streamlit dashboard for vendor extraction output."""

import json
import streamlit as st
from pathlib import Path
from datetime import datetime

st.set_page_config(
    page_title="Vendor Dashboard",
    page_icon="💒",
    layout="wide"
)

# Clean, light CSS
st.markdown("""
<style>
    /* Light background */
    .stApp {
        background-color: #f8fafc;
    }

    /* Header styling */
    .vendor-header {
        font-size: 2rem;
        font-weight: 600;
        color: #1e293b;
        margin-bottom: 0.25rem;
    }
    .vendor-category {
        display: inline-block;
        padding: 0.375rem 1rem;
        background: #ede9fe;
        color: #6d28d9;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 500;
        text-transform: capitalize;
        letter-spacing: 0.025em;
    }

    /* KPI Cards */
    .kpi-card {
        background: white;
        padding: 1.25rem 1.5rem;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .kpi-label {
        font-size: 0.75rem;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.5rem;
    }
    .kpi-value {
        font-size: 1.75rem;
        font-weight: 700;
        color: #0f172a;
    }
    .kpi-value-green {
        color: #059669;
    }
    .kpi-value-purple {
        color: #7c3aed;
    }
    .kpi-subtitle {
        font-size: 0.8rem;
        color: #94a3b8;
        margin-top: 0.25rem;
    }

    /* Status badges */
    .status-success {
        display: inline-flex;
        align-items: center;
        gap: 0.375rem;
        padding: 0.5rem 1rem;
        background: #ecfdf5;
        color: #047857;
        border-radius: 8px;
        font-weight: 500;
        font-size: 0.875rem;
    }
    .status-warning {
        display: inline-flex;
        align-items: center;
        gap: 0.375rem;
        padding: 0.5rem 1rem;
        background: #fef3c7;
        color: #b45309;
        border-radius: 8px;
        font-weight: 500;
        font-size: 0.875rem;
    }

    /* Section cards */
    .section-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        height: 100%;
    }
    .section-title {
        font-size: 0.8rem;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 1rem;
        padding-bottom: 0.75rem;
        border-bottom: 1px solid #f1f5f9;
    }

    /* Detail rows */
    .detail-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.875rem 1rem;
        background: #f8fafc;
        border-radius: 8px;
        margin-bottom: 0.5rem;
    }
    .detail-category {
        font-size: 0.65rem;
        font-weight: 600;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .detail-label {
        font-size: 0.9rem;
        color: #334155;
        margin-top: 0.125rem;
    }
    .detail-value {
        font-size: 1rem;
        font-weight: 600;
        color: #0f172a;
    }

    /* Commitment items */
    .commitment-item {
        padding: 1rem;
        background: #f8fafc;
        border-radius: 8px;
        margin-bottom: 0.75rem;
        border-left: 3px solid #10b981;
    }
    .commitment-title {
        font-size: 0.95rem;
        font-weight: 500;
        color: #1e293b;
    }
    .commitment-date {
        font-size: 0.8rem;
        color: #64748b;
        margin-top: 0.375rem;
    }
    .commitment-badge {
        display: inline-block;
        padding: 0.125rem 0.5rem;
        background: #e2e8f0;
        color: #64748b;
        border-radius: 4px;
        font-size: 0.7rem;
        margin-left: 0.5rem;
    }

    /* Thread items */
    .thread-item {
        padding: 0.875rem 1rem;
        background: #fffbeb;
        border-radius: 8px;
        margin-bottom: 0.5rem;
        border-left: 3px solid #f59e0b;
    }
    .thread-low {
        background: #f8fafc;
        border-left-color: #cbd5e1;
    }
    .thread-text {
        font-size: 0.9rem;
        color: #1e293b;
    }

    /* Summary box */
    .summary-box {
        background: white;
        padding: 1.25rem 1.5rem;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        font-size: 0.95rem;
        line-height: 1.6;
        color: #334155;
    }

    /* Next action highlight */
    .next-action-box {
        background: linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%);
        padding: 1.25rem 1.5rem;
        border-radius: 12px;
        color: white;
    }
    .next-action-label {
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        opacity: 0.8;
        margin-bottom: 0.5rem;
    }
    .next-action-text {
        font-size: 1.1rem;
        font-weight: 500;
    }

    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}
</style>
""", unsafe_allow_html=True)


def load_data():
    """Load extraction output JSON."""
    json_path = Path(__file__).parent / "extraction_output.json"
    if not json_path.exists():
        return None
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def format_date(date_str):
    """Format date string nicely."""
    if not date_str:
        return "TBD"
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d")
        return date.strftime("%d %b %Y")
    except:
        return date_str


def main():
    data = load_data()

    if not data:
        st.error("Could not load extraction_output.json. Run main.py first.")
        return

    # === HEADER ===
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown(f'<p class="vendor-header">{data["vendor_name"]}</p>', unsafe_allow_html=True)
        st.markdown(f'<span class="vendor-category">{data["vendor_category"]}</span>', unsafe_allow_html=True)
    with col2:
        if data.get("risk_flag"):
            st.markdown('<div class="status-warning">⚠️ Needs Attention</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-success">✓ On Track</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # === TOP KPIs - Most Important Info ===
    kpi1, kpi2, kpi3 = st.columns(3)

    with kpi1:
        if data.get("pending_payment"):
            payment = data["pending_payment"]
            amount = f"₹{payment['amount']:,.0f}"
            st.markdown(f'''
                <div class="kpi-card">
                    <div class="kpi-label">Pending Payment</div>
                    <div class="kpi-value kpi-value-green">{amount}</div>
                    <div class="kpi-subtitle">{payment.get("purpose", "Balance").capitalize()} • {payment.get("status", "").capitalize()}</div>
                </div>
            ''', unsafe_allow_html=True)
        else:
            st.markdown('''
                <div class="kpi-card">
                    <div class="kpi-label">Pending Payment</div>
                    <div class="kpi-value">₹0</div>
                    <div class="kpi-subtitle">All cleared</div>
                </div>
            ''', unsafe_allow_html=True)

    with kpi2:
        commitment_count = len(data.get("commitments", []))
        thread_count = len(data.get("loose_threads", []))
        st.markdown(f'''
            <div class="kpi-card">
                <div class="kpi-label">Open Items</div>
                <div class="kpi-value">{commitment_count + thread_count}</div>
                <div class="kpi-subtitle">{commitment_count} commitments • {thread_count} loose threads</div>
            </div>
        ''', unsafe_allow_html=True)

    with kpi3:
        next_commitment = data.get("commitments", [{}])[0] if data.get("commitments") else {}
        next_date = format_date(next_commitment.get("by_when", ""))
        st.markdown(f'''
            <div class="kpi-card">
                <div class="kpi-label">Next Date</div>
                <div class="kpi-value kpi-value-purple">{next_date}</div>
                <div class="kpi-subtitle">{next_commitment.get("what", "No upcoming dates")[:30]}...</div>
            </div>
        ''', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # === NEXT ACTION (Prominent) ===
    if data.get("next_action"):
        st.markdown(f'''
            <div class="next-action-box">
                <div class="next-action-label">→ Next Action Required</div>
                <div class="next-action-text">{data["next_action"]}</div>
            </div>
        ''', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

    # === SUMMARY ===
    st.markdown(f'''
        <div class="summary-box">
            <strong style="color: #64748b; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em;">Summary</strong><br><br>
            {data["summary"]}
        </div>
    ''', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # === TWO COLUMN LAYOUT: Details & Commitments ===
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">📋 Agreed Details</div>', unsafe_allow_html=True)

        for item in data.get("agreed_details", []):
            st.markdown(f'''
                <div class="detail-row">
                    <div>
                        <div class="detail-category">{item["category"]}</div>
                        <div class="detail-label">{item["detail"]}</div>
                    </div>
                    <div class="detail-value">{item["value"]}</div>
                </div>
            ''', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">📅 Commitments</div>', unsafe_allow_html=True)

        if data.get("commitments"):
            for item in data["commitments"]:
                date_str = format_date(item.get("by_when"))
                confidence = item.get("when_confidence", "")
                st.markdown(f'''
                    <div class="commitment-item">
                        <div class="commitment-title">{item["what"]}</div>
                        <div class="commitment-date">
                            📅 {date_str}
                            <span class="commitment-badge">{confidence}</span>
                        </div>
                    </div>
                ''', unsafe_allow_html=True)
        else:
            st.markdown('<p style="color: #94a3b8; font-size: 0.9rem;">No commitments yet</p>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # === LOOSE THREADS ===
    if data.get("loose_threads"):
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">🧵 Loose Threads</div>', unsafe_allow_html=True)

        cols = st.columns(2)
        for i, item in enumerate(data["loose_threads"]):
            urgency = item.get("urgency", "low")
            urgency_class = "thread-low" if urgency == "low" else ""
            with cols[i % 2]:
                st.markdown(f'''
                    <div class="thread-item {urgency_class}">
                        <div class="thread-text">{item["what"]}</div>
                    </div>
                ''', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    # === COMPLETED ===
    if data.get("completed") and len(data["completed"]) > 0:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">✅ Completed</div>', unsafe_allow_html=True)

        completed_html = " ".join([
            f'<span style="display: inline-block; padding: 0.375rem 0.75rem; background: #ecfdf5; color: #047857; border-radius: 6px; font-size: 0.85rem; margin: 0.25rem;">✓ {item}</span>'
            for item in data["completed"]
        ])
        st.markdown(completed_html, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
