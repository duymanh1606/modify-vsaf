# -*- coding: utf-8 -*-
"""Build storage XHTML trang KBNT — CHI bang case.

Sua so v1:
  - Header tu viet bang tay (v1 copy byte tu template -> double-encoded mojibake,
    va bê luon loi lech 1 o cua template o hang 2/3).
  - Bullet hoa noi dung o theo rule NTAPP-srs-to-confluence:
    o >= 2 cau VA >= 80 ky tu -> <ul><li>; co thu tu -> <ol><li>; nhom co nhan
    -> <li><strong>Nhan:</strong> ...
  - colgroup dat be rong cot.
  - Muc da nghiem thu o dot khac -> giu hang muc + nhan, BO het hang case.
"""
import argparse
import io
import os
import re

ap = argparse.ArgumentParser(
    description=u"Build storage XHTML bang case KBNT tu file markdown chi-bang-case.")
ap.add_argument("--cases", required=True, help=u"file {dot_slug}_kbnt_cases.md")
ap.add_argument("--manifest", required=True, help=u"file dot-manifest.yaml")
ap.add_argument("--out", required=True, help=u"file storage .xhtml se ghi ra")
ap.add_argument("--author", default="", help=u"gia tri o 'Nguoi tao' cua bang thong tin dau tai lieu")
ap.add_argument("--carry-info", default="", metavar="SNAPSHOT",
                help=u"snapshot lan publish truoc — neu co bang thong tin thi GIU NGUYEN VERBATIM "
                     u"(4 o chu ky do nguoi dung dien, tuyet doi khong sinh lai)")
ap.add_argument("--no-info", action="store_true", help=u"bo bang thong tin dau tai lieu")
ARGS = ap.parse_args()

CASES = ARGS.cases
MANIFEST = ARGS.manifest
OUT = ARGS.out

TD = '<td style="text-align: left;">'
EMPTY = TD + "<br /></td>"

# Muc da nghiem thu tai dot khac -> doc tu dot-manifest.yaml (repo la nguon su that).


def load_manifest():
    import yaml
    with io.open(MANIFEST, encoding="utf-8") as f:
        return yaml.safe_load(f.read()) or {}


MAN = load_manifest()
DONE = {k: (str(v["page_id"]), v["page_title"])
        for k, v in (MAN.get("da_nghiem_thu_o_dot_khac") or {}).items()}
KBNV = MAN.get("tai_lieu_kbnv") or {}

# Be rong cot (px) — 16 cot theo dung thu tu template.
COLW = [110, 300, 360, 380, 420, 78, 78, 78, 78, 78, 78, 62, 62, 62, 62, 260]

NHAN = (u"Giao diện", u"Dữ liệu", u"Gửi đi", u"Log", u"Nhật ký",
        u"LƯU Ý", u"Lưu ý", u"Hồi quy", u"Ghi chú")


def read(p):
    with io.open(p, encoding="utf-8") as f:
        return f.read()


def esc(md):
    s = md.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    return s


def segments(md):
    """Tach o markdown thanh cac ve theo <br> goc."""
    parts = re.split(r"<br\s*/?>", md)
    return [p.strip() for p in parts if p.strip()]


def sentences(txt):
    """Tach cau: dau cham + khoang trang + chu hoa/so. Khong tach o so thap phan."""
    # dau cham + chu hoa/so  HOAC  dau cham phay (ve cau — mot bullet khong ganh 2 y)
    out = re.split(r"(?<=\.)\s+(?=[A-ZĐÁÀẢÃẠÂẤẦẨẫẬĂẮẰẲẴẶÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÚÙỦŨỤƯỨỪỬỮỰÝỲỶỸỴ0-9])|(?<=;)\s+", txt)
    return [s.strip().rstrip(";") for s in out if s.strip(" ;")]


def split_label(seg):
    """'Giao diện: xxx' -> ('Giao diện', 'xxx'); khong co nhan -> (None, seg)."""
    m = re.match(r"^([^:]{1,20}):\s*(.+)$", seg, re.S)
    if m and m.group(1).strip() in NHAN:
        return m.group(1).strip(), m.group(2).strip()
    return None, seg


