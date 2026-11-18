#!/usr/bin/env python3
"""Build the profile README cards in assets/ (one light and one dark SVG each).

The look follows Motionfolio's "warm editorial neo-brutalism": cream paper, ink borders,
hard offset shadows, terracotta accents, Outfit for display and Space Mono for labels.
Fonts are subset to the glyphs each card uses and embedded, so the SVGs make no network
requests. Every animation stops under prefers-reduced-motion.

    pip install fonttools brotli pillow
    python3 scripts/build_cards.py --fonts DIR --shots DIR --icons DIR

--fonts: a folder holding outfit-latin-{400,700,800,900}-normal.woff2 and
         space-mono-latin-{400,700}-normal.woff2 (from @fontsource/outfit, @fontsource/space-mono)
--shots: Motionfolio's docs/images folder (for the screenshot in the Motionfolio card)
--icons: an unpacked simple-icons package (npm pack simple-icons; CC0), for the logo grid
"""

from __future__ import annotations

import argparse
import base64
import io
from pathlib import Path
from xml.sax.saxutils import escape

from fontTools import subset
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

OUT = Path(__file__).resolve().parent.parent / "assets"

# ---------------------------------------------------------------------------- palette

LIGHT = dict(
    name="light",
    paper="#FAF6EE", card="#FFFDF8", warm="#F3E9DA", sand="#EDE4CD",
    ink="#1C1917", muted="#57534E", faint="#6B635E", rule="#1C1917", hair="#E4DACB",
    accent="#E05A36", accent_text="#B23F1C", accent_soft="#FCECE6",
    sage="#6C7D64", sage_text="#4F5E48", sage_soft="#E3EAD9", ok="#0B6B4A",
    shadow="#1C1917", dots="#D9CDBB",
    panel="#1C1917", panel_raised="#2A2522", panel_text="#FAF6EE", panel_muted="#A8A29E",
    panel_line="#4A433E",
)
DARK = dict(
    name="dark",
    paper="#1C1917", card="#24201D", warm="#2E2925", sand="#3A332E",
    ink="#FAF6EE", muted="#D6CFC6", faint="#A8A29E", rule="#FAF6EE", hair="#3E3732",
    accent="#E86A47", accent_text="#F2896A", accent_soft="#3A2620",
    sage="#93A589", sage_text="#B5C4AB", sage_soft="#2C3328", ok="#6FCF9F",
    shadow="#E05A36", dots="#3A332E",
    panel="#120F0D", panel_raised="#2A2522", panel_text="#FAF6EE", panel_muted="#A8A29E",
    panel_line="#4A433E",
)

FALLBACK = {
    "O9": "'Outfit','Arial Black','Helvetica Neue',Arial,sans-serif",
    "O8": "'Outfit','Helvetica Neue',Arial,sans-serif",
    "O7": "'Outfit','Helvetica Neue',Arial,sans-serif",
    "O4": "'Outfit',-apple-system,'Segoe UI',Helvetica,Arial,sans-serif",
    "M4": "'Space Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace",
    "M7": "'Space Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace",
}
WEIGHT = {"O9": 900, "O8": 800, "O7": 700, "O4": 400, "M4": 400, "M7": 700}
FONT_FILES = {
    "O9": "outfit-latin-900-normal.woff2",
    "O8": "outfit-latin-800-normal.woff2",
    "O7": "outfit-latin-700-normal.woff2",
    "O4": "outfit-latin-400-normal.woff2",
    "M4": "space-mono-latin-400-normal.woff2",
    "M7": "space-mono-latin-700-normal.woff2",
}

FONTS: dict[str, TTFont] = {}
FONT_BYTES: dict[str, bytes] = {}


def load_fonts(folder: Path) -> None:
    for key, name in FONT_FILES.items():
        data = (folder / name).read_bytes()
        FONT_BYTES[key] = data
        FONTS[key] = TTFont(io.BytesIO(data))


def measure(s: str, font: str, size: float, ls: float = 0.0) -> float:
    f = FONTS[font]
    cmap = f.getBestCmap()
    hmtx = f["hmtx"]
    upm = f["head"].unitsPerEm
    w = 0
    for ch in s:
        g = cmap.get(ord(ch)) or cmap.get(ord("?"))
        w += hmtx[g][0]
    return w * size / upm + ls * size * len(s)


def wrap(s: str, font: str, size: float, width: float) -> list[str]:
    lines, cur = [], ""
    for word in s.split(" "):
        test = (cur + " " + word).strip()
        if cur and measure(test, font, size) > width:
            lines.append(cur)
            cur = word
        else:
            cur = test
    if cur:
        lines.append(cur)
    return lines


# ---------------------------------------------------------------------------- svg builder

CSS = """
.rise{transform-box:fill-box;animation:rise .9s cubic-bezier(.16,1,.3,1) both}
.fade{animation:fade .8s ease-out both}
.grow{transform-box:fill-box;transform-origin:left center;animation:grow 1.1s cubic-bezier(.16,1,.3,1) both}
.beacon{transform-box:fill-box;transform-origin:center;animation:beacon 2.4s ease-out 3}
.blink{animation:blink 1.1s steps(2,start) infinite}
.marq{animation:marq 26s linear infinite}
@keyframes rise{from{opacity:0;transform:translateY(28px)}to{opacity:1;transform:none}}
@keyframes fade{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
@keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}
@keyframes beacon{0%{opacity:.7;transform:scale(1)}80%,100%{opacity:0;transform:scale(2.8)}}
@keyframes blink{to{visibility:hidden}}
.show{animation:show .7s cubic-bezier(.22,1,.36,1) both}
.lift{animation:lift 1s cubic-bezier(.22,1,.36,1) both}
@keyframes show{from{opacity:0}to{opacity:1}}
@keyframes lift{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
"""
REDUCED = "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"

PLAYS = 5  # how many times each diagram plays before it rests
GROVE_PHONE_H, WORK_PHONE_H, MF_PHONE_H = 1010, 725, 980  # heights of the phone-layout cards


def finite_loops(s: "Svg", rest: float) -> None:
    """Make this card's diagram play PLAYS times, then hold still. The last play stops at
    `rest` (a fraction of the loop) and keeps that frame, so each diagram comes to rest on
    its finished state (scores filled, order received, write committed) rather than blank."""
    s.extra_css = s.extra_css.replace(" infinite", f" {PLAYS - 1 + rest:g} forwards")


def spring_keyframes(name: str, dur: float = 1.25, samples: int = 48,
                     zeta: float = 0.62, omega: float = 8.5, depth: float = 112.0) -> str:
    """One continuous damped spring, sampled finely and played back linearly.

    Chaining eased keyframes makes the letter brake to a near stop at every turn of the
    bounce (each segment eases out on its own), which reads as jitter. Sampling a real
    spring keeps speed continuous through rise, overshoot and settle. Squash and stretch
    follow the spring on one smooth curve: stretched while it rises, squashed at the
    overshoot, volume kept."""
    import math
    wd = omega * math.sqrt(1 - zeta * zeta)
    t_peak = math.pi / wd  # when the overshoot tops out
    frames = []
    for k in range(samples + 1):
        tt = dur * k / samples
        x = 1 - math.exp(-zeta * omega * tt) * (math.cos(wd * tt) + zeta * omega / wd * math.sin(wd * tt))
        # smooth in time: stretched (1.22) at the start, a soft squash pulse at the overshoot
        sy = 1 + 0.22 * (1 - x) - 0.06 * math.exp(-((tt - t_peak) / 0.11) ** 2)
        sx = 1 / math.sqrt(sy)
        ty = (1 - x) * depth
        if k == samples:
            frames.append("100%{transform:none}")
        else:
            frames.append(f"{100 * k / samples:.3g}%{{transform:translateY({ty:.2f}%) "
                          f"scale({sx:.4f},{sy:.4f})}}")
    return (f".{name}{{transform-box:fill-box;transform-origin:50% 100%;"
            f"animation:{name} {dur}s linear both}}@keyframes {name}{{{''.join(frames)}}}")


class Svg:
    def __init__(self, w: int, h: int, label: str, theme: dict):
        self.w, self.h, self.label, self.t = w, h, label, theme
        self.parts: list[str] = []
        self.used: dict[str, set[str]] = {k: set() for k in FONT_FILES}
        self.extra_css = ""
        self.defs: list[str] = []
        self.paths = False          # draw text as glyph outlines instead of <text>
        self.fp = ""                # font-family prefix; unique per card when cards are composed
        self.glyphs: set[str] = set()

    def add(self, s: str) -> None:
        self.parts.append(s)

    def text(self, x, y, s, font="O4", size=16, fill=None, anchor="start", ls=0.0,
             cls="", style="", fit=None, extra="", per_glyph=None):
        fill = fill or self.t["ink"]
        if self.paths:
            return self.outline(x, y, s, font, size, fill, anchor, ls, cls, style, per_glyph)
        self.used[font].update(s)
        a = f' text-anchor="{anchor}"' if anchor != "start" else ""
        l = f' letter-spacing="{ls * size:.2f}"' if ls else ""
        c = f' class="{cls}"' if cls else ""
        st = f' style="{style}"' if style else ""
        tl = f' textLength="{fit:.1f}" lengthAdjust="spacingAndGlyphs"' if fit else ""
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{self.fp}{font}, {FALLBACK[font]}" '
                 f'font-weight="{WEIGHT[font]}" font-size="{size}" fill="{fill}"{a}{l}{c}{st}{tl}{extra}>'
                 f"{escape(s)}</text>")

    def glyph_id(self, font: str, ch: str) -> str:
        f = FONTS[font]
        name = f.getBestCmap().get(ord(ch))
        gid = f"{font}-{name}"
        if gid not in self.glyphs:
            self.glyphs.add(gid)
            pen = SVGPathPen(f.getGlyphSet(), ntos=lambda v: f"{round(v)}")
            f.getGlyphSet()[name].draw(pen)
            self.defs.append(f'<path id="{gid}" d="{pen.getCommands()}"/>')
        return gid

    def outline(self, x, y, s, font, size, fill, anchor, ls, cls, style, per_glyph):
        """Text as <use> references to glyph paths: no font loading, no pixel snapping,
        so it can move smoothly. per_glyph=(class, first_delay, step) animates each letter."""
        f = FONTS[font]
        k = size / f["head"].unitsPerEm
        cmap, hmtx = f.getBestCmap(), f["hmtx"]
        width = measure(s, font, size, ls)
        x0 = x - (width / 2 if anchor == "middle" else width if anchor == "end" else 0)
        c = f' class="{cls}"' if cls else ""
        st = f' style="{style}"' if style else ""
        out = [f'<g fill="{fill}"{c}{st}>']
        cx, n = x0, 0
        for ch in s:
            name = cmap.get(ord(ch))
            adv = hmtx[name][0] * k + ls * size
            if ch != " ":
                use = (f'<use xlink:href="#{self.glyph_id(font, ch)}" '
                       f'transform="translate({cx:.2f} {y:.2f}) scale({k:.5f} {-k:.5f})"/>')
                if per_glyph:
                    pc, d0, step = per_glyph
                    use = f'<g class="{pc}" style="animation-delay:{d0 + n * step:.3f}s">{use}</g>'
                    n += 1
                out.append(use)
            cx += adv
        self.add("".join(out) + "</g>")

    def para(self, x, y, s, font, size, width, lh, fill=None, cls="", style=""):
        lines = wrap(s, font, size, width)
        for i, line in enumerate(lines):
            self.text(x, y + i * lh, line, font, size, fill, cls=cls, style=style)
        return y + (len(lines) - 1) * lh

    def box(self, x, y, w, h, r=16, fill=None, stroke=None, sw=2.5, shadow=None, off=6,
            cls="", style=""):
        t = self.t
        fill = fill or t["card"]
        stroke = stroke or t["rule"]
        c = f' class="{cls}"' if cls else ""
        st = f' style="{style}"' if style else ""
        g = f"<g{c}{st}>"
        if shadow is not False:
            g += (f'<rect x="{x + off:.1f}" y="{y + off:.1f}" width="{w:.1f}" height="{h:.1f}" '
                  f'rx="{r}" fill="{shadow or t["shadow"]}"/>')
        g += (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{r}" '
              f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
        self.add(g + "</g>")

    def pill(self, x, y, s, font="M7", size=12, fill=None, color=None, stroke=None, pad=12,
             h=28, ls=0.08, r=None):
        t = self.t
        w = measure(s, font, size, ls) + pad * 2
        r = h / 2 if r is None else r
        self.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h}" rx="{r}" '
                 f'fill="{fill or t["card"]}" stroke="{stroke or t["rule"]}" stroke-width="1.5"/>')
        self.text(x + pad, y + h / 2 + size * 0.36, s, font, size, color or t["ink"], ls=ls)
        return w

    def kicker(self, x, y, s, color=None, dot=True, size=13):
        t = self.t
        if dot:
            self.add(f'<circle cx="{x + 5}" cy="{y - 4.5}" r="5" fill="{t["accent"]}"/>')
            self.add(f'<circle cx="{x + 5}" cy="{y - 4.5}" r="5" fill="{t["accent"]}" class="beacon"/>')
            x += 20
        self.text(x, y, s, "M7", size, color or t["ink"], ls=0.12)

    def tags(self, x, y, items, maxw, size=12, h=28, gap=8, fill=None, color=None):
        cx, cy = x, y
        for it in items:
            w = measure(it, "M7", size, 0.06) + 24
            if cx + w > x + maxw:
                cx, cy = x, cy + h + gap
            self.pill(cx, cy, it, size=size, h=h, ls=0.06, fill=fill, color=color)
            cx += w + gap
        return cy + h

    def font_css(self) -> str:
        out = []
        for key, chars in self.used.items():
            if not chars:
                continue
            opts = subset.Options()
            opts.flavor = "woff2"
            opts.layout_features = ["kern", "liga"]
            opts.name_IDs = []
            opts.notdef_outline = True
            sub = subset.Subsetter(opts)
            font = TTFont(io.BytesIO(FONT_BYTES[key]))
            sub.populate(text="".join(sorted(chars)) + " ")
            sub.subset(font)
            buf = io.BytesIO()
            font.flavor = "woff2"
            font.recalcTimestamp = False  # same input, same bytes: no churn on rebuilds
            font["head"].modified = font["head"].created
            font.save(buf)
            b64 = base64.b64encode(buf.getvalue()).decode()
            out.append(f"@font-face{{font-family:{self.fp}{key};font-weight:{WEIGHT[key]};"
                       f"src:url(data:font/woff2;base64,{b64}) format('woff2')}}")
        return "".join(out)

    def render(self) -> str:
        lab = escape(self.label, {'"': "&quot;"})
        defs = f"<defs>{''.join(self.defs)}</defs>" if self.defs else ""
        return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
                f'width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}" role="img" '
                f'aria-label="{lab}">\n<title>{escape(self.label)}</title>\n'
                f"<style>{self.font_css()}{CSS}{self.extra_css}{REDUCED}</style>\n{defs}\n"
                + "\n".join(self.parts) + "\n</svg>\n")


