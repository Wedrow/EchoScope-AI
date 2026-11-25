"""Unit tests for UI table formatters, view-models, and HTML renderers."""

from __future__ import annotations

import pandas as pd

from echoscope.analytics.growth import VideoGrowthItem
from echoscope.analytics.metrics import ChannelSummaryMetrics, FormatBreakdown
from ui.components.styles import _compact_html
from ui.components.tables import (
    build_channels_ranking_rows,
    build_videos_catalog_rows,
    classify_channel_tier,
    compute_delta_pct,
    engagement_color_class,
    format_compact_number,
    format_duration,
    format_pct,
    render_channels_table_html,
    render_delta_pill_html,
    render_growth_videos_table_html,
    render_videos_table_html,
)


def test_format_compact_number_scales_and_edge_cases() -> None:
    assert format_compact_number(None) == "—"
    assert format_compact_number(float("nan")) == "—"
    assert format_compact_number(0) == "0"
    assert format_compact_number(42) == "42"
    assert format_compact_number(12.5) == "12,5"
    assert format_compact_number(977_000) == "977K"
    assert format_compact_number(62_100) == "62,1K"
    assert format_compact_number(1_770_000) == "1,77M"
    assert format_compact_number(2_500_000_000) == "2,5B"
    assert format_compact_number(-45_000) == "-45K"


def test_format_pct_and_duration() -> None:
    assert format_pct(None) == "—"
    assert format_pct(0.0, signed=True) == "0%"
    assert format_pct(6.36) == "6,36%"
    assert format_pct(14.0, signed=True) == "+14%"
    assert format_pct(730.2, signed=True) == "+730%"
    assert format_pct(-43.0, signed=True) == "-43%"

    assert format_duration(None) == "—"
    assert format_duration(58) == "0:58"
    assert format_duration(1200) == "20:00"
    assert format_duration(3665) == "1:01:05"


def test_compute_delta_and_pills_and_engagement_classes() -> None:
    assert compute_delta_pct(100, None) is None
    assert compute_delta_pct(0, 0) == 0.0
    assert compute_delta_pct(50, 0) == 100.0
    assert compute_delta_pct(150, 100) == 50.0
    assert compute_delta_pct(50, 100) == -50.0

    assert "es-pill-up" in render_delta_pill_html(25.0)
    assert "es-pill-down" in render_delta_pill_html(-12.5)
    assert "es-pill-neutral" in render_delta_pill_html(0.0)
    assert "VSR" in render_delta_pill_html(None, neutral_label="VSR 0,40x")
    assert render_delta_pill_html(None) == ""

    assert engagement_color_class(None) == "es-eng-muted"
    assert engagement_color_class(5.8) == "es-eng-high"
    assert engagement_color_class(3.4) == "es-eng-mid"
    assert engagement_color_class(1.1) == "es-eng-low"


def test_classify_channel_tier_branches() -> None:
    assert classify_channel_tier(1, 0, 0, 0, 0)[1] == "es-tier-muted"
    assert classify_channel_tier(1, 1000, 200, 800, 5)[1] == "es-tier-gold"
    assert classify_channel_tier(2, 1000, 700, 300, 5)[1] == "es-tier-crimson"
    assert classify_channel_tier(2, 1000, 100, 900, 5)[1] == "es-tier-blue"
    assert classify_channel_tier(3, 1000, 450, 550, 5)[1] == "es-tier-purple"


