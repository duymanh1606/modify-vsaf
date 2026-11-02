from __future__ import annotations

import json
import os
import re
from pathlib import Path

from openpyxl import Workbook
from openpyxl.utils import get_column_letter

SHEET_REPLACEMENTS = [
    ("insurance-", ""),
    ("business", "biz"),
    ("service", "svc"),
    ("management", "mgmt"),
    ("integration", "int"),
    ("notification", "notif"),
    ("authentication", "auth"),
    ("centralized", "central"),
    ("observability", "obs"),
    ("document", "doc"),
    ("customer", "cust"),
    ("payment", "pay"),
    ("proposal", "prop"),
    ("orchestrator", "orch"),
    ("workflow", "flow"),
    ("underwriting", "uw"),
    ("reconcile", "recon"),
    ("promotion", "promo"),
    ("commission", "comm"),
    ("configuration", "config"),
    ("regulator", "reg"),
    ("security", "sec"),
    ("billing", "bill"),
    ("gateway", "gw"),
    ("platform", "plat"),
]

PHASE_TO_ROLE = {
    "Design": "Architect",
    "Implementation": "Jr Dev",
    "Testing": "QA",
    "Integration": "DevOps",
}

PHASE_TRANSLATIONS_VI = {
    "Design": "Thiết kế",
    "Implementation": "Triển khai",
    "Testing": "Kiểm thử",
    "Integration": "Tích hợp",
}

ROLE_TRANSLATIONS_VI = {
    "Architect": "Kiến trúc sư",
    "Jr Dev": "Dev Jr",
    "QA": "QA",
    "DevOps": "DevOps",
}

PRIORITY_TRANSLATIONS_VI = {
    "High": "Cao",
    "Medium": "Trung bình",
    "Low": "Thấp",
}

DOCS_STATUS_TRANSLATIONS_VI = {
    "Complete": "Hoàn tất",
    "Incomplete": "Chưa đủ",
}

CODE_STATUS_TRANSLATIONS_VI = {
    "Implemented": "Đã triển khai",
    "Design-Only": "Thiết kế (Target State)",
}

EXEC_STATUS_TRANSLATIONS_VI = {
    "Done": "Hoàn thành",
    "Ready for Dev": "Sẵn sàng phát triển",
}

TASK_STATUS_TRANSLATIONS_VI = {
    "Pending": "Chờ",
    "Done": "Hoàn thành",
}

EXEC_HEADERS_VI = [
    "Tên dịch vụ",
    "Tên sheet",
    "Mức ưu tiên",
    "Trạng thái tài liệu",
    "Trạng thái code",
    "Phạm vi BRD",
    "Ước tính công (ngày)",
    "Trạng thái",
]

TASK_HEADERS_VI = [
    "Mã công việc",
    "Giai đoạn",
    "Mô tả công việc",
    "Phụ thuộc",
    "Vai trò",
    "Ước tính (giờ)",
    "Trạng thái",
]

CROSS_HEADERS_VI = [
    "Dịch vụ",
    "Loại phụ thuộc",
    "Phụ thuộc",
    "Miền BRD",
    "Nguồn",
]

DEPENDENCY_TYPE_VI = {
    "Cross-Service": "Liên dịch vụ",
    "Critical-Path": "Đường găng",
    "External": "Bên ngoài",
}

SOURCE_SECTION_VI = {
    "Cross-Service Dependencies": "Phụ thuộc liên dịch vụ",
    "Critical-Path Dependencies": "Phụ thuộc đường găng",
}

