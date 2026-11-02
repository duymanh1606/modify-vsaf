#!/usr/bin/env python3
"""Generate PlantUML diagrams for all VDS project services.

Supports: INSURANCE, LEP, SAVING, EKYC projects.

Usage:
    # Generate for all projects
    uv run python generate_all_diagrams.py

    # Generate for specific project
    uv run python generate_all_diagrams.py --project INSURANCE
    uv run python generate_all_diagrams.py --project LEP
    uv run python generate_all_diagrams.py --project SAVING

    # Generate for specific service
    uv run python generate_all_diagrams.py --project INSURANCE --service insurance-policy-business

    # List available services
    uv run python generate_all_diagrams.py --project LEP --list
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from typing import TYPE_CHECKING

from vds_diagram_generator.analyzer import JavaCodeAnalyzer
from vds_diagram_generator.c4_generator import C4Generator, C4Theme
from vds_diagram_generator.config import PROJECTS, DiagramGeneratorSettings, ProjectName, get_settings
from vds_diagram_generator.generator import PlantUMLGenerator
from vds_diagram_generator.mermaid_generator import MermaidGenerator
from vds_diagram_generator.scenario_templates import list_templates_text, load_templates
from vds_diagram_generator.structurizr_generator import StructurizrDSLGenerator
from vds_diagram_generator.usecase_generator import UseCaseGenerator

if TYPE_CHECKING:
    from vds_diagram_generator.models import ServiceAnalysis

C4_SERVICE_TYPES = {"c4-component", "c4-dynamic"}
C4_PLATFORM_TYPES = {"c4-context", "c4-container"}
DIAGRAM_TYPE_CHOICES = sorted(C4_SERVICE_TYPES | C4_PLATFORM_TYPES)
PLANTUML_OUTPUT_FORMATS = ["puml", "png", "svg"]
PLANTUML_VALIDATE_FLAG = "--validate"


def generate_for_service(
    settings: DiagramGeneratorSettings,
    project: ProjectName,
    service: str,
    analyzer: JavaCodeAnalyzer | None = None,
    sequence_scope: str = "all",
    scenario_match: str | None = None,
    split_sequences: bool = False,
    split_threshold: int = 40,
    generate_mermaid: bool = False,
    mermaid_output_override: str | None = None,
    controller_filter: set[str] | None = None,
    template_kafka_topics: set[str] | None = None,
    generate_usecase: bool = False,
    usecase_only: bool = False,
    usecase_group_by: str = "controller",
    usecase_include_methods: bool = False,
) -> tuple[dict, ServiceAnalysis, list[Path]]:
    """Generate PlantUML diagrams for a single service and return the analysis."""
    source_path = settings.get_project_source_path(project)
    output_base = settings.get_project_docs_path(project)

    analyzer = analyzer or JavaCodeAnalyzer(source_path)
    analysis = analyzer.analyze_service(service)

    output_dir = output_base / service
    output_dir.mkdir(parents=True, exist_ok=True)

    generator = PlantUMLGenerator(output_dir)
    scenario_endpoints = None
    scenario_kafka_topics: set[str] | None = None
    if scenario_match:
        match = scenario_match.lower()
        scenario_endpoints = []
        scenario_kafka_topics = set()
        for controller in analysis.controllers:
            for endpoint in controller.endpoints:
                tokens = [
                    endpoint.method,
                    endpoint.path,
                    endpoint.method_name or "",
                    endpoint.service_method or "",
                ]
                if any(match in token.lower() for token in tokens):
                    scenario_endpoints.append(endpoint)
        for handler in analysis.kafka_handlers:
            if match in handler.class_name.lower():
                scenario_kafka_topics.update(handler.topics)
            else:
                for topic in handler.topics:
                    if match in topic.lower():
                        scenario_kafka_topics.add(topic)

        if scenario_kafka_topics and sequence_scope == "rest":
            # Scenario matches only Kafka but scope is rest; keep endpoints None but still warn?
            pass

        if not scenario_endpoints:
            scenario_endpoints = None
        if scenario_kafka_topics and sequence_scope == "rest":
            scenario_kafka_topics = None
        if not scenario_endpoints and not scenario_kafka_topics:
            print(f"   ⚠️  No flows matched scenario filter '{scenario_match}'. Rendering default sequence.")
            scenario_endpoints = None
            scenario_kafka_topics = None
    if template_kafka_topics:
        if scenario_kafka_topics is None:
            scenario_kafka_topics = set(template_kafka_topics)
        else:
            scenario_kafka_topics.update(template_kafka_topics)

    seq_path, comp_path, split_paths = (
        generator.save_diagrams(
            analysis,
            output_dir,
            sequence_scope=sequence_scope,
            scenario_endpoints=scenario_endpoints,
            scenario_kafka_topics=scenario_kafka_topics,
            split_sequences=split_sequences,
            split_threshold=split_threshold,
            controller_filter=controller_filter,
        )
        if not usecase_only
        else (None, None, [])
    )

    usecase_paths: list[Path] = []
    if generate_usecase or usecase_only:
        usecase_generator = UseCaseGenerator(output_dir)
        usecase_path = usecase_generator.save_use_case_diagram(
            analysis,
            output_dir=output_dir,
            group_by=usecase_group_by,
            include_service_methods=usecase_include_methods,
        )
        usecase_paths.append(usecase_path)

    mermaid_paths: list[Path] = []
    if generate_mermaid and not usecase_only:
        if mermaid_output_override:
            mermaid_dir = Path(mermaid_output_override).expanduser()
            service_dir = mermaid_dir / service
        else:
            service_dir = output_dir

        mermaid_generator = MermaidGenerator(service_dir)
        m_seq, m_comp = mermaid_generator.save_diagrams(
            analysis,
            output_dir=service_dir,
            sequence_scope=sequence_scope,
            scenario_endpoints=scenario_endpoints,
            scenario_kafka_topics=scenario_kafka_topics,
            controller_filter=controller_filter,
        )
        mermaid_paths.extend([m_seq, m_comp])

    result = {
        "service": service,
        "project": project,
        "controllers": len(analysis.controllers),
        "services": len(analysis.services),
        "repositories": len(analysis.repositories),
        "feign_clients": len(analysis.feign_clients),
        "kafka_handlers": len(analysis.kafka_handlers),
        "sequence_diagram": str(seq_path) if seq_path else None,
        "component_diagram": str(comp_path) if comp_path else None,
    }

    diagram_paths = [seq_path, comp_path, *split_paths, *usecase_paths, *mermaid_paths]
    return result, analysis, [p for p in diagram_paths if p]


def generate_for_project(
    settings: DiagramGeneratorSettings,
    project: ProjectName,
    sequence_scope: str,
    scenario_match: str | None,
    split_sequences: bool,
    split_threshold: int,
    generate_mermaid: bool,
    mermaid_output_override: str | None,
    controller_filter: set[str] | None,
    template_kafka_topics: set[str] | None,
    generate_usecase: bool = False,
    usecase_only: bool = False,
    usecase_group_by: str = "controller",
    usecase_include_methods: bool = False,
) -> tuple[list[dict], dict[str, ServiceAnalysis], list[Path]]:
    """Generate PlantUML diagrams for all services in a project."""
    services = settings.discover_services(project)
    if not services:
        print(f"No services found in {project}")
        return [], {}, []

    analyzer = JavaCodeAnalyzer(settings.get_project_source_path(project))

    print(f"\n=== {project} Project ({len(services)} services) ===")
    results: list[dict] = []
    analyses: dict[str, ServiceAnalysis] = {}
    diagram_paths: list[Path] = []

    for service in services:
        print(f"  Analyzing {service}...")
        try:
            result, analysis, diag_files = generate_for_service(
                settings,
                project,
                service,
                analyzer=analyzer,
                sequence_scope=sequence_scope,
                scenario_match=scenario_match,
                split_sequences=split_sequences,
                split_threshold=split_threshold,
                generate_mermaid=generate_mermaid,
                mermaid_output_override=mermaid_output_override,
                controller_filter=controller_filter,
                template_kafka_topics=template_kafka_topics,
                generate_usecase=generate_usecase,
                usecase_only=usecase_only,
                usecase_group_by=usecase_group_by,
                usecase_include_methods=usecase_include_methods,
            )
            analyses[service] = analysis
            results.append(result)
            diagram_paths.extend(diag_files)
            print(f"    Done: {result['controllers']} ctrl, {result['services']} svc, {result['repositories']} repo")
        except Exception as e:
            print(f"    Error: {e}")
            results.append({"service": service, "project": project, "error": str(e)})

    return results, analyses, diagram_paths


def list_services(settings: DiagramGeneratorSettings, project: ProjectName) -> None:
    """List all services in a project."""
    services = settings.discover_services(project)
    print(f"\n{project} Project Services ({len(services)} total):")
    for service in services:
        print(f"  - {service}")


def print_summary(results: list[dict]) -> None:
    """Print summary of generation results."""
    print("\n" + "=" * 60)
    print("GENERATION SUMMARY")
    print("=" * 60)

    by_project: dict[str, list[dict]] = {}
    for r in results:
        proj = r.get("project", "unknown")
        if proj not in by_project:
            by_project[proj] = []
        by_project[proj].append(r)

    total_services = 0
    total_controllers = 0
    total_svc = 0
    total_repos = 0

    for project, proj_results in by_project.items():
        print(f"\n{project}:")
        for r in proj_results:
            if "error" in r:
                print(f"  {r['service']}: ERROR - {r['error']}")
            else:
                print(f"  {r['service']}: {r['controllers']} ctrl, {r['services']} svc, {r['repositories']} repo")
                total_services += 1
                total_controllers += r.get("controllers", 0)
                total_svc += r.get("services", 0)
                total_repos += r.get("repositories", 0)

    print(
        f"\nTotal: {total_services} services, {total_controllers} controllers, {total_svc} services, {total_repos} repositories"
    )


def _run_plantuml_command(paths: list[Path], args: list[str], action_label: str) -> None:
    plantuml_bin = shutil.which("plantuml")
    if not plantuml_bin:
        print(f"\n⚠️  PlantUML CLI not found; install with `brew install plantuml` to {action_label}.")
        return

    print(f"\n🔎 {action_label.capitalize()} {len(paths)} diagram(s)...")
    for path in paths:
        try:
            result = subprocess.run(
                [plantuml_bin, *args, str(path)],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                print(f"   ⚠️  PlantUML {action_label} failed for {path.name}: {result.stderr.strip()}")
        except (subprocess.TimeoutExpired, subprocess.SubprocessError) as exc:
            print(f"   ⚠️  PlantUML {action_label} failed for {path.name}: {exc}")


def _render_additional_formats(puml_paths: list[Path], output_format: str) -> None:
    if output_format == "puml" or not puml_paths:
        return

    flag = "-tpng" if output_format == "png" else "-tsvg"
    _run_plantuml_command(puml_paths, [flag], f"render {output_format.upper()}")


def _validate_diagrams(puml_paths: list[Path]) -> None:
    if not puml_paths:
        return
    _run_plantuml_command(puml_paths, [PLANTUML_VALIDATE_FLAG], "validate")


def _collect_existing_puml_paths(
    settings: DiagramGeneratorSettings,
    projects: list[ProjectName],
    service_filters: dict[ProjectName, list[str]] | None = None,
) -> list[Path]:
    collected: list[Path] = []
    seen: set[Path] = set()

    for project in projects:
        docs_root = settings.get_project_docs_path(project)
        if not docs_root.exists():
            continue

        services = service_filters.get(project) if service_filters else None
        if not services:
            services = settings.discover_services(project)
            if not services:
                continue

        for service in services:
            service_dir = docs_root / service
            if not service_dir.exists():
                continue
            for path in service_dir.rglob("*.puml"):
                norm = path.resolve()
                if norm not in seen:
                    seen.add(norm)
                    collected.append(norm)

    return collected


def _get_c4_generator(settings: DiagramGeneratorSettings, project: ProjectName, theme: C4Theme) -> C4Generator:
    """Initialize a C4 generator rooted at the project's analysis directory."""
    analysis_root = settings.get_project_docs_path(project).parent
    analysis_root.mkdir(parents=True, exist_ok=True)
    return C4Generator(analysis_root, theme=theme)


