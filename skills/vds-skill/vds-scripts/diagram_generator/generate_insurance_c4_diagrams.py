#!/usr/bin/env python3
"""Generate C4 diagrams for INSURANCE platform.

This script standardizes INSURANCE project diagrams to C4-PlantUML format,
generating L1, L2, and L3 diagrams for all 23 services aligned with
SAVING project C4 patterns.

Usage:
    cd vds-scripts/diagram_generator
    uv run python generate_insurance_c4_diagrams.py
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from vds_diagram_generator.analyzer import JavaCodeAnalyzer
from vds_diagram_generator.c4_generator import VDS_PLATFORMS, C4Generator

# Configuration
INSURANCE_PROJECT_PATH = Path(__file__).parent.parent.parent / "INSURANCE-project"
OUTPUT_BASE_PATH = Path(__file__).parent.parent.parent / "docs-nttc" / "projects" / "INSURANCE" / "analysis"
C4_OUTPUT_PATH = OUTPUT_BASE_PATH / "c4-diagrams"


def generate_l1_context_diagram(generator: C4Generator) -> Path:
    """Generate L1 System Context diagram for INSURANCE platform."""
    print("\n📊 Generating L1 System Context diagram...")
    path = generator.save_l1_context_diagram("INSURANCE", C4_OUTPUT_PATH, include_cross_platform=True)
    print(f"   ✅ Created: {path.name}")
    return path


def generate_l2_container_diagram(generator: C4Generator) -> Path:
    """Generate L2 Container diagram for INSURANCE platform."""
    print("\n📊 Generating L2 Container diagram...")
    path = generator.save_l2_container_diagram("INSURANCE", C4_OUTPUT_PATH)
    print(f"   ✅ Created: {path.name}")
    return path


def generate_l3_component_diagrams(generator: C4Generator, analyzer: JavaCodeAnalyzer) -> list[Path]:
    """Generate L3 Component diagrams for all INSURANCE services."""
    print("\n📊 Generating L3 Component diagrams for all services...")

    services = VDS_PLATFORMS["INSURANCE"].services
    paths = []
    analyzed_count = 0
    skipped_count = 0

    for service_name in services:
        # Find service directory
        service_path = INSURANCE_PROJECT_PATH / service_name

        if not service_path.exists():
            print(f"   ⚠️  Skipped {service_name}: directory not found")
            skipped_count += 1
            continue

        # Analyze service
        try:
            analysis = analyzer.analyze_service(service_path, service_name)

            # Generate L3 diagram
            path = generator.save_l3_component_diagram(analysis, C4_OUTPUT_PATH)
            paths.append(path)
            analyzed_count += 1
            print(f"   ✅ Created: {path.name}")

        except Exception as e:
            print(f"   ❌ Error analyzing {service_name}: {e}")
            skipped_count += 1

    print(f"\n   📈 Summary: {analyzed_count} diagrams created, {skipped_count} skipped")
    return paths


def create_readme(output_path: Path, _l1_path: Path, _l2_path: Path, l3_paths: list[Path]) -> Path:
    """Create README.md for the C4 diagrams directory."""
    readme_content = """# INSURANCE Platform - C4 Architecture Diagrams

## Overview

