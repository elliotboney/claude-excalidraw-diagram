"""
excalidraw.py — build editable, well-bound Excalidraw scenes from a layout spec.

Why this exists: hand-authoring Excalidraw JSON is error-prone, and the #1 failure
is arrows that LOOK connected but aren't actually *bound* — so when the user drags a
box in the app, the arrows stay behind, floating. Excalidraw binding is two-way and
geometry-sensitive; this module gets it right so every diagram is editable.

Usage (write a short script that imports this):

    from excalidraw import Diagram
    d = Diagram(theme="dark")
    d.box("browser", 40, 100, 180, 60, kind="neutral", text="Browser\\nclient")
    d.box("api",     320, 100, 180, 60, kind="process", text="API server\\nFastAPI")
    d.box("db",      600, 100, 180, 60, kind="data",    text="Postgres")
    d.arrow("browser", "api", label="HTTPS")
    d.arrow("api", "db")
    d.label(40, 60, "Request path", kind="process", size=16)
    d.save("my-diagram.excalidraw")

Then the user opens the .excalidraw file at excalidraw.com (File > Open) and edits.

Coordinates are a plain canvas plane (x right, y down). Lay boxes out in bands and
let arrows connect by NAME so they bind. You can also pass an (x, y) tuple as an
arrow endpoint for an unbound free end, but prefer names so dragging stays clean.
"""
import json
import random

# ── Palette ──────────────────────────────────────────────────────────────────
# Semantic "kinds" → (stroke, fill). Pick by ROLE, not by color name, so diagrams
# stay legible and consistent. Fills are deep/desaturated for the dark canvas.
KINDS_DARK = {
    "source":   ("#a78bfa", "#2e1065"),  # violet — inputs, databases, raw data
    "data":     ("#a78bfa", "#2e1065"),  # alias of source
    "process":  ("#34d399", "#064e3b"),  # emerald — services, transforms, logic
    "accent":   ("#fb923c", "#431407"),  # orange — buses, queues, connectors, intermediate artifacts
    "ui":       ("#22d3ee", "#083344"),  # cyan — frontends, dashboards, outputs the user sees
    "note":     ("#fb7185", "transparent"),  # rose (dashed) — annotations, rules, callouts
    "neutral":  ("#94a3b8", "#1e293b"),  # slate — external/generic/legacy
    "emphasis": ("#34d399", "#065f46"),  # brighter emerald — the central/hub node
}
KINDS_LIGHT = {
    "source":   ("#7c3aed", "#ede9fe"),
    "data":     ("#7c3aed", "#ede9fe"),
    "process":  ("#059669", "#d1fae5"),
    "accent":   ("#ea580c", "#ffedd5"),
    "ui":       ("#0891b2", "#cffafe"),
    "note":     ("#e11d48", "transparent"),
    "neutral":  ("#475569", "#f1f5f9"),
    "emphasis": ("#059669", "#a7f3d0"),
}
TEXT_DARK, BG_DARK = "#e2e8f0", "#020617"
TEXT_LIGHT, BG_LIGHT = "#1e293b", "#ffffff"
MUTED_DARK, MUTED_LIGHT = "#94a3b8", "#64748b"   # subtext under a box title
TITLE_SIZE, SUB_SIZE, TITLE_GAP = 20, 14, 4

FONT_CODE = 3      # Excalidraw monospace ("Code")
FONT_HAND = 1      # Excalidraw hand-drawn ("Virgil")
FONT_NORMAL = 2    # Excalidraw "Normal" (Helvetica)
FONT_EXCALIFONT = 5  # Excalidraw's current default hand font
FONT_NUNITO = 6    # house style (Oct 27, 2026): Nunito for ALL text, boxes, arrow labels, titles
LINE_HEIGHT = 1.35   # Nunito's line height in the app
SNAP_OUT = 5.75    # px an arrow end sits outside the box side it is snapped to; measured from
                   # arrows drawn by hand in the app (fixedPoint 1.0239 on a 240px box).