def run_c4_generation(
    settings: DiagramGeneratorSettings,
    project: ProjectName,
    analyses: dict[str, ServiceAnalysis],
    service_types: set[str],
    platform_types: set[str],
    hierarchy: bool,
    theme: C4Theme,
    limit_services: list[str] | None = None,
) -> None:
    """Generate requested C4 diagrams for a project."""
    generated: list[Path] = []
    if not (service_types or platform_types or hierarchy):
        return generated

    generator = _get_c4_generator(settings, project, theme)

    if hierarchy:
        if not analyses:
            print(f"\n⚠️  No analyses available for {project}; skipping hierarchical C4 generation.")
            return generated
        print(f"\n📊 Generating hierarchical C4 diagrams for {project}...")
        bundle = generator.generate_all_hierarchical_diagrams(project, list(analyses.values()))
        for paths in bundle.values():
            generated.extend(paths)
        return generated

    if platform_types:
        print(f"\n📊 Generating C4 platform diagrams for {project}...")
        if "c4-context" in platform_types:
            path = generator.save_l1_context_diagram(project)
            print(f"   ✅ L1 Context: {path}")
            generated.append(path)
        if "c4-container" in platform_types:
            path = generator.save_l2_container_diagram(project)
            print(f"   ✅ L2 Container: {path}")
            generated.append(path)

    if service_types:
        if not analyses:
            print(f"\n⚠️  No service analyses available for {project}; skipping service-level C4 diagrams.")
            return generated

        service_items = list(analyses.items())
        if limit_services:
            service_items = [(name, analyses[name]) for name in limit_services if name in analyses]

        if not service_items:
            print(f"\n⚠️  Requested services not analyzed for {project}; skipping service-level C4 diagrams.")
            return generated

        print(f"\n📊 Generating C4 service diagrams for {project}...")
        for service_name, analysis in service_items:
            if "c4-component" in service_types:
                path = generator.save_l3_component_diagram(analysis)
                print(f"   ✅ C4 Component ({service_name}): {path}")
                generated.append(path)
            if "c4-dynamic" in service_types:
                path = generator.save_c4_dynamic_diagram(analysis)
                print(f"   ✅ C4 Dynamic ({service_name}): {path}")
                generated.append(path)

    return generated