def li_for(seg):
    """Mot ve -> mot <li>, tu tach tiep neu ve con >= 2 cau va dai."""
    label, body = split_label(seg)
    sents = sentences(body)
    if len(sents) >= 2 and len(body) >= 80:
        inner = "".join("<li>%s</li>" % esc(s) for s in sents)
        if label:
            return "<li><strong>%s:</strong><ul>%s</ul></li>" % (esc(label), inner)
        return "<li><ul>%s</ul></li>" % inner
    if label:
        return "<li><strong>%s:</strong> %s</li>" % (esc(label), esc(body))
    return "<li>%s</li>" % esc(body)


def cell_prose(md):
    """O van xuoi: >= 2 y hoac >= 2 cau & >= 80 ky tu -> <ul>."""
    segs = segments(md)
    if not segs:
        return TD + "<br /></td>"
    plain = re.sub(r"<br\s*/?>", " ", md)
    if len(segs) == 1 and not (len(sentences(plain)) >= 2 and len(plain) >= 80):
        return TD + esc(segs[0]) + "</td>"
    return TD + "<ul>" + "".join(li_for(s) for s in segs) + "</ul></td>"


def cell_steps(md):
    """O 'Cac buoc thuc hien': co thu tu -> <ol>, bo tien to so."""
    segs = segments(md)
    if not segs:
        return TD + "<br /></td>"
    numbered = sum(1 for s in segs if re.match(r"^\d+[\.\)]\s", s))
    if numbered >= 2:
        items = [re.sub(r"^\d+[\.\)]\s*", "", s) for s in segs]
        return TD + "<ol>" + "".join("<li>%s</li>" % esc(x) for x in items) + "</ol></td>"
    return cell_prose(md)


ORDER_MUC = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X",
             "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX"]
KET_LUAN = u"Đủ điều kiện triển khai/Không đủ điều kiện triển khai"
INFO_NHAN = [u"Version tài liệu KBNV", u"Ngày thực hiện", u"Người tạo",
             u"Người phê duyệt", u"Người thực hiện", u"Kết luận"]


def kbnv_cell_body(order):
    """O 'Version tai lieu KBNV' = danh sach page-link toi cac trang KBNV da viet.

    Link theo TIEU DE (ri:content-title) — dung convention cac trang KBNT cu trong nhanh.
    Muc khong co KBNV rieng thi bo qua, KHONG doan.
    """
    if not KBNV:
        return "<br />"
    items = []
    for muc in order:
        docs = KBNV.get(muc)
        if not docs:
            continue
        links = ['<ac:link><ri:page ri:content-title="%s" /></ac:link>' % esc(d["title"])
                 for d in docs]
        items.append(u"<li><strong>Mục %s:</strong> %s</li>" % (muc, "<br />".join(links)))
    return ("<ul>" + "".join(items) + "</ul>") if items else "<br />"


def info_table():
    """Bang thong tin dau tai lieu (2 cot x 6 dong) — dung khuon template.

    Cot 2 la KHOI CHU KY: publish lan 2+ phai giu nguyen, nen uu tien carry tu snapshot.
    """
    if ARGS.no_info:
        return ""
    if ARGS.carry_info and os.path.isfile(ARGS.carry_info):
        with io.open(ARGS.carry_info, encoding="utf-8") as f:
            prev = f.read()
        m = re.search(r"<table[^>]*>\s*(?:<colgroup>.*?</colgroup>\s*)?<tbody>.*?</tbody>\s*</table>",
                      prev, re.S)
        if m and u"Version tài liệu KBNV" in m.group(0):
            return m.group(0)     # GIU NGUYEN — co the da co chu ky
    vals = [kbnv_cell_body(ORDER_MUC), "<br />",
            esc(ARGS.author) if ARGS.author else "<br />",
            "<br />", "<br />", esc(KET_LUAN)]
    rows = []
    for nhan, val in zip(INFO_NHAN, vals):
        rows.append('<tr><th style="text-align: left;">%s</th>%s%s</td></tr>'
                    % (esc(nhan), TD, val))
    return ('<table class="relative-table wrapped" style="width: 733.0px;"><tbody>'
            + "".join(rows) + "</tbody></table>")


