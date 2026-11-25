"""High-density dark-mode analytical tables with sorting, filtering, and trend pills."""

from __future__ import annotations

import html
import math
from typing import Any

import pandas as pd
import streamlit as st

from echoscope.analytics.growth import VideoGrowthItem
from echoscope.analytics.metrics import ChannelSummaryMetrics
from ui.components.styles import _compact_html, inject_dashboard_styles

AVATAR_VARIANTS = (
    "es-avatar-crimson",
    "es-avatar-amber",
    "es-avatar-emerald",
    "es-avatar-indigo",
)


def _is_missing(val: Any) -> bool:
    if val is None:
        return True
    if isinstance(val, float) and math.isnan(val):
        return True
    return str(val).strip().lower() in ("", "none", "nan", "<na>")


def format_compact_number(value: float | int | None, decimals: int = 1) -> str:
    """Formats numeric counts using compact K/M/B notation and comma decimal separator."""
    if _is_missing(value):
        return "—"
    num = float(value)  # type: ignore[arg-type]
    sign = "-" if num < 0 else ""
    abs_num = abs(num)

    if abs_num >= 1_000_000_000:
        scaled, suffix = abs_num / 1_000_000_000, "B"
    elif abs_num >= 1_000_000:
        scaled, suffix = abs_num / 1_000_000, "M"
    elif abs_num >= 1_000:
        scaled, suffix = abs_num / 1_000, "K"
    else:
        if abs_num.is_integer():
            return f"{sign}{int(abs_num)}"
        formatted_small = f"{abs_num:.{decimals}f}".rstrip("0").rstrip(".").replace(".", ",")
        return f"{sign}{formatted_small}"

    precision = 2 if scaled < 10 and decimals >= 1 else (1 if scaled < 100 and decimals >= 1 else 0)
    raw = f"{scaled:.{precision}f}"
    if "." in raw:
        raw = raw.rstrip("0").rstrip(".")
    return f"{sign}{raw.replace('.', ',')}{suffix}"


def format_pct(value: float | None, signed: bool = False) -> str:
    """Formats percentage values with comma decimal separator."""
    if _is_missing(value):
        return "—"
    num = float(value)  # type: ignore[arg-type]
    prefix = "+" if signed and num > 0 else ""
    abs_num = abs(num)
    if abs_num >= 100 or abs_num == 0:
        formatted = f"{num:.0f}"
    elif abs_num >= 10:
        formatted = f"{num:.1f}".rstrip("0").rstrip(".")
    else:
        formatted = f"{num:.2f}".rstrip("0").rstrip(".")
    return f"{prefix}{formatted.replace('.', ',')}%"


def format_duration(seconds: int | float | None) -> str:
    """Formats duration in seconds into H:MM:SS or M:SS."""
    if _is_missing(seconds):
        return "—"
    total = max(0, int(float(seconds)))  # type: ignore[arg-type]
    hrs, rem = divmod(total, 3600)
    mins, secs = divmod(rem, 60)
    if hrs > 0:
        return f"{hrs}:{mins:02d}:{secs:02d}"
    return f"{mins}:{secs:02d}"


def compute_delta_pct(current: float | int, previous: float | int | None) -> float | None:
    """Computes relative percentage variation from previous to current."""
    if _is_missing(previous):
        return None
    prev = float(previous)  # type: ignore[arg-type]
    curr = float(current)
    if prev == 0:
        return 0.0 if curr == 0 else 100.0
    return round(((curr - prev) / abs(prev)) * 100.0, 2)


def render_delta_pill_html(delta_pct: float | None, neutral_label: str | None = None) -> str:
    """Builds HTML pill badge for positive, negative, or neutral variations."""
    if delta_pct is None:
        if neutral_label:
            return f'<span class="es-pill es-pill-neutral">{html.escape(neutral_label)}</span>'
        return ""
    if delta_pct > 0:
        return f'<span class="es-pill es-pill-up">↑ {format_pct(delta_pct, signed=True)}</span>'
    if delta_pct < 0:
        return f'<span class="es-pill es-pill-down">↓ {format_pct(delta_pct, signed=True)}</span>'
    return '<span class="es-pill es-pill-neutral">— 0%</span>'


def engagement_color_class(rate_pct: float | None) -> str:
    """Maps likes-to-views engagement rate to semantic color class."""
    if _is_missing(rate_pct):
        return "es-eng-muted"
    val = float(rate_pct)  # type: ignore[arg-type]
    if val >= 4.5:
        return "es-eng-high"
    if val >= 2.0:
        return "es-eng-mid"
    return "es-eng-low"


def classify_channel_tier(
    rank: int,
    total_views: int,
    shorts_views: int,
    long_views: int,
    videos_count: int,
) -> tuple[str, str]:
    """Determines deterministic profile badge label and CSS class for a channel row."""
    if videos_count <= 0 or total_views <= 0:
        return ("📭 SEM VÍDEOS", "es-tier-muted")
    if rank == 1:
        return ("🏆 LÍDER", "es-tier-gold")
    shorts_ratio = shorts_views / total_views
    long_ratio = long_views / total_views
    if shorts_ratio >= 0.6:
        return ("⚡ SHORTS", "es-tier-crimson")
    if long_ratio >= 0.7:
        return ("🎬 LONG-FORM", "es-tier-blue")
    return ("⚖️ HÍBRIDO", "es-tier-purple")


def _extract_initials(label: str) -> str:
    cleaned = label.lstrip("@").strip()
    if not cleaned:
        return "YT"
    parts = [p for p in cleaned.replace("_", " ").replace("-", " ").split() if p]
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    return cleaned[:2].upper()


def _channel_youtube_url(handle: str, channel_id: str | None) -> str:
    clean_handle = handle.strip()
    if clean_handle.startswith("@"):
        return f"https://www.youtube.com/{clean_handle}"
    if channel_id and channel_id.startswith("UC"):
        return f"https://www.youtube.com/channel/{channel_id}"
    return f"https://www.youtube.com/@{clean_handle}"