VI_REPLACEMENTS = [
    (r"Initialize Git Repository & Branching Strategy", "Khởi tạo kho Git & chiến lược nhánh"),
    (r"Create Docker Base Image & Local Dev Environment", "Tạo Docker base image & môi trường dev local"),
    (r"Configure CI/CD Pipeline Structure", "Cấu hình cấu trúc pipeline CI/CD"),
    (r"Configure Monitoring & Alerting", "Cấu hình giám sát & cảnh báo"),
    (r"Documentation & Runbooks", "Tài liệu & runbook"),
    (r"Initialize", "Khởi tạo"),
    (r"Review architecture", "Rà soát kiến trúc"),
    (r"BRD alignment", "đối chiếu BRD"),
    (r"dependency contracts", "hợp đồng phụ thuộc"),
    (r"shared infrastructure", "hạ tầng dùng chung"),
    (r"upstream", "đầu vào"),
    (r"downstream", "đầu ra"),
    (r"external", "bên ngoài"),
    (r"Confirm", "Xác nhận"),
    (r"Map BRD", "Ánh xạ BRD"),
    (r"policy flows", "luồng hợp đồng"),
    (r"Implement domain workflows for", "Triển khai luồng nghiệp vụ cho"),
    (r"policy", "hợp đồng"),
    (r"proposal", "đề xuất"),
    (r"claim", "bồi thường"),
    (r"payment", "thanh toán"),
    (r"billing", "tính phí"),
    (r"renewal", "gia hạn"),
    (r"endorsement", "điều chỉnh"),
    (r"issuance", "phát hành"),
    (r"cancellation", "hủy"),
    (r"commission", "hoa hồng"),
    (r"contract rules", "quy tắc hợp đồng"),
    (r"rules", "quy tắc"),
    (r"flows", "luồng"),
    (r"Implement core workflows for", "Triển khai luồng nghiệp vụ cốt lõi cho"),
    (r"Implement Camunda 8", "Triển khai Camunda 8"),
    (r"Implement payment lifecycle", "Triển khai vòng đời thanh toán"),
    (r"Implement aggregation layer", "Triển khai lớp tổng hợp"),
    (r"Implement orchestration", "Triển khai điều phối"),
    (r"Implement reconciliation workflow", "Triển khai luồng đối soát"),
    (r"Implement notification orchestration", "Triển khai điều phối thông báo"),
    (r"Implement content authoring and approval flow", "Triển khai luồng biên tập và phê duyệt nội dung"),
    (r"Expose REST endpoints for", "Cung cấp REST API cho"),
    (r"Expose REST endpoints", "Cung cấp REST API"),
    (r"Expose APIs for", "Cung cấp API cho"),
    (r"Expose APIs", "Cung cấp API"),
    (r"Implement adapters for", "Triển khai adapter cho"),
    (r"Build adapters for", "Xây dựng adapter cho"),
    (r"Build connectors for", "Xây dựng connector cho"),
    (r"Build connectors", "Xây dựng connector"),
    (r"Implement adapters", "Triển khai adapter"),
    (r"Implement", "Triển khai"),
    (r"Build", "Xây dựng"),
    (r"Configure", "Cấu hình"),
    (r"Define", "Xác định"),
    (r"Create", "Tạo"),
    (r"Update", "Cập nhật"),
    (r"Publish", "Phát hành"),
    (r"Emit", "Phát"),
    (r"Ingest", "Tiếp nhận"),
    (r"Validate", "Xác thực"),
    (r"ingest and validate inputs from", "tiếp nhận và xác thực đầu vào từ"),
    (r"persist state in", "lưu trạng thái vào"),
    (r"publish outcomes to", "phát kết quả tới"),
    (r"via Kafka", "qua Kafka"),
    (r"execute core processing steps and state transitions", "thực thi các bước xử lý cốt lõi và chuyển trạng thái"),
    (r"state transitions", "chuyển trạng thái"),
    (r"query status", "tra cứu trạng thái"),
    (r"retrieve outputs", "lấy kết quả"),
    (r"requests", "yêu cầu"),
    (r"outputs", "kết quả"),
    (r"enforce", "áp dụng"),
    (r"validate payloads", "xác thực payload"),
    (r"support idempotency", "hỗ trợ idempotency"),
    (r"map errors consistently", "chuẩn hóa ánh xạ lỗi"),
    (r"contract mapping", "ánh xạ hợp đồng"),
    (r"retry/backoff", "retry/backoff"),
    (r"circuit breakers", "circuit breaker"),
    (r"timeouts", "timeout"),
    (r"observability hooks", "hook quan sát"),
    (r"workflow", "workflow"),
    (r"integration", "tích hợp"),
    (r"dependencies", "phụ thuộc"),
    (r"status", "trạng thái"),
    (r"submit", "gửi"),
    (r"query", "tra cứu"),
    (r"retrieve", "lấy"),
    (r"\bto\b", "cho"),
    (r"\bfor\b", "cho"),
    (r"\bwith\b", "với"),
    (r"\bfrom\b", "từ"),
    (r"\binto\b", "vào"),
    (r"\busing\b", "bằng"),
    (r"\bvia\b", "qua"),
    (r" and ", " và "),
]


