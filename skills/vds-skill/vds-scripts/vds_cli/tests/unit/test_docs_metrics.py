"""Tests for docs_metrics module."""

from vds_cli.docs_metrics import generate_freshness_heatmap, generate_onboarding_funnel


class TestOnboardingFunnel:
    def test_generates_result(self, tmp_path):
        result = generate_onboarding_funnel(tmp_path)
        assert "steps" in result
        assert len(result["steps"]) == 4


class TestFreshnessHeatmap:
    def test_empty_repos(self):
        result = generate_freshness_heatmap([])
        assert result["repos"] == {}
