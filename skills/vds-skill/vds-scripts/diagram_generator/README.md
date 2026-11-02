# VDS Diagram Generator

Java source code analyzer and PlantUML diagram generator for VDS platform services.

## Supported Projects

- **INSURANCE** - Digital Insurance Platform (23 services)
- **LEP** - Digital Lending Platform (25+ services)
- **SAVING** - Digital Savings Platform (13 services)
- **EKYC** - EKYC Services (2 services)

## Overview

This tool analyzes Java Spring Boot source code to extract:

- REST Controllers with endpoints
- Service implementations
- Repository interfaces
- Feign client integrations
- Kafka message handlers

It then generates accurate PlantUML diagrams based on the actual codebase:

- **Sequence Diagrams**: Show request flows from client → controller → service → repository
- **Component Diagrams**: Show architectural components and their relationships
- **Use Case Diagrams**: Map REST endpoints and Kafka topics to use cases with actors
- **C4 Model Diagrams**: Hierarchical architecture views (L1 Context, L2 Container, L3 Component, Dynamic)
- **Mermaid Diagrams**: GitHub/GitLab-native diagram formats
- **Structurizr DSL**: Model-based architecture documentation

**Automatic Syntax Validation**: All generated diagrams are automatically validated using the latest PlantUML CLI to ensure correct syntax. Validation runs by default after every generation to catch syntax errors early.

## Installation

```bash
cd vds-scripts/diagram_generator

# Install production dependencies only
uv sync

# Install with dev dependencies (for testing)
uv sync --group dev
```

## CLI Usage

### Via VDS CLI (Recommended)

The diagram generator is integrated into the unified VDS CLI. This is the recommended approach for AI agents and automation:

```bash
# List available services
./scripts/worktree_uv.sh run --project vds_cli vds-cli diagrams -- --project INSURANCE --list

# Generate for specific service
./scripts/worktree_uv.sh run --project vds_cli vds-cli diagrams -- --project INSURANCE --service insurance-policy-business

# Generate all diagram types (C4, Mermaid, Use Case)
./scripts/worktree_uv.sh run --project vds_cli vds-cli diagrams -- --project INSURANCE --c4 --mermaid --use-case

# Full C4 hierarchy with Structurizr DSL export
./scripts/worktree_uv.sh run --project vds_cli vds-cli diagrams -- --project INSURANCE --hierarchy --export-dsl

# Validate existing diagrams (CI-friendly)
./scripts/worktree_uv.sh run --project vds_cli vds-cli diagrams -- --project INSURANCE --validate-existing
```

### Direct Access (from diagram_generator directory)

```bash
cd vds-scripts/diagram_generator

# Generate for all projects
uv run python generate_all_diagrams.py

# Generate for specific project
uv run python generate_all_diagrams.py --project INSURANCE
uv run python generate_all_diagrams.py --project LEP
uv run python generate_all_diagrams.py --project SAVING
uv run python generate_all_diagrams.py --project EKYC

# Generate for specific service
uv run python generate_all_diagrams.py --project INSURANCE --service insurance-policy-business
uv run python generate_all_diagrams.py --project LEP --service lending-payment-service
uv run python generate_all_diagrams.py --project SAVING --service saving-business
```

### List Available Services

```bash
# List all services in all projects
uv run python generate_all_diagrams.py --list

# List services in specific project
uv run python generate_all_diagrams.py --project LEP --list
```

### Generate C4 Diagrams

```bash
# Add C4 component + dynamic diagrams alongside standard outputs
uv run python generate_all_diagrams.py --project INSURANCE --c4

# Generate just the requested C4 diagram type (e.g., platform context)
uv run python generate_all_diagrams.py --project INSURANCE --diagram-type c4-context

# Produce the full C4 hierarchy (L1→L3 + Dynamic) with a sketchy theme
uv run python generate_all_diagrams.py --project INSURANCE --hierarchy --theme sketchy
```

**Flags**