def build_channels_ranking_rows(
    macro_df: pd.DataFrame,
    metrics_list: list[ChannelSummaryMetrics] | None = None,
    channel_details: list[dict[str, Any]] | None = None,
    baseline_macro_df: pd.DataFrame | None = None,
    baseline_metrics_list: list[ChannelSummaryMetrics] | None = None,
) -> list[dict[str, Any]]:
    """Merges macro dataframe, summary metrics, and optional T0 baseline into rich row models."""
    if macro_df.empty:
        return []

    metrics_by_handle = {m.handle: m for m in (metrics_list or [])}
    metrics_by_id = {m.channel_id: m for m in (metrics_list or [])}

    details_by_id = {str(d.get("channel_id", "")): d for d in (channel_details or [])}
    details_by_handle = {str(d.get("handle", "")): d for d in (channel_details or [])}

    base_macro_by_key: dict[str, dict[str, Any]] = {}
    base_rank_by_key: dict[str, int] = {}
    if baseline_macro_df is not None and not baseline_macro_df.empty:
        sorted_base = baseline_macro_df.sort_values(
            by="Total_Views"
            if "Total_Views" in baseline_macro_df.columns
            else baseline_macro_df.columns[0],
            ascending=False,
        )
        for idx, rec in enumerate(sorted_base.to_dict(orient="records"), start=1):
            key = str(rec.get("channel_id") or rec.get("Channel") or "")
            if key:
                base_macro_by_key[key] = rec
                base_rank_by_key[key] = idx
            ch_handle = str(rec.get("Channel") or "")
            if ch_handle and ch_handle not in base_macro_by_key:
                base_macro_by_key[ch_handle] = rec
                base_rank_by_key[ch_handle] = idx

    base_metrics_by_key: dict[str, ChannelSummaryMetrics] = {}
    for bm in baseline_metrics_list or []:
        base_metrics_by_key[bm.channel_id] = bm
        base_metrics_by_key[bm.handle] = bm

    raw_records = macro_df.to_dict(orient="records")
    total_sample_views = sum(int(float(r.get("Total_Views") or 0)) for r in raw_records)

    rows: list[dict[str, Any]] = []

    for i, rec in enumerate(raw_records):
        ch_id = str(rec.get("channel_id") or "")
        handle = str(rec.get("Channel") or ch_id or f"channel_{i + 1}")
        m = metrics_by_id.get(ch_id) or metrics_by_handle.get(handle)
        detail = details_by_id.get(ch_id) or details_by_handle.get(handle) or {}
        title = str(detail.get("title") or handle)

        subs_raw = rec.get("Subs")
        subs = None if _is_missing(subs_raw) else int(float(subs_raw))  # type: ignore[arg-type]

        videos_n = int(rec.get("Videos_Published", m.sample_size_videos if m else 0) or 0)
        total_views = int(rec.get("Total_Views", m.total_views if m else 0) or 0)
        long_views = int(rec.get("Long_Views", m.format_breakdown.long_form_views if m else 0) or 0)
        shorts_views = int(
            rec.get("Shorts_Views", m.format_breakdown.shorts_views if m else 0) or 0
        )
        unknown_views = int(
            rec.get("Unknown_Views", m.format_breakdown.unknown_views if m else 0) or 0
        )
        total_likes = int(rec.get("Total_Likes", 0) or 0)

        if m is not None:
            median_views = float(m.median_views)
            engagement_pct = m.likes_to_views_ratio_pct
            vsr = m.views_to_subscribers_ratio
            upload_freq = float(m.upload_frequency_per_week)
            long_count = int(m.format_breakdown.long_form_count)
            shorts_count = int(m.format_breakdown.shorts_count)
            unknown_count = int(m.format_breakdown.unknown_count)
        else:
            median_views = float(total_views / videos_n) if videos_n > 0 else 0.0
            engagement_pct = (
                round((total_likes / total_views) * 100.0, 2) if total_views > 0 else None
            )
            vsr = round(total_views / subs, 4) if subs and subs > 0 else None
            upload_freq = 0.0
            long_count = 1 if long_views > 0 and shorts_views == 0 else 0
            shorts_count = 1 if shorts_views > 0 and long_views == 0 else 0
            unknown_count = 0

        share_pct = (
            round((total_views / total_sample_views) * 100.0, 1) if total_sample_views > 0 else 0.0
        )

        # Baseline lookup (T0)
        base_rec = base_macro_by_key.get(ch_id) or base_macro_by_key.get(handle)
        base_m = base_metrics_by_key.get(ch_id) or base_metrics_by_key.get(handle)
        prev_rank = base_rank_by_key.get(ch_id) or base_rank_by_key.get(handle)

        prev_total_views = (
            int(base_rec.get("Total_Views", 0) or 0) if base_rec is not None else None
        )
        prev_long_views = int(base_rec.get("Long_Views", 0) or 0) if base_rec is not None else None
        prev_shorts_views = (
            int(base_rec.get("Shorts_Views", 0) or 0) if base_rec is not None else None
        )
        prev_videos_n = (
            int(base_rec.get("Videos_Published", 0) or 0) if base_rec is not None else None
        )
        prev_median_views = float(base_m.median_views) if base_m is not None else None

        avg_long = (long_views / long_count) if long_count > 0 else None
        avg_shorts = (shorts_views / shorts_count) if shorts_count > 0 else None

        rows.append(
            {
                "channel_id": ch_id,
                "handle": handle,
                "title": title,
                "url": _channel_youtube_url(handle, ch_id),
                "avatar_initials": _extract_initials(title or handle),
                "avatar_cls": AVATAR_VARIANTS[i % len(AVATAR_VARIANTS)],
                "subs": subs,
                "videos_n": videos_n,
                "total_views": total_views,
                "median_views": median_views,
                "long_views": long_views,
                "shorts_views": shorts_views,
                "unknown_views": unknown_views,
                "total_likes": total_likes,
                "engagement_pct": engagement_pct,
                "vsr": vsr,
                "upload_freq": upload_freq,
                "share_pct": share_pct,
                "long_count": long_count,
                "shorts_count": shorts_count,
                "unknown_count": unknown_count,
                "avg_long": avg_long,
                "avg_shorts": avg_shorts,
                "prev_rank": prev_rank,
                "prev_total_views": prev_total_views,
                "prev_long_views": prev_long_views,
                "prev_shorts_views": prev_shorts_views,
                "prev_videos_n": prev_videos_n,
                "prev_median_views": prev_median_views,
                "delta_total_pct": compute_delta_pct(total_views, prev_total_views),
                "delta_long_pct": compute_delta_pct(long_views, prev_long_views),
                "delta_shorts_pct": compute_delta_pct(shorts_views, prev_shorts_views),
                "delta_videos_pct": compute_delta_pct(videos_n, prev_videos_n),
                "delta_median_pct": compute_delta_pct(median_views, prev_median_views),
            }
        )

    # Compute baseline natural ranks by Total_Views descending
    by_views = sorted(rows, key=lambda r: r["total_views"], reverse=True)
    for natural_idx, row in enumerate(by_views, start=1):
        row["natural_rank"] = natural_idx
        tier_label, tier_cls = classify_channel_tier(
            rank=natural_idx,
            total_views=row["total_views"],
            shorts_views=row["shorts_views"],
            long_views=row["long_views"],
            videos_count=row["videos_n"],
        )
        row["tier_label"] = tier_label
        row["tier_cls"] = tier_cls
        row["profile_group"] = (
            "Shorts"
            if "SHORTS" in tier_label
            else ("Long-form" if "LONG-FORM" in tier_label else "Híbrido / Geral")
        )

    return rows


