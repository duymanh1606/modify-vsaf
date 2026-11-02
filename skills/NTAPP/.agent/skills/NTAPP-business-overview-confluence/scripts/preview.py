# -*- coding: utf-8 -*-
"""
preview.py — render mxfile (KHÔNG nén) ra PNG để SOI TRƯỚC KHI PUBLISH + lint hình học.

Vì sao cần: drawio_lib.py chỉ sinh XML. Nếu không render, cả agent lẫn người đều KHÔNG
nhìn thấy sơ đồ cho tới khi nó đã nằm trên Confluence — đúng cách mà lỗi "mũi tên trùng
nhau" lọt lên trang xuất bản (2026-08-07). Script này đóng vòng lặp vẽ → soi → sửa,
tương đương phần PNG của generator activity bên skill SRS, nhưng giữ nguyên Python.

Dùng:
    python preview.py <mxfile> [mxfile2 ...] [-o OUTDIR] [--no-png] [--strict]

    <mxfile>   file mxfile do drawio_lib sinh (KHÔNG có đuôi, tên = diagramName)
    -o OUTDIR  nơi ghi .svg/.png (mặc định: cùng thư mục file nguồn)
    --no-png   chỉ lint + ghi SVG, bỏ bước Chrome
    --strict   có cảnh báo lint => exit 1 (dùng khi muốn chặn cứng)

Exit code (CONTRACT — giống build-activity-diagram.mjs bên SRS):
    0 = đã ghi SVG + PNG, lint sạch (hoặc chỉ có cảnh báo mà không --strict)
    2 = đã ghi SVG + lint chạy xong nhưng KHÔNG có PNG (thiếu Chrome / Chrome lỗi).
        KHÔNG phải lỗi chặn: mxfile vẫn publish được, macro draw.io tự render live.
        Chỉ mất ảnh soi -> phải tự soi bằng file .svg.
    1 = mxfile hỏng / không parse được, hoặc --strict và lint có cảnh báo.

PNG ở đây là ẢNH SOI, không bắt buộc đính kèm trang. Nếu muốn dùng làm ảnh tĩnh dự phòng
(export PDF/email) thì khai báo trong manifest theo confluence-publish.md.

⚠️ Độ trung thực: cạnh có port + waypoint (edgeStyle=none — state_diagram / breakdown_tree /
process_3col) được vẽ ĐÚNG đường mà draw.io sẽ vẽ. Cạnh orthogonalEdgeStyle (overview_zones)
và entityRelationEdgeStyle (erd) do draw.io tự định tuyến lúc render nên ở đây chỉ vẽ XẤP XỈ
(nối tâm, cắt ở mép hộp) — xem bố cục, đừng phán xét đường đi. Lint cũng bỏ qua nhóm này.
"""
import os
import re
import subprocess
import sys
import tempfile
import shutil
import xml.etree.ElementTree as ET

CHROME_CANDIDATES = [
    os.environ.get("CHROME_PATH", ""),
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
]
WIDE_PAGE_WARN = 2600          # rộng hơn mức này -> Confluence scale nhỏ, chữ khó đọc
SEG_OVERLAP_MIN = 12           # 2 đoạn cùng trục chồng nhau quá ngần này px -> cảnh báo
AXIS_TOL = 4                   # sai số coi 2 đoạn là cùng trục


# ---------------------------------------------------------------- parse mxfile
class Node(object):
    __slots__ = ("id", "x", "y", "w", "h", "val", "style")

    def __init__(self, i, x, y, w, h, val, style):
        self.id, self.x, self.y, self.w, self.h, self.val, self.style = i, x, y, w, h, val, style

    @property
    def r(self): return self.x + self.w

    @property
    def b(self): return self.y + self.h

    @property
    def cx(self): return self.x + self.w / 2.0

    @property
    def cy(self): return self.y + self.h / 2.0

    @property
    def is_container(self):
        s = self.style
        return "fillColor=none" in s or "swimlane" in s or "text;" in s


