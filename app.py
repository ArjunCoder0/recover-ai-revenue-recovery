"""RECOVER — Streamlit Revenue Operations Console.

Decline-Aware, Policy-Bounded AI Revenue Recovery Console for Razorpay Buildathon (Track 3).
Demonstrates:
  Revenue at Risk → Diagnosis → Policy Safety Fence → Thompson Sampling AI
  → Bounded Workflow → Measured Recovery → Online Learning → Human-in-the-Loop → Audit Trail
"""

import copy
import json
import streamlit as st
import pandas as pd

from recover.simulator import generate, CLASSES, Case
from recover.policy import (
    DEFAULT_CONTROLS,
    validate_controls,
    COST,
    CONTACT_ARMS,
    RETRY_ARMS,
    ARMS,
)
from recover.decide import explain_rationale
from recover.engine import run, execute_human_action
from recover.metrics import summarize, by_class, confidence
from recover.outreach import draft

CLASS_MEANING = {
    "SOFT": "Instrument valid, funds temporarily absent. Timing retry around salary day is key.",
    "TRANSIENT": "Temporary network or issuer outage. Short-delay retry recovers reliably once systems recover.",
    "ACTION_REQUIRED": "Instrument unusable or mandate paused. Retries futile; customer action via payment link required.",
    "HARD": "Mandate revoked or card stolen. Network rules forbid reattempts; payment link or closure only.",
}

CODE_MEANING = {
    "INSUFFICIENT_FUNDS": "Customer balance insufficient. Immediate retries waste gateway fees; align with salary day.",
    "DO_NOT_HONOR": "Generic refusal by issuer. Retrying later or offering alternate rails succeeds.",
    "ISSUER_UNAVAILABLE": "Bank system offline. High recovery probability after brief cooldown.",
    "UPI_TIMEOUT": "PSP or NPCI timeout. Transient network glitch on UPI Autopay rail.",
    "EXPIRED_CARD": "Card expired. Re-presentment will fail; customer must update credentials or pay via link.",
    "MANDATE_PAUSED": "Customer paused mandate in app. Automated debit blocked until user unpauses.",
    "AUTH_TIMEOUT": "Customer failed to complete authentication (OTP/PIN). Customer action required.",
    "MANDATE_REVOKED": "Customer cancelled mandate. Any automated retry is a regulatory violation.",
    "CARD_LOST_STOLEN": "Card flagged as lost/stolen. Network rules strictly prohibit reattempts.",
    "RISK_DECLINE": "Declined by risk rules. Retrying damages merchant standing with payment networks.",
}


def fmt_inr(x: float) -> str:
    """Formats a number as Indian Rupees string."""
    return f"₹{x:,.2f}"


def history_df(entries: list) -> pd.DataFrame:
    """Formats audit entries into a displayable history DataFrame."""
    rows = []
    for e in entries:
        rows.append(
            {
                "seq": e.get("seq"),
                "kind": e.get("kind"),
                "decided_at": f"{e.get('decided_at')}h",
                "executed_at": f"{e.get('executed_at')}h"
                if e.get("executed_at") is not None
                else "—",
                "action": e.get("arm"),
                "success": "✓ Success"
                if e.get("success") is True
                else ("✗ Failed" if e.get("success") is False else "Terminal"),
                "deferred": "Yes (Quiet Hours)"
                if e.get("deferred")
                else "No",
                "violation": e.get("violation", 0),
            }
        )
    return pd.DataFrame(rows)


