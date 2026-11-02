"""
Group Tasks by Service ID

This script:
1. Collects all tasks grouped by Service ID
2. Reorders rows so all tasks for the same service are adjacent
3. Maintains summary section at top
4. Preserves all formatting
"""

from collections import defaultdict
from pathlib import Path

from openpyxl import load_workbook

EXCEL_PATH = Path(
    "../../insurance-document/projects/INSURANCE/analysis/reference/vietin/estimation/Estimation_HTBH.xlsx"
)


def group_tasks_by_service_id(excel_path: Path):
    """Group all tasks by Service ID and reorder rows."""
    wb = load_workbook(excel_path, data_only=False)
    ws = wb["VDS_Task_Breakdown_Detailed"]

    print("=" * 80)
    print("Grouping Tasks by Service ID")
    print("=" * 80)

    # Step 1: Collect all tasks by service ID
    print("\nStep 1: Collecting tasks by Service ID...")
    tasks_by_service = defaultdict(list)

    for row in range(9, ws.max_row + 1):  # Start from row 9 (after summary)
        service_id = ws.cell(row, 1).value

        if service_id and isinstance(service_id, (int, float)):
            service_id_int = int(service_id)

            # Collect all cell data for this row
            row_data = []
            for col in range(1, ws.max_column + 1):
                cell = ws.cell(row, col)
                row_data.append(
                    {
                        "value": cell.value,
                        "font": cell.font,
                        "fill": cell.fill,
                        "alignment": cell.alignment,
                        "border": cell.border,
                        "number_format": cell.number_format,
                    }
                )

            tasks_by_service[service_id_int].append(row_data)

    print(f"  Found {len(tasks_by_service)} services")
    print(f"  Total tasks: {sum(len(tasks) for tasks in tasks_by_service.values())}")

    # Step 2: Delete all task rows (keep summary at top)
    print("\nStep 2: Clearing existing task rows...")
    # Delete from row 9 to end
    if ws.max_row >= 9:
        ws.delete_rows(9, ws.max_row - 8)
        print(f"  ✓ Deleted rows 9 to {ws.max_row}")

    # Step 3: Reinsert tasks grouped by service ID
    print("\nStep 3: Reinserting tasks grouped by Service ID...")

    current_row = 9  # Start after summary (rows 2-8)
    task_counter_by_service = {}

    for service_id in sorted(tasks_by_service.keys()):
        tasks = tasks_by_service[service_id]
        task_counter_by_service[service_id] = 1

        print(f"  Service {service_id}: {len(tasks)} tasks")

        for task_data in tasks:
            # Insert row
            ws.insert_rows(current_row)

            # Write task data
            for col_idx, cell_data in enumerate(task_data, 1):
                cell = ws.cell(current_row, col_idx)
                cell.value = cell_data["value"]

                # Restore formatting (copy attributes, not objects)
                if cell_data["font"]:
                    from openpyxl.styles import Font

                    font = cell_data["font"]
                    cell.font = Font(
                        name=font.name,
                        size=font.size,
                        bold=font.bold,
                        italic=font.italic,
                        underline=font.underline,
                        strike=font.strike,
                        color=font.color,
                    )
                if cell_data["fill"]:
                    from openpyxl.styles import PatternFill

                    fill = cell_data["fill"]
                    if fill and fill.fill_type:
                        cell.fill = PatternFill(
                            fill_type=fill.fill_type,
                            start_color=fill.start_color,
                            end_color=fill.end_color,
                        )
                if cell_data["alignment"]:
                    from openpyxl.styles import Alignment

                    align = cell_data["alignment"]
                    if align:
                        cell.alignment = Alignment(
                            horizontal=align.horizontal,
                            vertical=align.vertical,
                            wrap_text=align.wrap_text,
                        )
                if cell_data["border"]:
                    from openpyxl.styles import Border

                    border = cell_data["border"]
                    if border:
                        cell.border = Border(
                            left=border.left,
                            right=border.right,
                            top=border.top,
                            bottom=border.bottom,
                        )
                if cell_data["number_format"]:
                    cell.number_format = cell_data["number_format"]

            # Update task ID
            task_id = f"S{service_id}-T{task_counter_by_service[service_id]:03d}"
            ws.cell(current_row, 5, task_id)  # Task ID column
            task_counter_by_service[service_id] += 1

            current_row += 1

    wb.save(excel_path)
    print(f"\n✅ Reordered {sum(len(tasks) for tasks in tasks_by_service.values())} tasks")
    print("✅ All tasks are now grouped by Service ID")

    # Step 4: Verify grouping
    print("\nStep 4: Verifying grouping...")
    current_service_id = None
    service_changes = []

    for row in range(9, ws.max_row + 1):
        service_id = ws.cell(row, 1).value

        if service_id and isinstance(service_id, (int, float)):
            service_id_int = int(service_id)

            if current_service_id is not None and service_id_int != current_service_id:
                service_changes.append({"row": row, "from": current_service_id, "to": service_id_int})

            current_service_id = service_id_int

    if service_changes:
        print(f"  ✅ Service transitions at {len(service_changes)} points:")
        for change in service_changes[:10]:
            print(f"    Row {change['row']}: Service {change['from']} → Service {change['to']}")
    else:
        print("  ✅ All tasks are properly grouped")

    # Check for gaps
    gaps_found = 0
    for service_id in sorted(tasks_by_service.keys()):
        service_rows = []
        for row in range(9, ws.max_row + 1):
            if ws.cell(row, 1).value == service_id:
                service_rows.append(row)

        if service_rows:
            min_row = min(service_rows)
            max_row = max(service_rows)
            expected_count = max_row - min_row + 1
            actual_count = len(service_rows)

            if expected_count != actual_count:
                gaps_found += 1
                print(f"  ⚠️ Service {service_id}: {actual_count} tasks span {expected_count} rows (gap found)")

    if gaps_found == 0:
        print("  ✅ No gaps found - all tasks are adjacent")
    else:
        print(f"  ⚠️ Found gaps in {gaps_found} services")

    return len(tasks_by_service), sum(len(tasks) for tasks in tasks_by_service.values())


def main():
    """Main execution."""
    services_count, tasks_count = group_tasks_by_service_id(EXCEL_PATH)

    print("\n" + "=" * 80)
    print("Grouping completed!")
    print("=" * 80)
    print("\nSummary:")
    print(f"  Services: {services_count}")
    print(f"  Tasks: {tasks_count}")
    print("  All tasks grouped by Service ID: ✅")


if __name__ == "__main__":
    main()