class Edge(object):
    __slots__ = ("id", "src", "dst", "val", "style", "pts")

    def __init__(self, i, src, dst, val, style, pts):
        self.id, self.src, self.dst, self.val, self.style, self.pts = i, src, dst, val, style, pts

    @property
    def routed(self):
        """Cạnh do ta tự định tuyến (port + waypoint) — preview khớp draw.io 1:1."""
        return "edgeStyle=none" in self.style


def sval(style, key, cast=str, default=None):
    m = re.search(re.escape(key) + r"=([^;]+)", style or "")
    if not m:
        return default
    try:
        return cast(m.group(1))
    except ValueError:
        return default


def parse(path):
    with open(path, "r", encoding="utf-8") as fh:
        raw = fh.read()
    root = ET.fromstring(raw.encode("utf-8"))
    model = root.find(".//mxGraphModel")
    if model is None:
        raise ValueError("khong tim thay <mxGraphModel> (mxfile bi nen? script chi doc ban KHONG nen)")
    pw = int(float(model.get("pageWidth", 1000)))
    ph = int(float(model.get("pageHeight", 800)))
    nodes, edges = {}, []
    for c in model.find("root"):
        g = c.find("mxGeometry")
        if c.get("vertex") == "1" and g is not None:
            nodes[c.get("id")] = Node(
                c.get("id"), float(g.get("x", 0)), float(g.get("y", 0)),
                float(g.get("width", 0)), float(g.get("height", 0)),
                c.get("value", ""), c.get("style", ""))
        elif c.get("edge") == "1":
            pts = []
            arr = g.find("Array") if g is not None else None
            if arr is not None:
                pts = [(float(p.get("x")), float(p.get("y"))) for p in arr]
            edges.append(Edge(c.get("id"), c.get("source"), c.get("target"),
                              c.get("value", ""), c.get("style", ""), pts))
    return pw, ph, nodes, edges


# ------------------------------------------------------------------ hình học
def clip_to_rect(p, q, n):
    """Cắt đoạn p->q tại mép hộp n (dùng cho cạnh xấp xỉ nối tâm)."""
    dx, dy = q[0] - p[0], q[1] - p[1]
    if dx == 0 and dy == 0:
        return p
    t = 1.0
    for edge_t in (
        ((n.x - p[0]) / dx) if dx else None,
        ((n.r - p[0]) / dx) if dx else None,
        ((n.y - p[1]) / dy) if dy else None,
        ((n.b - p[1]) / dy) if dy else None,
    ):
        if edge_t is None or not (0 < edge_t <= 1):
            continue
        px, py = p[0] + dx * edge_t, p[1] + dy * edge_t
        if n.x - 0.5 <= px <= n.r + 0.5 and n.y - 0.5 <= py <= n.b + 0.5:
            t = min(t, edge_t)
    return (p[0] + dx * t, p[1] + dy * t)


def polyline(e, nodes):
    """Đường đi thực của cạnh. routed -> theo port + waypoint; còn lại -> xấp xỉ nối tâm."""
    s, t = nodes.get(e.src), nodes.get(e.dst)
    if s is None or t is None:
        return []
    if e.routed:
        ex = sval(e.style, "exitX", float, 0.5)
        ey = sval(e.style, "exitY", float, 1.0)
        nx = sval(e.style, "entryX", float, 0.5)
        ny = sval(e.style, "entryY", float, 0.0)
        p = (s.x + s.w * ex, s.y + s.h * ey)
        q = (t.x + t.w * nx, t.y + t.h * ny)
        return [p] + list(e.pts) + [q]
    p = clip_to_rect((s.cx, s.cy), (t.cx, t.cy), s)
    q = clip_to_rect((t.cx, t.cy), (s.cx, s.cy), t)
    return [p] + list(e.pts) + [q]


