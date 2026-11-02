from vds_git_orchestrator.cli import _default_concurrency


def test_default_concurrency_from_env(monkeypatch):
    monkeypatch.setenv("VDS_GIT_CONCURRENCY_DEFAULT", "12")
    assert _default_concurrency() == 12


def test_default_concurrency_cpu_fallback(monkeypatch):
    monkeypatch.delenv("VDS_GIT_CONCURRENCY_DEFAULT", raising=False)
    monkeypatch.setattr("vds_git_orchestrator.cli._get_real_cpu_count", lambda: 6)
    assert _default_concurrency() == 2  # max(2, 6//3)=2


def test_default_concurrency_invalid_env(monkeypatch):
    monkeypatch.setenv("VDS_GIT_CONCURRENCY_DEFAULT", "bad")
    monkeypatch.setattr("vds_git_orchestrator.cli._get_real_cpu_count", lambda: 32)
    # cpu fallback -> max(2, 32//3)=10, capped at 6
    assert _default_concurrency() == 6