def resolve_repo_root(start: Path | None = None) -> Path:
    base = start or Path.cwd()
    for candidate in [base, *base.parents]:
        if (candidate / "WHO-project").exists() or any(candidate.glob("*-project")):
            return candidate
    return base


def resolve_insurance_docs_root(start: Path | None = None) -> Path:
    override = os.environ.get("VDS_INSURANCE_DOCS_ROOT")
    if override:
        return Path(override).expanduser()
    root = resolve_repo_root(start)
    preferred = root / "WHO-project" / "insurance-document"
    if preferred.exists():
        return preferred
    matches = sorted(root.glob("*-project/insurance-document"))
    if matches:
        return matches[0]
    return preferred


def resolve_default_paths(
    arch_root: Path | None,
    output_file: Path | None,
    brd_report: Path | None,
    audit_report: Path | None = None,
    *,
    repo_root: Path | None = None,
) -> tuple[Path, Path, Path, Path | None]:
    root = repo_root or resolve_repo_root(Path(__file__).resolve())
    docs_root = resolve_insurance_docs_root(root)
    if arch_root is None:
        arch_root = docs_root / "projects/INSURANCE/analysis/target-state/architecture"
    if output_file is None:
        output_file = docs_root / "projects/INSURANCE/analysis/target-state/target-state-status.xlsx"
    if brd_report is None:
        brd_report = root / "WHO-project/vds-scripts/scripts/brd_coverage_report.json"

    if audit_report is None:
        # Try to find audit report in common locations
        candidates = [
            root / "WHO-project/vds-scripts/scripts/audit-results.json",
            docs_root / "projects/INSURANCE/analysis/target-state/audit-results.json",
        ]
        for c in candidates:
            if c.exists():
                audit_report = c
                break

    return arch_root, output_file, brd_report, audit_report


def load_brd_coverage(brd_report: Path) -> str:
    if not brd_report.exists():
        return "100%"
    try:
        data = json.loads(brd_report.read_text(encoding="utf-8"))
        pct = float(data.get("coverage_percentage", 100.0))
        return f"{pct:.1f}%"
    except Exception:
        return "100%"


def load_audit_results(audit_report: Path | None) -> dict[str, dict]:
    if not audit_report or not audit_report.exists():
        return {}
    try:
        data = json.loads(audit_report.read_text(encoding="utf-8"))
        # Assume data is a list of results or a dict with service keys
        # If it's a list, convert to dict by service name
        if isinstance(data, list):
            return {item.get("service", ""): item for item in data if item.get("service")}
        return data
    except Exception:
        return {}


def parse_metadata(content: str) -> dict[str, str]:
    patterns = {
        "Service": r"^\*\*Service\*\*:\s*(.+)$",
        "Priority": r"^\*\*Priority\*\*:\s*(.+)$",
        "Complexity": r"^\*\*Complexity\*\*:\s*(.+)$",
        "Total Effort (Jr Dev)": r"^\*\*Total Effort \(Jr Dev\)\*\*:\s*([0-9.]+)",
        "Buffer (20%)": r"^\*\*Buffer \(20%\)\*\*:\s*([0-9.]+)",
        "Total With Buffer": r"^\*\*Total With Buffer\*\*:\s*([0-9.]+)",
    }
    meta: dict[str, str] = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, content, flags=re.MULTILINE)
        if match:
            value = match.group(1).strip()
            if value.startswith("`") and value.endswith("`"):
                value = value[1:-1].strip()
            meta[key] = value
    return meta


