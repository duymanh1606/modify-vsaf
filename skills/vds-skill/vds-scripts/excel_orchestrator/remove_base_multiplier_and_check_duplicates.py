"""
Remove Base Multiplier (1.59x -> 1.0x) and Check for Duplicates/Overlaps

This script:
1. Removes the 1.59x base multiplier from all tasks
2. Recalculates final efforts with only specific multipliers
3. Checks for duplicate tasks
4. Checks for overlapping tasks
5. Updates summary section
"""

import re
from pathlib import Path

from openpyxl import load_workbook

EXCEL_PATH = Path(
    "../../insurance-document/projects/INSURANCE/analysis/reference/vietin/estimation/Estimation_HTBH.xlsx"
)


def normalize_task_name(name: str) -> str:
    """Normalize task name for comparison."""
    if not name:
        return ""
    normalized = re.sub(r"[^\w\s]", "", str(name).lower().strip())
    normalized = " ".join(normalized.split())
    return normalized


def calculate_final_effort_no_base(base_effort: float, multiplier_str: str) -> tuple:
    """Calculate final effort WITHOUT base 1.59x multiplier."""
    if not multiplier_str:
        return base_effort, base_effort * 8, "1.0x"

    multiplier_str_clean = str(multiplier_str).strip()

    # First, try to extract numeric multipliers from string (e.g., "1.05x × 1.05x")
    mult_matches = re.findall(r"(\d+\.?\d*)x", multiplier_str_clean, re.IGNORECASE)

    if mult_matches:
        # Multiply all found multipliers
        total_multiplier = 1.0
        for m in mult_matches:
            total_multiplier *= float(m)
    else:
        # Fallback: check for keywords
        multipliers = {
            "performance": 1.05,
            "compliance": 1.05,
            "renewal": 1.3,
            "logic": 1.3,
            "dynamic pricing": 1.2,
            "workflow": 1.25,
            "ai": 1.4,
            "claims": 1.25,
            "payment": 1.15,
            "comparison": 1.1,
        }

        total_multiplier = 1.0
        multiplier_str_lower = multiplier_str_clean.lower()

        for key, value in multipliers.items():
            if key in multiplier_str_lower:
                total_multiplier *= value

        # If no keywords found, default to 1.0
        if total_multiplier == 1.0 and "1.0x" not in multiplier_str_clean:
            # Try to find any number in the string
            num_match = re.search(r"(\d+\.?\d*)", multiplier_str_clean)
            if num_match:
                total_multiplier = float(num_match.group(1))

    final_days = base_effort * total_multiplier
    final_hours = final_days * 8

    multiplier_display = f"{total_multiplier:.2f}x" if total_multiplier != 1.0 else "1.0x"

    return final_days, final_hours, multiplier_display


def find_duplicates(ws):
    """Find duplicate tasks."""
    duplicates = []
    task_signatures = {}

    for row in range(9, ws.max_row + 1):
        service_id = ws.cell(row, 1).value
        task_name = ws.cell(row, 6).value

        if service_id and task_name:
            signature = f"{service_id}_{normalize_task_name(task_name)}"

            if signature in task_signatures:
                duplicates.append(
                    {
                        "row1": task_signatures[signature],
                        "row2": row,
                        "service_id": service_id,
                        "task_name": task_name,
                    }
                )
            else:
                task_signatures[signature] = row

    return duplicates


def find_overlaps(ws):
    """Find overlapping tasks (similar tasks in same service)."""
    overlaps = []
    service_tasks = {}

    # Group tasks by service
    for row in range(9, ws.max_row + 1):
        service_id = ws.cell(row, 1).value
        task_name = ws.cell(row, 6).value

        if service_id and task_name:
            if service_id not in service_tasks:
                service_tasks[service_id] = []

            task_words = set(normalize_task_name(task_name).split())
            service_tasks[service_id].append({"row": row, "name": task_name, "words": task_words})

    # Find overlaps
    for service_id, tasks in service_tasks.items():
        for i, task1 in enumerate(tasks):
            for task2 in tasks[i + 1 :]:
                common_words = task1["words"] & task2["words"]
                total_words = task1["words"] | task2["words"]

                if len(total_words) > 0:
                    overlap_ratio = len(common_words) / len(total_words)
                    # Consider overlap if >70% word overlap and at least 3 common words
                    if overlap_ratio > 0.7 and len(common_words) >= 3:
                        overlaps.append(
                            {
                                "service_id": service_id,
                                "row1": task1["row"],
                                "row2": task2["row"],
                                "task1": task1["name"],
                                "task2": task2["name"],
                                "overlap": overlap_ratio,
                            }
                        )

    return overlaps