CHANNEL_COLUMNS_META: dict[str, tuple[str, str]] = {
    "median_views": (
        "VIEWS MEDIANA",
        "Desempenho típico por vídeo na janela (imune a outliers isolados)",
    ),
    "engagement": (
        "ENGAJAMENTO",
        "Total de likes públicos e taxa ponderada Likes/Views da amostra",
    ),
    "total_views": (
        "VIEWS TOTAIS",
        "Soma de visualizações dos vídeos publicados no período monitorado",
    ),
    "long_views": (
        "VIEWS LONGOS",
        "Visualizações acumuladas em vídeos Long-form (> 60s / formato horizontal)",
    ),
    "shorts_views": (
        "VIEWS SHORTS",
        "Visualizações acumuladas em YouTube Shorts",
    ),
    "videos": (
        "VÍDEOS",
        "Quantidade total de vídeos coletados no período e cadência",
    ),
    "format_counts": (
        "QUANTIDADE LONGOS / SHORTS",
        "Distribuição de uploads por formato de conteúdo",
    ),
    "period_breakdown": (
        "VIEWS PERÍODO",
        "Média de views por vídeo/short e volume por formato no período",
    ),
}

SORT_FIELD_TO_COL: dict[str, tuple[str, str]] = {
    "Views Totais": ("total_views", "total_views"),
    "Views Mediana": ("median_views", "median_views"),
    "Engajamento (%)": ("engagement", "engagement_pct"),
    "Views Longos": ("long_views", "long_views"),
    "Views Shorts": ("shorts_views", "shorts_views"),
    "Vídeos Publicados": ("videos", "videos_n"),
    "Inscritos": ("channel", "subs"),
}