LANE_MARGIN = 14   # px kept clear between a lane and the source/target side (room for the arrowhead)
CHAR_W = 0.55      # average glyph width as a fraction of fontSize, for the text width estimate.
                   # Excalidraw re-measures on load (autoResize), but width 0 makes it wrap per char.


class Diagram:
    def __init__(self, theme="dark", font=FONT_NUNITO):
        self.theme = theme
        self.font = font
        self.kinds = KINDS_DARK if theme == "dark" else KINDS_LIGHT
        self.text_color = TEXT_DARK if theme == "dark" else TEXT_LIGHT
        self.bg = BG_DARK if theme == "dark" else BG_LIGHT
        self.els = []
        self.boxes = {}          # name -> rectangle element dict
        self._rng = random.Random(20240601)
        self._meta = []          # per arrow: what _route() needs to place ports and lanes

    # ── internals ────────────────────────────────────────────────────────────
    def _id(self, p):
        return f"{p}{len(self.els)}_{self._rng.randint(1, 2**31)}"

    def _nonce(self):
        return self._rng.randint(1, 2**31)

    _NOW = 1750000000000

    @staticmethod
    def _text_size(text, size):
        lines = text.split("\n")
        return max(len(l) for l in lines) * size * CHAR_W, len(lines) * size * LINE_HEIGHT

    def _add_text(self, x, y, text, size, color, align, gid, container=None, font=None,
                  valign="top"):
        """A text element. With `container` (a rectangle or arrow element) the text is
        BOUND to it: Excalidraw treats it as the shape's own label, keeps it centered,
        and moves/edits it with the shape. Both sides record the link."""
        w, h = self._text_size(text, size)
        t = {
            "type": "text", "id": self._id("t"), "x": x, "y": y,
            "width": w, "height": h, "angle": 0, "strokeColor": color,
            "backgroundColor": "transparent", "fillStyle": "solid", "strokeWidth": 1,
            "strokeStyle": "solid", "roughness": 0, "opacity": 100,
            "groupIds": [gid] if gid else [], "frameId": None, "roundness": None,
            "seed": self._nonce(), "version": 1, "versionNonce": self._nonce(),
            "isDeleted": False, "boundElements": [], "updated": self._NOW, "link": None,
            "locked": False, "text": text, "fontSize": size,
            "fontFamily": self.font if font is None else font,
            "textAlign": align, "verticalAlign": valign,
            "containerId": container["id"] if container else None,
            "originalText": text, "autoResize": True, "lineHeight": LINE_HEIGHT,
        }
        self.els.append(t)
        if container is not None:
            container["boundElements"].append({"type": "text", "id": t["id"]})
        return t

    # ── public API ───────────────────────────────────────────────────────────
    def box(self, name, x, y, w, h, kind="neutral", text="", size=16, dashed=False, sub=None):
        """A rectangle whose text is BOUND to it (the shape's own label, not a separate
        text box floating on top). Refer to it by `name` when drawing arrows so the
        connection binds. `kind` selects the palette role.

        `sub` switches to title + subtext: `text` becomes a 20px title and `sub` 14px muted
        notes under it. Excalidraw allows one bound text per shape, so both are separate
        texts GROUPED with the box (they drag with it; double-click either to edit)."""
        stroke, bg = self.kinds.get(kind, self.kinds["neutral"])
        gid = self._id("g")
        rect = {
            "type": "rectangle", "id": self._id("r"), "x": x, "y": y, "width": w, "height": h,
            "angle": 0, "strokeColor": stroke, "backgroundColor": bg, "fillStyle": "solid",
            "strokeWidth": 1.5, "strokeStyle": "dashed" if dashed else "solid", "roughness": 0,
            "opacity": 100, "groupIds": [gid], "frameId": None, "roundness": {"type": 3},
            "seed": self._nonce(), "version": 1, "versionNonce": self._nonce(),
            "isDeleted": False, "boundElements": [], "updated": self._NOW, "link": None,
            "locked": False,
        }
        self.els.append(rect)
        self.boxes[name] = rect
        if text and sub:
            muted = MUTED_DARK if self.theme == "dark" else MUTED_LIGHT
            (tw1, th1), (tw2, th2) = self._text_size(text, TITLE_SIZE), self._text_size(sub, SUB_SIZE)
            if max(tw1, tw2) > w - 16 or th1 + TITLE_GAP + th2 > h - 8:
                print(f"warn: box {name!r} is {w}x{h} but title + subtext need about "
                      f"{max(tw1, tw2):.0f}x{th1 + TITLE_GAP + th2:.0f}; widen it or shorten the text")
            top = y + (h - th1 - TITLE_GAP - th2) / 2
            for txt, sz, col, ty, tw in ((text, TITLE_SIZE, self.text_color, top, tw1),
                                         (sub, SUB_SIZE, muted, top + th1 + TITLE_GAP, tw2)):
                self._add_text(x + (w - tw) / 2, ty, txt, sz, col, "center", gid)
        elif text:
            tw, th = self._text_size(text, size)
            if tw > w - 16 or th > h - 8:
                print(f"warn: box {name!r} is {w}x{h} but its text needs about {tw:.0f}x{th:.0f}; widen it or shorten the text")
            tw = min(tw, w - 16)
            self._add_text(x + (w - tw) / 2, y + (h - th) / 2, text, size, self.text_color,
                           "center", None, container=rect, font=FONT_NUNITO, valign="middle")
        return rect

    def label(self, x, y, text, kind=None, color=None, size=15, align="left"):
        """Standalone (unboxed) text — band headers, titles, free annotations."""
        if color is None:
            color = self.kinds[kind][0] if kind else self.text_color
        self._add_text(x, y, text, size, color, align, None)

    @staticmethod
    def _sides(a, b):
        """Which side of box `a` an arrow to box `b` leaves from, and which side of `b` it
        enters. The rule layered layout engines use: if `b` lies wholly to the right of `a`,
        leave a's right side and enter b's left side, even when b is far above or below
        (think a hub fanning out to a column of targets). Likewise left, below, above.
        Only when the boxes overlap on both axes fall back to the dominant direction."""
        if b["x"] >= a["x"] + a["width"]:
            return "right", "left"
        if b["x"] + b["width"] <= a["x"]:
            return "left", "right"
        if b["y"] >= a["y"] + a["height"]:
            return "bottom", "top"
        if b["y"] + b["height"] <= a["y"]:
            return "top", "bottom"
        dx = (b["x"] + b["width"] / 2) - (a["x"] + a["width"] / 2)
        dy = (b["y"] + b["height"] / 2) - (a["y"] + a["height"] / 2)
        if abs(dx) >= abs(dy):
            return ("right", "left") if dx >= 0 else ("left", "right")
        return ("bottom", "top") if dy >= 0 else ("top", "bottom")

    @staticmethod
    def _side_point(r, side):
        """Where the app snaps an arrow end: the MIDPOINT of `side`, SNAP_OUT px outside
        it. Returns (x, y, fixedPoint). The along-edge coordinate is 0.5001 (the app's own
        value) and the other one encodes the outside offset, e.g. the right side of a
        240-wide box is fixedPoint [1 + 5.75/240, 0.5001]. Aiming at the other box's
        center instead lands the end off-middle whenever the two boxes differ in size,
        and the arrow then stays tilted after you align them."""
        cx, cy = r["x"] + r["width"] / 2, r["y"] + r["height"] / 2
        w, h = r["width"], r["height"]
        if side in ("left", "right"):
            x = r["x"] + w + SNAP_OUT if side == "right" else r["x"] - SNAP_OUT
            return x, cy, [round((x - r["x"]) / w, 6), 0.5001]
        y = r["y"] + h + SNAP_OUT if side == "bottom" else r["y"] - SNAP_OUT
        return cx, y, [0.5001, round((y - r["y"]) / h, 6)]

    # ── layout helpers: keep same-stage boxes on one axis so arrows come out level ──
    class _Column:
        def __init__(self, d, x, w, y, gap):
            self.d, self.x, self.w, self.y, self.gap = d, x, w, y, gap

        def box(self, name, h, **kw):
            r = self.d.box(name, self.x, self.y, self.w, h, **kw)
            self.y += h + self.gap
            return r

        def skip(self, px):
            self.y += px

    def column(self, x, w, y=0, gap=40):
        """Stack boxes top-down at one x with one width: `c = d.column(360, 200, y=150)`
        then `c.box("fab", 90, kind="process", text=...)`. Same width per column and a
        fixed gap is most of what makes a layered diagram look laid out."""
        return Diagram._Column(self, x, w, y, gap)

    def align_middle(self, *names):
        """Shift the named boxes vertically so their centers match the first one's. Use on
        boxes in adjacent columns joined by a horizontal arrow, so the arrow is level."""
        cy = self.boxes[names[0]]["y"] + self.boxes[names[0]]["height"] / 2
        for n in names[1:]:
            r = self.boxes[n]
            dy = cy - r["height"] / 2 - r["y"]
            r["y"] += dy
            for t in self.els:     # bound text, and title + subtext grouped with the box
                if t["type"] == "text" and (t.get("containerId") == r["id"] or
                                            set(t["groupIds"]) & set(r["groupIds"])):
                    t["y"] += dy

    def arrow(self, start, end, kind="neutral", color=None, dashed=False, width=1.5,
              label=None, elbow=True, label_at=None):
        """Connect two boxes (by name) with a SNAPPED arrow. Each endpoint sits at the
        middle of the box side facing the other box, SNAP_OUT px outside it, and is bound
        with a matching `fixedPoint`, which is exactly what the app writes when you drag an
        arrow end onto a shape. Aligning two boxes by their middles then levels the arrow.
        Both the arrow and the two boxes record the binding, so the arrow follows the box
        on drag. `label` becomes text BOUND to the arrow (the arrow's own label, moves with
        it), not a free text element parked near the midpoint. By default it sits on the
        first leg, by the source; `label_at` (0..1 of the path length, the app's
        `labelPosition`) overrides that. Ports and lanes are placed later, in save().
        `start`/`end` may also be (x, y) tuples for a free, unbound endpoint.

        `elbow=True` (default) makes an orthogonal right-angle arrow — Excalidraw's
        elbow router keeps the path tidy and re-routes automatically when boxes move,
        which reads far cleaner than diagonal straight lines in a banded layout. Pass
        elbow=False only when a direct diagonal genuinely looks better."""
        if color is None:
            color = self.kinds.get(kind, self.kinds["neutral"])[0]

        a_rect = self.boxes[start] if isinstance(start, str) else None
        b_rect = self.boxes[end] if isinstance(end, str) else None
        if a_rect and b_rect:
            a_side, b_side = self._sides(a_rect, b_rect)
        else:
            # one free end: face the free point
            fake = lambda p: {"x": p[0], "y": p[1], "width": 0, "height": 0}
            a_side, b_side = self._sides(a_rect or fake(start), b_rect or fake(end))

        if a_rect:
            sx, sy, a_fp = self._side_point(a_rect, a_side)
        else:
            (sx, sy), a_fp = (float(start[0]), float(start[1])), None
        if b_rect:
            ex, ey, b_fp = self._side_point(b_rect, b_side)
        else:
            (ex, ey), b_fp = (float(end[0]), float(end[1])), None

        dx, dy = ex - sx, ey - sy
        if elbow and abs(dx) > 2 and abs(dy) > 2:
            # Orthogonal route for the initial render; Excalidraw's elbow router
            # recomputes a tidy path from the bindings on load/drag. Leave the start box
            # along the axis its snap side faces, so the first segment exits cleanly.
            # Provisional; _route() on save spreads ports and gives each arrow its own lane.
            horizontal_exit = a_side in ("left", "right")
            if horizontal_exit:
                points = [[0, 0], [dx / 2, 0], [dx / 2, dy], [dx, dy]]
            else:
                points = [[0, 0], [0, dy / 2], [dx, dy / 2], [dx, dy]]
            roundness = None
        else:
            points = [[0, 0], [dx, dy]]
            roundness = None if elbow else {"type": 2}

        aid = self._id("a")
        arrow = {
            "type": "arrow", "id": aid, "x": sx, "y": sy,
            "width": abs(dx), "height": abs(dy), "angle": 0,
            "strokeColor": color, "backgroundColor": "transparent", "fillStyle": "solid",
            "strokeWidth": width, "strokeStyle": "dashed" if dashed else "solid",
            "roughness": 1, "opacity": 100, "groupIds": [], "frameId": None,
            "roundness": roundness, "elbowed": bool(elbow), "seed": self._nonce(), "version": 1,
            "versionNonce": self._nonce(), "isDeleted": False, "boundElements": [],
            "updated": self._NOW, "link": None, "locked": False,
            "points": points, "lastCommittedPoint": None,
            "startBinding": {"elementId": a_rect["id"], "mode": "orbit",
                             "fixedPoint": a_fp} if a_rect else None,
            "endBinding": {"elementId": b_rect["id"], "mode": "orbit",
                           "fixedPoint": b_fp} if b_rect else None,
            "startArrowhead": None, "endArrowhead": "arrow",
        }
        self.els.append(arrow)
        if a_rect is not None:
            a_rect["boundElements"].append({"id": aid, "type": "arrow"})
        if b_rect is not None:
            b_rect["boundElements"].append({"id": aid, "type": "arrow"})
        if label:
            # bound label: the app keeps it at the path's middle, or at `labelPosition`
            # (a 0..1 fraction of the path length) when that is set
            tw, th = self._text_size(label, 16)
            if label_at is None:
                mx, my = sx + dx / 2, sy + dy / 2
            else:
                mx, my = self._along(points, label_at)
                mx, my = sx + mx, sy + my
            t = self._add_text(mx - tw / 2, my - th / 2, label, 16, self.text_color, "center",
                               None, container=arrow, font=FONT_NUNITO, valign="middle")
            if label_at is not None:
                t["labelPosition"] = float(label_at)
        else:
            t = None
        self._meta.append(dict(arrow=arrow, a=a_rect, b=b_rect, a_side=a_side, b_side=b_side,
                               start=start, end=end, label=t, label_at=label_at, elbow=elbow))
        return arrow

    @staticmethod
    def _along(points, frac):
        """Point at `frac` of the polyline's length, in the arrow's local coordinates."""
        segs = list(zip(points, points[1:]))
        lens = [abs(q[0] - p[0]) + abs(q[1] - p[1]) for p, q in segs]
        target, run = frac * sum(lens), 0.0
        for (p, q), L in zip(segs, lens):
            if run + L >= target and L > 0:
                k = (target - run) / L
                return p[0] + (q[0] - p[0]) * k, p[1] + (q[1] - p[1]) * k
            run += L
        return points[-1]

    # ── routing pass, run on save: needs every arrow before it can share out the ports ──
    @staticmethod
    def _port(r, side, frac):
        """Point on `side` of r at `frac` along it, SNAP_OUT px outside, plus its fixedPoint."""
        w, h = r["width"], r["height"]
        if side in ("left", "right"):
            x = r["x"] + w + SNAP_OUT if side == "right" else r["x"] - SNAP_OUT
            return x, r["y"] + h * frac, [round((x - r["x"]) / w, 6), round(frac, 6)]
        y = r["y"] + h + SNAP_OUT if side == "bottom" else r["y"] - SNAP_OUT
        return r["x"] + w * frac, y, [round(frac, 6), round((y - r["y"]) / h, 6)]

    @staticmethod
    def _crossings(polys):
        def orient(a, b, c):
            return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        def cross(p, q, r, s):
            if orient(p, q, r) * orient(p, q, s) < 0 and orient(r, s, p) * orient(r, s, q) < 0:
                return True
            # two parallel legs lying on each other read as one line: count it like a crossing
            for ax in (0, 1):
                o = 1 - ax
                if abs(p[o] - q[o]) < 1 and abs(r[o] - s[o]) < 1 and abs(p[o] - r[o]) < 4:
                    lo = max(min(p[ax], q[ax]), min(r[ax], s[ax]))
                    if min(max(p[ax], q[ax]), max(r[ax], s[ax])) - lo > 4:
                        return True
            return False
        n = 0
        for i in range(len(polys)):
            for j in range(i + 1, len(polys)):
                n += any(cross(p, q, r, s) for p, q in zip(polys[i], polys[i][1:])
                         for r, s in zip(polys[j], polys[j][1:]))
        return n

    def _route(self):
        """House arrow style (from a hand-fixed diagram, Oct 27, 2026):
        1. Ports spread: when n arrows use one side of a box, their ends sit at (i+1)/(n+1)
           along it, ordered by where the other end is, so the top neighbour gets the top
           port. A lone arrow keeps the midpoint, so middle-aligned boxes stay level.
        2. One lane per arrow: every elbow arrow gets its own vertical segment in the gap,
           pinned with `fixedSegments` so the app's router keeps it. No shared trunk.
           Lane order is searched to minimize crossings within the gap."""
        ends = {}
        for m in self._meta:
            for which, r, side, other in (("a", m["a"], m["a_side"], m["b"] or m["end"]),
                                          ("b", m["b"], m["b_side"], m["a"] or m["start"])):
                if r is not None:
                    ends.setdefault((r["id"], side), []).append((m, which, r, side, other))
        for group in ends.values():
            def key(g):
                o, side = g[4], g[3]
                if isinstance(o, dict):
                    c = (o["x"] + o["width"] / 2, o["y"] + o["height"] / 2)
                else:
                    c = o
                return c[1] if side in ("left", "right") else c[0]
            group.sort(key=key)
            # an arrow to a box aligned with this one by middle keeps the midpoint, so it
            # stays level; the rest spread over the half above or below it
            r0, side0 = group[0][2], group[0][3]
            mid = r0["y"] + r0["height"] / 2 if side0 in ("left", "right") else r0["x"] + r0["width"] / 2
            pin = next((g for g in group if isinstance(g[4], dict) and abs(key(g) - mid) < 2), None)
            if pin is None:
                fracs = [0.5001] if len(group) == 1 else [(i + 1) / (len(group) + 1) for i in range(len(group))]
            else:
                k = group.index(pin)
                fracs = [0.5 * (i + 1) / (k + 1) for i in range(k)] + [0.5001] + \
                        [0.5 + 0.5 * (i + 1) / (len(group) - k) for i in range(len(group) - k - 1)]
            for frac, (m, which, r, side, _) in zip(fracs, group):
                m[which + "_pt"] = self._port(r, side, frac)
        # a horizontal arrow a few px off level: slide its target port to the source's height
        for m in self._meta:
            if m["a"] and m["b"] and m["b_side"] in ("left", "right"):
                r, dy = m["b"], m["a_pt"][1] - m["b_pt"][1]
                if 0 < abs(dy) <= 12 and r["y"] < m["a_pt"][1] < r["y"] + r["height"]:
                    m["b_pt"] = self._port(r, m["b_side"], (m["a_pt"][1] - r["y"]) / r["height"])
        for m in self._meta:
            m["sx"], m["sy"] = (m["a_pt"][:2] if m["a"] else map(float, m["start"]))
            m["ex"], m["ey"] = (m["b_pt"][:2] if m["b"] else map(float, m["end"]))
            m["lane"] = None
        # lanes: horizontal-exit elbow arrows that need a bend, grouped by the column they enter
        gaps = {}
        for m in self._meta:
            dx, dy = m["ex"] - m["sx"], m["ey"] - m["sy"]
            if m["elbow"] and m["a_side"] in ("left", "right") and abs(dy) > 2 and abs(dx) > 2:
                gaps.setdefault((round(m["ex"] / 20), dx > 0), []).append(m)
        for (_, rightward), g in gaps.items():
            near = max(m["sx"] for m in g) if rightward else min(m["sx"] for m in g)
            far = g[0]["ex"]
            lo, hi = sorted((near, far))
            lo, hi = lo + LANE_MARGIN, hi - LANE_MARGIN
            if hi <= lo:
                for m in g:
                    m["lane"] = (m["sx"] + m["ex"]) / 2
                continue
            slots = [lo + (hi - lo) * (i + 1) / (len(g) + 1) for i in range(len(g))]
            if not rightward:
                slots.reverse()
            if len(g) > 1 and (hi - lo) / (len(g) + 1) < 12:
                print(f"warn: {len(g)} arrow lanes squeezed into a {hi - lo + 2 * LANE_MARGIN:.0f}px gap; widen the gap before x={far:.0f}")
            poly = lambda m, x: [(m["sx"], m["sy"]), (x, m["sy"]), (x, m["ey"]), (m["ex"], m["ey"])]
            order = sorted(g, key=lambda m: m["ey"])
            best = self._crossings([poly(m, x) for m, x in zip(order, slots)])
            improved = True
            while improved and best:
                improved = False
                for i in range(len(order)):
                    for j in range(i + 1, len(order)):
                        order[i], order[j] = order[j], order[i]
                        c = self._crossings([poly(m, x) for m, x in zip(order, slots)])
                        if c < best:
                            best, improved = c, True
                        else:
                            order[i], order[j] = order[j], order[i]
            for m, x in zip(order, slots):
                m["lane"] = x
        for m in self._meta:
            a, sx, sy = m["arrow"], m["sx"], m["sy"]
            dx, dy = m["ex"] - sx, m["ey"] - sy
            if m["lane"] is not None:
                lx = m["lane"] - sx
                pts = [[0, 0], [lx, 0], [lx, dy], [dx, dy]]
                a["fixedSegments"] = [{"index": 2, "start": [lx, 0], "end": [lx, dy]}]
                a["startIsSpecial"] = a["endIsSpecial"] = False
            elif m["elbow"] and abs(dx) > 2 and abs(dy) > 2:     # vertical exit: bend halfway
                pts = [[0, 0], [0, dy / 2], [dx, dy / 2], [dx, dy]]
            else:
                pts = [[0, 0], [dx, dy]]
            a.update(x=sx, y=sy, width=abs(dx), height=abs(dy), points=pts)
            if m["a"]:
                a["startBinding"]["fixedPoint"] = m["a_pt"][2]
            if m["b"]:
                a["endBinding"]["fixedPoint"] = m["b_pt"][2]
            t = m["label"]
            if t is not None:
                frac = m["label_at"]
                if frac is None:     # default: middle of the first leg, by the source
                    total = sum(abs(q[0] - p[0]) + abs(q[1] - p[1]) for p, q in zip(pts, pts[1:]))
                    first = abs(pts[1][0]) + abs(pts[1][1])
                    frac = 0.5 if len(pts) == 2 or not total else first / 2 / total
                    t["labelPosition"] = round(frac, 4)
                lx, ly = self._along(pts, frac)
                t["x"], t["y"] = sx + lx - t["width"] / 2, sy + ly - t["height"] / 2

    def to_scene(self):
        self._route()
        return {
            "type": "excalidraw", "version": 2, "source": "excalidraw.py",
            "elements": self.els,
            "appState": {"viewBackgroundColor": self.bg, "gridSize": None, "theme": self.theme,
                         "currentItemFontFamily": FONT_NUNITO},
            "files": {},
        }

    def save(self, path):
        with open(path, "w") as f:
            json.dump(self.to_scene(), f, indent=2)
        n_arrows = sum(1 for e in self.els if e["type"] == "arrow")
        print(f"wrote {path}  ({len(self.els)} elements, {n_arrows} arrows)")
        return path
