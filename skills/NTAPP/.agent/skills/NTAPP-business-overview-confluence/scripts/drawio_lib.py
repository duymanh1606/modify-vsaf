# -*- coding: utf-8 -*-
"""
drawio_lib — sinh nội dung mxfile (draw.io) KHÔNG NÉN cho từng loại sơ đồ của
tài liệu Tổng quan nghiệp vụ. Portable, không phụ thuộc dữ liệu dự án: truyền data vào.

Bám khung template Tổng quan nghiệp vụ (5 loại sơ đồ, xem references/style-conventions.md):
  overview_zones(title, zones, flows, actors)  -> §2 Mô hình tổng quan (bố cục VÙNG trái→phải)
  process_3col(rows)                           -> §3 Quy trình (cột: đối tượng | bước | mô tả)
  erd(entities, rels, dom_color)               -> §4 ERD lưới FIELD-LEVEL (mỗi entity 1 bảng field)
  erd_graph(entities, rels, dom_color)         -> §4 ERD MỨC BẢNG — phân tầng + định tuyến theo
                                                  kênh; dùng khi trọng tâm là QUAN HỆ giữa bảng
  state_diagram(states, transitions)           -> §5 Biểu đồ trạng thái
  breakdown_tree(root, groups)                 -> §6 Phân rã chức năng (cây building-block 3 loại)

Helper:
  esc(s)            -> escape XML (& < > ")
  label(*lines)     -> gộp nhiều dòng cho 1 ô (dùng '\\n'; wrap() đổi sang '&#10;')
  wrap(name,cells,pw,ph) -> chuỗi mxfile hoàn chỉnh

⚠️ Escape newline: LUÔN dựng nhãn nhiều dòng bằng label()/'\\n' literal. wrap() đổi '\\n'→'&#10;'
   Ở BƯỚC CUỐI, SAU esc(). ĐỪNG tự viết '&#10;' trong nhãn (esc() sẽ biến '&' → '&amp;#10;' hỏng).

⚠️ Cạnh (edge) — 2 chế độ:
   - orthogonalEdgeStyle (mặc định của _edge): dùng cho quan hệ tự do (ERD) và mũi tên
     cấp cao giữa các vùng (overview_zones), nơi node chưa canh trục.
   - edgeStyle=none + port (exitX/exitY/entryX/entryY) + waypoint (<Array as="points">):
     BẮT BUỘC cho process_3col / state_diagram / breakdown_tree. Ở các sơ đồ này node đã
     canh trục sẵn nên toạ độ tính được chính xác; để orthogonalEdgeStyle tự re-route thì
     draw.io kéo mọi cạnh chụm vào giữa → mũi tên CHỒNG LÊN NHAU và cắt qua hộp. Mỗi cạnh
     nhảy/lùi phải có LÀN RAIL riêng. Xem references/diagram-drawio.md.
"""