def seg_hits_rect(p, q, n, margin=2.0):
    """Đoạn thẳng có xuyên qua LÒNG hộp không (Liang-Barsky, đã co biên margin)."""
    x0, y0, x1, y1 = n.x + margin, n.y + margin, n.r - margin, n.b - margin
    if x1 <= x0 or y1 <= y0:
        return False
    dx, dy = q[0] - p[0], q[1] - p[1]
    t0, t1 = 0.0, 1.0
    for pp, qq in ((-dx, p[0] - x0), (dx, x1 - p[0]), (-dy, p[1] - y0), (dy, y1 - p[1])):
        if pp == 0:
            if qq < 0:
                return False
            continue
        r = qq / float(pp)
        if pp < 0:
            if r > t1:
                return False
            t0 = max(t0, r)
        else:
            if r < t0:
                return False
            t1 = min(t1, r)
    return t0 < t1


def overlap_len(a0, a1, b0, b1):
    return min(a1, b1) - max(a0, b0)


# --------------------------------------------------------------------- lint
def lint(pw, ph, nodes, edges):
    warns = []
    boxes = [n for n in nodes.values() if not n.is_container and n.w > 0 and n.h > 0]

    # 1) hộp đè hộp
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            ox = overlap_len(a.x, a.r, b.x, b.r)
            oy = overlap_len(a.y, a.b, b.y, b.b)
            if ox > 1 and oy > 1:
                warns.append("hop '%s' de len hop '%s' (%dx%d px)"
                             % (a.id, b.id, round(ox), round(oy)))

    # 2) cạnh xuyên qua hộp không liên quan (chỉ soát cạnh mình tự định tuyến)
    for e in edges:
        if not e.routed:
            continue
        pl = polyline(e, nodes)
        for k in range(len(pl) - 1):
            for n in boxes:
                if n.id in (e.src, e.dst):
                    continue
                if seg_hits_rect(pl[k], pl[k + 1], n):
                    warns.append("canh %s (%s -> %s) xuyen qua hop '%s' — doi lan rail"
                                 % (e.id, e.src, e.dst, n.id))
                    break

    # 3) hai cạnh chạy chồng nhau trên cùng một trục
    segs = []
    for e in edges:
        if not e.routed:
            continue
        pl = polyline(e, nodes)
        for k in range(len(pl) - 1):
            segs.append((e, pl[k], pl[k + 1]))
    seen = set()
    for i, (e1, p1, q1) in enumerate(segs):
        for e2, p2, q2 in segs[i + 1:]:
            if e1.id == e2.id or e1.src == e2.src:
                continue          # cùng nguồn = thân cây dùng chung, có chủ đích
            key = tuple(sorted((e1.id, e2.id)))
            if key in seen:
                continue
            vert = abs(p1[0] - q1[0]) < 1 and abs(p2[0] - q2[0]) < 1
            horz = abs(p1[1] - q1[1]) < 1 and abs(p2[1] - q2[1]) < 1
            if vert and abs(p1[0] - p2[0]) < AXIS_TOL:
                if overlap_len(min(p1[1], q1[1]), max(p1[1], q1[1]),
                               min(p2[1], q2[1]), max(p2[1], q2[1])) > SEG_OVERLAP_MIN:
                    warns.append("canh %s va %s chong nhau tren truc doc x=%d"
                                 % (e1.id, e2.id, round(p1[0])))
                    seen.add(key)
            elif horz and abs(p1[1] - p2[1]) < AXIS_TOL:
                if overlap_len(min(p1[0], q1[0]), max(p1[0], q1[0]),
                               min(p2[0], q2[0]), max(p2[0], q2[0])) > SEG_OVERLAP_MIN:
                    warns.append("canh %s va %s chong nhau tren truc ngang y=%d"
                                 % (e1.id, e2.id, round(p1[1])))
                    seen.add(key)

    # 4) node tràn ra ngoài khổ trang
    for n in nodes.values():
        if n.x < 0 or n.y < 0 or n.r > pw + 1 or n.b > ph + 1:
            warns.append("hop '%s' tran ra ngoai kho trang (%dx%d)" % (n.id, pw, ph))

    # 5) trang quá rộng -> Confluence thu nhỏ, chữ không đọc được
    if pw > WIDE_PAGE_WARN:
        warns.append("trang rong %dpx (> %d) — Confluence se thu nho, chu kho doc; "
                     "cannh nhac tach nhieu so do theo cum" % (pw, WIDE_PAGE_WARN))
    return warns


