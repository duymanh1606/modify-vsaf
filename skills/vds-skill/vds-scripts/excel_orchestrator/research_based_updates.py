"""
Research-Based Updates to Estimation

Based on MCP research, this script:
1. Identifies missing non-functional requirements tasks
2. Adds comprehensive testing coverage
3. Enhances infrastructure and DevOps tasks
4. Adds security and compliance tasks
5. Improves BRD coverage further
"""

import re
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.styles import Alignment, Border, Side

EXCEL_PATH = Path(
    "../../insurance-document/projects/INSURANCE/analysis/reference/vietin/estimation/Estimation_HTBH.xlsx"
)
BRD_PATH = Path("../../insurance-document/projects/INSURANCE/analysis/reference/BRD/BRD_NTBH_2.0.md")

# Additional tasks based on research findings
RESEARCH_BASED_TASKS = {
    # Non-functional requirements that might be missing
    "performance_testing": {
        "services": ["Platform Infrastructure & Testing"],
        "tasks": [
            {
                "category": "Kiểm thử",
                "name": "Performance Testing: Load testing, stress testing, và capacity planning",
                "complexity": "Phức tạp",
                "base_effort": 10,
                "brd_ref": "NFR",
                "multiplier": "1.59x (base) × 1.05x (performance)",
            },
            {
                "category": "Kiểm thử",
                "name": "Performance Optimization: Database query optimization, caching strategy",
                "complexity": "Phức tạp",
                "base_effort": 8,
                "brd_ref": "NFR",
                "multiplier": "1.59x (base) × 1.05x (performance)",
            },
        ],
    },
    "security_testing": {
        "services": ["Platform Infrastructure & Testing", "Security Gateway"],
        "tasks": [
            {
                "category": "Kiểm thử",
                "name": "Security Testing: Penetration testing, vulnerability scanning",
                "complexity": "Phức tạp",
                "base_effort": 8,
                "brd_ref": "NFR",
                "multiplier": "1.59x (base) × 1.05x (compliance)",
            },
            {
                "category": "Bảo mật",
                "name": "Security Audit: Code review, dependency scanning, OWASP compliance",
                "complexity": "Trung bình",
                "base_effort": 5,
                "brd_ref": "NFR",
                "multiplier": "1.59x (base) × 1.05x (compliance)",
            },
        ],
    },
    "accessibility_testing": {
        "services": ["Customer Interface"],
        "tasks": [
            {
                "category": "Kiểm thử",
                "name": "Accessibility Testing: WCAG 2.1 AA compliance testing",
                "complexity": "Trung bình",
                "base_effort": 5,
                "brd_ref": "NFR",
                "multiplier": "1.59x (base)",
            }
        ],
    },
    "disaster_recovery": {
        "services": ["Platform Infrastructure & Testing"],
        "tasks": [
            {
                "category": "Triển khai",
                "name": "Disaster Recovery Planning: Backup strategy, failover procedures",
                "complexity": "Phức tạp",
                "base_effort": 8,
                "brd_ref": "NFR",
                "multiplier": "1.59x (base)",
            },
            {
                "category": "Triển khai",
                "name": "Disaster Recovery Testing: DR drills và recovery time validation",
                "complexity": "Trung bình",
                "base_effort": 5,
                "brd_ref": "NFR",
                "multiplier": "1.59x (base)",
            },
        ],
    },
    "monitoring_observability": {
        "services": ["Observability", "Platform Infrastructure & Testing"],
        "tasks": [
            {
                "category": "Phát triển",
                "name": "Distributed Tracing: Implement tracing across microservices",
                "complexity": "Phức tạp",
                "base_effort": 8,
                "brd_ref": "NFR",
                "multiplier": "1.59x (base)",
            },
            {
                "category": "Phát triển",
                "name": "Business Metrics Dashboard: KPI tracking và business intelligence",
                "complexity": "Trung bình",
                "base_effort": 6,
                "brd_ref": "4.10",
                "multiplier": "1.59x (base)",
            },
        ],
    },
    "compliance_testing": {
        "services": ["Platform Infrastructure & Testing"],
        "tasks": [
            {
                "category": "Kiểm thử",
                "name": "Compliance Testing: GDPR, PCI-DSS, local regulatory compliance",
                "complexity": "Phức tạp",
                "base_effort": 10,
                "brd_ref": "NFR",
                "multiplier": "1.59x (base) × 1.05x (compliance)",
            }
        ],
    },
}


def calculate_final_effort(base_effort: float, multiplier_str: str) -> tuple:
    """Calculate final effort from base effort and multiplier string."""
    multipliers = {
        "base": 1.59,
        "performance": 1.05,
        "compliance": 1.05,
        "renewal": 1.3,
        "logic": 1.3,
        "dynamic pricing": 1.2,
        "workflow": 1.25,
        "ai": 1.4,
    }

    total_multiplier = 1.0
    for key, value in multipliers.items():
        if key in multiplier_str.lower():
            total_multiplier *= value

    final_days = base_effort * total_multiplier
    final_hours = final_days * 8

    return final_days, final_hours, f"{total_multiplier:.2f}x"


