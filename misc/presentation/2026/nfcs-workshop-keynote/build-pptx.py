#!/usr/bin/env python3
"""Build the NFCS keynote PowerPoint from keynote.md — modern theme.

Excalidraw diagrams referenced as images (`![](…/foo.png)`) are recreated as
NATIVE PowerPoint objects (rounded cards, connectors w/ arrowheads, text boxes)
by reading the sibling `foo.excalidraw` source — not embedded as pictures.
A modern theme is applied: dark title/section slides, clean light content slides,
an indigo/slate palette, Segoe UI, accent rules, footer + page numbers, and
soft-shadowed flat cards.

Output: keynote-v<VERSION>.pptx   (VERSION read from ./VERSION, semver).
Iterate: edit keynote.md, bump ./VERSION, re-run `python3 build-pptx.py`.
"""
import json, re, pathlib
from pptx import Presentation
from pptx.util import Emu, Pt
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor
from pptx.oxml.ns import qn

HERE = pathlib.Path(__file__).resolve().parent
DECK = HERE / "keynote.md"
VERSION = (HERE / "VERSION").read_text().strip() if (HERE / "VERSION").exists() else "1.0.0"
OUT = HERE / f"keynote-v{VERSION}.pptx"
FOOTER = "NFCS AI Container Registry · Workshop 4 · Cambridge · 21 Jul 2026"

IN = 914400
SLIDE_W, SLIDE_H = int(13.333 * IN), int(7.5 * IN)

# ---- modern palette ----
BG_LIGHT = RGBColor(0xFF,0xFF,0xFF)
BG_DARK  = RGBColor(0x0F,0x17,0x2A)   # slate-900
INK      = RGBColor(0x0F,0x17,0x2A)
MUTED    = RGBColor(0x64,0x74,0x8B)   # slate-500
ACCENT   = RGBColor(0x63,0x66,0xF1)   # indigo-500
ACCENT_D = RGBColor(0x43,0x38,0xCA)   # indigo-700
ON_DARK  = RGBColor(0xE2,0xE8,0xF0)   # slate-200
ACCENT_L = RGBColor(0xC7,0xD2,0xFE)   # indigo-200
FONT   = "Segoe UI"
FONT_H = "Segoe UI Semibold"

# recolour Excalidraw's blue palette into the modern indigo/slate one
REMAP = {
    "3b82f6":"6366f1", "93c5fd":"c7d2fe", "dbeafe":"e0e7ff", "eff6ff":"eef2ff",
    "1e293b":"0f172a", "1e3a5f":"6366f1", "1e40af":"4338ca", "334155":"475569",
    "374151":"0f172a", "dc2626":"f43f5e",
}

def hexcolor(s, remap=True):
    if not s or s == "transparent": return None
    s = s.lstrip("#").lower()
    if len(s) == 3: s = "".join(c*2 for c in s)
    if remap: s = REMAP.get(s, s)
    try: return RGBColor(int(s[0:2],16), int(s[2:4],16), int(s[4:6],16))
    except Exception: return None

def clean(t):
    t = re.sub(r'`([^`]*)`', r'\1', t)
    return t.replace("**","").replace("*","").strip()

def set_bg(slide, rgb):
    slide.background.fill.solid(); slide.background.fill.fore_color.rgb = rgb

def no_shadow(shape):
    shape.shadow.inherit = False

def soft_shadow(shape):
    sp = shape._element.spPr
    old = sp.find(qn('a:effectLst'))
    if old is not None: sp.remove(old)
    eff = sp.makeelement(qn('a:effectLst'), {})
    shd = eff.makeelement(qn('a:outerShdw'),
                          {'blurRad':'55000','dist':'28000','dir':'5400000','rotWithShape':'0'})
    clr = shd.makeelement(qn('a:srgbClr'), {'val':'0F172A'})
    clr.append(clr.makeelement(qn('a:alpha'), {'val':'20000'}))
    shd.append(clr); eff.append(shd); sp.append(eff)

# ---------- Excalidraw -> native shapes ----------
def _bbox(elems):
    xs, ys = [], []
    for e in elems:
        x,y,w,h = e.get("x",0), e.get("y",0), e.get("width",0), e.get("height",0)
        if e.get("type") in ("arrow","line") and e.get("points"):
            for px,py in e["points"]: xs += [x+px]; ys += [y+py]
        else:
            xs += [x, x+w]; ys += [y, y+h]
    return min(xs), min(ys), max(xs), max(ys)

