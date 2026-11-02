"""Report generation for SonarQube analysis results."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from vds_sonarqube_orchestrator.config import SonarqubeSettings

logger = structlog.get_logger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"


class ReportError(Exception):
    """Base error for report generation."""

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.context = context or {}


@dataclass
class TrendDataPoint:
    """Single data point in trend analysis."""

    date: str
    value: float | int

    def to_dict(self) -> dict[str, Any]:
        return {"date": self.date, "value": self.value}


@dataclass
class TrendData:
    """Trend data for a metric over time."""

    metric: str
    data_points: list[TrendDataPoint] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"metric": self.metric, "data_points": [dp.to_dict() for dp in self.data_points]}


@dataclass
class ReportData:
    """Data container for report generation."""

    project_key: str
    project_name: str
    generated_at: str
    quality_gate_status: str
    metrics: dict[str, Any] = field(default_factory=dict)
    issues_summary: dict[str, int] = field(default_factory=dict)
    trends: list[TrendData] = field(default_factory=list)
    conditions: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_key": self.project_key,
            "project_name": self.project_name,
            "generated_at": self.generated_at,
            "quality_gate_status": self.quality_gate_status,
            "metrics": self.metrics,
            "issues_summary": self.issues_summary,
            "trends": [t.to_dict() for t in self.trends],
            "conditions": self.conditions,
        }


class SonarqubeReportGenerator:
    """Generator for SonarQube quality reports in PDF and HTML formats."""

    def __init__(self, settings: SonarqubeSettings, template_dir: Path | None = None) -> None:
        self._settings = settings
        self._template_dir = template_dir or TEMPLATES_DIR
        self._sonar_client = None

    def _get_client(self):
        if self._sonar_client is None:
            from vds_sonarqube_orchestrator.client import SonarqubeClient

            self._sonar_client = SonarqubeClient(self._settings)
        return self._sonar_client

    def _fetch_report_data(
        self,
        project_key: str,
        branch: str | None = None,
    ) -> ReportData:
        """Fetch all data needed for report generation."""
        client = self._get_client()

        with client:
            project = client.get_project(project_key)
            qg_status = client.get_quality_gate_status(project_key, branch)
            measures = client.get_measures(
                project_key,
                [
                    "bugs",
                    "vulnerabilities",
                    "code_smells",
                    "coverage",
                    "duplicated_lines_density",
                    "ncloc",
                ],
                branch,
            )
            issues = client.get_issues(project_key=project_key, per_page=500)

        project_status = qg_status.get("projectStatus", {})
        issues_by_severity: dict[str, int] = {}
        for issue in issues:
            sev = issue.get("severity", "UNKNOWN")
            issues_by_severity[sev] = issues_by_severity.get(sev, 0) + 1

        return ReportData(
            project_key=project_key,
            project_name=project.get("name", project_key),
            generated_at=datetime.now().isoformat(),
            quality_gate_status=project_status.get("status", "UNKNOWN"),
            metrics=measures,
            issues_summary=issues_by_severity,
            conditions=project_status.get("conditions", []),
        )

    def get_trend_data(
        self,
        project_key: str,
        metrics: list[str] | None = None,
        days: int = 30,
    ) -> list[TrendData]:
        """Fetch historical trend data for metrics."""
        if metrics is None:
            metrics = ["bugs", "vulnerabilities", "coverage"]

        client = self._get_client()
        trends: list[TrendData] = []

        try:
            with client:
                history = client.get_measures_history(project_key, metrics, days)

            for metric_data in history:
                metric_name = metric_data.get("metric", "")
                data_points = []
                for point in metric_data.get("history", []):
                    data_points.append(
                        TrendDataPoint(
                            date=point.get("date", ""),
                            value=float(point.get("value", 0)),
                        )
                    )
                trends.append(TrendData(metric=metric_name, data_points=data_points))
        except Exception as exc:
            logger.warning("Failed to fetch trend data", error=str(exc))

        return trends

    def generate_html_report(
        self,
        project_key: str,
        output_path: Path,
        branch: str | None = None,
        include_trends: bool = False,
        trend_days: int = 30,
    ) -> Path:
        """Generate HTML report for a project."""
        from jinja2 import Environment, FileSystemLoader, select_autoescape

        report_data = self._fetch_report_data(project_key, branch)

        if include_trends:
            report_data.trends = self.get_trend_data(project_key, days=trend_days)

        template_path = self._template_dir / "html"
        if not template_path.exists():
            template_path = TEMPLATES_DIR / "html"

        env = Environment(
            loader=FileSystemLoader(str(template_path)),
            autoescape=select_autoescape(["html", "xml"]),
        )

        try:
            template = env.get_template("default.jinja2")
        except Exception:
            template_content = self._get_default_html_template()
            template = env.from_string(template_content)

        html_content = template.render(
            report=report_data.to_dict(),
            sonar_url=self._settings.base_url,
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html_content)

        logger.info("HTML report generated", output=str(output_path))
        return output_path

    def generate_pdf_report(
        self,
        project_key: str,
        output_path: Path,
        branch: str | None = None,
        _template_name: str = "detailed",
        include_trends: bool = False,
        trend_days: int = 30,
    ) -> Path:
        """Generate PDF report for a project using PDF Orchestrator."""
        try:
            from vds_pdf_orchestrator import PDFGenerator
        except ImportError as exc:
            raise ReportError(
                "vds-pdf-orchestrator is required for PDF generation",
                {"error": str(exc)},
            ) from exc

        report_data = self._fetch_report_data(project_key, branch)

        if include_trends:
            report_data.trends = self.get_trend_data(project_key, days=trend_days)

        html_path = output_path.with_suffix(".html")
        self.generate_html_report(
            project_key,
            html_path,
            branch,
            include_trends,
            trend_days,
        )

        try:
            pdf_generator = PDFGenerator()
            pdf_generator.html_to_pdf(html_path, output_path)
            html_path.unlink(missing_ok=True)
        except Exception as exc:
            logger.warning("PDF generation failed, keeping HTML", error=str(exc))
            raise ReportError(f"PDF generation failed: {exc}") from exc

        logger.info("PDF report generated", output=str(output_path))
        return output_path

    def _get_default_html_template(self) -> str:
        """Return default HTML template for reports."""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SonarQube Quality Report - {{ report.project_name }}</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 40px; color: #333; }
        h1 { color: #4a90d9; border-bottom: 2px solid #4a90d9; padding-bottom: 10px; }
        h2 { color: #555; margin-top: 30px; }
        .status { padding: 10px 20px; border-radius: 5px; display: inline-block; font-weight: bold; }
        .status-OK { background: #28a745; color: white; }
        .status-ERROR { background: #dc3545; color: white; }
        .status-WARN { background: #ffc107; color: #333; }
        .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }
        .metric-card { background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; }
        .metric-value { font-size: 2em; font-weight: bold; color: #4a90d9; }
        .metric-label { color: #666; margin-top: 5px; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #f8f9fa; }
        .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 0.9em; }
    </style>
</head>
<body>
    <h1>SonarQube Quality Report</h1>
    <p><strong>Project:</strong> {{ report.project_name }} ({{ report.project_key }})</p>
    <p><strong>Generated:</strong> {{ report.generated_at }}</p>

    <h2>Quality Gate Status</h2>
    <div class="status status-{{ report.quality_gate_status }}">{{ report.quality_gate_status }}</div>

    <h2>Key Metrics</h2>
    <div class="metrics">
        {% for key, value in report.metrics.items() %}
        <div class="metric-card">
            <div class="metric-value">{{ value }}</div>
            <div class="metric-label">{{ key | replace('_', ' ') | title }}</div>
        </div>
        {% endfor %}
    </div>

    <h2>Issues by Severity</h2>
    <table>
        <tr><th>Severity</th><th>Count</th></tr>
        {% for severity, count in report.issues_summary.items() %}
        <tr><td>{{ severity }}</td><td>{{ count }}</td></tr>
        {% endfor %}
    </table>

    {% if report.conditions %}
    <h2>Quality Gate Conditions</h2>
    <table>
        <tr><th>Metric</th><th>Status</th><th>Value</th><th>Threshold</th></tr>
        {% for cond in report.conditions %}
        <tr>
            <td>{{ cond.metricKey or cond.metric }}</td>
            <td>{{ cond.status }}</td>
            <td>{{ cond.actualValue or cond.value }}</td>
            <td>{{ cond.errorThreshold or '-' }}</td>
        </tr>
        {% endfor %}
    </table>
    {% endif %}

    <div class="footer">
        <p>Report generated by VDS SonarQube Orchestrator</p>
        <p>SonarQube Server: <a href="{{ sonar_url }}">{{ sonar_url }}</a></p>
    </div>
</body>
</html>"""

    def close(self) -> None:
        if self._sonar_client:
            self._sonar_client.close()
            self._sonar_client = None

    def __enter__(self) -> SonarqubeReportGenerator:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


__all__ = [
    "SonarqubeReportGenerator",
    "ReportData",
    "TrendData",
    "TrendDataPoint",
    "ReportError",
]