def render_channels_table_html(
    rows: list[dict[str, Any]],
    visible_columns: list[str] | None = None,
    active_sort_col: str = "total_views",
    descending: bool = True,
    baseline_label: str | None = None,
) -> str:
    """Renders pure HTML string for the dark-mode YouTube Channel Ranking table."""
    cols = visible_columns if visible_columns is not None else list(CHANNEL_COLUMNS_META.keys())
    arrow = "▼" if descending else "▲"
    has_baseline = any(r.get("prev_total_views") is not None for r in rows)

    def _th(col_id: str, label: str, tooltip: str = "", extra_cls: str = "") -> str:
        is_active = active_sort_col == col_id
        cls_str = f"{extra_cls} {'es-th-active' if is_active else ''}".strip()
        cls_attr = f' class="{cls_str}"' if cls_str else ""
        sort_html = f'<span class="es-sort-arrow">{arrow}</span>' if is_active else ""
        info_html = (
            f'<span class="es-info-icon" title="{html.escape(tooltip)}">ⓘ</span>' if tooltip else ""
        )
        return f"<th{cls_attr}>{html.escape(label)}{sort_html}{info_html}</th>"

    headers = [
        '<th class="es-align-center">#</th>',
        '<th class="es-align-center" title="Variação de posição no ranking">⇅</th>',
        _th("channel", "CANAL", "Canal monitorado, perfil de formato, inscritos e vídeos"),
    ]
    for c_key in cols:
        if c_key in CHANNEL_COLUMNS_META:
            c_label, c_tip = CHANNEL_COLUMNS_META[c_key]
            headers.append(_th(c_key, c_label, c_tip))

    body_rows: list[str] = []
    for display_idx, r in enumerate(rows, start=1):
        rank_num = r.get("natural_rank", display_idx)
        prev_rank = r.get("prev_rank")

        if prev_rank is not None:
            diff = prev_rank - rank_num
            if diff > 0:
                pos_html = (
                    f'<div class="es-pos-stack">'
                    f'<span class="es-pos-up">▲ {diff}</span>'
                    f'<span class="es-pos-prev">#{prev_rank}</span></div>'
                )
            elif diff < 0:
                pos_html = (
                    f'<div class="es-pos-stack">'
                    f'<span class="es-pos-down">▼ {abs(diff)}</span>'
                    f'<span class="es-pos-prev">#{prev_rank}</span></div>'
                )
            else:
                pos_html = (
                    f'<div class="es-pos-stack">'
                    f'<span class="es-pos-same">= 0</span>'
                    f'<span class="es-pos-prev">#{prev_rank}</span></div>'
                )
        else:
            pos_html = (
                f'<div class="es-pos-stack">'
                f'<span class="es-pos-same">•</span>'
                f'<span class="es-pos-prev">#{rank_num}</span></div>'
            )

        subs_txt = format_compact_number(r["subs"]) if r["subs"] is not None else "Oculto"
        display_name = html.escape(r["title"])
        handle_sub = (
            f"<span>{html.escape(r['handle'])}</span>"
            if r["handle"].lower() != r["title"].lower()
            else ""
        )

        channel_cell = (
            f'<div class="es-entity-cell">'
            f'<div class="es-avatar {r["avatar_cls"]}">{html.escape(r["avatar_initials"])}</div>'
            f'<div class="es-entity-body">'
            f'<div class="es-entity-title-row">'
            f'<span class="es-entity-name" title="{display_name}">{display_name}</span>'
            f'<a class="es-ext-link" href="{html.escape(r["url"])}" target="_blank" rel="noopener noreferrer" title="Abrir canal no YouTube">↗</a>'
            f"</div>"
            f'<span class="es-tier-badge {r["tier_cls"]}">{html.escape(r["tier_label"])}</span>'
            f'<div class="es-entity-sub">'
            f'<span title="Inscritos">👥 {subs_txt}</span>'
            f'<span title="Vídeos analisados">🎬 {r["videos_n"]}</span>'
            f"{handle_sub}"
            f"</div>"
            f"</div>"
            f"</div>"
        )

        cells = [
            f'<td class="es-align-center"><span class="es-rank-num">{display_idx}</span></td>',
            f'<td class="es-align-center">{pos_html}</td>',
            f"<td>{channel_cell}</td>",
        ]

        for c_key in cols:
            if c_key == "median_views":
                med_str = format_compact_number(r["median_views"])
                vsr_label = (
                    f"VSR {r['vsr']:.2f}x".replace(".", ",") if r["vsr"] is not None else None
                )
                pill = render_delta_pill_html(r["delta_median_pct"], neutral_label=vsr_label)
                sub_line = (
                    f"{format_compact_number(r['prev_median_views'])} → {med_str}"
                    if r["prev_median_views"] is not None
                    else (vsr_label or "Mediana por upload")
                )
                cells.append(
                    f'<td><div class="es-metric-stack">'
                    f'<div class="es-metric-top"><span class="es-val-strong">{med_str}</span>{pill}</div>'
                    f'<span class="es-sub-transition">{html.escape(sub_line)}</span>'
                    f"</div></td>"
                )
            elif c_key == "engagement":
                likes_str = format_compact_number(r["total_likes"])
                eng_cls = engagement_color_class(r["engagement_pct"])
                eng_str = format_pct(r["engagement_pct"])
                cells.append(
                    f'<td><div class="es-metric-stack">'
                    f'<div class="es-metric-top"><span class="es-val-strong">👍 {likes_str}</span></div>'
                    f'<span class="{eng_cls}">{eng_str}</span>'
                    f"</div></td>"
                )
            elif c_key == "total_views":
                tot_str = format_compact_number(r["total_views"])
                share_lbl = f"{format_pct(r['share_pct'])} share"
                pill = render_delta_pill_html(r["delta_total_pct"], neutral_label=share_lbl)
                sub_line = (
                    f"{format_compact_number(r['prev_total_views'])} → {tot_str}"
                    if r["prev_total_views"] is not None
                    else f"Participação: {format_pct(r['share_pct'])}"
                )
                cells.append(
                    f'<td><div class="es-metric-stack">'
                    f'<div class="es-metric-top"><span class="es-val-strong">{tot_str}</span>{pill}</div>'
                    f'<span class="es-sub-transition">{html.escape(sub_line)}</span>'
                    f"</div></td>"
                )
            elif c_key == "long_views":
                lv_str = format_compact_number(r["long_views"])
                lv_share = (
                    format_pct((r["long_views"] / r["total_views"]) * 100.0)
                    if r["total_views"] > 0
                    else "0%"
                )
                pill = render_delta_pill_html(r["delta_long_pct"], neutral_label=lv_share)
                sub_line = (
                    f"{format_compact_number(r['prev_long_views'])} → {lv_str}"
                    if r["prev_long_views"] is not None
                    else f"{lv_share} das views"
                )
                cells.append(
                    f'<td><div class="es-metric-stack">'
                    f'<div class="es-metric-top"><span class="es-val-strong">{lv_str}</span>{pill}</div>'
                    f'<span class="es-sub-transition">{html.escape(sub_line)}</span>'
                    f"</div></td>"
                )
            elif c_key == "shorts_views":
                sv_str = format_compact_number(r["shorts_views"])
                sv_share = (
                    format_pct((r["shorts_views"] / r["total_views"]) * 100.0)
                    if r["total_views"] > 0
                    else "0%"
                )
                pill = render_delta_pill_html(r["delta_shorts_pct"], neutral_label=sv_share)
                sub_line = (
                    f"{format_compact_number(r['prev_shorts_views'])} → {sv_str}"
                    if r["prev_shorts_views"] is not None
                    else f"{sv_share} das views"
                )
                cells.append(
                    f'<td><div class="es-metric-stack">'
                    f'<div class="es-metric-top"><span class="es-val-strong">{sv_str}</span>{pill}</div>'
                    f'<span class="es-sub-transition">{html.escape(sub_line)}</span>'
                    f"</div></td>"
                )
            elif c_key == "videos":
                v_str = str(r["videos_n"])
                cadence_lbl = f"{r['upload_freq']:.1f}/sem".replace(".", ",")
                pill = render_delta_pill_html(r["delta_videos_pct"], neutral_label=cadence_lbl)
                sub_line = (
                    f"{r['prev_videos_n']} → {v_str}"
                    if r["prev_videos_n"] is not None
                    else f"Cadência: {cadence_lbl}"
                )
                cells.append(
                    f'<td><div class="es-metric-stack">'
                    f'<div class="es-metric-top"><span class="es-val-strong">{v_str}</span>{pill}</div>'
                    f'<span class="es-sub-transition">{html.escape(sub_line)}</span>'
                    f"</div></td>"
                )
            elif c_key == "format_counts":
                extra_unk = (
                    f'<span class="es-dual-row">Outros: <span class="es-dual-strong">{r["unknown_count"]}</span></span>'
                    if r["unknown_count"] > 0
                    else ""
                )
                cells.append(
                    f'<td><div class="es-dual-lines">'
                    f'<span class="es-dual-row">Longos: <span class="es-dual-strong">{r["long_count"]}</span></span>'
                    f'<span class="es-dual-row">Shorts: <span class="es-dual-strong">{r["shorts_count"]}</span></span>'
                    f"{extra_unk}"
                    f"</div></td>"
                )
            elif c_key == "period_breakdown":
                avg_l_txt = (
                    f"{format_compact_number(r['avg_long'])}/vídeo"
                    if r["avg_long"] is not None
                    else "--/vídeo"
                )
                avg_s_txt = (
                    f"{format_compact_number(r['avg_shorts'])}/short"
                    if r["avg_shorts"] is not None
                    else "--/short"
                )
                cells.append(
                    f'<td><div class="es-dual-lines">'
                    f'<span class="es-dual-row">Longos: <span class="es-dual-avg">({avg_l_txt})</span> <span class="es-dual-strong">{format_compact_number(r["long_views"])}</span></span>'
                    f'<span class="es-dual-row">Shorts: <span class="es-dual-avg">({avg_s_txt})</span> <span class="es-dual-strong">{format_compact_number(r["shorts_views"])}</span></span>'
                    f"</div></td>"
                )

        body_rows.append(f"<tr>{''.join(cells)}</tr>")

    footer_right = (
        f"Comparado contra baseline: <strong>{html.escape(baseline_label)}</strong>"
        if has_baseline and baseline_label
        else "Snapshot isolado • Passe o mouse nos ícones ⓘ para detalhes metodológicos"
    )
    table_html = f"""
    <div class="es-table-shell">
        <div class="es-table-scroll">
            <table class="es-table">
                <thead><tr>{"".join(headers)}</tr></thead>
                <tbody>{"".join(body_rows)}</tbody>
            </table>
        </div>
        <div class="es-table-footer">
            <span>Exibindo <strong>{len(rows)}</strong> {"canal" if len(rows) == 1 else "canais"} no ranking</span>
            <span>{footer_right}</span>
        </div>
    </div>
    """
    return _compact_html(table_html)