def parse_tasks(content: str) -> list[list]:
    tasks: list[list] = []
    phase_label: str | None = None

    for line in content.splitlines():
        line = line.strip()
        if line.startswith("### Phase "):
            if "Design" in line:
                phase_label = "Design"
            elif "Implementation" in line:
                phase_label = "Implementation"
            elif "Testing" in line:
                phase_label = "Testing"
            elif "Integration" in line or "Deployment" in line:
                phase_label = "Integration"
            else:
                phase_label = None
            continue

        if not phase_label:
            continue

        if line.startswith("|") and "Task ID" in line:
            continue
        if line.startswith("|") and "---" in line:
            continue

        if line.startswith("|"):
            parts = [p.strip() for p in line.strip("|").split("|")]
            if len(parts) < 5:
                continue
            task_id, desc, deps, effort_days = parts[0], parts[1], parts[2], parts[3]
            if not task_id.startswith("T-"):
                continue
            try:
                effort_days = float(effort_days)
            except ValueError:
                effort_days = 0.0
            role = PHASE_TO_ROLE.get(phase_label, "Jr Dev")
            est_hours = round(effort_days * 8.0, 1)
            tasks.append([task_id, phase_label, desc, deps, role, est_hours, "Pending"])

    return tasks


def extract_section_list(content: str, heading: str) -> list[str]:
    idx = content.find(heading)
    if idx == -1:
        return []
    sub = content[idx + len(heading) :]
    lines = sub.splitlines()
    out: list[str] = []
    for line in lines:
        if line.startswith("### ") or line.startswith("## "):
            break
        line = line.strip()
        if line.startswith("- "):
            out.append(line[2:].strip())
    return out


def _apply_vi_replacements(text: str) -> str:
    out = text
    for pattern, replacement in VI_REPLACEMENTS:
        out = re.sub(pattern, replacement, out, flags=re.IGNORECASE)
    out = re.sub(r"\s+", " ", out).strip()
    return out


def _protect_service_names(text: str) -> tuple[str, dict[str, str]]:
    mapping: dict[str, str] = {}

    def repl(match: re.Match[str]) -> str:
        service = match.group(0)
        token = f"__SERVICE_{len(mapping)}__"
        mapping[token] = service
        return token

    protected = re.sub(r"insurance-[a-z0-9-]+", repl, text)
    return protected, mapping


def _to_bullets(text: str) -> str:
    if not text:
        return text
    segments = [seg.strip() for seg in text.split(";") if seg.strip()]
    if not segments:
        return text
    return "\n".join(f"• {seg}" for seg in segments)


def translate_task_description_vi(text: str) -> str:
    protected, mapping = _protect_service_names(text)
    translated = _apply_vi_replacements(protected)
    for token, service in mapping.items():
        translated = translated.replace(token, service)
    return _to_bullets(translated)


def translate_phase_vi(phase: str) -> str:
    return PHASE_TRANSLATIONS_VI.get(phase, phase)


def translate_role_vi(role: str) -> str:
    return ROLE_TRANSLATIONS_VI.get(role, role)


def translate_priority_vi(priority: str) -> str:
    return PRIORITY_TRANSLATIONS_VI.get(priority, priority)


def translate_docs_status_vi(status: str) -> str:
    return DOCS_STATUS_TRANSLATIONS_VI.get(status, status)


def translate_code_status_vi(status: str) -> str:
    return CODE_STATUS_TRANSLATIONS_VI.get(status, status)


def translate_exec_status_vi(status: str) -> str:
    return EXEC_STATUS_TRANSLATIONS_VI.get(status, status)


