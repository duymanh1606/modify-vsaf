#!/usr/bin/env python3
"""
tc_import.py — Parse Excel manual test case file into structured JSON.

Handles:
  - Flexible Vietnamese/English header detection
  - Merged cells (fill-down for category grouping)
  - Multi-row TCs (continuation rows appended to previous TC)
  - Multi-sheet: scans all sheets, picks first sheet with recognisable headers

Output: JSON to stdout
"""

import sys
import json
import re
import openpyxl

COLUMN_ALIASES = {
    'id': [
        'id', 'stt', 'tc id', 'test id', 'mã tc', 'mã', 'số tt', 'testcase id',
    ],
    'category': [
        'mục đích kiểm thử', 'mục đích', 'category', 'purpose', 'loại tc',
        'nhóm', 'phân loại',
    ],
    'title': [
        'trường hợp kiểm thử', 'tên tc', 'test case', 'tiêu đề', 'tên test',
        'tên kiểm thử', 'kịch bản', 'mô tả tc',
    ],
    'data': [
        'data test', 'dữ liệu test', 'test data', 'preconditions',
        'điều kiện tiên quyết', 'điều kiện', 'dữ liệu đầu vào', 'input',
    ],
    'steps': [
        'các bước thực hiện', 'bước thực hiện', 'steps', 'các bước',
        'bước', 'thực hiện', 'hành động',
    ],
    'expected': [
        'kết quả mong muốn', 'kết quả kỳ vọng', 'expected result',
        'expected', 'kết quả', 'kq mong muốn',
    ],
    'notes': [
        'ghi chú', 'notes', 'note', 'nhận xét', 'comment', 'ghi chú thêm',
    ],
}

REQUIRED_COLUMNS = {'title', 'steps', 'expected'}


def normalize(s):
    return str(s or '').lower().strip()


def score_row(row):
    """Count how many alias groups are matched in this row."""
    vals = [normalize(c.value) for c in row if c.value]
    score = 0
    for aliases in COLUMN_ALIASES.values():
        if any(alias in v for v in vals for alias in aliases):
            score += 1
    return score


def find_header_row(ws):
    for row_idx, row in enumerate(ws.iter_rows(max_row=30), start=1):
        if score_row(row) >= 3:
            return row_idx
    return None


def map_columns(ws, header_row):
    col_map = {}
    for cell in ws[header_row]:
        if cell.value is None:
            continue
        val = normalize(cell.value)
        for key, aliases in COLUMN_ALIASES.items():
            if key not in col_map and any(alias in val for alias in aliases):
                col_map[key] = cell.column
    return col_map


def unmerge_fill(ws):
    """Fill merged cell ranges with the top-left cell value."""
    for merge_range in list(ws.merged_cells.ranges):
        top_val = ws.cell(merge_range.min_row, merge_range.min_col).value
        min_r, max_r = merge_range.min_row, merge_range.max_row
        min_c, max_c = merge_range.min_col, merge_range.max_col
        ws.unmerge_cells(str(merge_range))
        for r in range(min_r, max_r + 1):
            for c in range(min_c, max_c + 1):
                ws.cell(row=r, column=c).value = top_val


def cell_val(ws, row, col):
    if col is None:
        return ''
    v = ws.cell(row=row, column=col).value
    return str(v).strip() if v is not None else ''


def parse_steps(raw):
    if not raw:
        return []
    lines = re.split(r'\n|\\n', raw)
    result = []
    for line in lines:
        line = line.strip()
        line = re.sub(r'^\d+[\.\)\-]\s*', '', line)
        if line:
            result.append(line)
    return result


def to_snake(title):
    """Convert TC title to Snake_Case for RF test name."""
    # Strip common Vietnamese/English TC prefixes (TH:, TC:, 1., etc.)
    title = re.sub(r'^(?:TH|TC|Test\s*Case)\s*[:\.)\-]\s*', '', title, flags=re.IGNORECASE)
    title = re.sub(r'^\d+[\.\)\-]\s*', '', title)
    title = re.sub(r'[^\w\s]', ' ', title)
    title = re.sub(r'\s+', ' ', title).strip()
    words = title.split()
    return '_'.join(w.capitalize() for w in words if w)


