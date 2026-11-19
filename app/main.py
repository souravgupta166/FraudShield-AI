import html
import os
from datetime import datetime, timezone

import httpx
import streamlit as st
import streamlit.components.v1 as components

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
USER_NAME = os.getenv("FRAUDSHIELD_USER", "Sourav")
DEMO_TXID = "64a24d399c4302373531a40bbd87fa9d1b4dc0d4699b573cbd43a9269a00a87e"

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
:root{--bg:#0c0e11;--panel:#16191e;--panel2:#1c2027;--line:#272c34;--text:#f2f4f7;--muted:#8e97a3;
--mint:#2ee6c1;--purple:#7b4cf0;--blue:#2f86c9;--orange:#f7931a;--red:#ff6b78;--green:#3ddc97}
html,body,[class*="css"]{font-family:'Manrope',sans-serif}
.stApp{background:radial-gradient(ellipse at 8% -8%,rgba(46,230,193,.10),transparent 32%),radial-gradient(ellipse at 95% 0%,rgba(123,76,240,.10),transparent 30%),var(--bg);color:var(--text)}
[data-testid="stHeader"]{background:transparent}
.block-container{max-width:1560px;padding-top:1.2rem;padding-bottom:4rem}
h1,h2,h3,h4{color:var(--text)!important;letter-spacing:-.03em;font-weight:800!important}
p,li,label,[data-testid="stMarkdownContainer"]{color:#d3d9e0}
[data-testid="stCaptionContainer"],small{color:var(--muted)!important}
code,pre,[data-testid="stCode"]{font-family:'DM Mono',monospace!important}
hr{border-color:var(--line)!important}

/* sidebar */
[data-testid="stSidebar"]{background:#0f1215;border-right:1px solid var(--line)}
.fs-brand{display:flex;align-items:center;gap:12px;padding:6px 0 18px}
.fs-logo{width:42px;height:42px;border-radius:50%;background:linear-gradient(135deg,var(--blue),#1c5e96);display:grid;place-items:center;color:#fff;font-size:20px;box-shadow:0 0 0 4px rgba(47,134,201,.15)}
.fs-brand b{display:block;font-size:17px;color:var(--text);letter-spacing:-.02em}
.fs-brand span{font-size:12px;color:var(--muted)}
[data-testid="stSidebar"] [role="radiogroup"]{gap:6px}
[data-testid="stSidebar"] [role="radiogroup"] label{background:transparent;border:1px solid transparent;border-radius:12px;padding:11px 14px;width:100%;transition:background .15s}
[data-testid="stSidebar"] [role="radiogroup"] label>div:first-child{display:none}
[data-testid="stSidebar"] [role="radiogroup"] label:hover{background:var(--panel)}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked){background:rgba(46,230,193,.10);border-color:rgba(46,230,193,.35)}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p{color:var(--mint)!important;font-weight:700}
.fs-live{display:inline-flex;align-items:center;gap:8px;padding:7px 12px;border-radius:999px;background:rgba(46,230,193,.09);color:var(--mint);font-size:12px;font-weight:700}
.fs-live i{width:7px;height:7px;border-radius:50%;background:var(--mint);box-shadow:0 0 8px var(--mint)}

/* top bar */
.fs-top{display:flex;align-items:center;gap:16px}
.fs-avatar{width:54px;height:54px;border-radius:50%;background:linear-gradient(135deg,var(--mint),var(--blue));display:grid;place-items:center;font-weight:800;font-size:22px;color:#06201b}
.fs-hi{font-size:clamp(1.5rem,2.6vw,2.1rem);font-weight:800;letter-spacing:-.04em;color:var(--text)}
.fs-sub{color:var(--muted);font-size:13.5px;margin-top:2px}
.fs-clock-label{text-align:right;color:var(--muted);font-size:11px;font-weight:600;padding-top:6px}

/* cards */
.fs-stat{display:flex;align-items:center;gap:15px;background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:18px;min-height:104px}
.fs-ico{width:50px;height:50px;border-radius:14px;display:grid;place-items:center;font-size:21px;flex:none;color:#06201b}
.fs-ico.mint{background:var(--mint)}.fs-ico.purple{background:var(--purple);color:#fff}.fs-ico.blue{background:var(--blue);color:#fff}.fs-ico.teal{background:#25c7d9}.fs-ico.orange{background:var(--orange)}
.fs-sl{color:var(--muted);font-size:12.5px;font-weight:600}
.fs-sv{font-size:25px;font-weight:800;letter-spacing:-.04em;font-variant-numeric:tabular-nums;color:var(--text);line-height:1.2}
.fs-sn{font-size:11.5px;color:var(--muted);margin-top:1px}
.fs-sn.bad{color:var(--red)}.fs-sn.ok{color:var(--green)}
.fs-card{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:20px;margin-bottom:14px}
.fs-ct{font-weight:800;font-size:15px;color:var(--text);margin-bottom:14px;letter-spacing:-.02em}
.fs-bar{margin-bottom:13px}
.fs-bl{display:flex;justify-content:space-between;font-size:12.5px;color:var(--muted);margin-bottom:6px}
.fs-bl b{color:var(--text);font-variant-numeric:tabular-nums}
.fs-track{height:9px;border-radius:99px;background:#0e1115;overflow:hidden}
.fs-track i{display:block;height:100%;border-radius:99px}
.fs-track i.mint{background:linear-gradient(90deg,#1fb89b,var(--mint))}.fs-track i.orange{background:linear-gradient(90deg,#d97a0b,var(--orange))}
.fs-track i.purple{background:linear-gradient(90deg,#5a33c4,var(--purple))}.fs-track i.red{background:var(--red)}.fs-track i.blue{background:var(--blue)}
.fs-row{display:flex;align-items:center;gap:14px;padding:13px 4px;border-bottom:1px solid var(--line)}
.fs-row:last-child{border-bottom:0}
.fs-rico{width:36px;height:36px;border-radius:11px;background:var(--panel2);display:grid;place-items:center;color:var(--mint);flex:none}
.fs-rmain{flex:1;min-width:0}.fs-rmain b{display:block;font-size:13.5px;color:var(--text)}.fs-rmain small{font-size:11.5px}
.fs-pill{font-size:11px;font-weight:700;padding:4px 10px;border-radius:99px;background:rgba(61,220,151,.12);color:var(--green)}
.fs-pill.bad{background:rgba(255,107,120,.12);color:var(--red)}.fs-pill.warn{background:rgba(247,147,26,.14);color:var(--orange)}
.fs-amt{font-weight:800;font-variant-numeric:tabular-nums;min-width:84px;text-align:right;color:var(--mint);font-size:13.5px}
.fs-chip{display:inline-flex;align-items:center;gap:8px;padding:7px 14px;border-radius:99px;font-size:12.5px;font-weight:700;margin:6px 0 16px}
.fs-chip.ok{background:rgba(61,220,151,.10);color:var(--green)}.fs-chip.warn{background:rgba(247,147,26,.12);color:var(--orange)}
.fs-h{font-size:1.45rem;font-weight:800;letter-spacing:-.04em;color:var(--text);margin:8px 0 2px}
.fs-help{border:1px dashed #36505a;border-radius:16px;padding:14px 18px;background:rgba(46,230,193,.04);margin:10px 0 14px}
.fs-help strong{color:var(--text)}
.fs-mini{background:var(--panel2);border:1px solid var(--line);border-radius:16px;padding:14px;margin-bottom:10px}
.fs-mini .l{font-size:11.5px;color:var(--muted);font-weight:600;display:flex;justify-content:space-between}
.fs-mini .v{font-size:20px;font-weight:800;color:var(--text);font-variant-numeric:tabular-nums;margin:4px 0 8px}
.fs-portfolio{background:linear-gradient(145deg,#1d2229,#12161b);border:1px solid #2d343d;border-radius:20px;padding:20px;margin-bottom:16px}
.fs-portfolio .big{font-size:32px;font-weight:800;letter-spacing:-.05em;color:var(--text);font-variant-numeric:tabular-nums;margin:6px 0 12px}
.fs-foot{margin-top:18px;padding-top:12px;border-top:1px solid var(--line);color:#7d8793;font-size:11px;line-height:1.7}

/* streamlit widgets */
div[data-testid="stMetric"]{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:15px 17px}
[data-testid="stMetricLabel"]{color:var(--muted)!important;font-size:.76rem;font-weight:600}
[data-testid="stMetricValue"]{color:var(--text)!important;font-weight:800;letter-spacing:-.04em;font-variant-numeric:tabular-nums}
div[data-testid="stForm"],div[data-testid="stExpander"],div[data-testid="stDataFrame"],div[data-testid="stVerticalBlockBorderWrapper"]:has(>div>[data-testid="stVerticalBlock"] .fs-ev){border:1px solid var(--line);border-radius:16px;background:var(--panel)}
div[data-testid="stForm"]{padding:1.1rem 1.2rem}
.stTextInput input,.stTextArea textarea{background:#0e1115!important;color:var(--text)!important;border:1px solid #333a44!important;border-radius:12px!important;font-family:'DM Mono',monospace!important}
.stTextInput input:focus{border-color:var(--mint)!important;box-shadow:0 0 0 1px var(--mint)!important}
.stButton button,[data-testid="stFormSubmitButton"] button{border-radius:12px;border:0;background:var(--mint);color:#06201b!important;font-weight:800;transition:transform .15s,box-shadow .15s}
.stButton button:hover,[data-testid="stFormSubmitButton"] button:hover{transform:translateY(-1px);box-shadow:0 8px 24px rgba(46,230,193,.25);background:#5cf0d3}
.stButton button p,[data-testid="stFormSubmitButton"] button p{color:#06201b!important}
[data-testid="stTabs"] button{color:var(--muted)!important;font-weight:700}
[data-testid="stTabs"] button[aria-selected="true"]{color:var(--mint)!important}
[data-testid="stTabs"] [data-baseweb="tab-highlight"]{background:var(--mint)!important}
[data-testid="stAlert"]{border-radius:14px;border:1px solid var(--line)}
[data-testid="stCode"] pre{background:#0e1115!important;border:1px solid var(--line);border-radius:12px}
@media(max-width:800px){.block-container{padding-left:1rem;padding-right:1rem}.fs-sv{font-size:21px}}
@media(prefers-reduced-motion:reduce){*{transition:none!important}}
</style>
""",
    unsafe_allow_html=True,
)


# ---------- helpers ----------
def esc(value):
    return html.escape(str(value)) if value is not None else ""


def stat(icon, tone, label, value, note="", note_tone=""):
    note_html = f'<div class="fs-sn {note_tone}">{note}</div>' if note else ""
    return (
        f'<div class="fs-stat"><div class="fs-ico {tone}">{icon}</div>'
        f'<div><div class="fs-sl">{label}</div><div class="fs-sv">{value}</div>{note_html}</div></div>'
    )


def bars(title, rows):
    top = max([v for _, v, _ in rows] + [1])
    body = "".join(
        f'<div class="fs-bar"><div class="fs-bl"><span>{label}</span><b>{value:,}</b></div>'
        f'<div class="fs-track"><i class="{tone}" style="width:{max(value / top * 100, 3 if value else 0):.0f}%"></i></div></div>'
        for label, value, tone in rows
    )
    return f'<div class="fs-card"><div class="fs-ct">{title}</div>{body}</div>'


def fmt(n):
    return f"{n:,}" if isinstance(n, int) else "Unavailable"


@st.cache_data(ttl=30, show_spinner=False)
def get_monitor():
    try:
        r = httpx.get(f"{API_BASE_URL}/api/v1/bitcoin/ingestion/monitor", timeout=15.0)
        r.raise_for_status()
        return r.json()
    except (httpx.HTTPError, ValueError):
        return None


def render_match(match):
    st.markdown(f"**{match.get('entity_name', 'Unknown entity')}**")
    st.write(
        {
            "Entity ID": match.get("entity_id"),
            "Entity type": match.get("entity_type"),
            "OFAC feature record ID": match.get("source_record_id"),
            "Sanctions programmes": match.get("sanctions_programmes", []),
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
        st.markdown(f"[Official sanctions dataset]({source.get('url') or 'https://sanctionslistservice.ofac.treas.gov/'})")


# ---------- sidebar ----------
PAGES = {"Network Monitoring": "◈  Network monitoring", "Investigations": "⌕  Investigations"}
with st.sidebar:
    st.markdown(
        '<div class="fs-brand"><div class="fs-logo">🛡</div><div><b>FraudShield AI</b><span>Bitcoin intelligence</span></div></div>',
        unsafe_allow_html=True,
    )
    active_page = st.radio(
        "Workspace",
        list(PAGES),
        format_func=PAGES.get,
        label_visibility="collapsed",
        key="fraudshield_active_page",
    )
    st.divider()
    st.caption("Network · Bitcoin mainnet")
    st.caption("Evidence · Public blockchain records")
    st.caption("API · FastAPI  |  Storage · PostgreSQL")
    st.caption("Build 0.1.0")
    st.markdown('<span class="fs-live"><i></i>Live monitoring on</span>', unsafe_allow_html=True)


# ---------- top bar ----------
top_left, top_right = st.columns([3, 1.2])
with top_left:
    st.markdown(
        f'<div class="fs-top"><div class="fs-avatar">{esc(USER_NAME[:1].upper())}</div>'
        f'<div><div class="fs-hi">Hi {esc(USER_NAME)} 👋</div>'
        f'<div class="fs-sub">Monitor the Bitcoin pipeline, investigate transactions and review sanctions evidence.</div></div></div>',
        unsafe_allow_html=True,
    )
with top_right:
    st.markdown('<div class="fs-clock-label">Local time</div>', unsafe_allow_html=True)
    components.html(
        """<div id="c" style="text-align:right;font:800 24px Manrope,sans-serif;color:#f2f4f7;letter-spacing:-.03em;font-variant-numeric:tabular-nums">--:--:--</div>
        <script>const f=()=>document.getElementById('c').textContent=new Date().toLocaleTimeString([],{hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false});f();setInterval(f,1000)</script>""",
        height=44,
    )
st.write("")


# ---------- network monitoring ----------
@st.fragment(run_every="60s")
def render_monitor():
    st.markdown(
        '<div class="fs-h">Network operations</div><div class="fs-sub">Health, coverage and freshness of the Bitcoin data FraudShield collects.</div>',
        unsafe_allow_html=True,
    )
    data = get_monitor()
    if data is None:
        st.error("Unable to load ingestion monitoring data. Check that the API is running at " + API_BASE_URL)
        return

    ing = data.get("ingestion_runs", {})
    chain = data.get("blockchain_data", {})
    latest = data.get("latest_ingestion") or {}
    tx = chain.get("transactions_by_status", {})
    status = str(data.get("status", "unknown")).upper()
    ok = status == "OPERATIONAL"

    st.markdown(
        f'<span class="fs-chip {"ok" if ok else "warn"}">● Ingestion service {esc(status)}</span>',
        unsafe_allow_html=True,
    )
    failed = ing.get("failed", 0)
    cards = [
        ("⛓", "mint", "Latest stored block", fmt(chain.get("latest_block_height")), "", ""),
        ("▦", "purple", "Canonical blocks", fmt(chain.get("canonical_blocks_stored", 0)), "", ""),
        ("⇄", "blue", "Stored transactions", fmt(chain.get("total_stored_transactions", 0)), "", ""),
        ("✓", "teal", "Completed runs", fmt(ing.get("completed", 0)), f"{failed} failed", "bad" if failed else "ok"),
    ]
    for col, (icon, tone, label, value, note, nt) in zip(st.columns(4), cards):
        col.markdown(stat(icon, tone, label, value, note, nt), unsafe_allow_html=True)
    st.write("")

    left, right = st.columns(2)
    left.markdown(
        bars(
            "Stored transactions",
            [
                ("Confirmed", tx.get("confirmed", 0), "mint"),
                ("Mempool", tx.get("mempool", 0), "orange"),
                ("Orphaned", tx.get("orphaned", 0), "purple"),
            ],
        ),
        unsafe_allow_html=True,
    )
    right.markdown(
        bars(
            f"Ingestion runs · {ing.get('total', 0):,} total",
            [
                ("Completed", ing.get("completed", 0), "mint"),
                ("Running", ing.get("running", 0), "blue"),
                ("Failed", failed, "red"),
            ],
        ),
        unsafe_allow_html=True,
    )

    # freshness
    stamp = latest.get("finished_at") or latest.get("started_at")
    if stamp:
        try:
            ts = datetime.fromisoformat(stamp)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            age = max(0, int((datetime.now(timezone.utc) - ts).total_seconds()))
            if age < 60:
                label = f"{age} seconds ago"
            elif age < 3600:
                label = f"{age // 60} minutes ago"
            elif age < 86400:
                label = f"{age // 3600} hours ago"
            else:
                label = f"{age // 86400} days ago"
            c1, c2 = st.columns(2)
            c1.markdown(stat("◷", "orange", "Last recorded run", label), unsafe_allow_html=True)
            c2.markdown(stat("●", "mint", "Latest run status", esc(str(latest.get("status", "Unknown")).upper())), unsafe_allow_html=True)
            st.caption("Latest recorded completion: " + ts.strftime("%Y-%m-%d %H:%M:%S UTC"))
            if age > 86400:
                st.warning("No ingestion recorded in the last 24 hours. The stored dataset may be stale.")
            else:
                st.info("Freshness is measured from the latest recorded run. It does not verify the current Bitcoin network tip.")
        except ValueError:
            st.info("The latest ingestion timestamp could not be read.")
    else:
        st.info("No ingestion runs have been recorded yet.")

    # history
    runs = data.get("recent_runs", [])
    st.write("")
    if runs:
        rows = ""
        for run in runs:
            s = str(run.get("status", "unknown")).lower()
            cls = "" if s in ("completed", "success") else ("bad" if s == "failed" else "warn")
            err = f' · {esc(run.get("error_message"))}' if run.get("error_message") else ""
            rows += (
                f'<div class="fs-row"><div class="fs-rico">⇄</div>'
                f'<div class="fs-rmain"><b>{esc(run.get("source") or "Bitcoin ingestion")}</b>'
                f'<small>{esc(run.get("started_at"))}{err}</small></div>'
                f'<span class="fs-pill {cls}">{esc(s.upper())}</span>'
                f'<div class="fs-amt">{run.get("transactions_processed", 0):,} tx</div></div>'
            )
        st.markdown(f'<div class="fs-card"><div class="fs-ct">Recent ingestion activity</div>{rows}</div>', unsafe_allow_html=True)
    else:
        st.info("No ingestion activity has been recorded yet.")


# ---------- investigations ----------
def render_transaction_tab():
    st.markdown(
        '<div class="fs-help"><strong>Try a live investigation</strong><br>'
        '<span style="color:#8e97a3">Paste a Bitcoin transaction ID, or load the verified example stored in this demo.</span></div>',
        unsafe_allow_html=True,
    )

    def load_demo():
        st.session_state["transaction_txid_input"] = DEMO_TXID

    b, n = st.columns([1, 3])
    b.button("Load example", key="load_demo_transaction", on_click=load_demo, use_container_width=True)
    n.caption("Example transaction · confirmed on Bitcoin mainnet")

    with st.form("transaction_search"):
        txid = st.text_input(
            "Bitcoin transaction ID",
            placeholder="Paste a 64-character transaction ID",
            max_chars=64,
            key="transaction_txid_input",
            help="A transaction ID is a 64-character hexadecimal identifier.",
        ).strip().lower()
        submitted = st.form_submit_button("Investigate transaction", use_container_width=True)

    if submitted:
        if len(txid) != 64 or any(c not in "0123456789abcdef" for c in txid):
            st.error("Enter a valid 64-character hexadecimal transaction ID.")
        else:
            with st.spinner("Retrieving transaction evidence..."):
                try:
                    r = httpx.get(f"{API_BASE_URL}/api/v1/bitcoin/transactions/{txid}/investigation", timeout=30.0)
                    if r.status_code == 404:
                        st.error("Transaction not found in the FraudShield database.")
                    elif r.status_code != 200:
                        st.error(f"Investigation request failed: HTTP {r.status_code}")
                        st.code(r.text[:1500])
                    else:
                        st.session_state["investigation_result"] = r.json()
                        st.session_state["investigation_txid"] = txid
                except httpx.RequestError as exc:
                    st.error(f"Could not connect to the FraudShield API: {exc}")

    result = st.session_state.get("investigation_result")
    if not result:
        st.info("Enter a Bitcoin transaction ID above to begin an investigation.")
        c1, c2, c3 = st.columns(3)
        c1.markdown(stat("⇄", "mint", "Transaction analysis", "Inputs & outputs", "Fees and value reconciliation"), unsafe_allow_html=True)
        c2.markdown(stat("⚑", "orange", "Risk indicators", "Explainable", "Transaction-level findings"), unsafe_allow_html=True)
        c3.markdown(stat("◎", "purple", "UTXO graph", "Connected", "Observed transactions and addresses"), unsafe_allow_html=True)
        return

    record = result.get("transaction_record", {})
    transaction = record.get("transaction", {})
    block = record.get("block") or {}
    summary = record.get("summary", {})
    features = result.get("features", {})
    graph = result.get("graph_context", {})
    findings = result.get("transaction_findings", [])
    activity = result.get("address_activity", [])
    sanctions = result.get("address_sanctions_screening", {})

    st.divider()
    st.subheader("Investigation overview")
    st.code(st.session_state.get("investigation_txid", ""), language=None)
    fee = transaction.get("fee_sats")
    rate = features.get("fee_rate_sat_vb")
    c = st.columns(4)
    c[0].metric("Transaction status", str(transaction.get("status", "Unknown")).upper())
    c[1].metric("Block height", str(block.get("height", "Unconfirmed")))
    c[2].metric("Transaction fee", f"{fee:,} sats" if isinstance(fee, int) else "Unavailable")
    c[3].metric("Fee rate", f"{rate:.2f} sat/vB" if isinstance(rate, (int, float)) else "Unavailable")

    st.subheader("Evidence timeline")
    events = []
    if block.get("time"):
        events.append((block["time"], "Bitcoin block confirmation",
                       f"Included in block {block.get('height', 'Unknown')} ({block.get('hash', 'hash unavailable')})."))
    if transaction.get("first_seen_at"):
        events.append((transaction["first_seen_at"], "Transaction first observed",
                       "FraudShield recorded this transaction in its local dataset."))
    if events:
        for ts, name, desc in sorted(events, key=lambda e: e[0]):
            with st.container(border=True):
                st.markdown(f"**{name}**")
                st.caption(f"Timestamp: {ts}")
                st.write(desc)
    else:
        st.info("No timestamped transaction events are available.")
    st.caption("Block time comes from the Bitcoin block. First observed is the local recording time, not necessarily the broadcast time.")

    c = st.columns(3)
    c[0].metric("Triggered indicators", len(findings))
    c[1].metric("Connected transactions", len(graph.get("connected_transaction_ids", [])))
    c[2].metric("OFAC address matches", sanctions.get("matched_address_count", 0))

    st.subheader("Transaction structure")
    c = st.columns(5)
    c[0].metric("Inputs", summary.get("input_count", "—"))
    c[1].metric("Outputs", summary.get("output_count", "—"))
    c[2].metric("Accounting complete", "Yes" if summary.get("accounting_complete") else "No")
    c[3].metric("Known input (sats)", fmt(summary.get("known_input_total_sats")))
    c[4].metric("Total output (sats)", fmt(summary.get("total_output_sats")))

    st.subheader("Explainable risk indicators")
    if findings:
        for f in findings:
            msg = f"**{f.get('indicator', 'Finding')}** — {f.get('description') or f.get('indicator', 'Finding')}"
            {"high": st.error, "warning": st.warning}.get(f.get("severity"), st.info)(msg)
            with st.expander("View finding evidence"):
                st.json(f)
    else:
        st.success("No configured transaction indicators were triggered.")
    st.caption("No triggered indicator does not mean a transaction is safe. Indicators are investigative signals, not proof of fraud.")

    st.subheader("Observed graph context")
    c = st.columns(4)
    c[0].metric("Stored transactions", graph.get("stored_transaction_count", "—"))
    c[1].metric("Input outpoints", graph.get("input_outpoint_count", "—"))
    c[2].metric("Output outpoints", graph.get("output_outpoint_count", "—"))
    c[3].metric("External inputs", graph.get("external_input_outpoint_count", "—"))
    st.caption(f"Graph scope: {graph.get('dataset_scope', 'Unavailable')}")
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
    if activity:
        st.dataframe(activity, use_container_width=True, hide_index=True)
    else:
        st.info("No address activity records were returned.")

    st.subheader("Automatic OFAC sanctions screening")
    matched = sanctions.get("matched_address_count", 0)
    c = st.columns(2)
    c[0].metric("Addresses screened", sanctions.get("screened_address_count", 0))
    c[1].metric("Exact OFAC address matches", matched)
    items = sanctions.get("results", [])
    if items:
        st.dataframe(
            [
                {
                    "Bitcoin address": i.get("address", ""),
                    "Transaction role": ", ".join(i.get("transaction_roles", [])),
                    "Screening status": i.get("screening", {}).get("match_status", "unknown").replace("_", " ").upper(),
                    "Matching records": i.get("screening", {}).get("match_count", 0),
                }
                for i in items
            ],
            use_container_width=True,
            hide_index=True,
        )
        if matched:
            st.warning("One or more addresses exactly match the active OFAC snapshot. This is an investigative lead, not proof of ownership, control or illicit activity.")
        else:
            st.success("No exact address matches were found in the active OFAC snapshot.")
        for i in items:
            matches = i.get("screening", {}).get("matches", [])
            if matches:
                with st.expander(f"OFAC evidence — {i.get('address', 'Unknown')} ({', '.join(i.get('transaction_roles', []))})"):
                    for idx, m in enumerate(matches):
                        render_match(m)
                        if idx < len(matches) - 1:
                            st.divider()
    else:
        st.info("No address screening results were returned.")
    st.caption(sanctions.get("screening_note", "Screening is limited to addresses in the stored transaction graph and the active OFAC snapshot."))

    with st.expander("Raw transaction inputs and outputs"):
        st.markdown("**Inputs**")
        st.json(record.get("inputs", []))
        st.markdown("**Outputs**")
        st.json(record.get("outputs", []))
    with st.expander("Full investigation response"):
        st.json(result)
    st.caption(result.get("investigation_note", ""))


def render_sanctions_tab():
    st.markdown(
        '<div class="fs-help"><strong>Address screening</strong><br>'
        '<span style="color:#8e97a3">Check a Bitcoin address against the active official OFAC snapshot. Exact matches are leads, not proof of wrongdoing.</span></div>',
        unsafe_allow_html=True,
    )
    with st.form("sanctions_screening"):
        address = st.text_input("Bitcoin address", placeholder="Enter a Bitcoin address", max_chars=90).strip()
        go = st.form_submit_button("Screen address", use_container_width=True)

    if go:
        if not 14 <= len(address) <= 90 or not address.isalnum():
            st.error("Enter a valid-looking alphanumeric Bitcoin address.")
        else:
            with st.spinner("Checking the active OFAC sanctions snapshot..."):
                try:
                    r = httpx.get(f"{API_BASE_URL}/api/v1/bitcoin/addresses/{address}/sanctions-screening", timeout=30.0)
                    if r.status_code != 200:
                        st.error(f"Sanctions screening failed: HTTP {r.status_code}")
                        st.code(r.text[:1500])
                    else:
                        st.session_state["sanctions_result"] = r.json()
                        st.session_state["sanctions_address"] = address
                except httpx.RequestError as exc:
                    st.error(f"Could not connect to the FraudShield API: {exc}")

    res = st.session_state.get("sanctions_result")
    if not res:
        return
    st.markdown("#### Screening result")
    st.code(st.session_state.get("sanctions_address", ""), language=None)
    c = st.columns(2)
    c[0].metric("Screening status", res.get("match_status", "Unknown").replace("_", " ").upper())
    c[1].metric("Matching OFAC records", res.get("match_count", 0))
    if res.get("is_sanctioned_address_match"):
        st.warning("Exact address match found in the active OFAC snapshot. Review every source record before drawing conclusions.")
        for idx, m in enumerate(res.get("matches", []), start=1):
            with st.expander(f"OFAC record {idx}: {m.get('entity_name', 'Unknown entity')} | Entity ID: {m.get('entity_id', 'Unavailable')}", expanded=True):
                render_match(m)
    else:
        st.success("No exact match found in the active OFAC Bitcoin address snapshot.")
    st.caption(res.get("investigation_note", ""))
    st.info("Absence from this snapshot does not establish that an address is safe. An exact match does not prove ownership, control or criminal activity.")


def render_investigations():
    st.markdown(
        '<div class="fs-h">Investigations</div><div class="fs-sub">Transaction analysis, explainable risk indicators and sanctions evidence in one place.</div>',
        unsafe_allow_html=True,
    )
    tx_tab, addr_tab = st.tabs(["Transaction investigation", "Address sanctions screening"])
    with tx_tab:
        render_transaction_tab()
    with addr_tab:
        render_sanctions_tab()


# ---------- right rail ----------
@st.fragment(run_every="60s")
def render_rail():
    st.markdown('<div class="fs-ct" style="font-size:18px">Network intelligence</div>', unsafe_allow_html=True)
    data = get_monitor()
    if data is None:
        st.markdown(
            '<div class="fs-portfolio"><div class="fs-sl">Pipeline status</div><div class="fs-sv" style="color:#ff6b78">● Unavailable</div>'
            '<div class="fs-sn">Could not retrieve live API metrics.</div></div>',
            unsafe_allow_html=True,
        )
    else:
        chain = data.get("blockchain_data", {})
        ing = data.get("ingestion_runs", {})
        tx = chain.get("transactions_by_status", {})
        status = str(data.get("status", "unknown")).upper()
        ok = status == "OPERATIONAL"
        height = chain.get("latest_block_height")
        st.markdown(
            f'<div class="fs-portfolio"><div class="fs-sl">Latest block</div>'
            f'<div class="big">{f"{height:,}" if height is not None else "—"}</div>'
            f'<span class="fs-chip {"ok" if ok else "warn"}" style="margin:0">● {esc(status)}</span>'
            f'<div class="fs-sn" style="margin-top:12px">{chain.get("total_stored_transactions", 0):,} transactions stored · '
            f'{ing.get("completed", 0):,} runs completed</div></div>',
            unsafe_allow_html=True,
        )
        total = max(sum(tx.get(k, 0) for k in ("confirmed", "mempool", "orphaned")), 1)
        st.markdown('<div class="fs-ct">Transaction pool</div>', unsafe_allow_html=True)
        for label, key, tone in (("Confirmed", "confirmed", "mint"), ("Mempool", "mempool", "orange"), ("Orphaned", "orphaned", "purple")):
            n = tx.get(key, 0)
            st.markdown(
                f'<div class="fs-mini"><div class="l"><span>{label}</span><span>{n / total:.0%}</span></div>'
                f'<div class="v">{n:,}</div><div class="fs-track"><i class="{tone}" style="width:{n / total * 100:.0f}%"></i></div></div>',
                unsafe_allow_html=True,
            )
        runs = data.get("recent_runs", [])[:3]
        if runs:
            rows = "".join(
                f'<div class="fs-row"><div class="fs-rico">⇄</div><div class="fs-rmain"><b>{esc(str(r.get("status", "unknown")).upper())}</b>'
                f'<small>{esc(r.get("source") or "Bitcoin ingestion")} · {r.get("transactions_processed", 0):,} tx</small></div></div>'
                for r in runs
            )
            st.markdown(f'<div class="fs-card" style="margin-top:16px"><div class="fs-ct">Recent events</div>{rows}</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="fs-foot">On-chain evidence only. Public blockchain records do not independently establish identity or criminal activity.</div>',
        unsafe_allow_html=True,
    )


# ---------- layout ----------
main_col, rail_col = st.columns([3.1, 1.1], gap="large")
with main_col:
    if active_page == "Network Monitoring":
        render_monitor()
    else:
        render_investigations()
    st.divider()
    st.caption("FraudShield AI | Bitcoin investigation prototype")
with rail_col:
    render_rail()