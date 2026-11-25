"""Testes reais de interface headless com Streamlit AppTest sobre ui/app.py (P2)."""

from datetime import date
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from echoscope.database.models import AnalysisRun
from echoscope.services.pipeline_service import PipelineService

APP_ENTRYPOINT = str(Path(__file__).resolve().parents[2] / "ui" / "app.py")


def _configure_isolated_ui_env(monkeypatch: pytest.MonkeyPatch, db_file: Path) -> None:
    monkeypatch.setenv("DB_PATH", str(db_file))
    monkeypatch.setenv("YOUTUBE_API_KEY", "")
    monkeypatch.setenv("GEMINI_API_KEY", "")


@pytest.mark.ui_smoke
@pytest.mark.ui
def test_ui_empty_history_and_navigation_no_keyerror(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cenario 1: Historico vazio e alternancia para Historical Runs sem KeyError: None."""
    db_file = tmp_path / "ui_empty.db"
    _configure_isolated_ui_env(monkeypatch, db_file)

    at = AppTest.from_file(APP_ENTRYPOINT, default_timeout=15).run()
    assert not at.exception
    assert any("Select a historical run" in el.value for el in at.info)

    # Reproduz fluxo onde usuario navega para Historical Runs com lista de execucoes vazia
    nav_radio = at.sidebar.radio[0]
    nav_radio.set_value("Historical Runs").run()
    assert not at.exception
    assert any("No runs recorded in database yet." in el.value for el in at.sidebar.info)


@pytest.mark.ui
def test_ui_populated_history_renders_demo_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cenario 2: Historico populado renderiza execucoes e metricas de mercado."""
    db_file = tmp_path / "ui_pop.db"
    _configure_isolated_ui_env(monkeypatch, db_file)

    svc = PipelineService(db_path=db_file)
    try:
        run_id = svc.seed_demo_dataset()
    finally:
        svc.conn.close()

    at = AppTest.from_file(APP_ENTRYPOINT, default_timeout=15)
    at.session_state["active_run_id"] = run_id
    at.run()

    assert not at.exception
    assert any(run_id in el.value for el in at.subheader)
    assert any("Sample Competitive Overview" in el.value for el in at.markdown)


@pytest.mark.ui
def test_ui_incomplete_failed_snapshot_does_not_crash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cenario 3: Snapshot falho/incompleto sem canais finalizados exibe erro controlado."""
    db_file = tmp_path / "ui_incomplete.db"
    _configure_isolated_ui_env(monkeypatch, db_file)

    svc = PipelineService(db_path=db_file)
    try:
        svc.repository.create_run(
            AnalysisRun(
                run_id="run_failed_snapshot",
                period_start=date(2026, 2, 1),
                period_end=date(2026, 2, 10),
                status="failed",
            )
        )
        svc.repository.record_channel_input_attempt(
            run_id="run_failed_snapshot",
            requested_identifier="@broken_handle",
            resolved_channel_id=None,
            status="failed",
            error_code="CHANNEL_NOT_FOUND",
            error_message="Handle does not exist",
        )
    finally:
        svc.conn.close()

    at = AppTest.from_file(APP_ENTRYPOINT, default_timeout=15)
    at.session_state["active_run_id"] = "run_failed_snapshot"
    at.run()

    assert not at.exception
    assert any("FAILED" in el.value for el in at.error)
    assert any("@broken_handle" in el.value for el in at.markdown)


@pytest.mark.ui
def test_ui_widget_selection_updates_active_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cenario 4: Selectbox no historico lista somente execucoes validas e altera estado."""
    db_file = tmp_path / "ui_select.db"
    _configure_isolated_ui_env(monkeypatch, db_file)

    svc = PipelineService(db_path=db_file)
    try:
        run_1 = svc.seed_demo_dataset()
        svc.repository.create_run(
            AnalysisRun(
                run_id="run_manual_second",
                period_start=date(2026, 3, 1),
                period_end=date(2026, 3, 7),
                status="completed",
            )
        )
    finally:
        svc.conn.close()

    at = AppTest.from_file(APP_ENTRYPOINT, default_timeout=15).run()
    at.sidebar.radio[0].set_value("Historical Runs").run()
    assert not at.exception

    selector = at.sidebar.selectbox[0]
    assert len(selector.options) >= 2
    target_opt = next(opt for opt in selector.options if "run_manual_second" in opt)
    selector.select(target_opt).run()

    assert not at.exception
    assert at.session_state["active_run_id"] == "run_manual_second"
    assert run_1 != "run_manual_second"


@pytest.mark.ui
def test_ui_completed_run_without_metrics_shows_empty_state_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cenario 5: Execucao concluida sem metricas exibe mensagem informativa adequada."""
    db_file = tmp_path / "ui_no_metrics.db"
    _configure_isolated_ui_env(monkeypatch, db_file)

    svc = PipelineService(db_path=db_file)
    try:
        svc.repository.create_run(
            AnalysisRun(
                run_id="run_zero_metrics",
                period_start=date(2026, 2, 1),
                period_end=date(2026, 2, 5),
                status="completed",
            )
        )
    finally:
        svc.conn.close()

    at = AppTest.from_file(APP_ENTRYPOINT, default_timeout=15)
    at.session_state["active_run_id"] = "run_zero_metrics"
    at.run()

    assert not at.exception
    assert any("No completed channel metrics available" in el.value for el in at.info)


@pytest.mark.ui
def test_ui_invalid_run_id_shows_controlled_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cenario 6: Dados/ID invalido na sessao apresenta erro controlado na tela."""
    db_file = tmp_path / "ui_invalid.db"
    _configure_isolated_ui_env(monkeypatch, db_file)

    at = AppTest.from_file(APP_ENTRYPOINT, default_timeout=15)
    at.session_state["active_run_id"] = "run_does_not_exist_999"
    at.run()

    assert not at.exception
    assert any("Error loading run data" in el.value for el in at.error)


@pytest.mark.ui
def test_ui_load_demo_dataset_growth_and_ai_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cenario 7: Load Demo Dataset carrega dados offline, calcula Growth Velocity e trata IA sem chave."""
    db_file = tmp_path / "ui_demo_flow.db"
    _configure_isolated_ui_env(monkeypatch, db_file)

    at = AppTest.from_file(APP_ENTRYPOINT, default_timeout=15).run()
    assert not at.exception

    demo_btn = next(b for b in at.sidebar.button if "Load Demo Dataset" in b.label)
    demo_btn.click().run()
    assert not at.exception
    assert at.session_state["active_run_id"]
    assert any("Demo dataset loaded successfully" in el.value for el in at.success)

    # Dismiss notification banner
    dismiss_btn = next(b for b in at.button if "Dismiss Notification" in b.label)
    dismiss_btn.click().run()
    assert not at.exception

    # Calculate inter-snapshot growth velocity across seeded T0 and T1 runs
    calc_btn = next(b for b in at.button if "Calculate Growth Velocity" in b.label)
    calc_btn.click().run()
    assert not at.exception
    assert any("New uploads published between T0 and T1" in el.value for el in at.markdown)

    # Trigger AI report generation on demo dataset (serves cached offline demo diagnosis)
    ai_btn = next(b for b in at.button if "Generate Strategic Report" in b.label)
    ai_btn.click().run()
    assert not at.exception
    assert any("Report generated successfully" in el.value for el in at.success)


@pytest.mark.ui
def test_ui_validation_empty_channels_and_session_keys_update(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cenario 8: Validacao de canais vazios na UI e aplicacao de chaves de sessao na sidebar."""
    db_file = tmp_path / "ui_validation.db"
    _configure_isolated_ui_env(monkeypatch, db_file)

    at = AppTest.from_file(APP_ENTRYPOINT, default_timeout=15).run()
    assert not at.exception

    # Empty channel submission shows validation error without crashing
    at.sidebar.text_area[0].set_value("   \n  ")
    start_btn = next(b for b in at.sidebar.button if "Start Collection" in b.label)
    start_btn.click().run()
    assert not at.exception
    assert any("Please provide at least one valid channel" in el.value for el in at.sidebar.error)

    # Applying session API keys updates status cleanly (synthetic non-secret placeholders)
    at.sidebar.text_input(key="input_yt_key").set_value("demo_yt_placeholder_value")
    at.sidebar.text_input(key="input_ai_key").set_value("demo_ai_placeholder_value")
    apply_btn = next(b for b in at.sidebar.button if "Apply Session Keys" in b.label)
    apply_btn.click().run()
    assert not at.exception
    assert any("Configured" in el.value for el in at.sidebar.markdown)


@pytest.mark.ui
def test_ui_ranking_table_filters_and_hidden_columns_interaction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cenario 9: Tabela inspirada no YouTube Ranking renderiza HTML rico, filtros e colunas ocultas."""
    db_file = tmp_path / "ui_ranking_tables.db"
    _configure_isolated_ui_env(monkeypatch, db_file)

    svc = PipelineService(db_path=db_file)
    try:
        run_id = svc.seed_demo_dataset()
    finally:
        svc.conn.close()

    at = AppTest.from_file(APP_ENTRYPOINT, default_timeout=15)
    at.session_state["active_run_id"] = run_id
    at.run()
    assert not at.exception

    # Verifica que a tabela de ranking de canais renderizou comparativos T0 -> T1 e formatos
    assert any("es-table" in el.value and "VIEWS PERÍODO" in el.value for el in at.markdown)
    assert any("45M → 129M" in el.value for el in at.markdown)

    # Filtra busca de canal na tabela de ranking e testa cenario sem correspondencia
    search_key = f"ch_rank_{run_id}_search"
    at.text_input(key=search_key).set_value("canal_inexistente_xyz").run()
    assert not at.exception
    assert any("Nenhum canal corresponde aos filtros" in el.value for el in at.info)

    # Restaura busca para canal especifico e oculta uma coluna para validar "Mostrar Todas"
    at.text_input(key=search_key).set_value("veritasium").run()
    assert not at.exception
    assert any("Veritasium" in el.value for el in at.markdown)

    vis_key = f"ch_rank_{run_id}_visible_cols"
    current_cols = list(at.multiselect(key=vis_key).value)
    at.multiselect(key=vis_key).set_value(current_cols[:-2]).run()
    assert not at.exception
    assert any("es-hidden-chip" in el.value for el in at.markdown)

    show_all_btn = next(b for b in at.button if b.key == f"ch_rank_{run_id}_show_all")
    show_all_btn.click().run()
    assert not at.exception
    assert len(at.multiselect(key=vis_key).value) == len(current_cols)