def render_channels_table(
    macro_df: pd.DataFrame,
    metrics_list: list[ChannelSummaryMetrics] | None = None,
    channel_details: list[dict[str, Any]] | None = None,
    baseline_macro_df: pd.DataFrame | None = None,
    baseline_metrics_list: list[ChannelSummaryMetrics] | None = None,
    baseline_label: str | None = None,
    key_prefix: str = "channels_ranking",
) -> None:
    """Renders interactive YouTube Channel Ranking UI with filters, hidden columns, and trend badges."""
    if macro_df.empty:
        st.info("No channels recorded in this execution run.")
        return

    inject_dashboard_styles()

    rows = build_channels_ranking_rows(
        macro_df=macro_df,
        metrics_list=metrics_list,
        channel_details=channel_details,
        baseline_macro_df=baseline_macro_df,
        baseline_metrics_list=baseline_metrics_list,
    )

    all_col_keys = list(CHANNEL_COLUMNS_META.keys())
    col_labels_to_key = {CHANNEL_COLUMNS_META[k][0]: k for k in all_col_keys}
    all_col_labels = list(col_labels_to_key.keys())

    vis_state_key = f"{key_prefix}_visible_cols"
    if vis_state_key not in st.session_state:
        st.session_state[vis_state_key] = list(all_col_labels)

    # 1. Collapsible Filter & Sort Bar
    with st.expander("🌪️ Filtros & Ordenação", expanded=False):
        f_col1, f_col2, f_col3, f_col4 = st.columns([2.2, 1.6, 1.2, 1.4])
        with f_col1:
            search_query = st.text_input(
                "Buscar canal:",
                value="",
                placeholder="Digite nome ou @handle...",
                key=f"{key_prefix}_search",
            )
        with f_col2:
            sort_choice = st.selectbox(
                "Ordenar por:",
                list(SORT_FIELD_TO_COL.keys()),
                index=0,
                key=f"{key_prefix}_sort_by",
            )
        with f_col3:
            sort_dir = st.selectbox(
                "Direção:",
                ["Decrescente ▼", "Crescente ▲"],
                index=0,
                key=f"{key_prefix}_sort_dir",
            )
        with f_col4:
            profile_filter = st.selectbox(
                "Perfil de Formato:",
                ["Todos", "Long-form", "Shorts", "Híbrido / Geral"],
                index=0,
                key=f"{key_prefix}_profile",
            )

    # 2. Collapsible Hidden Columns Bar (matching "Colunas Ocultas (N)" in reference UI)
    current_visible_labels: list[str] = st.session_state.get(vis_state_key, all_col_labels)
    hidden_labels = [lbl for lbl in all_col_labels if lbl not in current_visible_labels]

    with st.expander(
        f"👁️ Colunas Ocultas ({len(hidden_labels)})",
        expanded=len(hidden_labels) > 0,
    ):
        if hidden_labels:
            chips_html = "".join(
                f'<span class="es-hidden-chip">👁️ {html.escape(lbl)}</span>' for lbl in hidden_labels
            )
            st.markdown(
                _compact_html(f'<div class="es-hidden-bar">{chips_html}</div>'),
                unsafe_allow_html=True,
            )

        hc_col1, hc_col2 = st.columns([4, 1])
        with hc_col1:
            selected_labels = st.multiselect(
                "Colunas visíveis na tabela:",
                options=all_col_labels,
                key=vis_state_key,
            )
        with hc_col2:
            if hidden_labels:
                st.button(
                    "👁️ Mostrar Todas",
                    key=f"{key_prefix}_show_all",
                    use_container_width=True,
                    on_click=st.session_state.__setitem__,
                    args=(vis_state_key, list(all_col_labels)),
                )

    visible_keys = [col_labels_to_key[lbl] for lbl in selected_labels if lbl in col_labels_to_key]
    if not visible_keys:
        visible_keys = all_col_keys

    # Apply Filtering
    filtered = rows
    if search_query.strip():
        q = search_query.strip().lower()
        filtered = [r for r in filtered if q in r["title"].lower() or q in r["handle"].lower()]
    if profile_filter != "Todos":
        filtered = [r for r in filtered if r["profile_group"] == profile_filter]

    if not filtered:
        st.info("Nenhum canal corresponde aos filtros aplicados.")
        return

    # Apply Sorting
    active_col_id, sort_dict_key = SORT_FIELD_TO_COL.get(
        str(sort_choice), ("total_views", "total_views")
    )
    is_desc = "Decrescente" in str(sort_dir)
    filtered.sort(
        key=lambda r: float(r.get(sort_dict_key) or -1.0),
        reverse=is_desc,
    )

    html_out = render_channels_table_html(
        rows=filtered,
        visible_columns=visible_keys,
        active_sort_col=active_col_id,
        descending=is_desc,
        baseline_label=baseline_label,
    )
    st.markdown(html_out, unsafe_allow_html=True)