def save(name: str, build, label: str, w: int, h: int) -> None:
    for theme in (LIGHT, DARK):
        s = Svg(w, h, label, theme)
        build(s, theme)
        (OUT / f"{name}-{theme['name']}.svg").write_text(s.render(), encoding="utf-8")
        print(f"  {name}-{theme['name']}.svg  {len(s.render()) / 1024:.1f} kB")


def save_composed(name: str, label: str, layouts: dict) -> None:
    """Several cards in one SVG, once per layout: {layout: (builders, w, h, cols, gap)}.
    A wide layout (cards side by side) and a phone layout (cards stacked, possibly drawn in
    a narrower portrait shape) are both written; the README picks one with <picture> media
    queries, so the cards stay readable on a phone without changing the desktop look."""
    for theme in (LIGHT, DARK):
        for lname, (parts, w, h, cols, gap) in layouts.items():
            docs = []
            for i, build in enumerate(parts):
                c = Svg(w, h, label, theme)
                c.fp = f"c{i}"
                build(c, theme)
                docs.append(c.render())
            rows = -(-len(docs) // cols)
            W, H = cols * w + (cols - 1) * gap, rows * h + (rows - 1) * gap
            body = []
            for i, d in enumerate(docs):
                x, y = (i % cols) * (w + gap), (i // cols) * (h + gap)
                body.append(d.replace("<svg ", f'<svg x="{x}" y="{y}" ', 1))
            out = (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
                   f'width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
                   f'aria-label="{escape(label, {chr(34): "&quot;"})}">\n<title>{escape(label)}</title>\n'
                   + "".join(body) + "</svg>\n")
            (OUT / f"{name}-{lname}-{theme['name']}.svg").write_text(out, encoding="utf-8")
            print(f"  {name}-{lname}-{theme['name']}.svg  {len(out) / 1024:.1f} kB")


def dot_grid(s: Svg, x, y, w, h, gap=22):
    pid = f"dots-{s.t['name']}"
    s.defs.append(f'<pattern id="{pid}" width="{gap}" height="{gap}" patternUnits="userSpaceOnUse">'
                  f'<circle cx="2" cy="2" r="1.3" fill="{s.t["dots"]}"/></pattern>')
    s.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="url(#{pid})"/>')


# ---------------------------------------------------------------------------- cards

def header(s: Svg, t: dict):
    W, H = s.w, s.h
    s.paths = True
    s.box(3, 3, W - 14, H - 14, r=26, fill=t["paper"], off=8)
    s.add(f'<clipPath id="hc"><rect x="5" y="5" width="{W - 18}" height="{H - 18}" rx="24"/></clipPath>')
    s.add('<g clip-path="url(#hc)">')
    dot_grid(s, 5, 5, W - 18, H - 18)
    s.add("</g>")

    s.kicker(56, 70, "SOFTWARE DEVELOPER · BENGALURU, INDIA · @RRUSHIKESHP89")
    # each letter springs up out of its own line, like jelly settling
    s.extra_css += spring_keyframes("jelly")
    s.add(f'<clipPath id="l1"><rect x="0" y="0" width="{W}" height="190"/></clipPath>'
          f'<clipPath id="l2"><rect x="0" y="190" width="{W}" height="104"/></clipPath>')
    s.add('<g clip-path="url(#l1)">')
    s.text(50, 186, "RUSHIKESH", "O9", 116, t["ink"], ls=-0.01, per_glyph=("jelly", 0.3, 0.045))
    s.add('</g><g clip-path="url(#l2)">')
    s.text(50, 290, "PANCHAL", "O9", 116, t["accent"], ls=-0.01, per_glyph=("jelly", 0.55, 0.045))
    s.add("</g>")
    s.add(f'<rect x="56" y="318" width="640" height="2.5" fill="{t["rule"]}" class="grow" '
          f'style="animation-delay:.8s"/>')
    s.text(56, 352, "I build software that can explain itself.", "O7", 22, t["ink"], cls="show",
           style="animation-delay:.95s")
    s.text(56, 382, "Full-stack TypeScript · server-side access control · explainable AI",
           "O4", 18, t["muted"], cls="show", style="animation-delay:1.05s")

    # right: a tilted "whoami" inspector
    px, py, pw_, ph = 792, 64, 350, 300
    s.add(f'<g transform="rotate(-2.2 {px + pw_ / 2} {py + ph / 2})"><g class="lift" '
          f'style="animation-delay:.7s">')
    s.box(px, py, pw_, ph, r=18, fill=t["card"], off=7)
    s.add(f'<line x1="{px}" y1="{py + 46}" x2="{px + pw_}" y2="{py + 46}" stroke="{t["rule"]}" stroke-width="2"/>')
    for i, c in enumerate([t["accent"], t["sand"], t["sage"]]):
        s.add(f'<circle cx="{px + 24 + i * 18}" cy="{py + 23}" r="5.5" fill="{c}" stroke="{t["rule"]}" stroke-width="1.5"/>')
    s.text(px + pw_ - 20, py + 28, "whoami.ts", "M7", 13, t["faint"], anchor="end", ls=0.04)
    rows = [
        ("role", "Software Developer"),
        ("stack", "Next.js · Node · Postgres"),
        ("focus", "RBAC · integrity · XAI"),
        ("degree", "B.Tech CSE (Data Sci.)"),
        ("tests", "unit · e2e · axe"),
    ]
    for i, (k, v) in enumerate(rows):
        yy = py + 86 + i * 36
        s.text(px + 24, yy, k, "M4", 14, t["accent_text"])
        s.text(px + 104, yy, v, "M4", 14, t["ink"])
    yy = py + 86 + 5 * 36 + 8
    s.add(f'<rect x="{px + 20}" y="{yy - 22}" width="{pw_ - 40}" height="34" rx="17" '
          f'fill="{t["sage_soft"]}" stroke="{t["rule"]}" stroke-width="1.5"/>')
    s.add(f'<circle cx="{px + 40}" cy="{yy - 5}" r="5" fill="{t["ok"]}"/>')
    s.add(f'<circle cx="{px + 40}" cy="{yy - 5}" r="5" fill="{t["ok"]}" class="beacon"/>')
    s.text(px + 54, yy, "OPEN TO SOFTWARE DEVELOPER ROLES", "M7", 11.5, t["sage_text"] if t["name"] == "light" else t["ok"], ls=0.06)
    s.add("</g></g>")


def stats(s: Svg, t: dict):
    items = [
        ("8", "PUBLIC PROJECTS"),
        ("6", "LIVE SITES"),
        ("130+", "TESTS ON GROVE"),
        ("100×4", "LIGHTHOUSE · MOTIONFOLIO"),
    ]
    gap, x0, w = 22, 3, (s.w - 14 - 3 * 22) / 4
    for i, (n, lab) in enumerate(items):
        x = x0 + i * (w + gap)
        fill = t["accent_soft"] if i == 3 else t["card"]
        s.box(x, 3, w, s.h - 14, r=18, fill=fill, off=6, cls="fade", style=f"animation-delay:{i * .08:.2f}s")
        s.text(x + 26, 82, n, "O8", 56, t["accent"] if i == 3 else t["ink"], cls="fade",
               style=f"animation-delay:{i * .08:.2f}s")
        s.add(f'<rect x="{x + 26}" y="{100}" width="44" height="4" rx="2" fill="{t["accent"]}" '
              f'class="grow" style="animation-delay:{.3 + i * .08:.2f}s"/>')
        s.text(x + 26, 132, lab, "M7", 12.5, t["muted"], ls=0.1)


def motionfolio(s: Svg, t: dict, shot_b64: str):
    W, H = s.w, s.h
    s.box(3, 3, W - 14, H - 14, r=26, fill=t["card"], off=8)
    s.kicker(48, 66, "NEW  ·  NOV 2026  ·  MOTION PORTFOLIO")
    s.text(44, 132, "Motionfolio", "O8", 64, t["ink"], ls=-0.02)
    y = s.para(48, 176, "My animated portfolio. Kinetic type, a live RBAC simulator, 3D tilt cards "
               "and a write path that traces itself, all in CSS and the browser's Web Animations "
               "API, with no animation library.", "O4", 18, 520, 27, t["muted"])
    rows = [
        ("100 · 100 · 100 · 100", "Lighthouse mobile"),
        ("147.2 kB", "of JavaScript, under a 150 kB budget"),
        ("113 tests", "61 unit and 52 end-to-end, with axe"),
        ("0 requests", "to third parties: strict CSP"),
    ]
    yy = y + 50
    for i, (a, b) in enumerate(rows):
        s.add(f'<rect x="48" y="{yy - 15}" width="10" height="10" fill="{t["accent"]}" class="fade" '
              f'style="animation-delay:{.2 + i * .1:.1f}s"/>')
        s.text(72, yy - 4, a, "M7", 15, t["ink"])
        s.text(72 + measure(a, "M7", 15) + 12, yy - 4, b, "O4", 16, t["muted"])
        yy += 34
    s.tags(48, yy + 6, ["NEXT.JS 16", "REACT 19", "TAILWIND V4", "WAAPI", "PLAYWRIGHT + AXE"], 560,
           size=11.5, h=26)
    # url bar
    s.add(f'<rect x="48" y="{H - 82}" width="{W - 110}" height="2" fill="{t["hair"]}"/>')
    s.text(48, H - 44, "rrushikeshp89.github.io/motionfolio  ↗", "M7", 15, t["accent_text"], ls=0.02)
    s.text(W - 62, H - 44, "ALSO: THE FULL PORTFOLIO AT RRUSHIKESHP89.GITHUB.IO", "M4", 12, t["faint"],
           anchor="end", ls=0.08)

    # right: browser frame with a real screenshot, and the LIVE sticker
    browser_shot(s, t, shot_b64, 640, 58, 500, 356, 1.6)
    live_sticker(s, t, 1085, 410)


def browser_shot(s: Svg, t: dict, shot_b64: str, bx, by, bw, bh, rot):
    """A tilted browser window holding the Motionfolio screenshot."""
    s.add(f'<g transform="rotate({rot} {bx + bw / 2} {by + bh / 2})"><g class="fade" style="animation-delay:.2s">')
    s.box(bx, by, bw, bh, r=16, fill=t["paper"], off=8)
    s.add(f'<line x1="{bx}" y1="{by + 38}" x2="{bx + bw}" y2="{by + 38}" stroke="{t["rule"]}" stroke-width="2"/>')
    for i, c in enumerate([t["accent"], t["sand"], t["sage"]]):
        s.add(f'<circle cx="{bx + 20 + i * 16}" cy="{by + 19}" r="5" fill="{c}" stroke="{t["rule"]}" stroke-width="1.5"/>')
    s.add(f'<rect x="{bx + 82}" y="{by + 9}" width="{bw - 102}" height="20" rx="10" fill="{t["card"]}" '
          f'stroke="{t["rule"]}" stroke-width="1.2"/>')
    s.text(bx + 96, by + 23.5, "rrushikeshp89.github.io/motionfolio", "M4", 10.5, t["faint"])
    s.add(f'<clipPath id="shot"><rect x="{bx + 1.5}" y="{by + 39}" width="{bw - 3}" height="{bh - 40.5}" '
          f'rx="0"/></clipPath>')
    ih = (bw - 3) * 1000 / 1600
    s.add(f'<image x="{bx + 1.5}" y="{by + 39}" width="{bw - 3}" height="{ih:.1f}" clip-path="url(#shot)" '
          f'preserveAspectRatio="xMidYMin slice" xlink:href="data:image/jpeg;base64,{shot_b64}"/>')
    s.add(f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="16" fill="none" stroke="{t["rule"]}" stroke-width="2.5"/>')
    s.add("</g></g>")


def live_sticker(s: Svg, t: dict, cx, cy):
    s.add(f'<g transform="rotate(-8 {cx} {cy})">')
    s.add(f'<rect x="{cx - 75}" y="{cy - 20}" width="150" height="40" rx="20" fill="{t["accent"]}" '
          f'stroke="{t["rule"]}" stroke-width="2"/>')
    s.text(cx, cy + 5.5, "LIVE ↗", "M7", 14, "#1C1917", anchor="middle", ls=0.12)
    s.add("</g>")


def motionfolio_phone(s: Svg, t: dict, shot_b64: str):
    """Phone layout: the screenshot on top, then the story, metrics and links, in a
    narrower card so the text stays readable at phone width."""
    W, H = s.w, s.h
    s.box(3, 3, W - 14, H - 14, r=26, fill=t["card"], off=8)
    browser_shot(s, t, shot_b64, 40, 40, 432, 300, 1.2)
    live_sticker(s, t, 400, 340)
    x = 38
    s.kicker(x, 412, "NEW  ·  NOV 2026  ·  MOTION PORTFOLIO", size=12)
    s.text(x - 4, 474, "Motionfolio", "O8", 58, t["ink"], ls=-0.02)
    y = s.para(x, 514, "My animated portfolio. Kinetic type, a live RBAC simulator, 3D tilt cards "
               "and a write path that traces itself, all in CSS and the browser's Web Animations "
               "API, with no animation library.", "O4", 18, W - 14 - 2 * x, 27, t["muted"])
    rows = [
        ("100 · 100 · 100 · 100", "Lighthouse mobile"),
        ("147.2 kB", "of JavaScript, under 150 kB"),
        ("113 tests", "61 unit, 52 end-to-end"),
        ("0 requests", "to third parties"),
    ]
    yy = y + 50
    for i, (a, b) in enumerate(rows):
        s.add(f'<rect x="{x}" y="{yy - 15}" width="10" height="10" fill="{t["accent"]}"/>')
        s.text(x + 24, yy - 4, a, "M7", 15, t["ink"])
        s.text(x + 24 + measure(a, "M7", 15) + 12, yy - 4, b, "O4", 16, t["muted"])
        yy += 34
    s.tags(x, yy + 6, ["NEXT.JS 16", "REACT 19", "TAILWIND V4", "WAAPI", "PLAYWRIGHT + AXE"],
           W - 14 - 2 * x, size=11.5, h=26)
    s.add(f'<rect x="{x}" y="{H - 104}" width="{W - 14 - 2 * x}" height="2" fill="{t["hair"]}"/>')
    s.text(x, H - 68, "rrushikeshp89.github.io/motionfolio  ↗", "M7", 15, t["accent_text"], ls=0.02)
    s.text(x, H - 40, "ALSO: THE FULL PORTFOLIO AT RRUSHIKESHP89.GITHUB.IO", "M4", 11, t["faint"], ls=0.06)


def project(s: Svg, t: dict, d: dict):
    """Generic project card. d: kicker, title, pitch, metrics[(strong, rest)], tags, url, visual."""
    W, H = s.w, s.h
    s.box(3, 3, W - 14, H - 14, r=24, fill=t["card"], off=7)
    pad = d.get("pad", 40)
    textw = d.get("textw", W - 14 - pad * 2)
    big = d.get("big", 46)
    top = 58 + d.get("top", 0)
    s.kicker(pad, top, d["kicker"])
    s.text(pad - 2, top + big + 14, d["title"], "O8", big, t["ink"], ls=-0.02)
    y = s.para(pad, top + big + 48, d["pitch"], "O4", d.get("ps", 17), textw, d.get("plh", 25), t["muted"])
    y += d.get("gap", 44)
    ms = d.get("ms", 15)
    for i, (a, b) in enumerate(d["metrics"]):
        s.add(f'<rect x="{pad}" y="{y - ms * .75}" width="9" height="9" fill="{t["accent"]}"/>')
        s.text(pad + 20, y, a, "M7", ms, t["ink"])
        if b:
            lx = pad + 20 + measure(a, "M7", ms) + 8
            avail = pad + 20 + textw - 22 - lx
            line, words = "", b.split(" ")
            while words and measure((line + " " + words[0]).strip(), "O4", ms + 1) <= avail:
                line = (line + " " + words.pop(0)).strip()
            if line:
                s.text(lx, y, line, "O4", ms + 1, t["muted"])
            if words:
                y += ms + 9
                y = s.para(pad + 20, y, " ".join(words), "O4", ms + 1, textw - 22, ms + 9, t["muted"])
        y += ms + d.get("mgap", 17)
    ty = s.tags(pad, y + 4, d["tags"], d.get("tagw", textw), size=d.get("ts", 11.5), h=26)
    s.add(f'<rect x="{pad}" y="{H - 70}" width="{W - 14 - pad * 2}" height="2" fill="{t["hair"]}"/>')
    s.text(pad, H - 38, d["url"], "M7", d.get("us", 14), t["accent_text"], ls=0.02)
    if d.get("band"):  # phone layouts: frame the diagram in a band above the text
        bx, by, bw, bh = d["band"]
        s.add(f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="12" fill="{t["paper"]}" '
              f'stroke="{t["rule"]}" stroke-width="1.8"/>')
    if d.get("visual"):
        dx, dy = d.get("vis_at", (0, 0))
        if dx or dy:
            s.add(f'<g transform="translate({dx} {dy})">')
        d["visual"](s, t)
        if dx or dy:
            s.add("</g>")


def v_rbac(s: Svg, t: dict):
    """Grove: a field-masking table that cycles through the roles."""
    x, y, w = 690, 48, 452
    s.box(x, y, w, 300, r=16, fill=t["paper"], off=6)
    s.text(x + 22, y + 34, "WHAT EACH ROLE CAN SEE", "M7", 12, t["faint"], ls=0.1)
    roles = ["EMPLOYEE", "MANAGER", "HR ADMIN"]
    fields = [("Name", (1, 1, 1)), ("Team", (1, 1, 1)), ("Salary", (0, 0, 1)),
              ("Bank details", (0, 0, 1)), ("Reviews", (0, 1, 1)), ("Leave balance", (1, 1, 1))]
    cx = [x + 186, x + 276, x + 376]
    # moving column highlight, one role at a time
    s.extra_css += ("@keyframes col{0%,30%{transform:translateX(0)}34%,63%{transform:translateX(90px)}"
                    "67%,96%{transform:translateX(190px)}100%{transform:translateX(0)}}"
                    ".col{animation:col 7.5s cubic-bezier(.65,0,.35,1) infinite}")
    s.add(f'<rect x="{cx[0] - 46}" y="{y + 50}" width="92" height="236" rx="10" fill="{t["accent_soft"]}" '
          f'stroke="{t["accent"]}" stroke-width="2" class="col"/>')
    for i, r in enumerate(roles):
        s.text(cx[i], y + 68, r, "M7", 11, t["ink"], anchor="middle", ls=0.06)
    for j, (f, vis) in enumerate(fields):
        yy = y + 104 + j * 31
        s.add(f'<line x1="{x + 20}" y1="{yy - 20}" x2="{x + w - 20}" y2="{yy - 20}" stroke="{t["hair"]}"/>')
        s.text(x + 22, yy, f, "O4", 15, t["ink"])
        for i, v in enumerate(vis):
            if v:
                s.add(f'<path d="M{cx[i] - 7} {yy - 5} l5 5 l9 -10" fill="none" stroke="{t["ok"]}" '
                      f'stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>')
            else:
                s.add(f'<rect x="{cx[i] - 22}" y="{yy - 12}" width="44" height="12" rx="3" fill="{t["sand"]}"/>')
    s.text(x + 22, y + 330, "checked on the server, not just hidden in the UI", "M4", 12, t["faint"])
    finite_loops(s, 0.9)


def v_states(s: Svg, t: dict):
    """Stockroom: the purchase-order state machine that lives in the database.
    A token walks the order through each state; RECEIVED commits, then a duplicate
    receive bounces off with a 409. With no animation it shows the finished state."""
    x, y, P = 316, 150, 7
    steps = ["DRAFT", "APPROVAL", "ORDERED", "RECEIVED"]
    soft, acc, paper, rule, ink = t["accent_soft"], t["accent"], t["paper"], t["rule"], t["ink"]
    s.extra_css += (
        f"@keyframes poOn{{0%,12%{{fill:{soft};stroke:{acc}}}13.5%,100%{{fill:{paper};stroke:{rule}}}}}"
        f".po{{animation:poOn {P}s ease-in-out infinite}}"
        f"@keyframes poRecv{{0%,41%{{fill:{paper}}}42%,95%{{fill:{acc}}}100%{{fill:{paper}}}}}"
        f".po-recv{{animation:poRecv {P}s ease-in-out infinite}}"
        f"@keyframes poRecvText{{0%,41%{{fill:{ink}}}42%,95%{{fill:#1C1917}}100%{{fill:{ink}}}}}"
        f".po-recv-text{{animation:poRecvText {P}s ease-in-out infinite}}"
        "@keyframes poPop{0%,41%{transform:scale(1)}44.5%{transform:scale(1.05)}48%,100%{transform:scale(1)}}"
        f".po-pop{{transform-box:fill-box;transform-origin:center;animation:poPop {P}s cubic-bezier(.34,1.56,.64,1) infinite}}"
        "@keyframes poToken{0%{opacity:0;transform:translateY(0)}3%,10%{opacity:1;transform:translateY(0)}"
        "14%,24%{transform:translateY(40px)}28%,38%{transform:translateY(80px)}"
        "42%,90%{opacity:1;transform:translateY(120px)}95%,100%{opacity:0;transform:translateY(120px)}}"
        f".po-token{{animation:poToken {P}s cubic-bezier(.65,0,.35,1) infinite}}"
        "@keyframes poGhost{0%,52%{opacity:0;transform:translateY(80px)}54%{opacity:1;transform:translateY(80px)}"
        "58%{transform:translateY(112px)}62%{transform:translateY(90px)}66%{transform:translateY(102px)}"
        "70%{opacity:1;transform:translateY(96px)}76%,100%{opacity:0;transform:translateY(96px)}}"
        f".po-ghost{{animation:poGhost {P}s cubic-bezier(.34,1.3,.64,1) infinite}}"
        "@keyframes poErr{0%,57%{opacity:0;transform:none}58%{opacity:1}60%{transform:translateX(-3px)}"
        "62%{transform:translateX(3px)}64%{transform:translateX(-2px)}66%{transform:translateX(1px)}"
        "68%,90%{opacity:1;transform:none}94%,100%{opacity:0}}"
        f".po-err{{animation:poErr {P}s ease-out infinite}}"
    )
    s.text(x, y - 18, "PO LIFECYCLE · DB TRIGGER", "M7", 10.5, t["faint"], ls=0.08)
    for i, st in enumerate(steps):
        yy = y + i * 40
        if i < 3:
            s.add(f'<rect x="{x}" y="{yy}" width="230" height="30" rx="8" fill="{paper}" stroke="{rule}" '
                  f'stroke-width="1.8" class="po" style="animation-delay:{i * P * .14:.2f}s"/>')
            s.text(x + 14, yy + 20, f"0{i + 1}  {st}", "M7", 12, ink, ls=0.06)
            s.add(f'<path d="M{x + 115} {yy + 31} v8" stroke="{rule}" stroke-width="1.8"/>')
        else:
            s.add('<g class="po-pop">')
            s.add(f'<rect x="{x}" y="{yy}" width="230" height="30" rx="8" fill="{acc}" stroke="{rule}" '
                  f'stroke-width="1.8" class="po-recv"/>')
            s.text(x + 14, yy + 20, f"0{i + 1}  {st}", "M7", 12, "#1C1917", ls=0.06, cls="po-recv-text")
            s.text(x + 216, yy + 20, "409 if twice", "M4", 10.5, "#1C1917", anchor="end", cls="po-err")
            s.add("</g>")
    # the order token, and the duplicate receive that gets refused
    tx, ty = x - 14, y + 15
    s.add(f'<circle cx="{tx}" cy="{ty}" r="5" fill="{acc}" stroke="{rule}" stroke-width="1.5" '
          f'class="po-token" opacity="0"/>')
    s.add(f'<circle cx="{tx}" cy="{ty}" r="5" fill="{t["card"]}" stroke="{acc}" stroke-width="2" '
          f'class="po-ghost" opacity="0"/>')
    finite_loops(s, 0.88)


def v_pipeline(s: Svg, t: dict):
    """LeadHub: a weighted pipeline. A deal sweeps through each stage in turn, then the
    Won bar grows and a +1 pops. With no animation it shows the static pipeline."""
    x, y, P = 330, 140, 6
    s.text(x, y - 8, "WEIGHTED PIPELINE", "M7", 10.5, t["faint"], ls=0.08)
    vals = [(0.92, "New"), (0.74, "Contacted"), (0.58, "Discovery"), (0.40, "Proposal"), (0.24, "Won")]
    s.extra_css += (
        "@keyframes lhWon{0%,40%{transform:scaleX(1)}46%{transform:scaleX(1.75)}50%{transform:scaleX(1.55)}"
        "54%,90%{transform:scaleX(1.62)}97%,100%{transform:scaleX(1)}}"
        f".lh-won{{transform-box:fill-box;transform-origin:left center;animation:lhWon {P}s cubic-bezier(.34,1.56,.64,1) infinite}}"
        "@keyframes lhPlus{0%,45%{opacity:0;transform:translateY(5px)}50%,84%{opacity:1;transform:none}"
        "92%,100%{opacity:0;transform:translateY(-3px)}}"
        f".lh-plus{{animation:lhPlus {P}s cubic-bezier(.22,1,.36,1) infinite}}"
    )
    for i, (v, lab) in enumerate(vals):
        yy = y + 8 + i * 30
        w = 207 * v
        s.add(f'<rect x="{x}" y="{yy}" width="210" height="18" rx="4" fill="{t["paper"]}" stroke="{t["rule"]}" stroke-width="1.5"/>')
        fill = t["accent"] if i == 4 else ("#B7C4AD" if t["name"] == "light" else t["sage"])
        bar = (f'<rect x="{x + 1.5}" y="{yy + 1.5}" width="{w:.1f}" height="15" rx="3" fill="{fill}" '
               f'class="grow" style="animation-delay:{.2 + i * .1:.1f}s"/>')
        s.add(f'<g class="lh-won">{bar}</g>' if i == 4 else bar)
        # a soft highlight that sweeps along this stage's fill
        dist = max(w - 24, 8)
        s.extra_css += (f"@keyframes lhSweep{i}{{0%{{opacity:0;transform:translateX(0)}}3%{{opacity:.6}}"
                        f"13%{{opacity:.6;transform:translateX({dist:.0f}px)}}16%,100%{{opacity:0;"
                        f"transform:translateX({dist:.0f}px)}}}}"
                        f".lh-s{i}{{animation:lhSweep{i} {P}s cubic-bezier(.45,0,.55,1) infinite;"
                        f"animation-delay:{i * .5:.1f}s}}")
        s.add(f'<rect x="{x + 1.5}" y="{yy + 1.5}" width="24" height="15" rx="3" fill="#FFFFFF" '
              f'opacity="0" class="lh-s{i}"/>')
        s.text(x + 8, yy + 13.5, lab, "M7", 10, "#1C1917")
        if i == 4:
            s.text(x + 118, yy + 13.5, "+1 WON", "M7", 10, t["accent_text"], ls=0.06,
                   cls="lh-plus", extra=' opacity="0"')
    finite_loops(s, 0.8)


def band(s: Svg, t: dict, title: str):
    s.add(f'<rect x="30" y="30" width="326" height="132" rx="12" fill="{t["paper"]}" stroke="{t["rule"]}" stroke-width="1.8"/>')
    s.text(48, 56, title, "M7", 11, t["faint"], ls=0.1)


def kf(name: str, frames: list[tuple[float, str]]) -> str:
    """@keyframes from (percent, declarations) pairs."""
    return f"@keyframes {name}{{" + "".join(f"{p:g}%{{{d}}}" for p, d in frames) + "}"


def v_rank(s: Svg, t: dict):
    """Tessaract: each candidate's score builds up in four parts, one candidate after
    another, and the score pops in when its bar completes."""
    band(s, t, "RANK BY FIT")
    P = 6
    for i, (n, v) in enumerate([("Candidate A", .86), ("Candidate B", .79), ("Candidate C", .64)]):
        yy = 72 + i * 28
        s0 = 4 + i * 18
        steps = [(0, "transform:scaleX(0)"), (s0, "transform:scaleX(0)")]
        for k in range(4):
            steps += [(s0 + 4 * k + 3, f"transform:scaleX({(k + 1) / 4:g})"),
                      (s0 + 4 * k + 4, f"transform:scaleX({(k + 1) / 4:g})")]
        steps += [(92, "transform:scaleX(1)"), (97, "transform:scaleX(0)"), (100, "transform:scaleX(0)")]
        s.extra_css += (kf(f"tsF{i}", steps) + f".ts-f{i}{{transform-box:fill-box;transform-origin:left center;"
                        f"animation:tsF{i} {P}s cubic-bezier(.34,1.4,.64,1) infinite}}"
                        + kf(f"tsN{i}", [(0, "opacity:0;transform:translateY(4px)"),
                                         (s0 + 16, "opacity:0;transform:translateY(4px)"),
                                         (s0 + 19, "opacity:1;transform:none"), (92, "opacity:1"),
                                         (96, "opacity:0"), (100, "opacity:0")])
                        + f".ts-n{i}{{animation:tsN{i} {P}s cubic-bezier(.22,1,.36,1) infinite}}")
        s.text(48, yy + 12, n, "M4", 12, t["ink"])
        s.add(f'<rect x="150" y="{yy}" width="150" height="16" rx="4" fill="{t["card"]}" stroke="{t["rule"]}" stroke-width="1.4"/>')
        s.add(f'<g class="ts-f{i}"><rect x="151.5" y="{yy + 1.5}" width="{147 * v:.1f}" height="13" rx="3" '
              f'fill="{t["accent"] if i == 0 else t["sage"]}" class="grow" style="animation-delay:{.2 + i * .1:.1f}s"/></g>')
        s.text(338, yy + 12.5, f"{v:.2f}", "M7", 12, t["ink"], anchor="end", cls=f"ts-n{i}")
    finite_loops(s, 0.88)


def v_agents(s: Svg, t: dict):
    """StrategyRoom: the researcher works, hands off to the analyst, the verdict pops in
    and the caption writes itself."""
    band(s, t, "TWO AGENTS, ONE REPORT")
    P = 6.5
    soft, acc, card, rule = t["accent_soft"], t["accent"], t["card"], t["rule"]
    windows = [(2, 22), (24, 44)]
    for i, (a0, a1) in enumerate(windows):
        s.extra_css += (
            kf(f"srB{i}", [(0, f"fill:{card};stroke:{rule}"), (a0, f"fill:{card};stroke:{rule}"),
                           (a0 + 1.5, f"fill:{soft};stroke:{acc}"), (a1, f"fill:{soft};stroke:{acc}"),
                           (a1 + 2, f"fill:{card};stroke:{rule}"), (100, f"fill:{card};stroke:{rule}")])
            + f".sr-b{i}{{animation:srB{i} {P}s ease-in-out infinite}}"
            + kf(f"srP{i}", [(0, "opacity:0;transform:scaleX(0)"), (a0, "opacity:1;transform:scaleX(0)"),
                             (a1, "opacity:1;transform:scaleX(1)"), (a1 + 2, "opacity:0;transform:scaleX(1)"),
                             (100, "opacity:0;transform:scaleX(1)")])
            + f".sr-p{i}{{transform-box:fill-box;transform-origin:left center;"
              f"animation:srP{i} {P}s cubic-bezier(.45,0,.55,1) infinite}}")
    s.extra_css += (
        kf("srPop", [(0, "opacity:.35;transform:scale(1)"), (44, "opacity:.35;transform:scale(1)"),
                     (47, "opacity:1;transform:scale(1.14)"), (51, "transform:scale(.96)"),
                     (54, "transform:scale(1)"), (93, "opacity:1"), (100, "opacity:.35")])
        + f".sr-pop{{transform-box:fill-box;transform-origin:center;animation:srPop {P}s cubic-bezier(.34,1.56,.64,1) infinite}}"
        + kf("srCap", [(0, "opacity:1;transform:scaleX(1)"), (52, "opacity:1;transform:scaleX(1)"),
                       (70, "opacity:1;transform:scaleX(0)"), (71, "opacity:0;transform:scaleX(0)"),
                       (100, "opacity:0;transform:scaleX(0)")])
        + f".sr-cap{{transform-box:fill-box;transform-origin:right center;animation:srCap {P}s steps(24,end) infinite}}"
    )
    for i, (a, b) in enumerate([("RESEARCHER", "web + sources"), ("ANALYST", "gemini")]):
        x = 48 + i * 112
        s.add(f'<rect x="{x}" y="72" width="100" height="44" rx="8" fill="{card}" stroke="{rule}" '
              f'stroke-width="1.6" class="sr-b{i}"/>')
        s.text(x + 10, 91, a, "M7", 10.5, t["ink"], ls=0.04)
        s.text(x + 10, 107, b, "M4", 10.5, t["faint"])
        s.add(f'<rect x="{x + 8}" y="111" width="84" height="2.5" rx="1.25" fill="{acc}" opacity="0" class="sr-p{i}"/>')
        s.add(f'<path d="M{x + 101} 94 h10" stroke="{rule}" stroke-width="1.6"/>')
    s.add('<g class="sr-pop">')
    s.add(f'<rect x="272" y="72" width="66" height="44" rx="8" fill="{acc}" stroke="{rule}" stroke-width="1.6"/>')
    s.text(305, 91, "BUY", "M7", 10.5, "#1C1917", anchor="middle", ls=0.06)
    s.text(305, 107, "+ cites", "M4", 10.5, "#1C1917", anchor="middle")
    s.add("</g>")
    cap = "reasoning chain, citations, confidence"
    s.text(48, 144, cap, "M4", 11, t["faint"])
    # a paper-coloured cover that slides off the caption, typewriter-style
    w = measure(cap, "M4", 11) + 4
    s.add(f'<rect x="46" y="132" width="{w:.1f}" height="16" fill="{t["paper"]}" opacity="0" class="sr-cap"/>')
    finite_loops(s, 0.88)


def v_shap(s: Svg, t: dict):
    """Readmission Shield: the SHAP reasons spring out one by one, each label lighting
    up while its bar grows."""
    band(s, t, "WHY THIS PATIENT IS HIGH RISK")
    P = 7
    for i, (lab, v) in enumerate([("prior visits", .9), ("discharge to SNF", .62), ("age over 70", .42)]):
        yy = 72 + i * 28
        s0 = 4 + i * 14
        s.extra_css += (
            kf(f"rsF{i}", [(0, "transform:scaleX(0)"), (s0, "transform:scaleX(0)"),
                           (s0 + 6, "transform:scaleX(1.08)"), (s0 + 9, "transform:scaleX(.97)"),
                           (s0 + 11, "transform:scaleX(1)"), (92, "transform:scaleX(1)"),
                           (97, "transform:scaleX(0)"), (100, "transform:scaleX(0)")])
            + f".rs-f{i}{{transform-box:fill-box;transform-origin:left center;"
              f"animation:rsF{i} {P}s cubic-bezier(.22,1,.36,1) infinite}}"
            + kf(f"rsL{i}", [(0, f"fill:{t['ink']}"), (s0, f"fill:{t['ink']}"),
                             (s0 + 1, f"fill:{t['accent_text']}"), (s0 + 12, f"fill:{t['accent_text']}"),
                             (s0 + 15, f"fill:{t['ink']}"), (100, f"fill:{t['ink']}")])
            + f".rs-l{i}{{animation:rsL{i} {P}s ease-in-out infinite}}")
        s.text(48, yy + 12, lab, "M4", 12, t["ink"], cls=f"rs-l{i}")
        s.add(f'<g class="rs-f{i}"><rect x="190" y="{yy + 2}" width="{148 * v:.1f}" height="12" rx="3" '
              f'fill="{t["accent"]}" class="grow" style="animation-delay:{.2 + i * .1:.1f}s"/></g>')
    finite_loops(s, 0.88)


def principles(s: Svg, t: dict):
    rules = [
        ("SHOW THE WHY.", "Scores and decisions come with their reasons: SHAP reasons for every "
         "readmission score, weighted factors in résumé matching.", "EXPLAINABILITY"),
        ("ENFORCE IT ON THE SERVER.", "Permissions are checked where the data is written, so "
         "hiding a button is never the only safeguard.", "SERVER-SIDE ENFORCEMENT"),
        ("PROVE IT, THEN SAY WHAT'S MISSING.", "Claims ship with tests (unit, end-to-end, axe), "
         "and every project states what it does not do yet.", "STATED LIMITS"),
    ]
    gap, w = 24, (s.w - 14 - 2 * 24) / 3
    for i, (title, body, foot) in enumerate(rules):
        x = 3 + i * (w + gap)
        s.add(f'<g><g class="fade" style="animation-delay:{i * .1:.1f}s">')
        s.box(x, 3, w, 280, r=18, fill=t["card"], off=6)
        s.text(x + 26, 44, f"RULE // 0{i + 1}", "M7", 12.5, t["accent_text"], ls=0.1)
        lines = wrap(title, "O8", 25, w - 52)
        for k, ln in enumerate(lines):
            s.text(x + 26, 86 + k * 30, ln, "O8", 25, t["ink"], ls=-0.01)
        yy = 86 + (len(lines) - 1) * 30 + 36
        s.para(x + 26, yy, body, "O4", 16, w - 52, 24, t["muted"])
        s.add(f'<line x1="{x + 26}" y1="236" x2="{x + w - 26}" y2="236" stroke="{t["hair"]}" stroke-width="1.5"/>')
        s.text(x + 26, 262, foot, "M4", 11.5, t["ink"], ls=0.08)
        s.text(x + w - 26, 262, f"0{i + 1} / 03", "M4", 11.5, t["ink"], anchor="end", ls=0.06)
        s.add("</g></g>")

    # write path panel: a request travels the path; each step pops as it arrives and
    # stays lit, a trace line says what that step does, and the write commits at the end.
    # With no animation it shows the trace paused at step 03.
    py, ph = 316, 250
    if t["name"] == "dark":   # the original ink panel
        wp = dict(bg=t["panel"], text=t["panel_text"], muted=t["panel_muted"], base=t["panel_raised"],
                  line=t["panel_line"], rail=t["panel_line"], done="#3A2620", trace=t["accent"],
                  tok=t["panel_text"], ok="#6FCF9F", ok_text="#6FCF9F", check="#1C1917", cur_line=t["accent"])
    else:                     # light: cream paper, ink borders, like every other light card
        wp = dict(bg=t["paper"], text=t["ink"], muted=t["muted"], base=t["card"],
                  line=t["rule"], rail="#D9CDBB", done=t["accent_soft"], trace=t["accent_text"],
                  tok=t["ink"], ok="#0B6B4A", ok_text="#0B6B4A", check="#FFFFFF", cur_line=t["rule"])
    s.box(3, py, s.w - 14, ph, r=22, fill=wp["bg"], stroke=t["rule"], off=7)
    s.add(f'<circle cx="38" cy="{py + 40}" r="5" fill="{t["accent"]}"/>')
    s.text(52, py + 45, "GROVE HRMS WRITE PATH", "M7", 13, wp["text"], ls=0.1)
    s.text(36, py + 76, "Every write in Grove HRMS takes this path, and it is traced on the server.",
           "O4", 16, wp["muted"])
    steps = [
        ("INTERFACE", "The browser submits a form. Nothing it sends is trusted."),
        ("SERVER ACTION", "A Next.js server action receives it and authenticates the session."),
        ("PERMISSION", "Role, scope and record are checked on the server; hiding a button is never the only safeguard."),
        ("ZOD", "The input is validated with Zod before anything is written."),
        ("TRANSACTION", "The change, its audit entries and notifications commit or roll back together."),
        ("AUDIT LOG", "Every change records who did what, and when."),
        ("POSTGRES", "Postgres via Prisma, with row level security on and no public access."),
    ]
    n, STATIC = len(steps), 2
    sw_, sg = (s.w - 14 - 64 - (n - 1) * 12) / n, 12
    P, win = 11.2, 12.5                      # loop length (s), one step's share of it (%)
    base, line, acc, done = wp["base"], wp["line"], t["accent"], wp["done"]
    ease = "animation-timing-function:cubic-bezier(.45,0,.55,1)"
    xs = [35 + i * (sw_ + sg) for i in range(n)]
    cs = [x + sw_ / 2 for x in xs]
    railY, capY = py + 186, py + 224
    L = cs[-1] - cs[0]

    def f(v):  # keyframe percent
        return f"{max(0, min(100, v)):.2f}"

    css = []
    for i in range(n):
        a = i * win
        st_base, st_cur, st_done = (f"fill:{base};stroke:{line}", f"fill:{acc};stroke:{wp['cur_line']}",
                                    f"fill:{done};stroke:{acc}")
        css.append(f"@keyframes wpS{i}{{0%{{{st_base}}}{f(a)}%{{{st_base}}}{f(a + 1.2)}%{{{st_cur}}}"
                   f"{f(a + win)}%{{{st_cur}}}{f(a + win + 1.5)}%{{{st_done}}}96%{{{st_done}}}"
                   f"99%,100%{{{st_base}}}}}.wp-s{i}{{animation:wpS{i} {P}s ease-in-out infinite}}")
        css.append(f"@keyframes wpP{i}{{0%,{f(a)}%{{transform:scale(1)}}{f(a + 1.4)}%{{transform:scale(1.07)}}"
                   f"{f(a + 3)}%{{transform:scale(.985)}}{f(a + 4.4)}%,100%{{transform:scale(1)}}}}"
                   f".wp-p{i}{{transform-box:fill-box;transform-origin:center;"
                   f"animation:wpP{i} {P}s cubic-bezier(.45,0,.55,1) infinite}}")
        out_at = (i + 1) * win if i < n - 1 else n * win + 0.5
        css.append(f"@keyframes wpC{i}{{0%,{f(a + 0.8)}%{{opacity:0;transform:translateY(5px)}}"
                   f"{f(a + 2.2)}%,{f(out_at - 0.6)}%{{opacity:1;transform:none}}"
                   f"{f(out_at + 0.4)}%,100%{{opacity:0;transform:none}}}}"
                   f".wp-c{i}{{animation:wpC{i} {P}s ease-out infinite}}")
    # the request token and the rail it fills, stopping under each step
    tok = [f"0%{{opacity:0;transform:translateX({cs[0] - cs[STATIC]:.1f}px);{ease}}}"]
    rail = [f"0%{{transform:scaleX(0);{ease}}}"]
    for i in range(n):
        a = i * win
        arrive, leave = (1.0 if i == 0 else a + 1), ((i + 1) * win - 3)
        dx, k = cs[i] - cs[STATIC], (cs[i] - cs[0]) / L
        tok.append(f"{f(arrive)}%{{opacity:1;transform:translateX({dx:.1f}px);{ease}}}")
        rail.append(f"{f(arrive)}%{{transform:scaleX({k:.4f});{ease}}}")
        if i < n - 1:
            tok.append(f"{f(leave)}%{{opacity:1;transform:translateX({dx:.1f}px);{ease}}}")
            rail.append(f"{f(leave)}%{{transform:scaleX({k:.4f});{ease}}}")
    tok += [f"96%{{opacity:1;transform:translateX({cs[-1] - cs[STATIC]:.1f}px)}}",
            f"99%,100%{{opacity:0;transform:translateX({cs[-1] - cs[STATIC]:.1f}px)}}"]
    rail += ["96%{transform:scaleX(1);opacity:1}", "99%{transform:scaleX(1);opacity:0}",
             "100%{transform:scaleX(0);opacity:0}"]
    css.append("@keyframes wpTok{" + "".join(tok) + f"}}.wp-tok{{animation:wpTok {P}s infinite}}")
    css.append("@keyframes wpRail{" + "".join(rail) + f"}}.wp-rail{{transform-box:fill-box;"
               f"transform-origin:left center;animation:wpRail {P}s infinite}}")
    end = n * win
    css.append(f"@keyframes wpOk{{0%,{f(end + 1)}%{{opacity:0;transform:translateY(5px)}}"
               f"{f(end + 2.5)}%,95%{{opacity:1;transform:none}}97.5%,100%{{opacity:0}}}}"
               f".wp-ok{{animation:wpOk {P}s ease-out infinite}}")
    s.extra_css += "".join(css)

    # rail under the steps
    s.add(f'<line x1="{cs[0]:.1f}" y1="{railY}" x2="{cs[-1]:.1f}" y2="{railY}" stroke="{wp["rail"]}" '
          f'stroke-width="2" stroke-linecap="round"/>')
    k2 = (cs[STATIC] - cs[0]) / L
    s.add(f'<rect x="{cs[0]:.1f}" y="{railY - 1.5}" width="{L:.1f}" height="3" rx="1.5" fill="{acc}" '
          f'class="wp-rail" transform="scale({k2:.4f} 1)"/>')  # origin: the class's left edge
    for i, (name, _) in enumerate(steps):
        x = xs[i]
        fill, stroke = ((done, acc) if i < STATIC else (acc, wp["cur_line"]) if i == STATIC else (base, line))
        if i < n - 1:
            s.add(f'<line x1="{x + sw_:.1f}" y1="{py + 131}" x2="{x + sw_ + sg:.1f}" y2="{py + 131}" '
                  f'stroke="{line}" stroke-width="2"/>')
        s.add(f'<circle cx="{cs[i]:.1f}" cy="{railY}" r="3" fill="{wp["rail"]}"/>')
        s.add(f'<g class="wp-p{i}">')
        s.add(f'<rect x="{x:.1f}" y="{py + 100}" width="{sw_:.1f}" height="62" rx="10" fill="{fill}" '
              f'stroke="{stroke}" stroke-width="1.5" class="wp-s{i}"/>')
        s.text(cs[i], py + 125, f"0{i + 1}", "M7", 11, wp["text"], anchor="middle")
        s.text(cs[i], py + 145, name, "M7", 11, wp["text"], anchor="middle", ls=0.06)
        s.add("</g>")
    # the token: a small glowing request riding the rail
    s.add(f'<g class="wp-tok"><circle cx="{cs[STATIC]:.1f}" cy="{railY}" r="11" fill="{acc}" opacity=".22"/>'
          f'<circle cx="{cs[STATIC]:.1f}" cy="{railY}" r="6" fill="{acc}" stroke="{wp["tok"]}" '
          f'stroke-width="2"/></g>')
    # one trace line per step, and the commit line
    for i, (name, desc) in enumerate(steps):
        op = "1" if i == STATIC else "0"
        s.add(f'<g class="wp-c{i}" opacity="{op}">')
        s.text(36, capY, f"TRACE 0{i + 1}", "M7", 12, wp["trace"], ls=0.08)
        s.text(36 + measure(f"TRACE 0{i + 1}", "M7", 12, 0.08) + 14, capY, desc, "O4", 15.5, wp["text"])
        s.add("</g>")
    s.add('<g class="wp-ok" opacity="0">')
    s.add(f'<circle cx="44" cy="{capY - 4.5}" r="8" fill="{wp["ok"]}"/>'
          f'<path d="M40 {capY - 4.5} l3 3 l5.5 -6" fill="none" stroke="{wp["check"]}" stroke-width="2" '
          f'stroke-linecap="round" stroke-linejoin="round"/>')
    s.text(60, capY, "COMMITTED", "M7", 12, wp["ok_text"], ls=0.08)
    s.text(60 + measure("COMMITTED", "M7", 12, 0.08) + 14, capY,
           "One audited, transactional write: it all landed together, or none of it did.", "O4", 15.5,
           wp["text"])
    s.add("</g>")
    finite_loops(s, 0.92)


RULES = [
    ("SHOW THE WHY.", "Scores and decisions come with their reasons: SHAP reasons for every "
     "readmission score, weighted factors in résumé matching.", "EXPLAINABILITY"),
    ("ENFORCE IT ON THE SERVER.", "Permissions are checked where the data is written, so "
     "hiding a button is never the only safeguard.", "SERVER-SIDE ENFORCEMENT"),
    ("PROVE IT, THEN SAY WHAT'S MISSING.", "Claims ship with tests (unit, end-to-end, axe), "
     "and every project states what it does not do yet.", "STATED LIMITS"),
]
WP_STEPS = [
    ("INTERFACE", "The browser submits a form. Nothing it sends is trusted."),
    ("SERVER ACTION", "A Next.js server action receives it and authenticates the session."),
    ("PERMISSION", "Role, scope and record are checked on the server; hiding a button is never the only safeguard."),
    ("ZOD", "The input is validated with Zod before anything is written."),
    ("TRANSACTION", "The change, its audit entries and notifications commit or roll back together."),
    ("AUDIT LOG", "Every change records who did what, and when."),
    ("POSTGRES", "Postgres via Prisma, with row level security on and no public access."),
]


def wp_palette(t: dict) -> dict:
    if t["name"] == "dark":
        return dict(bg=t["panel"], text=t["panel_text"], muted=t["panel_muted"], base=t["panel_raised"],
                    line=t["panel_line"], rail=t["panel_line"], done="#3A2620", trace=t["accent"],
                    tok=t["panel_text"], ok="#6FCF9F", ok_text="#6FCF9F", check="#1C1917", cur_line=t["accent"])
    return dict(bg=t["paper"], text=t["ink"], muted=t["muted"], base=t["card"],
                line=t["rule"], rail="#D9CDBB", done=t["accent_soft"], trace=t["accent_text"],
                tok=t["ink"], ok="#0B6B4A", ok_text="#0B6B4A", check="#FFFFFF", cur_line=t["rule"])


def principles_phone(s: Svg, t: dict):
    """Phone layout of How I work: the three rules stacked, then the write path running
    top to bottom, with the same trace animation as the desktop panel."""
    W = s.w
    cw = W - 14
    y0 = 3
    for i, (title, body, foot) in enumerate(RULES):
        tl = wrap(title, "O8", 26, cw - 52)
        bl = wrap(body, "O4", 17, cw - 52)
        title_y = y0 + 84
        body_y = title_y + (len(tl) - 1) * 31 + 36
        hair_y = body_y + (len(bl) - 1) * 25 + 28
        h = hair_y - y0 + 50
        s.add(f'<g><g class="fade" style="animation-delay:{i * .1:.1f}s">')
        s.box(3, y0, cw, h, r=18, fill=t["card"], off=6)
        s.text(29, y0 + 42, f"RULE // 0{i + 1}", "M7", 13, t["accent_text"], ls=0.1)
        for k, ln in enumerate(tl):
            s.text(29, title_y + k * 31, ln, "O8", 26, t["ink"], ls=-0.01)
        for k, ln in enumerate(bl):
            s.text(29, body_y + k * 25, ln, "O4", 17, t["muted"])
        s.add(f'<line x1="29" y1="{hair_y}" x2="{cw - 23}" y2="{hair_y}" stroke="{t["hair"]}" stroke-width="1.5"/>')
        s.text(29, hair_y + 27, foot, "M4", 12, t["ink"], ls=0.08)
        s.text(cw - 23, hair_y + 27, f"0{i + 1} / 03", "M4", 12, t["ink"], anchor="end", ls=0.06)
        s.add("</g></g>")
        y0 += h + 22

    # vertical write path
    wp = wp_palette(t)
    py = y0 + 10
    n, STATIC = len(WP_STEPS), 2
    P, win = 11.2, 12.5
    base, line, acc, done = wp["base"], wp["line"], t["accent"], wp["done"]
    ease = "animation-timing-function:cubic-bezier(.45,0,.55,1)"
    desc = wrap("Every write in Grove HRMS takes this path, and it is traced on the server.", "O4", 16.5, cw - 64)
    first = py + 100 + (len(desc) - 1) * 24
    rowh, boxh = 58, 44
    ys = [first + i * rowh for i in range(n)]          # top of each step box
    cs = [y + boxh / 2 for y in ys]                    # centre line of each step
    railX, bx, bw = 52, 82, cw - 82 - 26
    L = cs[-1] - cs[0]
    capY = ys[-1] + boxh + 50
    cap_lines = max(len(wrap(d, "O4", 16, cw - 64)) for _, d in WP_STEPS)
    ph = capY + 24 + cap_lines * 24 + 18 - py
    s.box(3, py, cw, ph, r=22, fill=wp["bg"], stroke=t["rule"], off=7)
    s.add(f'<circle cx="38" cy="{py + 40}" r="5" fill="{acc}"/>')
    s.text(52, py + 45, "GROVE HRMS WRITE PATH", "M7", 13.5, wp["text"], ls=0.1)
    for k, ln in enumerate(desc):
        s.text(36, py + 76 + k * 24, ln, "O4", 16.5, wp["muted"])

    def f(v):
        return f"{max(0, min(100, v)):.2f}"

    css = []
    for i in range(n):
        a = i * win
        st_base, st_cur, st_done = (f"fill:{base};stroke:{line}", f"fill:{acc};stroke:{wp['cur_line']}",
                                    f"fill:{done};stroke:{acc}")
        css.append(f"@keyframes wpS{i}{{0%{{{st_base}}}{f(a)}%{{{st_base}}}{f(a + 1.2)}%{{{st_cur}}}"
                   f"{f(a + win)}%{{{st_cur}}}{f(a + win + 1.5)}%{{{st_done}}}96%{{{st_done}}}"
                   f"99%,100%{{{st_base}}}}}.wp-s{i}{{animation:wpS{i} {P}s ease-in-out infinite}}")
        css.append(f"@keyframes wpP{i}{{0%,{f(a)}%{{transform:scale(1)}}{f(a + 1.4)}%{{transform:scale(1.04)}}"
                   f"{f(a + 3)}%{{transform:scale(.99)}}{f(a + 4.4)}%,100%{{transform:scale(1)}}}}"
                   f".wp-p{i}{{transform-box:fill-box;transform-origin:center;"
                   f"animation:wpP{i} {P}s cubic-bezier(.45,0,.55,1) infinite}}")
        out_at = (i + 1) * win if i < n - 1 else n * win + 0.5
        css.append(f"@keyframes wpC{i}{{0%,{f(a + 0.8)}%{{opacity:0;transform:translateY(5px)}}"
                   f"{f(a + 2.2)}%,{f(out_at - 0.6)}%{{opacity:1;transform:none}}"
                   f"{f(out_at + 0.4)}%,100%{{opacity:0;transform:none}}}}"
                   f".wp-c{i}{{animation:wpC{i} {P}s ease-out infinite}}")
    tok = [f"0%{{opacity:0;transform:translateY({cs[0] - cs[STATIC]:.1f}px);{ease}}}"]
    rail = [f"0%{{transform:scaleY(0);{ease}}}"]
    for i in range(n):
        a = i * win
        arrive, leave = (1.0 if i == 0 else a + 1), ((i + 1) * win - 3)
        dy, k = cs[i] - cs[STATIC], (cs[i] - cs[0]) / L
        tok.append(f"{f(arrive)}%{{opacity:1;transform:translateY({dy:.1f}px);{ease}}}")
        rail.append(f"{f(arrive)}%{{transform:scaleY({k:.4f});{ease}}}")
        if i < n - 1:
            tok.append(f"{f(leave)}%{{opacity:1;transform:translateY({dy:.1f}px);{ease}}}")
            rail.append(f"{f(leave)}%{{transform:scaleY({k:.4f});{ease}}}")
    tok += [f"96%{{opacity:1;transform:translateY({cs[-1] - cs[STATIC]:.1f}px)}}",
            f"99%,100%{{opacity:0;transform:translateY({cs[-1] - cs[STATIC]:.1f}px)}}"]
    rail += ["96%{transform:scaleY(1);opacity:1}", "99%{transform:scaleY(1);opacity:0}",
             "100%{transform:scaleY(0);opacity:0}"]
    css.append("@keyframes wpTok{" + "".join(tok) + f"}}.wp-tok{{animation:wpTok {P}s infinite}}")
    css.append("@keyframes wpRail{" + "".join(rail) + f"}}.wp-rail{{transform-box:fill-box;"
               f"transform-origin:center top;animation:wpRail {P}s infinite}}")
    end = n * win
    css.append(f"@keyframes wpOk{{0%,{f(end + 1)}%{{opacity:0;transform:translateY(5px)}}"
               f"{f(end + 2.5)}%,95%{{opacity:1;transform:none}}97.5%,100%{{opacity:0}}}}"
               f".wp-ok{{animation:wpOk {P}s ease-out infinite}}")
    s.extra_css += "".join(css)

    s.add(f'<line x1="{railX}" y1="{cs[0]:.1f}" x2="{railX}" y2="{cs[-1]:.1f}" stroke="{wp["rail"]}" '
          f'stroke-width="2" stroke-linecap="round"/>')
    k2 = (cs[STATIC] - cs[0]) / L
    s.add(f'<rect x="{railX - 1.5}" y="{cs[0]:.1f}" width="3" height="{L:.1f}" rx="1.5" fill="{acc}" '
          f'class="wp-rail" transform="scale(1 {k2:.4f})"/>')  # origin: the class's top edge
    for i, (name, _) in enumerate(WP_STEPS):
        fill, stroke = ((done, acc) if i < STATIC else (acc, wp["cur_line"]) if i == STATIC else (base, line))
        s.add(f'<line x1="{railX}" y1="{cs[i]:.1f}" x2="{bx}" y2="{cs[i]:.1f}" stroke="{wp["rail"]}" stroke-width="2"/>')
        s.add(f'<circle cx="{railX}" cy="{cs[i]:.1f}" r="3.5" fill="{wp["rail"]}"/>')
        s.add(f'<g class="wp-p{i}">')
        s.add(f'<rect x="{bx}" y="{ys[i]:.1f}" width="{bw}" height="{boxh}" rx="10" fill="{fill}" '
              f'stroke="{stroke}" stroke-width="1.5" class="wp-s{i}"/>')
        s.text(bx + 18, cs[i] + 5, f"0{i + 1}", "M7", 13, wp["text"])
        s.text(bx + 58, cs[i] + 5, name, "M7", 13, wp["text"], ls=0.06)
        s.add("</g>")
    s.add(f'<g class="wp-tok"><circle cx="{railX}" cy="{cs[STATIC]:.1f}" r="11" fill="{acc}" opacity=".22"/>'
          f'<circle cx="{railX}" cy="{cs[STATIC]:.1f}" r="6.5" fill="{acc}" stroke="{wp["tok"]}" '
          f'stroke-width="2"/></g>')
    s.add(f'<line x1="36" y1="{capY - 30}" x2="{cw - 30}" y2="{capY - 30}" stroke="{wp["rail"]}" stroke-width="1.2"/>')
    for i, (name, d) in enumerate(WP_STEPS):
        op = "1" if i == STATIC else "0"
        s.add(f'<g class="wp-c{i}" opacity="{op}">')
        s.text(36, capY, f"TRACE 0{i + 1} · {name}", "M7", 12.5, wp["trace"], ls=0.08)
        for k, ln in enumerate(wrap(d, "O4", 16, cw - 64)):
            s.text(36, capY + 26 + k * 24, ln, "O4", 16, wp["text"])
        s.add("</g>")
    s.add('<g class="wp-ok" opacity="0">')
    s.add(f'<circle cx="44" cy="{capY - 4.5}" r="8" fill="{wp["ok"]}"/>'
          f'<path d="M40 {capY - 4.5} l3 3 l5.5 -6" fill="none" stroke="{wp["check"]}" stroke-width="2" '
          f'stroke-linecap="round" stroke-linejoin="round"/>')
    s.text(60, capY, "COMMITTED", "M7", 12.5, wp["ok_text"], ls=0.08)
    for k, ln in enumerate(wrap("One audited, transactional write: it all landed together, or none of it did.",
                                "O4", 16, cw - 64)):
        s.text(36, capY + 26 + k * 24, ln, "O4", 16, wp["text"])
    s.add("</g>")
    finite_loops(s, 0.92)
    s.needed_h = py + ph + 12


def experience(s: Svg, t: dict):
    W, H = s.w, s.h
    s.box(3, 3, W - 14, H - 14, r=24, fill=t["card"], off=7)
    split = 690
    s.add(f'<line x1="{split}" y1="34" x2="{split}" y2="{H - 44}" stroke="{t["hair"]}" stroke-width="2"/>')
    s.kicker(40, 56, "EXPERIENCE")
    jobs = [
        ("JAN 2026 – APR 2026  ·  REMOTE", "Business Analytics Intern", "Maincrafts Technology",
         "Interactive Power BI dashboards (DAX, Power Query) and table relationships so "
         "stakeholders can answer KPI questions themselves."),
        ("OCT 2025 – JAN 2026  ·  BENGALURU, ON-SITE", "Data Science Intern", "Zetpeak",
         "Tested Python and SQL data-quality checks on ingestion pipelines cut ingestion-level "
         "errors by 15%; regression and K-means models surfaced patterns in company data."),
    ]
    y = 100
    for i, (when, role, org, what) in enumerate(jobs):
        s.add(f'<circle cx="46" cy="{y - 5}" r="6" fill="{t["card"]}" stroke="{t["accent"]}" stroke-width="2.5"/>')
        if i == 0:
            s.add(f'<line x1="46" y1="{y + 2}" x2="46" y2="{y + 132}" stroke="{t["hair"]}" stroke-width="2"/>')
        s.text(66, y, when, "M7", 11.5, t["accent_text"], ls=0.08)
        s.text(66, y + 34, role, "O8", 24, t["ink"], ls=-0.01)
        s.text(66 + measure(role, "O8", 24, -0.01) + 10, y + 34, "· " + org, "O4", 20, t["muted"])
        s.para(66, y + 62, what, "O4", 15.5, 580, 23, t["muted"])
        y += 142

    x = split + 36
    s.kicker(x, 56, "EDUCATION")
    s.text(x, 104, "B.Tech, Computer Science", "O8", 24, t["ink"], ls=-0.01)
    s.text(x, 132, "Engineering (Data Science)", "O8", 24, t["ink"], ls=-0.01)
    s.text(x, 162, "Garden City University, Bengaluru · 2026", "O4", 16, t["muted"])
    s.box(x, 182, 168, 70, r=12, fill=t["accent_soft"], off=4)
    s.text(x + 18, 230, "8.53", "O8", 38, t["accent"])
    s.text(x + 106, 222, "CGPA", "M7", 11, t["ink"], ls=0.08)
    s.text(x + 106, 238, "/ 10", "M4", 11, t["faint"])
    s.text(x + 190, 214, "Graduated", "M7", 11.5, t["faint"], ls=0.08)
    s.text(x + 190, 234, "JULY 2026", "M7", 13, t["ink"], ls=0.08)

    s.kicker(x, 300, "CERTIFICATIONS", dot=False, size=12)
    certs = ["GOOGLE GEN AI ACADEMY", "MCKINSEY FORWARD PROGRAM", "GOOGLE DATA ANALYTICS (PROFESSIONAL)"]
    yy = 318
    for c in certs:
        s.pill(x, yy, c, size=11, h=26, ls=0.06, fill=t["paper"])
        yy += 34


def contact(s: Svg, t: dict):
    W, H = s.w, s.h
    s.box(3, 3, W - 14, H - 14, r=24, fill=t["accent"], off=8)
    ink = "#1C1917"
    s.text(44, 64, "● OPEN TO SOFTWARE DEVELOPER ROLES · BENGALURU", "M7", 13, ink, ls=0.12)
    s.text(40, 132, "Let's build something", "O9", 54, ink, ls=-0.02)
    s.text(40, 190, "that can explain itself.", "O9", 54, "#FFFDF8", ls=-0.02)
    bx, by = 780, 74
    s.add(f'<rect x="{bx + 5}" y="{by + 5}" width="350" height="96" rx="16" fill="{ink}"/>')
    s.add(f'<rect x="{bx}" y="{by}" width="350" height="96" rx="16" fill="#FFFDF8" stroke="{ink}" stroke-width="2.5"/>')
    s.text(bx + 24, by + 36, "WRITE TO ME · CLICK TO EMAIL", "M7", 12, "#B23F1C", ls=0.12)
    s.add(f'<rect x="{bx + 300}" y="{by + 18}" width="30" height="30" rx="8" fill="#E05A36" stroke="{ink}" stroke-width="2"/>')
    s.text(bx + 315, by + 38, "↗", "M7", 15, ink, anchor="middle")
    s.text(bx + 24, by + 70, "rrushikeshp8@gmail.com", "M7", 19, ink)
    s.add(f'<rect x="{bx + 24 + measure("rrushikeshp8@gmail.com", "M7", 19) + 4}" y="{by + 54}" width="10" '
          f'height="20" fill="{ink}" class="blink"/>')


# ---------------------------------------------------------------------------- phone layouts

def header_phone(s: Svg, t: dict):
    """Phone header: the same springy name, set to fit 520 wide, with the whoami panel below."""
    W, H = s.w, s.h
    s.paths = True
    s.box(3, 3, W - 14, H - 14, r=26, fill=t["paper"], off=8)
    s.add(f'<clipPath id="hc"><rect x="5" y="5" width="{W - 18}" height="{H - 18}" rx="24"/></clipPath>')
    s.add('<g clip-path="url(#hc)">')
    dot_grid(s, 5, 5, W - 18, H - 18)
    s.add("</g>")
    x = 36
    s.kicker(x, 62, "SOFTWARE DEVELOPER · BENGALURU, INDIA", size=12)
    size = round(min(96, (W - 14 - 2 * x) / measure("RUSHIKESH", "O9", 100, -0.01) * 100), 1)
    b1, b2 = 62 + size * 0.98 + 14, 62 + size * 1.86 + 14
    s.extra_css += spring_keyframes("jelly")
    s.add(f'<clipPath id="l1"><rect x="0" y="0" width="{W}" height="{b1 + 4:.0f}"/></clipPath>'
          f'<clipPath id="l2"><rect x="0" y="{b1 + 4:.0f}" width="{W}" height="{b2 - b1:.0f}"/></clipPath>')
    s.add('<g clip-path="url(#l1)">')
    s.text(x - 4, b1, "RUSHIKESH", "O9", size, t["ink"], ls=-0.01, per_glyph=("jelly", 0.3, 0.045))
    s.add('</g><g clip-path="url(#l2)">')
    s.text(x - 4, b2, "PANCHAL", "O9", size, t["accent"], ls=-0.01, per_glyph=("jelly", 0.55, 0.045))
    s.add("</g>")
    y = b2 + 28
    s.add(f'<rect x="{x}" y="{y:.0f}" width="{W - 14 - 2 * x}" height="2.5" fill="{t["rule"]}" class="grow" '
          f'style="animation-delay:.8s"/>')
    s.text(x, y + 38, "I build software that can explain itself.", "O7", 21, t["ink"], cls="show",
           style="animation-delay:.95s")
    for k, ln in enumerate(wrap("Full-stack TypeScript · server-side access control · explainable AI",
                                "O4", 17.5, W - 14 - 2 * x)):
        s.text(x, y + 70 + k * 25, ln, "O4", 17.5, t["muted"], cls="show", style="animation-delay:1.05s")
    px, py, pw_, ph = 40, y + 128, W - 14 - 80 + 6, 300
    s.add(f'<g transform="rotate(-1.6 {px + pw_ / 2} {py + ph / 2})"><g class="lift" style="animation-delay:.7s">')
    s.box(px, py, pw_, ph, r=18, fill=t["card"], off=7)
    s.add(f'<line x1="{px}" y1="{py + 46}" x2="{px + pw_}" y2="{py + 46}" stroke="{t["rule"]}" stroke-width="2"/>')
    for i, c in enumerate([t["accent"], t["sand"], t["sage"]]):
        s.add(f'<circle cx="{px + 24 + i * 18}" cy="{py + 23}" r="5.5" fill="{c}" stroke="{t["rule"]}" stroke-width="1.5"/>')
    s.text(px + pw_ - 20, py + 28, "whoami.ts", "M7", 13, t["faint"], anchor="end", ls=0.04)
    rows = [("role", "Software Developer"), ("stack", "Next.js · Node · Postgres"),
            ("focus", "RBAC · integrity · XAI"), ("degree", "B.Tech CSE (Data Sci.)"),
            ("tests", "unit · e2e · axe")]
    for i, (k, v) in enumerate(rows):
        yy = py + 86 + i * 36
        s.text(px + 24, yy, k, "M4", 15, t["accent_text"])
        s.text(px + 108, yy, v, "M4", 15, t["ink"])
    yy = py + 86 + 5 * 36 + 8
    s.add(f'<rect x="{px + 20}" y="{yy - 22}" width="{pw_ - 40}" height="34" rx="17" '
          f'fill="{t["sage_soft"]}" stroke="{t["rule"]}" stroke-width="1.5"/>')
    s.add(f'<circle cx="{px + 40}" cy="{yy - 5}" r="5" fill="{t["ok"]}"/>')
    s.add(f'<circle cx="{px + 40}" cy="{yy - 5}" r="5" fill="{t["ok"]}" class="beacon"/>')
    s.text(px + 54, yy, "OPEN TO SOFTWARE DEVELOPER ROLES", "M7", 11.5,
           t["sage_text"] if t["name"] == "light" else t["ok"], ls=0.06)
    s.add("</g></g>")
    s.needed_h = py + ph + 40


def stats_phone(s: Svg, t: dict):
    """The four stats as a 2 x 2 grid."""
    items = [("8", "PUBLIC PROJECTS"), ("6", "LIVE SITES"), ("130+", "TESTS ON GROVE"),
             ("100×4", "LIGHTHOUSE ·", "MOTIONFOLIO")]
    gap = 18
    w, h = (s.w - 14 - gap) / 2, 150
    for i, it in enumerate(items):
        n, lab = it[0], it[1:]
        x, y = 3 + (i % 2) * (w + gap), 3 + (i // 2) * (h + gap)
        fill = t["accent_soft"] if i == 3 else t["card"]
        s.box(x, y, w, h, r=18, fill=fill, off=6, cls="fade", style=f"animation-delay:{i * .08:.2f}s")
        s.text(x + 24, y + 70, n, "O8", 52, t["accent"] if i == 3 else t["ink"], cls="fade",
               style=f"animation-delay:{i * .08:.2f}s")
        s.add(f'<rect x="{x + 24}" y="{y + 86}" width="44" height="4" rx="2" fill="{t["accent"]}" '
              f'class="grow" style="animation-delay:{.3 + i * .08:.2f}s"/>')
        for k, ln in enumerate(lab):
            s.text(x + 24, y + 116 + k * 18, ln, "M7", 12.5, t["muted"], ls=0.08)


def experience_phone(s: Svg, t: dict):
    """Experience, then education and certifications, in one column."""
    W = s.w
    x, tw = 36, W - 14 - 72
    jobs = [
        ("JAN 2026 – APR 2026 · REMOTE", "Business Analytics Intern", "Maincrafts Technology",
         "Interactive Power BI dashboards (DAX, Power Query) and table relationships so "
         "stakeholders can answer KPI questions themselves."),
        ("OCT 2025 – JAN 2026 · BENGALURU", "Data Science Intern", "Zetpeak",
         "Tested Python and SQL data-quality checks on ingestion pipelines cut ingestion-level "
         "errors by 15%; regression and K-means models surfaced patterns in company data."),
    ]
    body = []          # draw after the box, once its height is known
    y = 58
    body.append(lambda: s.kicker(x, 58, "EXPERIENCE", size=12.5))
    y += 46
    for i, (when, role, org, what) in enumerate(jobs):
        yy = y
        lines = wrap(what, "O4", 16.5, tw - 24)
        def draw(yy=yy, when=when, role=role, org=org, lines=lines, last=(i == len(jobs) - 1)):
            s.add(f'<circle cx="{x + 6}" cy="{yy - 5}" r="6" fill="{t["card"]}" stroke="{t["accent"]}" stroke-width="2.5"/>')
            s.text(x + 24, yy, when, "M7", 12, t["accent_text"], ls=0.06)
            s.text(x + 24, yy + 34, role, "O8", 24, t["ink"], ls=-0.01)
            s.text(x + 24, yy + 60, org, "O4", 18, t["muted"])
            for k, ln in enumerate(lines):
                s.text(x + 24, yy + 90 + k * 24, ln, "O4", 16.5, t["muted"])
        body.append(draw)
        step = 90 + (len(lines) - 1) * 24 + 44
        if i == 0:
            body.append(lambda yy=yy, step=step: s.add(
                f'<line x1="{x + 6}" y1="{yy + 3}" x2="{x + 6}" y2="{yy + step - 12}" stroke="{t["hair"]}" stroke-width="2"/>'))
        y += step
    y += 6
    hy = y
    body.append(lambda: s.add(f'<line x1="{x}" y1="{hy}" x2="{W - 14 - x}" y2="{hy}" stroke="{t["hair"]}" stroke-width="2"/>'))
    y += 46
    ey = y
    def edu():
        s.kicker(x, ey, "EDUCATION", size=12.5)
        s.text(x, ey + 46, "B.Tech, Computer Science", "O8", 25, t["ink"], ls=-0.01)
        s.text(x, ey + 76, "Engineering (Data Science)", "O8", 25, t["ink"], ls=-0.01)
        s.text(x, ey + 106, "Garden City University, Bengaluru · 2026", "O4", 17, t["muted"])
        s.box(x, ey + 126, 176, 72, r=12, fill=t["accent_soft"], off=4)
        s.text(x + 18, ey + 175, "8.53", "O8", 40, t["accent"])
        s.text(x + 112, ey + 166, "CGPA", "M7", 12, t["ink"], ls=0.08)
        s.text(x + 112, ey + 183, "/ 10", "M4", 12, t["faint"])
        s.text(x + 202, ey + 158, "Graduated", "M7", 12, t["faint"], ls=0.08)
        s.text(x + 202, ey + 180, "JULY 2026", "M7", 14, t["ink"], ls=0.08)
        s.kicker(x, ey + 248, "CERTIFICATIONS", dot=False, size=12.5)
        yy = ey + 266
        for c in ["GOOGLE GEN AI ACADEMY", "MCKINSEY FORWARD PROGRAM", "GOOGLE DATA ANALYTICS (PROFESSIONAL)"]:
            s.pill(x, yy, c, size=12, h=28, ls=0.05, fill=t["paper"])
            yy += 38
    body.append(edu)
    total = ey + 266 + 3 * 38 + 30
    s.box(3, 3, W - 14, total - 3, r=24, fill=t["card"], off=7)
    for f in body:
        f()
    s.needed_h = total + 14


def contact_phone(s: Svg, t: dict):
    """The orange contact card, stacked: kicker, headline, then the email box."""
    W, H = s.w, s.h
    ink = "#1C1917"
    s.box(3, 3, W - 14, H - 14, r=24, fill=t["accent"], off=8)
    s.text(36, 58, "● OPEN TO SOFTWARE DEVELOPER ROLES", "M7", 12.5, ink, ls=0.1)
    s.text(36, 80, "BENGALURU", "M7", 12.5, ink, ls=0.1)
    for k, (ln, col) in enumerate([("Let's build", ink), ("something that", ink),
                                   ("can explain", "#FFFDF8"), ("itself.", "#FFFDF8")]):
        s.text(34, 140 + k * 54, ln, "O9", 52, col, ls=-0.02)
    bx, by, bw = 36, 140 + 3 * 54 + 40, W - 14 - 72
    s.add(f'<rect x="{bx + 5}" y="{by + 5}" width="{bw}" height="96" rx="16" fill="{ink}"/>')
    s.add(f'<rect x="{bx}" y="{by}" width="{bw}" height="96" rx="16" fill="#FFFDF8" stroke="{ink}" stroke-width="2.5"/>')
    s.text(bx + 22, by + 36, "WRITE TO ME · TAP TO EMAIL", "M7", 12, "#B23F1C", ls=0.1)
    s.add(f'<rect x="{bx + bw - 50}" y="{by + 18}" width="30" height="30" rx="8" fill="#E05A36" stroke="{ink}" stroke-width="2"/>')
    s.text(bx + bw - 35, by + 38, "↗", "M7", 15, ink, anchor="middle")
    s.text(bx + 22, by + 72, "rrushikeshp8@gmail.com", "M7", 20, ink)
    s.add(f'<rect x="{bx + 22 + measure("rrushikeshp8@gmail.com", "M7", 20) + 4}" y="{by + 55}" width="10" '
          f'height="21" fill="{ink}" class="blink"/>')
    s.needed_h = by + 96 + 44


def save_sized(name: str, build, label: str, w: int) -> None:
    """Save a layout whose height comes from its content (the builder sets needed_h)."""
    probe = Svg(w, 4000, "", LIGHT)
    build(probe, LIGHT)
    save(name, build, label, w, int(probe.needed_h))


# ---------------------------------------------------------------------------- icon grid

ICONS = [  # (simple-icons slug, label, brand colour)
    ("typescript", "TypeScript", "#3178C6"), ("react", "React", "#61DAFB"),
    ("nextdotjs", "Next.js", "#000000"), ("nodedotjs", "Node.js", "#5FA04E"),
    ("express", "Express", "#000000"), ("python", "Python", "#3776AB"),
    ("fastapi", "FastAPI", "#009688"), ("postgresql", "PostgreSQL", "#4169E1"),
    ("sqlite", "SQLite", "#003B57"), ("prisma", "Prisma", "#2D3748"),
    ("supabase", "Supabase", "#3FCF8E"), ("tailwindcss", "Tailwind", "#06B6D4"),
    ("vite", "Vite", "#646CFF"), ("docker", "Docker", "#2496ED"),
    ("githubactions", "Actions", "#2088FF"), ("vercel", "Vercel", "#000000"),
    ("figma", "Figma", "#F24E1E"), ("git", "Git", "#F05032"),
]
ICON_PATHS: dict[str, str] = {}


def load_icons(folder: Path) -> None:
    import re
    for slug, _, _ in ICONS:
        svg = (folder / "icons" / f"{slug}.svg").read_text()
        ICON_PATHS[slug] = re.search(r'<path d="([^"]+)"', svg).group(1)


def _lum(hexc: str) -> float:
    r, g, b = (int(hexc[i:i + 2], 16) / 255 for i in (1, 3, 5))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def contrast(a: str, b: str) -> float:
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def icons(s: Svg, t: dict, per_row: int = 9, tile: int = 100, glyph: int = 50, row_h: int = 168,
          label: float = 14):
    """Stack logos in the card style: one flat SVG with a viewBox, so it scales on every
    screen (the external skill-icons strip showed one giant icon in the GitHub app)."""
    slot = (s.w - 14) / per_row
    lab_size = label
    for i, (slug, name, colour) in enumerate(ICONS):
        row, col = divmod(i, per_row)
        in_row = min(per_row, len(ICONS) - row * per_row)        # centre a short last row
        cx = 3 + (s.w - 14 - in_row * slot) / 2 + col * slot + slot / 2
        y = 3 + row * row_h
        x = cx - tile / 2
        c = colour if contrast(colour, t["card"]) >= 2.6 else t["ink"]
        s.add(f'<g class="show" style="animation-delay:{i * 0.03:.2f}s">')
        s.box(x, y, tile, tile, r=18, fill=t["card"], sw=2.2, off=5)
        k = glyph / 24
        s.add(f'<path d="{ICON_PATHS[slug]}" fill="{c}" '
              f'transform="translate({cx - glyph / 2:.1f} {y + (tile - glyph) / 2:.1f}) scale({k:.4f})"/>')
        s.text(cx, y + tile + 32, name.upper(), "M7", lab_size, t["ink"], anchor="middle", ls=0.06)
        s.add("</g>")


# ---------------------------------------------------------------------------- link buttons

def i_sparkle(s, cx, cy, c):
    s.add(f'<path d="M{cx} {cy - 9} Q{cx} {cy} {cx + 9} {cy} Q{cx} {cy} {cx} {cy + 9} '
          f'Q{cx} {cy} {cx - 9} {cy} Q{cx} {cy} {cx} {cy - 9}Z" fill="{c}"/>')


def i_globe(s, cx, cy, c):
    s.add(f'<g fill="none" stroke="{c}" stroke-width="1.7"><circle cx="{cx}" cy="{cy}" r="8"/>'
          f'<ellipse cx="{cx}" cy="{cy}" rx="3.4" ry="8"/><path d="M{cx - 8} {cy}h16"/></g>')


def i_doc(s, cx, cy, c):
    s.add(f'<g fill="none" stroke="{c}" stroke-width="1.7" stroke-linecap="round">'
          f'<rect x="{cx - 6.5}" y="{cy - 8.5}" width="13" height="17" rx="2"/>'
          f'<path d="M{cx - 3} {cy - 3.5}h6M{cx - 3} {cy}h6M{cx - 3} {cy + 3.5}h4"/></g>')


def i_mail(s, cx, cy, c):
    s.add(f'<g fill="none" stroke="{c}" stroke-width="1.7" stroke-linejoin="round">'
          f'<rect x="{cx - 8.5}" y="{cy - 6.5}" width="17" height="13" rx="2"/>'
          f'<path d="M{cx - 8} {cy - 5.5}l8 6l8 -6"/></g>')


def i_word(word, size):
    def draw(s, cx, cy, c):
        s.text(cx, cy + size * 0.36, word, "O8", size, c, anchor="middle")
    return draw


BUTTONS = [
    # name, label, tile colour, icon colour, icon, chip
    ("motionfolio", "Motionfolio", "#E05A36", "#FFFFFF", i_sparkle, "NEW"),
    ("portfolio", "Portfolio", "#1C1917", "#FAF6EE", i_globe, None),
    ("resume", "Résumé", "#4F5E48", "#FFFFFF", i_doc, None),
    ("linkedin", "LinkedIn", "#0A66C2", "#FFFFFF", i_word("in", 15), None),
    ("email", "Email me", "#EA4335", "#FFFFFF", i_mail, None),
    ("orcid", "ORCID", "#A6CE39", "#1C1917", i_word("iD", 13), None),
]


def button_width(label: str, chip) -> int:
    w = 50 + measure(label, "O7", 16) + 12 + measure("↗", "M7", 13) + 16
    if chip:
        w += measure(chip, "M7", 10, 0.1) + 18 + 8
    return int(round(w)) + 6


def button(s: Svg, t: dict, label, tile, ic, icon, chip):
    w = s.w - 6
    s.box(2, 2, w, 40, r=12, fill=t["card"], sw=2, off=4)
    s.add(f'<rect x="9" y="9" width="26" height="26" rx="7" fill="{tile}" stroke="{t["rule"]}" stroke-width="1.5"/>')
    icon(s, 22, 22, ic)
    x = 46
    s.text(x, 27.5, label, "O7", 16, t["ink"])
    x += measure(label, "O7", 16) + 10
    if chip:
        cw = measure(chip, "M7", 10, 0.1) + 14
        s.add(f'<rect x="{x:.1f}" y="13" width="{cw:.1f}" height="18" rx="9" fill="{t["ink"]}"/>')
        s.text(x + 7, 25.5, chip, "M7", 10, t["card"], ls=0.1)
        x += cw + 8
    s.text(x, 27, "↗", "M7", 13, t["accent_text"])


# ---------------------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fonts", required=True, type=Path)
    ap.add_argument("--shots", required=True, type=Path)
    ap.add_argument("--icons", required=True, type=Path)
    args = ap.parse_args()
    load_fonts(args.fonts)
    load_icons(args.icons)

    from PIL import Image
    im = Image.open(args.shots / "desktop-hero.png").convert("RGB").resize((994, 621), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=74, optimize=True, progressive=True)
    shot = base64.b64encode(buf.getvalue()).decode()

    save("header", header, "Rushikesh Panchal, Software Developer in Bengaluru, India. I build software "
         "that can explain itself: full-stack TypeScript, server-side access control and explainable AI. "
         "Open to Software Developer roles.", 1200, 420)
    save_sized("header-phone", header_phone, "Rushikesh Panchal, Software Developer in Bengaluru, India. "
               "I build software that can explain itself: full-stack TypeScript, server-side access control "
               "and explainable AI. Open to Software Developer roles.", 520)
    save("stats", stats, "8 public projects, 6 live sites, 130+ tests on Grove HRMS, and Lighthouse "
         "100 in all four categories on Motionfolio.", 1200, 160)
    save("stats-phone", stats_phone, "8 public projects, 6 live sites, 130+ tests on Grove HRMS, and "
         "Lighthouse 100 in all four categories on Motionfolio.", 520, 3 + 150 * 2 + 18 + 14)
    mf_label = ("Motionfolio, my animated portfolio, new in November 2026: Lighthouse mobile 100 in all "
                "four categories, 147.2 kB of JavaScript, 113 tests, no third-party requests. Live at "
                "rrushikeshp89.github.io/motionfolio.")
    save("motionfolio", lambda s, t: motionfolio(s, t, shot), mf_label, 1200, 560)
    save("motionfolio-phone", lambda s, t: motionfolio_phone(s, t, shot), mf_label, 520, MF_PHONE_H)

    GROVE = dict(
        kicker="FLAGSHIP  ·  HRMS", title="Grove HRMS", big=52, textw=600,
        pitch="A full-stack HR system for a 100-person company: people, attendance, leave, payroll "
              "and hiring, with separate experiences for employees, managers, HR and admins.",
        metrics=[("45 tables", "in one Prisma schema, seeded demo company"),
                 ("28 permissions", "scoped own / team / company, across 4 roles"),
                 ("1 write path", "Zod-validated, transactional, audit-logged"),
                 ("130+ tests", "Vitest, Playwright and axe · Lighthouse a11y 100")],
        tags=["NEXT.JS 16", "TYPESCRIPT", "PRISMA", "POSTGRES", "PLAYWRIGHT"],
        url="hrms.fluentopsai.com  ↗", gap=40, visual=v_rbac)
    grove_label = ("Grove HRMS, my flagship HR system: 45 tables, 28 scoped permissions across 4 roles, "
                   "one audited transactional write path, 130+ tests and Lighthouse accessibility 100. "
                   "Next.js 16, TypeScript, Prisma, Postgres, Playwright. Live at hrms.fluentopsai.com.")
    save("grove", lambda s, t: project(s, t, GROVE), grove_label, 1200, 500)
    # phone: the role table on top, the text below, in a narrower card that stays readable
    save("grove-phone", lambda s, t: project(s, t, dict(
        GROVE, pad=34, textw=438, big=46, top=352, vis_at=(-663, -16), ps=17, plh=25)),
        grove_label, 520, GROVE_PHONE_H)

    STOCK = dict(
        kicker="ERP · INVENTORY", title="Stockroom", big=42, textw=250, pad=34,
        pitch="Inventory and purchase orders for small shops and cafés.",
        metrics=[("Atomic receiving,", "enforced by database triggers"),
                 ("4-layer RBAC:", "20 permissions, 3 roles"),
                 ("CLS 0.495 → 0.004", ""),
                 ("956 tap targets", "fixed")],
        tags=["REACT", "EXPRESS 5", "SQLITE", "ZOD"], tagw=520, ms=14, gap=36, mgap=16,
        url="erp.fluentopsai.com  ↗", visual=v_states)
    LEAD = dict(
        kicker="CRM · SALES", title="LeadHub", big=42, textw=270, pad=34,
        pitch="A B2B sales CRM whose rules live in one TypeScript layer.",
        metrics=[("10-stage pipeline,", "weighted forecasts"),
                 ("Claude assistant", "that suggests, never edits"),
                 ("37 tests,", "Docker image in CI")],
        tags=["REACT", "EXPRESS 5", "TURSO", "CLAUDE API"], tagw=520, ms=14, gap=36, mgap=16,
        url="crm.fluentopsai.com/inquiry  ↗", visual=v_pipeline)
    # phone: portrait cards with the diagram framed in a band on top, like the AI cards
    stock_phone = dict(STOCK, textw=358, tagw=358, top=250, band=(30, 28, 366, 226), vis_at=(-218, -74))
    lead_phone = dict(LEAD, textw=358, tagw=358, top=250, band=(30, 28, 366, 226), vis_at=(-222, -66))
    work_label = (
        "Stockroom, inventory and purchase-order ERP: atomic receiving enforced by database "
        "triggers, four-layer RBAC with 20 permissions across 3 roles, layout shift cut from 0.495 "
        "to 0.004. React, Express 5, SQLite, Zod. Live at erp.fluentopsai.com. "
        "LeadHub, a B2B sales CRM: 10-stage pipeline with weighted forecasts, a Claude assistant "
        "that suggests but never edits, 37 tests and a Docker image tested in CI. React, Express 5, "
        "Turso, Claude API.")
    save_composed("work", work_label, {
        "row": ([lambda s, t: project(s, t, STOCK), lambda s, t: project(s, t, LEAD)], 600, 500, 2, 24),
        "stack": ([lambda s, t: project(s, t, stock_phone), lambda s, t: project(s, t, lead_phone)],
                  440, WORK_PHONE_H, 1, 24),
    })

    xai, xai_labels = [], []
    for name, kick, title, pitch, mets, tg, url, vis, label in [
        ("tessaract", "EXPLAINABLE IR", "Tessaract", "Résumé-to-job matching that shows its arithmetic.",
         [("4 weighted parts", "per score"), ("No LLM API", "needed to score")],
         ["FASTAPI", "POSTGRES", "REACT 19"], "source on GitHub  ↗", v_rank,
         "Tessaract: résumé-to-job matching that shows its arithmetic. Four weighted parts per score, "
         "no LLM API needed. FastAPI, Postgres, React 19."),
        ("strategyroom", "MULTI-AGENT AI", "StrategyRoom", "Investment research with a reasoning chain and sources.",
         [("Confidence", "broken into factors"), ("Two agents,", "one cited report")],
         ["SUPABASE", "GEMINI", "REACT"], "source on GitHub  ↗", v_agents,
         "StrategyRoom.ai: two-agent investment research with a reasoning chain, citations and a "
         "confidence breakdown. Supabase, Gemini, React."),
        ("readmission", "CLINICAL ML", "Readmission Shield", "Flags 30-day readmission risk before a patient leaves.",
         [("0.55 recall", "on a 9:91 imbalance"), ("SHAP reasons", "for every score")],
         ["XGBOOST", "SHAP", "STREAMLIT"], "live demo  ↗", v_shap,
         "Readmission Shield: flags 30-day readmission risk for diabetic patients. 0.55 recall on a "
         "9 to 91 class imbalance, SHAP reasons for every score. XGBoost, SHAP, Streamlit."),
    ]:
        xai.append(lambda s, t, k=kick, ti=title, p=pitch, m=mets, tg=tg, u=url, v=vis: project(s, t, dict(
            kicker=k, title=ti, big=34 if len(ti) < 14 else 30, pitch=p, metrics=m, tags=tg, url=u,
            visual=v, pad=30, ps=16, plh=23, ms=13.5, gap=30, mgap=12, us=13, textw=326, top=148)))
        xai_labels.append(label)
    # one image, two layouts: three across on wide screens, stacked on phones
    save_composed("xai", " ".join(xai_labels), {"row": (xai, 400, 510, 3, 24),
                                                "stack": (xai, 400, 510, 1, 24)})


    save("principles", principles, "How I work. Rule 01, show the why. Rule 02, enforce it on the "
         "server. Rule 03, prove it, then say what's missing. Every write in Grove HRMS takes one path: "
         "interface, server action, permission check, Zod validation, transaction, audit log, Postgres.",
         1200, 576)
    probe = Svg(520, 4000, "", LIGHT)
    principles_phone(probe, LIGHT)
    save("principles-phone", principles_phone, "How I work. Rule 01, show the why. Rule 02, enforce it "
         "on the server. Rule 03, prove it, then say what's missing. Every write in Grove HRMS takes one "
         "path: interface, server action, permission check, Zod validation, transaction, audit log, "
         "Postgres.", 520, int(probe.needed_h))
    save("experience", experience, "Experience: Business Analytics Intern at Maincrafts Technology, "
         "January to April 2026, remote. Data Science Intern at Zetpeak, October 2025 to January 2026, "
         "Bengaluru, where tested data-quality checks cut ingestion errors by 15%. Education: B.Tech in "
         "Computer Science Engineering (Data Science), Garden City University, graduated July 2026, "
         "CGPA 8.53 of 10. Certifications: Google Gen AI Academy, McKinsey Forward Program, Google Data "
         "Analytics Professional Certificate.", 1200, 456)
    save_sized("experience-phone", experience_phone, "Experience: Business Analytics Intern at Maincrafts "
               "Technology, January to April 2026, remote. Data Science Intern at Zetpeak, October 2025 to "
               "January 2026, Bengaluru, where tested data-quality checks cut ingestion errors by 15%. "
               "Education: B.Tech in Computer Science Engineering (Data Science), Garden City University, "
               "graduated July 2026, CGPA 8.53 of 10. Certifications: Google Gen AI Academy, McKinsey Forward "
               "Program, Google Data Analytics Professional Certificate.", 520)
    save("icons", icons, "Stack logos: " + ", ".join(lab for _, lab, _ in ICONS) + ".", 1200, 330)
    save("icons-phone", lambda s, t: icons(s, t, per_row=5, tile=78, glyph=40, row_h=136, label=12),
         "Stack logos: " + ", ".join(lab for _, lab, _ in ICONS) + ".", 520, 4 * 136 - 20)
    for name, label, tile, ic, icon, chip in BUTTONS:
        save(f"btn-{name}", lambda s, t, a=(label, tile, ic, icon, chip): button(s, t, *a),
             label, button_width(label, chip), 48)
    save("contact", contact,"Open to Software Developer roles in Bengaluru. Let's build something that "
         "can explain itself. Write to me at rrushikeshp8@gmail.com.", 1200, 250)
    save_sized("contact-phone", contact_phone, "Open to Software Developer roles in Bengaluru. Let's build "
               "something that can explain itself. Write to me at rrushikeshp8@gmail.com.", 520)


if __name__ == "__main__":
    main()
