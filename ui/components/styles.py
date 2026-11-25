"""Global dark-mode design system and CSS styles inspired by modern YouTube ranking UIs."""

import streamlit as st

DASHBOARD_CSS = """
<style>
/* --- Core Surface & Typography --- */
.block-container,
div[data-testid="stMainBlockContainer"] {
    padding-top: 1.5rem !important;
    padding-bottom: 3rem !important;
    padding-left: 1.75rem !important;
    padding-right: 1.75rem !important;
    max-width: 99% !important;
}

/* --- Context Header Banner --- */
.es-header-banner {
    background: linear-gradient(180deg, #151821 0%, #101218 100%);
    border: 1px solid #232734;
    border-radius: 12px;
    padding: 14px 20px;
    margin-bottom: 14px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 12px;
}
.es-header-left {
    display: flex;
    align-items: center;
    gap: 14px;
}
.es-brand-badge {
    width: 38px;
    height: 38px;
    border-radius: 10px;
    background: radial-gradient(circle at 30% 30%, #ff3b3b, #b80710);
    border: 1px solid rgba(255, 90, 90, 0.45);
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 800;
    font-size: 13px;
    letter-spacing: -0.03em;
    color: #ffffff;
    box-shadow: 0 4px 14px rgba(229, 9, 20, 0.28);
    flex-shrink: 0;
}
.es-eyebrow {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.11em;
    text-transform: uppercase;
    color: #ef4444;
    margin-bottom: 2px;
}
.es-header-title-row {
    display: flex;
    align-items: baseline;
    gap: 10px;
    flex-wrap: wrap;
}
.es-header-title {
    font-size: 19px;
    font-weight: 700;
    color: #f8fafc;
    letter-spacing: -0.01em;
}
.es-header-period {
    font-size: 13px;
    font-weight: 500;
    color: #8b93a7;
    font-variant-numeric: tabular-nums;
}
.es-header-right {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
}
.es-meta-chip {
    background: #181c26;
    border: 1px solid #272c3a;
    border-radius: 7px;
    padding: 4px 10px;
    font-size: 11.5px;
    color: #cbd5e1;
    font-variant-numeric: tabular-nums;
}
.es-status-completed {
    background: rgba(16, 185, 129, 0.14);
    border: 1px solid rgba(16, 185, 129, 0.35);
    color: #34d399;
    font-weight: 700;
}
.es-status-partial {
    background: rgba(245, 158, 11, 0.14);
    border: 1px solid rgba(245, 158, 11, 0.35);
    color: #fbbf24;
    font-weight: 700;
}

/* --- Segmented Pill Tabs (matching reference navigation bar) --- */
div[data-testid="stTabs"] div[role="tablist"] {
    background: #12141c;
    border: 1px solid #222634;
    border-radius: 10px;
    padding: 5px 6px;
    gap: 6px;
    margin-bottom: 12px;
}
div[data-testid="stTabs"] button[role="tab"] {
    border-radius: 7px !important;
    padding: 7px 15px !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    color: #94a3b8 !important;
    border: 1px solid transparent !important;
    background: transparent !important;
    transition: all 0.15s ease !important;
}
div[data-testid="stTabs"] button[role="tab"]:hover {
    color: #f1f5f9 !important;
    background: rgba(255, 255, 255, 0.04) !important;
}
div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
    background: rgba(229, 9, 20, 0.16) !important;
    border: 1px solid rgba(229, 9, 20, 0.55) !important;
    color: #ffffff !important;
    box-shadow: inset 0 0 12px rgba(229, 9, 20, 0.12);
}
div[data-testid="stTabs"] div[data-baseweb="tab-highlight"] {
    display: none !important;
}
div[data-testid="stTabs"] div[data-baseweb="tab-border"] {
    display: none !important;
}

/* --- KPI Metric Cards --- */
div[data-testid="stMetric"] {
    background: #12151e;
    border: 1px solid #222634;
    border-radius: 10px;
    padding: 12px 16px;
}
div[data-testid="stMetricLabel"] {
    font-size: 12px !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #8b93a7 !important;
}
div[data-testid="stMetricValue"] {
    font-variant-numeric: tabular-nums;
    font-weight: 700 !important;
}

/* --- Sleek Collapsible Filter & Hidden Columns Bars --- */
div[data-testid="stExpander"] {
    background: #12151e !important;
    border: 1px solid #222634 !important;
    border-radius: 9px !important;
    margin-bottom: 8px !important;
}
div[data-testid="stExpander"] summary {
    padding: 8px 14px !important;
    font-size: 12.5px !important;
    font-weight: 600 !important;
    color: #cbd5e1 !important;
}

/* --- Hidden Columns Chips Strip --- */
.es-hidden-bar {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 7px;
    padding: 4px 0 8px 0;
}
.es-hidden-chip {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: #1b1f2c;
    border: 1px solid #2c3246;
    border-radius: 6px;
    padding: 3px 9px;
    font-size: 11.5px;
    font-weight: 600;
    color: #cbd5e1;
}

/* --- Data Table Container & Grid --- */
.es-table-shell {
    background: #11131a;
    border: 1px solid #222634;
    border-radius: 11px;
    overflow: hidden;
    box-shadow: 0 10px 28px rgba(0, 0, 0, 0.35);
    margin-top: 6px;
    margin-bottom: 14px;
}
.es-table-scroll {
    width: 100%;
    overflow-x: auto;
}
.es-table-scroll::-webkit-scrollbar {
    height: 8px;
}
.es-table-scroll::-webkit-scrollbar-track {
    background: #0f1117;
}
.es-table-scroll::-webkit-scrollbar-thumb {
    background: #282d3e;
    border-radius: 4px;
}
.es-table {
    width: 100%;
    border-collapse: collapse;
    border: none !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Roboto, sans-serif;
    font-variant-numeric: tabular-nums;
    color: #f1f5f9;
}
div[data-testid="stMarkdownContainer"] table.es-table,
div[data-testid="stMarkdownContainer"] table.es-table thead,
div[data-testid="stMarkdownContainer"] table.es-table tbody,
div[data-testid="stMarkdownContainer"] table.es-table tr,
div[data-testid="stMarkdownContainer"] table.es-table th,
div[data-testid="stMarkdownContainer"] table.es-table td {
    border-left: none !important;
    border-right: none !important;
    border-top: none !important;
}
.es-table thead tr {
    background: #161923;
    border: none !important;
    border-bottom: 1px solid #252a3a !important;
}
.es-table th {
    padding: 11px 11px;
    border: none !important;
    border-bottom: 1px solid #252a3a !important;
    font-size: 10.5px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #8b93a7;
    white-space: nowrap;
    text-align: left;
    vertical-align: middle;
    user-select: none;
}
.es-table th.es-align-right,
.es-table td.es-align-right {
    text-align: right;
}
.es-table th.es-align-center,
.es-table td.es-align-center {
    text-align: center;
}
.es-th-active {
    color: #f8fafc !important;
}
.es-sort-arrow {
    color: #ef4444;
    font-size: 10px;
    margin-left: 4px;
}
.es-info-icon {
    display: inline-block;
    margin-left: 4px;
    color: #5b6378;
    font-size: 11px;
    cursor: help;
}
.es-table tbody tr {
    border: none !important;
    border-bottom: 1px solid #1b1f2b !important;
    transition: background-color 0.12s ease;
}
.es-table tbody tr:last-child {
    border-bottom: none !important;
}
.es-table tbody tr:hover {
    background: #181c27;
}
.es-table td {
    padding: 11px 11px;
    border: none !important;
    vertical-align: middle;
    font-size: 13px;
    white-space: nowrap;
}

/* --- Rank & Position Delta Cells --- */
.es-rank-num {
    font-size: 13px;
    font-weight: 600;
    color: #94a3b8;
}
.es-pos-stack {
    display: flex;
    flex-direction: column;
    align-items: center;
    line-height: 1.2;
    gap: 2px;
}
.es-pos-up {
    font-size: 12px;
    font-weight: 700;
    color: #34d399;
}
.es-pos-down {
    font-size: 12px;
    font-weight: 700;
    color: #f87171;
}
.es-pos-same {
    font-size: 12px;
    font-weight: 600;
    color: #64748b;
}
.es-pos-prev {
    font-size: 10.5px;
    color: #596174;
}

/* --- Channel & Video Identity Cell --- */
.es-entity-cell {
    display: flex;
    align-items: center;
    gap: 12px;
    min-width: 220px;
}
.es-avatar {
    width: 38px;
    height: 38px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12.5px;
    font-weight: 800;
    color: #ffffff;
    flex-shrink: 0;
    letter-spacing: -0.02em;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4);
}
.es-avatar-crimson {
    background: linear-gradient(135deg, #991b1b, #ef4444);
    border: 2px solid #f87171;
}
.es-avatar-amber {
    background: linear-gradient(135deg, #92400e, #f59e0b);
    border: 2px solid #fbbf24;
}
.es-avatar-emerald {
    background: linear-gradient(135deg, #065f46, #10b981);
    border: 2px solid #34d399;
}
.es-avatar-indigo {
    background: linear-gradient(135deg, #3730a3, #6366f1);
    border: 2px solid #818cf8;
}
.es-video-thumb {
    width: 36px;
    height: 28px;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: 700;
    flex-shrink: 0;
}
.es-thumb-long {
    background: rgba(59, 130, 246, 0.16);
    border: 1px solid rgba(59, 130, 246, 0.4);
    color: #60a5fa;
}
.es-thumb-shorts {
    background: rgba(239, 68, 68, 0.16);
    border: 1px solid rgba(239, 68, 68, 0.4);
    color: #f87171;
}
.es-thumb-unknown {
    background: rgba(148, 163, 184, 0.14);
    border: 1px solid rgba(148, 163, 184, 0.3);
    color: #94a3b8;
}
.es-entity-body {
    display: flex;
    flex-direction: column;
    gap: 3px;
    min-width: 0;
}
.es-entity-title-row {
    display: flex;
    align-items: center;
    gap: 6px;
}
.es-entity-name {
    font-size: 13.5px;
    font-weight: 700;
    color: #f8fafc;
    max-width: 290px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.es-ext-link {
    color: #64748b !important;
    text-decoration: none !important;
    font-size: 11.5px;
    line-height: 1;
    transition: color 0.15s ease;
}
.es-ext-link:hover {
    color: #f8fafc !important;
}

/* --- Profile / Tier Badges (inspired by gold ATLETA badge in reference) --- */
.es-tier-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    width: fit-content;
    padding: 1.5px 7px;
    border-radius: 999px;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}
.es-tier-gold {
    background: rgba(245, 158, 11, 0.16);
    border: 1px solid rgba(251, 191, 36, 0.45);
    color: #fbbf24;
}
.es-tier-blue {
    background: rgba(59, 130, 246, 0.15);
    border: 1px solid rgba(96, 165, 250, 0.4);
    color: #60a5fa;
}
.es-tier-crimson {
    background: rgba(239, 68, 68, 0.15);
    border: 1px solid rgba(248, 113, 113, 0.4);
    color: #f87171;
}
.es-tier-purple {
    background: rgba(168, 85, 247, 0.15);
    border: 1px solid rgba(192, 132, 252, 0.4);
    color: #c084fc;
}
.es-tier-muted {
    background: rgba(148, 163, 184, 0.12);
    border: 1px solid rgba(148, 163, 184, 0.28);
    color: #94a3b8;
}
.es-entity-sub {
    font-size: 11.5px;
    color: #7c8599;
    display: flex;
    align-items: center;
    gap: 8px;
}

/* --- Metric Cells, Trend Pills & Sub-Comparisons --- */
.es-metric-stack {
    display: flex;
    flex-direction: column;
    gap: 3px;
}
.es-metric-top {
    display: flex;
    align-items: center;
    gap: 7px;
}
.es-val-strong {
    font-size: 14px;
    font-weight: 700;
    color: #f8fafc;
    letter-spacing: -0.01em;
}
.es-sub-transition {
    font-size: 11.5px;
    font-weight: 500;
    color: #737c91;
}

/* --- Delta / Trend Pills --- */
.es-pill {
    display: inline-flex;
    align-items: center;
    gap: 3px;
    padding: 2px 7px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 700;
    line-height: 1.25;
    white-space: nowrap;
}
.es-pill-up {
    background: rgba(16, 185, 129, 0.16);
    border: 1px solid rgba(52, 211, 153, 0.28);
    color: #34d399;
}
.es-pill-down {
    background: rgba(239, 68, 68, 0.16);
    border: 1px solid rgba(248, 113, 113, 0.28);
    color: #f87171;
}
.es-pill-neutral {
    background: rgba(148, 163, 184, 0.12);
    border: 1px solid rgba(148, 163, 184, 0.22);
    color: #94a3b8;
}

/* --- Engagement Rate Semantic Colors --- */
.es-eng-high {
    font-size: 12px;
    font-weight: 700;
    color: #34d399;
}
.es-eng-mid {
    font-size: 12px;
    font-weight: 700;
    color: #fbbf24;
}
.es-eng-low {
    font-size: 12px;
    font-weight: 700;
    color: #f87171;
}
.es-eng-muted {
    font-size: 12px;
    font-weight: 600;
    color: #64748b;
}

/* --- Two-Line Format Breakdown Columns (Longos / Shorts) --- */
.es-dual-lines {
    display: flex;
    flex-direction: column;
    gap: 3px;
    font-size: 12.5px;
    line-height: 1.3;
}
.es-dual-row {
    color: #8b93a7;
}
.es-dual-avg {
    color: #687083;
    font-size: 11.5px;
}
.es-dual-strong {
    color: #f8fafc;
    font-weight: 700;
}

/* --- Table Footer Summary --- */
.es-table-footer {
    background: #141722;
    border-top: 1px solid #222634;
    padding: 8px 14px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 8px;
    font-size: 11.5px;
    color: #7c8599;
}
</style>
"""


