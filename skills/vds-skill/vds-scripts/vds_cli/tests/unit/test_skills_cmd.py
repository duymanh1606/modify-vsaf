"""Unit tests for the vds-cli skills subcommand group.

Covers TSK-SYNC-050: subprocess delegation to vds-skills-sync package.

Per VDS testing rules, no test is permitted to run a real subprocess — every
delegation test mocks `subprocess.run` to isolate from the external package.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner
from vds_cli.skills_cmd import _find_vds_skills_sync, skills_app


def _make_pkg(tmp_path: Path) -> Path:
    """Create a stub vds-skills-sync package package layout under tmp_path."""
    pkg = tmp_path / "vds-skills-sync package"
    init = pkg / "src" / "vds_skills_sync" / "__init__.py"
    init.parent.mkdir(parents=True, exist_ok=True)
    init.write_text("", encoding="utf-8")
    return pkg


class TestFindVdsSkillsSync:
    """Tests for _find_vds_skills_sync resolution logic."""

    def test_env_override_accepted(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        pkg = _make_pkg(tmp_path)
        monkeypatch.setenv("VDS_SKILLS_SYNC_DIR", str(pkg))
        assert _find_vds_skills_sync() == pkg

    def test_env_override_rejects_invalid_path(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setenv("VDS_SKILLS_SYNC_DIR", str(tmp_path))
        with pytest.raises(RuntimeError, match="does not contain"):
            _find_vds_skills_sync()

    def test_walk_up_fallback_finds_real_package(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When running inside the real monorepo, walk-up should locate the package."""
        monkeypatch.delenv("VDS_SKILLS_SYNC_DIR", raising=False)
        result = _find_vds_skills_sync()
        assert result.name == "vds-skills-sync"
        assert (result / "src" / "vds_skills_sync" / "__init__.py").exists()

    def test_walk_up_failure_raises(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """If no valid package is discoverable, RuntimeError is raised."""
        monkeypatch.delenv("VDS_SKILLS_SYNC_DIR", raising=False)
        fake_file = tmp_path / "fake_cli.py"
        fake_file.write_text("", encoding="utf-8")
        # Patch __file__ used inside skills_cmd via module attribute.
        with patch("vds_cli.skills_cmd.__file__", str(fake_file)):
            with pytest.raises(RuntimeError, match="vds-skills-sync package not found"):
                _find_vds_skills_sync()


class TestSkillsCommands:
    """Tests for each skills subcommand's argument forwarding."""

    def setup_method(self) -> None:
        self.runner = CliRunner()

    @patch("vds_cli.skills_cmd.subprocess.run")
    @patch("vds_cli.skills_cmd._find_vds_skills_sync")
    def test_sync_default_forwards_agent_and_scope(
        self, mock_find: MagicMock, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        mock_find.return_value = tmp_path
        mock_run.return_value = MagicMock(returncode=0)

        result = self.runner.invoke(skills_app, ["sync"])

        assert result.exit_code == 0
        args = mock_run.call_args[0][0]
        assert "--agent" in args
        assert "claude" in args
        assert "--scope" in args
        assert "project" in args
        assert "--dry-run" not in args
        assert "--force" not in args

    @patch("vds_cli.skills_cmd.subprocess.run")
    @patch("vds_cli.skills_cmd._find_vds_skills_sync")
    def test_sync_with_dry_run_and_force(self, mock_find: MagicMock, mock_run: MagicMock, tmp_path: Path) -> None:
        mock_find.return_value = tmp_path
        mock_run.return_value = MagicMock(returncode=0)

        result = self.runner.invoke(
            skills_app,
            ["sync", "--agent", "cursor", "--dry-run", "--force", "--scope", "user"],
        )

        assert result.exit_code == 0
        args = mock_run.call_args[0][0]
        assert "cursor" in args
        assert "--dry-run" in args
        assert "--force" in args
        assert "user" in args

    @patch("vds_cli.skills_cmd.subprocess.run")
    @patch("vds_cli.skills_cmd._find_vds_skills_sync")
    def test_sync_propagates_nonzero_exit(self, mock_find: MagicMock, mock_run: MagicMock, tmp_path: Path) -> None:
        mock_find.return_value = tmp_path
        mock_run.return_value = MagicMock(returncode=3)

        result = self.runner.invoke(skills_app, ["sync"])

        assert result.exit_code == 3

    @patch("vds_cli.skills_cmd.subprocess.run")
    @patch("vds_cli.skills_cmd._find_vds_skills_sync")
    def test_list_forwards_list_flag(self, mock_find: MagicMock, mock_run: MagicMock, tmp_path: Path) -> None:
        mock_find.return_value = tmp_path
        mock_run.return_value = MagicMock(returncode=0)

        result = self.runner.invoke(skills_app, ["list"])

        assert result.exit_code == 0
        args = mock_run.call_args[0][0]
        assert "--list" in args

    @patch("vds_cli.skills_cmd.subprocess.run")
    @patch("vds_cli.skills_cmd._find_vds_skills_sync")
    def test_validate_forwards_validate_only(self, mock_find: MagicMock, mock_run: MagicMock, tmp_path: Path) -> None:
        """Phase 6 W2b: validate with no args now delegates --validate-all
        (the old --validate-only stub was replaced per TSK-SYNC-063 cli half)."""
        mock_find.return_value = tmp_path
        mock_run.return_value = MagicMock(returncode=0)

        result = self.runner.invoke(skills_app, ["validate"])

        assert result.exit_code == 0
        args = mock_run.call_args[0][0]
        assert "--validate-all" in args

    @patch("vds_cli.skills_cmd.subprocess.run")
    @patch("vds_cli.skills_cmd._find_vds_skills_sync")
    def test_info_forwards_read_with_name(self, mock_find: MagicMock, mock_run: MagicMock, tmp_path: Path) -> None:
        mock_find.return_value = tmp_path
        mock_run.return_value = MagicMock(returncode=0)

        result = self.runner.invoke(skills_app, ["info", "audit-orchestrator-skill"])

        assert result.exit_code == 0
        args = mock_run.call_args[0][0]
        assert "--read" in args
        assert "audit-orchestrator-skill" in args

    @patch("vds_cli.skills_cmd.subprocess.run")
    @patch("vds_cli.skills_cmd._find_vds_skills_sync")
    def test_rollback_forwards_rollback_flag(self, mock_find: MagicMock, mock_run: MagicMock, tmp_path: Path) -> None:
        mock_find.return_value = tmp_path
        mock_run.return_value = MagicMock(returncode=0)

        result = self.runner.invoke(skills_app, ["rollback"])

        assert result.exit_code == 0
        args = mock_run.call_args[0][0]
        assert "--rollback" in args

    @patch("vds_cli.skills_cmd.subprocess.run")
    @patch("vds_cli.skills_cmd._find_vds_skills_sync")
    def test_version_forwards_version_flag(self, mock_find: MagicMock, mock_run: MagicMock, tmp_path: Path) -> None:
        mock_find.return_value = tmp_path
        mock_run.return_value = MagicMock(returncode=0)

        result = self.runner.invoke(skills_app, ["version"])

        assert result.exit_code == 0
        args = mock_run.call_args[0][0]
        assert "--version" in args

    @patch("vds_cli.skills_cmd.subprocess.run")
    @patch("vds_cli.skills_cmd._find_vds_skills_sync")
    def test_pythonpath_injected_for_src(self, mock_find: MagicMock, mock_run: MagicMock, tmp_path: Path) -> None:
        """Subprocess env must include package src/ on PYTHONPATH."""
        mock_find.return_value = tmp_path
        mock_run.return_value = MagicMock(returncode=0)

        result = self.runner.invoke(skills_app, ["list"])

        assert result.exit_code == 0
        call_kwargs = mock_run.call_args[1]
        env = call_kwargs["env"]
        assert str(tmp_path / "src") in env["PYTHONPATH"]
        assert call_kwargs["cwd"] == str(tmp_path)

    def test_help_shows_all_commands(self) -> None:
        result = self.runner.invoke(skills_app, ["--help"])

        assert result.exit_code == 0
        for cmd in ("sync", "list", "validate", "info", "rollback", "version"):
            assert cmd in result.stdout


# ---------------------------------------------------------------------------
# Phase 6 W1 / W2b — selective sync + validate surface (TSK-SYNC-063 cli half)
# ---------------------------------------------------------------------------


class TestSyncSelectiveFlags:
    """Tests for new --skills, --exclude-skills, --category, --diff,
    --diff-format flags added to the sync subcommand."""

    def setup_method(self) -> None:
        self.runner = CliRunner()

    @patch("vds_cli.skills_cmd._run_vds_skills_sync")
    def test_sync_with_skills_flag(self, mock_run: MagicMock) -> None:
        """--skills NAME passes --skills NAME through to vds-skills-sync."""
        mock_run.return_value = 0

        result = self.runner.invoke(
            skills_app,
            ["sync", "--skills", "research-skill", "--agent", "claude", "--dry-run"],
        )

        assert result.exit_code == 0
        args: list[str] = mock_run.call_args[0][0]
        assert "--skills" in args
        assert "research-skill" in args

    @patch("vds_cli.skills_cmd._run_vds_skills_sync")
    def test_sync_with_exclude_skills(self, mock_run: MagicMock) -> None:
        """--exclude-skills NAME passes --exclude-skills NAME through."""
        mock_run.return_value = 0

        result = self.runner.invoke(
            skills_app,
            ["sync", "--exclude-skills", "deprecated-skill"],
        )

        assert result.exit_code == 0
        args: list[str] = mock_run.call_args[0][0]
        assert "--exclude-skills" in args
        assert "deprecated-skill" in args

    @patch("vds_cli.skills_cmd._run_vds_skills_sync")
    def test_sync_mutual_exclusion(self, mock_run: MagicMock) -> None:
        """Combining --skills and --exclude-skills must fail with non-zero exit."""
        mock_run.return_value = 0

        result = self.runner.invoke(
            skills_app,
            ["sync", "--skills", "foo", "--exclude-skills", "bar"],
        )

        assert result.exit_code != 0
        mock_run.assert_not_called()

    @patch("vds_cli.skills_cmd._run_vds_skills_sync")
    def test_sync_diff_format_choices_invalid(self, mock_run: MagicMock) -> None:
        """--diff-format with invalid value (xml) must be rejected before subprocess."""
        mock_run.return_value = 0

        result = self.runner.invoke(
            skills_app,
            ["sync", "--diff-format", "xml"],
        )

        assert result.exit_code != 0
        mock_run.assert_not_called()

    @patch("vds_cli.skills_cmd._run_vds_skills_sync")
    def test_sync_diff_format_valid_choices(self, mock_run: MagicMock) -> None:
        """--diff-format accepts summary, unified, json without error."""
        mock_run.return_value = 0

        for fmt in ("summary", "unified", "json"):
            result = self.runner.invoke(
                skills_app,
                ["sync", "--diff", "--diff-format", fmt],
            )
            assert result.exit_code == 0, (
                f"Expected exit 0 for --diff-format {fmt}, got {result.exit_code}: {result.output}"
            )
            args: list[str] = mock_run.call_args[0][0]
            assert "--diff-format" in args
            assert fmt in args

    @patch("vds_cli.skills_cmd._run_vds_skills_sync")
    def test_sync_category_flag_forwarded(self, mock_run: MagicMock) -> None:
        """--category passes through correctly."""
        mock_run.return_value = 0

        result = self.runner.invoke(
            skills_app,
            ["sync", "--category", "audit"],
        )

        assert result.exit_code == 0
        args: list[str] = mock_run.call_args[0][0]
        assert "--category" in args
        assert "audit" in args

    @patch("vds_cli.skills_cmd._run_vds_skills_sync")
    def test_sync_diff_flag_forwarded(self, mock_run: MagicMock) -> None:
        """--diff with --dry-run passes --diff through."""
        mock_run.return_value = 0

        result = self.runner.invoke(
            skills_app,
            ["sync", "--dry-run", "--diff"],
        )

        assert result.exit_code == 0
        args: list[str] = mock_run.call_args[0][0]
        assert "--diff" in args
        assert "--dry-run" in args


class TestValidateSubcommand:
    """Tests for the replaced validate subcommand with W2a flags."""

    def setup_method(self) -> None:
        self.runner = CliRunner()

    @patch("vds_cli.skills_cmd._run_vds_skills_sync")
    def test_validate_no_args_runs_all(self, mock_run: MagicMock) -> None:
        """vds-cli skills validate with no args calls --validate-all."""
        mock_run.return_value = 0

        result = self.runner.invoke(skills_app, ["validate"])

        assert result.exit_code == 0
        args: list[str] = mock_run.call_args[0][0]
        assert "--validate-all" in args

    @patch("vds_cli.skills_cmd._run_vds_skills_sync")
    def test_validate_skill_path(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """--skill PATH passes --validate-skill PATH through."""
        mock_run.return_value = 0
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text("# skill", encoding="utf-8")

        result = self.runner.invoke(
            skills_app,
            ["validate", "--skill", str(skill_file)],
        )

        assert result.exit_code == 0
        args: list[str] = mock_run.call_args[0][0]
        assert "--validate-skill" in args
        assert str(skill_file) in args

    @patch("vds_cli.skills_cmd._run_vds_skills_sync")
    def test_validate_strict(self, mock_run: MagicMock) -> None:
        """--strict passes through."""
        mock_run.return_value = 0

        result = self.runner.invoke(skills_app, ["validate", "--strict"])

        assert result.exit_code == 0
        args: list[str] = mock_run.call_args[0][0]
        assert "--strict" in args

    @patch("vds_cli.skills_cmd._run_vds_skills_sync")
    def test_validate_fix_flag(self, mock_run: MagicMock) -> None:
        """--fix passes through."""
        mock_run.return_value = 0

        result = self.runner.invoke(skills_app, ["validate", "--fix"])

        assert result.exit_code == 0
        args: list[str] = mock_run.call_args[0][0]
        assert "--fix" in args

    @patch("vds_cli.skills_cmd._run_vds_skills_sync")
    def test_validate_output_path(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """--output FILE passes --output FILE through."""
        mock_run.return_value = 0
        out_file = tmp_path / "audit.md"

        result = self.runner.invoke(
            skills_app,
            ["validate", "--output", str(out_file)],
        )

        assert result.exit_code == 0
        args: list[str] = mock_run.call_args[0][0]
        assert "--output" in args
        assert str(out_file) in args

    @patch("vds_cli.skills_cmd._run_vds_skills_sync")
    def test_validate_json_output(self, mock_run: MagicMock) -> None:
        """--json passes through."""
        mock_run.return_value = 0

        result = self.runner.invoke(skills_app, ["validate", "--json"])

        assert result.exit_code == 0
        args: list[str] = mock_run.call_args[0][0]
        assert "--json" in args

    @patch("vds_cli.skills_cmd._run_vds_skills_sync")
    def test_validate_skill_and_all_mutex(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Combining --skill PATH and --all must fail."""
        mock_run.return_value = 0
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text("# skill", encoding="utf-8")

        result = self.runner.invoke(
            skills_app,
            ["validate", "--skill", str(skill_file), "--all"],
        )

        assert result.exit_code != 0
        mock_run.assert_not_called()

    @patch("vds_cli.skills_cmd._run_vds_skills_sync")
    def test_validate_nonzero_exit_propagated(self, mock_run: MagicMock) -> None:
        """Non-zero return code from subprocess is surfaced."""
        mock_run.return_value = 2

        result = self.runner.invoke(skills_app, ["validate"])

        assert result.exit_code == 2
