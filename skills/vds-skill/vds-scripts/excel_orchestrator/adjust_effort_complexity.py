"""
Adjust effort estimates for complex services based on research findings:
- AI/Intelligent services: 1.4x multiplier (research, algorithm development, integration)
- Complex workflow services: 1.25x multiplier (solution research, workflow design)
- Complex logic services: 1.3x multiplier (algorithm complexity, testing)

Based on research:
- AI/LLM services require additional research time (40% increase)
- Business workflow creation involves solution research (25% increase)
- Complex logic requires more effort for algorithm development (30% increase)
"""

from openpyxl import load_workbook

FILE_PATH = "../../insurance-document/projects/INSURANCE/analysis/reference/vietin/estimation/Estimation_HTBH.xlsx"

# Multipliers based on research
AI_INTELLIGENT_MULTIPLIER = 1.4  # 40% increase for research, algorithm, integration
COMPLEX_WORKFLOW_MULTIPLIER = 1.25  # 25% increase for solution research
COMPLEX_LOGIC_MULTIPLIER = 1.3  # 30% increase for algorithm complexity

# Service categories
AI_INTELLIGENT_KEYWORDS = [
    "chatbot",
    "intelligent",
    "recommendation",
    "filtering",
    "targeted",
]
COMPLEX_WORKFLOW_KEYWORDS = [
    "workflow",
    "camunda",
    "renewal",
    "process",
    "orchestrator",
    "claim",
    "reconcile",
    "timeout",
]
COMPLEX_LOGIC_KEYWORDS = [
    "engine",
    "rating",
    "underwriting",
    "rules",
    "fraud",
    "detection",
]


def classify_service(service_name):
    """Classify service and return appropriate multiplier."""
    service_lower = service_name.lower()

    # Check AI/Intelligent first (highest priority)
    if any(keyword in service_lower for keyword in AI_INTELLIGENT_KEYWORDS):
        return "ai_intelligent", AI_INTELLIGENT_MULTIPLIER

    # Check complex workflow
    if any(keyword in service_lower for keyword in COMPLEX_WORKFLOW_KEYWORDS):
        return "complex_workflow", COMPLEX_WORKFLOW_MULTIPLIER

    # Check complex logic
    if any(keyword in service_lower for keyword in COMPLEX_LOGIC_KEYWORDS):
        return "complex_logic", COMPLEX_LOGIC_MULTIPLIER

    return None, 1.0


def main():
    wb = load_workbook(FILE_PATH, read_only=False)
    ws = wb["VDS_Est_Detail_Target_State"]

    adjusted_services = {
        "ai_intelligent": [],
        "complex_workflow": [],
        "complex_logic": [],
    }

    total_adjusted_tasks = 0
    total_additional_days = 0.0

    print("=== Adjusting Effort for Complex Services ===\n")

    # Process each service
    for row in range(10, ws.max_row + 1):
        col2 = ws.cell(row, 2).value
        col3 = ws.cell(row, 3).value

        # Service header row
        if isinstance(col2, (int, float)) and col2 > 0 and col3:
            service_num = int(col2)
            service_name = str(col3).strip()

            category, multiplier = classify_service(service_name)

            if category:
                # Find all tasks for this service
                service_tasks = []
                original_total_days = 0.0

                for task_row in range(row + 1, ws.max_row + 1):
                    task_col2 = ws.cell(task_row, 2).value
                    task_col3 = ws.cell(task_row, 3).value
                    task_col5 = ws.cell(task_row, 5).value

                    # Stop at next service
                    if isinstance(task_col2, (int, float)) and task_col2 > 0:
                        break

                    # Task row
                    if task_col3 and isinstance(task_col5, (int, float)):
                        days = float(task_col5)
                        service_tasks.append((task_row, days))
                        original_total_days += days

                # Apply multiplier to each task
                if service_tasks:
                    new_total_days = 0.0
                    for task_row, days in service_tasks:
                        new_days = days * multiplier
                        ws.cell(task_row, 5).value = new_days
                        ws.cell(task_row, 5).number_format = "0.00"
                        # Update hours formula
                        ws.cell(task_row, 4).value = f"=E{task_row}*8"
                        new_total_days += new_days
                        total_adjusted_tasks += 1

                    additional_days = new_total_days - original_total_days
                    total_additional_days += additional_days

                    adjusted_services[category].append(
                        {
                            "num": service_num,
                            "name": service_name,
                            "original_days": original_total_days,
                            "new_days": new_total_days,
                            "additional_days": additional_days,
                            "multiplier": multiplier,
                        }
                    )

                    print(
                        f"✅ Service {service_num} ({category}): {original_total_days:.1f} → {new_total_days:.1f} days (+{additional_days:.1f}, {multiplier}x)"
                    )

    # Update totals
    for row in range(500, ws.max_row + 1):
        col3 = ws.cell(row, 3).value
        if isinstance(col3, str) and "total" in col3.lower():
            totals_row = row
            ws.cell(totals_row, 4).value = f"=SUM(D10:D{totals_row - 1})"
            ws.cell(totals_row, 5).value = f"=SUM(E10:E{totals_row - 1})"
            break

    # Update summary sheet
    if "VDS_Summary_Target_State" in wb.sheetnames:
        ws_summary = wb["VDS_Summary_Target_State"]
        ws_summary.cell(10, 4).value = f"='VDS_Est_Detail_Target_State'!D{totals_row}"
        ws_summary.cell(10, 5).value = f"='VDS_Est_Detail_Target_State'!E{totals_row}"

    # Summary
    print("\n=== Summary ===")
    print(f"AI/Intelligent services adjusted: {len(adjusted_services['ai_intelligent'])}")
    print(f"Complex workflow services adjusted: {len(adjusted_services['complex_workflow'])}")
    print(f"Complex logic services adjusted: {len(adjusted_services['complex_logic'])}")
    print(f"Total tasks adjusted: {total_adjusted_tasks}")
    print(f"Total additional days: {total_additional_days:.1f}")
    print(f"Total additional hours: {total_additional_days * 8:.1f}")

    # Breakdown by category
    for category in ["ai_intelligent", "complex_workflow", "complex_logic"]:
        services = adjusted_services[category]
        if services:
            cat_total = sum(s["additional_days"] for s in services)
            print(f"\n{category.replace('_', ' ').title()}: +{cat_total:.1f} days")
            for s in services:
                print(f"  Service {s['num']}: +{s['additional_days']:.1f} days")

    wb.save(FILE_PATH)
    print("\n✅ Effort adjustments applied and saved!")


if __name__ == "__main__":
    main()