def remove_base_multiplier(excel_path: Path):
    """Remove 1.59x base multiplier and recalculate efforts."""
    wb = load_workbook(excel_path, data_only=False)
    ws = wb["VDS_Task_Breakdown_Detailed"]

    print("=" * 80)
    print("Removing Base Multiplier (1.59x -> 1.0x)")
    print("=" * 80)

    updated_count = 0

    for row in range(9, ws.max_row + 1):
        base_effort = ws.cell(row, 9).value  # Column I: Base Effort
        multiplier_str = ws.cell(row, 10).value  # Column J: Multiplier Applied

        if base_effort and isinstance(base_effort, (int, float)):
            # Remove 1.59x from multiplier string
            if multiplier_str:
                multiplier_str_clean = str(multiplier_str).replace("1.59x", "").replace("(base)", "").strip()
                multiplier_str_clean = re.sub(r"\s*×\s*", " × ", multiplier_str_clean)
                multiplier_str_clean = re.sub(r"^\s*×\s*", "", multiplier_str_clean)
                multiplier_str_clean = multiplier_str_clean.strip()

                if not multiplier_str_clean or multiplier_str_clean == "×":
                    multiplier_str_clean = "1.0x"
            else:
                multiplier_str_clean = "1.0x"

            # Recalculate final effort
            final_days, final_hours, multiplier_applied = calculate_final_effort_no_base(
                float(base_effort), multiplier_str_clean
            )

            # Update cells
            ws.cell(row, 10, multiplier_str_clean)  # Multiplier
            ws.cell(row, 11, final_days)  # Final Days
            ws.cell(row, 12, final_hours)  # Final Hours

            # Format numbers
            ws.cell(row, 11).number_format = "#,##0.00"
            ws.cell(row, 12).number_format = "#,##0"

            updated_count += 1

    wb.save(excel_path)
    print(f"✅ Updated {updated_count} tasks")
    return updated_count


def check_and_report_duplicates(excel_path: Path):
    """Check for duplicates and overlaps."""
    wb = load_workbook(excel_path, data_only=False)
    ws = wb["VDS_Task_Breakdown_Detailed"]

    print("\n" + "=" * 80)
    print("Checking for Duplicates and Overlaps")
    print("=" * 80)

    duplicates = find_duplicates(ws)
    overlaps = find_overlaps(ws)

    print(f"\nDuplicate Tasks: {len(duplicates)}")
    if duplicates:
        for dup in duplicates[:20]:
            print(f"  Row {dup['row1']} and {dup['row2']}: Service {dup['service_id']}")
            print(f"    Task: {dup['task_name'][:70]}...")

    print(f"\nOverlapping Tasks: {len(overlaps)}")
    if overlaps:
        for ov in overlaps[:20]:
            print(f"  Service {ov['service_id']}: Row {ov['row1']} vs {ov['row2']} ({ov['overlap']:.0%} overlap)")
            print(f"    Task1: {ov['task1'][:60]}...")
            print(f"    Task2: {ov['task2'][:60]}...")

    return duplicates, overlaps


def update_summary(excel_path: Path):
    """Update summary section with recalculated totals."""
    wb = load_workbook(excel_path, data_only=False)
    ws = wb["VDS_Task_Breakdown_Detailed"]

    print("\n" + "=" * 80)
    print("Updating Summary Section")
    print("=" * 80)

    # Recalculate totals
    total_tasks = 0
    total_days = 0.0
    total_hours = 0.0

    for row in range(9, ws.max_row + 1):
        task_id = ws.cell(row, 5).value
        days = ws.cell(row, 11).value
        hours = ws.cell(row, 12).value

        if task_id:
            total_tasks += 1

        if isinstance(days, (int, float)):
            total_days += float(days)

        if isinstance(hours, (int, float)):
            total_hours += float(hours)

    # Update summary rows
    ws.cell(2, 2, total_tasks)  # Row 2: Total Tasks
    ws.cell(3, 2, total_days)  # Row 3: Total Days
    ws.cell(4, 2, total_hours)  # Row 4: Total Hours

    # Format summary values
    ws.cell(3, 2).number_format = "#,##0.00"
    ws.cell(4, 2).number_format = "#,##0"

    wb.save(excel_path)

    print("✅ Summary updated:")
    print(f"   Total Tasks: {total_tasks}")
    print(f"   Total Days: {total_days:.2f}")
    print(f"   Total Hours: {total_hours:.0f}")


def main():
    """Main execution."""
    print("=" * 80)
    print("Remove Base Multiplier and Check Duplicates")
    print("=" * 80)

    # Step 1: Check for duplicates/overlaps BEFORE changes
    print("\nStep 1: Checking for duplicates/overlaps...")
    duplicates, overlaps = check_and_report_duplicates(EXCEL_PATH)

    # Step 2: Remove base multiplier
    print("\nStep 2: Removing base multiplier (1.59x -> 1.0x)...")
    updated_count = remove_base_multiplier(EXCEL_PATH)

    # Step 3: Update summary
    print("\nStep 3: Updating summary section...")
    update_summary(EXCEL_PATH)

    # Step 4: Final verification
    print("\nStep 4: Final verification...")
    duplicates_after, overlaps_after = check_and_report_duplicates(EXCEL_PATH)

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"✅ Tasks updated: {updated_count}")
    print(f"⚠️ Duplicates found: {len(duplicates_after)}")
    print(f"⚠️ Overlaps found: {len(overlaps_after)}")

    if len(duplicates_after) == 0 and len(overlaps_after) == 0:
        print("\n✅ No duplicates or overlaps found!")
    else:
        print("\n⚠️ Please review duplicates and overlaps above")


if __name__ == "__main__":
    main()
