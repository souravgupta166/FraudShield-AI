import os
from datetime import datetime, timezone

import httpx
import streamlit as st
import streamlit.components.v1 as components


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")

st.set_page_config(
    page_title="FraudShield AI | Intelligence Workspace",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
    :root { --fs-bg:#0b0d10; --fs-panel:#14181e; --fs-line:#29313b; --fs-text:#f2f4f7; --fs-muted:#a1aab5; --fs-orange:#f7931a; }
    html,body,[class*="css"]{font-family:'Manrope',sans-serif}
    .stApp{background:radial-gradient(ellipse at 80% -10%,rgba(247,147,26,.09),transparent 30%),radial-gradient(ellipse at 4% 12%,rgba(65,91,115,.12),transparent 28%),var(--fs-bg);color:var(--fs-text)}
    [data-testid="stHeader"]{background:rgba(11,13,16,.92)}
    .block-container{max-width:1500px;padding-top:1.4rem;padding-bottom:4rem}
    [data-testid="stSidebar"]{background:linear-gradient(180deg,#11151b,#0d1015);border-right:1px solid var(--fs-line)}
    [data-testid="stSidebar"]>div{padding-top:1.35rem}
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,[data-testid="stSidebar"] [data-testid="stCaptionContainer"]{color:#aab3be!important}
    [data-testid="stSidebar"] strong{color:#f1f3f6!important}
    h1,h2,h3,h4{color:#f4f6f8!important;letter-spacing:-.04em}
    h1{font-weight:800!important} h2,h3{font-weight:750!important}
    p,li,label,[data-testid="stMarkdownContainer"]{color:#d0d6dd}
    [data-testid="stCaptionContainer"],small{color:#a1aab5!important}
    code,pre,.stCode,[data-testid="stCode"]{font-family:'DM Mono',monospace!important}
    div[data-testid="stMetric"]{background:linear-gradient(145deg,#1a2028,#14191f);border:1px solid #303945;border-radius:15px;padding:16px 18px;min-height:105px;box-shadow:0 8px 24px rgba(0,0,0,.18)}
    [data-testid="stMetricLabel"]{color:#aab4c0!important;font-size:.76rem;font-weight:700}
    [data-testid="stMetricValue"]{color:#f6f7f9!important;font-weight:800;letter-spacing:-.04em;font-variant-numeric:tabular-nums}
    [data-testid="stMetricDelta"]{font-family:'DM Mono',monospace}
    div[data-testid="stForm"],div[data-testid="stExpander"],div[data-testid="stDataFrame"],div[data-testid="stTable"]{border:1px solid #303945;border-radius:14px;background:#14191f}
    div[data-testid="stForm"]{padding:1.15rem 1.2rem}
    div[data-testid="stExpander"] summary{color:#edf1f5!important;font-weight:700}
    .stTextInput input,.stTextArea textarea,.stNumberInput input,.stDateInput input,.stTimeInput input{background:#0e1319!important;color:#f2f4f7!important;border:1px solid #3a4653!important;border-radius:10px!important;font-family:'DM Mono',monospace!important}
    .stTextInput input::placeholder,.stTextArea textarea::placeholder{color:#778391!important}
    .stTextInput input:focus,.stTextArea textarea:focus,.stNumberInput input:focus{border-color:var(--fs-orange)!important;box-shadow:0 0 0 1px var(--fs-orange)!important}
    [data-baseweb="select"]>div,[data-baseweb="input"]>div{background:#10151c!important;border-color:#3a4653!important;color:#f2f4f7!important}
    [data-baseweb="popover"],[data-baseweb="menu"]{background:#171d25!important;color:#f2f4f7!important}
    [role="option"]{color:#f2f4f7!important}
    .stButton button,[data-testid="stFormSubmitButton"] button{border-radius:10px;border:1px solid #f7931a;background:linear-gradient(110deg,#f7931a,#e98212);color:#17120b!important;font-weight:800;transition:all .16s ease}
    .stButton button:hover,[data-testid="stFormSubmitButton"] button:hover{transform:translateY(-1px);box-shadow:0 7px 22px rgba(247,147,26,.2);background:#ffab3d;border-color:#ffab3d}
    .stButton button p,[data-testid="stFormSubmitButton"] button p{color:#17120b!important}
    [data-testid="stTabs"] button{color:#aeb8c3!important;font-weight:700}
    [data-testid="stTabs"] button[aria-selected="true"]{color:#ffad45!important;border-bottom-color:#f7931a!important}
    hr{border-color:#29313b!important}
    [data-testid="stAlert"]{border-radius:12px;border:1px solid #303945}
    [data-testid="stCode"] pre{background:#0e1319!important;color:#e8edf2!important;border:1px solid #303945;border-radius:11px}
    [data-testid="stJson"]{background:#10151c;border-radius:10px}
    .fs-eyebrow{color:#ffb75e;font:500 11px 'DM Mono',monospace;letter-spacing:.18em;text-transform:uppercase}
    .fs-hero{position:relative;overflow:hidden;padding:27px 31px 25px;margin:4px 0 24px;border:1px solid rgba(247,147,26,.28);border-radius:19px;background:radial-gradient(circle at 88% 5%,rgba(247,147,26,.16),transparent 27%),linear-gradient(112deg,#191f27,#12171e 66%,#1b1b1b);box-shadow:0 16px 42px rgba(0,0,0,.22)}
    .fs-hero h1{margin:7px 0 5px;color:#f6f7f8!important;font-size:clamp(1.8rem,3vw,2.55rem)}
    .fs-hero p{margin:0;color:#b8c1cb!important;max-width:760px}
    .fs-hero-tag{display:inline-block;margin-top:16px;padding:6px 10px;border-radius:7px;border:1px solid rgba(247,147,26,.32);color:#ffc477;background:rgba(247,147,26,.08);font:11px 'DM Mono',monospace;letter-spacing:.08em}
    .fs-section-kicker{color:#f7a63e;font:500 10px 'DM Mono',monospace;letter-spacing:.16em;text-transform:uppercase;margin-bottom:3px}
    .fs-mono{font-family:'DM Mono',monospace;font-variant-numeric:tabular-nums}
    .fs-help-card{border:1px solid #303945;border-radius:13px;padding:14px 16px;background:linear-gradient(135deg,#171e26,#131920);margin:8px 0 14px}
    .fs-help-card strong{color:#f4f6f8}

    .fs-rail-heading{font:500 10px 'DM Mono',monospace;letter-spacing:.16em;color:#f7a63e;margin:20px 0 9px}
    .fs-rail-card{background:linear-gradient(145deg,#1a2028,#12171e);border:1px solid #303945;border-radius:14px;padding:15px;margin:5px 0 12px}
    .fs-rail-label{font:500 10px 'DM Mono',monospace;letter-spacing:.13em;color:#a1aab5}
    .fs-rail-status{font-size:18px;font-weight:800;color:#f2f4f7;margin-top:8px}
    .fs-rail-note{font-size:11px;color:#a1aab5;margin-top:3px}
    .fs-rail-row{display:flex;justify-content:space-between;padding:9px 2px;border-bottom:1px solid #29313b;color:#b7c0ca;font-size:12px}
    .fs-rail-row strong{color:#f2f4f7;font-family:'DM Mono',monospace;font-variant-numeric:tabular-nums}
    .fs-event{border-left:1px solid #46515e;padding:2px 0 10px 12px;margin-left:4px;color:#e4e8ed;font-size:11px}
    .fs-event-dot{display:inline-block;width:6px;height:6px;border-radius:50%;background:#f7931a;margin:0 7px 1px -16px}
    .fs-event small{color:#9ca7b3}
    .fs-rail-footnote{margin-top:22px;padding-top:13px;border-top:1px solid #29313b;color:#8e99a6;font:10px 'DM Mono',monospace;line-height:1.7}
    @media(max-width:900px){.fs-rail-heading{margin-top:12px}}

    @media(max-width:800px){.block-container{padding-left:1rem;padding-right:1rem}.fs-hero{padding:21px}}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="fs-hero">
      <div class="fs-eyebrow">FRAUDSHIELD AI &nbsp; / &nbsp; BITCOIN INTELLIGENCE</div>
      <h1>Good to see you. <span style="color:#f7931a">Stay ahead of risk.</span></h1>
      <p>Monitor the Bitcoin data pipeline, investigate transactions and review sanctions evidence in one workspace.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown(
        """
        <div style="padding:4px 0 15px">
          <div style="font:500 10px 'DM Mono',monospace;letter-spacing:.18em;color:#f7931a">FRAUDSHIELD / INTEL</div>
          <div style="font-size:22px;font-weight:800;letter-spacing:-1px;color:#f2f4f7;margin-top:5px">Command Center</div>
          <div style="font:11px 'DM Mono',monospace;color:#9ca7b3;margin-top:4px">BUILD 0.1.0 · BTC MAINNET</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.divider()
    st.markdown("**WORKSPACES**")
    st.markdown("◈ &nbsp; Network operations", unsafe_allow_html=True)
    st.markdown("⌕ &nbsp; Transaction investigation", unsafe_allow_html=True)
    st.markdown("◎ &nbsp; Address sanctions screening", unsafe_allow_html=True)
    st.divider()
    st.markdown("**SYSTEM CONTEXT**")
    st.caption("Network · Bitcoin")
    st.caption("Evidence · Public blockchain records")
    st.caption("API · FastAPI")
    st.caption("Storage · PostgreSQL")
    st.divider()
    st.markdown(
        '<span style="color:#f7931a;font:11px \'DM Mono\',monospace">● LIVE MONITORING ENABLED</span>',
        unsafe_allow_html=True,
    )

    st.divider()
    st.markdown("**NAVIGATION**")
    active_page = st.radio(
        "Workspace",
        ["Network Monitoring", "Investigations"],
        label_visibility="collapsed",
        key="fraudshield_active_page",
    )
    st.divider()
    st.caption(
        "Monitoring provides ingestion health and data coverage. "
        "Investigations combines transaction analysis and Bitcoin address sanctions screening."
    )



# ==================================================
# LIVE BITCOIN INGESTION MONITOR
# ==================================================

@st.fragment(run_every="60s")
def render_ingestion_monitor():
    heading_col, refresh_col = st.columns([3, 1])

    heading_col.title("Network Operations")

    with refresh_col:
        st.markdown(
            """
            <div style="
                text-align: right;
                color: #888;
                font-size: 12px;
                padding-top: 5px;
            ">
                LIVE CLOCK
            </div>
            """,
            unsafe_allow_html=True,
        )

        components.html(
            """
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {
                        margin: 0;
                        padding: 0;
                        font-family: sans-serif;
                        text-align: right;
                    }

                    #live-clock {
                        font-size: 18px;
                        font-weight: 600;
                        color: inherit;
                    }
                </style>
            </head>
            <body>
                <div id="live-clock">--:--:--</div>

                <script>
                    function updateClock() {
                        const now = new Date();

                        document.getElementById("live-clock").textContent =
                            now.toLocaleTimeString(undefined, {
                                hour: "2-digit",
                                minute: "2-digit",
                                second: "2-digit",
                                hour12: false
                            });
                    }

                    updateClock();
                    setInterval(updateClock, 1000);
                </script>
            </body>
            </html>
            """,
            height=55,
            scrolling=False,
        )

    st.caption(
        "Monitor the health, coverage and freshness of Bitcoin data "
        "collected by FraudShield AI."
    )

    try:
        monitor_response = httpx.get(
            f"{API_BASE_URL}/api/v1/bitcoin/ingestion/monitor",
            timeout=15.0,
        )
        monitor_response.raise_for_status()
        monitor_data = monitor_response.json()

        ingestion = monitor_data.get("ingestion_runs", {})
        blockchain = monitor_data.get("blockchain_data", {})
        latest = monitor_data.get("latest_ingestion") or {}
        transaction_statuses = blockchain.get("transactions_by_status", {})

        monitor_status = monitor_data.get("status", "unknown").upper()

        if monitor_status == "OPERATIONAL":
            st.success(f"Ingestion service status: {monitor_status}")
        else:
            st.warning(f"Ingestion service status: {monitor_status}")

        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Latest stored block",
            f"{blockchain['latest_block_height']:,}"
            if blockchain.get("latest_block_height") is not None
            else "Unavailable",
        )
        col2.metric(
            "Canonical blocks stored",
            f"{blockchain.get('canonical_blocks_stored', 0):,}",
        )
        col3.metric(
            "Stored transactions",
            f"{blockchain.get('total_stored_transactions', 0):,}",
        )
        col4.metric(
            "Completed ingestion runs",
            f"{ingestion.get('completed', 0):,}",
            delta=f"{ingestion.get('failed', 0)} failed",
            delta_color="inverse",
        )

        st.subheader("Ingestion health")

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Total runs", f"{ingestion.get('total', 0):,}")
        col2.metric("Completed", f"{ingestion.get('completed', 0):,}")
        col3.metric("Running", f"{ingestion.get('running', 0):,}")
        col4.metric("Failed", f"{ingestion.get('failed', 0):,}")

        st.subheader("Stored transaction breakdown")

        col1, col2, col3 = st.columns(3)
        col1.metric("Confirmed", f"{transaction_statuses.get('confirmed', 0):,}")
        col2.metric("Mempool", f"{transaction_statuses.get('mempool', 0):,}")
        col3.metric("Orphaned", f"{transaction_statuses.get('orphaned', 0):,}")

        st.subheader("Data freshness")

        if latest.get("finished_at") or latest.get("started_at"):
            latest_timestamp = datetime.fromisoformat(
                latest.get("finished_at") or latest["started_at"]
            )

            if latest_timestamp.tzinfo is None:
                latest_timestamp = latest_timestamp.replace(tzinfo=timezone.utc)

            age_seconds = max(
                0,
                int((datetime.now(timezone.utc) - latest_timestamp).total_seconds()),
            )

            if age_seconds < 60:
                freshness_label = f"{age_seconds} seconds ago"
            elif age_seconds < 3600:
                freshness_label = f"{age_seconds // 60} minutes ago"
            elif age_seconds < 86400:
                freshness_label = f"{age_seconds // 3600} hours ago"
            else:
                freshness_label = f"{age_seconds // 86400} days ago"

            col1, col2 = st.columns(2)
            col1.metric("Last successful/recorded run", freshness_label)
            col2.metric(
                "Latest run status",
                str(latest.get("status", "Unknown")).upper(),
            )

            st.caption(
                "Latest recorded ingestion completion: "
                + latest_timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
            )

            if age_seconds > 86400:
                st.warning(
                    "No ingestion has been recorded in the last 24 hours. "
                    "The stored dataset may be stale."
                )
            else:
                st.info(
                    "Freshness is measured from the latest recorded ingestion run. "
                    "It does not independently verify the current Bitcoin network tip."
                )
        else:
            st.info("No ingestion runs have been recorded yet.")

        st.subheader("Recent ingestion activity")

        recent_runs = monitor_data.get("recent_runs", [])

        if recent_runs:
            display_runs = [
                {
                    "Started (UTC)": run.get("started_at"),
                    "Source": run.get("source"),
                    "Status": run.get("status"),
 
def render_intelligence_rail():
    """Show live, database-backed Bitcoin intelligence alongside the workspace."""
    st.markdown(
        '<div class="fs-rail-heading">NETWORK INTELLIGENCE</div>',
        unsafe_allow_html=True,
    )
    try:
        response = httpx.get(
            f"{API_BASE_URL}/api/v1/bitcoin/ingestion/monitor",
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()
        blockchain = data.get("blockchain_data", {})
        ingestion = data.get("ingestion_runs", {})
        statuses = blockchain.get("transactions_by_status", {})
        status = str(data.get("status", "unknown")).upper()

        status_color = "#58c995" if status == "OPERATIONAL" else "#f0ae55"
        st.markdown(
            f'<div class="fs-rail-card"><div class="fs-rail-label">PIPELINE STATUS</div>'
            f'<div class="fs-rail-status"><span style="color:{status_color}">●</span> {status}</div>'
            f'<div class="fs-rail-note">FraudShield ingestion service</div></div>',
            unsafe_allow_html=True,
        )

        st.markdown('<div class="fs-rail-heading">BITCOIN DATA</div>', unsafe_allow_html=True)
        rail_col1, rail_col2 = st.columns(2)
        with rail_col1:
            st.metric(
                "LATEST BLOCK",
                f"{blockchain['latest_block_height']:,}"
                if blockchain.get("latest_block_height") is not None else "—",
            )
        with rail_col2:
            st.metric(
                "TX RECORDS",
                f"{blockchain.get('total_stored_transactions', 0):,}",
            )

        st.markdown('<div class="fs-rail-heading">TRANSACTION POOL</div>', unsafe_allow_html=True)
        for label, key in (
            ("Confirmed", "confirmed"),
            ("Mempool", "mempool"),
            ("Orphaned", "orphaned"),
        ):
            count = statuses.get(key, 0)
            st.markdown(
                f'<div class="fs-rail-row"><span>{label}</span>'
                f'<strong>{count:,}</strong></div>',
                unsafe_allow_html=True,
            )

        st.markdown('<div class="fs-rail-heading">INGESTION ACTIVITY</div>', unsafe_allow_html=True)
        st.metric("Completed runs", f"{ingestion.get('completed', 0):,}")
        st.metric("Failed runs", f"{ingestion.get('failed', 0):,}")

        recent = data.get("recent_runs", [])
        if recent:
            st.markdown('<div class="fs-rail-heading">RECENT EVENTS</div>', unsafe_allow_html=True)
            for run in recent[:3]:
                run_status = str(run.get("status", "unknown")).upper()
                st.markdown(
                    f'<div class="fs-event"><span class="fs-event-dot"></span>'
                    f'<strong>{run_status}</strong><br>'
                    f'<small>{run.get("source") or "Bitcoin ingestion"} · '
                    f'{run.get("transactions_processed", 0)} transactions</small></div>',
                    unsafe_allow_html=True,
                )
    except (httpx.RequestError, httpx.HTTPStatusError, ValueError, TypeError):
        st.markdown(
            '<div class="fs-rail-card"><div class="fs-rail-label">PIPELINE STATUS</div>'
            '<div class="fs-rail-status" style="color:#e4777e">● UNAVAILABLE</div>'
            '<div class="fs-rail-note">Could not retrieve live API metrics.</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="fs-rail-footnote">ON-CHAIN EVIDENCE ONLY<br>'
        'Public blockchain records do not independently establish identity or criminal activity.</div>',
        unsafe_allow_html=True,
    )


workspace_col, intelligence_col = st.columns([3.15, 1.12], gap="large")
with workspace_col:
    if active_page == "Network Monitoring":
        render_ingestion_monitor()

    if active_page == "Investigations":
        st.markdown(
            '<div class="fs-section-kicker">CASEWORK / ON-CHAIN INTELLIGENCE</div>',
            unsafe_allow_html=True,
        )
        st.title("Transaction Investigation")

        st.caption(
            "Inspect on-chain transaction details, explainable risk indicators "
            "and observed UTXO graph relationships."
        )

        st.markdown(
            '<div class="fs-help-card"><strong>Try a live investigation</strong><br><span style="color:#a1aab5">Paste a Bitcoin transaction ID, or load the verified example stored in this demo environment.</span></div>',
            unsafe_allow_html=True,
        )
        demo_txid = "64a24d399c4302373531a40bbd87fa9d1b4dc0d4699b573cbd43a9269a00a87e"
        def load_demo_transaction():
            st.session_state["transaction_txid_input"] = demo_txid
        demo_col, note_col = st.columns([1, 3])
        with demo_col:
            st.button("Load example transaction", key="load_demo_transaction", on_click=load_demo_transaction, use_container_width=True)
        with note_col:
            st.caption("Example transaction · confirmed on Bitcoin mainnet · explore the full investigation workflow")
        with st.form("transaction_search"):
            txid = st.text_input(
                "Bitcoin transaction ID",
                placeholder="Paste a 64-character transaction ID",
                max_chars=64,
                key="transaction_txid_input",
                help="A transaction ID is a 64-character hexadecimal identifier.",
            ).strip().lower()

            submitted = st.form_submit_button(
                "Investigate transaction",
                type="primary",
                use_container_width=True,
            )

        if submitted:
            if len(txid) != 64 or any(c not in "0123456789abcdef" for c in txid):
                st.error("Enter a valid 64-character hexadecimal transaction ID.")
            else:
                with st.spinner("Retrieving transaction evidence..."):
                    try:
                        response = httpx.get(
                            f"{API_BASE_URL}/api/v1/bitcoin/transactions/{txid}/investigation",
                            timeout=30.0,
                        )

                        if response.status_code == 404:
                            st.error("Transaction not found in the FraudShield database.")
                        elif response.status_code != 200:
                            st.error(
                                f"Investigation request failed: HTTP {response.status_code}"
                            )
                            st.code(response.text[:1500])
                        else:
                            result = response.json()

                            st.session_state["investigation_result"] = result
                            st.session_state["investigation_txid"] = txid

                    except httpx.RequestError as exc:
                        st.error(f"Could not connect to the FraudShield API: {exc}")

        result = st.session_state.get("investigation_result")
        current_txid = st.session_state.get("investigation_txid")

        if result:
            transaction_record = result.get("transaction_record", {})
            transaction = transaction_record.get("transaction", {})
            block = transaction_record.get("block") or {}
            summary = transaction_record.get("summary", {})
            features = result.get("features", {})
            graph = result.get("graph_context", {})
            findings = result.get("transaction_findings", [])
            address_activity = result.get("address_activity", [])
            sanctions_screening = result.get("address_sanctions_screening", {})

            st.divider()

            st.subheader("Investigation overview")

            st.code(current_txid, language=None)

            status = transaction.get("status", "Unknown")
            block_height = block.get("height", "Unconfirmed")
            fee_sats = transaction.get("fee_sats")

            col1, col2, col3, col4 = st.columns(4)

            col1.metric("Transaction status", str(status).upper())
            col2.metric("Block height", str(block_height))
            col3.metric(
                "Transaction fee",
                f"{fee_sats:,} sats" if isinstance(fee_sats, int) else "Unavailable",
            )
            col4.metric(
                "Fee rate",
                f"{features['fee_rate_sat_vb']:.2f} sat/vB"
                if isinstance(features.get("fee_rate_sat_vb"), (int, float))
                else "Unavailable",
            )

            # --------------------------------------------------
            # Investigation evidence timeline
            # --------------------------------------------------

            st.divider()
            st.subheader("Investigation evidence timeline")

            block_time = block.get("time")
            first_seen_at = transaction.get("first_seen_at")

            timeline_events = []

            if block_time:
                timeline_events.append(
                    (
                        block_time,
                        "Bitcoin block confirmation",
                        f"Transaction included in block {block.get('height', 'Unknown')} "
                        f"({block.get('hash', 'Hash unavailable')}).",
                    )
                )

            if first_seen_at:
                timeline_events.append(
                    (
                        first_seen_at,
                        "Transaction first observed",
                        "FraudShield recorded this transaction in its local dataset.",
                    )
                )

            if timeline_events:
                timeline_events.sort(key=lambda event: event[0])

                for timestamp, event_name, description in timeline_events:
                    with st.container(border=True):
                        st.markdown(f"**{event_name}**")
                        st.caption(f"Timestamp: {timestamp}")
                        st.write(description)
            else:
                st.info("No timestamped transaction events are available.")

            st.caption(
                "Block time is the timestamp reported by the Bitcoin block. "
                "First observed is the local database recording time; it is not "
                "necessarily the time the transaction was first broadcast."
            )

            st.markdown("**Investigation evidence snapshot**")

            col1, col2, col3 = st.columns(3)

            col1.metric(
                "Triggered transaction indicators",
                len(findings),
            )
            col2.metric(
                "Connected transactions observed",
                len(graph.get("connected_transaction_ids", [])),
            )
            col3.metric(
                "OFAC address matches",
                sanctions_screening.get("matched_address_count", 0),
            )

            st.caption(
                "These are findings from the current investigation response, "
                "not additional timestamped blockchain events."
            )

            st.subheader("Transaction structure")

            col1, col2, col3 = st.columns(3)
            col1.metric("Inputs", summary.get("input_count", "—"))
            col2.metric("Outputs", summary.get("output_count", "—"))
            col3.metric(
                "Accounting complete",
                "Yes" if summary.get("accounting_complete") else "No",
            )

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Known input value**")
                value = summary.get("known_input_total_sats")
                st.metric(
                    "Satoshis",
                    f"{value:,}" if isinstance(value, int) else "Unavailable",
                )

            with col2:
                st.markdown("**Total output value**")
                value = summary.get("total_output_sats")
                st.metric(
                    "Satoshis",
                    f"{value:,}" if isinstance(value, int) else "Unavailable",
                )

            st.subheader("Explainable risk indicators")

            if findings:
                for finding in findings:
                    severity = finding.get("severity", "informational")
                    message = finding.get("description") or finding.get("indicator", "Finding")

                    if severity == "warning":
                        st.warning(f"**{finding.get('indicator', 'Finding')}** — {message}")
                    elif severity == "high":
                        st.error(f"**{finding.get('indicator', 'Finding')}** — {message}")
                    else:
                        st.info(f"**{finding.get('indicator', 'Finding')}** — {message}")

                    with st.expander("View finding evidence"):
                        st.json(finding)
            else:
                st.success("No configured transaction indicators were triggered.")

            st.caption(
                "No triggered indicator does not establish that a transaction is safe. "
                "These indicators are investigative signals, not proof of fraud."
            )

            st.subheader("Observed graph context")

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Stored transactions", graph.get("stored_transaction_count", "—"))
            col2.metric("Input outpoints", graph.get("input_outpoint_count", "—"))
            col3.metric("Output outpoints", graph.get("output_outpoint_count", "—"))
            col4.metric("External input outpoints", graph.get("external_input_outpoint_count", "—"))

            st.caption(
                f"Graph scope: {graph.get('dataset_scope', 'Unavailable')}"
            )

            with st.expander("Connected transaction IDs"):
                st.markdown("**Previous transactions observed**")
                st.write(graph.get("known_previous_transaction_ids", []))
                st.markdown("**Later spending transactions observed**")
                st.write(graph.get("known_spending_transaction_ids", []))

            with st.expander("Input and output addresses"):
                st.markdown("**Input addresses**")
                st.write(graph.get("input_addresses", []))
                st.markdown("**Output addresses**")
                st.write(graph.get("output_addresses", []))

            st.subheader("Address activity")

            if address_activity:
                st.dataframe(
                    address_activity,
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("No address activity records were returned.")

            # --------------------------------------------------
            # Automatic OFAC sanctions screening
            # --------------------------------------------------

            st.subheader("Automatic OFAC sanctions screening")

            screened_count = sanctions_screening.get("screened_address_count", 0)
            matched_count = sanctions_screening.get("matched_address_count", 0)
            screening_results = sanctions_screening.get("results", [])

            col1, col2 = st.columns(2)
            col1.metric("Addresses screened", screened_count)
            col2.metric("Exact OFAC address matches", matched_count)

            if screening_results:
                screening_rows = []

                for item in screening_results:
                    screening = item.get("screening", {})

                    screening_rows.append(
                        {
                            "Bitcoin address": item.get("address", ""),
                            "Transaction role": ", ".join(
                                item.get("transaction_roles", [])
                            ),
                            "Screening status": screening.get(
                                "match_status", "unknown"
                            ).replace("_", " ").upper(),
                            "Matching records": screening.get("match_count", 0),
                        }
                    )

                st.dataframe(
                    screening_rows,
                    use_container_width=True,
                    hide_index=True,
                )

                if matched_count:
                    st.warning(
                        "One or more transaction addresses exactly match records "
                        "in the active OFAC snapshot. This is an investigative lead, "
                        "not proof of ownership, control, or illicit activity."
                    )
                else:
                    st.success(
                        "No exact address matches were found in the active OFAC snapshot."
                    )

                for item in screening_results:
                    screening = item.get("screening", {})
                    matches = screening.get("matches", [])

                    if not matches:
                        continue

                    address = item.get("address", "Unknown address")
                    roles = ", ".join(item.get("transaction_roles", []))

                    with st.expander(
                        f"OFAC evidence — {address} ({roles})"
                    ):
                        for index, match in enumerate(matches, start=1):
                            st.markdown(
                                f"**Match {index}: "
                                f"{match.get('entity_name', 'Unknown entity')}**"
                            )

                            st.write(
                                {
                                    "Entity ID": match.get("entity_id"),
                                    "Entity type": match.get("entity_type"),
                                    "Source record ID": match.get("source_record_id"),
                                    "Feature version ID": match.get("feature_version_id"),
                                    "Sanctions programmes": match.get(
                                        "sanctions_programmes", []
                                    ),
                                    "Primary record": match.get("is_primary"),
                                    "Reliability": match.get("reliability"),
                                }
                            )

                            source = match.get("source", {})

                            if source:
                                st.markdown("**Source provenance**")
                                st.write(
                                    {
                                        "Dataset": source.get("name"),
                                        "Dataset version": source.get("dataset_version"),
                                        "Published at": source.get("published_at"),
                                        "SHA-256": source.get("checksum_sha256"),
                                    }
                                )

                                source_url = source.get("url")
                                if source_url:
                                    st.markdown(
                                        f"[Official sanctions dataset]({source_url})"
                                    )

                            if index < len(matches):
                                st.divider()

            else:
                st.info("No address screening results were returned.")

            st.caption(
                sanctions_screening.get(
                    "screening_note",
                    "Screening results are limited to addresses observed in the "
                    "stored transaction graph and the active OFAC snapshot."
                )
            )

            with st.expander("Raw transaction inputs and outputs"):
                st.markdown("**Inputs**")
                st.json(transaction_record.get("inputs", []))
                st.markdown("**Outputs**")
                st.json(transaction_record.get("outputs", []))

            with st.expander("Full investigation response"):
                st.json(result)

            st.divider()
            st.caption(result.get("investigation_note", ""))

        else:
            st.info(
                "Enter a Bitcoin transaction ID above to begin an investigation."
            )

            st.markdown("### Available investigation evidence")
            col1, col2, col3 = st.columns(3)
            col1.markdown("**Transaction analysis**\n\nInputs, outputs, fees and value reconciliation.")
            col2.markdown("**Risk indicators**\n\nExplainable transaction-level findings.")
            col3.markdown("**UTXO graph context**\n\nObserved connected transactions and addresses.")

        st.divider()

        st.markdown(
            '<div class="fs-section-kicker">ADDRESS INTELLIGENCE / SANCTIONS</div>',
            unsafe_allow_html=True,
        )
        st.header("Bitcoin Address Sanctions Screening")
        st.caption(
            "Check an address against the active official OFAC sanctions snapshot. "
            "Exact matches are investigative leads, not proof of ownership or wrongdoing."
        )
        st.markdown(
            '<div class="fs-help-card"><strong>Address screening</strong><br><span style="color:#a1aab5">Paste a Bitcoin address to review exact matches, entity details and official dataset provenance.</span></div>',
            unsafe_allow_html=True,
        )

        with st.form("sanctions_screening"):
            address_to_screen = st.text_input(
                "Bitcoin address",
                placeholder="Enter a Bitcoin address",
                max_chars=90,
            ).strip()

            sanctions_submitted = st.form_submit_button(
                "Screen address",
                type="primary",
                use_container_width=True,
            )

        if sanctions_submitted:
            if (
                len(address_to_screen) < 14
                or len(address_to_screen) > 90
                or not address_to_screen.isalnum()
            ):
                st.error("Enter a valid-looking alphanumeric Bitcoin address.")
            else:
                with st.spinner("Checking the active OFAC sanctions snapshot..."):
                    try:
                        response = httpx.get(
                            f"{API_BASE_URL}/api/v1/bitcoin/addresses/"
                            f"{address_to_screen}/sanctions-screening",
                            timeout=30.0,
                        )

                        if response.status_code != 200:
                            st.error(
                                f"Sanctions screening failed: HTTP {response.status_code}"
                            )
                            st.code(response.text[:1500])
                        else:
                            st.session_state["sanctions_result"] = response.json()
                            st.session_state["sanctions_address"] = address_to_screen

                    except httpx.RequestError as exc:
                        st.error(f"Could not connect to the FraudShield API: {exc}")

        sanctions_result = st.session_state.get("sanctions_result")

        if sanctions_result:
            st.markdown("#### Screening result")
            st.code(st.session_state.get("sanctions_address", ""), language=None)

            match_count = sanctions_result.get("match_count", 0)

            col1, col2 = st.columns(2)
            col1.metric(
                "Screening status",
                sanctions_result.get("match_status", "Unknown").replace("_", " ").upper(),
            )
            col2.metric("Matching OFAC records", match_count)

            if sanctions_result.get("is_sanctioned_address_match"):
                st.warning(
                    "Exact address match found in the active OFAC snapshot. "
                    "Review every source record before drawing conclusions."
                )

                for index, match in enumerate(sanctions_result.get("matches", []), start=1):
                    entity_name = match.get("entity_name", "Unknown entity")
                    entity_id = match.get("entity_id", "Unavailable")

                    with st.expander(
                        f"OFAC record {index}: {entity_name} | Entity ID: {entity_id}",
                        expanded=True,
                    ):
                        st.write(f"**Entity type:** {match.get('entity_type') or 'Unavailable'}")
                        st.write(f"**OFAC feature record ID:** {match.get('source_record_id')}")
                        st.write(
                            "**Sanctions programmes:** "
                            + ", ".join(match.get("sanctions_programmes") or [])
                        )
                        st.write(f"**Primary address:** {match.get('is_primary')}")

                        source = match.get("source", {})
                        st.write(f"**Dataset version:** {source.get('dataset_version', 'Unavailable')}")
                        st.write(f"**Published at:** {source.get('published_at', 'Unavailable')}")
                        st.markdown(
                            f"[Official OFAC dataset]({source.get('url', 'https://sanctionslistservice.ofac.treas.gov/')})"
                        )

                        with st.expander("Source provenance and checksum"):
                            st.json(source)

            else:
                st.success(
                    "No exact match found in the active OFAC Bitcoin address snapshot."
                )

            st.caption(sanctions_result.get("investigation_note", ""))

            st.info(
                "Screening limitation: absence from this snapshot does not establish "
                "that an address or transaction is safe. An exact match does not prove "
                "address ownership, control, or criminal activity."
            )

    st.divider()
    st.caption(
        "FraudShield AI | Bitcoin investigation prototype | "
        "Public blockchain records do not independently establish identity or criminal activity."
    )


with intelligence_col:
    render_intelligence_rail()