def test_build_and_render_channels_ranking_with_and_without_baseline() -> None:
    macro_t1 = pd.DataFrame(
        [
            {
                "channel_id": "UC_1",
                "Channel": "@alpha",
                "Subs": 1_200_000,
                "Videos_Published": 4,
                "Total_Views": 2_000_000,
                "Long_Views": 1_500_000,
                "Shorts_Views": 500_000,
                "Unknown_Views": 0,
                "Total_Likes": 120_000,
            },
            {
                "channel_id": "UC_2",
                "Channel": "beta_raw",
                "Subs": None,
                "Videos_Published": 2,
                "Total_Views": 800_000,
                "Long_Views": 100_000,
                "Shorts_Views": 700_000,
                "Unknown_Views": 0,
                "Total_Likes": 10_000,
            },
        ]
    )
    macro_t0 = pd.DataFrame(
        [
            {
                "channel_id": "UC_2",
                "Channel": "beta_raw",
                "Subs": None,
                "Videos_Published": 2,
                "Total_Views": 900_000,
                "Long_Views": 200_000,
                "Shorts_Views": 700_000,
                "Unknown_Views": 0,
                "Total_Likes": 12_000,
            },
            {
                "channel_id": "UC_1",
                "Channel": "@alpha",
                "Subs": 1_100_000,
                "Videos_Published": 2,
                "Total_Views": 500_000,
                "Long_Views": 500_000,
                "Shorts_Views": 0,
                "Unknown_Views": 0,
                "Total_Likes": 30_000,
            },
        ]
    )
    metrics_t1 = [
        ChannelSummaryMetrics(
            channel_id="UC_1",
            handle="@alpha",
            sample_size_videos=4,
            total_views=2_000_000,
            average_views=500_000.0,
            median_views=450_000.0,
            p25_views=300_000.0,
            p75_views=600_000.0,
            views_to_subscribers_ratio=1.67,
            likes_to_views_ratio_pct=6.0,
            likes_sample_size_videos=4,
            upload_frequency_per_week=1.0,
            average_views_per_day=20_000.0,
            median_views_per_day=18_000.0,
            format_breakdown=FormatBreakdown(
                shorts_count=1,
                long_form_count=2,
                unknown_count=1,
                shorts_views=500_000,
                long_form_views=1_500_000,
                unknown_views=0,
            ),
        )
    ]

    # With baseline comparison (rank swap + deltas)
    rows = build_channels_ranking_rows(
        macro_df=macro_t1,
        metrics_list=metrics_t1,
        channel_details=[{"channel_id": "UC_1", "handle": "@alpha", "title": "Alpha <Channel>"}],
        baseline_macro_df=macro_t0,
    )
    assert len(rows) == 2
    html_with_base = render_channels_table_html(
        rows=rows,
        active_sort_col="total_views",
        descending=True,
        baseline_label="demo_t0",
    )
    assert "Alpha &lt;Channel&gt;" in html_with_base
    assert "500K → 2M" in html_with_base
    assert "demo_t0" in html_with_base
    assert "Outros:" in html_with_base

    # Without baseline comparison
    rows_single = build_channels_ranking_rows(macro_df=macro_t1)
    html_single = render_channels_table_html(rows=rows_single, descending=False)
    assert "Snapshot isolado" in html_single
    assert "▲" in html_single


def test_build_and_render_videos_and_growth_tables() -> None:
    assert build_channels_ranking_rows(pd.DataFrame()) == []
    assert build_videos_catalog_rows(pd.DataFrame()) == []
    assert _compact_html("   <div>ok</div>\n\n  ") == "<div>ok</div>"

    vids_df = pd.DataFrame(
        [
            {
                "video_id": "v1",
                "title": "Big <Video>",
                "category": "Long-form",
                "views": 1_000_000,
                "likes": 60_000,
                "duration_seconds": 900,
                "date": "2026-10-15T12:00:00Z",
                "classification_evidence": "duration>60s",
            },
            {
                "video_id": "v2",
                "title": "Quick Short",
                "category": "Shorts",
                "views": 200_000,
                "likes": None,
                "duration_seconds": 45,
                "date": "2026-10-20",
                "classification_evidence": "duration<=60s",
            },
            {
                "video_id": "",
                "title": "Mystery Clip",
                "category": "Unknown",
                "views": 0,
                "likes": 0,
                "duration_seconds": 0,
                "date": "",
                "classification_evidence": "",
            },
        ]
    )
    v_rows = build_videos_catalog_rows(vids_df)
    v_html = render_videos_table_html(
        v_rows,
        visible_columns=["format", "views", "engagement", "duration", "published", "evidence"],
    )
    assert "Big &lt;Video&gt;" in v_html
    assert "15/10/2026" in v_html
    assert "👍 Oculto" in v_html

    growth_items = [
        VideoGrowthItem(
            video_id="g1",
            title="Growing Hit",
            views_t0=400_000,
            views_t1=1_000_000,
            delta_views=600_000,
            daily_velocity=60_000.0,
            is_negative_adjustment=False,
        ),
        VideoGrowthItem(
            video_id="g2",
            title="Audit Drop",
            views_t0=100_000,
            views_t1=95_000,
            delta_views=-5_000,
            daily_velocity=-500.0,
            is_negative_adjustment=True,
        ),
        VideoGrowthItem(
            video_id="g3",
            title="Flat Video",
            views_t0=50_000,
            views_t1=50_000,
            delta_views=0,
            daily_velocity=0.0,
            is_negative_adjustment=False,
        ),
    ]
    g_html = render_growth_videos_table_html(growth_items)
    assert "400K → 1M" in g_html
    assert "AJUSTE NEGATIVO" in g_html
    assert "TRAÇÃO POSITIVA" in g_html
    assert "ESTÁVEL" in g_html
