"""
Finalize BRD Coverage: Remove Duplicates and Move Summary to Top

This script:
1. Checks for and removes duplicate tasks
2. Increases BRD coverage further
3. Moves summary section to the top (after headers)
4. Ensures no duplication
"""

import re
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.styles import Border, PatternFill, Side

EXCEL_PATH = Path(
    "../../insurance-document/projects/INSURANCE/analysis/reference/vietin/estimation/Estimation_HTBH.xlsx"
)
BRD_PATH = Path("../../insurance-document/projects/INSURANCE/analysis/reference/BRD/BRD_NTBH_2.0.md")


def find_duplicate_tasks(excel_path: Path) -> list[tuple[int, int]]:
    """Find duplicate tasks (same task name in same service)."""
    wb = load_workbook(excel_path, data_only=False)
    ws = wb["VDS_Task_Breakdown_Detailed"]

    # Track tasks by service and task name
    task_map = {}  # {(service_id, task_name_normalized): [row_numbers]}
    duplicates = []

    for row in range(2, ws.max_row + 1):
        service_id = ws.cell(row, 1).value
        task_name = ws.cell(row, 6).value

        if service_id and isinstance(service_id, (int, float)) and task_name:
            service_id_int = int(service_id)
            # Normalize task name for comparison
            task_normalized = str(task_name).lower().strip()
            task_normalized = re.sub(r"[^\w\s]", "", task_normalized)
            task_normalized = " ".join(task_normalized.split())

            key = (service_id_int, task_normalized)
            if key not in task_map:
                task_map[key] = []
            task_map[key].append(row)

    # Find duplicates (same task in same service)
    for _key, rows in task_map.items():
        if len(rows) > 1:
            # Keep first occurrence, mark others as duplicates
            duplicates.extend(rows[1:])

    return duplicates


def remove_duplicates(excel_path: Path):
    """Remove duplicate tasks."""
    print("Checking for duplicate tasks...")
    duplicates = find_duplicate_tasks(excel_path)

    if not duplicates:
        print("✅ No duplicate tasks found")
        return 0

    print(f"Found {len(duplicates)} duplicate tasks")

    wb = load_workbook(excel_path, data_only=False)
    ws = wb["VDS_Task_Breakdown_Detailed"]

    # Delete duplicate rows in reverse order
    for row in sorted(duplicates, reverse=True):
        task_name = ws.cell(row, 6).value
        service_id = ws.cell(row, 1).value
        print(f"  Removing duplicate: Row {row} - Service {service_id} - {task_name[:50]}...")
        ws.delete_rows(row)

    # Recalculate task IDs
    current_service_id = None
    task_counter = 1

    for row in range(2, ws.max_row + 1):
        service_id = ws.cell(row, 1).value

        if service_id and isinstance(service_id, (int, float)):
            service_id_int = int(service_id)

            if service_id_int != current_service_id:
                current_service_id = service_id_int
                task_counter = 1

            task_id = f"S{service_id_int}-T{task_counter:03d}"
            ws.cell(row, 5, task_id)
            task_counter += 1

    wb.save(excel_path)
    print(f"✅ Removed {len(duplicates)} duplicate tasks")
    return len(duplicates)


def move_summary_to_top(excel_path: Path):
    """Move summary section to the top (after header row)."""
    wb = load_workbook(excel_path, data_only=False)
    ws = wb["VDS_Task_Breakdown_Detailed"]

    # Find summary section
    summary_start = None
    summary_end = None

    for row in range(ws.max_row - 30, ws.max_row + 1):
        cell_value = ws.cell(row, 1).value
        if cell_value:
            cell_str = str(cell_value).upper()
            if "TỔNG KẾT" in cell_str or "SUMMARY" in cell_str:
                summary_start = row
                break

    if not summary_start:
        print("⚠️ Summary section not found")
        return

    # Find end of summary (next non-empty row or end of sheet)
    summary_end = ws.max_row

    print(f"Found summary section: rows {summary_start} to {summary_end}")

    # Copy summary rows
    summary_rows = []
    for row in range(summary_start, summary_end + 1):
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
        summary_rows.append(row_data)

    # Delete summary rows from bottom
    ws.delete_rows(summary_start, summary_end - summary_start + 1)

    # Insert summary rows after header (row 2)
    for i, row_data in enumerate(summary_rows):
        insert_row = 2 + i
        ws.insert_rows(insert_row)

        for col_idx, cell_data in enumerate(row_data, 1):
            cell = ws.cell(insert_row, col_idx)
            cell.value = cell_data["value"]

            if cell_data["font"]:
                cell.font = cell_data["font"]
            if cell_data["fill"]:
                cell.fill = cell_data["fill"]
            if cell_data["alignment"]:
                cell.alignment = cell_data["alignment"]
            if cell_data["border"]:
                cell.border = cell_data["border"]
            if cell_data["number_format"]:
                cell.number_format = cell_data["number_format"]

    # Add separator row between summary and data
    separator_row = 2 + len(summary_rows)
    ws.insert_rows(separator_row)

    # Format separator
    for col in range(1, ws.max_column + 1):
        cell = ws.cell(separator_row, col)
        cell.fill = PatternFill(start_color="D3D3D3", end_color="D3D3D3", fill_type="solid")
        cell.border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
        )

    wb.save(excel_path)
    print(f"✅ Moved summary section to top (rows 2-{2 + len(summary_rows)})")