def header():
    b = lambda t: "<strong>%s</strong>" % t
    r3 = lambda t: '<td style="text-align: left;" rowspan="3">%s</td>' % b(t)
    g2 = lambda t: '<td style="text-align: left;" colspan="2" rowspan="2">%s</td>' % b(t)
    c = lambda t: TD + b(t) + "</td>"

    row1 = ("<tr>"
            + r3(u"STT") + r3(u"Mô tả trường hợp") + r3(u"Điều kiện")
            + r3(u"Các bước thực hiện") + r3(u"Kết quả mong muốn")
            + g2(u"Kết quả môi trường Test") + g2(u"Kết quả môi trường UAT")
            + g2(u"Kết quả sau upcode")
            + '<td style="text-align: left;" colspan="4">'
            + b(u"Kết quả sau Merge app môi trường Production") + "<br />"
            + b(u"(điền cột này trong trường hợp đầu việc có up App)") + "</td>"
            + r3(u"Ghi chú") + "</tr>")
    # hang 2 chi con 4 cot Production (12-15) — template goc thua 1 o, da bo.
    row2 = ("<tr>"
            + '<td style="text-align: left;" colspan="2">%s</td>' % b(u"iOS (phiên bản)")
            + '<td style="text-align: left;" colspan="2">%s</td>' % b(u"Android (phiên bản)")
            + "</tr>")
    # hang 3: 6 o cho Test/UAT/upcode + 4 o cho iOS/Android = 10 o.
    row3 = "<tr>" + (c(u"Mã giao dịch") + c(u"Kết quả")) * 5 + "</tr>"
    return [row1, row2, row3]


def main():
    sections, cur = [], None
    for ln in read(CASES).replace("\r\n", "\n").split("\n"):
        s = ln.strip()
        m = re.match(r"^##\s+Mục\s+([IVX]+)\s+—\s+(.+)$", s)
        if m:
            cur = {"num": m.group(1), "name": m.group(2).strip(), "rows": []}
            sections.append(cur)
            continue
        if s.startswith("| NT-") and cur is not None:
            cols = [x.strip() for x in s.strip().strip("|").split("|")]
            if len(cols) != 6:
                raise SystemExit("dong %d o: %s" % (len(cols), cols[0]))
            cur["rows"].append(cols)

    out = []
    info = info_table()
    if info:
        out.append(info)
    out.append('<table class="relative-table wrapped" style="width: 100.0%;">')
    out.append("<colgroup>" + "".join('<col style="width: %d.0px;" />' % w for w in COLW) + "</colgroup>")
    out.append("<tbody>")
    out += header()

    n_case = n_cut = 0
    for sec in sections:
        title = esc(sec["name"])
        if sec["num"] in DONE:
            pid, pname = DONE[sec["num"]]
            title += (u" — <strong>ĐÃ NGHIỆM THU</strong> tại trang “%s” (pageId %s). "
                      u"Không chạy lại trong đợt này." % (esc(pname), pid))
            n_cut += len(sec["rows"])
        out.append("<tr>" + TD + sec["num"] + "</td>"
                   + '<td style="text-align: left;" colspan="15">' + title + "</td></tr>")
        if sec["num"] in DONE:
            continue
        for r in sec["rows"]:
            body = TD + esc(r[0]) + "</td>"
            body += cell_prose(r[1]) + cell_prose(r[2]) + cell_steps(r[3]) + cell_prose(r[4])
            body += EMPTY * 10 + cell_prose(r[5])
            out.append("<tr>" + body + "</tr>")
            n_case += 1
    out.append("</tbody></table>")

    xhtml = "".join(out)
    with io.open(OUT, "w", encoding="utf-8", newline="") as f:
        f.write(xhtml)

    # kiem tra co hoc: MOI hang (ke ca header) phai du 16 cot logic
    bad = []
    case_tbl = xhtml[xhtml.index('style="width: 100.0%;"'):]
    for i, tr in enumerate(re.findall(r"<tr>.*?</tr>", case_tbl, re.S)):
        span = 0
        for m in re.finditer(r"<td[^>]*>", tr):
            cs = re.search(r'colspan="(\d+)"', m.group(0))
            span += int(cs.group(1)) if cs else 1
        # hang 2 va 3 duoc rowspan tu hang 1 phu bot cot
        want = {1: 4, 2: 10}.get(i, 16)
        if span != want:
            bad.append((i, span, want))
    assert len(COLW) == 16, "colgroup phai 16 cot"
    print("bang thong tin: %s" % ("co" if info else "khong"))
    print("muc=%d  case-day=%d  case-cat=%d  bytes=%d" % (len(sections), n_case, n_cut,
                                                          len(xhtml.encode("utf-8"))))
    print("hang lech cot: %d %s" % (len(bad), bad[:5]))
    print("mojibake check: %s" % ("FAIL" if re.search(u"[ÃÂ][\u0080-\u00bf]", xhtml) else "ok"))
    print("out: %s" % OUT)


main()
