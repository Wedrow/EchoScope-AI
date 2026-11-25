"""Testes reais de persistencia em arquivo SQLite com conexoes independentes (P1)."""

import sqlite3
from contextlib import closing
from datetime import UTC, date, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from echoscope.api.youtube_client import ResolvedChannel, YouTubeClient
from echoscope.database.connection import get_db_connection, transaction
from echoscope.database.migrations import init_schema
from echoscope.database.models import AnalysisRun, Channel, Video, VideoSnapshot
from echoscope.database.repository import EchoScopeRepository
from echoscope.services.pipeline_service import PipelineService


def _make_stub_youtube() -> YouTubeClient:
    mock = MagicMock(spec=YouTubeClient)
    mock.quota_units_used = 15
    mock.resolve_channel.return_value = ResolvedChannel(
        channel_id="UC_PERSIST_01",
        handle="@persist_ch",
        title="Persistence Channel",
        uploads_playlist_id="UU_PERSIST_01",
        subscribers_count=42000,
        is_artist_channel=False,
    )
    mock.fetch_channel_videos_for_period.return_value = (
        [
            Video(
                video_id="vid_persist_1",
                channel_id="UC_PERSIST_01",
                title="Persisted Video",
                published_at=datetime(2026, 2, 1, tzinfo=UTC),
                duration_seconds=420,
            )
        ],
        [
            VideoSnapshot(
                run_id="run_placeholder",
                channel_id="UC_PERSIST_01",
                video_id="vid_persist_1",
                views_count=12345,
                likes_count=500,
                format_category="Long-form",
                classification_method="duration_and_date",
                classification_evidence=">180s",
                collected_at=datetime.now(UTC),
            )
        ],
    )
    return mock


@pytest.mark.persistence
def test_pipeline_collection_persists_across_independent_connections(tmp_path: Path) -> None:
    """Conexao A grava via PipelineService sem commit artificial no teste; Conexao B comprova."""
    db_file = tmp_path / "echo_persist.db"

    # Conexao A: executa fluxo real de criacao e coleta e fecha conexao
    yt = _make_stub_youtube()

    def _fix_run_id_fetch(channel, start_date, end_date, run_id, max_pages=25):
        vid = Video(
            video_id="vid_persist_1",
            channel_id=channel.channel_id,
            title="Persisted Video",
            published_at=datetime(2026, 2, 1, tzinfo=UTC),
            duration_seconds=420,
        )
        snap = VideoSnapshot(
            run_id=run_id,
            channel_id=channel.channel_id,
            video_id=vid.video_id,
            views_count=12345,
            likes_count=500,
            format_category="Long-form",
            classification_method="duration_and_date",
            classification_evidence=">180s",
            collected_at=datetime.now(UTC),
        )
        return [vid], [snap]

    yt.fetch_channel_videos_for_period.side_effect = _fix_run_id_fetch  # type: ignore[method-assign]

    svc_a = PipelineService(db_path=db_file, youtube_client=yt)
    try:
        run_id = svc_a.create_analysis_run(date(2026, 2, 1), date(2026, 2, 10))
        summary = svc_a.collect_channels(run_id, ["@persist_ch"])
        assert summary["status"] == "completed"
    finally:
        svc_a.conn.close()

    # Conexao B: abre nova sessao limpa no mesmo arquivo SQLite
    svc_b = PipelineService(db_path=db_file)
    try:
        overview = svc_b.get_run_overview(run_id)
        assert overview["run"]["run_id"] == run_id
        assert overview["run"]["status"] == "completed"
        assert len(overview["metrics"]) == 1
        assert overview["metrics"][0].channel_id == "UC_PERSIST_01"
        assert overview["metrics"][0].total_views == 12345
    finally:
        svc_b.conn.close()

    with closing(sqlite3.connect(db_file)) as raw_b:
        v_count = raw_b.execute(
            "SELECT COUNT(*) FROM video_snapshots WHERE run_id = ?", (run_id,)
        ).fetchone()[0]
        assert v_count == 1


@pytest.mark.persistence
def test_repository_batch_rollback_prevents_partial_writes(tmp_path: Path) -> None:
    """Falha na gravacao de snapshots nao deixa videos ou contadores parciais persistidos."""
    db_file = tmp_path / "echo_rollback.db"

    with closing(get_db_connection(db_file)) as setup_conn:
        init_schema(setup_conn)
        repo_setup = EchoScopeRepository(setup_conn)
        repo_setup.create_run(
            AnalysisRun(
                run_id="run_atomic_check",
                period_start=date(2026, 2, 1),
                period_end=date(2026, 2, 5),
                status="running",
            )
        )
        repo_setup.associate_channel_run(
            "run_atomic_check",
            Channel(channel_id="UC_ATOM", handle="@atom", title="Atom Channel"),
            status="pending",
        )

    # Tentativa atomica onde video e valido mas snapshot viola CHECK constraint
    with pytest.raises(sqlite3.IntegrityError), transaction(db_file) as tx_conn:
        repo_tx = EchoScopeRepository(tx_conn)
        bad_snap = VideoSnapshot(
            run_id="run_atomic_check",
            channel_id="UC_ATOM",
            video_id="vid_partial_1",
            views_count=100,
            format_category="INVALID_FORMAT",  # type: ignore[arg-type]
        )
        repo_tx.save_video_batch(
            "run_atomic_check",
            "UC_ATOM",
            [
                Video(
                    video_id="vid_partial_1",
                    channel_id="UC_ATOM",
                    title="Should Rollback",
                    published_at=datetime(2026, 2, 2, tzinfo=UTC),
                    duration_seconds=300,
                )
            ],
            [bad_snap],
        )

    # Conexao B independente confirma ausencia total de gravacoes parciais
    with closing(sqlite3.connect(db_file)) as verify_conn:
        videos_count = verify_conn.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
        snaps_count = verify_conn.execute("SELECT COUNT(*) FROM video_snapshots").fetchone()[0]
        arc_row = verify_conn.execute(
            "SELECT status, videos_collected FROM analysis_run_channels "
            "WHERE run_id = 'run_atomic_check' AND channel_id = 'UC_ATOM'"
        ).fetchone()
        assert videos_count == 0
        assert snaps_count == 0
        assert arc_row == ("pending", 0)