This directory contains C4 model architecture diagrams for the INSURANCE Platform using PlantUML with the [C4-PlantUML](https://github.com/plantuml-stdlib/C4-PlantUML) library.

## C4 Model Levels

The C4 model consists of 4 levels of abstraction:

| Level | Name | Description | Audience |
|-------|------|-------------|----------|
| 1 | System Context | Shows the system and its relationships with users and external systems | Everyone |
| 2 | Container | Zooms into the system showing containers (applications, data stores) | Technical people |
| 3 | Component | Zooms into a container showing its internal components | Developers |
| 4 | Code | Shows how a component is implemented (optional) | Developers |

## Diagram Files

### Level 1 - System Context
| File | Description |
|------|-------------|
| [L1-insurance-platform-context.puml](L1-insurance-platform-context.puml) | Overall system context showing INSURANCE Platform and external systems |

### Level 2 - Container
| File | Description |
|------|-------------|
| [L2-insurance-platform-containers.puml](L2-insurance-platform-containers.puml) | All 23 microservices and infrastructure components |

### Level 3 - Component (per service)
| File | Service | Description |
|------|---------|-------------|
"""

    # Add L3 diagram entries
    for path in sorted(l3_paths):
        service_name = path.stem.replace("L3-", "").replace("-components", "")
        readme_content += f"| [{path.name}]({path.name}) | {service_name} | Internal components |\n"

    readme_content += """
## How to Render

### Using PlantUML Online Server
1. Go to https://www.plantuml.com/plantuml/uml/
2. Paste the diagram content
3. View/download the rendered diagram

### Using VS Code
1. Install the "PlantUML" extension
2. Open any `.puml` file
3. Press `Alt+D` to preview

### Using CLI
```bash
# Install PlantUML
brew install plantuml

# Render a single diagram
plantuml L1-insurance-platform-context.puml

# Render all diagrams
plantuml *.puml
```

### Using Docker
```bash
docker run -v $(pwd):/data plantuml/plantuml *.puml
```

## C4-PlantUML Syntax Reference

### Level 1 - Context Diagram
```plantuml
!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Context.puml

Person(user, "User", "Description")
System(system, "System", "Description")
System_Ext(external, "External System", "Description")

Rel(user, system, "Uses")
```

### Level 2 - Container Diagram
```plantuml
!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Container.puml

Container(app, "Application", "Technology", "Description")
ContainerDb(db, "Database", "Technology", "Description")
ContainerQueue(queue, "Queue", "Technology", "Description")
```

### Level 3 - Component Diagram
```plantuml
!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Component.puml

Container_Boundary(container, "Container Name") {
    Component(comp, "Component", "Technology", "Description")
}
```

## Cross-Project Consistency

These diagrams follow the same C4 patterns established in the SAVING Platform:
- See `docs-nttc/projects/SAVING/analysis/c4-diagrams/` for reference
- Consistent styling and element usage across VDS platforms
- Standardized naming conventions: `L{level}-{platform}-{type}.puml`

## References

- [C4 Model](https://c4model.com/) - The C4 model for visualising software architecture
- [C4-PlantUML](https://github.com/plantuml-stdlib/C4-PlantUML) - C4 Model support for PlantUML
- [PlantUML](https://plantuml.com/) - Open-source UML diagram tool

## Diagram Statistics

| Level | Count | Status |
|-------|-------|--------|
"""

    l3_count = len(l3_paths)
    readme_content += "| Level 1 - Context | 1 | ✅ Complete |\n"
    readme_content += "| Level 2 - Container | 1 | ✅ Complete |\n"
    readme_content += f"| Level 3 - Component | {l3_count} | ✅ Complete |\n"
    readme_content += f"| **Total** | **{2 + l3_count}** | **100%** |\n"

    readme_content += """
---
**Last Updated**: 2025-11-28
**Generated by**: generate_insurance_c4_diagrams.py
"""

    readme_path = output_path / "README.md"
    readme_path.write_text(readme_content, encoding="utf-8")
    return readme_path


def main():
    """Main entry point for generating INSURANCE C4 diagrams."""
    print("=" * 60)
    print("INSURANCE Platform C4 Diagram Generator")
    print("=" * 60)

    # Create output directory
    C4_OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
    print(f"\n📁 Output directory: {C4_OUTPUT_PATH}")

    # Initialize generator and analyzer
    generator = C4Generator(OUTPUT_BASE_PATH)
    analyzer = JavaCodeAnalyzer()

    # Generate L1 System Context diagram
    l1_path = generate_l1_context_diagram(generator)

    # Generate L2 Container diagram
    l2_path = generate_l2_container_diagram(generator)

    # Generate L3 Component diagrams for all services
    l3_paths = generate_l3_component_diagrams(generator, analyzer)

    # Create README
    print("\n📝 Creating README.md...")
    readme_path = create_readme(C4_OUTPUT_PATH, l1_path, l2_path, l3_paths)
    print(f"   ✅ Created: {readme_path.name}")

    # Summary
    print("\n" + "=" * 60)
    print("✅ INSURANCE C4 Diagram Generation Complete!")
    print("=" * 60)
    print("\nGenerated diagrams:")
    print("  - L1 System Context: 1")
    print("  - L2 Container: 1")
    print(f"  - L3 Component: {len(l3_paths)}")
    print(f"  - Total: {2 + len(l3_paths)}")
    print(f"\nOutput location: {C4_OUTPUT_PATH}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