def get_service_id_by_name(excel_path: Path, service_name: str) -> int:
    """Get service ID by service name."""
    wb = load_workbook(excel_path, data_only=True)
    ws = wb["VDS_Est_Detail_Services_Total"]

    for row in range(2, 60):
        name = ws.cell(row, 2).value
        service_id = ws.cell(row, 1).value

        if name and service_id:
            name_clean = str(name).split(":")[0].strip()
            if service_name.lower() in name_clean.lower() or name_clean.lower() in service_name.lower():
                return int(service_id)

    return None


def get_next_task_id(excel_path: Path, service_id: int) -> str:
    """Get next task ID for a service."""
    wb = load_workbook(excel_path, data_only=False)
    ws = wb["VDS_Task_Breakdown_Detailed"]

    max_task_num = 0
    for row in range(9, ws.max_row + 1):
        row_service_id = ws.cell(row, 1).value
        task_id = ws.cell(row, 5).value

        if row_service_id and isinstance(row_service_id, (int, float)) and int(row_service_id) == service_id:
            if task_id and isinstance(task_id, str):
                match = re.search(r"T(\d+)", str(task_id))
                if match:
                    task_num = int(match.group(1))
                    max_task_num = max(max_task_num, task_num)

    next_task_num = max_task_num + 1
    return f"S{service_id}-T{next_task_num:03d}"


def check_if_task_exists(excel_path: Path, service_id: int, task_name: str) -> bool:
    """Check if a similar task already exists."""
    wb = load_workbook(excel_path, data_only=False)
    ws = wb["VDS_Task_Breakdown_Detailed"]

    task_normalized = str(task_name).lower().strip()
    task_normalized = re.sub(r"[^\w\s]", "", task_normalized)
    task_normalized = " ".join(task_normalized.split())

    for row in range(9, ws.max_row + 1):
        row_service_id = ws.cell(row, 1).value
        row_task_name = ws.cell(row, 6).value

        if row_service_id == service_id and row_task_name:
            row_task_normalized = str(row_task_name).lower().strip()
            row_task_normalized = re.sub(r"[^\w\s]", "", row_task_normalized)
            row_task_normalized = " ".join(row_task_normalized.split())

            # Check for similarity (80% match)
            if task_normalized in row_task_normalized or row_task_normalized in task_normalized:
                return True

    return False


def add_research_based_tasks(excel_path: Path):
    """Add research-based tasks to estimation."""
    wb = load_workbook(excel_path, data_only=False)
    ws = wb["VDS_Task_Breakdown_Detailed"]

    # Get service info
    ws_services = wb["VDS_Est_Detail_Services_Total"]
    service_info = {}
    for row in range(2, 60):
        service_id = ws_services.cell(row, 1).value
        service_name = ws_services.cell(row, 2).value
        responsibility = ws_services.cell(row, 6).value

        if service_id and isinstance(service_id, (int, float)) and service_name:
            name_clean = str(service_name).split(":")[0].strip()
            service_info[int(service_id)] = {
                "name": name_clean,
                "full_name": str(service_name).strip(),
                "responsibility": responsibility or "Unknown",
            }

    added_count = 0
    skipped_count = 0

    print("=" * 80)
    print("Adding Research-Based Tasks")
    print("=" * 80)

    # Add tasks for each research area
    for research_area, area_data in RESEARCH_BASED_TASKS.items():
        print(f"\n{research_area}:")

        for service_name_pattern in area_data["services"]:
            # Find matching service
            service_id = None
            for sid, info in service_info.items():
                if service_name_pattern.lower() in info["name"].lower():
                    service_id = sid
                    break

            if not service_id:
                print(f"  ⚠️ Service not found: {service_name_pattern}")
                continue

            service_data = service_info[service_id]
            print(f"  ✓ Found service: {service_id} - {service_data['name']}")

            # Add tasks
            for task_data in area_data["tasks"]:
                # Check if task already exists
                if check_if_task_exists(excel_path, service_id, task_data["name"]):
                    skipped_count += 1
                    print(f"    ⊘ Skipped (exists): {task_data['name'][:50]}...")
                    continue

                # Get next task ID
                task_id = get_next_task_id(excel_path, service_id)

                # Calculate final effort
                final_days, final_hours, multiplier_applied = calculate_final_effort(
                    task_data["base_effort"], task_data["multiplier"]
                )

                # Find next empty row
                next_row = ws.max_row + 1

                # Set values
                ws.cell(next_row, 1, service_id)
                ws.cell(next_row, 2, service_data["full_name"])
                ws.cell(next_row, 3, service_data["responsibility"])
                ws.cell(next_row, 4, task_data["category"])
                ws.cell(next_row, 5, task_id)
                ws.cell(next_row, 6, task_data["name"])
                ws.cell(next_row, 7, task_data["brd_ref"])
                ws.cell(next_row, 8, task_data["complexity"])
                ws.cell(next_row, 9, task_data["base_effort"])
                ws.cell(next_row, 10, task_data["multiplier"])
                ws.cell(next_row, 11, final_days)
                ws.cell(next_row, 12, final_hours)
                ws.cell(next_row, 13, "")
                ws.cell(next_row, 14, f"Added based on research: {research_area}")

                # Apply formatting
                border = Border(
                    left=Side(style="thin"),
                    right=Side(style="thin"),
                    top=Side(style="thin"),
                    bottom=Side(style="thin"),
                )

                for col in range(1, ws.max_column + 1):
                    cell = ws.cell(next_row, col)
                    cell.border = border

                    # Apply alignment
                    if col in [1, 5]:
                        cell.alignment = Alignment(horizontal="center", vertical="center")
                    elif col in [9, 11, 12]:
                        cell.alignment = Alignment(horizontal="right", vertical="center")
                        if isinstance(cell.value, (int, float)):
                            if col in [9, 11]:
                                cell.number_format = "#,##0.00"
                            elif col == 12:
                                cell.number_format = "#,##0"
                    else:
                        cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

                added_count += 1
                print(f"    ✓ Added: {task_id} - {task_data['name'][:50]}...")

    wb.save(excel_path)
    print(f"\n✅ Added {added_count} research-based tasks")
    print(f"⊘ Skipped {skipped_count} tasks (already exist)")

    return added_count