# ---------------------------------------------------------------------- SVG
def esc(s):
    return (str(s).replace("&amp;", "&").replace("&#10;", "\n")
            .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def node_svg(n):
    fill = sval(n.style, "fillColor", str, "#ffffff") or "#ffffff"
    stroke = sval(n.style, "strokeColor", str, "#333333") or "#333333"
    sw = sval(n.style, "strokeWidth", float, 1.4)
    if fill == "none":
        fill = "transparent"
    if stroke == "none":
        stroke = "transparent"
    dash = ' stroke-dasharray="8 5"' if "dashed=1" in n.style else ""
    fs = sval(n.style, "fontSize", float, 12.0)
    bold = "fontStyle=1" in n.style or "fontStyle=3" in n.style
    ital = "fontStyle=2" in n.style
    align = sval(n.style, "align", str, "center")
    valign = sval(n.style, "verticalAlign", str, "middle")
    padl = sval(n.style, "spacingLeft", float, 0.0)
    justify = {"left": "flex-start", "right": "flex-end"}.get(align, "center")
    items = {"top": "flex-start", "bottom": "flex-end"}.get(valign, "center")

    if "shape=umlActor" in n.style:
        cxx, hh = n.cx, n.h
        body = ('<g stroke="%s" stroke-width="2" fill="none">'
                '<circle cx="%.0f" cy="%.0f" r="%.0f" fill="%s"/>'
                '<path d="M %.0f %.0f L %.0f %.0f M %.0f %.0f L %.0f %.0f M %.0f %.0f L %.0f %.0f '
                'M %.0f %.0f L %.0f %.0f"/></g>'
                % (stroke, cxx, n.y + hh * .16, hh * .15, fill,
                   cxx, n.y + hh * .31, cxx, n.y + hh * .66,
                   n.x + 6, n.y + hh * .44, n.r - 6, n.y + hh * .44,
                   cxx, n.y + hh * .66, n.x + 8, n.b,
                   cxx, n.y + hh * .66, n.r - 8, n.b))
        lbl = ('<foreignObject x="%.0f" y="%.0f" width="%.0f" height="34">'
               '<div xmlns="http://www.w3.org/1999/xhtml" class="t" '
               'style="font-size:%.1fpx;justify-content:center;align-items:flex-start">%s</div>'
               '</foreignObject>' % (n.x - 30, n.b + 2, n.w + 60, fs, esc(n.val)))
        return body + lbl

    if "ellipse" in n.style:
        shape = ('<ellipse cx="%.1f" cy="%.1f" rx="%.1f" ry="%.1f" fill="%s" stroke="%s" '
                 'stroke-width="%.1f"%s/>' % (n.cx, n.cy, n.w / 2, n.h / 2, fill, stroke, sw, dash))
    elif "rhombus" in n.style:
        shape = ('<polygon points="%.0f,%.0f %.0f,%.0f %.0f,%.0f %.0f,%.0f" fill="%s" '
                 'stroke="%s" stroke-width="%.1f"%s/>'
                 % (n.cx, n.y, n.r, n.cy, n.cx, n.b, n.x, n.cy, fill, stroke, sw, dash))
    elif "shape=cylinder3" in n.style:
        shape = ('<rect x="%.0f" y="%.0f" width="%.0f" height="%.0f" rx="8" fill="%s" '
                 'stroke="%s" stroke-width="%.1f"%s/>' % (n.x, n.y, n.w, n.h, fill, stroke, sw, dash))
    else:
        rx = 8 if "rounded=1" in n.style else 0
        shape = ('<rect x="%.0f" y="%.0f" width="%.0f" height="%.0f" rx="%d" fill="%s" '
                 'stroke="%s" stroke-width="%.1f"%s/>' % (n.x, n.y, n.w, n.h, rx, fill, stroke, sw, dash))
    style = ("font-size:%.1fpx;justify-content:%s;align-items:%s;font-weight:%s;font-style:%s;"
             "padding-left:%.0fpx" % (fs, justify, items, "700" if bold else "400",
                                      "italic" if ital else "normal", padl + 4))
    txt = ('<foreignObject x="%.0f" y="%.0f" width="%.0f" height="%.0f">'
           '<div xmlns="http://www.w3.org/1999/xhtml" class="t" style="%s">%s</div></foreignObject>'
           % (n.x, n.y, n.w, n.h, style, esc(n.val)))
    return shape + txt


def edge_svg(e, nodes, mid):
    pl = polyline(e, nodes)
    if len(pl) < 2:
        return ""
    stroke = sval(e.style, "strokeColor", str, "#4b5563") or "#4b5563"
    dash = ' stroke-dasharray="7 4"' if "dashed=1" in e.style else ""
    d = "M " + " L ".join("%.0f %.0f" % p for p in pl)
    marker = "arw-" + re.sub(r"[^0-9a-fA-F]", "", stroke)
    out = ('<path d="%s" fill="none" stroke="%s" stroke-width="1.6"%s marker-end="url(#%s)"/>'
           % (d, stroke, dash, marker))
    if e.val:
        i = len(pl) // 2
        lx, ly = (pl[i][0] + pl[i - 1][0]) / 2, (pl[i][1] + pl[i - 1][1]) / 2
        fc = sval(e.style, "fontColor", str, "#b45309") or "#b45309"
        w = 7.0 * len(e.val) + 8
        out += ('<rect x="%.0f" y="%.0f" width="%.0f" height="15" fill="#ffffff" opacity="0.92"/>'
                '<text x="%.0f" y="%.0f" font-size="10.5" fill="%s">%s</text>'
                % (lx + 3, ly - 12, w, lx + 6, ly - 1, fc, esc(e.val)))
    mid.add(stroke)
    return out


def build_svg(pw, ph, nodes, edges, title):
    colors = set()
    ebody = []
    for e in edges:
        ebody.append(edge_svg(e, nodes, colors))
    defs = "".join(
        '<marker id="arw-%s" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" '
        'markerUnits="strokeWidth"><path d="M0,0 L8,3 L0,6 z" fill="%s"/></marker>'
        % (re.sub(r"[^0-9a-fA-F]", "", c), c) for c in colors)
    order = sorted(nodes.values(), key=lambda n: (0 if n.is_container else 1, n.y))
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" '
            'font-family="Segoe UI, Arial, sans-serif"><defs>%s</defs>'
            '<rect width="100%%" height="100%%" fill="#ffffff"/>%s%s%s</svg>'
            % (pw, ph, pw, ph, defs,
               "".join(node_svg(n) for n in order if n.is_container),
               "".join(ebody),
               "".join(node_svg(n) for n in order if not n.is_container)))