def improve_brd_references_further(excel_path: Path):
    """Further improve BRD references for tasks without them."""
    wb = load_workbook(excel_path, data_only=False)
    ws = wb["VDS_Task_Breakdown_Detailed"]

    # Enhanced BRD mapping
    brd_keyword_map = {
        # Section 3
        "tài khoản": "3.1",
        "đăng ký": "3.1.1",
        "đăng nhập": "3.1.2",
        "đăng xuất": "3.1.3",
        "quên mật khẩu": "3.1.4",
        "quản lý thông tin": "3.2",
        "mua bảo hiểm": "3.3",
        "đề xuất": "3.3.1",
        "gợi ý": "3.3.1",
        "chatbot": "3.3.2",
        "tùy chỉnh": "3.3.3",
        "so sánh": "3.3.4",
        "thanh toán": "3.3.5",
        "voucher": "3.3.8",
        "quản lý hợp đồng": "3.4",
        "xem chi tiết": "3.4.1",
        "gia hạn": "3.4.3",
        "tái tục": "3.4.3",
        "hủy hợp đồng": "3.4.4",
        "bồi thường": "3.5",
        "yêu cầu bồi thường": "3.5",
        # Section 4
        "quản lý tài khoản quản trị": "4.1",
        "quản lý đối tác": "4.2",
        "quản lý sản phẩm": "4.3",
        "danh sách sản phẩm": "4.3.1",
        "nhóm sản phẩm": "4.3.1",
        "cấu hình sản phẩm": "4.3.2",
        "gói sản phẩm": "4.3.2",
        "quyền lợi": "4.3.3",
        "phí": "4.3.3",
        "quản lý khách hàng": "4.4",
        "quản lý hợp đồng": "4.5",
        "quản lý yêu cầu bồi thường": "4.6",
        "quản lý kênh bán": "4.7",
        "quản lý chiến dịch": "4.8",
        "quản lý nội dung": "4.9",
        "báo cáo": "4.10",
        "đối soát": "4.10",
        "cảnh báo": "4.11",
    }

    updated_count = 0

    for row in range(2, ws.max_row + 1):
        task_name = ws.cell(row, 6).value
        current_brd_ref = ws.cell(row, 7).value
        service_name = ws.cell(row, 2).value

        if task_name:
            task_lower = str(task_name).lower()
            service_lower = str(service_name).lower() if service_name else ""
            combined_text = f"{task_lower} {service_lower}"

            # Find matching BRD references
            matched_refs = []
            for keyword, brd_ref in brd_keyword_map.items():
                if keyword in combined_text and brd_ref not in matched_refs:
                    matched_refs.append(brd_ref)

            # Update if we found references and current is missing or too generic
            if matched_refs:
                new_ref = ", ".join(matched_refs[:3])

                if not current_brd_ref or str(current_brd_ref) == "N/A" or len(str(current_brd_ref)) < 5:
                    ws.cell(row, 7, new_ref)
                    updated_count += 1
                elif not any(ref in str(current_brd_ref) for ref in matched_refs):
                    # Append new references
                    existing_refs = [r.strip() for r in str(current_brd_ref).split(",")]
                    combined = list(set(existing_refs + matched_refs[:2]))
                    ws.cell(row, 7, ", ".join(combined[:3]))
                    updated_count += 1

    wb.save(excel_path)
    print(f"✅ Improved BRD references for {updated_count} additional tasks")


def main():
    """Main execution."""
    print("=" * 80)
    print("Finalize BRD Coverage: Remove Duplicates and Move Summary")
    print("=" * 80)

    # Step 1: Remove duplicates
    print("\nStep 1: Removing duplicate tasks...")
    remove_duplicates(EXCEL_PATH)

    # Step 2: Improve BRD references further
    print("\nStep 2: Further improving BRD references...")
    improve_brd_references_further(EXCEL_PATH)

    # Step 3: Move summary to top
    print("\nStep 3: Moving summary section to top...")
    move_summary_to_top(EXCEL_PATH)

    # Final verification
    print("\n=== Final Verification ===")
    wb = load_workbook(EXCEL_PATH, data_only=False)
    ws = wb["VDS_Task_Breakdown_Detailed"]

    print(f"Total tasks: {ws.max_row - 1}")

    # Count BRD references
    tasks_with_brd = 0
    for row in range(2, ws.max_row + 1):
        brd_ref = ws.cell(row, 7).value
        if brd_ref and str(brd_ref) != "N/A" and len(str(brd_ref)) > 3:
            tasks_with_brd += 1

    print(
        f"Tasks with BRD references: {tasks_with_brd}/{ws.max_row - 1} ({tasks_with_brd / (ws.max_row - 1) * 100:.1f}%)"
    )

    # Check summary position
    summary_found = False
    for row in range(2, 10):
        cell_value = ws.cell(row, 1).value
        if cell_value and ("TỔNG KẾT" in str(cell_value).upper() or "SUMMARY" in str(cell_value).upper()):
            summary_found = True
            print(f"✅ Summary section found at row {row} (top)")
            break

    if not summary_found:
        print("⚠️ Summary section not found at top")

    print("\n" + "=" * 80)
    print("Finalization completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