def run_structurizr_export(
    settings: DiagramGeneratorSettings,
    project: ProjectName,
    analyses: dict[str, ServiceAnalysis],
    output_override: str | None,
    limit_services: list[str] | None = None,
) -> list[Path]:
    if not analyses:
        print(f"\n⚠️  No analyses available for {project}; skipping Structurizr DSL export.")
        return []

    if output_override:
        base_dir = Path(output_override).expanduser()
    else:
        base_dir = settings.get_project_docs_path(project).parent / "structurizr"

    project_dir = base_dir / project.lower()
    service_dir = project_dir / "services"
    platform_dir = project_dir / "platform"
    service_dir.mkdir(parents=True, exist_ok=True)
    platform_dir.mkdir(parents=True, exist_ok=True)

    generator = StructurizrDSLGenerator(project_dir)
    generated: list[Path] = []

    service_items = list(analyses.items())
    if limit_services:
        service_items = [(name, analyses[name]) for name in limit_services if name in analyses]
    if not service_items:
        print(f"\n⚠️  Requested services not analyzed for {project}; skipping Structurizr DSL export.")
        return []

    print(f"\n🗂️  Generating Structurizr DSL for {project}...")
    for _service_name, analysis in service_items:
        path = generator.save_service_workspace(analysis, output_dir=service_dir)
        generated.append(path)
        print(f"   ✅ Workspace: {path.name}")

    if not limit_services:
        path = generator.save_platform_workspace(
            project, output_dir=platform_dir, service_analyses=list(analyses.values())
        )
        generated.append(path)
        print(f"   ✅ Platform workspace: {path.name}")

    return generated


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate PlantUML diagrams for VDS services")
    parser.add_argument(
        "--project",
        "-p",
        type=str,
        choices=list(PROJECTS.keys()),
        help="Project to generate diagrams for (default: all projects)",
    )
    parser.add_argument(
        "--service",
        "-s",
        type=str,
        help="Specific service to generate diagrams for",
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="List available services instead of generating",
    )
    parser.add_argument(
        "--workspace",
        "-w",
        type=str,
        help="Workspace root path (default: current directory)",
    )
    parser.add_argument(
        "--all-projects",
        action="store_true",
        help="Generate diagrams for all projects (overrides --project)",
    )
    parser.add_argument(
        "--c4",
        action="store_true",
        help="Generate C4-PlantUML diagrams (component + dynamic) in addition to standard diagrams",
    )
    parser.add_argument(
        "--diagram-type",
        type=str,
        choices=DIAGRAM_TYPE_CHOICES,
        help="Limit C4 generation to a specific diagram type (context, container, component, dynamic)",
    )
    parser.add_argument(
        "--hierarchy",
        action="store_true",
        help="Generate full C4 hierarchy (L1 Context, L2 Container, L3 Component, Dynamic) for the selected project",
    )
    parser.add_argument(
        "--theme",
        type=str,
        choices=[theme.value for theme in C4Theme],
        default=C4Theme.DEFAULT.value,
        help="C4 diagram theme (default, sketchy, verbose)",
    )
    parser.add_argument(
        "--sequence-scope",
        type=str,
        choices=["all", "rest", "kafka"],
        default="all",
        help="Choose which flows to include in generated sequence diagrams",
    )
    parser.add_argument(
        "--sequence-scenario",
        type=str,
        help="Restrict REST sequence flows to endpoints whose method or path contains the provided keyword",
    )
    parser.add_argument(
        "--scenario-template",
        type=str,
        help="Apply a named scenario template (see --list-templates)",
    )
    parser.add_argument(
        "--list-templates",
        action="store_true",
        help="List available scenario templates and exit",
    )
    parser.add_argument(
        "--auto-split-sequence",
        action="store_true",
        help="Automatically split oversized sequence diagrams into per-controller/per-topic views",
    )
    parser.add_argument(
        "--split-threshold",
        type=int,
        default=40,
        help="Participant threshold that triggers sequence auto-splitting (default: 40)",
    )
    parser.add_argument(
        "--export-dsl",
        action="store_true",
        help="Generate Structurizr DSL workspaces for analyzed services (and platform when applicable)",
    )
    parser.add_argument(
        "--dsl-output",
        type=str,
        help="Directory to store Structurizr DSL workspaces (default: docs-nttc/.../structurizr/<project>)",
    )
    parser.add_argument(
        "--output-format",
        type=str,
        choices=PLANTUML_OUTPUT_FORMATS,
        default="puml",
        help="Final diagram format (puml, png, svg)",
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip PlantUML syntax validation (validation is enabled by default to ensure correct diagram syntax)",
    )
    parser.add_argument(
        "--validate-existing",
        action="store_true",
        help="Validate existing .puml diagrams without regenerating (respecting --project/--service filters)",
    )
    parser.add_argument(
        "--mermaid",
        action="store_true",
        help="Generate Mermaid (.mmd) diagrams alongside PlantUML outputs",
    )
    parser.add_argument(
        "--mermaid-output",
        type=str,
        help="Optional root directory for Mermaid outputs (defaults to standard docs path)",
    )
    parser.add_argument(
        "--use-case",
        action="store_true",
        help="Generate use case diagrams alongside sequence/component diagrams",
    )
    parser.add_argument(
        "--use-case-only",
        action="store_true",
        help="Generate use case diagrams only (skip sequence/component diagrams)",
    )
    parser.add_argument(
        "--use-case-group-by",
        type=str,
        choices=["controller", "service"],
        default="controller",
        help="Group use cases by controller (default) or service",
    )
    parser.add_argument(
        "--use-case-include-methods",
        action="store_true",
        help="Include service methods as use cases (optional enhancement)",
    )

    args = parser.parse_args()
    if args.hierarchy and args.service:
        parser.error("--hierarchy cannot be combined with --service")
    if args.all_projects and args.service:
        parser.error("--all-projects cannot be combined with --service")
    selected_theme = C4Theme(args.theme)
    sequence_scope = args.sequence_scope
    auto_split_sequences = args.auto_split_sequence
    split_threshold = max(10, args.split_threshold)
    generate_mermaid = args.mermaid
    mermaid_output_override = args.mermaid_output
    generate_usecase = args.use_case
    usecase_only = args.use_case_only
    usecase_group_by = args.use_case_group_by
    usecase_include_methods = args.use_case_include_methods
    controller_filter: set[str] | None = None
    template_kafka_topics: set[str] | None = None

    if args.list_templates:
        print(list_templates_text())
        return

    templates = load_templates()
    if args.scenario_template:
        template = templates.get(args.scenario_template)
        if not template:
            print(
                f"Unknown scenario template '{args.scenario_template}'. Use --list-templates to view available templates."
            )
            return
        if template.sequence_scope:
            sequence_scope = template.sequence_scope
        if template.match and not args.sequence_scenario:
            args.sequence_scenario = template.match
        if template.auto_split is not None:
            auto_split_sequences = template.auto_split
        if template.split_threshold:
            split_threshold = max(10, template.split_threshold)
        if template.controllers:
            controller_filter = set(template.controllers)
        if template.kafka_topics:
            template_kafka_topics = set(template.kafka_topics)
        if template.enable_mermaid:
            generate_mermaid = True

    service_c4_types: set[str] = set()
    platform_c4_types: set[str] = set()

    if args.diagram_type in C4_SERVICE_TYPES:
        service_c4_types.add(args.diagram_type)
    elif args.diagram_type in C4_PLATFORM_TYPES:
        platform_c4_types.add(args.diagram_type)

    if args.c4 and args.diagram_type is None:
        service_c4_types.update(C4_SERVICE_TYPES)

    if args.hierarchy:
        service_c4_types.update(C4_SERVICE_TYPES)
        platform_c4_types.update(C4_PLATFORM_TYPES)

    want_c4 = bool(service_c4_types or platform_c4_types)

    # Initialize settings
    if args.workspace:
        settings = DiagramGeneratorSettings(workspace_root=Path(args.workspace))
    else:
        # Try to find workspace root by looking for *-project folders
        cwd = Path.cwd()
        if any((cwd / f"{p}-project").exists() for p in ["INSURANCE", "LEP", "SAVING", "EKYC"]):
            settings = DiagramGeneratorSettings(workspace_root=cwd)
        elif any((cwd.parent / f"{p}-project").exists() for p in ["INSURANCE", "LEP", "SAVING", "EKYC"]):
            settings = DiagramGeneratorSettings(workspace_root=cwd.parent)
        elif any((cwd.parent.parent / f"{p}-project").exists() for p in ["INSURANCE", "LEP", "SAVING", "EKYC"]):
            settings = DiagramGeneratorSettings(workspace_root=cwd.parent.parent)
        else:
            settings = get_settings()

    print(f"Workspace: {settings.workspace_root}")

    list_targets = list(PROJECTS.keys()) if args.all_projects or not args.project else [args.project]

    if args.validate_existing:
        service_filters: dict[ProjectName, list[str]] = {}
        if args.service:
            service_filters.setdefault(args.project, []).append(args.service)
        existing_puml = _collect_existing_puml_paths(
            settings,
            list_targets,
            service_filters if service_filters else None,
        )
        if not existing_puml:
            print("\n⚠️  No existing .puml diagrams found for the requested scope.")
        else:
            _validate_diagrams(existing_puml)
        return

    # List mode
    if args.list:
        if args.project and not args.all_projects:
            list_services(settings, args.project)
        else:
            for project in list_targets:
                list_services(settings, project)
        return

    # Generate mode
    results: list[dict] = []
    generated_puml: list[Path] = []

    if args.service:
        # Single service
        if not args.project:
            print("Error: --project is required when specifying --service")
            sys.exit(1)
        print(f"Generating diagrams for {args.project}/{args.service}...")
        result, analysis, diag_files = generate_for_service(
            settings,
            args.project,
            args.service,
            sequence_scope=sequence_scope,
            scenario_match=args.sequence_scenario,
            split_sequences=auto_split_sequences,
            split_threshold=split_threshold,
            generate_mermaid=generate_mermaid,
            mermaid_output_override=mermaid_output_override,
            controller_filter=controller_filter,
            template_kafka_topics=template_kafka_topics,
            generate_usecase=generate_usecase,
            usecase_only=usecase_only,
            usecase_group_by=usecase_group_by,
            usecase_include_methods=usecase_include_methods,
        )
        results.append(result)
        generated_puml.extend(diag_files)

        if want_c4:
            c4_paths = run_c4_generation(
                settings,
                args.project,
                {args.service: analysis},
                service_c4_types,
                platform_c4_types,
                args.hierarchy,
                selected_theme,
                limit_services=[args.service],
            )
            generated_puml.extend(c4_paths)
        if args.export_dsl:
            run_structurizr_export(
                settings,
                args.project,
                {args.service: analysis},
                args.dsl_output,
                limit_services=[args.service],
            )
    else:
        for project in list_targets:
            proj_results, analyses, diag_files = generate_for_project(
                settings,
                project,
                sequence_scope,
                args.sequence_scenario,
                auto_split_sequences,
                split_threshold,
                generate_mermaid,
                mermaid_output_override,
                controller_filter,
                template_kafka_topics,
                generate_usecase=generate_usecase,
                usecase_only=usecase_only,
                usecase_group_by=usecase_group_by,
                usecase_include_methods=usecase_include_methods,
            )
            results.extend(proj_results)
            generated_puml.extend(diag_files)
            if want_c4:
                c4_paths = run_c4_generation(
                    settings,
                    project,
                    analyses,
                    service_c4_types,
                    platform_c4_types,
                    args.hierarchy,
                    selected_theme,
                )
                generated_puml.extend(c4_paths)
            if args.export_dsl:
                run_structurizr_export(
                    settings,
                    project,
                    analyses,
                    args.dsl_output,
                )

    print_summary(results)
    unique_puml = list(dict.fromkeys(generated_puml))
    _render_additional_formats(unique_puml, args.output_format)
    # Validation is enabled by default to ensure correct syntax
    if not args.no_validate and unique_puml:
        _validate_diagrams(unique_puml)


if __name__ == "__main__":
    main()