- `--c4`: Adds C4 component + dynamic diagrams for every analyzed service (default theme `default`)
- `--diagram-type {c4-context|c4-container|c4-component|c4-dynamic}`: Limits the C4 output to a specific diagram type
- `--hierarchy`: Generates the complete C4 stack (L1 Context, L2 Container, L3 Component, Dynamic) for the selected project
- `--theme {default, sketchy, verbose}`: Applies the matching theme to every generated C4 diagram
- `--sequence-scope {all, rest, kafka}`: Toggle whether sequence diagrams render only synchronous flows, only Kafka/event flows, or both
- `--sequence-scenario <keyword>`: Limit sequence flows (REST + Kafka) to endpoints/topics whose path/method/topic contains the keyword
- `--scenario-template <name>`: Apply a reusable scenario preset defined in `src/vds_diagram_generator/templates/scenario_templates.json`
- `--list-templates`: Print all available scenario presets and exit
- `--auto-split-sequence`: When enabled, automatically emits per-controller/per-topic sequence diagrams if the participant count exceeds the threshold
- `--split-threshold <n>`: Participant threshold that triggers auto-splitting; defaults to 40 (minimum 10)
- `--no-validate`: Skip PlantUML syntax validation (validation is **enabled by default** to ensure correct diagram syntax)
- `--validate-existing`: Validate existing `.puml` diagrams without regenerating (respecting `--project/--service` filters) – ideal for CI pipelines
- `--mermaid`: Emit Mermaid `.mmd` diagrams (sequence + component) alongside PlantUML output
- `--mermaid-output <path>`: Override the output directory used for Mermaid diagrams (defaults to the standard docs path)
- `--use-case`: Generate use case diagrams alongside sequence/component diagrams
- `--use-case-only`: Generate use case diagrams only (skip sequence/component diagrams)
- `--use-case-group-by {controller,service}`: Group use cases by controller (default) or service
- `--use-case-include-methods`: Include service methods as use cases (optional enhancement)
- `--all-projects`: Runs generation across every registered project without needing multiple invocations
- `--output-format {puml, png, svg}`: Renders final diagrams directly to PNG/SVG via `plantuml` (default keeps `.puml` only)

> Supplying `--diagram-type` or `--hierarchy` automatically enables C4 generation even without the `--c4` flag. Standard PlantUML sequence/component diagrams continue to be rendered unless the script is invoked in list-only mode.

### Sequence Diagram Controls

- Interface-only controllers (with `@RequestMapping` but without `@RestController`) are now merged automatically with their implementing classes, so every declared endpoint appears in the generated diagrams.
- The analyzer infers the most likely service method for each endpoint (based on injected dependencies and method names), allowing the sequence diagram to show controller → service → repository hops instead of generic responses.
- Combine `--sequence-scope` with `--sequence-scenario <keyword>` to produce narrowly focused diagrams (for example, REST-only `/policy/enable-renewal` flows or Kafka-only renewal topics).
- Use `--auto-split-sequence` (with `--split-threshold`) to emit per-controller/per-topic diagrams automatically whenever a service’s participant count exceeds the specified threshold.
- Add `--mermaid` to produce GitHub/GitLab-friendly `.mmd` outputs (sequence + component). Mermaid files mirror the PlantUML content and live beside the `.puml` artefacts unless `--mermaid-output` overrides the destination.

### Scenario Templates

Repeatable filters live in `src/vds_diagram_generator/templates/scenario_templates.json`. Each template can define:

- `match`: keyword used by the analyzer’s scenario filter (maps to `--sequence-scenario`)
- `sequence_scope`: overrides `--sequence-scope`
- `controllers`: restricts the diagram to selected controllers (other participants drop out automatically)
- `kafka_topics`: explicit topic whitelist (merged with any keyword matches)
- `auto_split` / `split_threshold`: overrides the auto-splitting knobs
- `enable_mermaid`: force Mermaid output for that scenario

Usage:

```bash
# List templates
uv run python generate_all_diagrams.py --list-templates

# Apply a template (e.g., policy-renewal) without remembering the knobs
uv run python generate_all_diagrams.py \
  --project INSURANCE \
  --service insurance-policy-business \
  --scenario-template policy-renewal
```

### Automatic Syntax Validation

**Validation is enabled by default** to ensure all generated diagrams have correct PlantUML syntax. The generator automatically validates every `.puml` file after generation using the latest PlantUML CLI.