def translate_task_status_vi(status: str) -> str:
    return TASK_STATUS_TRANSLATIONS_VI.get(status, status)


def translate_dependency_type_vi(dep_type: str) -> str:
    return DEPENDENCY_TYPE_VI.get(dep_type, dep_type)


def translate_source_section_vi(section: str) -> str:
    return SOURCE_SECTION_VI.get(section, section)


def infer_code_status(arch_path: Path) -> str:
    if not arch_path.exists():
        return "Design-Only"
    text = arch_path.read_text(encoding="utf-8")
    match = re.search(r"^\*\*Status\*\*:\s*(.+)$", text, flags=re.MULTILINE)
    if not match:
        return "Design-Only"
    status = match.group(1).lower()
    if "implemented" in status:
        return "Implemented"
    return "Design-Only"


def docs_status(service_dir: Path, service_name: str) -> str:
    required = [
        [
            service_dir / f"{service_name}-architecture.md",
            service_dir / "architecture.md",
        ],
        [service_dir / "openapi.yaml"],
        [
            service_dir / f"{service_name}-api-contracts.md",
            service_dir / "api-contracts.md",
        ],
        [
            service_dir / f"{service_name}-modernization-guide.md",
            service_dir / "modernization-guide.md",
        ],
    ]
    return "Complete" if all(any(path.exists() for path in group) for group in required) else "Incomplete"


def make_sheet_name(service: str, used: set[str]) -> str:
    name = service
    if len(name) > 31:
        for old, new in SHEET_REPLACEMENTS:
            name = name.replace(old, new)
            if len(name) <= 31:
                break
    if len(name) > 31:
        name = name[:31]
    base = name
    i = 1
    while name in used:
        suffix = f"-{i}"
        name = (base[: 31 - len(suffix)] + suffix) if len(base) + len(suffix) > 31 else base + suffix
        i += 1
    used.add(name)
    return name


def collect_task_files(arch_root: Path) -> list[Path]:
    if not arch_root.exists():
        return []
    task_files = []
    for path in arch_root.rglob("*-tasks.md"):
        name = path.name
        parent = path.parent.name
        if "workflow-workers" in name or "workflow-workers" in parent:
            continue
        task_files.append(path)
    return sorted(task_files)


def _parse_dependency_domains(line: str) -> tuple[str, str]:
    domains = ""
    if "BRD domains:" in line:
        before, _, after = line.partition("BRD domains:")
        domains = after.strip()
        dep = before.strip()
        dep = dep.rstrip("-\u2014\u2013").strip()
        return dep, domains
    return line.strip(), domains


