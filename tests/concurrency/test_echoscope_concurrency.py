"""Testes reais de concorrencia SQLite sobre servicos e conexoes do EchoScope AI (P3)."""

import multiprocessing
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from echoscope.database.connection import get_db_connection, transaction
from echoscope.database.migrations import init_schema
from echoscope.database.models import AnalysisRun, Channel, Video, VideoSnapshot
from echoscope.database.repository import EchoScopeRepository
from echoscope.services.pipeline_service import PipelineService


def _init_app_db(db_file: Path) -> None:
    svc = PipelineService(db_path=db_file)
    svc.conn.close()


def _mp_create_run_worker(
    db_path_str: str,
    worker_id: int,
    start_event: object,
    result_queue: object,
) -> None:
    db_file = Path(db_path_str)
    start_event.wait(timeout=15)  # type: ignore[attr-defined]
    try:
        svc = PipelineService(db_path=db_file)
        try:
            run_id = svc.create_analysis_run(date(2026, 2, 1), date(2026, 2, 10))
            result_queue.put(("ok", worker_id, run_id))  # type: ignore[attr-defined]
        finally:
            svc.conn.close()
    except Exception as exc:  # pragma: no cover
        result_queue.put(("err", worker_id, repr(exc)))  # type: ignore[attr-defined]


@pytest.mark.concurrency
def test_app_connections_expose_wal_and_busy_timeout(tmp_path: Path) -> None:
    """Verifica PRAGMAs reais abertos por get_db_connection() da aplicacao."""
    db_file = tmp_path / "echo_pragmas.db"
    _init_app_db(db_file)

    with closing(get_db_connection(db_file)) as app_conn:
        journal = str(app_conn.execute("PRAGMA journal_mode;").fetchone()[0]).lower()
        busy_ms = int(app_conn.execute("PRAGMA busy_timeout;").fetchone()[0])
        fk_on = int(app_conn.execute("PRAGMA foreign_keys;").fetchone()[0])
        assert journal == "wal"
        assert busy_ms == 30000
        assert fk_on == 1


@pytest.mark.concurrency
def test_five_concurrent_services_persist_all_runs_without_loss_or_duplication(
    tmp_path: Path,
) -> None:
    """Cinco threads com PipelineService independentes gravam simultaneamente sem perda/duplicacao."""
    db_file = tmp_path / "echo_5threads.db"
    _init_app_db(db_file)

    workers = 5
    barrier = threading.Barrier(workers)

    def worker(idx: int) -> str:
        svc = PipelineService(db_path=db_file)
        try:
            barrier.wait(timeout=15)
            run_id = svc.create_analysis_run(date(2026, 1, 1), date(2026, 1, 15))
            ch = Channel(
                channel_id=f"UC_CONC_{idx}",
                handle=f"@conc_{idx}",
                title=f"Concurrent Channel {idx}",
            )
            svc.repository.associate_channel_run(run_id, ch, status="pending")
            vid = Video(
                video_id=f"vid_conc_{idx}",
                channel_id=ch.channel_id,
                title=f"Video {idx}",
                published_at=datetime(2026, 1, 5, tzinfo=UTC),
                duration_seconds=300,
            )
            snap = VideoSnapshot(
                run_id=run_id,
                channel_id=ch.channel_id,
                video_id=vid.video_id,
                views_count=1000 + idx,
                format_category="Long-form",
            )
            svc.repository.save_video_batch(run_id, ch.channel_id, [vid], [snap])
            svc.repository.update_run_status(run_id, "completed")
            return run_id
        finally:
            svc.conn.close()

    with ThreadPoolExecutor(max_workers=workers) as pool:
        run_ids = [f.result() for f in [pool.submit(worker, i) for i in range(workers)]]

    assert len(set(run_ids)) == workers

    # Conexao independente comprova 5 execucoes, 5 snapshots e integridade fisica ok
    with closing(sqlite3.connect(db_file)) as verify_conn:
        total_runs = verify_conn.execute("SELECT COUNT(*) FROM analysis_runs").fetchone()[0]
        total_snaps = verify_conn.execute("SELECT COUNT(*) FROM video_snapshots").fetchone()[0]
        integrity = verify_conn.execute("PRAGMA integrity_check;").fetchone()[0].lower()
        assert total_runs == workers
        assert total_snaps == workers
        assert integrity == "ok"


