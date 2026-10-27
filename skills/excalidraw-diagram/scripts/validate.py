"""
validate.py — sanity-check an .excalidraw file before handing it to the user.

The failure this catches is the expensive one: arrows that render fine but aren't
actually bound, so they detach the moment the user drags a box. Binding is two-way
in Excalidraw — the arrow must name the box AND the box must name the arrow — and the
arrow endpoint must sit just OUTSIDE the box edge (within the declared `gap`), or the
app discards the binding on import. This script verifies all of that.

Run:  python validate.py path/to/file.excalidraw
Exits non-zero and prints a report if anything is wrong, so you can fix before shipping.
"""
import json
import sys


def validate(path):
    problems, warnings = [], []
    try:
        scene = json.load(open(path))
    except Exception as e:
        return [f"file is not valid JSON: {e}"], []

    if scene.get("type") != "excalidraw":
        problems.append(f'top-level "type" is {scene.get("type")!r}, expected "excalidraw"')
    els = scene.get("elements", [])
    by_id = {e["id"]: e for e in els}
    rects = [e for e in els if e["type"] == "rectangle"]
    arrows = [e for e in els if e["type"] == "arrow"]

    if not rects:
        warnings.append("no rectangles — unusual for a diagram")
    if not arrows:
        warnings.append("no arrows — fine for a static layout, but most diagrams have connections")

    for a in arrows:
        aid = a["id"]
        for side in ("startBinding", "endBinding"):
            b = a.get(side)
            if not b:
                warnings.append(f"arrow {aid}: {side} is null (free/unbound endpoint — OK only if intentional)")
                continue
            tgt = by_id.get(b.get("elementId"))
            if tgt is None:
                problems.append(f"arrow {aid}: {side} points at missing element {b.get('elementId')}")
                continue
            # reciprocal check — the box must list this arrow
            if not any(be.get("id") == aid for be in tgt.get("boundElements", [])):
                problems.append(
                    f"arrow {aid}: {side} -> box {tgt['id']} but that box does not list the arrow "
                    f"in boundElements (binding is one-way; it will detach on drag)")
            # snapped, not floating: the app writes a fixedPoint when you drop an arrow end on a shape
            if not b.get("fixedPoint"):
                problems.append(
                    f"arrow {aid}: {side} has no fixedPoint — it is not snapped to the shape's edge "
                    f"and will re-route or detach when the box moves")
            # geometry check — endpoint should sit on or just outside the edge, not deep inside
            pts = a.get("points", [])
            if pts:
                ox, oy = a["x"], a["y"]
                idx = 0 if side == "startBinding" else len(pts) - 1
                ex, ey = ox + pts[idx][0], oy + pts[idx][1]
                m = 2  # tolerance: on the edge is correct
                inside = (tgt["x"] + m < ex < tgt["x"] + tgt["width"] - m and
                          tgt["y"] + m < ey < tgt["y"] + tgt["height"] - m)
                if inside:
                    warnings.append(
                        f"arrow {aid}: {side} endpoint sits INSIDE box {tgt['id']} — move it to the edge")

    # text must belong to its shape: box labels bound to the box, arrow labels bound to the arrow
    texts = [e for e in els if e["type"] == "text"]
    for t in texts:
        cid = t.get("containerId")
        if cid:
            c = by_id.get(cid)
            if c is None:
                problems.append(f"text {t['id']} ({t.get('text','')[:30]!r}): containerId {cid} does not exist")
            elif not any(be.get("id") == t["id"] for be in c.get("boundElements", [])):
                problems.append(
                    f"text {t['id']} ({t.get('text','')[:30]!r}): bound to {cid} but that element does not "
                    f"list it in boundElements (one-way; the label will not move with the shape)")
        if not t.get("width"):
            problems.append(f"text {t['id']} ({t.get('text','')[:30]!r}): width is 0 — excalidraw.com wraps it one character per line")
    bound_ids = {be["id"] for e in els for be in e.get("boundElements", []) if be.get("type") == "text"}
    for t in texts:
        if not t.get("containerId") and t["id"] not in bound_ids:
            # a free text sitting on top of a rectangle is the "textbox inside a shape" anti-pattern
            tx, ty = t["x"] + t["width"] / 2, t["y"] + t["height"] / 2
            for r in rects:
                if set(t.get("groupIds", [])) & set(r.get("groupIds", [])):
                    continue   # title + subtext grouped with its box: intended
                if r["x"] < tx < r["x"] + r["width"] and r["y"] < ty < r["y"] + r["height"]:
                    warnings.append(
                        f"text {t['id']} ({t.get('text','')[:30]!r}) floats over box {r['id']} but is not "
                        f"bound to it — put the text IN the shape (containerId) so it moves and edits with it")
                    break

    # font / theme consistency (nice-to-have, not fatal)
    # ── layout quality: the things graph-drawing research says hurt reading most ──
    def segments(a):
        pts = [(a["x"] + p[0], a["y"] + p[1]) for p in a.get("points", [])]
        return list(zip(pts, pts[1:]))

    def label_of(e):
        for be in e.get("boundElements", []):
            if be.get("type") == "text" and be["id"] in by_id:
                return by_id[be["id"]].get("text", "").split("\n")[0][:28]
        g = set(e.get("groupIds", []))
        titles = sorted((t for t in texts if g & set(t.get("groupIds", []))), key=lambda t: t["y"])
        return titles[0]["text"].split("\n")[0][:28] if titles else e["id"]

    def seg_hits_rect(p, q, r, m=2):
        # does segment p-q pass through the interior of rect r (shrunk by m px)?
        x0, y0, x1, y1 = r["x"] + m, r["y"] + m, r["x"] + r["width"] - m, r["y"] + r["height"] - m
        (px, py), (qx, qy) = p, q
        # Liang–Barsky clip test
        dx, dy = qx - px, qy - py
        t0, t1 = 0.0, 1.0
        for pk, qk in ((-dx, px - x0), (dx, x1 - px), (-dy, py - y0), (dy, y1 - py)):
            if pk == 0:
                if qk < 0:
                    return False
                continue
            t = qk / pk
            if pk < 0:
                t0 = max(t0, t)
            else:
                t1 = min(t1, t)
            if t0 > t1:
                return False
        return t1 - t0 > 1e-6

    def seg_cross(p, q, r, s):
        def orient(a, b, c):
            return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        o1, o2, o3, o4 = orient(p, q, r), orient(p, q, s), orient(r, s, p), orient(r, s, q)
        return (o1 * o2 < 0) and (o3 * o4 < 0)   # strict: shared endpoints don't count

    bound_rects = lambda a: {(a.get("startBinding") or {}).get("elementId"), (a.get("endBinding") or {}).get("elementId")}
    for a in arrows:
        # 1. a nearly-level arrow is a tell that two boxes were meant to be aligned by middle
        pts = a.get("points", [])
        if len(pts) >= 2 and a.get("startBinding") and a.get("endBinding"):
            (x0, y0), (x1, y1) = (a["x"] + pts[0][0], a["y"] + pts[0][1]), (a["x"] + pts[-1][0], a["y"] + pts[-1][1])
            for off, axis in ((abs(y1 - y0), "y"), (abs(x1 - x0), "x")):
                if 1 < off < 16 and (abs(x1 - x0) if axis == "y" else abs(y1 - y0)) > 40:
                    s, e = by_id.get((a.get("startBinding") or {}).get("elementId")), by_id.get((a.get("endBinding") or {}).get("elementId"))
                    warnings.append(
                        f"arrow {label_of(s) if s else '?'} -> {label_of(e) if e else '?'} is off level by {off:.0f}px on {axis}; "
                        f"align the two boxes by their middles so it runs straight")
        # 2. an arrow should never pass through a box it is not connected to
        for r in rects:
            if r["id"] in bound_rects(a):
                continue
            if any(seg_hits_rect(p, q, r) for p, q in segments(a)):
                warnings.append(f"arrow {a['id']} passes through box {label_of(r)!r}; move the box or route around it")
                break
    # 3. crossings: the aesthetic with the largest measured effect on comprehension
    crossings, pairs = 0, []
    def ends(a):
        n = lambda b: label_of(by_id[b["elementId"]]) if b and b.get("elementId") in by_id else "?"
        return f"{n(a.get('startBinding'))} -> {n(a.get('endBinding'))}"
    for i in range(len(arrows)):
        for j in range(i + 1, len(arrows)):
            if bound_rects(arrows[i]) & bound_rects(arrows[j]):
                continue   # arrows sharing a box meet by design (fan-in/out)
            if any(seg_cross(p, q, r, s) for p, q in segments(arrows[i]) for r, s in segments(arrows[j])):
                crossings += 1
                pairs.append(f"[{ends(arrows[i])}] x [{ends(arrows[j])}]")
    if crossings:
        warnings.append(f"{crossings} arrow crossing(s) between unrelated arrows; reorder boxes within their column to remove them: "
                        + "; ".join(pairs[:5]))

    # 4. one lane per arrow (house style, Oct 27 2026): two arrows must not share a segment
    shared, spairs = 0, []
    for i in range(len(arrows)):
        for j in range(i + 1, len(arrows)):
            for p, q in segments(arrows[i]):
                for r, s_ in segments(arrows[j]):
                    vert = abs(p[0] - q[0]) < 1 and abs(r[0] - s_[0]) < 1 and abs(p[0] - r[0]) < 1
                    horiz = abs(p[1] - q[1]) < 1 and abs(r[1] - s_[1]) < 1 and abs(p[1] - r[1]) < 1
                    if vert:
                        lo, hi = max(min(p[1], q[1]), min(r[1], s_[1])), min(max(p[1], q[1]), max(r[1], s_[1]))
                    elif horiz:
                        lo, hi = max(min(p[0], q[0]), min(r[0], s_[0])), min(max(p[0], q[0]), max(r[0], s_[0]))
                    else:
                        continue
                    if hi - lo > 4:
                        shared += 1
                        spairs.append(f"[{ends(arrows[i])}] = [{ends(arrows[j])}]")
    if shared:
        warnings.append(f"{shared} overlapping arrow segment(s): arrows share a trunk; give each arrow its own lane and port: " + "; ".join(spairs[:5]))

    # Nunito (fontFamily 6) for all text, house style Oct 27 2026
    other = {e.get("fontFamily") for e in els if e["type"] == "text"} - {6}
    if other:
        warnings.append(f"text uses fontFamily {other}; house style is Nunito (6) everywhere")

    return problems, warnings


def main():
    if len(sys.argv) < 2:
        print("usage: python validate.py file.excalidraw")
        sys.exit(2)
    path = sys.argv[1]
    problems, warnings = validate(path)
    arrows = sum(1 for e in json.load(open(path)).get("elements", []) if e.get("type") == "arrow") \
        if not problems or "not valid JSON" not in problems[0] else 0
    if problems:
        print(f"❌ {len(problems)} problem(s) in {path}:")
        for p in problems:
            print(f"   - {p}")
    if warnings:
        print(f"⚠️  {len(warnings)} warning(s):")
        for w in warnings:
            print(f"   - {w}")
    if not problems and not warnings:
        print(f"✅ {path} looks good — {arrows} arrows, all bindings reciprocal & well-placed.")
    elif not problems:
        print(f"✅ no fatal problems ({arrows} arrows). Review warnings above.")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