VIDEO_COLUMNS_META: dict[str, tuple[str, str]] = {
    "format": ("FORMATO", "Classificação de formato (Shorts vs Long-form)"),
    "views": ("VIEWS", "Visualizações totais do vídeo e comparação com a mediana do canal"),
    "engagement": ("ENGAJAMENTO", "Likes públicos e taxa Likes/Views do vídeo"),
    "duration": ("DURAÇÃO", "Duração do vídeo em minutos/segundos"),
    "published": ("PUBLICAÇÃO", "Data de publicação em UTC"),
    "evidence": ("EVIDÊNCIA", "Critério determinístico utilizado na classificação"),
}

VIDEO_SORT_MAP: dict[str, tuple[str, str]] = {
    "Views": ("views", "views_num"),
    "Engajamento (%)": ("engagement", "eng_pct_sort"),
    "Likes": ("engagement", "likes_num"),
    "Duração": ("duration", "duration_num"),
    "Publicação": ("published", "date_str"),
}


def build_videos_catalog_rows(
    videos_df: pd.DataFrame,
    channel_median_views: float | None = None,
) -> list[dict[str, Any]]:
    """Transforms raw channel videos DataFrame into enriched row view-models."""
    if videos_df.empty:
        return []

    records = videos_df.to_dict(orient="records")
    if channel_median_views is None:
        v_vals = [float(r.get("views") or 0) for r in records]
        s_vals = sorted(v_vals)
        mid = len(s_vals) // 2
        channel_median_views = (
            s_vals[mid] if len(s_vals) % 2 == 1 else (s_vals[mid - 1] + s_vals[mid]) / 2.0
        )

    rows: list[dict[str, Any]] = []
    for r in records:
        vid_id = str(r.get("video_id") or "")
        title = str(r.get("title") or "Untitled Video")
        cat = str(r.get("category") or "Unknown")
        views_num = int(float(r.get("views") or 0))

        raw_likes = r.get("likes")
        likes_num = None if _is_missing(raw_likes) else int(float(raw_likes))  # type: ignore[arg-type]
        eng_pct = (
            round((likes_num / views_num) * 100.0, 2)
            if likes_num is not None and views_num > 0
            else None
        )

        dur_raw = r.get("duration_seconds")
        dur_num = 0 if _is_missing(dur_raw) else int(float(dur_raw))  # type: ignore[arg-type]

        raw_date = str(r.get("date") or "")
        date_iso = raw_date[:10] if len(raw_date) >= 10 else raw_date
        parts = date_iso.split("-")
        date_fmt = f"{parts[2]}/{parts[1]}/{parts[0]}" if len(parts) == 3 else (date_iso or "—")

        evidence = str(r.get("classification_evidence") or "duration_and_date")
        vs_median_pct = (
            compute_delta_pct(views_num, channel_median_views)
            if channel_median_views and channel_median_views > 0
            else None
        )

        url = f"https://www.youtube.com/watch?v={vid_id}" if vid_id else "https://www.youtube.com"
        rows.append(
            {
                "video_id": vid_id,
                "title": title,
                "url": url,
                "category": cat,
                "views_num": views_num,
                "likes_num": likes_num if likes_num is not None else -1,
                "likes_display": likes_num,
                "eng_pct": eng_pct,
                "eng_pct_sort": eng_pct if eng_pct is not None else -1.0,
                "duration_num": dur_num,
                "duration_fmt": format_duration(dur_num),
                "date_str": date_iso,
                "date_fmt": date_fmt,
                "evidence": evidence,
                "vs_median_pct": vs_median_pct,
                "median_ref": channel_median_views,
            }
        )
    return rows