def parse_sheet(ws):
    unmerge_fill(ws)
    header_row = find_header_row(ws)
    if header_row is None:
        return None, None

    col_map = map_columns(ws, header_row)
    missing = REQUIRED_COLUMNS - col_map.keys()
    if missing:
        return col_map, {'error': f'Missing required columns: {missing}'}

    # Collect header strings so fill-down artifacts (sub-header rows) can be skipped.
    # When header cells are merged vertically across multiple rows, unmerge_fill copies
    # the header text into the rows below (e.g. rows 14-15 in multi-level header sheets).
    header_strings = set()
    for key in col_map:
        v = ws.cell(row=header_row, column=col_map[key]).value
        if v:
            header_strings.add(str(v).lower().strip())

    tcs = []
    current_tc = None
    tc_counter = 0
    prev_category = ''

    for row_idx in range(header_row + 1, ws.max_row + 1):
        id_val    = cell_val(ws, row_idx, col_map.get('id'))
        title_val = cell_val(ws, row_idx, col_map.get('title'))
        steps_val = cell_val(ws, row_idx, col_map.get('steps'))
        exp_val   = cell_val(ws, row_idx, col_map.get('expected'))
        cat_val   = cell_val(ws, row_idx, col_map.get('category'))
        data_val  = cell_val(ws, row_idx, col_map.get('data'))
        notes_val = cell_val(ws, row_idx, col_map.get('notes'))

        # Skip fill-down artifacts: rows where key columns still hold header text.
        if steps_val.lower().strip() in header_strings or exp_val.lower().strip() in header_strings:
            continue

        # Skip completely blank rows.
        if not any([id_val, title_val, steps_val, exp_val]):
            continue

        # Skip horizontally-merged section rows: after unmerge_fill, a row merged
        # across columns gets the same value in title and steps (and possibly more).
        # Detected when id is empty and title == steps (partial or full horizontal merge).
        if not id_val and title_val and title_val == steps_val:
            prev_category = title_val
            continue

        # Section / category header rows: have label text but no steps and no expected.
        # Capture as the running category and skip — do not create a TC.
        if not steps_val and not exp_val:
            label = cat_val or title_val
            if label:
                prev_category = label
            continue

        # Update running category when the column has a real value.
        if cat_val:
            prev_category = cat_val
        effective_category = prev_category

        is_new_tc = bool(id_val or title_val)

        if is_new_tc:
            if current_tc:
                tcs.append(current_tc)
            tc_counter += 1
            current_tc = {
                'raw_id': id_val,
                'tc_num': tc_counter,
                'snake_name': to_snake(title_val),
                'category': effective_category,
                'title': title_val,
                'data': data_val,
                'steps': parse_steps(steps_val),
                'expected': exp_val,
                'notes': notes_val,
            }
        elif current_tc:
            # Continuation row — append steps / expected / notes.
            if steps_val:
                current_tc['steps'].extend(parse_steps(steps_val))
            if exp_val and exp_val != current_tc['expected']:
                current_tc['expected'] = (current_tc['expected'] + '\n' + exp_val).strip()
            if notes_val and notes_val != current_tc['notes']:
                current_tc['notes'] = (current_tc['notes'] + '\n' + notes_val).strip()

    if current_tc:
        tcs.append(current_tc)

    return col_map, {'total': len(tcs), 'sheet': ws.title, 'tcs': tcs}


def parse_excel(path):
    wb = openpyxl.load_workbook(path, data_only=True)

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        col_map, result = parse_sheet(ws)
        if result and 'error' not in result:
            result['columns_detected'] = list(col_map.keys())
            return result

    return {'error': 'No sheet with recognisable TC headers found. Expected columns: ID, Trường hợp kiểm thử, Các bước thực hiện, Kết quả mong muốn'}


def _render_field_multiline(label, value):
    """Render a field that may contain embedded newlines."""
    lines = [l for l in value.split('\n') if l.strip()]
    if len(lines) <= 1:
        return [f'**{label}**: {value}']
    out = [f'**{label}**:']
    for l in lines:
        out.append(f'  {l}')
    return out


def render_markdown(data, feature, xlsx_filename):
    """Convert parsed TC data to TC-NNN markdown format."""
    lines = []
    lines.append(f'# {feature} — Manual Test Cases\n')
    lines.append(f'> Imported from: {xlsx_filename}')
    lines.append(f'> Total: {data["total"]} test cases\n')
    lines.append('---\n')

    for tc in data['tcs']:
        n = tc['tc_num']
        lines.append(f'### TC-{n:03d}: {tc["snake_name"]}')
        if tc.get('raw_id'):
            lines.append(f'**TC ID**: {tc["raw_id"]}')
        lines.extend(_render_field_multiline('Category', tc['category']))
        lines.append('**Priority**: P1')
        if tc.get('data'):
            lines.extend(_render_field_multiline('Preconditions', tc['data']))
        lines.append('**Steps**:')
        for i, step in enumerate(tc['steps'], 1):
            lines.append(f'{i}. {step}')
        lines.extend(_render_field_multiline('Expected Results', tc['expected']))
        if tc.get('notes'):
            lines.extend(_render_field_multiline('Notes', tc['notes']))
        lines.append('')

    return '\n'.join(lines)


if __name__ == '__main__':
    import argparse as _ap
    import os as _os

    parser = _ap.ArgumentParser(description='Parse Excel TC file to TC-NNN markdown.')
    parser.add_argument('xlsx', help='Path to .xlsx file')
    parser.add_argument('--write', metavar='OUTPUT_PATH',
                        help='Write rendered markdown to this path instead of printing JSON')
    parser.add_argument('--feature', metavar='FEATURE',
                        help='Feature name used in the markdown header (required with --write)')
    args = parser.parse_args()

    result = parse_excel(args.xlsx)

    if args.write:
        if 'error' in result:
            print(json.dumps(result, ensure_ascii=False))
            sys.exit(1)
        feature = args.feature or _os.path.splitext(_os.path.basename(args.xlsx))[0]
        xlsx_filename = _os.path.basename(args.xlsx)
        md = render_markdown(result, feature, xlsx_filename)
        _os.makedirs(_os.path.dirname(args.write) or '.', exist_ok=True)
        with open(args.write, 'w', encoding='utf-8') as f:
            f.write(md)
        print(json.dumps({'written': args.write, 'total': result['total']}, ensure_ascii=False))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))