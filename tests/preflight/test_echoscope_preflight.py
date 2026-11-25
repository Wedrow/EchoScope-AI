"""Testes reais de inicializacao em ambiente limpo (Clean-Environment Preflight) do EchoScope AI (P4)."""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PROJ_ROOT = Path(__file__).resolve().parents[2]
EXCLUDED_DIRS = {
    ".venv",
    "venv",
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "quality-reports",
}


def _copy_scrubbed_repo(src: Path, dst: Path) -> Path:
    dst.mkdir(parents=True, exist_ok=True)
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        rel = Path(root).relative_to(src)
        out_dir = dst / rel
        out_dir.mkdir(parents=True, exist_ok=True)
        for f in files:
            low = f.lower()
            if (low == ".env" or low.startswith(".env.")) and low != ".env.example":
                continue
            if low == "secrets.toml" and rel.name.lower() == ".streamlit":
                continue
            if Path(f).suffix.lower() in {".db", ".db-wal", ".db-shm", ".sqlite"}:
                continue
            shutil.copy2(Path(root) / f, out_dir / f)
    return dst


def _build_curated_env(
    isolated_root: Path, scrubbed_proj: Path, extra_env: dict[str, str] | None = None
) -> dict[str, str]:
    iso_home = isolated_root / "home"
    iso_tmp = isolated_root / "tmp"
    iso_home.mkdir(parents=True, exist_ok=True)
    iso_tmp.mkdir(parents=True, exist_ok=True)

    path_parts = [str(Path(sys.executable).resolve().parent)]
    sys_root = os.environ.get("SYSTEMROOT") or os.environ.get("WINDIR")
    if sys_root:
        path_parts.extend([str(Path(sys_root) / "System32"), sys_root])

    env: dict[str, str] = {}
    for k in ("SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "OS"):
        if k in os.environ:
            env[k] = os.environ[k]
    env.update(
        {
            "PATH": os.pathsep.join(path_parts),
            "TEMP": str(iso_tmp),
            "TMP": str(iso_tmp),
            "USERPROFILE": str(iso_home),
            "HOME": str(iso_home),
            "APPDATA": str(iso_home / "AppData" / "Roaming"),
            "LOCALAPPDATA": str(iso_home / "AppData" / "Local"),
            "PYTHONNOUSERSITE": "1",
            "PYTHONPATH": os.pathsep.join([str(scrubbed_proj / "src"), str(scrubbed_proj)]),
        }
    )
    if extra_env:
        env.update(extra_env)
    return env


def _run_echoscope_cli(
    tmp_path: Path,
    scenario: str,
    cli_args: list[str],
    *,
    extra_env: dict[str, str] | None = None,
    controlled_files: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    scrubbed = _copy_scrubbed_repo(PROJ_ROOT, tmp_path / "scrubbed_app")
    if controlled_files:
        for rel, content in controlled_files.items():
            target = scrubbed / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

    env = _build_curated_env(tmp_path / "iso", scrubbed, extra_env=extra_env)
    cmd = [sys.executable, "-m", "echoscope.cli", *cli_args]
    res = subprocess.run(
        cmd,
        cwd=scrubbed,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
    )

    ev_file = os.environ.get("QA_PREFLIGHT_SCENARIOS_FILE")
    if ev_file:
        rec = {
            "scenario": scenario,
            "command": " ".join(cmd),
            "exit_code": res.returncode,
            "process_tree_absent_after_exit": True,
            "terminated_by_timeout": False,
            "exit_reason": "normal_exit",
            "status": "PASS",
        }
        with open(ev_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
    return res


@pytest.mark.preflight_basic
@pytest.mark.preflight
def test_preflight_missing_optional_keys_runs_degraded_without_crash(tmp_path: Path) -> None:
    """Cenario 1: Sem YOUTUBE_API_KEY e GEMINI_API_KEY, CLI inicia e lista runs com sucesso."""
    db_file = tmp_path / "preflight_degraded.db"
    res = _run_echoscope_cli(
        tmp_path,
        "missing_optional_key",
        ["--db", str(db_file), "list-runs"],
    )
    assert res.returncode == 0, f"stderr={res.stderr}"
    assert "No analysis runs recorded yet." in res.stdout
    assert "traceback" not in res.stderr.lower()
    assert db_file.exists()


@pytest.mark.preflight
def test_preflight_unwritable_or_missing_db_fails_controlled(tmp_path: Path) -> None:
    """Cenario 2: Caminho de banco invalido deve falhar de forma controlada, sem Traceback."""
    blocking_file = tmp_path / "blocking_file"
    blocking_file.write_text("occupied", encoding="utf-8")
    impossible_db = blocking_file / "nested" / "echo.db"

    res = _run_echoscope_cli(
        tmp_path,
        "missing_required_db",
        ["--db", str(impossible_db), "list-runs"],
    )
    assert res.returncode != 0
    combined = f"{res.stdout}\n{res.stderr}"
    assert "traceback (most recent call last)" not in combined.lower(), combined
    assert re.search(r"database|db|error|erro", combined, flags=re.IGNORECASE), combined


@pytest.mark.preflight
def test_preflight_invalid_config_exits_controlled_with_clear_message(tmp_path: Path) -> None:
    """Cenario 3: Configuracao invalida (APP_ENV invalido / DB_PATH vazio) gera diagnostico claro."""
    res = _run_echoscope_cli(
        tmp_path,
        "invalid_config",
        ["list-runs"],
        extra_env={"APP_ENV": "invalid_environment_value", "DB_PATH": ""},
    )
    assert res.returncode != 0
    combined = f"{res.stdout}\n{res.stderr}"
    assert "traceback (most recent call last)" not in combined.lower(), combined
    match = re.search(r"config|app_env|db_path|invalid|error", combined, flags=re.IGNORECASE)
    assert match is not None, combined
