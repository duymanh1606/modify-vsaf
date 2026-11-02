// =============================================================================
// build-activity-diagram.mjs — single-source-of-truth activity-diagram generator
// =============================================================================
// One node model  ->  BOTH (a) an editable draw.io mxfile  and  (b) a matching PNG
// (rendered by headless Chrome from an SVG built with the SAME coordinates, so the
// PNG faithfully represents the mxfile without needing draw.io installed).
//
// Why: §2.1 of the "Template API/tiến trình nghiệp vụ" is an ACTIVITY diagram drawn
// in draw.io. The draw.io macro live-renders the mxfile via mxGraph (the mxfile is
// the source of truth for display). We ALSO attach a clean PNG export (named
// "<base>.png", comment "<base> exported to image") as a STATIC fallback preview —
// used for PDF/email export or when the viewer's JS is off — plus the mxfile
// (label "drawio") for editability. The PNG is best-effort, NOT required for the
// live macro to display. (See references/confluence-server-publish.md §3: the real
// cause of any "diagram not updating" is the macro `revision` vs attachment version,
// NOT a license watermark — that old theory was refuted.)
//
// Usage:
//   node build-activity-diagram.mjs <model.json> <out_dir> <base_name>
//   e.g. node build-activity-diagram.mjs BE-RP-17-activity.model.json ./ BE-RP-17-activity-flow
//   -> writes  <out_dir>/<base_name>        (mxfile, no extension = draw.io diagramName)
//              <out_dir>/<base_name>.png     (clean export, 2x)
// Chrome: set env CHROME_PATH, else common Windows/Chrome/Edge paths are tried.
//
// Exit code CONTRACT: 0 = wrote mxfile + <base>.png (static fallback preview).
//                     2 = wrote mxfile ONLY (Chrome not found, Chrome errored, or
//                         PNG missing) —
//                         caller MUST still publish the mxfile + drawio macro. The
//                         macro live-renders fine without the PNG; only the static
//                         export fallback is absent. Do NOT hard-stop for a missing PNG.
//
// model.json shape:
// {
//   "title": "BE-RP-17 — Biểu đồ activity ...",
//   "canvasW": 1000, "canvasH": 2470,          // SVG/mxfile page size
//   "colors": { ...optional overrides per type... },
//   "endRail": 1050,                            // optional x of the far-right "-> Kết thúc" bus
//   "nodes": [ { "id":"a1", "type":"action|decision|term|bar|group|lane|outcome|abort",
//                "x":170,"y":96,"w":340,"h":66, "t":"label text" }, ... ],
//   "edges": [ { "f":"a1", "t":"d1", "k":"v|R|L|join|end|loopL|loopR", "l":"Có", "rail":150 }, ... ]
// }
//   type:  action(rounded) decision(rhombus) term(ellipse) bar(loop label)
//          group(dashed loop container, drawn BEHIND — label top-left)
//          lane(SWIMLANE column: header band + body, drawn BEHIND everything — one
//               per actor/system; nodes sit inside it purely by their own x/y)
//          outcome(green side box) abort(red side box)
//   edge k: v     = bottom->top; STRAIGHT when both nodes share centre-x, and
//                   auto-jogs (down / across / down) when they sit in different lanes
//           R     = right elbow to a side node (target on the RIGHT)
//           L     = left elbow to a side node (target on the LEFT — mirror of R)
//           join  = side box bottom -> back to a main node's right edge
//           end   = side node right -> far-right bus (endRail) -> into the End node
//           loopL = back-edge: source left -> left rail (edge.rail) -> up -> target left  (dashed blue)
//           loopR = back-edge: source left -> mid rail -> up -> target right             (dashed blue)
//                   rail MUST be to the RIGHT of the target's right edge, otherwise the
//                   last segment cuts straight through the target box.
// =============================================================================
import { writeFileSync, readFileSync, existsSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';

const [modelPath, outDir, base] = process.argv.slice(2);
if (!modelPath || !outDir || !base) {
  console.error('usage: node build-activity-diagram.mjs <model.json> <out_dir> <base_name>');
  process.exit(1);
}
const model = JSON.parse(readFileSync(modelPath, 'utf8'));
const CANVAS_W = model.canvasW ?? 1000;
const CANVAS_H = model.canvasH ?? 2000;
const N = model.nodes ?? [];
const E = model.edges ?? [];
const clr = Object.assign({
  action:  { fill: '#e6f2f2', stroke: '#0b6b6b' },
  decision:{ fill: '#fff2cc', stroke: '#d6b656' },
  term:    { fill: '#d5e8d4', stroke: '#6aa84f' },
  bar:     { fill: '#dae8fc', stroke: '#6c8ebf' },
  group:   { fill: 'rgba(37,99,235,0.045)', stroke: '#6c8ebf' },
  lane:    { fill: '#ffffff', stroke: '#9aa5b1', head: '#eef2f7', headText: '#33495e' },
  outcome: { fill: '#e8f5e9', stroke: '#4b8a4f' },
  abort:   { fill: '#f8d7da', stroke: '#c0392b' },
}, model.colors ?? {});
const END_RAIL = model.endRail ?? (CANVAS_W - 30);
const LOOP_CLR = '#2563eb', END_CLR = '#c0392b';

const byId = Object.fromEntries(N.map(n => [n.id, n]));
const cx = n => n.x + n.w/2, cy = n => n.y + n.h/2;

// ---- Lane sanity check (drawing convention 7) --------------------------------
// Swimlanes must share their borders: lane[i].x + lane[i].w === lane[i+1].x, all at
// the same y/h. A few pixels of gap makes the published page read as several loose
// rectangles instead of one swimlane block (real case SCR-COMPOSE 2026-08-07 — the
// reviewer rejected it). Warn only: never block generating, the author decides.
function checkLanes() {
  const lanes = N.filter(n => n.type === 'lane').sort((a, b) => a.x - b.x);
  if (lanes.length < 2) return;
  const warn = m => console.warn('LANE WARN: ' + m);
  for (let i = 0; i < lanes.length - 1; i++) {
    const a = lanes[i], b = lanes[i + 1];
    const delta = b.x - (a.x + a.w);
    if (delta > 0) warn(`hở ${delta}px giữa lane "${a.t}" (hết ${a.x + a.w}) và "${b.t}" (bắt đầu ${b.x}) — đặt w của lane trước = ${b.x - a.x}`);
    if (delta < 0) warn(`lane "${a.t}" chồng ${-delta}px lên "${b.t}"`);
  }
  const { y, h } = lanes[0];
  for (const l of lanes.slice(1)) {
    if (l.y !== y || l.h !== h) warn(`lane "${l.t}" lệch dọc (y=${l.y} h=${l.h}) so với lane đầu (y=${y} h=${h})`);
  }
  const spanL = lanes[0].x, spanR = lanes[lanes.length - 1].x + lanes[lanes.length - 1].w;
  for (const n of N) {
    if (n.type === 'lane' || n.type === 'group') continue;
    const host = lanes.filter(l => n.x >= l.x && n.x + n.w <= l.x + l.w);
    if (host.length !== 1) {
      const where = n.x + n.w <= spanL || n.x >= spanR ? 'nằm ngoài dải lane' : 'vắt qua biên lane';
      warn(`node "${n.id}" (x=${n.x}..${n.x + n.w}) ${where} — nới w của lane chứa nó, đừng để hộp tràn sang lane khác`);
    }
  }
  // Every drawn line must stay INSIDE the lane band: a bus running in the page margin
  // looks like it fell out of the diagram (real case SCR-COMPOSE 2026-08-07 — the
  // reviewer asked to widen the lanes so they enclose the buses).
  const last = lanes[lanes.length - 1], first = lanes[0];
  if (!(last.x < END_RAIL && END_RAIL < spanR))
    warn(`endRail=${END_RAIL} nằm ngoài lane cuối "${last.t}" (${last.x}..${spanR}) — nới w của lane cuối để bao bus Kết thúc, đừng để bus chạy ở lề trang`);
  for (const e of E) {
    if ((e.k !== 'loopL' && e.k !== 'loopR') || e.rail == null) continue;
    if (e.rail <= spanL || e.rail >= spanR)
      warn(`rail=${e.rail} của edge ${e.k} ${e.f}->${e.t} nằm ngoài dải lane (${spanL}..${spanR}) — nới lane để bao bus vòng lặp`);
    else if (e.k === 'loopL' && e.rail <= first.x)
      warn(`rail=${e.rail} của edge loopL ${e.f}->${e.t} nằm ngoài lane đầu "${first.t}" (${first.x}..${first.x + first.w})`);
  }
}
checkLanes();

const bottom = n => ({ x: cx(n), y: n.y + n.h });
const top    = n => ({ x: cx(n), y: n.y });
const left   = n => ({ x: n.x, y: cy(n) });
const right  = n => ({ x: n.x + n.w, y: cy(n) });

// ---- (A) SVG / HTML ----
const esc = s => String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
const LANE_HEAD = 40;                       // height of a lane's title band
function laneSVG(n) {
  const c = clr.lane;
  return `<rect x="${n.x}" y="${n.y}" width="${n.w}" height="${n.h}" fill="${c.fill}" stroke="${c.stroke}" stroke-width="1.6"/>`+
    `<rect x="${n.x}" y="${n.y}" width="${n.w}" height="${LANE_HEAD}" fill="${c.head}" stroke="${c.stroke}" stroke-width="1.6"/>`+
    `<foreignObject x="${n.x+6}" y="${n.y+2}" width="${n.w-12}" height="${LANE_HEAD-4}">`+
    `<div xmlns="http://www.w3.org/1999/xhtml" class="lanelbl">${esc(n.t)}</div></foreignObject>`;
}
function groupSVG(n) {
  const c = clr.group;
  return `<rect x="${n.x}" y="${n.y}" width="${n.w}" height="${n.h}" rx="14" ry="14" fill="${c.fill}" stroke="${c.stroke}" stroke-width="1.6" stroke-dasharray="8 5"/>`+
    `<foreignObject x="${n.x+10}" y="${n.y+5}" width="${n.w-20}" height="30"><div xmlns="http://www.w3.org/1999/xhtml" class="glbl">${esc(n.t)}</div></foreignObject>`;
}
function shapeSVG(n) {
  const c = clr[n.type] || clr.action;
  const fo = `<foreignObject x="${n.x}" y="${n.y}" width="${n.w}" height="${n.h}">`+
    `<div xmlns="http://www.w3.org/1999/xhtml" class="lbl ${n.type}">${esc(n.t)}</div></foreignObject>`;
  if (n.type === 'term')
    return `<ellipse cx="${cx(n)}" cy="${cy(n)}" rx="${n.w/2}" ry="${n.h/2}" fill="${c.fill}" stroke="${c.stroke}" stroke-width="2"/>${fo}`;
  if (n.type === 'decision') {
    const pts = `${cx(n)},${n.y} ${n.x+n.w},${cy(n)} ${cx(n)},${n.y+n.h} ${n.x},${cy(n)}`;
    return `<polygon points="${pts}" fill="${c.fill}" stroke="${c.stroke}" stroke-width="2"/>${fo}`;
  }
  const rx = n.type === 'bar' ? 4 : 10;
  return `<rect x="${n.x}" y="${n.y}" width="${n.w}" height="${n.h}" rx="${rx}" ry="${rx}" fill="${c.fill}" stroke="${c.stroke}" stroke-width="2"/>${fo}`;
}
function edgeSVG(e) {
  const f = byId[e.f], t = byId[e.t];
  let d, lx = 0, ly = 0, stroke = '#4b5563', marker = 'arw', dash = '';
  if (e.k === 'R') {
    const p = right(f), q = left(t), midx = (p.x + q.x)/2;
    d = `M ${p.x} ${p.y} L ${midx} ${p.y} L ${midx} ${q.y} L ${q.x} ${q.y}`; lx = p.x + 6; ly = p.y - 8;
  } else if (e.k === 'L') {
    const p = left(f), q = right(t), midx = (p.x + q.x)/2;
    // label anchored just RIGHT of the target box (the arrow runs leftwards), so it
    // never slides under the source box sitting at the right end of the segment.
    d = `M ${p.x} ${p.y} L ${midx} ${p.y} L ${midx} ${q.y} L ${q.x} ${q.y}`; lx = q.x + 6; ly = q.y - 8;
  } else if (e.k === 'join') {
    const p = bottom(f), q = right(t);
    d = `M ${p.x} ${p.y} L ${p.x} ${q.y} L ${q.x} ${q.y}`;
  } else if (e.k === 'end') {
    const p = right(f), q = right(t);   // into End node's right edge via the far-right bus
    d = `M ${p.x} ${p.y} L ${END_RAIL} ${p.y} L ${END_RAIL} ${q.y} L ${q.x} ${q.y}`;
    stroke = END_CLR; marker = 'arwE';
  } else if (e.k === 'loopL') {
    const p = left(f), q = left(t), rail = e.rail ?? (p.x - 60);
    d = `M ${p.x} ${p.y} L ${rail} ${p.y} L ${rail} ${q.y} L ${q.x} ${q.y}`;
    stroke = LOOP_CLR; marker = 'arwL'; dash = ' stroke-dasharray="7 4"'; lx = rail + 6; ly = (p.y + q.y)/2;
  } else if (e.k === 'loopR') {
    const p = left(f), q = right(t), rail = e.rail ?? ((p.x + q.x)/2);
    d = `M ${p.x} ${p.y} L ${rail} ${p.y} L ${rail} ${q.y} L ${q.x} ${q.y}`;
    stroke = LOOP_CLR; marker = 'arwL'; dash = ' stroke-dasharray="7 4"'; lx = rail + 6; ly = (p.y + q.y)/2;
  } else { // 'v'
    const p = bottom(f), q = top(t);
    if (Math.abs(p.x - q.x) < 1) {                       // same lane / same spine → straight down
      d = `M ${p.x} ${p.y} L ${q.x} ${q.y}`; lx = p.x + 8; ly = (p.y+q.y)/2;
    } else {                                             // crosses lanes → down, across, down
      const midy = e.rail ?? (p.y + q.y)/2;
      d = `M ${p.x} ${p.y} L ${p.x} ${midy} L ${q.x} ${midy} L ${q.x} ${q.y}`;
      lx = (p.x + q.x)/2 - 10; ly = midy - 8;
    }
  }
  const path = `<path d="${d}" fill="none" stroke="${stroke}" stroke-width="1.6"${dash} marker-end="url(#${marker})"/>`;
  const cls = (e.k === 'loopL' || e.k === 'loopR') ? 'elbl loop' : 'elbl';
  const label = e.l ? `<text x="${lx}" y="${ly}" class="${cls}">${esc(e.l)}</text>` : '';
  return path + label;
}
const lanes  = N.filter(n => n.type === 'lane');
const groups = N.filter(n => n.type === 'group');
const plain  = N.filter(n => n.type !== 'group' && n.type !== 'lane');
const svg =
`<svg xmlns="http://www.w3.org/2000/svg" width="${CANVAS_W}" height="${CANVAS_H}" viewBox="0 0 ${CANVAS_W} ${CANVAS_H}" font-family="Segoe UI, Arial, sans-serif">
<defs>
<marker id="arw" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L8,3 L0,6 z" fill="#4b5563"/></marker>
<marker id="arwL" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L8,3 L0,6 z" fill="${LOOP_CLR}"/></marker>
<marker id="arwE" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L8,3 L0,6 z" fill="${END_CLR}"/></marker>
</defs>
<rect x="0" y="0" width="${CANVAS_W}" height="${CANVAS_H}" fill="#ffffff"/>
${lanes.map(laneSVG).join('\n')}
${groups.map(groupSVG).join('\n')}
${E.map(edgeSVG).join('\n')}
${plain.map(shapeSVG).join('\n')}
</svg>`;
const html =
`<!doctype html><html><head><meta charset="utf-8"><style>
*{box-sizing:border-box} body{margin:0;background:#fff}
.lbl{width:100%;height:100%;display:flex;align-items:center;justify-content:center;text-align:center;
     padding:4px 8px;font-size:12.5px;line-height:1.28;color:#1f2937;overflow:hidden}
.lbl.bar{font-weight:600;color:#274a7a} .lbl.term{font-weight:600;color:#2f5c33}
.lbl.abort{color:#7a231d} .lbl.outcome{color:#2f5c33}
.glbl{font-size:12.5px;font-weight:700;color:#2563eb;text-align:left;line-height:1.2}
.lanelbl{width:100%;height:100%;display:flex;align-items:center;justify-content:center;text-align:center;
     font-size:13px;font-weight:700;color:#33495e;line-height:1.2;padding:2px 6px}
.elbl{font-size:12px;fill:#b45309;font-weight:600}
.elbl.loop{fill:#2563eb}
h2.title{font:700 20px "Segoe UI",Arial,sans-serif;color:#0b3d5c;text-align:center;margin:34px 40px 6px}
svg{display:block;margin:0 auto 40px}
</style></head><body>${model.title ? `<h2 class="title">${esc(model.title)}</h2>` : ''}${svg}</body></html>`;
const htmlPath = join(tmpdir(), `activity-${base}-${N.length}.html`);
writeFileSync(htmlPath, html, 'utf8');

// ---- (B) mxfile ----
const xesc = s => String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
function mxStyle(n) {
  const c = clr[n.type] || clr.action;
  if (n.type === 'lane')     return `swimlane;html=1;horizontal=1;startSize=${LANE_HEAD};fillColor=${c.head};swimlaneFillColor=${c.fill};strokeColor=${c.stroke};fontStyle=1;fontSize=13;fontColor=${c.headText};swimlaneLine=1;`;
  if (n.type === 'group')    return `rounded=1;dashed=1;dashPattern=8 5;html=1;fillColor=none;strokeColor=${c.stroke};verticalAlign=top;align=left;spacingLeft=10;spacingTop=4;fontColor=#2563eb;fontStyle=1;arcSize=6;`;
  if (n.type === 'term')     return `ellipse;whiteSpace=wrap;html=1;fillColor=${c.fill};strokeColor=${c.stroke};fontStyle=1;`;
  if (n.type === 'decision') return `rhombus;whiteSpace=wrap;html=1;fillColor=${c.fill};strokeColor=${c.stroke};`;
  if (n.type === 'bar')      return `rounded=1;whiteSpace=wrap;html=1;fillColor=${c.fill};strokeColor=${c.stroke};fontStyle=1;arcSize=6;`;
  return `rounded=1;whiteSpace=wrap;html=1;fillColor=${c.fill};strokeColor=${c.stroke};arcSize=10;`;
}
// exit/entry ports per edge kind — MUST match the SVG connection points so draw.io
// draws each arrow at the same side of each node as the rendered PNG.
function mxPorts(e) {
  switch (e.k) {
    case 'R':     return { exitX:1,   exitY:0.5, entryX:0, entryY:0.5 }; // right -> left
    case 'L':     return { exitX:0,   exitY:0.5, entryX:1, entryY:0.5 }; // left  -> right
    case 'join':  return { exitX:0.5, exitY:1,   entryX:1, entryY:0.5 }; // bottom -> right
    case 'end':   return { exitX:1,   exitY:0.5, entryX:1, entryY:0.5 }; // right -> right (via bus)
    case 'loopL': return { exitX:0,   exitY:0.5, entryX:0, entryY:0.5 }; // left -> left
    case 'loopR': return { exitX:0,   exitY:0.5, entryX:1, entryY:0.5 }; // left -> right
    default:      return { exitX:0.5, exitY:1,   entryX:0.5, entryY:0 }; // bottom -> top
  }
}
function mxEdgeStyle(e) {
  const p = mxPorts(e);
  const ports = `exitX=${p.exitX};exitY=${p.exitY};exitDx=0;exitDy=0;entryX=${p.entryX};entryY=${p.entryY};entryDx=0;entryDy=0;`;
  // edgeStyle=none → draw.io draws STRAIGHT segments through the explicit waypoints
  // (the rail/elbow corners), reproducing the SVG path EXACTLY. orthogonalEdgeStyle
  // would re-route on its own and pull edges toward the middle (arrows "dính vào giữa").
  if (e.k === 'end')   return 'edgeStyle=none;html=1;endArrow=block;strokeColor=' + END_CLR + ';' + ports;
  if (e.k === 'loopL' || e.k === 'loopR')
                       return 'edgeStyle=none;html=1;endArrow=block;dashed=1;dashPattern=7 4;strokeColor=' + LOOP_CLR + ';fontColor=' + LOOP_CLR + ';' + ports;
  return 'edgeStyle=none;html=1;endArrow=block;strokeColor=#4b5563;' + ports;
}
// explicit waypoints (the rail/elbow corners) — same geometry the SVG path uses,
// so draw.io routes through them instead of auto-routing a different path.
function mxEdgePoints(e) {
  const f = byId[e.f], t = byId[e.t];
  if (e.k === 'R')     { const p = right(f), q = left(t), midx = (p.x+q.x)/2;
                         // same-y side box → pure horizontal, NO waypoints (ports alone draw a clean
                         // straight line). Only emit the mid elbow when the box is vertically offset,
                         // and never emit duplicate/degenerate points (they glitch mxGraph routing).
                         return Math.abs(p.y - q.y) < 1 ? [] : [[midx,p.y],[midx,q.y]]; }
  if (e.k === 'L')     { const p = left(f), q = right(t), midx = (p.x+q.x)/2;
                         return Math.abs(p.y - q.y) < 1 ? [] : [[midx,p.y],[midx,q.y]]; }
  if (e.k === 'join')  { const p = bottom(f), q = right(t); return [[p.x,q.y]]; }
  if (e.k === 'end')   { const p = right(f), q = right(t);  return [[END_RAIL,p.y],[END_RAIL,q.y]]; }
  if (e.k === 'loopL') { const p = left(f), q = left(t),  rail = e.rail ?? (p.x-60);         return [[rail,p.y],[rail,q.y]]; }
  if (e.k === 'loopR') { const p = left(f), q = right(t), rail = e.rail ?? ((p.x+q.x)/2);    return [[rail,p.y],[rail,q.y]]; }
  // 'v' crossing lanes → the two elbow corners of the down/across/down jog
  { const p = bottom(f), q = top(t);
    if (Math.abs(p.x - q.x) < 1) return [];
    const midy = e.rail ?? (p.y + q.y)/2;
    return [[p.x,midy],[q.x,midy]]; }
}
const cells = [];
for (const n of [...lanes, ...groups, ...plain])
  cells.push(`<mxCell id="${n.id}" value="${xesc(n.t)}" style="${mxStyle(n)}" vertex="1" parent="1"><mxGeometry x="${n.x}" y="${n.y}" width="${n.w}" height="${n.h}" as="geometry"/></mxCell>`);
let ei = 0;
for (const e of E) {
  const pts = mxEdgePoints(e);
  const ptsXml = pts.length
    ? `<Array as="points">${pts.map(([x,y]) => `<mxPoint x="${Math.round(x)}" y="${Math.round(y)}"/>`).join('')}</Array>`
    : '';
  cells.push(`<mxCell id="e${ei++}" value="${xesc(e.l||'')}" style="${mxEdgeStyle(e)}" edge="1" parent="1" source="${e.f}" target="${e.t}"><mxGeometry relative="1" as="geometry">${ptsXml}</mxGeometry></mxCell>`);
}
const mxfile =
`<mxfile host="confluence" type="atlas" version="24.7.0"><diagram name="${xesc(base)}" id="act-${xesc(base)}"><mxGraphModel dx="1000" dy="1400" grid="0" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="${CANVAS_W}" pageHeight="${CANVAS_H}" math="0" shadow="0"><root><mxCell id="0"/><mxCell id="1" parent="0"/>
${cells.join('\n')}
</root></mxGraphModel></diagram></mxfile>`;
writeFileSync(join(outDir, base), mxfile, 'utf8');

// ---- (C) render PNG via headless Chrome ----
function findChrome() {
  if (process.env.CHROME_PATH && existsSync(process.env.CHROME_PATH)) return process.env.CHROME_PATH;
  const cands = [
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
    '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser',
  ];
  return cands.find(existsSync) || null;
}
const chrome = findChrome();
const pngPath = resolve(outDir, `${base}.png`);  // absolute: --headless=new writes relative paths to Chrome's own cwd
if (!chrome) {
  console.error(`[warn] Chrome not found — wrote mxfile + HTML (${htmlPath}) but NOT the PNG. Set CHROME_PATH and re-run, or screenshot ${htmlPath} manually.`);
  process.exit(2);
}
const winH = Math.round(CANVAS_H + 190);
const winW = Math.round(CANVAS_W + 140);
// Isolated --user-data-dir + --headless=new: without a fresh profile, Chrome
// ATTACHES to an already-running instance and returns WITHOUT writing the PNG
// (leaving a stale file on disk). rmSync the temp profile after.
import { rmSync, mkdtempSync } from 'node:fs';
const profile = mkdtempSync(join(tmpdir(), 'actshot-'));
try {
  execFileSync(chrome, [
    '--headless=new', '--disable-gpu', '--hide-scrollbars', '--force-device-scale-factor=2',
    `--user-data-dir=${profile}`, '--no-first-run', '--no-default-browser-check',
    `--window-size=${winW},${winH}`, '--default-background-color=FFFFFFFF',
    `--screenshot=${pngPath}`, `file://${htmlPath.replace(/\\/g,'/')}`,
  ], { stdio: 'ignore' });
} catch (e) {
  try { rmSync(profile, { recursive: true, force: true }); } catch {}
  console.error(`[warn] Chrome ran but failed (${e.message}) — wrote mxfile only, no PNG. ${htmlPath}`);
  process.exit(2);
}
try { rmSync(profile, { recursive: true, force: true }); } catch {}
if (!existsSync(pngPath)) {
  console.error(`[warn] Chrome ran but PNG missing at ${pngPath} — HTML is at ${htmlPath}. Screenshot it manually.`);
  process.exit(2);
}
console.log(`wrote: ${join(outDir, base)}  +  ${pngPath}  (${CANVAS_W}x${CANVAS_H} @2x)`);