- **Default behavior**: All generated diagrams are automatically validated
- **Skip validation**: Use `--no-validate` to disable validation (not recommended)
- **Requirements**: PlantUML CLI must be installed (`brew install plantuml` on macOS, `apt install plantuml` on Debian)

If validation fails, the generator will report syntax errors and continue. Fix any reported issues to ensure diagrams render correctly.

### CI Validation Workflow

When running in CI, you have two options:

**Option 1: Validate existing diagrams (recommended for CI)**

1. Ensure the PlantUML CLI is installed on the runner
2. Validate previously generated `.puml` files without regeneration:

   ```bash
   uv run python generate_all_diagrams.py --project INSURANCE --service insurance-policy-business --validate-existing
   ```

   Omit `--service` (or add `--all-projects`) to validate every project.

**Option 2: Generate and validate (automatic validation)**

- Simply run generation - validation happens automatically by default:

   ```bash
   uv run python generate_all_diagrams.py --project INSURANCE --service insurance-policy-business
   ```

   Validation runs automatically after generation completes.

For a compact CI entrypoint, you can also use the helper script:

```bash
# Validate all INSURANCE diagrams
./ci_validate.sh INSURANCE

# Validate a single service
./ci_validate.sh INSURANCE insurance-policy-business
```

#### GitHub Actions Example

A sample workflow lives in `examples/github-actions-validate.yml`. It:

1. Installs PlantUML + uv on `ubuntu-latest`
2. Runs `./ci_validate.sh <PROJECT>` to exercise `--validate-existing`

```yaml
- name: Validate PlantUML diagrams
  run: |
    cd vds-scripts/diagram_generator
    ./ci_validate.sh INSURANCE
```

To sync artefacts with Confluence, follow this validation step with the existing `vds-cli confluence content upload` commands used earlier in Phase 1 (see `AGENTS.md` for token requirements). The same pipeline can invoke `--mermaid` and `--export-dsl` flags if you want CI to regenerate diagrams before upload.

### Mermaid Output (Experimental)

```bash
# Generate PlantUML + Mermaid diagrams into the standard docs folder
uv run python generate_all_diagrams.py --project INSURANCE --service insurance-policy-business --mermaid

# Send Mermaid outputs to a custom folder (e.g., for GitHub Pages)
uv run python generate_all_diagrams.py \
  --project INSURANCE \
  --service insurance-policy-business \
  --mermaid \
  --mermaid-output ./out/mermaid
```

Mermaid sequence diagrams use the standard `sequenceDiagram` syntax (compatible with GitHub/GitLab/DevOps wiki renderers), while component diagrams emit `graph TD` flows. Both mirror the same analysis data as PlantUML so you can embed `.mmd` files directly in Markdown without extra rendering steps.

### Use Case Diagram Generation

Generate PlantUML use case diagrams from REST endpoints and service methods:

```bash
# Generate use case diagrams alongside sequence/component diagrams
uv run python generate_all_diagrams.py --project INSURANCE --service insurance-policy-business --use-case

# Generate use case diagrams only (skip sequence/component)
uv run python generate_all_diagrams.py --project INSURANCE --service insurance-policy-business --use-case-only

# Group use cases by service instead of controller
uv run python generate_all_diagrams.py --project INSURANCE --use-case --use-case-group-by service

# Include service methods as use cases
uv run python generate_all_diagrams.py --project INSURANCE --use-case --use-case-include-methods
```

**Flags**

- `--use-case`: Generate use case diagrams alongside sequence/component diagrams
- `--use-case-only`: Generate use case diagrams only (skip sequence/component diagrams)
- `--use-case-group-by {controller,service}`: Group use cases by controller (default) or service
- `--use-case-include-methods`: Include service methods as use cases (optional enhancement)

**Actor Extraction**

- **Default Actor**: "Client" - always present for REST API consumers
- **External Actors**: Extracted from Feign clients (target services as external actors)
- **Internal Actors**: Derived from controller names (e.g., `PolicyController` → `Policy` actor)
- **System Actors**: Kafka System for event-driven flows

**Use Case Mapping**

- Each REST endpoint (`@GetMapping`, `@PostMapping`, etc.) becomes a use case
- Format: `{HTTP_METHOD} {path}` (e.g., `GET /policy/{id}`)
- Kafka topics become use cases: `Consume {topic}`
- Optional: Service methods can be included as use cases when `--use-case-include-methods` is used

