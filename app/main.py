import os
from datetime import datetime, timezone

import httpx
import streamlit as st
import streamlit.components.v1 as components


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")

st.set_page_config(
    page_title="FraudShield AI | Investigation",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');

    :root {
        --fs-bg: #080c12;
        --fs-panel: #101722;
        --fs-panel-2: #131e2b;
        --fs-line: rgba(145, 167, 190, .15);
        --fs-text: #eaf1f8;
        --fs-muted: #8292a6;
        --fs-orange: #ff9b45;
        --fs-cyan: #51d6d0;
        --fs-red: #ff657a;
    }

    html, body, [class*="css"] { font-family: 'Manrope', sans-serif; }
    .stApp {
        background:
            radial-gradient(ellipse at 12% 0%, rgba(34, 91, 112, .19), transparent 34%),
            radial-gradient(ellipse at 92% 8%, rgba(255, 132, 53, .10), transparent 27%),
            var(--fs-bg);
        color: var(--fs-text);
    }
    [data-testid="stHeader"] { background: rgba(8,12,18,.72); }
    [data-testid="stToolbar"] { right: 1rem; }
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 4rem;
        max-width: 1540px;
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1520 0%, #0a1018 100%);
        border-right: 1px solid var(--fs-line);
    }
    [data-testid="stSidebar"] > div { padding-top: 1.5rem; }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: #a7b5c6;
    }
    h1, h2, h3 { letter-spacing: -.045em; color: var(--fs-text); }
    h1 { font-weight: 800 !important; }
    h2, h3 { font-weight: 750 !important; }
    p, label, li { color: #b8c5d3; }
    small, [data-testid="stCaptionContainer"] { color: var(--fs-muted) !important; }
    code, .stCode, [data-testid="stCode"] {
        font-family: 'DM Mono', monospace !important;
    }
    div[data-testid="stMetric"] {
        background: linear-gradient(145deg, rgba(21,32,46,.96), rgba(13,21,31,.96));
        border: 1px solid var(--fs-line);
        border-radius: 15px;
        padding: 17px 19px;
        box-shadow: 0 12px 32px rgba(0,0,0,.16);
        min-height: 112px;
    }
    [data-testid="stMetricLabel"] { color: #91a2b6 !important; font-size: .78rem; font-weight: 700; }
    [data-testid="stMetricValue"] { color: #f4f8fc !important; font-weight: 800; letter-spacing: -.04em; }
    [data-testid="stMetricDelta"] { font-family: 'DM Mono', monospace; font-size: .75rem; }
    div[data-testid="stForm"], div[data-testid="stExpander"], div[data-testid="stDataFrame"] {
        border: 1px solid var(--fs-line);
        border-radius: 15px;
        background: rgba(15,23,34,.72);
    }
    div[data-testid="stForm"] { padding: 1.1rem 1.2rem; }
    div[data-testid="stExpander"] summary { color: #dce6f0; font-weight: 700; }
    .stTextInput input {
        background: #0b121c !important;
        color: #edf5fc !important;
        border: 1px solid #2a3a4d !important;
        border-radius: 10px !important;
        font-family: 'DM Mono', monospace !important;
    }
    .stTextInput input:focus {
        border-color: var(--fs-cyan) !important;
        box-shadow: 0 0 0 1px var(--fs-cyan) !important;
    }
    .stButton button, [data-testid="stFormSubmitButton"] button {
        border-radius: 10px;
        border: 1px solid rgba(255,155,69,.55);
        background: linear-gradient(110deg, #ff9b45, #ff713d);
        color: #111820;
        font-weight: 800;
        transition: transform .15s ease, box-shadow .15s ease;
    }
    .stButton button:hover, [data-testid="stFormSubmitButton"] button:hover {
        transform: translateY(-1px);
        box-shadow: 0 8px 24px rgba(255,132,61,.22);
        color: #101820;
        border-color: #ffb16f;
    }
    hr { border-color: var(--fs-line) !important; }
    [data-testid="stAlert"] { border-radius: 12px; border: 1px solid var(--fs-line); }
    [data-testid="stDataFrame"] { overflow: hidden; }
    .fs-eyebrow {
        color: var(--fs-cyan);
        font: 500 11px 'DM Mono', monospace;
        letter-spacing: .18em;
        text-transform: uppercase;
    }
    .fs-hero {
        position: relative;
        overflow: hidden;
        padding: 27px 30px 25px;
        margin: 4px 0 25px;
        border: 1px solid rgba(103,190,194,.23);
        border-radius: 20px;
        background:
            radial-gradient(circle at 84% 10%, rgba(255,155,69,.17), transparent 28%),
            linear-gradient(115deg, rgba(17,37,48,.98), rgba(14,22,33,.98) 58%, rgba(30,28,28,.92));
        box-shadow: 0 18px 55px rgba(0,0,0,.22);
    }
    .fs-hero h1 { margin: 7px 0 5px; font-size: clamp(1.8rem, 3vw, 2.65rem); }
    .fs-hero p { margin: 0; color: #9eafc0; max-width: 760px; }
    .fs-hero-tag {
        display: inline-block; margin-top: 17px; padding: 6px 10px;
        border-radius: 7px; border: 1px solid rgba(81,214,208,.25);
        color: #78e0d8; background: rgba(81,214,208,.07);
        font: 11px 'DM Mono', monospace; letter-spacing: .08em;
    }
    .fs-section-kicker {
        color: var(--fs-orange); font: 500 10px 'DM Mono', monospace;
        letter-spacing: .16em; text-transform: uppercase; margin-bottom: 3px;
    }
    .fs-mono { font-family: 'DM Mono', monospace; }
    [data-testid="stStatusWidget"] { border-radius: 9px; }
    @media (max-width: 800px) {
        .block-container { padding-left: 1rem; padding-right: 1rem; }
        .fs-hero { padding: 21px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="fs-hero">
      <div class="fs-eyebrow">Financial intelligence · Bitcoin network</div>
      <h1>FraudShield <span style="color:#ff9b45">/</span> AI</h1>
      <p>On-chain investigations, sanctions intelligence and explainable risk signals.
         Evidence first. Decisions with context.</p>
      <span class="fs-hero-tag">● SYSTEM ONLINE &nbsp; / &nbsp; BITCOIN MAINNET DATA</span>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown(
        """
        <div style="padding:4px 0 15px">
          <div style="font:500 10px 'DM Mono',monospace;letter-spacing:.18em;color:#51d6d0">FRAUDSHIELD / INTEL</div>
          <div style="font-size:22px;font-weight:800;letter-spacing:-1px;color:#edf4fa;margin-top:5px">Command Center</div>
          <div style="font:11px 'DM Mono',monospace;color:#8292a6;margin-top:4px">BUILD 0.1.0 · BTC MAINNET</div>
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
        '<span style="color:#51d6d0;font:11px \'DM Mono\',monospace">● LIVE MONITORING ENABLED</span>',
        unsafe_allow_html=True,
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
                    "Blocks": run.get("blocks_processed"),
                    "Transactions": run.get("transactions_processed"),
                    "Error": run.get("error_message") or "",
                }
                for run in recent_runs
            ]

            st.dataframe(
                display_runs,
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No recent ingestion activity is available.")

        st.caption(monitor_data.get("monitoring_note", ""))

        st.caption(
            "Skipped transaction counts are not currently persisted in the "
            "ingestion-run records and are therefore not included."
        )

    except httpx.RequestError as exc:
        st.error(f"Could not connect to the ingestion monitoring API: {exc}")
    except httpx.HTTPStatusError as exc:
        st.error(
            "Ingestion monitoring request failed: "
            f"HTTP {exc.response.status_code}"
        )
    except (KeyError, TypeError, ValueError) as exc:
        st.error(f"Could not interpret ingestion monitoring data: {exc}")


render_ingestion_monitor()

st.divider()

st.title("Transaction Investigation")
st.caption(
    "Inspect on-chain transaction details, explainable risk indicators "
    "and observed UTXO graph relationships."
)

with st.form("transaction_search"):
    txid = st.text_input(
        "Bitcoin transaction ID",
        placeholder="Enter a 64-character transaction ID",
        max_chars=64,
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

st.header("Bitcoin Address Sanctions Screening")
st.caption(
    "Screen a Bitcoin address against the active official OFAC sanctions snapshot."
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