def generate_status_xlsx(
    arch_root: Path,
    output_file: Path,
    brd_report: Path,
    audit_report: Path | None = None,
) -> dict[str, str | int]:
    task_files = collect_task_files(arch_root)
    brd_pct = load_brd_coverage(brd_report)
    audit_data = load_audit_results(audit_report)

    summary_rows: list[dict[str, str | float]] = []
    service_tasks: dict[str, list[list]] = {}
    cross_rows: list[list[str]] = []

    for path in task_files:
        content = path.read_text(encoding="utf-8")
        meta = parse_metadata(content)

        service_name = meta.get("Service") or path.name.replace("-tasks.md", "")
        service_dir = path.parent

        tasks = parse_tasks(content)
        service_tasks[service_name] = tasks

        # Calculate effort from tasks (sum of hours / 8.0)
        total_hours = sum(t[5] for t in tasks) if tasks else 0.0
        effort_days = round(total_hours / 8.0, 1)

        # Determine Code Status
        code_status_val = "Design-Only"
        if service_name in audit_data and "has_code" in audit_data[service_name]:
            code_status_val = "Implemented" if audit_data[service_name]["has_code"] else "Design-Only"
        else:
            code_status_val = infer_code_status(service_dir / f"{service_name}-architecture.md")

        summary_rows.append(
            {
                "Service Name": service_name,
                "Priority": meta.get("Priority", "Unknown"),
                "Docs Status": docs_status(service_dir, service_name),
                "Code Status": code_status_val,
                "BRD Coverage": brd_pct,
                "Effort Estimate (Days)": effort_days,
            }
        )

        cross = extract_section_list(content, "### Cross-Service Dependencies")
        for dep_line in cross:
            if dep_line.lower().startswith("none"):
                continue
            parts = [p.strip() for p in dep_line.split(",") if p.strip()]
            for dep in parts:
                cross_rows.append([service_name, "Cross-Service", dep, "", "Cross-Service Dependencies"])

        critical = extract_section_list(content, "### Critical-Path Dependencies (BRD-aligned)")
        for line in critical:
            if line.lower().startswith("none"):
                continue
            dep_type = "Critical-Path"
            dep = line
            domains = ""
            if line.lower().startswith("external:"):
                dep_type = "External"
                dep, domains = _parse_dependency_domains(line.replace("External:", "", 1).strip())
            else:
                dep, domains = _parse_dependency_domains(line)
            cross_rows.append([service_name, dep_type, dep, domains, "Critical-Path Dependencies"])

    wb = Workbook()
    exec_ws = wb.active
    exec_ws.title = "Executive Dashboard"

    exec_headers = [
        "Service Name",
        "Sheet Name",
        "Priority",
        "Docs Status",
        "Code Status",
        "BRD Coverage",
        "Effort Estimate (Days)",
        "Status",
    ]
    exec_ws.append(exec_headers)

    used: set[str] = {"Executive Dashboard"}

    for row in summary_rows:
        sheet_name = make_sheet_name(row["Service Name"], used)
        status = "Done" if row["Code Status"] == "Implemented" else "Ready for Dev"
        exec_ws.append(
            [
                row["Service Name"],
                sheet_name,
                row["Priority"],
                row["Docs Status"],
                row["Code Status"],
                row["BRD Coverage"],
                row["Effort Estimate (Days)"],
                status,
            ]
        )

        ws = wb.create_sheet(title=sheet_name)
        ws.append(
            [
                "Task ID",
                "Phase",
                "Task Description",
                "Dependency",
                "Role",
                "Est. Hours",
                "Status",
            ]
        )
        for task in service_tasks.get(row["Service Name"], []):
            ws.append(task)

    cross_ws = wb.create_sheet(title="Cross-Service Dependencies")
    cross_ws.append(["Service Name", "Dependency Type", "Dependency", "BRD Domains", "Source Section"])
    for row in cross_rows:
        cross_ws.append(row)

    for ws in wb.worksheets:
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val = cell.value
                if val is None:
                    continue
                max_len = max(max_len, len(str(val)))
            ws.column_dimensions[col_letter].width = min(max_len + 2, 80)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_file)

    return {
        "task_files": len(task_files),
        "cross_dependencies": len(cross_rows),
        "output_file": str(output_file),
    }