@pytest.mark.concurrency
def test_concurrent_readers_and_failing_writer_rollback_atomically(tmp_path: Path) -> None:
    """Leitores e escritores concorrentes mantem atomicidade e rollback quando um escritor falha."""
    db_file = tmp_path / "echo_rw_rollback.db"
    _init_app_db(db_file)

    with closing(get_db_connection(db_file)) as seed_conn:
        init_schema(seed_conn)
        repo = EchoScopeRepository(seed_conn)
        repo.create_run(
            AnalysisRun(
                run_id="run_seed_base",
                period_start=date(2026, 1, 1),
                period_end=date(2026, 1, 2),
                status="completed",
            )
        )

    barrier = threading.Barrier(5)

    def good_writer(idx: int) -> None:
        barrier.wait(timeout=15)
        with transaction(db_file) as tx:
            r = EchoScopeRepository(tx)
            r.create_run(
                AnalysisRun(
                    run_id=f"run_ok_{idx}",
                    period_start=date(2026, 2, 1),
                    period_end=date(2026, 2, 2),
                    status="completed",
                )
            )

    def failing_writer() -> None:
        barrier.wait(timeout=15)
        with pytest.raises(RuntimeError), transaction(db_file) as tx:
            r = EchoScopeRepository(tx)
            # Nota: repository.create_run executa commit proprio; usamos tx.execute na mesma UoW
            tx.execute(
                "INSERT INTO analysis_runs (run_id, period_start, period_end, status) "
                "VALUES ('run_should_rollback', '2026-02-01', '2026-02-02', 'running')"
            )
            assert r is not None
            raise RuntimeError("Falha simulada durante UoW concorrente")

    def reader() -> int:
        barrier.wait(timeout=15)
        svc = PipelineService(db_path=db_file)
        try:
            runs = svc.list_runs()
            return len(runs)
        finally:
            svc.conn.close()

    with ThreadPoolExecutor(max_workers=5) as pool:
        f_w0 = pool.submit(good_writer, 0)
        f_w1 = pool.submit(good_writer, 1)
        f_fail = pool.submit(failing_writer)
        f_r0 = pool.submit(reader)
        f_r1 = pool.submit(reader)

        f_w0.result()
        f_w1.result()
        f_fail.result()
        assert f_r0.result() >= 1
        assert f_r1.result() >= 1

    with closing(sqlite3.connect(db_file)) as verify_conn:
        ids = {row[0] for row in verify_conn.execute("SELECT run_id FROM analysis_runs").fetchall()}
        integrity = verify_conn.execute("PRAGMA integrity_check;").fetchone()[0].lower()
        assert ids == {"run_seed_base", "run_ok_0", "run_ok_1"}
        assert "run_should_rollback" not in ids
        assert integrity == "ok"


@pytest.mark.multiprocess
def test_multiprocess_echoscope_concurrency_extended(tmp_path: Path) -> None:
    """Quatro processos OS independentes gravam via PipelineService sem corrupcao (Extended)."""
    db_file = tmp_path / "echo_mp.db"
    _init_app_db(db_file)

    ctx = multiprocessing.get_context("spawn")
    start_event = ctx.Event()
    result_queue = ctx.Queue()
    processes = 4

    procs = [
        ctx.Process(
            target=_mp_create_run_worker,
            args=(str(db_file), idx, start_event, result_queue),
        )
        for idx in range(processes)
    ]

    for p in procs:
        p.start()
    start_event.set()
    for p in procs:
        p.join(timeout=30)

    outcomes = [result_queue.get(timeout=5) for _ in range(processes)]
    errors = [o for o in outcomes if o[0] != "ok"]
    assert not errors, f"Erros em processos concorrentes: {errors}"

    created_ids = [o[2] for o in outcomes]
    assert len(set(created_ids)) == processes

    with closing(sqlite3.connect(db_file)) as verify_conn:
        db_ids = {r[0] for r in verify_conn.execute("SELECT run_id FROM analysis_runs").fetchall()}
        integrity = verify_conn.execute("PRAGMA integrity_check;").fetchone()[0].lower()
        assert db_ids == set(created_ids)
        assert integrity == "ok"