**Example Output**

Generated file: `insurance-policy-business-usecase.puml`

The diagram shows:

- Actors (Client, external systems, controllers, Kafka System)
- Use cases grouped by controller or service
- Relationships (actor → use case, use case dependencies)

### Structurizr DSL Export

```bash
# Generate Structurizr DSL for a single service
uv run python generate_all_diagrams.py --project INSURANCE --service insurance-policy-business --export-dsl

# Export the entire project's DSL workspaces to a custom folder
uv run python generate_all_diagrams.py --project INSURANCE --export-dsl --dsl-output ./out/structurizr

# Combine DSL export with C4 hierarchy + PNG rendering
uv run python generate_all_diagrams.py --project INSURANCE --hierarchy --export-dsl --output-format png
```

- `--export-dsl`: Writes Structurizr workspaces (`*-workspace.dsl`) for each analyzed service (and platform when processing a full project)
- `--dsl-output <path>`: Overrides the default Structurizr output directory (`docs-nttc/projects/<PROJECT>/analysis/structurizr/<project>/…`)
- DSL files are only rewritten when their content changes, enabling incremental updates without unnecessary file churn.

## C4 Model Overview

| Level | Diagram | Purpose | CLI Example |
|-------|---------|---------|-------------|
| L1 | System Context | Shows platform + actors + external systems | `--diagram-type c4-context` |
| L2 | Container | Shows microservices, storage, queues | `--diagram-type c4-container` |
| L3 | Component | Shows controllers/services/repos inside a container | `--diagram-type c4-component` or `--c4` |
| Dynamic | Sequence-style runtime view | `--diagram-type c4-dynamic` |

**Benefits**