def _arrow(conn, start, end):
    ln = conn.line._get_or_add_ln()
    ln.set("cap","rnd")
    for tag,on in (("a:headEnd",start), ("a:tailEnd",end)):
        if not on: continue
        el = ln.find(qn(tag))
        if el is None: el = ln.makeelement(qn(tag), {}); ln.append(el)
        el.set("type","triangle"); el.set("w","med"); el.set("len","med")

def draw_excalidraw(slide, path, box):
    data = json.loads(pathlib.Path(path).read_text())
    elems = [e for e in data["elements"] if not e.get("isDeleted")]
    minx,miny,maxx,maxy = _bbox(elems)
    dw,dh = max(maxx-minx,1), max(maxy-miny,1)
    bx,by,bw,bh = box
    scale = min(bw/dw, bh/dh)
    offx, offy = bx + (bw-dw*scale)/2, by + (bh-dh*scale)/2
    X = lambda p: int(offx + (p-minx)*scale)
    Y = lambda p: int(offy + (p-miny)*scale)
    S = lambda v: max(int(v*scale), 1)
    order = {"rectangle":0,"ellipse":0,"diamond":0,"line":1,"text":2,"arrow":3}
    for e in sorted(elems, key=lambda e: order.get(e.get("type"),2)):
        t = e.get("type")
        if t in ("rectangle","ellipse","diamond"):
            shp = (MSO_SHAPE.ROUNDED_RECTANGLE if t=="rectangle"
                   else MSO_SHAPE.OVAL if t=="ellipse" else MSO_SHAPE.DIAMOND)
            sp = slide.shapes.add_shape(shp, X(e["x"]), Y(e["y"]), S(e["width"]), S(e["height"]))
            no_shadow(sp)
            if t == "rectangle":
                try: sp.adjustments[0] = 0.08
                except Exception: pass
            bg = hexcolor(e.get("backgroundColor"))
            dashed = e.get("strokeStyle") == "dashed"
            if bg:
                sp.fill.solid(); sp.fill.fore_color.rgb = bg
                if dashed:                       # container frame: keep a light border
                    sp.line.color.rgb = hexcolor(e.get("strokeColor")) or MUTED
                    sp.line.width = Pt(1)
                    ln = sp.line._get_or_add_ln(); ln.append(ln.makeelement(qn("a:prstDash"), {"val":"dash"}))
                else:
                    sp.line.fill.background()      # flat, borderless card
                    soft_shadow(sp)
            else:
                sp.fill.background()
                sp.line.color.rgb = hexcolor(e.get("strokeColor")) or MUTED
                sp.line.width = Pt(1)
                if dashed:
                    ln = sp.line._get_or_add_ln(); ln.append(ln.makeelement(qn("a:prstDash"), {"val":"dash"}))
        elif t in ("arrow","line"):
            pts = e.get("points") or [[0,0],[e.get("width",0),e.get("height",0)]]
            x0,y0 = e["x"]+pts[0][0], e["y"]+pts[0][1]
            x1,y1 = e["x"]+pts[-1][0], e["y"]+pts[-1][1]
            conn = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, X(x0),Y(y0),X(x1),Y(y1))
            conn.line.color.rgb = hexcolor(e.get("strokeColor")) or MUTED
            conn.line.width = Pt(max(1.25, e.get("strokeWidth",1)))
            if t == "arrow":
                _arrow(conn, bool(e.get("startArrowhead")), bool(e.get("endArrowhead", "arrow")))
        elif t == "text":
            tb = slide.shapes.add_textbox(X(e["x"]), Y(e["y"]), S(max(e.get("width",10),10)), S(max(e.get("height",10),10)))
            tf = tb.text_frame; tf.word_wrap = True
            tf.vertical_anchor = MSO_ANCHOR.MIDDLE if e.get("verticalAlign")=="middle" else MSO_ANCHOR.TOP
            for m in ("margin_left","margin_right","margin_top","margin_bottom"): setattr(tf, m, Emu(0))
            col = hexcolor(e.get("strokeColor")) or INK
            align = {"center":PP_ALIGN.CENTER,"right":PP_ALIGN.RIGHT}.get(e.get("textAlign"), PP_ALIGN.LEFT)
            big = e.get("fontSize",16) >= 24
            fs = Pt(max(7, e.get("fontSize",16)*scale/12700))
            for i,line in enumerate(str(e.get("text","")).split("\n")):
                p = tf.paragraphs[0] if i==0 else tf.add_paragraph()
                p.alignment = align
                r = p.add_run(); r.text = line
                r.font.size = fs; r.font.name = FONT_H if big else FONT
                r.font.bold = big; r.font.color.rgb = col