def esc(s):
    return (str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;'))

def label(*lines):
    """Gộp nhiều dòng thành 1 nhãn ô — dùng '\\n' literal (wrap() sẽ đổi sang '&#10;')."""
    return "\n".join(str(x) for x in lines)

def _cell(cid, val, x, y, w, h, style):
    return ('<mxCell id="%s" value="%s" style="%s" vertex="1" parent="1">'
            '<mxGeometry x="%d" y="%d" width="%d" height="%d" as="geometry"/></mxCell>'
            % (cid, esc(val), style, x, y, w, h))

def _edge(eid, s, t, val="", style="edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;endArrow=block;"):
    return ('<mxCell id="%s" value="%s" style="%s" edge="1" parent="1" source="%s" target="%s">'
            '<mxGeometry relative="1" as="geometry"/></mxCell>' % (eid, esc(val), style, s, t))

# --- cạnh "khớp pixel": port cố định + waypoint tường minh (kỹ thuật của generator
#     activity ở skill SRS). Dùng cho mọi sơ đồ đã canh trục sẵn -> không chồng mũi tên.
_PORT = "exitX=%s;exitY=%s;exitDx=0;exitDy=0;entryX=%s;entryY=%s;entryDx=0;entryDy=0;"
_EBASE = ("edgeStyle=none;html=1;rounded=0;endArrow=block;endFill=1;fontSize=10;"
          "labelBackgroundColor=#ffffff;")

def _edge_px(eid, s, t, val="", ports=(0.5, 1, 0.5, 0), points=None, extra="", color="#4b5563"):
    """ports = (exitX, exitY, entryX, entryY); points = [(x,y), ...] các góc gấp khúc."""
    style = _EBASE + ("strokeColor=%s;" % color) + (_PORT % ports) + extra
    pts = ""
    if points:
        pts = ('<Array as="points">%s</Array>'
               % "".join('<mxPoint x="%d" y="%d"/>' % (round(x), round(y)) for x, y in points))
    return ('<mxCell id="%s" value="%s" style="%s" edge="1" parent="1" source="%s" target="%s">'
            '<mxGeometry relative="1" as="geometry">%s</mxGeometry></mxCell>'
            % (eid, esc(val), style, s, t, pts))

def wrap(name, cells, pw, ph):
    inner = "".join(cells).replace(chr(10), "&#10;")
    return ('<mxfile host="confluence" type="atlas" version="20.8.2"><diagram id="D" name="Page-1">'
            '<mxGraphModel dx="1200" dy="800" grid="1" gridSize="10" page="1" pageScale="1" '
            'pageWidth="%d" pageHeight="%d" math="0" shadow="0"><root>'
            '<mxCell id="0"/><mxCell id="1" parent="0"/>%s</root></mxGraphModel></diagram></mxfile>'
            % (pw, ph, inner))

# ---------- 1) §2 MÔ HÌNH TỔNG QUAN — bố cục VÙNG (zone) trái→phải ----------
# Bám template: Nguồn dữ liệu đầu vào (trái) | Hệ thống lõi (giữa, có bước xử lý + kho dữ liệu)
#              | Cơ chế tích hợp | Giao diện (FE, phải) | Actor (ngoài cùng phải).
_ZONE_COLORS = {
    'src':   ('#f5f5f5', '#999999'),   # nguồn / hệ thống ngoài — xám nhận diện
    'core':  ('#dae8fc', '#6c8ebf'),   # hệ thống lõi — xanh
    'integ': ('#fff2cc', '#d6b656'),   # cơ chế tích hợp — vàng
    'fe':    ('#d5e8d4', '#82b366'),   # giao diện người dùng — xanh lá
    'data':  ('#ffe6cc', '#d79b00'),   # kho dữ liệu trung gian — cam
}

def overview_zones(title, zones, flows=None, actors=None, zw=250, comp_h=46, comp_gap=12):
    """
    zones:  list[(zone_title, kind, [ (id, label) ])]  # trái→phải; kind ∈ src/core/integ/fe/data
    flows:  list[(src_id, dst_id, label)]              # mũi tên cấp cao (id = component id HOẶC 'Z<idx>' cho cả vùng)
    actors: list[(id, label, target_id, edge_label)]   # người que ngoài cùng phải, 1 mũi tên/actor
    Ít mũi tên: mặc định nối 1 mũi tên giữa các vùng liền kề (in→xử lý→out) nếu không truyền flows.
    """
    flows = flows or []
    actors = actors or []
    cells = []
    x = 40
    top = 70
    zone_ids = {}            # idx -> container id
    zone_right = {}          # idx -> right x
    stack_heights = []
    # tính chiều cao đồng đều để canh đỉnh các vùng
    for _, _, comps in zones:
        stack_heights.append(60 + max(1, len(comps)) * (comp_h + comp_gap))
    zone_h = max(stack_heights) if stack_heights else 200
    for zi, (ztitle, kind, comps) in enumerate(zones):
        f, s = _ZONE_COLORS.get(kind, _ZONE_COLORS['core'])
        zid = "Z%d" % zi
        zone_ids[zi] = zid
        cells.append(_cell(zid, ztitle, x, top, zw, zone_h,
            "rounded=0;whiteSpace=wrap;html=1;fillColor=none;strokeColor=%s;strokeWidth=2;"
            "verticalAlign=top;align=center;fontStyle=1;fontSize=12;spacingTop=6;dashed=%d;"
            % (s, 1 if kind == 'src' else 0)))
        cy = top + 40
        for cid, clbl in comps:
            cells.append(_cell(cid, clbl, x + 20, cy, zw - 40, comp_h,
                "rounded=1;whiteSpace=wrap;html=1;fillColor=%s;strokeColor=%s;fontSize=11;" % (f, s)))
            cy += comp_h + comp_gap
        zone_right[zi] = x + zw
        x += zw + 70
    # mũi tên giữa các vùng
    def _resolve(ident):
        if isinstance(ident, str) and ident.startswith("Z") and ident[1:].isdigit():
            return zone_ids.get(int(ident[1:]), ident)
        return ident
    if flows:
        for i, (a, b, lbl) in enumerate(flows):
            cells.append(_edge("zf%d" % i, _resolve(a), _resolve(b), lbl,
                "edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;endArrow=block;strokeColor=#555;fontSize=10;"))
    else:
        for zi in range(len(zones) - 1):
            cells.append(_edge("zf%d" % zi, zone_ids[zi], zone_ids[zi + 1], "",
                "edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;endArrow=block;strokeColor=#555;"))
    # actors ngoài cùng phải
    ax = x
    ay = top + 20
    for aid, albl, tgt, el in actors:
        cells.append(_cell(aid, albl, ax, ay, 60, 84,
            "shape=umlActor;html=1;whiteSpace=wrap;verticalLabelPosition=bottom;verticalAlign=top;"
            "fillColor=#fff2cc;strokeColor=#d6b656;fontSize=11;"))
        if tgt:
            cells.append(_edge("af_%s" % aid, aid, tgt, el,
                "edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;endArrow=block;strokeColor=#777;fontSize=10;"))
        ay += 130
    pw = ax + (140 if actors else 40)
    ph = top + zone_h + 60
    # tiêu đề trên cùng
    cells.insert(0, _cell("TITLE", title, 40, 20, max(pw - 80, 400), 34,
        "text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;fontStyle=1;fontSize=15;"))
    return wrap("overview", cells, pw, ph)

# ---------- 2) §3 QUY TRÌNH — 3 cột (đối tượng | bước | mô tả) ----------
def process_3col(rows, c1x=30, c2x=240, c3x=560, c1w=190, c2w=300, c3w=390):
    """rows: list[(actor, step, desc, kind)] kind in {'proc','dec'}"""
    HDR = "rounded=0;whiteSpace=wrap;html=1;fillColor=#e0e0e0;strokeColor=#666;fontStyle=1;align=center;"
    ACT = "rounded=0;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;"
    STEP = "rounded=1;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;"
    DEC = "rhombus;whiteSpace=wrap;html=1;fillColor=#ffe6cc;strokeColor=#d79b00;"
    DESC = "rounded=0;whiteSpace=wrap;html=1;fillColor=#fff;strokeColor=#999;align=left;spacingLeft=6;fontSize=11;"
    TERM = "ellipse;whiteSpace=wrap;html=1;fillColor=#f8cecc;strokeColor=#b85450;"
    cells = [_cell("h1", "Đối tượng thực hiện", c1x, 20, c1w, 34, HDR),
             _cell("h2", "Bước thực hiện", c2x, 20, c2w, 34, HDR),
             _cell("h3", "Mô tả", c3x, 20, c3w, 34, HDR),
             _cell("start", "BẮT ĐẦU", c2x + c2w // 2 - 55, 70, 110, 40, TERM)]
    prev = "start"; y = 134; gap = 86; sh = 64
    for i, (actor, step, desc, kind) in enumerate(rows):
        ry = y + i * gap; sid = "s%d" % i
        cells.append(_cell("a%d" % i, actor, c1x, ry, c1w, sh, ACT))
        cells.append(_cell(sid, "%d. %s" % (i + 1, step), c2x, ry, c2w, sh, DEC if kind == "dec" else STEP))
        cells.append(_cell("d%d" % i, desc, c3x, ry, c3w, sh, DESC))
        # start/step/end đều canh cùng trục dọc giữa cột 2 -> cạnh thẳng đứng, không waypoint
        cells.append(_edge_px("e%d" % i, prev, sid)); prev = sid
    endy = 70 + 64 + len(rows) * gap
    cells.append(_cell("end", "KẾT THÚC", c2x + c2w // 2 - 55, endy, 110, 40, TERM))
    cells.append(_edge_px("efin", prev, "end"))
    return wrap("process", cells, c3x + c3w + 40, endy + 80)

# ---------- 3) §4 ERD bảng lưới ----------
def erd(entities, rels, dom_color=None, collapsed=False):
    """
    entities: dict name -> (domain, [ (field,type,key,note) ])  # key in PK/FK/UK/'' ; note optional
    rels: list[(src,dst,label)]
    dom_color: dict domain -> (fill,stroke)  header màu theo miền
    collapsed: True -> chỉ render field có key PK/FK (ẩn field thường, không cộng chiều
               cao cho field bị ẩn) — dùng cho Tầng A cross-store overview.
    """
    dom_color = dom_color or {}
    C1, C2, C3 = 64, 152, 120; W = C1 + C2 + C3; HDR = 26; RH = 24
    cells = []
    def note3(k, note): return k if k else (note or "")
    names = list(entities.keys()); ncol = 5
    colx = [40 + i * (W + 60) for i in range(ncol)]
    cur = [40] * ncol
    hdr_ids = {}
    for idx, name in enumerate(names):
        col = idx % ncol; x = colx[col]; y = cur[col]
        dom, fields = entities[name]
        fill, stroke = dom_color.get(dom, ("#dae8fc", "#6c8ebf"))
        cells.append(_cell("h_" + name, name, x, y, W, HDR, "rounded=0;whiteSpace=wrap;html=1;fillColor=%s;strokeColor=%s;fontStyle=1;fontSize=11;align=center;" % (fill, stroke)))
        hdr_ids[name] = "h_" + name
        shown = [f for f in fields if not collapsed or f[2] in ("PK", "FK")]
        for i, f in enumerate(shown):
            field, typ, key = f[0], f[1], f[2]; note = f[3] if len(f) > 3 else ""
            ry = y + HDR + i * RH
            cells.append(_cell("%s_t%d" % (name, i), typ, x, ry, C1, RH, "rounded=0;whiteSpace=wrap;html=1;fillColor=#fafafa;strokeColor=#b3b3b3;fontSize=10;align=left;spacingLeft=4;fontStyle=2;"))
            cells.append(_cell("%s_n%d" % (name, i), field, x + C1, ry, C2, RH, "rounded=0;whiteSpace=wrap;html=1;fillColor=#fff;strokeColor=#b3b3b3;fontSize=10;align=left;spacingLeft=4;overflow=hidden;"))
            cells.append(_cell("%s_k%d" % (name, i), note3(key, note), x + C1 + C2, ry, C3, RH, "rounded=0;whiteSpace=wrap;html=1;fillColor=#fff;strokeColor=#b3b3b3;fontSize=9;align=left;spacingLeft=4;"))
        cur[col] = y + HDR + len(shown) * RH + 40
    for i, (a, b, lbl) in enumerate(rels):
        cells.append(_edge("r%d" % i, hdr_ids[a], hdr_ids[b], lbl or "1 : N",
            "edgeStyle=entityRelationEdgeStyle;html=1;rounded=1;endArrow=ERmany;startArrow=ERone;fontSize=9;strokeColor=#888;"))
    return wrap("erd", cells, max(colx) + W + 40, max(cur) + 40)

# ---------- 3b) §4 ERD MỨC BẢNG — bố cục phân tầng + định tuyến theo kênh ----------
def erd_graph(entities, rels, dom_color=None, node_w=210, base_h=40, max_cols=6):
    """
    ERD mức bảng (hộp = tên bảng, không lưới field) — dùng khi cần thể hiện QUAN HỆ.

    entities: dict name -> (domain, [ (field,type,key,note), ... ])   # tương thích erd()
              field rỗng  -> hộp chỉ có tên bảng;
              có field    -> thêm 1 dòng nhỏ liệt kê khoá PK/FK dưới tên.
    rels:     list[(src, dst, label)]

    Vì sao không dùng erd(): erd() xếp bảng theo lưới cố định rồi để draw.io tự định tuyến
    (entityRelationEdgeStyle). Với vài chục quan hệ thì đường nối chạy chéo, CẮT XUYÊN các hộp
    khác và nhãn đè lên nhau. Hàm này:
      1. xếp bảng thành TẦNG theo khoảng cách tới bảng trung tâm (BFS), thứ tự trong tầng tinh
         chỉnh bằng barycenter để giảm số lần cắt nhau;
      2. định tuyến trực giao tường minh: đoạn NGANG chỉ chạy trong KÊNH giữa hai tầng, đoạn DỌC
         chỉ chạy trong MÁNG giữa hai cột. Cả hai vùng đều không có hộp nào -> cạnh KHÔNG BAO GIỜ
         cắt qua hộp. Mỗi đoạn chiếm một làn riêng nên không có hai cạnh nào đè nhau.
    """
    dom_color = dom_color or {}
    names = list(entities.keys())
    if not names:
        return wrap("erd", [], 400, 200)
    idx = {n: i for i, n in enumerate(names)}
    rels = [(a, b, l) for (a, b, l) in rels if a in idx and b in idx and a != b]

    # --- 1) phân tầng: BFS từ đỉnh bậc cao nhất của từng thành phần liên thông ---
    adj = {n: set() for n in names}
    for a, b, _ in rels:
        adj[a].add(b); adj[b].add(a)
    layer, slot_of, seen = {}, {}, set()
    row_base = 0
    # Bảng đứng một mình (không quan hệ) gom chung vào các hàng cuối — để mỗi bảng một hàng
    # riêng thì sơ đồ dài lê thê toàn khoảng trắng.
    lonely = [n for n in names if not adj[n]]
    seen.update(lonely)
    for root in sorted(names, key=lambda n: (-len(adj[n]), idx[n])):
        if root in seen:
            continue
        comp, frontier, d = [], [root], 0
        seen.add(root)
        while frontier:
            for n in frontier:
                layer[n] = d
                comp.append(n)
            nxt = []
            for n in frontier:
                for m in sorted(adj[n], key=lambda x: idx[x]):
                    if m not in seen:
                        seen.add(m); nxt.append(m)
            frontier, d = nxt, d + 1
        # thứ tự trong tầng: barycenter vài lượt cho bớt cắt nhau
        rows = {}
        for n in comp:
            rows.setdefault(layer[n], []).append(n)
        pos = {n: i for lv in rows for i, n in enumerate(rows[lv])}
        for _ in range(4):
            for lv in sorted(rows):
                def bary(n):
                    nb = [pos[m] for m in adj[n] if m in pos and layer[m] != lv]
                    return sum(nb) / float(len(nb)) if nb else pos[n]
                rows[lv].sort(key=lambda n: (bary(n), idx[n]))
                for i, n in enumerate(rows[lv]):
                    pos[n] = i
        # Tầng quá rộng -> cắt thành nhiều HÀNG liên tiếp (≤ max_cols cột). Giữ được tính cục bộ
        # của BFS mà vẫn bó chiều ngang: trang quá rộng thì Confluence thu nhỏ, chữ không đọc nổi.
        band = []
        for lv in sorted(rows):
            seq = rows[lv]
            for k in range(0, len(seq), max_cols):
                band.append(seq[k:k + max_cols])
        width = max(len(r) for r in band)
        # Thành phần liên thông xếp CHỒNG theo chiều dọc (không xếp cạnh nhau): xếp ngang thì
        # bề rộng trang cộng dồn theo số thành phần và vượt xa ngưỡng đọc được.
        for r_i, r in enumerate(band):
            off = (width - len(r)) // 2                       # canh giữa theo bước slot nguyên
            for i, n in enumerate(r):
                slot_of[n] = off + i
                layer[n] = row_base + r_i
        row_base += len(band)

    for k in range(0, len(lonely), max_cols):
        chunk = lonely[k:k + max_cols]
        for i, n in enumerate(chunk):
            slot_of[n] = i
            layer[n] = row_base
        row_base += 1

    nlayer = max(layer.values()) + 1
    nslot = max(slot_of.values()) + 1

    # --- 2) kênh/máng mỗi cạnh sẽ dùng (kênh c nằm giữa tầng c và c+1; c = -1 là kênh trên cùng) ---
    plan = []
    gut_load = {}
    for i, (a, b, lbl) in enumerate(rels):
        la, lb, sa, sb = layer[a], layer[b], slot_of[a], slot_of[b]
        if la == lb:
            ch1 = ch2 = la; side_a = side_b = "B"
        elif la < lb:
            ch1, ch2, side_a, side_b = la, lb - 1, "B", "T"
        else:
            ch1, ch2, side_a, side_b = la - 1, lb, "T", "B"
        gut = None
        if ch1 != ch2:
            # Rải cạnh dài ra nhiều máng: dồn hết vào máng cạnh bảng đích thì máng đó phình ra
            # hàng chục làn và kéo cả trang rộng gấp đôi. Chọn máng ÍT TẢI NHẤT trong khoảng
            # giữa hai cột, ưu tiên gần đích khi tải bằng nhau.
            near = sb if sa < sb else sb + 1
            cands = range(min(sa, sb), max(sa, sb) + 2)
            gut = min(cands, key=lambda g: (gut_load.get(g, 0), abs(g - near)))
            gut_load[gut] = gut_load.get(gut, 0) + 1
        plan.append(dict(i=i, a=a, b=b, lbl=lbl, ch1=ch1, ch2=ch2, gut=gut,
                         sa=sa, sb=sb, sida=side_a, sidb=side_b))

    H_LANE, V_LANE = 13, 13
    ch_edges, gut_edges = {}, {}
    for p in plan:
        ch_edges.setdefault(p["ch1"], []).append(p["i"])
        if p["ch2"] != p["ch1"]:
            ch_edges.setdefault(p["ch2"], []).append(p["i"])
        if p["gut"] is not None:
            gut_edges.setdefault(p["gut"], []).append(p["i"])
    # Giãn hàng BIẾN THIÊN theo số làn thực có của từng kênh (không lấy chung một giá trị lớn
    # nhất): hàng không có cạnh nào chạy qua thì khít lại, sơ đồ bớt khoảng trắng.
    def gap_of(c):
        return max(52, 30 + len(ch_edges.get(c, [])) * H_LANE)
    gutw = max(80, 24 + max([len(v) for v in gut_edges.values()] or [0]) * V_LANE)

    # --- 3) hình học ---
    MARGIN = 40
    TOP = 60 + (gap_of(-1) if -1 in ch_edges else 0)
    SW = node_w + gutw
    heights = {}
    for n in names:
        keys = [f[0] for f in entities[n][1] if len(f) > 2 and f[2] in ("PK", "FK")]
        heights[n] = base_h + (16 if keys else 0)
    row_h = max(heights.values())
    _rt = [TOP]
    for lv in range(1, nlayer):
        _rt.append(_rt[-1] + row_h + gap_of(lv - 1))
    def nx_(n): return MARGIN + slot_of[n] * SW
    def row_top(lv): return _rt[lv]
    def row_bot(lv): return _rt[lv] + row_h
    def ny_(n): return row_top(layer[n])
    def chan_y0(c): return row_bot(c) if c >= 0 else TOP - gap_of(-1)
    def gut_x0(g): return MARGIN + g * SW - gutw          # mép trái của máng trước slot g

    lane_ch, lane_gut = {}, {}
    for c, ids in ch_edges.items():
        for k, i in enumerate(sorted(ids)):
            lane_ch[(c, i)] = chan_y0(c) + 16 + k * H_LANE
    for g, ids in gut_edges.items():
        for k, i in enumerate(sorted(ids)):
            lane_gut[(g, i)] = gut_x0(g) + 12 + k * V_LANE

    # Cổng trên/dưới: cấp theo (CỘT, KÊNH) chứ không theo từng hộp. Hai đoạn nối cùng chạy trong
    # một kênh ở cùng một cột — một đi xuống từ hộp trên, một đi lên vào hộp dưới — dùng chung
    # dải x của cột đó; nếu cấp cổng theo hộp thì cả hai rơi vào cùng toạ độ x và ĐÈ LÊN NHAU.
    ports = {}
    grp = {}
    for p in plan:
        grp.setdefault((p["sa"], p["ch1"]), []).append((p["i"], p["a"], p["sida"], p["sb"]))
        grp.setdefault((p["sb"], p["ch2"]), []).append((p["i"], p["b"], p["sidb"], p["sa"]))
    for key, items in grp.items():
        items.sort(key=lambda t: (t[3], t[0]))               # xếp theo cột của đầu kia
        for k, (i, n, side, _) in enumerate(items):
            ports[(i, n, side)] = (k + 1) / float(len(items) + 1)

    # --- 4) dựng cell ---
    cells = []
    for n in names:
        dom = entities[n][0]
        fill, stroke = dom_color.get(dom, ("#dae8fc", "#6c8ebf"))
        keys = [f[0] for f in entities[n][1] if len(f) > 2 and f[2] in ("PK", "FK")]
        val = label(n, " · ".join(keys[:3])) if keys else n
        cells.append(_cell("t_" + str(idx[n]), val, nx_(n), ny_(n), node_w, heights[n],
                           "rounded=0;whiteSpace=wrap;html=1;fillColor=%s;strokeColor=%s;"
                           "fontSize=11;fontStyle=1;verticalAlign=middle;" % (fill, stroke)))
    for p in plan:
        a, b, i = p["a"], p["b"], p["i"]
        fa, fb = ports[(i, a, p["sida"])], ports[(i, b, p["sidb"])]
        ax, bx = nx_(a) + node_w * fa, nx_(b) + node_w * fb
        ay = row_bot(layer[a]) if p["sida"] == "B" else row_top(layer[a])
        by = row_bot(layer[b]) if p["sidb"] == "B" else row_top(layer[b])
        y1 = lane_ch[(p["ch1"], i)]
        pts = [(ax, y1)]
        if p["gut"] is not None:
            gx = lane_gut[(p["gut"], i)]
            y2 = lane_ch[(p["ch2"], i)]
            pts += [(gx, y1), (gx, y2), (bx, y2)]
        else:
            pts += [(bx, y1)]
        ey = 1.0 if p["sida"] == "B" else 0.0
        ny = 1.0 if p["sidb"] == "B" else 0.0
        cells.append(_edge_px("er%d" % i, "t_" + str(idx[a]), "t_" + str(idx[b]), p["lbl"],
                              (round(fa, 4), ey, round(fb, 4), ny), pts, color="#7a8794",
                              extra="startArrow=ERone;startFill=0;endArrow=ERmany;endFill=0;fontColor=#5a6673;"))
    pw = MARGIN + nslot * SW + 40
    ph = row_top(nlayer - 1) + row_h + gap_of(nlayer - 1) + 20
    return wrap("erd", cells, pw, ph)

# ---------- 4) §6 CÂY PHÂN RÃ ----------
def breakdown_tree(root, groups, gw=340, leaf_h=46, leaf_gap=10):
    """
    groups: list[(group_label, style_key, [leaf_label,...])]  style_key in {'fe','bc','bi','grey'}

    Routing (bracket kiểu sơ đồ tổ chức — không để mũi tên chồng nhau):
      - root -> nhóm: xuống 1 BUS ngang chung, rẽ ngang tới trục nhóm, rồi xuống đỉnh nhóm.
        Mỗi nhóm có đoạn xuống riêng nên đầu mũi tên tách bạch.
      - nhóm -> lá: một TRỤC DỌC duy nhất bên trái cụm, mỗi lá nhận 1 nhánh ngang riêng vào
        cạnh TRÁI của lá. Không có cạnh nào cắt qua hộp phía trên (lỗi cũ: mọi cạnh đều
        đi từ đáy nhóm xuống đỉnh lá theo cùng một đường thẳng).
    """
    ST = {"fe": ("#d5e8d4", "#82b366", "#f3fbef"), "bc": ("#dae8fc", "#6c8ebf", "#f2f7fe"),
          "bi": ("#ffe6cc", "#d79b00", "#fff8ef"), "grey": ("#eee", "#999", "#f7f7f7")}
    COL = gw + 40                      # bước cột giữa 2 cụm
    ROOT_Y, ROOT_H, ROOT_W = 14, 50, 320
    GRP_Y, GRP_H = 116, 46
    BUS_Y = 92                         # bus ngang root -> các nhóm
    SPINE_DX = 16                      # trục dọc nhóm -> lá, tính từ mép trái cụm
    LEAF_DX = 40                       # thụt lá vào trong
    span = max(1, len(groups)) * COL - 40
    root_x = 40 + span // 2 - ROOT_W // 2
    root_cx = root_x + ROOT_W // 2
    cells = [_cell("root", root, root_x, ROOT_Y, ROOT_W, ROOT_H,
                   "rounded=1;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#666;fontStyle=1;")]
    maxy = 0
    for gi, (glabel, sk, leaves) in enumerate(groups):
        cf, cs, lf = ST.get(sk, ST["bc"])
        x = 40 + gi * COL
        gcx = x + gw // 2
        cells.append(_cell("g%d" % gi, glabel, x, GRP_Y, gw, GRP_H,
                           "rounded=0;whiteSpace=wrap;html=1;fillColor=%s;strokeColor=%s;fontStyle=1;" % (cf, cs)))
        # root -> nhóm: thẳng nếu cùng trục, ngược lại gấp khúc qua bus chung
        pts = None if abs(gcx - root_cx) < 2 else [(root_cx, BUS_Y), (gcx, BUS_Y)]
        cells.append(_edge_px("eg%d" % gi, "root", "g%d" % gi, "", (0.5, 1, 0.5, 0), pts, color="#666666"))
        spine_x = x + SPINE_DX
        exit_x = round(SPINE_DX / float(gw), 4)      # cho trục dọc trùng mép ra của hộp nhóm
        y = GRP_Y + GRP_H + 34
        for li, leaf in enumerate(leaves):
            lid = "l%d_%d" % (gi, li)
            cells.append(_cell(lid, leaf, x + LEAF_DX, y, gw - LEAF_DX, leaf_h,
                               "rounded=1;whiteSpace=wrap;html=1;fillColor=%s;strokeColor=%s;fontSize=11;align=left;spacingLeft=8;" % (lf, cs)))
            cells.append(_edge_px("el%d_%d" % (gi, li), "g%d" % gi, lid, "",
                                  (exit_x, 1, 0, 0.5), [(spine_x, y + leaf_h // 2)], color=cs))
            y += leaf_h + leaf_gap
        maxy = max(maxy, y)
    return wrap("tree", cells, 40 + max(1, len(groups)) * COL + 40, maxy + 40)

# ---------- 5) §5 STATE DIAGRAM ----------
_BACK_CLR, _END_CLR = "#2563eb", "#c0392b"

def state_diagram(states, transitions, node_w=210, node_h=48, vgap=46):
    """
    states: list[label] xếp dọc theo trục chính; transitions: list[(from_idx,to_idx,label)]
    với idx theo states, -1 = 'bắt đầu', -2 = 'kết thúc'.

    Routing (edgeStyle=none + port + waypoint — không để mũi tên chồng nhau):
      - chuyển trạng thái liền kề  -> thẳng đứng trên trục chính;
      - nhảy tiến (bỏ qua ≥1 trạng thái) và cạnh vào 'kết thúc' -> RAIL bên PHẢI;
      - quay lui / tự lặp          -> RAIL bên TRÁI, nét đứt (phân biệt luồng nghịch);
      mỗi cạnh rail chiếm MỘT LÀN riêng (làn gần hộp nhất dành cho bước nhảy ngắn nhất),
      và mỗi điểm nối vào hộp chiếm MỘT SLOT riêng theo chiều cao hộp — nếu để chung
      một độ cao thì hai đoạn ngang (một đi ra, một đi vào) đè lên nhau ngay sát mép hộp.
    """
    n = len(states)
    TERM_W, TERM_H = 130, 38

    def row(ix):                       # -1 = start (trên cùng), -2 = end (dưới cùng)
        return -1 if ix == -1 else (n if ix == -2 else ix)

    # phân loại cạnh + cấp làn rail
    kinds = []
    for a, b, lbl in transitions:
        ra, rb = row(a), row(b)
        k = "straight" if rb == ra + 1 else ("self" if rb == ra else ("fwd" if rb > ra else "back"))
        kinds.append((k, ra, rb, lbl))
    right_ix = [i for i, (k, _, _, _) in enumerate(kinds) if k in ("fwd", "self")]
    left_ix = [i for i, (k, _, _, _) in enumerate(kinds) if k == "back"]
    right_ix.sort(key=lambda i: abs(kinds[i][2] - kinds[i][1]))
    left_ix.sort(key=lambda i: abs(kinds[i][2] - kinds[i][1]))
    lane = {}
    for j, i in enumerate(right_ix): lane[i] = j
    for j, i in enumerate(left_ix): lane[i] = j
    nL, nR = len(left_ix), len(right_ix)

    RAIL_0, RAIL_D = 34, 38
    node_x = 40 if not nL else (30 + RAIL_0 + (nL - 1) * RAIL_D)
    node_r = node_x + node_w
    spine_cx = node_x + node_w // 2

    # ---- cấp SLOT cổng: mỗi điểm nối trên một cạnh hộp có độ cao riêng ----
    # Không làm bước này thì đoạn ngang của cạnh ĐI RA và cạnh ĐI VÀO cùng một hộp nằm
    # đúng một độ cao -> hai mũi tên đè lên nhau sát mép hộp (preview.py bắt được).
    def rail_of(i):
        return (node_x - RAIL_0 - lane[i] * RAIL_D) if kinds[i][0] == "back" \
            else (node_r + RAIL_0 + lane[i] * RAIL_D)

    req = {}                            # (hàng, phía) -> [(khoảng cách rail, edge_idx, vai trò)]
    for i, (k, ra, rb, _) in enumerate(kinds):
        if k == "straight":
            continue
        side = "L" if k == "back" else "R"
        d = abs(rail_of(i) - (node_x if side == "L" else node_r))
        req.setdefault((ra, side), []).append((d, i, "src"))
        req.setdefault((rb, side), []).append((d, i, "dst"))
    slot = {}                           # (edge_idx, vai trò) -> tỉ lệ y trên chiều cao hộp
    for key in req:
        items = sorted(req[key])
        for j, (_, i, role) in enumerate(items):
            slot[(i, role)] = (j + 1) / float(len(items) + 1)
    # nhiều cổng trên một cạnh hộp -> nới cao hộp để 2 slot cách nhau ≥ 16px
    max_slots = max([len(v) for v in req.values()] or [0])
    node_h = max(node_h, 16 * max_slots)
    STEP = node_h + vgap

    cells = [_cell("start", "Bắt đầu", spine_cx - TERM_W // 2, 20, TERM_W, TERM_H,
                   "ellipse;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#6aa84f;fontStyle=1;")]
    y0 = 20 + TERM_H + vgap
    ids = {-1: "start"}
    for i, s in enumerate(states):
        cells.append(_cell("s%d" % i, s, node_x, y0 + i * STEP, node_w, node_h,
                           "rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;arcSize=12;"))
        ids[i] = "s%d" % i
    y_end = y0 + n * STEP
    cells.append(_cell("end", "Kết thúc", spine_cx - TERM_W // 2, y_end, TERM_W, TERM_H,
                       "ellipse;whiteSpace=wrap;html=1;fillColor=#f8cecc;strokeColor=#b85450;fontStyle=1;"))
    ids[n] = "end"; ids[-2] = "end"

    def geom(r):                       # (top_y, height, left_x, right_x) của 1 hàng
        if r == -1: return 20, TERM_H, spine_cx - TERM_W // 2, spine_cx + TERM_W // 2
        if r == n:  return y_end, TERM_H, spine_cx - TERM_W // 2, spine_cx + TERM_W // 2
        return y0 + r * STEP, node_h, node_x, node_r

    for i, (k, ra, rb, lbl) in enumerate(kinds):
        sid, tid = ids[ra], ids[rb]
        ty_s, h_s, _, _ = geom(ra)
        ty_t, h_t, _, _ = geom(rb)
        if k == "straight":
            cells.append(_edge_px("t%d" % i, sid, tid, lbl, (0.5, 1, 0.5, 0)))
            continue
        fy_s, fy_t = slot[(i, "src")], slot[(i, "dst")]
        ay_s, ay_t = ty_s + h_s * fy_s, ty_t + h_t * fy_t
        rail = rail_of(i)
        if k == "back" or k == "self":
            side = 0 if k == "back" else 1
            cells.append(_edge_px("t%d" % i, sid, tid, lbl, (side, fy_s, side, fy_t),
                                  [(rail, ay_s), (rail, ay_t)], color=_BACK_CLR,
                                  extra="dashed=1;dashPattern=7 4;fontColor=%s;" % _BACK_CLR))
        else:                          # fwd — nhảy tiến / vào Kết thúc
            clr = _END_CLR if rb == n else "#4b5563"
            cells.append(_edge_px("t%d" % i, sid, tid, lbl, (1, fy_s, 1, fy_t),
                                  [(rail, ay_s), (rail, ay_t)], color=clr,
                                  extra=("fontColor=%s;" % clr) if rb == n else ""))

    pw = (node_r + RAIL_0 + max(0, nR - 1) * RAIL_D + 60) if nR else node_r + 40
    return wrap("state", cells, pw, y_end + TERM_H + 40)

if __name__ == "__main__":
    # smoke test: chỉ in độ dài (tránh lỗi encoding console Windows khi in tiếng Việt)
    ov = overview_zones("Hệ thống X", [
        ("Nguồn dữ liệu đầu vào", "src", [("n1", "NAPAS"), ("n2", "Bank/Đối tác")]),
        ("Hệ thống lõi", "core", [("c1", "Thu thập"), ("c2", "Đối soát"), ("c3", "Gửi kết quả")]),
        ("Giao diện (FE)", "fe", [("f1", "Màn hình vận hành")]),
    ], actors=[("ac1", "Nhân viên đối soát", "f1", "thao tác")])
    pr = process_3col([("A", "step1", "desc1", "proc"), ("B", "step2", "desc2", "dec")])
    print("overview_zones bytes:", len(ov), "| process_3col bytes:", len(pr))