def render_videos_table_html(
    rows: list[dict[str, Any]],
    visible_columns: list[str] | None = None,
    active_sort_col: str = "views",
    descending: bool = True,
) -> str:
    """Renders dark-mode HTML table for granular video performance."""
    cols = visible_columns if visible_columns is not None else list(VIDEO_COLUMNS_META.keys())
    arrow = "▼" if descending else "▲"

    headers = [
        '<th class="es-align-center">#</th>',
        "<th>VÍDEO</th>",
    ]
    for c_key in cols:
        if c_key in VIDEO_COLUMNS_META:
            c_label, c_tip = VIDEO_COLUMNS_META[c_key]
            is_act = active_sort_col == c_key
            act_cls = ' class="es-th-active"' if is_act else ""
            sort_html = f'<span class="es-sort-arrow">{arrow}</span>' if is_act else ""
            info_html = f'<span class="es-info-icon" title="{html.escape(c_tip)}">ⓘ</span>'
            headers.append(f"<th{act_cls}>{html.escape(c_label)}{sort_html}{info_html}</th>")

    body_rows: list[str] = []
    for idx, r in enumerate(rows, start=1):
        cat = r["category"]
        if cat == "Shorts":
            thumb_cls, thumb_icon, badge_cls, badge_lbl = (
                "es-thumb-shorts",
                "⚡",
                "es-tier-crimson",
                "📱 Shorts",
            )
        elif cat == "Long-form":
            thumb_cls, thumb_icon, badge_cls, badge_lbl = (
                "es-thumb-long",
                "▶",
                "es-tier-blue",
                "🎬 Long-form",
            )
        else:
            thumb_cls, thumb_icon, badge_cls, badge_lbl = (
                "es-thumb-unknown",
                "?",
                "es-tier-muted",
                "❓ Unknown",
            )

        title_esc = html.escape(r["title"])
        id_sub = f"ID: {html.escape(r['video_id'])}" if r["video_id"] else "Snapshot Video"
        link_html = (
            f'<a class="es-ext-link" href="{html.escape(r["url"])}" target="_blank" rel="noopener noreferrer" title="Assistir no YouTube">↗</a>'
            if r["video_id"]
            else ""
        )
        video_cell = (
            f'<div class="es-entity-cell">'
            f'<div class="es-video-thumb {thumb_cls}">{thumb_icon}</div>'
            f'<div class="es-entity-body">'
            f'<div class="es-entity-title-row">'
            f'<span class="es-entity-name" title="{title_esc}">{title_esc}</span>'
            f"{link_html}"
            f"</div>"
            f'<div class="es-entity-sub"><span>{id_sub}</span></div>'
            f"</div>"
            f"</div>"
        )

        cells = [
            f'<td class="es-align-center"><span class="es-rank-num">{idx}</span></td>',
            f"<td>{video_cell}</td>",
        ]

        for c_key in cols:
            if c_key == "format":
                cells.append(f'<td><span class="es-tier-badge {badge_cls}">{badge_lbl}</span></td>')
            elif c_key == "views":
                v_compact = format_compact_number(r["views_num"])
                pill = render_delta_pill_html(r["vs_median_pct"])
                exact_str = f"{r['views_num']:,}".replace(",", ".") + " views"
                cells.append(
                    f'<td><div class="es-metric-stack">'
                    f'<div class="es-metric-top"><span class="es-val-strong">{v_compact}</span>{pill}</div>'
                    f'<span class="es-sub-transition">{exact_str} (vs mediana)</span>'
                    f"</div></td>"
                )
            elif c_key == "engagement":
                likes_txt = (
                    f"👍 {format_compact_number(r['likes_display'])}"
                    if r["likes_display"] is not None
                    else "👍 Oculto"
                )
                eng_cls = engagement_color_class(r["eng_pct"])
                eng_txt = format_pct(r["eng_pct"])
                cells.append(
                    f'<td><div class="es-metric-stack">'
                    f'<div class="es-metric-top"><span class="es-val-strong">{likes_txt}</span></div>'
                    f'<span class="{eng_cls}">{eng_txt}</span>'
                    f"</div></td>"
                )
            elif c_key == "duration":
                cells.append(
                    f'<td><div class="es-metric-stack">'
                    f'<span class="es-val-strong">{html.escape(r["duration_fmt"])}</span>'
                    f'<span class="es-sub-transition">{r["duration_num"]}s</span>'
                    f"</div></td>"
                )
            elif c_key == "published":
                cells.append(
                    f'<td><span class="es-val-strong">{html.escape(r["date_fmt"])}</span></td>'
                )
            elif c_key == "evidence":
                ev_esc = html.escape(r["evidence"])
                cells.append(f'<td><span class="es-sub-transition">{ev_esc}</span></td>')

        body_rows.append(f"<tr>{''.join(cells)}</tr>")

    table_html = f"""
    <div class="es-table-shell">
        <div class="es-table-scroll">
            <table class="es-table">
                <thead><tr>{"".join(headers)}</tr></thead>
                <tbody>{"".join(body_rows)}</tbody>
            </table>
        </div>
        <div class="es-table-footer">
            <span>Exibindo <strong>{len(rows)}</strong> {"vídeo" if len(rows) == 1 else "vídeos"} no catálogo</span>
            <span>Pílulas comparam cada vídeo contra a mediana do canal</span>
        </div>
    </div>
    """
    return _compact_html(table_html)


def render_videos_table(
    videos_df: pd.DataFrame,
    channel_median_views: float | None = None,
    key_prefix: str = "video_catalog",
) -> None:
    """Renders interactive dark-mode Video Catalog table with search, sort, and column controls."""
    if videos_df.empty:
        st.info("No videos found.")
        return

    inject_dashboard_styles()
    rows = build_videos_catalog_rows(videos_df, channel_median_views=channel_median_views)

    all_keys = list(VIDEO_COLUMNS_META.keys())
    default_keys = ["format", "views", "engagement", "duration", "published"]
    label_to_key = {VIDEO_COLUMNS_META[k][0]: k for k in all_keys}
    all_labels = list(label_to_key.keys())
    default_labels = [VIDEO_COLUMNS_META[k][0] for k in default_keys]

    vis_key = f"{key_prefix}_vis_cols"
    if vis_key not in st.session_state:
        st.session_state[vis_key] = default_labels

    with st.expander("🌪️ Filtros & Ordenação do Catálogo", expanded=False):
        vc1, vc2, vc3 = st.columns([2.4, 1.5, 1.3])
        with vc1:
            v_query = st.text_input(
                "Buscar título do vídeo:",
                value="",
                placeholder="Filtrar por palavra-chave no título...",
                key=f"{key_prefix}_search",
            )
        with vc2:
            v_sort = st.selectbox(
                "Ordenar vídeos por:",
                list(VIDEO_SORT_MAP.keys()),
                index=0,
                key=f"{key_prefix}_sort",
            )
        with vc3:
            v_dir = st.selectbox(
                "Ordem:",
                ["Decrescente ▼", "Crescente ▲"],
                index=0,
                key=f"{key_prefix}_dir",
            )

    curr_labels: list[str] = st.session_state.get(vis_key, default_labels)
    hidden_v_labels = [lbl for lbl in all_labels if lbl not in curr_labels]

    with st.expander(f"👁️ Colunas Ocultas ({len(hidden_v_labels)})", expanded=False):
        if hidden_v_labels:
            chips = "".join(
                f'<span class="es-hidden-chip">👁️ {html.escape(lbl)}</span>'
                for lbl in hidden_v_labels
            )
            st.markdown(
                _compact_html(f'<div class="es-hidden-bar">{chips}</div>'),
                unsafe_allow_html=True,
            )
        h1, h2 = st.columns([4, 1])
        with h1:
            chosen_v_labels = st.multiselect(
                "Colunas visíveis:",
                options=all_labels,
                key=vis_key,
            )
        with h2:
            if hidden_v_labels:
                st.button(
                    "👁️ Mostrar Todas",
                    key=f"{key_prefix}_show_all",
                    use_container_width=True,
                    on_click=st.session_state.__setitem__,
                    args=(vis_key, list(all_labels)),
                )

    visible_v_keys = [label_to_key[lbl] for lbl in chosen_v_labels if lbl in label_to_key]
    if not visible_v_keys:
        visible_v_keys = default_keys

    filtered = rows
    if v_query.strip():
        q = v_query.strip().lower()
        filtered = [r for r in filtered if q in r["title"].lower()]

    if not filtered:
        st.info("Nenhum vídeo corresponde à busca informada.")
        return

    act_col, sort_attr = VIDEO_SORT_MAP.get(str(v_sort), ("views", "views_num"))
    is_desc = "Decrescente" in str(v_dir)
    filtered.sort(key=lambda r: r.get(sort_attr, 0), reverse=is_desc)

    st.markdown(
        render_videos_table_html(
            rows=filtered,
            visible_columns=visible_v_keys,
            active_sort_col=act_col,
            descending=is_desc,
        ),
        unsafe_allow_html=True,
    )