def improve_brd_references_further(excel_path: Path):
    """Further improve BRD references based on research."""
    wb = load_workbook(excel_path, data_only=False)
    ws = wb["VDS_Task_Breakdown_Detailed"]

    # Enhanced keyword mapping
    brd_enhancements = {
        "lưu đơn hàng": "3.3.6",
        "sửa đơn hàng": "3.3.6",
        "hủy đơn hàng": "3.3.6",
        "mã giới thiệu": "3.3.7",
        "referral": "3.3.7",
        "mã giảm giá": "3.3.8",
        "voucher": "3.3.8",
        "thanh toán đơn hàng": "3.3.9",
        "payment": "3.3.9",
        "performance": "NFR",
        "scalability": "NFR",
        "security": "NFR",
        "compliance": "NFR",
        "accessibility": "NFR",
        "monitoring": "NFR",
        "observability": "NFR",
        "disaster recovery": "NFR",
        "backup": "NFR",
        "failover": "NFR",
    }

    updated_count = 0

    for row in range(9, ws.max_row + 1):
        task_name = ws.cell(row, 6).value
        current_brd_ref = ws.cell(row, 7).value

        if task_name:
            task_lower = str(task_name).lower()

            # Find matching BRD references
            matched_refs = []
            for keyword, brd_ref in brd_enhancements.items():
                if keyword in task_lower and brd_ref not in matched_refs:
                    matched_refs.append(brd_ref)

            # Update if we found references
            if matched_refs:
                new_ref = ", ".join(sorted(set(matched_refs))[:3])

                if not current_brd_ref or str(current_brd_ref) == "N/A" or len(str(current_brd_ref)) < 5:
                    ws.cell(row, 7, new_ref)
                    updated_count += 1
                else:
                    existing_refs = [r.strip() for r in str(current_brd_ref).split(",")]
                    new_refs_to_add = [r for r in matched_refs if r not in existing_refs]

                    if new_refs_to_add:
                        combined = sorted(set(existing_refs + new_refs_to_add))
                        ws.cell(row, 7, ", ".join(combined[:3]))
                        updated_count += 1

    wb.save(excel_path)
    print(f"✅ Improved BRD references for {updated_count} tasks")
    return updated_count


def main():
    """Main execution."""
    print("=" * 80)
    print("Research-Based Updates to Estimation")
    print("=" * 80)

    # Step 1: Add research-based tasks
    print("\nStep 1: Adding research-based tasks...")
    added_count = add_research_based_tasks(EXCEL_PATH)

    # Step 2: Improve BRD references
    print("\nStep 2: Improving BRD references...")
    brd_updated = improve_brd_references_further(EXCEL_PATH)

    # Step 3: Recalculate task IDs and group by service
    print("\nStep 3: Recalculating task IDs...")
    wb = load_workbook(EXCEL_PATH, data_only=False)
    ws = wb["VDS_Task_Breakdown_Detailed"]

    current_service_id = None
    task_counter = 1

    for row in range(9, ws.max_row + 1):
        service_id = ws.cell(row, 1).value

        if service_id and isinstance(service_id, (int, float)):
            service_id_int = int(service_id)

            if service_id_int != current_service_id:
                current_service_id = service_id_int
                task_counter = 1

            task_id = f"S{service_id_int}-T{task_counter:03d}"
            ws.cell(row, 5, task_id)
            task_counter += 1

    wb.save(EXCEL_PATH)
    print("  ✅ Task IDs recalculated")

    # Final summary
    print("\n" + "=" * 80)
    print("Research-Based Updates Completed")
    print("=" * 80)
    print("\nSummary:")
    print(f"  Tasks added: {added_count}")
    print(f"  BRD references improved: {brd_updated}")
    print(f"  Total tasks: {ws.max_row - 8}")


if __name__ == "__main__":
    main()