# ---------- keynote.md parser ----------
def parse(md):
    lines = pathlib.Path(md).read_text().split("\n")
    i = 0
    if lines and lines[0].strip() == "---":
        i = 1
        while i < len(lines) and lines[i].strip() != "---": i += 1
        i += 1
    chunks, cur = [], []
    for line in lines[i:]:
        if line.strip() == "---": chunks.append(cur); cur = []
        else: cur.append(line)
    chunks.append(cur)
    slides = []
    for ch in chunks:
        text = "\n".join(ch)
        notes = "\n".join(c.strip() for c in re.findall(r'<!--(.*?)-->', text, re.S)).strip()
        vis = re.sub(r'<!--.*?-->', '', text, flags=re.S)
        headings, bullets, table = [], [], []
        subtitle, image = None, None
        for raw in vis.split("\n"):
            s = raw.strip()
            if not s: continue
            if s.startswith("#"):
                lvl = len(s) - len(s.lstrip("#"))
                headings.append((lvl, clean(s.lstrip("#").strip())))
            elif s.startswith("!["):
                m = re.search(r'\(([^)]+)\)', s)
                if m: image = m.group(1)
            elif s.startswith("|"):
                cells = [c.strip() for c in s.strip("|").split("|")]
                if set("".join(cells)) <= set("-: "): continue
                table.append([clean(c) for c in cells])
            elif s.startswith("- "):
                lvl = (len(raw) - len(raw.lstrip())) // 2
                bullets.append((lvl, clean(s[2:])))
            elif s.startswith("*") and s.endswith("*"):
                subtitle = clean(s)
            else:
                bullets.append((0, clean(s)))
        if not (headings or bullets or table or image): continue
        slides.append(dict(headings=headings, subtitle=subtitle, bullets=bullets,
                           table=table, image=image, notes=notes))
    return slides

# ---------- slide rendering ----------
def _box(slide, l, t, w, h):
    tb = slide.shapes.add_textbox(int(l*IN), int(t*IN), int(w*IN), int(h*IN))
    tb.text_frame.word_wrap = True
    return tb

def _rule(slide, l, t, w=1.5, color=ACCENT):
    r = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, int(l*IN), int(t*IN), int(w*IN), int(0.06*IN))
    no_shadow(r); r.fill.solid(); r.fill.fore_color.rgb = color; r.line.fill.background()
    try: r.adjustments[0] = 0.5
    except Exception: pass

def add_notes(slide, notes):
    if notes: slide.notes_slide.notes_text_frame.text = notes

def add_chrome(slide, page):
    fb = _box(slide, 0.6, 7.02, 9.5, 0.35)
    r = fb.text_frame.paragraphs[0].add_run(); r.text = FOOTER
    r.font.size = Pt(9); r.font.name = FONT; r.font.color.rgb = MUTED
    pb = _box(slide, 12.2, 7.02, 0.9, 0.35); pp = pb.text_frame.paragraphs[0]; pp.alignment = PP_ALIGN.RIGHT
    r = pp.add_run(); r.text = str(page); r.font.size = Pt(10); r.font.name = FONT; r.font.color.rgb = MUTED

def render_lead(slide, s):
    big = [t for l,t in s["headings"] if l == 1]
    sub = [t for l,t in s["headings"] if l == 2] + ([s["subtitle"]] if s["subtitle"] else []) + [b for _,b in s["bullets"]]
    tb = _box(slide, 1.2, 2.0, 10.93, 3.5); tf = tb.text_frame; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    for i,line in enumerate(big):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph(); p.alignment = PP_ALIGN.CENTER
        r = p.add_run(); r.text = line
        r.font.size = Pt(44); r.font.bold = True; r.font.name = FONT_H; r.font.color.rgb = RGBColor(0xFF,0xFF,0xFF)
    _rule(slide, 6.17, 4.7, 1.0)
    for j,line in enumerate(sub):
        p = tf.add_paragraph(); p.alignment = PP_ALIGN.CENTER; p.space_before = Pt(10)
        r = p.add_run(); r.text = line
        r.font.size = Pt(20 if j == 0 else 16); r.font.name = FONT
        r.font.color.rgb = ACCENT_L if j == 0 else ON_DARK