def _compact_html(raw_html: str) -> str:
    """Strips leading per-line indentation so CommonMark never wraps HTML in code blocks."""
    return "\n".join(line.lstrip() for line in raw_html.splitlines() if line.strip())


def inject_dashboard_styles() -> None:
    """Injects the dark analytics UI stylesheet into the current Streamlit page."""
    st.markdown(_compact_html(DASHBOARD_CSS), unsafe_allow_html=True)


def render_context_banner(
    run_id: str,
    period_start: str | None,
    period_end: str | None,
    status: str,
    metrics_version: str = "1.0",
) -> None:
    """Renders the top dark header banner inspired by the YouTube Ranking reference UI."""
    import html

    def _fmt_iso_date(val: str | None) -> str:
        if not val:
            return "—"
        s = str(val)[:10]
        parts = s.split("-")
        if len(parts) == 3:
            return f"{parts[2]}/{parts[1]}/{parts[0]}"
        return html.escape(s)

    p_start = _fmt_iso_date(period_start)
    p_end = _fmt_iso_date(period_end)
    status_upper = (status or "UNKNOWN").upper()
    status_cls = (
        "es-status-completed"
        if status.lower() == "completed"
        else ("es-status-partial" if status.lower() == "partial" else "")
    )

    banner_html = f"""
    <div class="es-header-banner">
        <div class="es-header-left">
            <div class="es-brand-badge">ES</div>
            <div>
                <div class="es-eyebrow">FERRAMENTAS • YOUTUBE COMPETITIVE INTELLIGENCE</div>
                <div class="es-header-title-row">
                    <span class="es-header-title">YouTube Ranking</span>
                    <span class="es-header-period">— {p_start} → {p_end}</span>
                </div>
            </div>
        </div>
        <div class="es-header-right">
            <span class="es-meta-chip">Run: <strong>{html.escape(run_id)}</strong></span>
            <span class="es-meta-chip {status_cls}">{html.escape(status_upper)}</span>
            <span class="es-meta-chip">Engine v{html.escape(str(metrics_version))}</span>
        </div>
    </div>
    """
    st.markdown(_compact_html(banner_html), unsafe_allow_html=True)