def render_growth_videos_table_html(video_items: list[VideoGrowthItem]) -> str:
    """Renders dark-mode HTML comparison table for inter-snapshot video growth (T0 -> T1)."""
    headers = [
        '<th class="es-align-center">#</th>',
        "<th>VÍDEO COMPARADO (T0 ∩ T1)</th>",
        '<th>VIEWS T1 <span class="es-info-icon" title="Evolução de visualizações entre T0 e T1">ⓘ</span></th>',
        '<th class="es-th-active">SALDO ΔV <span class="es-sort-arrow">▼</span></th>',
        '<th>VELOCIDADE DIÁRIA (R) <span class="es-info-icon" title="Ganho líquido médio por dia entre coletas">ⓘ</span></th>',
        "<th>STATUS</th>",
    ]

    body_rows: list[str] = []
    for idx, item in enumerate(video_items, start=1):
        pct = compute_delta_pct(item.views_t1, item.views_t0)
        pill = render_delta_pill_html(pct)
        t0_fmt = format_compact_number(item.views_t0)
        t1_fmt = format_compact_number(item.views_t1)

        sign_prefix = "+" if item.delta_views > 0 else ""
        delta_compact = f"{sign_prefix}{format_compact_number(item.delta_views)}"
        delta_exact = f"{sign_prefix}{item.delta_views:,}".replace(",", ".")

        vel_compact = f"{format_compact_number(item.daily_velocity)}/dia"
        status_badge = (
            '<span class="es-tier-badge es-tier-crimson">⚠️ AJUSTE NEGATIVO</span>'
            if item.is_negative_adjustment
            else (
                '<span class="es-tier-badge es-tier-gold">🚀 TRAÇÃO POSITIVA</span>'
                if item.delta_views > 0
                else '<span class="es-tier-badge es-tier-muted">⏸️ ESTÁVEL</span>'
            )
        )

        url = f"https://www.youtube.com/watch?v={html.escape(item.video_id)}"
        title_esc = html.escape(item.title)

        body_rows.append(
            f"<tr>"
            f'<td class="es-align-center"><span class="es-rank-num">{idx}</span></td>'
            f'<td><div class="es-entity-cell">'
            f'<div class="es-video-thumb es-thumb-long">▶</div>'
            f'<div class="es-entity-body">'
            f'<div class="es-entity-title-row">'
            f'<span class="es-entity-name" title="{title_esc}">{title_esc}</span>'
            f'<a class="es-ext-link" href="{url}" target="_blank" rel="noopener noreferrer">↗</a>'
            f"</div>"
            f'<div class="es-entity-sub"><span>ID: {html.escape(item.video_id)}</span></div>'
            f"</div></div></td>"
            f'<td><div class="es-metric-stack">'
            f'<div class="es-metric-top"><span class="es-val-strong">{t1_fmt}</span>{pill}</div>'
            f'<span class="es-sub-transition">{t0_fmt} → {t1_fmt}</span>'
            f"</div></td>"
            f'<td><div class="es-metric-stack">'
            f'<span class="es-val-strong">{delta_compact}</span>'
            f'<span class="es-sub-transition">{delta_exact} views</span>'
            f"</div></td>"
            f'<td><span class="es-val-strong">{vel_compact}</span></td>'
            f"<td>{status_badge}</td>"
            f"</tr>"
        )

    html_table = f"""
    <div class="es-table-shell">
        <div class="es-table-scroll">
            <table class="es-table">
                <thead><tr>{"".join(headers)}</tr></thead>
                <tbody>{"".join(body_rows)}</tbody>
            </table>
        </div>
        <div class="es-table-footer">
            <span><strong>{len(video_items)}</strong> {"vídeo comparável" if len(video_items) == 1 else "vídeos comparáveis"} entre T0 e T1</span>
            <span>Ordenado pelo maior ganho líquido de views (ΔV)</span>
        </div>
    </div>
    """
    return _compact_html(html_table)


def render_growth_videos_table(video_items: list[VideoGrowthItem]) -> None:
    """Renders comparative table of identical videos tracked across T0 and T1."""
    if not video_items:
        st.info("Nenhum vídeo em comum encontrado entre os dois snapshots selecionados.")
        return

    inject_dashboard_styles()
    st.markdown(render_growth_videos_table_html(video_items), unsafe_allow_html=True)