# Template dùng token @@..@@ + replace, KHÔNG dùng '%' (CSS có sẵn ký tự '%' -> vỡ format).
HTML = """<!doctype html><html><head><meta charset="utf-8"><style>
*{box-sizing:border-box} body{margin:0;background:#fff}
.t{width:100%;height:100%;display:flex;text-align:center;line-height:1.25;color:#1f2937;
   padding:3px 6px;overflow:hidden;white-space:pre-wrap;word-break:break-word}
h2{font:700 18px "Segoe UI",Arial;color:#0b3d5c;text-align:center;margin:22px 40px 4px}
svg{display:block;margin:0 auto 30px}
</style></head><body><h2>@@TITLE@@</h2>@@SVG@@</body></html>"""


# --------------------------------------------------------------------- render
def find_chrome():
    for c in CHROME_CANDIDATES:
        if c and os.path.isfile(c):
            return c
    return None


def shoot(html_path, png_path, pw, ph):
    chrome = find_chrome()
    if not chrome:
        return False, "khong tim thay Chrome/Edge (dat bien CHROME_PATH)"
    profile = tempfile.mkdtemp(prefix="bo-preview-")
    try:
        subprocess.check_call([
            chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
            "--force-device-scale-factor=2", "--user-data-dir=" + profile,
            "--no-first-run", "--no-default-browser-check",
            "--window-size=%d,%d" % (int(pw) + 90, int(ph) + 120),
            "--default-background-color=FFFFFFFF",
            "--screenshot=" + png_path, "file:///" + html_path.replace("\\", "/"),
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (subprocess.CalledProcessError, OSError) as ex:
        return False, "Chrome loi: %s" % ex
    finally:
        shutil.rmtree(profile, ignore_errors=True)
    if not os.path.isfile(png_path):
        return False, "Chrome chay xong nhung khong co PNG"
    return True, png_path


# ----------------------------------------------------------------------- main
def main(argv):
    files, outdir, want_png, strict = [], None, True, False
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "-o":
            i += 1
            outdir = argv[i]
        elif a == "--no-png":
            want_png = False
        elif a == "--strict":
            strict = True
        else:
            files.append(a)
        i += 1
    if not files:
        print(__doc__)
        return 1

    any_warn, missing_png = False, False
    for f in files:
        if not os.path.isfile(f):
            print("LOI: khong thay file %s" % f)
            return 1
        base = os.path.basename(f)
        # PHẢI tuyệt đối: Chrome --headless=new hiểu path tương đối theo cwd của CHÍNH NÓ,
        # nên -o dạng tương đối sẽ ghi PNG đi chỗ khác (hoặc mất hẳn) mà không báo lỗi.
        od = os.path.abspath(outdir) if outdir else (os.path.dirname(os.path.abspath(f)) or ".")
        if not os.path.isdir(od):
            os.makedirs(od)
        try:
            pw, ph, nodes, edges = parse(f)
        except (ET.ParseError, ValueError) as ex:
            print("LOI parse %s: %s" % (base, ex))
            return 1

        warns = lint(pw, ph, nodes, edges)
        svg = build_svg(pw, ph, nodes, edges, base)
        svg_path = os.path.join(od, base + ".preview.svg")
        with open(svg_path, "w", encoding="utf-8") as fh:
            fh.write(svg)

        n_routed = sum(1 for e in edges if e.routed)
        print("\n=== %s === %dx%d px | %d hop | %d canh (%d dinh tuyen chinh xac, %d xap xi)"
              % (base, pw, ph, len(nodes), len(edges), n_routed, len(edges) - n_routed))
        print("  SVG: %s" % svg_path)

        png_path = os.path.join(od, base + ".preview.png")
        if want_png:
            html = HTML.replace("@@TITLE@@", esc(base)).replace("@@SVG@@", svg)
            hp = os.path.join(tempfile.gettempdir(), "bo-preview-%s.html" % re.sub(r"\W", "_", base))
            with open(hp, "w", encoding="utf-8") as fh:
                fh.write(html)
            ok, info = shoot(hp, png_path, pw, ph)
            if ok:
                print("  PNG: %s   <- MO ANH NAY SOI TRUOC KHI PUBLISH" % info)
            else:
                missing_png = True
                print("  PNG: KHONG co (%s) — soi bang file SVG o tren. KHONG chan publish." % info)

        if warns:
            any_warn = True
            print("  LINT: %d canh bao" % len(warns))
            for w in warns:
                print("    - " + w)
        else:
            print("  LINT: sach")

    if any_warn and strict:
        return 1
    return 2 if missing_png else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