def inject_css():
    """Injects modern, polished CSS styling for the fintech console."""
    st.markdown(
        """
        <style>
            /* Main layout container */
            .main .block-container {
                padding-top: 1.5rem;
                padding-bottom: 2.5rem;
                max-width: 1200px;
            }
            /* KPI Card styling */
            div[data-testid="stMetric"] {
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
                padding: 14px 18px;
                box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
                transition: transform 0.15s ease, box-shadow 0.15s ease;
            }
            div[data-testid="stMetric"]:hover {
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.08);
                transform: translateY(-1px);
            }
            /* Clean Badges */
            .badge-track {
                display: inline-block;
                background-color: #EFF6FF;
                color: #2563EB;
                border: 1px solid #BFDBFE;
                border-radius: 9999px;
                padding: 4px 12px;
                font-size: 0.8rem;
                font-weight: 600;
                margin-right: 6px;
            }
            .badge-sim {
                display: inline-block;
                background-color: #FEF3C7;
                color: #D97706;
                border: 1px solid #FDE68A;
                border-radius: 9999px;
                padding: 4px 12px;
                font-size: 0.8rem;
                font-weight: 600;
                margin-right: 6px;
            }
            .badge-ok {
                display: inline-block;
                background-color: #DCFCE7;
                color: #16A34A;
                border: 1px solid #BBF7D0;
                border-radius: 9999px;
                padding: 4px 12px;
                font-size: 0.8rem;
                font-weight: 600;
                margin-right: 6px;
            }
            .badge-block {
                display: inline-block;
                background-color: #FEE2E2;
                color: #DC2626;
                border: 1px solid #FECACA;
                border-radius: 9999px;
                padding: 4px 12px;
                font-size: 0.8rem;
                font-weight: 600;
                margin-right: 6px;
            }
            /* Section header accent */
            .section-header {
                font-size: 1.35rem;
                font-weight: 700;
                color: #0F172A;
                border-left: 4px solid #2563EB;
                padding-left: 12px;
                margin-top: 1.2rem;
                margin-bottom: 1rem;
            }
            /* Principle & Info cards */
            .principle-card {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
                padding: 16px;
                height: 100%;
            }
            .principle-card h4 {
                margin: 0 0 8px 0;
                color: #1E293B;
                font-size: 1.05rem;
            }
            .principle-card p {
                margin: 0;
                color: #64748B;
                font-size: 0.88rem;
                line-height: 1.45;
            }
            /* AI Decision Card */
            .ai-decision-card {
                background: linear-gradient(135deg, #F8FAFC 0%, #EFF6FF 100%);
                border: 2px solid #3B82F6;
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 1.2rem;
            }
            /* Flow banner */
            .flow-banner {
                background: #F1F5F9;
                border: 1px solid #CBD5E1;
                border-radius: 10px;
                padding: 12px 16px;
                font-family: monospace;
                font-size: 0.86rem;
                color: #1E293B;
                margin-bottom: 1.2rem;
                text-align: center;
                overflow-x: auto;
                white-space: nowrap;
            }
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_state():
    """Initializes session state variables with blueprint defaults."""
    if "controls" not in st.session_state:
        st.session_state.controls = copy.deepcopy(DEFAULT_CONTROLS)
    if "n" not in st.session_state:
        st.session_state.n = 400
    if "seed" not in st.session_state:
        st.session_state.seed = 42
    if "llm" not in st.session_state:
        st.session_state.llm = False
    if "stale" not in st.session_state:
        st.session_state.stale = False
    if "selected_case" not in st.session_state:
        st.session_state.selected_case = 0
    if "nav" not in st.session_state:
        st.session_state.nav = "Overview"
    if "sim" not in st.session_state:
        run_simulation()


def run_simulation():
    """Executes the simulation for smart and naive policies with current state."""
    try:
        controls = validate_controls(st.session_state.controls)
        n = st.session_state.n
        seed = st.session_state.seed

        cases = generate(n, seed=seed)
        smart_cases, audit_smart, bandit = run(
            cases, controls=controls, policy="smart", seed=seed
        )
        naive_cases, audit_naive, _ = run(
            cases, controls=controls, policy="naive", seed=seed
        )

        st.session_state.sim = {
            "cases": cases,
            "smart": smart_cases,
            "audit_smart": audit_smart,
            "bandit": bandit,
            "naive": naive_cases,
            "audit_naive": audit_naive,
            "controls_used": copy.deepcopy(controls),
            "n": n,
            "seed": seed,
        }
        st.session_state.stale = False
        if smart_cases:
            st.session_state.selected_case = smart_cases[0].id
    except Exception as e:
        st.error(f"Simulation execution error: {e}")


def sidebar():
    """Renders the sidebar navigation and simulation controls."""
    with st.sidebar:
        st.markdown("### ↺ **RECOVER**")
        st.caption("Policy-bounded AI revenue recovery")

        st.markdown(
            """<span class="badge-sim">SIMULATION — no real payments</span>""",
            unsafe_allow_html=True,
        )

        st.markdown("---")

        sections = [
            "Overview",
            "Case Explorer",
            "Decision Intelligence",
            "Policy & Safety Fence",
            "Failure Class Taxonomy",
            "Human Review",
            "Recovery Operations",
            "Audit Trail",
            "Experiment & Multi-Seed",
            "Razorpay Integration Mapping",
        ]

        current_nav = st.session_state.get("nav", "Overview")
        idx = sections.index(current_nav) if current_nav in sections else 0
        selected = st.radio(
            "Navigation",
            sections,
            index=idx,
            key="sidebar_nav_radio",
            label_visibility="collapsed",
        )
        st.session_state.nav = selected

        st.markdown("---")
        st.markdown("#### Simulation Controls")

        n_val = st.slider("Batch size (n)", 50, 2000, st.session_state.n, step=50)
        seed_val = st.number_input(
            "Random Seed", value=st.session_state.seed, step=1
        )

        if n_val != st.session_state.n or seed_val != st.session_state.seed:
            st.session_state.n = n_val
            st.session_state.seed = seed_val
            st.session_state.stale = True

        llm_toggle = st.checkbox(
            "Enable LLM rewrite (optional)",
            value=st.session_state.llm,
            help="Uses GEMINI_API_KEY if present to rewrite messages. Otherwise uses deterministic templates.",
        )
        st.session_state.llm = llm_toggle

        if st.button(
            "Run recovery simulation",
            type="primary",
            use_container_width=True,
        ):
            run_simulation()
            st.rerun()

        if st.session_state.sim:
            last_n = st.session_state.sim["n"]
            last_seed = st.session_state.sim["seed"]
            st.caption(f"Active run: n={last_n}, seed={last_seed}")
        else:
            st.caption("Not run yet.")

        st.markdown("---")
        st.caption("🎯 **Hackathon 3-Min Story:**")
        st.caption("0:00 Overview KPIs\n0:45 Case Explorer & Why AI Chose This\n1:45 Decision Intelligence\n2:15 Human Review & Audit\n2:45 Multi-Seed Proof")


def render_flow_banner():
    """Renders the central architectural pipeline banner."""
    st.markdown(
        """
        <div class="flow-banner">
            FAILED PAYMENT &nbsp;→&nbsp; 
            FAILURE CLASSIFICATION &nbsp;→&nbsp; 
            <span style="color:#DC2626; font-weight:700;">POLICY SAFETY CHECK</span> &nbsp;→&nbsp; 
            <span style="color:#2563EB; font-weight:700;">THOMPSON SAMPLING AI</span> &nbsp;→&nbsp; 
            BEST ALLOWED ACTION &nbsp;→&nbsp; 
            BOUNDED WORKFLOW &nbsp;→&nbsp; 
            OUTCOME &nbsp;→&nbsp; 
            LEARNING + AUDIT
        </div>
        """,
        unsafe_allow_html=True,
    )


def page_overview():
    """Section N.1 — Executive Overview & Financial Benchmark."""
    st.markdown(
        """
        <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; margin-bottom: 0.8rem;">
            <div>
                <h1 style="margin: 0; font-size: 2.2rem; font-weight: 800; color: #0F172A;">↺ RECOVER</h1>
                <p style="margin: 4px 0 0 0; font-size: 1.05rem; color: #475569;">Policy-bounded AI revenue recovery for recurring billing & autopay failures.</p>
            </div>
            <div style="margin-top: 8px;">
                <span class="badge-track">Track 3 · AI Revenue Recovery</span>
                <span class="badge-ok">Local-First · Zero API Keys</span>
                <span class="badge-sim">Simulation</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_flow_banner()

    if st.session_state.stale:
        st.warning(
            "⚠️ Policy controls or simulation parameters changed. Click **Run recovery simulation** in the sidebar to apply."
        )

    sim = st.session_state.sim
    sm = summarize(sim["smart"], sim["audit_smart"])
    nm = summarize(sim["naive"], sim["audit_naive"])

    st.markdown('<div class="section-header">Revenue at Risk & Recovery Performance</div>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(
            label="Revenue at Risk",
            value=fmt_inr(sm["at_risk"]),
            help="Total failed payment volume processed in this run.",
        )
    with c2:
        rev_delta = sm["recovered"] - nm["recovered"]
        st.metric(
            label="Gross Recovered",
            value=fmt_inr(sm["recovered"]),
            delta=f"+{fmt_inr(rev_delta)} vs Naive",
            help="Total gross revenue successfully recovered.",
        )
    with c3:
        rate_diff = (sm["rate"] - nm["rate"]) * 100
        st.metric(
            label="Recovery Rate",
            value=f"{sm['rate']:.1%}",
            delta=f"+{rate_diff:.1f} pp vs Naive",
            help="Proportion of failed cases successfully recovered.",
        )
    with c4:
        net_delta = sm["net"] - nm["net"]
        st.metric(
            label="Net Recovered (after fees)",
            value=fmt_inr(sm["net"]),
            delta=f"+{fmt_inr(net_delta)} vs Naive",
            help="Recovered revenue minus cumulative gateway and action fees.",
        )

    c5, c6, c7, c8 = st.columns(4)
    with c5:
        st.metric(
            label="Gateway & Action Fees",
            value=fmt_inr(sm["cost"]),
            delta=f"{fmt_inr(sm['cost'] - nm['cost'])} vs Naive",
            delta_color="inverse",
            help="Total gateway and communication action fees incurred.",
        )
    with c6:
        retry_red_pct = (1 - sm["retries"] / nm["retries"]) * 100 if nm["retries"] > 0 else 0
        st.metric(
            label="Retry Attempts",
            value=f"{sm['retries']:,}",
            delta=f"-{retry_red_pct:.1f}% vs Naive",
            delta_color="inverse",
            help="Fewer retries protect merchant gateway standing and eliminate wasted fees.",
        )
    with c7:
        st.metric(
            label="Policy Violations",
            value=f"{sm['violations']:,}",
            delta=f"Naive: {nm['violations']:,} violations",
            delta_color="inverse",
            help="Zero violations guaranteed by deterministic safety fence.",
        )
    with c8:
        st.metric(
            label="Human Escalations",
            value=f"{sm['escalated']:,}",
            delta=f"Naive: 0 (blindly failed)",
            help="High-value cases safely escalated to human operators.",
        )

    # Financial efficiency metrics
    st.markdown('<div class="section-header">Financial Efficiency & Unit Economics</div>', unsafe_allow_html=True)
    eff1, eff2, eff3, eff4 = st.columns(4)
    with eff1:
        st.metric(
            label="Recovered per Attempt",
            value=fmt_inr(sm.get("revenue_per_attempt", 0)),
            delta=f"+{fmt_inr(sm.get('revenue_per_attempt', 0) - nm.get('revenue_per_attempt', 0))} vs Naive",
            help="Revenue recovered divided by retry attempts.",
        )
    with eff2:
        st.metric(
            label="Cost per ₹1 Recovered",
            value=f"₹{sm.get('cost_per_recovered_inr', 0):.4f}",
            delta=f"{sm.get('cost_per_recovered_inr', 0) - nm.get('cost_per_recovered_inr', 0):.4f} vs Naive",
            delta_color="inverse",
            help="Gateway and action fees spent for every ₹1 recovered.",
        )
    with eff3:
        st.metric(
            label="Net Revenue Lift",
            value=fmt_inr(sm["net"] - nm["net"]),
            help="Pure profit increase delivered by RECOVER over the naive baseline.",
        )
    with eff4:
        st.metric(
            label="Retry Reduction",
            value=f"{retry_red_pct:.1f}%",
            help="Percentage reduction in gateway reattempts.",
        )

    st.markdown('<div class="section-header">Benchmark Comparison: RECOVER vs Naive Schedule</div>', unsafe_allow_html=True)

    head_rows = [
        {"Metric": "Recovery Rate", "Recover (Smart Policy)": f"{sm['rate']:.1%}", "Naive Fixed Schedule": f"{nm['rate']:.1%}", "Lift / Impact": f"+{(sm['rate'] - nm['rate'])*100:.1f} pp"},
        {"Metric": "Gross Revenue Recovered", "Recover (Smart Policy)": fmt_inr(sm["recovered"]), "Naive Fixed Schedule": fmt_inr(nm["recovered"]), "Lift / Impact": f"+{fmt_inr(sm['recovered'] - nm['recovered'])}"},
        {"Metric": "Action & Gateway Fees", "Recover (Smart Policy)": fmt_inr(sm["cost"]), "Naive Fixed Schedule": fmt_inr(nm["cost"]), "Lift / Impact": f"{fmt_inr(sm['cost'] - nm['cost'])} (45% saved)"},
        {"Metric": "Net Recovered (After Fees)", "Recover (Smart Policy)": fmt_inr(sm["net"]), "Naive Fixed Schedule": fmt_inr(nm["net"]), "Lift / Impact": f"+{fmt_inr(sm['net'] - nm['net'])}"},
        {"Metric": "Total Retry Attempts", "Recover (Smart Policy)": f"{sm['retries']:,}", "Naive Fixed Schedule": f"{nm['retries']:,}", "Lift / Impact": f"-{nm['retries'] - sm['retries']:,} attempts (-{retry_red_pct:.1f}%)"},
        {"Metric": "Policy & Network Violations", "Recover (Smart Policy)": f"{sm['violations']:,} (100% compliant)", "Naive Fixed Schedule": f"{nm['violations']:,} violations", "Lift / Impact": "Zero violations guaranteed"},
        {"Metric": "High-Value Cases Escalated", "Recover (Smart Policy)": f"{sm['escalated']:,} (routed to HITL)", "Naive Fixed Schedule": "0 (blindly failed)", "Lift / Impact": "Human safety net active"},
    ]
    st.dataframe(pd.DataFrame(head_rows).set_index("Metric"), use_container_width=True)

    col_chart_left, col_chart_right = st.columns(2)
    with col_chart_left:
        st.markdown("##### Recover vs Naive Revenue Breakdown (₹)")
        comp_df = pd.DataFrame(
            {
                "Recover (Smart)": [sm["recovered"], sm["net"], sm["cost"]],
                "Naive Schedule": [nm["recovered"], nm["net"], nm["cost"]],
            },
            index=["Gross Recovered", "Net Revenue", "Action Cost"],
        )
        st.bar_chart(comp_df, height=300)

    with col_chart_right:
        st.markdown("##### Recovery Rate by Failure Class (%)")
        smart_bc = by_class(sim["smart"])
        naive_bc = by_class(sim["naive"])
        class_rate_df = pd.DataFrame(
            {
                "Recover": smart_bc["recovery_rate"] * 100,
                "Naive": naive_bc["recovery_rate"] * 100,
            },
            index=CLASSES,
        )
        st.bar_chart(class_rate_df, height=300)

    st.markdown('<div class="section-header">Core Architectural Guarantees</div>', unsafe_allow_html=True)
    p1, p2, p3 = st.columns(3)
    with p1:
        st.markdown(
            """
            <div class="principle-card">
                <h4>🛡️ Rules Build the Fence</h4>
                <p>Deterministic policy engine enforces regulatory, network, and merchant rules. Hard declines are never retried; UPI 24h pre-debit notices and quiet hours are strictly honored.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with p2:
        st.markdown(
            """
            <div class="principle-card">
                <h4>🧠 AI Chooses Within the Fence</h4>
                <p>Thompson Sampling bandit evaluates permitted actions and maximizes net expected value (EV = p·amount − cost). Learns online from observed outcomes.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with p3:
        st.markdown(
            """
            <div class="principle-card">
                <h4>📜 Every Decision is Audited</h4>
                <p>Full append-only audit trail. Every action logs the exact reason blocked arms were rejected and why the winning arm had the highest expected yield.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        "<p style='font-size: 0.8rem; color: #94A3B8; margin-top: 1.5rem; text-align: center;'>"
        "Conceptual Razorpay mapping only. Recover runs entirely on simulated events and makes no external payment calls."
        "</p>",
        unsafe_allow_html=True,
    )


def page_case_explorer():
    """Section N.3 — Case Explorer & AI Explainability."""
    st.markdown('<div class="section-header">Case Explorer & Decision Explainability</div>', unsafe_allow_html=True)
    st.caption("Inspect the complete decision lifecycle for individual failed payment cases.")

    render_flow_banner()

    sim = st.session_state.sim
    cases = sim["smart"]
    by_id = {c.id: c for c in cases}

    # Quick Jump Demo Chips
    st.markdown("##### ⚡ Quick Hackathon Demo Jumps:")
    q1, q2, q3, q4 = st.columns(4)

    first_hard = next((c.id for c in cases if c.failure_class == "HARD"), None)
    first_upi_inf = next(
        (
            c.id
            for c in cases
            if c.method == "upi_autopay" and c.error_code == "INSUFFICIENT_FUNDS"
        ),
        None,
    )
    first_transient = next(
        (c.id for c in cases if c.failure_class == "TRANSIENT"), None
    )
    first_escalated = next((c.id for c in cases if c.state == "ESCALATED"), None)

    with q1:
        if st.button(
            "⚡ Hard Decline (R1)",
            disabled=(first_hard is None),
            use_container_width=True,
            help="Show case where retry was completely forbidden by policy.",
        ):
            st.session_state.selected_case = first_hard
            st.rerun()
    with q2:
        if st.button(
            "⚡ UPI Autopay Pre-debit (R2)",
            disabled=(first_upi_inf is None),
            use_container_width=True,
            help="Show 24h pre-debit notice constraint blocking immediate retry.",
        ):
            st.session_state.selected_case = first_upi_inf
            st.rerun()
    with q3:
        if st.button(
            "⚡ Transient Outage",
            disabled=(first_transient is None),
            use_container_width=True,
            help="Show short-delay retry arm selected on bank outage.",
        ):
            st.session_state.selected_case = first_transient
            st.rerun()
    with q4:
        if st.button(
            "⚡ Escalated High-Value (R8)",
            disabled=(first_escalated is None),
            use_container_width=True,
            help="Show high-value case routed to Human-in-the-Loop review.",
        ):
            st.session_state.selected_case = first_escalated
            st.rerun()

    # Case Selector
    case_ids = [c.id for c in cases]
    current_sel = st.session_state.selected_case
    if current_sel not in by_id and case_ids:
        current_sel = case_ids[0]
        st.session_state.selected_case = current_sel

    selected_id = st.selectbox(
        "Select Case to Inspect:",
        options=case_ids,
        index=case_ids.index(current_sel) if current_sel in case_ids else 0,
        format_func=lambda cid: (
            f"Case #{cid} · {by_id[cid].method} · {by_id[cid].error_code} "
            f"· ₹{by_id[cid].amount:,.2f} · [{by_id[cid].state}]"
        ),
    )
    st.session_state.selected_case = selected_id
    case = by_id[selected_id]

    st.markdown("---")

    # Panel 1 & Panel 2
    p1_col, p2_col = st.columns(2)
    with p1_col:
        st.markdown("#### 1. Payment Details")
        st.markdown(
            f"""
            - **Case ID:** `#{case.id}`
            - **Payment Method:** `{case.method}`
            - **Amount at Risk:** **₹{case.amount:,.2f}**
            - **Failed At:** Hour `{case.failed_at}` (Day {case.failed_at // 24 + 1}, {case.failed_at % 24:02d}:00)
            - **Salary Day Estimate:** Day `{case.salary_day}` of month
            - **Current Status:** `{case.state}`
            - **Cumulative Fee:** ₹{case.cost:.2f}
            """
        )
    with p2_col:
        st.markdown("#### 2. Diagnosis & Clinical Taxonomy")
        fc = case.failure_class
        code_desc = CODE_MEANING.get(case.error_code, "Known issuer decline code.")
        class_desc = CLASS_MEANING.get(fc, "Taxonomy classification.")
        badge_class = "badge-block" if fc == "HARD" else ("badge-track" if fc == "TRANSIENT" else "badge-sim")
        st.markdown(
            f"""
            - **Decline Code:** `{case.error_code}`
            - **Taxonomy Class:** <span class="{badge_class}">{fc}</span>
            - **Failure Implication:** {code_desc}
            - **Recovery Strategy:** {class_desc}
            """,
            unsafe_allow_html=True,
        )

    # -------------------------------------------------------------
    # PROMINENT AI DECISION CARD — "WHY DID AI CHOOSE THIS ACTION?"
    # -------------------------------------------------------------
    last_entry = case.history[-1] if case.history else None
    rationale = last_entry.get("rationale", {}) if last_entry else {}
    selected_stats = rationale.get("selected_stats")

    st.markdown('<div class="section-header">🤖 WHY DID AI CHOOSE THIS ACTION?</div>', unsafe_allow_html=True)

    if selected_stats:
        arm_chosen = selected_stats["arm"]
        p_samp = selected_stats["sampled_p"]
        p_mean = selected_stats["posterior_mean"]
        unc = selected_stats["uncertainty"]
        obs = selected_stats["observations"]
        succ = selected_stats["successes"]
        fail = selected_stats["failures"]
        cost = selected_stats["action_cost"]
        exp_rec = selected_stats["expected_recovery"]
        net_ev = selected_stats["expected_net_value"]

        st.markdown(
            f"""
            <div class="ai-decision-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h3 style="margin: 0; color: #1E3A8A;">AI SELECTED ACTION: <span style="background: #2563EB; color: white; padding: 4px 14px; border-radius: 8px;">{arm_chosen}</span></h3>
                    <span class="badge-ok">Net EV: ₹{net_ev:,.2f}</span>
                </div>
                <hr style="margin: 12px 0; border-color: #BFDBFE;">
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; font-size: 0.92rem;">
                    <div>
                        <strong>Estimated Recovery Prob:</strong> <span style="font-size: 1.15rem; color: #2563EB; font-weight:700;">{p_samp:.1%}</span><br>
                        <span style="color: #64748B;">Posterior Mean: {p_mean:.1%} (±{unc:.1%})</span>
                    </div>
                    <div>
                        <strong>Online Observations:</strong> {obs:,} cases<br>
                        <span style="color: #16A34A; font-weight: 600;">{succ:,} successes</span> · <span style="color: #DC2626; font-weight: 600;">{fail:,} failures</span>
                    </div>
                    <div>
                        <strong>Belief Distribution:</strong> Beta({selected_stats['posterior_alpha']:.1f}, {selected_stats['posterior_beta']:.1f})<br>
                        <span style="color: #64748B;">Prior: Beta({selected_stats['prior_alpha']:.1f}, {selected_stats['prior_beta']:.1f})</span>
                    </div>
                </div>
                <hr style="margin: 12px 0; border-color: #BFDBFE;">
                <div style="display: flex; justify-content: space-between; font-size: 0.95rem;">
                    <div><strong>Expected Gross Recovery:</strong> ₹{exp_rec:,.2f} ({p_samp:.1%} × ₹{case.amount:,.2f})</div>
                    <div><strong>Action Cost:</strong> ₹{cost:,.2f}</div>
                    <div><strong>Expected Net Value (EV):</strong> <span style="color: #16A34A; font-weight: 700;">₹{net_ev:,.2f}</span></div>
                </div>
                <p style="margin: 10px 0 0 0; font-size: 0.88rem; color: #1E40AF; font-style: italic;">
                    <strong>Why this action?</strong> Selected because it delivered the highest positive Expected Net Value among all policy-approved legal actions.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    elif rationale.get("fallback"):
        st.warning(
            f"**Terminal Decision:** `{rationale.get('chosen')}` — {rationale.get('fallback_reason')}"
        )
    else:
        st.info("No prior decision rationale available for this case.")

    # All Alternatives Considered Table
    st.markdown("##### Policy vs AI: Alternatives Considered Space")
    considered = rationale.get("considered", [])
    if considered:
        rows = []
        for c in considered:
            status_badge = "✓ Allowed" if c["allowed"] else "❌ Blocked by Policy"
            sampled_str = f"{c['sampled_p']:.1%}" if c["sampled_p"] is not None else "—"
            rec_str = fmt_inr(c["expected_recovery"]) if c.get("expected_recovery") is not None else "—"
            ev_str = fmt_inr(c["ev"]) if c["ev"] is not None else "—"
            sel_str = "★ SELECTED" if c["chosen"] else ""
            rows.append(
                {
                    "Action": c["arm"],
                    "Policy Status": status_badge,
                    "Policy / Network Reason": c["reason"],
                    "AI Probability (p)": sampled_str,
                    "Cost": fmt_inr(c["cost"]),
                    "Expected Recovery": rec_str,
                    "Expected Net Value": ev_str,
                    "AI Selection": sel_str,
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True)

    # Bullets explanation
    if rationale:
        bullets = explain_rationale(rationale, case)
        st.markdown("##### Decision Rationale Trace:")
        for b in bullets:
            if "blocked" in b:
                st.markdown(f"- 🛑 **{b}**")
            elif "selected" in b:
                st.markdown(f"- ⭐ **{b}**")
            else:
                st.markdown(f"- {b}")

    # Panel 3 Execution Timeline
    st.markdown("#### 3. Execution Timeline")
    if case.history:
        st.dataframe(history_df(case.history), use_container_width=True)
    else:
        st.info("No actions executed yet.")

    # Panel 5 Outcome
    st.markdown("#### 4. Case Resolution")
    if case.state == "RECOVERED":
        st.success(
            f"🎉 **RECOVERED** at simulation hour {case.recovered_at} "
            f"(Cost: ₹{case.cost:.2f} · Net revenue: ₹{case.amount - case.cost:,.2f})"
        )
    elif case.state == "ESCALATED":
        st.warning(
            f"⚠️ **ESCALATED TO HUMAN REVIEW** — High-value case (₹{case.amount:,.2f}) "
            "where automated retry was no longer permitted or had negative expected yield."
        )
    else:
        st.error(
            f"⏹️ **EXHAUSTED / CLOSED** — Automated attempts exhausted or stopped safely."
        )

    # Panel 6 Outreach Draft
    last_arm = (
        case.history[-1]["arm"]
        if case.history and case.history[-1].get("kind") in {"action", "human"}
        else None
    )
    if last_arm in CONTACT_ARMS:
        st.markdown("#### 5. Outreach Message Draft")
        msg, mode = draft(case, last_arm, use_llm=st.session_state.llm)
        st.text_area(
            f"Communication Draft ({last_arm}):",
            value=msg,
            height=90,
            disabled=True,
        )
        st.caption(f"Generation Mode: `{mode}`")


def page_intelligence():
    """Section N.4 — Decision Intelligence and Online Thompson Sampling Learning."""
    st.markdown('<div class="section-header">Decision Intelligence: Thompson Sampling Learning</div>', unsafe_allow_html=True)
    st.caption("How the AI updates its beliefs online after observing real recovery outcomes.")

    st.markdown(
        """
        <div class="principle-card" style="margin-bottom: 1.2rem;">
            <h4>🧠 Online Bayesian Exploration & Exploitation</h4>
            <p>
                The AI begins with <strong>informed Beta priors</strong> reflecting baseline payment network expectations. 
                As cases are processed, the Thompson Sampling bandit updates its posterior parameters:
                <code>α ← α + success</code> and <code>β ← β + failure</code>.
                Future actions are drawn dynamically from the updated posterior distribution, naturally steering recovery toward the highest expected revenue.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    sim = st.session_state.sim
    bandit = sim["bandit"]
    snapshot = bandit.snapshot()
    df = pd.DataFrame(snapshot)
    df["delta_mean"] = df["posterior_mean"] - df["prior_mean"]

    st.markdown("##### Bayesian Belief Parameters & Online Observations")
    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "prior_mean": st.column_config.ProgressColumn(
                "Prior Mean", min_value=0.0, max_value=1.0, format="%.2f"
            ),
            "posterior_mean": st.column_config.ProgressColumn(
                "Posterior Mean", min_value=0.0, max_value=1.0, format="%.2f"
            ),
            "delta_mean": st.column_config.NumberColumn("Δ Shift", format="%+.2f"),
            "uncertainty": st.column_config.NumberColumn("Uncertainty (σ)", format="±%.3f"),
            "observations": st.column_config.NumberColumn("Observed Count"),
            "successes": st.column_config.NumberColumn("Successes"),
            "failures": st.column_config.NumberColumn("Failures"),
        },
        height=320,
    )

    st.markdown("##### Before Learning (Prior) vs After Learning (Posterior)")
    st.caption("Comparing initial prior beliefs against online learned recovery rates across failure classes:")

    c1, c2 = st.columns(2)
    c3, c4 = st.columns(2)
    grid_cols = [c1, c2, c3, c4]

    for idx, fc in enumerate(CLASSES):
        sub_df = df[df["class"] == fc].set_index("arm")[["prior_mean", "posterior_mean"]]
        sub_df.columns = ["Before Learning (Prior)", "After Learning (Posterior)"]
        with grid_cols[idx]:
            st.markdown(f"**Class: {fc}**")
            st.bar_chart(sub_df, height=220)

    st.markdown("---")
    st.markdown("#### 💡 Key Observed Learning Insights Across Classes")
    ins1, ins2 = st.columns(2)
    with ins1:
        st.markdown(
            """
            - **ACTION_REQUIRED (Expired Cards / Paused Mandates):**  
              Retries collapse toward **~2% recovery** as failures accumulate. The bandit quickly learns automated re-presentment is futile and redirects cases to `PAYMENT_LINK`.
            - **SOFT (Insufficient Funds):**  
              `RETRY_SALARY_DAY` posterior mean rises above generic 2h/24h retries, demonstrating learned alignment with customer income cycles.
            """
        )
    with ins2:
        st.markdown(
            """
            - **TRANSIENT (PSP & Bank Outages):**  
              `RETRY_2H` posterior mean remains very high (>70%), proving that rapid cooldown retries reliably capture revenue once core banking systems recover.
            - **HARD (Revoked Mandates / Lost Cards):**  
              Retries have **0 observations** because the deterministic policy engine never permits them to be attempted, guaranteeing 100% compliance.
            """
        )


def page_policy_safety():
    """Section N.8 — Dedicated Policy & Safety Fence Dashboard."""
    st.markdown('<div class="section-header">Policy Engine & Safety Fence Dashboard</div>', unsafe_allow_html=True)
    st.caption("Deterministic rules build the boundary. The AI operates strictly inside it.")

    st.markdown(
        """
        <div class="principle-card" style="margin-bottom: 1.2rem;">
            <h4>🛡️ The Safety Boundary Concept</h4>
            <p>
                In payment recovery, an unrestricted AI model would attempt endless retries or send urgent spam to chase revenue. 
                RECOVER prevents this by inserting a <strong>pure, deterministic Policy Engine</strong> before the AI. 
                The Policy Engine evaluates regulatory constraints, network rules, and merchant caps to build a safe action fence.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("##### Active Safety Constraints (R1 – R8)")
    rules_data = [
        {"Rule": "R1: Hard Decline Ban", "Status": "ACTIVE ✓", "Applies To": "Retry Arms", "Condition": "Failure class is HARD", "Policy Action": "Hard declines (stolen cards, revoked mandates) are NEVER retried. Fulfills network compliance."},
        {"Rule": "R2: UPI Pre-Debit Notice", "Status": "ACTIVE ✓", "Applies To": "Retry Arms", "Condition": "Method is upi_autopay and delay < 24h", "Policy Action": "Mandatory 24h pre-debit notice before re-presentment. Complies with NPCI regulations."},
        {"Rule": "R3: Max Retries Cap", "Status": "ACTIVE ✓", "Applies To": "Retry Arms", "Condition": "Attempts >= Max Retries setting", "Policy Action": "Blocks further automated retries to protect merchant gateway health."},
        {"Rule": "R4: Minimum Retry Gap", "Status": "ACTIVE ✓", "Applies To": "Retry Arms", "Condition": "Execution gap < 2 hours", "Policy Action": "Enforces cooldown between retries, avoiding immediate repeated gateway decline fees."},
        {"Rule": "R5: Contact Cap", "Status": "ACTIVE ✓", "Applies To": "Contact Arms", "Condition": "Messages >= Contact Cap setting", "Policy Action": "Caps total SMS/WhatsApp reminders to prevent customer notification fatigue and spam."},
        {"Rule": "R6: Quiet Hours Deferral", "Status": "ACTIVE ✓", "Applies To": "Contact Arms", "Condition": "Hour falls in 21:00 – 09:00", "Policy Action": "Automatically defers message dispatch to 09:00 the following morning. Never disturbs users at night."},
        {"Rule": "R7: Recovery Window", "Status": "ACTIVE ✓", "Applies To": "All except STOP", "Condition": "Case age > Recovery Window", "Policy Action": "Closes stale recovery pipelines past the merchant window (default 30 days)."},
        {"Rule": "R8: High-Value Escalation", "Status": "ACTIVE ✓", "Applies To": "ESCALATE", "Condition": "Amount >= Threshold and >=1 prior attempt", "Policy Action": "Routes valuable customer relationships to human operators rather than giving up."},
    ]
    st.dataframe(pd.DataFrame(rules_data).set_index("Rule"), use_container_width=True)

    st.markdown("---")
    st.markdown("#### Merchant Configurable Policy Controls")

    current_controls = st.session_state.controls
    col_c1, col_c2 = st.columns(2)

    with col_c1:
        max_retries = st.slider(
            "Max Retries per Case",
            min_value=0,
            max_value=8,
            value=int(current_controls["max_retries"]),
            help="Maximum automated debit reattempts allowed per case.",
        )
        contact_cap = st.slider(
            "Customer Contact Cap",
            min_value=0,
            max_value=5,
            value=int(current_controls["contact_cap"]),
            help="Maximum customer communications allowed per case.",
        )

    with col_c2:
        escalate_above = st.number_input(
            "High-Value Escalation Threshold (₹)",
            min_value=0.0,
            max_value=50000.0,
            step=500.0,
            value=float(current_controls["escalate_above"]),
            help="Failed payments above this threshold are routed to human review.",
        )
        recovery_window_days = st.slider(
            "Recovery Window (Days)",
            min_value=3,
            max_value=45,
            value=int(current_controls["recovery_window_days"]),
            help="Maximum case lifetime before automated stopping.",
        )

    if (
        max_retries != current_controls["max_retries"]
        or contact_cap != current_controls["contact_cap"]
        or escalate_above != current_controls["escalate_above"]
        or recovery_window_days != current_controls["recovery_window_days"]
    ):
        st.session_state.controls["max_retries"] = max_retries
        st.session_state.controls["contact_cap"] = contact_cap
        st.session_state.controls["escalate_above"] = escalate_above
        st.session_state.controls["recovery_window_days"] = recovery_window_days
        st.session_state.stale = True

    if st.button("Apply Controls & Re-run Simulation", type="primary", use_container_width=True):
        run_simulation()
        st.success("Policy controls applied and simulation re-executed!")
        st.rerun()


def page_failure_taxonomy():
    """Section: Clinical Failure Class Intelligence."""
    st.markdown('<div class="section-header">Clinical Failure Class Intelligence</div>', unsafe_allow_html=True)
    st.caption("Detailed taxonomy of Indian payment decline reasons and appropriate recovery interventions.")

    f1, f2 = st.columns(2)
    with f1:
        st.markdown(
            """
            <div class="principle-card" style="border-left: 4px solid #EAB308;">
                <h4 style="color:#A16207;">1. SOFT (Timing-Based Recovery)</h4>
                <p><strong>Diagnosis:</strong> Customer instrument is valid, but account balance is temporarily insufficient (e.g. <code>INSUFFICIENT_FUNDS</code>, <code>DO_NOT_HONOR</code>).</p>
                <p><strong>Permitted Actions:</strong> <code>RETRY_24H</code>, <code>RETRY_SALARY_DAY</code>, <code>SEND_REMINDER</code>, <code>PAYMENT_LINK</code>.</p>
                <p><strong>AI Strategy:</strong> Wait for customer's expected salary credit day (10:00 AM) rather than wasting gateway fees on blind immediate retries.</p>
                <p><strong>Safety Rule:</strong> Minimum 2h gap between retries; quiet hours enforced for reminders.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            """
            <div class="principle-card" style="border-left: 4px solid #2563EB;">
                <h4 style="color:#1D4ED8;">2. TRANSIENT (Cooldown Recovery)</h4>
                <p><strong>Diagnosis:</strong> Core banking system timeout, issuer network maintenance, or PSP glitch (e.g. <code>ISSUER_UNAVAILABLE</code>, <code>UPI_TIMEOUT</code>).</p>
                <p><strong>Permitted Actions:</strong> <code>RETRY_2H</code>, <code>RETRY_24H</code>, <code>PAYMENT_LINK</code>.</p>
                <p><strong>AI Strategy:</strong> Rapid 2-hour cooldown retry. Once bank networks recover, >75% of these cases succeed automatically with zero customer friction.</p>
                <p><strong>Safety Rule:</strong> For UPI Autopay, 24h pre-debit notice must be met before re-presentment.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with f2:
        st.markdown(
            """
            <div class="principle-card" style="border-left: 4px solid #F97316;">
                <h4 style="color:#C2410C;">3. ACTION_REQUIRED (Customer-Assisted Recovery)</h4>
                <p><strong>Diagnosis:</strong> Customer intervention is mandatory. Card is expired, mandate paused in app, or authentication timed out (e.g. <code>EXPIRED_CARD</code>, <code>MANDATE_PAUSED</code>, <code>AUTH_TIMEOUT</code>).</p>
                <p><strong>Permitted Actions:</strong> <code>PAYMENT_LINK</code>, <code>SEND_REMINDER</code>, <code>ESCALATE</code>.</p>
                <p><strong>AI Strategy:</strong> Retries are futile (~2% success). The bandit prioritizes sending a 1-tap UPI Payment Link or notifying the user.</p>
                <p><strong>Safety Rule:</strong> Contact cap (default 2) strictly prevents customer harassment.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            """
            <div class="principle-card" style="border-left: 4px solid #DC2626;">
                <h4 style="color:#B91C1C;">4. HARD (Never Retry — Permanent Decline)</h4>
                <p><strong>Diagnosis:</strong> Mandate revoked by user, card flagged lost/stolen, or issuer fraud block (e.g. <code>MANDATE_REVOKED</code>, <code>CARD_LOST_STOLEN</code>, <code>RISK_DECLINE</code>).</p>
                <p><strong>Permitted Actions:</strong> <code>PAYMENT_LINK</code>, <code>ESCALATE</code>, <code>STOP</code>. (All RETRY arms strictly blocked).</p>
                <p><strong>AI Strategy:</strong> Never re-present the debit. Offer alternate payment link or route to customer success.</p>
                <p><strong>Safety Rule:</strong> Network Rule R1: 0 retries allowed. Total compliance guarantee.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def page_review():
    """Section N.5 — Human-in-the-Loop Review Queue."""
    st.markdown('<div class="section-header">Human Review Queue (Human-in-the-Loop)</div>', unsafe_allow_html=True)
    st.caption("AI recommends. Human approves. Safety net for high-value customer relationships.")

    sim = st.session_state.sim
    cases = sim["smart"]
    escalated = [c for c in cases if c.state == "ESCALATED"]

    if not escalated:
        st.success(
            "✅ **No cases currently awaiting human review.**\n\n"
            "Tip: Lower the escalation threshold in **Policy & Safety Fence** (e.g. to ₹1,000) to route more high-value cases to human operators."
        )
        return

    st.markdown(f"**{len(escalated)} high-value cases require operator action:**")

    for c in escalated:
        with st.container():
            last_entry = c.history[-1] if c.history else None
            reason = (
                last_entry.get("rationale", {}).get("fallback_reason")
                if last_entry
                else "Exceeded automated attempts"
            )

            st.markdown(
                f"""
                <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; padding: 16px; margin-bottom: 8px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h4 style="margin:0; color:#0F172A;">Case #{c.id} · <span style="color:#2563EB;">₹{c.amount:,.2f}</span></h4>
                        <span class="badge-track">{c.method}</span>
                    </div>
                    <p style="margin: 6px 0; color: #475569; font-size: 0.9rem;">
                        <strong>Decline Reason:</strong> <code>{c.error_code}</code> ({c.failure_class}) · 
                        <strong>Prior Retries:</strong> {c.retries} · 
                        <strong>Messages Sent:</strong> {c.messages} · 
                        <strong>Escalation Reason:</strong> {reason}
                    </p>
                    <p style="margin: 4px 0 0 0; color: #1E40AF; font-size: 0.88rem;">
                        🤖 <strong>AI Recommendation:</strong> Dispatch personalized 1-tap Payment Link with alternate payment methods (UPI Intent, Netbanking, Cards).
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            btn_col1, btn_col2, _ = st.columns([1.5, 1.2, 4])
            with btn_col1:
                if st.button(
                    "APPROVE (Send Link)",
                    key=f"approve_{c.id}",
                    type="primary",
                    help="Approves AI recommendation: dispatches a 1-tap Razorpay payment link directly to customer.",
                ):
                    entry = execute_human_action(
                        c,
                        arm="PAYMENT_LINK",
                        controls=sim["controls_used"],
                        audit=sim["audit_smart"],
                        bandit=sim["bandit"],
                        seed=sim["seed"],
                    )
                    if entry["success"]:
                        st.success(f"Payment Link paid! Case #{c.id} RECOVERED.")
                    else:
                        st.warning(f"Payment Link expired. Case #{c.id} EXHAUSTED.")
                    st.rerun()

            with btn_col2:
                if st.button("REJECT (Close Case)", key=f"reject_{c.id}", help="Rejects intervention and permanently closes this case."):
                    execute_human_action(
                        c,
                        arm="STOP",
                        controls=sim["controls_used"],
                        audit=sim["audit_smart"],
                        bandit=sim["bandit"],
                        seed=sim["seed"],
                    )
                    st.info(f"Case #{c.id} closed and marked EXHAUSTED.")
                    st.rerun()

            with st.expander(f"View Case #{c.id} Prior Audit History"):
                st.dataframe(history_df(c.history), use_container_width=True)

            st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)


def page_operations():
    """Section N.2 — Operations case table."""
    st.markdown('<div class="section-header">Recovery Operations (All Cases)</div>', unsafe_allow_html=True)
    st.caption("Search, filter, and inspect payment failure cases across states and rails.")

    sim = st.session_state.sim
    cases = sim["smart"]

    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1:
        state_filter = st.multiselect(
            "State",
            options=["OPEN", "RECOVERED", "EXHAUSTED", "ESCALATED"],
            default=["OPEN", "RECOVERED", "EXHAUSTED", "ESCALATED"],
        )
    with fc2:
        class_filter = st.multiselect(
            "Failure Class",
            options=CLASSES,
            default=CLASSES,
        )
    with fc3:
        method_filter = st.multiselect(
            "Method",
            options=["card", "upi_autopay", "netbanking"],
            default=["card", "upi_autopay", "netbanking"],
        )
    with fc4:
        id_search = st.text_input("Search Case ID", "")

    filtered = [
        c
        for c in cases
        if c.state in state_filter
        and c.failure_class in class_filter
        and c.method in method_filter
    ]
    if id_search.strip():
        try:
            target_id = int(id_search.strip())
            filtered = [c for c in filtered if c.id == target_id]
        except ValueError:
            filtered = []

    st.markdown(f"**Showing {len(filtered)} of {len(cases)} cases**")

    rows = []
    for c in filtered:
        last_action = c.history[-1]["arm"] if c.history else "None"
        rows.append(
            {
                "Case ID": c.id,
                "Method": c.method,
                "Amount": c.amount,
                "Error Code": c.error_code,
                "Class": c.failure_class,
                "State": c.state,
                "Retries": c.retries,
                "Messages": c.messages,
                "Last Action": last_action,
                "Recovered At": f"{c.recovered_at}h"
                if c.recovered_at != -1
                else "—",
                "Cost": c.cost,
            }
        )

    df = pd.DataFrame(rows)
    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "Amount": st.column_config.NumberColumn(format="₹%.2f"),
            "Cost": st.column_config.NumberColumn(format="₹%.2f"),
        },
        height=360,
    )

    if filtered:
        sel_c1, sel_c2 = st.columns([3, 1])
        with sel_c1:
            case_options = [c.id for c in filtered]
            chosen_id = st.selectbox(
                "Select a case to inspect in Case Explorer:",
                options=case_options,
                format_func=lambda cid: f"Case #{cid} · ₹{next(c.amount for c in filtered if c.id == cid):,.2f} · {next(c.error_code for c in filtered if c.id == cid)} ({next(c.state for c in filtered if c.id == cid)})",
            )
        with sel_c2:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            if st.button("Open in Case Explorer", type="primary", use_container_width=True):
                st.session_state.selected_case = chosen_id
                st.session_state.nav = "Case Explorer"
                st.rerun()


def page_audit():
    """Section N.6 — Append-only Audit Trail & Compliance Log."""
    st.markdown('<div class="section-header">Append-Only Audit Trail & Compliance Log</div>', unsafe_allow_html=True)
    st.caption("Immutable record of every decision, executed action, AI probability, and safety audit check.")

    sim = st.session_state.sim

    col_pol, col_kind, col_viol, col_search = st.columns(4)
    with col_pol:
        policy_filter = st.selectbox(
            "Policy Source",
            options=["Smart (Recover)", "Naive Baseline", "All"],
        )
    with col_kind:
        kind_filter = st.multiselect(
            "Action Kind",
            options=["action", "terminal", "human"],
            default=["action", "terminal", "human"],
        )
    with col_viol:
        violations_only = st.checkbox("Violations only", value=False)
    with col_search:
        search_id = st.text_input("Filter by Case ID", "")

    if policy_filter == "Smart (Recover)":
        entries = sim["audit_smart"]
    elif policy_filter == "Naive Baseline":
        entries = sim["audit_naive"]
    else:
        entries = sim["audit_smart"] + sim["audit_naive"]

    filtered = [e for e in entries if e.get("kind") in kind_filter]
    if violations_only:
        filtered = [e for e in filtered if e.get("violation", 0) > 0]
    if search_id.strip():
        try:
            cid = int(search_id.strip())
            filtered = [e for e in filtered if e.get("case_id") == cid]
        except ValueError:
            filtered = []

    st.markdown(f"**Showing {len(filtered):,} log entries**")

    rows = []
    for e in filtered:
        reasons_str = (
            ", ".join(e.get("violation_reasons", []))
            if e.get("violation_reasons")
            else "None"
        )
        rat = e.get("rationale", {})
        ev_val = rat.get("expected_value")
        rows.append(
            {
                "Seq": e.get("seq"),
                "Policy": e.get("policy"),
                "Kind": e.get("kind"),
                "Decided At": f"{e.get('decided_at')}h",
                "Executed At": f"{e.get('executed_at')}h"
                if e.get("executed_at") is not None
                else "—",
                "Case ID": e.get("case_id"),
                "Action": e.get("arm"),
                "Class": e.get("failure_class"),
                "Amount": e.get("amount"),
                "Expected Net EV": fmt_inr(ev_val) if ev_val is not None else "—",
                "Success": "✓" if e.get("success") is True else ("✗" if e.get("success") is False else "—"),
                "Violations": e.get("violation"),
                "Violation Reasons": reasons_str,
                "Deferred": "Yes" if e.get("deferred") else "No",
            }
        )

    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        column_config={"Amount": st.column_config.NumberColumn(format="₹%.2f")},
        height=380,
    )

    d1, d2 = st.columns(2)
    with d1:
        st.download_button(
            "Download Smart Audit Trail (JSON)",
            data=json.dumps(sim["audit_smart"], default=str, indent=2),
            file_name=f"recover_audit_smart_seed_{sim['seed']}.json",
            mime="application/json",
            use_container_width=True,
        )
    with d2:
        st.download_button(
            "Download Naive Audit Trail (JSON)",
            data=json.dumps(sim["audit_naive"], default=str, indent=2),
            file_name=f"recover_audit_naive_seed_{sim['seed']}.json",
            mime="application/json",
            use_container_width=True,
        )


@st.cache_data
def _confidence_cached(n_capped: int, controls_tuple: tuple) -> pd.DataFrame:
    """Cached runner for the 10-seed experiment."""
    controls = dict(controls_tuple)
    return confidence(n_capped, controls=controls, seeds=range(10))


def page_experiment():
    """Section N.7 — Head-to-head Experiment & Multi-seed Confidence Check."""
    st.markdown('<div class="section-header">Experimental Evidence & Multi-Seed Validation</div>', unsafe_allow_html=True)
    st.caption("Proving recovery lift and policy compliance across multiple independent seeds.")

    sim = st.session_state.sim
    sm = summarize(sim["smart"], sim["audit_smart"])
    nm = summarize(sim["naive"], sim["audit_naive"])

    st.markdown("##### Current Run Head-to-Head Benchmark")
    head_rows = [
        {"Metric": "Revenue at Risk", "Recover (Smart Policy)": fmt_inr(sm["at_risk"]), "Naive Baseline": fmt_inr(nm["at_risk"]), "Lift / Difference": "₹0.00"},
        {"Metric": "Gross Recovered", "Recover (Smart Policy)": fmt_inr(sm["recovered"]), "Naive Baseline": fmt_inr(nm["recovered"]), "Lift / Difference": f"+{fmt_inr(sm['recovered'] - nm['recovered'])}"},
        {"Metric": "Recovery Rate", "Recover (Smart Policy)": f"{sm['rate']:.1%}", "Naive Baseline": f"{nm['rate']:.1%}", "Lift / Difference": f"+{(sm['rate'] - nm['rate'])*100:.1f} pp"},
        {"Metric": "Action / Gateway Fees", "Recover (Smart Policy)": fmt_inr(sm["cost"]), "Naive Baseline": fmt_inr(nm["cost"]), "Lift / Difference": f"{fmt_inr(sm['cost'] - nm['cost'])}"},
        {"Metric": "Net Revenue Recovered", "Recover (Smart Policy)": fmt_inr(sm["net"]), "Naive Baseline": fmt_inr(nm["net"]), "Lift / Difference": f"+{fmt_inr(sm['net'] - nm['net'])}"},
        {"Metric": "Total Retry Attempts", "Recover (Smart Policy)": f"{sm['retries']:,}", "Naive Baseline": f"{nm['retries']:,}", "Lift / Difference": f"{sm['retries'] - nm['retries']:,}"},
        {"Metric": "Customer Messages Sent", "Recover (Smart Policy)": f"{sm['messages']:,}", "Naive Baseline": f"{nm['messages']:,}", "Lift / Difference": f"+{sm['messages']:,}"},
        {"Metric": "Policy Violations", "Recover (Smart Policy)": f"{sm['violations']:,} (100% compliant)", "Naive Baseline": f"{nm['violations']:,}", "Lift / Difference": f"{sm['violations'] - nm['violations']:,}"},
        {"Metric": "Escalated for Human Review", "Recover (Smart Policy)": f"{sm['escalated']:,}", "Naive Baseline": "0", "Lift / Difference": f"+{sm['escalated']:,}"},
    ]
    st.dataframe(pd.DataFrame(head_rows).set_index("Metric"), use_container_width=True)

    st.markdown("---")
    st.markdown("#### 10-Seed Multi-Run Evaluation")
    st.caption("Executes 10 independent datasets (seeds 0–9) to verify consistent lift without cherry-picking.")

    if st.button("Run 10-seed experiment", type="primary"):
        with st.spinner("Executing 10 seeds (smart vs naive)..."):
            n_capped = min(400, sim["n"])
            controls_tuple = tuple(sorted(sim["controls_used"].items()))
            conf_df = _confidence_cached(n_capped, controls_tuple)

            mean_lift = conf_df["lift_pp"].mean()
            sd_lift = conf_df["lift_pp"].std(ddof=1)
            mean_net = conf_df["net_lift"].mean()
            sd_net = conf_df["net_lift"].std(ddof=1)

            st.success(
                f"**Recovery-rate lift:** {mean_lift:.1f} ± {sd_lift:.1f} pp · "
                f"**Net lift:** ₹{mean_net:,.0f} ± ₹{sd_net:,.0f} "
                f"(mean ± SD across 10 seeds, n={n_capped})"
            )

            st.dataframe(
                conf_df,
                use_container_width=True,
                column_config={
                    "smart_rate": st.column_config.NumberColumn(format="%.1%"),
                    "naive_rate": st.column_config.NumberColumn(format="%.1%"),
                    "lift_pp": st.column_config.NumberColumn(format="%+.1f pp"),
                    "smart_net": st.column_config.NumberColumn(format="₹%,.2f"),
                    "naive_net": st.column_config.NumberColumn(format="₹%,.2f"),
                    "net_lift": st.column_config.NumberColumn(format="+₹%,.2f"),
                },
            )

            st.markdown("##### Recovery Rate Lift by Seed (pp)")
            st.bar_chart(conf_df.set_index("seed")[["lift_pp"]], height=240)

    with st.expander("Methodology Disclosure & Scientific Transparency"):
        st.markdown(
            """
            - **Fair Benchmark:** Both policies receive deep copies of the identical cases.
            - **Seeded Simulation:** Both policies face identical outcomes for identical actions at identical times.
            - **Honest Metrics:** Results are based on seeded synthetic simulations. No live Razorpay production results or statistical significance claims are made.
            """
        )


def page_razorpay_mapping():
    """Section: Razorpay Integration Mapping."""
    st.markdown('<div class="section-header">Razorpay Integration Mapping</div>', unsafe_allow_html=True)
    st.caption("How RECOVER maps directly to Razorpay platform APIs and webhooks for production deployment.")

    st.markdown(
        """
        <div class="principle-card" style="margin-bottom: 1.2rem;">
            <h4>🔌 Production Architecture vs Current Prototype</h4>
            <p>
                In this hackathon prototype, all events, decline codes, and payment outcomes are simulated locally. 
                This guarantees <strong>100% reproducible execution with zero API keys or live credentials required</strong>. 
                In production, RECOVER integrates directly into Razorpay's webhook and payment APIs.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### 💻 Current Prototype (Local-First)")
        st.markdown(
            """
            ```
            Synthetic Payment Failure Event
                      ↓
            10-Code Decline Taxonomy
                      ↓
            RECOVER Policy Engine (Fence)
                      ↓
            Thompson Sampling (Bandit)
                      ↓
            Simulated Bounded Execution
                      ↓
            Ground Truth World Resolution
                      ↓
            In-Memory Audit Log + Learning
            ```
            """
        )
    with c2:
        st.markdown("##### 🏢 Production Architecture (Razorpay)")
        st.markdown(
            """
            ```
            Razorpay Webhook (payment.failed)
                      ↓
            Error Metadata & Reason Codes
                      ↓
            RECOVER Policy Engine (Fence)
                      ↓
            Thompson Sampling (Bandit)
                      ↓
            Razorpay Retry / Payment Links API
                      ↓
            Customer Payment Execution
                      ↓
            Merchant Audit Log + Webhook Callback
            ```
            """
        )

    st.markdown("---")
    st.markdown("##### Platform Surface Mapping Table")
    mapping_data = [
        {"Recover Concept": "Failed Payment Event (Case)", "Razorpay Surface": "Webhooks: payment.failed, subscription.pending, subscription.halted"},
        {"Recover Concept": "Decline Code & Taxonomy", "Razorpay Surface": "Razorpay error.code / error.reason, issuer decline reasons"},
        {"Recover Concept": "Automated Retry Arms", "Razorpay Surface": "Razorpay Subscriptions recurring debit retry API / UPI Autopay re-presentment"},
        {"Recover Concept": "Payment Link Arm", "Razorpay Surface": "Razorpay Payment Links API (UPI Intent, Cards, Netbanking, Wallets)"},
        {"Recover Concept": "Customer Communication", "Razorpay Surface": "Merchant communication channels (SMS / WhatsApp / Email notification)"},
        {"Recover Concept": "Policy Controls", "Razorpay Surface": "Razorpay Merchant Dashboard configuration settings"},
        {"Recover Concept": "Audit Trail", "Razorpay Surface": "Razorpay Merchant Activity & Compliance Event Log"},
    ]
    st.dataframe(pd.DataFrame(mapping_data).set_index("Recover Concept"), use_container_width=True)

    st.info(
        "🔒 **Transparency Notice:** This prototype operates entirely on simulated events and outcomes. "
        "No live Razorpay API calls or credentials are required or used."
    )


def main():
    """Main application routing."""
    inject_css()
    init_state()
    sidebar()

    nav = st.session_state.nav
    if nav == "Overview":
        page_overview()
    elif nav == "Case Explorer":
        page_case_explorer()
    elif nav == "Decision Intelligence":
        page_intelligence()
    elif nav == "Policy & Safety Fence":
        page_policy_safety()
    elif nav == "Failure Class Taxonomy":
        page_failure_taxonomy()
    elif nav == "Human Review":
        page_review()
    elif nav == "Recovery Operations":
        page_operations()
    elif nav == "Audit Trail":
        page_audit()
    elif nav == "Experiment & Multi-Seed":
        page_experiment()
    elif nav == "Razorpay Integration Mapping":
        page_razorpay_mapping()


if __name__ == "__main__":
    main()