- Standardized notation via [C4-PlantUML](https://github.com/plantuml-stdlib/C4-PlantUML)
- Hierarchical navigation (L1→L2→L3 + dynamic) from the same analysis data
- Compatible with Structurizr DSL export for model-based documentation and CLI automation

To generate the whole stack in one shot:

```bash
uv run python generate_all_diagrams.py --project INSURANCE --hierarchy
```

## Example Outputs

After running the CLI, diagrams live under `docs-nttc/projects/<PROJECT>/analysis/c4-diagrams/`. Key example files:

- `L1-insurance-platform-context.puml` – INSURANCE System Context
- `L2-insurance-platform-containers.puml` – INSURANCE Container view
- `L3-insurance-policy-business-components.puml` – Service-level component view
- `insurance-policy-business-c4-dynamic.puml` – Dynamic request flow

PNG/SVG versions are emitted when `--output-format png|svg` is supplied.

## Migration Guide (Classic PlantUML → C4 Mode)

1. **Baseline**: Run the existing PlantUML workflow (no new flags) to confirm current diagrams.
2. **Pilot C4**: Execute `--project <NAME> --c4 --export-dsl` for one service to inspect C4 + Structurizr outputs.
3. **Adopt Hierarchy**: Use `--hierarchy` to generate L1/L2/L3/Dynamic for the full project. Validate style/payload via the new test suites (`tests/test_c4_syntax_correctness.py`).
4. **Backfill Documentation**: Reference the generated DSL in Confluence or the CI pipeline via Structurizr CLI export.
5. **Parallel Run**: Keep classic PlantUML outputs (default behavior) until stakeholders confirm C4 parity, then gradually shift Confluence embedding to the C4 diagrams.

## Python API Usage

### Analyze a Single Service

```python
from vds_diagram_generator import JavaCodeAnalyzer, PlantUMLGenerator, get_settings

settings = get_settings()

# Analyze a service
source_path = settings.get_project_source_path("INSURANCE")
analyzer = JavaCodeAnalyzer(source_path)
analysis = analyzer.analyze_service("insurance-policy-business")

# Generate diagrams
output_path = settings.get_project_docs_path("INSURANCE") / "insurance-policy-business"
generator = PlantUMLGenerator(output_path)
sequence_path, component_path, split_paths = generator.save_diagrams(analysis, output_path)

print(f"Sequence diagram: {sequence_path}")
print(f"Component diagram: {component_path}")
print(f"Split diagrams: {split_paths}")
```

### Discover Services in a Project

```python
from vds_diagram_generator import get_settings

settings = get_settings()

# List all services in LEP project
services = settings.discover_services("LEP")
print(f"Found {len(services)} services: {services}")
```

### Get Project Configuration

```python
from vds_diagram_generator import PROJECTS

for name, config in PROJECTS.items():
    print(f"{name}: source={config.source_folder}, docs={config.docs_folder}")
```

## Components

### JavaCodeAnalyzer

Parses Java source files to extract:

- `@RestController` / `@Controller` classes
- `@Service` annotated classes
- `@Repository` interfaces and JpaRepository extensions
- `@FeignClient` interfaces
- `@KafkaListener` handlers

### PlantUMLGenerator

Generates two types of diagrams:

- **Sequence Diagram**: Shows request flow through controllers, services, repositories
- **Component Diagram**: Shows internal architecture and external dependencies

### DiagramGeneratorSettings

Configuration management for multi-project support:

- Auto-discovers services in project folders
- Manages source and documentation paths
- Supports workspace root configuration

### UseCaseGenerator

Generates PlantUML use case diagrams from service analysis:

- **Actor Extraction**: Identifies actors from Feign clients (external), controllers (internal), and Kafka handlers (system)
- **Use Case Mapping**: Maps REST endpoints to use cases (each endpoint = one use case)
- **Grouping**: Groups use cases by controller or service for better organization
- **Relationships**: Creates actor → use case and use case dependency relationships

## Source Code Analysis

The diagram generator extracts information directly from Java source code using annotation patterns:

### Analysis Features

- **REST Endpoint Extraction**: Extracts endpoints from `@GetMapping`, `@PostMapping`, `@PutMapping`, `@DeleteMapping` annotations
- **Service Method Inference**: Infers which service method is called by each endpoint based on injected dependencies and method names
- **Kafka Topic Extraction**: Extracts Kafka topics from `@KafkaListener` annotations
- **Feign Client Detection**: Identifies external service integrations from `@FeignClient` annotations
- **Repository Detection**: Detects data access layers from `@Repository` and `JpaRepository`/`CrudRepository` extensions

### Supported Annotation Patterns

- `@RestController`, `@Controller` - REST API controllers
- `@Service` - Business logic services
- `@Repository`, `JpaRepository<T, ID>`, `CrudRepository<T, ID>` - Data access repositories
- `@FeignClient(name = "...")` - External service clients
- `@KafkaListener(topics = "...")` - Message queue handlers
- `@RequestMapping`, `@GetMapping`, `@PostMapping`, `@PutMapping`, `@DeleteMapping` - HTTP endpoint mappings

### Code → Diagram Mapping Example

```java
@RestController
@RequestMapping("/api/policy")
public class PolicyController {
    @Autowired
    private PolicyService policyService;
    
    @GetMapping("/{id}")
    public Policy getPolicy(@PathVariable String id) {
        return policyService.getPolicyById(id);
    }
}
```

**Generated Sequence Diagram**:

```plantuml
Client -> PolicyController : GET /api/policy/{id}
PolicyController -> PolicyService : getPolicyById()
PolicyService --> PolicyController : response
PolicyController --> Client : HTTP response
```

**Generated Use Case Diagram**:

```plantuml
actor "Client" as Client
package "PolicyController" {
  usecase "GET /api/policy/{id}" as (GET__api_policy_id)
}
Client --> (GET__api_policy_id)
```

All diagrams are generated from actual source code, ensuring accuracy and automatic updates when code changes.

## Requirements

- Python 3.11+
- uv (Python package manager)
- pydantic >= 2.0.0
- pydantic-settings>=2.13.1
- hypothesis >= 6.0.0 (dev dependency for property-based testing)

## Testing

```bash
# Ensure dev dependencies are installed
uv sync --group dev

# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=vds_diagram_generator

# Run specific test file
uv run pytest tests/test_analyzer_completeness.py -v
```

## Linting

```bash
# Check code style
uv run ruff check .

# Auto-fix issues
uv run ruff check --fix .
```

## Diagram Naming Convention

- Sequence diagrams: `{service-name}-sequence.puml`
- Component diagrams: `{service-name}-component.puml`

## Output Locations

Diagrams are saved to project-specific documentation folders:

- INSURANCE: `docs-nttc/projects/INSURANCE/analysis/current-state/{service-name}/`
- LEP: `docs-nttc/projects/LEP/analysis/current-state/{service-name}/`
- SAVING: `docs-nttc/projects/SAVING/analysis/current-state/{service-name}/`
- EKYC: `docs-nttc/projects/EKYC/analysis/current-state/{service-name}/`

## Structurizr DSL Integration

The diagram generator supports Structurizr DSL for model-based architecture documentation.

### Generate Structurizr DSL Workspace

```python
from vds_diagram_generator import StructurizrDSLGenerator, JavaCodeAnalyzer
from pathlib import Path

# Analyze a service
analyzer = JavaCodeAnalyzer(Path("INSURANCE-project"))
analysis = analyzer.analyze_service("insurance-policy-business")

# Generate Structurizr DSL
gen = StructurizrDSLGenerator(Path("docs-nttc/projects/INSURANCE/analysis"))
dsl_path = gen.save_service_workspace(analysis)
print(f"Generated: {dsl_path}")

# Generate platform-level workspace
platform_path = gen.save_platform_workspace("INSURANCE")
print(f"Platform workspace: {platform_path}")
```

### Export to PlantUML using Structurizr CLI

```python
from vds_diagram_generator import StructurizrCLI, ExportFormat, check_structurizr_cli
from pathlib import Path

# Check CLI availability
status = check_structurizr_cli()
print(f"CLI available: {status['available']}")

# Export workspace to C4-PlantUML
cli = StructurizrCLI()
if cli.is_available():
    result = cli.export_to_c4_plantuml(
        workspace_path=Path("workspace.dsl"),
        output_dir=Path("exported")
    )
    print(f"Exported {len(result.exported_files)} files")
```

### High-Level Exporter

```python
from vds_diagram_generator import StructurizrExporter, ExportFormat
from pathlib import Path

exporter = StructurizrExporter(Path("output"))

# Export service with automatic DSL generation and CLI export
dsl_path, export_result = exporter.export_service(analysis, ExportFormat.C4_PLANTUML)

# Export entire platform
platform_dsl, platform_export = exporter.export_platform("INSURANCE")
```

### Install Structurizr CLI

```bash
# macOS
brew install structurizr-cli

# Other platforms
# Download from: https://github.com/structurizr/cli/releases
```

## CI/CD Integration

The diagram generator includes a GitHub Actions workflow for automated diagram generation.

### Workflow Features

- **Automatic triggers**: Runs on code changes to Java source files
- **Manual dispatch**: Generate diagrams for specific projects on demand
- **PlantUML rendering**: Converts .puml files to PNG images
- **Structurizr export**: Generates C4-PlantUML from DSL workspaces
- **Confluence upload**: Optional upload to Confluence (requires secrets)
- **PR comments**: Adds diagram summary to pull requests

### Workflow Location

`.github/workflows/diagram-generation.yml`

### Manual Trigger

```bash
# Via GitHub CLI
gh workflow run diagram-generation.yml -f project=INSURANCE -f upload_confluence=false
```

### Required Secrets

For Confluence upload:

- `EXTERNAL_CONFLUENCE_TOKEN`: Confluence API token
- `CONFLUENCE_URL`: Confluence base URL

## Project Structure

```
vds-scripts/diagram_generator/
├── pyproject.toml              # Project configuration
├── generate_all_diagrams.py    # CLI entry point
├── render_png.py               # PNG rendering utility
├── .github/
│   └── workflows/
│       └── diagram-generation.yml  # CI/CD workflow
├── src/
│   └── vds_diagram_generator/
│       ├── __init__.py         # Package exports
│       ├── analyzer.py         # Java code analyzer
│       ├── c4_generator.py     # C4-PlantUML generator
│       ├── config.py           # Multi-project configuration
│       ├── generator.py        # PlantUML generator
│       ├── models.py           # Data models
│       ├── structurizr_generator.py  # Structurizr DSL generator
│       └── structurizr_cli.py  # Structurizr CLI integration
└── tests/
    ├── test_analyzer_completeness.py
    ├── test_component_coverage.py
    ├── test_png_generation.py
    └── test_style_consistency.py
```