def render_content(slide, s):
    title = next((t for l,t in s["headings"] if l == 2), None) or next((t for _,t in s["headings"]), "")
    tb = _box(slide, 0.6, 0.4, 12.13, 0.8)
    r = tb.text_frame.paragraphs[0].add_run(); r.text = title
    r.font.size = Pt(30); r.font.bold = True; r.font.name = FONT_H; r.font.color.rgb = INK
    _rule(slide, 0.62, 1.16, 1.4)
    top = 1.5
    if s["subtitle"]:
        sb = _box(slide, 0.62, 1.28, 12.1, 0.5); sp = sb.text_frame.paragraphs[0]
        rr = sp.add_run(); rr.text = s["subtitle"]
        rr.font.size = Pt(15); rr.font.italic = True; rr.font.name = FONT; rr.font.color.rgb = MUTED
        top = 1.85
    if s["image"]:
        exc = pathlib.Path((HERE / s["image"]).resolve()).with_suffix(".excalidraw")
        box = (int(0.6*IN), int(top*IN), int(12.13*IN), int((6.75-top)*IN))
        if exc.exists(): draw_excalidraw(slide, exc, box)
        else: slide.shapes.add_picture(str((HERE/s["image"]).resolve()), box[0], box[1], height=box[3])
    elif s["table"]:
        _render_table(slide, s["table"], top)
    if s["bullets"] and not s["image"]:
        bb = _box(slide, 0.7, top, 11.9, 6.7-top); btf = bb.text_frame
        for i,(lvl,txt) in enumerate(s["bullets"]):
            p = btf.paragraphs[0] if i == 0 else btf.add_paragraph()
            p.level = min(lvl, 4); p.space_after = Pt(8)
            marker = p.add_run(); marker.text = ("●  " if lvl == 0 else "–  ")
            marker.font.size = Pt(16 if lvl == 0 else 13); marker.font.name = FONT
            marker.font.color.rgb = ACCENT if lvl == 0 else MUTED
            r = p.add_run(); r.text = txt
            r.font.size = Pt(20 if lvl == 0 else 16); r.font.name = FONT; r.font.color.rgb = INK

def _render_table(slide, rows, top):
    nr, nc = len(rows), max(len(r) for r in rows)
    gf = slide.shapes.add_table(nr, nc, int(0.6*IN), int(top*IN), int(12.13*IN), int(min(0.8*nr,4.6)*IN))
    tbl = gf.table
    tbl.first_row = True; tbl.horz_banding = True
    for ci in range(nc): tbl.columns[ci].width = int(12.13/nc*IN)
    for ri,row in enumerate(rows):
        for ci in range(nc):
            cell = tbl.cell(ri, ci)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.margin_left = cell.margin_right = Emu(int(0.12*IN))
            cell.margin_top = cell.margin_bottom = Emu(int(0.06*IN))
            cell.fill.solid()
            cell.fill.fore_color.rgb = ACCENT_D if ri == 0 else (RGBColor(0xF1,0xF5,0xF9) if ri % 2 else BG_LIGHT)
            cell.text = row[ci] if ci < len(row) else ""
            for para in cell.text_frame.paragraphs:
                para.alignment = PP_ALIGN.LEFT
                for r in para.runs:
                    r.font.size = Pt(13); r.font.name = FONT; r.font.bold = (ri == 0)
                    r.font.color.rgb = RGBColor(0xFF,0xFF,0xFF) if ri == 0 else INK

def is_lead(s):
    return any(l == 1 for l,_ in s["headings"])

def main():
    prs = Presentation()
    prs.slide_width, prs.slide_height = SLIDE_W, SLIDE_H
    blank = prs.slide_layouts[6]
    slides = parse(DECK); page = 0
    for s in slides:
        slide = prs.slides.add_slide(blank)
        lead = is_lead(s)
        set_bg(slide, BG_DARK if lead else BG_LIGHT)
        if lead:
            render_lead(slide, s)
        else:
            page += 1
            render_content(slide, s)
            add_chrome(slide, page)
        add_notes(slide, s["notes"])
    prs.save(OUT)
    print(f"wrote {OUT.name}  ({len(slides)} slides, v{VERSION})")

if __name__ == "__main__":
    main()