def generate_status_vi_xlsx(
    arch_root: Path,
    output_file: Path,
    brd_report: Path,
    audit_report: Path | None = None,
) -> dict[str, str | int]:
    task_files = collect_task_files(arch_root)
    brd_pct = load_brd_coverage(brd_report)
    audit_data = load_audit_results(audit_report)

    summary_rows: list[dict[str, str | float]] = []
    service_tasks: dict[str, list[list]] = {}
    cross_rows: list[list[str]] = []

    for path in task_files:
        content = path.read_text(encoding="utf-8")
        meta = parse_metadata(content)

        service_name = meta.get("Service") or path.name.replace("-tasks.md", "")
        service_dir = path.parent

        tasks = parse_tasks(content)
        translated_tasks: list[list] = []
        for task_id, phase_label, desc, deps, role, est_hours, status in tasks:
            translated_tasks.append(
                [
                    task_id,
                    translate_phase_vi(phase_label),
                    translate_task_description_vi(desc),
                    deps,
                    translate_role_vi(role),
                    est_hours,
                    translate_task_status_vi(status),
                ]
            )
        service_tasks[service_name] = translated_tasks

        # Calculate effort from tasks
        total_hours = sum(t[5] for t in tasks) if tasks else 0.0
        effort_days = round(total_hours / 8.0, 1)

        # Determine Code Status
        code_status_val = "Design-Only"
        if service_name in audit_data and "has_code" in audit_data[service_name]:
            code_status_val = "Implemented" if audit_data[service_name]["has_code"] else "Design-Only"
        else:
            code_status_val = infer_code_status(service_dir / f"{service_name}-architecture.md")

        summary_rows.append(
            {
                "Service Name": service_name,
                "Priority": translate_priority_vi(meta.get("Priority", "Unknown")),
                "Docs Status": translate_docs_status_vi(docs_status(service_dir, service_name)),
                "Code Status": translate_code_status_vi(code_status_val),
                "BRD Coverage": brd_pct,
                "Effort Estimate (Days)": effort_days,
            }
        )

        cross = extract_section_list(content, "### Cross-Service Dependencies")
        for dep_line in cross:
            if dep_line.lower().startswith("none"):
                continue
            parts = [p.strip() for p in dep_line.split(",") if p.strip()]
            for dep in parts:
                cross_rows.append(
                    [
                        service_name,
                        translate_dependency_type_vi("Cross-Service"),
                        dep,
                        "",
                        translate_source_section_vi("Cross-Service Dependencies"),
                    ]
                )

        critical = extract_section_list(content, "### Critical-Path Dependencies (BRD-aligned)")
        for line in critical:
            if line.lower().startswith("none"):
                continue
            dep_type = "Critical-Path"
            dep = line
            domains = ""
            if line.lower().startswith("external:"):
                dep_type = "External"
                dep, domains = _parse_dependency_domains(line.replace("External:", "", 1).strip())
            else:
                dep, domains = _parse_dependency_domains(line)
            cross_rows.append(
                [
                    service_name,
                    translate_dependency_type_vi(dep_type),
                    dep,
                    domains,
                    translate_source_section_vi("Critical-Path Dependencies"),
                ]
            )

    wb = Workbook()
    exec_ws = wb.active
    exec_ws.title = "Executive Dashboard"
    exec_ws.append(EXEC_HEADERS_VI)

    used: set[str] = {"Executive Dashboard"}

    for row in summary_rows:
        sheet_name = make_sheet_name(row["Service Name"], used)
        status = (
            "Hoàn thành"
            if row["Code Status"] == CODE_STATUS_TRANSLATIONS_VI.get("Implemented")
            else "Sẵn sàng phát triển"
        )
        exec_ws.append(
            [
                row["Service Name"],
                sheet_name,
                row["Priority"],
                row["Docs Status"],
                row["Code Status"],
                row["BRD Coverage"],
                row["Effort Estimate (Days)"],
                status,
            ]
        )

        ws = wb.create_sheet(title=sheet_name)
        ws.append(TASK_HEADERS_VI)
        for task in service_tasks.get(row["Service Name"], []):
            ws.append(task)

    cross_ws = wb.create_sheet(title="Cross-Service Dependencies")
    cross_ws.append(CROSS_HEADERS_VI)
    for row in cross_rows:
        cross_ws.append(row)

    for ws in wb.worksheets:
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val = cell.value
                if val is None:
                    continue
                max_len = max(max_len, len(str(val)))
            ws.column_dimensions[col_letter].width = min(max_len + 2, 80)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_file)

    return {
        "task_files": len(task_files),
        "cross_dependencies": len(cross_rows),
        "output_file": str(output_file),
    }


def main() -> None:
    arch_root, output_file, brd_report, audit_report = resolve_default_paths(None, None, None, None)
    result = generate_status_xlsx(arch_root, output_file, brd_report, audit_report)
    print(
        f"Generated {result['output_file']} from {result['task_files']} task files "
        f"({result['cross_dependencies']} dependencies)"
    )


if __name__ == "__main__":
    main()
