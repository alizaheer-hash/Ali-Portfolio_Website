"""Render the portfolio promo video (1920x1080, 30 fps) frame by frame with Pillow and pipe the
frames into ffmpeg together with the generated soundtrack.

    python make_audio.py promo_audio.wav 52
    python make_promo.py promo_audio.wav ../client/public/media/promo.mp4

All visuals are drawn in code (text, shapes, transitions) plus crops of the avatar renders that
already live in ../screenshots, so the video matches the website exactly.
"""
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
AUDIO = sys.argv[1] if len(sys.argv) > 1 else str(HERE / 'promo_audio.wav')
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / 'client' / 'public' / 'media' / 'promo.mp4'
PREVIEW = len(sys.argv) > 3  # third arg = comma separated seconds -> dump stills only

W, H, FPS = 1920, 1080, 30
DUR = 52.0

# --- palette (same as the site's dark theme) ---------------------------------------------------
BG = (22, 19, 15)
BG2 = (15, 13, 10)
SURFACE = (33, 28, 23)
TEXT = (243, 236, 226)
MUTED = (189, 178, 163)
BORDER = (58, 50, 42)
ACCENT = (240, 138, 93)
ACCENT_D = (180, 66, 26)
ARCH = (59, 43, 34)

F = 'C:/Windows/Fonts/'


def font(name, size):
    return ImageFont.truetype(F + name, size)


SERIF_B = lambda s: font('georgiab.ttf', s)
SERIF_I = lambda s: font('georgiai.ttf', s)
SANS = lambda s: font('segoeui.ttf', s)
SANS_SB = lambda s: font('seguisb.ttf', s)
SANS_B = lambda s: font('segoeuib.ttf', s)

# --- easing ------------------------------------------------------------------------------------
clamp = lambda x, a=0.0, b=1.0: max(a, min(b, x))


def prog(t, t0, dur):
    return clamp((t - t0) / dur)


def out_cubic(x):
    return 1 - (1 - x) ** 3


def out_expo(x):
    return 1 if x >= 1 else 1 - 2 ** (-10 * x)


def in_out(x):
    return 3 * x * x - 2 * x ** 3


def out_back(x, s=1.4):
    x -= 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2


def mix(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


# --- assets ------------------------------------------------------------------------------------
def make_arch(png, scale=1.28):
    im = Image.open(ROOT / 'screenshots' / png).convert('RGB')
    if im.size != (440, 572):  # full-page screenshots need the arch cropped out; wave crops are ready
        im = im.crop((760, 127, 1200, 699))
    w, h = int(im.width * scale), int(im.height * scale)
    im = im.resize((w, h), Image.LANCZOS)
    mask = Image.new('L', (w * 2, h * 2), 0)
    d = ImageDraw.Draw(mask)
    d.pieslice((0, 0, w * 2 - 1, w * 2 - 1), 180, 360, fill=255)
    d.rectangle((0, w, w * 2 - 1, h * 2 - 1), fill=255)
    mask = mask.resize((w, h), Image.LANCZOS)
    out = im.convert('RGBA')
    out.putalpha(mask)
    return out


# (the wave screenshots are light-themed, so only the dark render is used; the avatar sways instead)
AVATARS = [make_arch('glb-dark.png')]
AV_W, AV_H = AVATARS[0].size

# vertical gradient background
_grad = np.linspace(0, 1, H)[:, None, None]
BASE = np.broadcast_to(
    (np.array(BG2) * _grad + np.array(BG) * (1 - _grad) * 1.0).astype(np.uint8), (H, W, 3)
).copy()
# soft warm glow bottom-right + vignette
yy, xx = np.mgrid[0:H, 0:W]
glow = np.exp(-(((xx - W * 0.78) / 700) ** 2 + ((yy - H * 0.55) / 520) ** 2))
BASE = np.clip(BASE + glow[..., None] * np.array([22, 11, 5]), 0, 255).astype(np.uint8)
vig = 1 - 0.38 * (((xx - W / 2) / (W / 1.55)) ** 2 + ((yy - H / 2) / (H / 1.25)) ** 2)
BASE = (BASE * np.clip(vig, 0.55, 1)[..., None]).astype(np.uint8)
BASE_IMG = Image.fromarray(BASE)


# --- drawing helpers ---------------------------------------------------------------------------
def text(img, xy, s, fnt, fill=TEXT, a=1.0, anchor='la', tracking=0):
    """Draw text with opacity. `tracking` adds letter spacing (px)."""
    if a <= 0.01:
        return
    d0 = ImageDraw.Draw(Image.new('L', (1, 1)))
    if tracking:
        widths = [d0.textlength(c, font=fnt) + tracking for c in s]
        tw = int(sum(widths))
    else:
        tw = int(d0.textlength(s, font=fnt))
    asc, desc = fnt.getmetrics()
    th = asc + desc
    pad = 12
    mask = Image.new('L', (tw + pad * 2, th + pad * 2), 0)
    md = ImageDraw.Draw(mask)
    if tracking:
        x = pad
        for c, wdt in zip(s, widths):
            md.text((x, pad), c, font=fnt, fill=255)
            x += wdt
    else:
        md.text((pad, pad), s, font=fnt, fill=255)
    x, y = xy
    if anchor[0] == 'm':
        x -= tw / 2
    elif anchor[0] == 'r':
        x -= tw
    if anchor[1] == 'm':
        y -= th / 2
    elif anchor[1] == 's':
        y -= asc
    if a < 1:
        mask = mask.point(lambda v: int(v * a))
    img.paste(Image.new('RGB', mask.size, fill), (int(x - pad), int(y - pad)), mask)


def text_w(s, fnt, tracking=0):
    d0 = ImageDraw.Draw(Image.new('L', (1, 1)))
    if tracking:
        return int(sum(d0.textlength(c, font=fnt) + tracking for c in s))
    return int(d0.textlength(s, font=fnt))


def rrect(img, box, r, fill=None, outline=None, width=1, a=1.0):
    x0, y0, x1, y1 = [int(v) for v in box]
    w, h = x1 - x0 + 1, y1 - y0 + 1
    if w <= 0 or h <= 0 or a <= 0.01:
        return
    S = 2
    mask = Image.new('L', (w * S, h * S), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w * S - 1, h * S - 1), r * S, fill=255)
    mask = mask.resize((w, h), Image.LANCZOS)
    if a < 1:
        mask = mask.point(lambda v: int(v * a))
    if fill is not None:
        img.paste(Image.new('RGB', (w, h), fill), (x0, y0), mask)
    if outline is not None:
        inner = Image.new('L', (w * S, h * S), 0)
        ImageDraw.Draw(inner).rounded_rectangle(
            (width * S, width * S, w * S - 1 - width * S, h * S - 1 - width * S), max(1, (r - width)) * S, fill=255
        )
        inner = inner.resize((w, h), Image.LANCZOS)
        ring = Image.fromarray(np.clip(np.array(mask, dtype=np.int16) - np.array(inner, dtype=np.int16), 0, 255).astype(np.uint8))
        img.paste(Image.new('RGB', (w, h), outline), (x0, y0), ring)


def chip(img, x, y, label, a=1.0, fnt=None, fill=SURFACE, outline=BORDER, color=TEXT):
    fnt = fnt or SANS_SB(24)
    w = text_w(label, fnt) + 40
    rrect(img, (x, y, x + w, y + 48), 24, fill=fill, outline=outline, width=2, a=a)
    text(img, (x + 20, y + 24), label, fnt, color, a, anchor='lm')
    return w


def line_poly(img, pts, fill):
    ImageDraw.Draw(img).polygon(pts, fill=fill)


def paste_rgba(img, rgba, xy, a=1.0):
    if a <= 0.01:
        return
    if a < 1:
        alpha = rgba.getchannel('A').point(lambda v: int(v * a))
        rgba = rgba.copy()
        rgba.putalpha(alpha)
    img.paste(rgba, (int(xy[0]), int(xy[1])), rgba)


# --- floating low-poly shapes (background decoration) -----------------------------------------
SHAPES = [
    # (cx, cy, size, kind, speed, phase, tone)
    (180, 220, 70, 'dia', 0.5, 0.0, 0.0),
    (1720, 160, 56, 'tri', 0.7, 1.2, 0.25),
    (1480, 900, 90, 'dia', 0.4, 2.4, 0.5),
    (320, 880, 48, 'tri', 0.8, 3.1, 0.2),
    (980, 110, 36, 'dia', 0.9, 4.3, 0.4),
    (1830, 640, 44, 'tri', 0.6, 5.5, 0.1),
    (90, 560, 38, 'dia', 0.7, 0.9, 0.35),
]


def draw_shapes(img, t, dim=1.0):
    d = ImageDraw.Draw(img)
    for cx, cy, s, kind, sp, ph, tone in SHAPES:
        ang = t * sp + ph
        x = cx + math.sin(ang * 0.9) * 26
        y = cy + math.cos(ang * 0.7) * 22
        base = mix(ARCH, ACCENT, tone * 0.55)
        base = mix(BG, base, 0.55 * dim)
        light = mix(base, ACCENT, 0.25)
        dark = mix(base, BG2, 0.45)
        sx = abs(math.cos(ang)) * 0.75 + 0.25
        if kind == 'dia':
            top, bot = (x, y - s), (x, y + s)
            l, r = (x - s * sx, y), (x + s * sx, y)
            d.polygon([top, r, bot], fill=light)
            d.polygon([top, l, bot], fill=dark)
        else:
            a = (x, y - s)
            b = (x + s * sx, y + s * 0.8)
            c = (x - s * sx, y + s * 0.8)
            d.polygon([a, b, c], fill=base)
            d.polygon([a, (x, y + s * 0.8), c], fill=dark)


# --- icons for the project cards ---------------------------------------------------------------
def icon_radar(img, cx, cy, t, a):
    d = ImageDraw.Draw(img)
    for r in (230, 170, 110, 50):
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=mix(BG, ACCENT, 0.35 * a), width=3)
    # rotating detection cone
    ang = t * 1.4
    for k in range(14):
        a0 = ang - k * 0.045
        d.polygon(
            [(cx, cy), (cx + 230 * math.cos(a0), cy + 230 * math.sin(a0)),
             (cx + 230 * math.cos(a0 - 0.05), cy + 230 * math.sin(a0 - 0.05))],
            fill=mix(ARCH, ACCENT, (1 - k / 14) * 0.7 * a),
        )
    gx, gy = cx + math.cos(t * 0.9) * 120, cy + math.sin(t * 0.9) * 90
    d.ellipse((gx - 14, gy - 14, gx + 14, gy + 14), fill=ACCENT)
    d.ellipse((cx - 9, cy - 9, cx + 9, cy + 9), fill=TEXT)
    # loot diamond
    lx, ly = cx - 120, cy + 100
    d.polygon([(lx, ly - 16), (lx + 14, ly), (lx, ly + 16), (lx - 14, ly)], fill=TEXT)


def icon_voxels(img, cx, cy, t, a):
    d = ImageDraw.Draw(img)
    s = 44

    def cube(gx, gy, gz, tone):
        x = cx + (gx - gy) * s * 0.87
        y = cy + (gx + gy) * s * 0.5 - gz * s
        top = mix(ARCH, ACCENT, 0.85 * tone)
        left = mix(top, BG2, 0.35)
        right = mix(top, BG2, 0.6)
        p = lambda dx, dy: (x + dx * s * 0.87, y + dy * s * 0.5)
        d.polygon([p(0, -1), p(1, 0), p(0, 1), p(-1, 0)], fill=top)
        d.polygon([p(-1, 0), p(0, 1), p(0, 1 + 2), p(-1, 2)], fill=left)
        d.polygon([p(1, 0), p(0, 1), p(0, 3), p(1, 2)], fill=right)

    cells = [(0, 0, 0, 0.5), (1, 0, 0, 0.6), (0, 1, 0, 0.4), (1, 1, 0, 0.5), (2, 0, 0, 0.35), (0, 2, 0, 0.45),
             (0, 0, 1, 0.9), (1, 0, 1, 0.8), (0, 1, 1, 1.0)]
    cells.sort(key=lambda c: (c[0] + c[1] + c[2] * 2, c[2]))
    bob = math.sin(t * 1.5) * 6
    for gx, gy, gz, tone in cells:
        cube(gx - 0.5, gy - 0.5, gz + bob / s, tone * a)


def icon_vault(img, cx, cy, t, a):
    d = ImageDraw.Draw(img)
    rrect(img, (cx - 190, cy - 190, cx + 190, cy + 190), 36, fill=mix(BG, SURFACE, 1), outline=mix(BG, ACCENT, 0.7 * a), width=5)
    d.ellipse((cx - 120, cy - 120, cx + 120, cy + 120), outline=mix(BG, ACCENT, 0.9 * a), width=8)
    d.ellipse((cx - 28, cy - 28, cx + 28, cy + 28), fill=ACCENT)
    for k in range(6):
        ang = t * 0.9 + k * math.pi / 3
        d.line((cx, cy, cx + 120 * math.cos(ang), cy + 120 * math.sin(ang)), fill=mix(BG, TEXT, 0.85 * a), width=9)
        d.ellipse((cx + 120 * math.cos(ang) - 13, cy + 120 * math.sin(ang) - 13,
                   cx + 120 * math.cos(ang) + 13, cy + 120 * math.sin(ang) + 13), fill=TEXT)
    # HUD pips
    for k in range(4):
        on = (int(t * 1.5) % 5) > k
        d.rectangle((cx - 80 + k * 44, cy + 150, cx - 52 + k * 44, cy + 164), fill=ACCENT if on else BORDER)


def icon_hospital(img, cx, cy, t, a):
    d = ImageDraw.Draw(img)
    rrect(img, (cx - 190, cy - 190, cx + 190, cy + 190), 44, fill=SURFACE, outline=mix(BG, ACCENT, 0.7 * a), width=5)
    d.rectangle((cx - 28, cy - 110, cx + 28, cy + 10), fill=ACCENT)
    d.rectangle((cx - 88, cy - 50, cx + 88, cy + 6), fill=ACCENT)
    # pulse line
    pts = []
    for i in range(0, 300, 4):
        x = cx - 150 + i
        ph = (i / 300 * 2 + t * 0.6) % 1
        y = cy + 120
        if 0.30 < ph < 0.36:
            y -= (ph - 0.30) / 0.06 * 50
        elif 0.36 <= ph < 0.42:
            y += (ph - 0.36) / 0.06 * 70 - 50
        elif 0.42 <= ph < 0.48:
            y += 20 - (ph - 0.42) / 0.06 * 20
        pts.append((x, y))
    d.line(pts, fill=TEXT, width=6, joint='curve')


# --- scene content -----------------------------------------------------------------------------
PROJECTS = [
    dict(n='01', title='Museum Heist', sub='AI Guard Lab', tags=['Three.js', 'JavaScript'], icon=icon_radar,
         lines=['A 3D stealth demo with a guard AI', 'state machine: patrol, chase, search.']),
    dict(n='02', title='WebCraft', sub='Voxel sandbox', tags=['Three.js', 'JavaScript'], icon=icon_voxels,
         lines=['Procedural terrain, chunked meshing', 'and collision. Break, place, fly.']),
    dict(n='03', title='Neon Vault', sub='Escape-room game', tags=['Three.js', 'Vite', 'JavaScript'], icon=icon_vault,
         lines=['Ordered objectives, timer, score', 'and a live HUD. Modular design.']),
    dict(n='04', title='Hospital Management', sub='Team project', tags=['HTML', 'CSS', 'PHP', 'MySQL'], icon=icon_hospital,
         lines=['Responsive web system with CRUD', 'for doctor records and a backend.']),
]

SKILLS = [
    ('Game development', [('Unity', 'Intermediate'), ('C#', 'Intermediate'), ('C / C++', 'Intermediate'), ('OOP & gameplay', 'Intermediate')]),
    ('Web & 3D', [('Three.js / JavaScript', 'Basic'), ('Blender', 'Basic'), ('MySQL', 'Basic'), ('Python', 'Basic')]),
    ('AI & automation', [('n8n workflows', 'Workshop'), ('OpenAI / Gemini APIs', 'Workshop'), ('Prompt design', 'Certified'), ('AI-assisted apps', 'Certified')]),
]

# --- timeline ----------------------------------------------------------------------------------
T_ABOUT = 7.0
WIPES = [15.0, 31.0, 40.0, 46.0]
P_START, P_LEN = 15.5, 3.9   # projects: 15.5 -> 31.1 (wipe covers the end)


def scene_at(t):
    if t < WIPES[0]:
        return 'intro' if t < T_ABOUT else 'about'
    if t < WIPES[1]:
        return 'projects'
    if t < WIPES[2]:
        return 'skills'
    if t < WIPES[3]:
        return 'achieve'
    return 'outro'


def avatar(img, t, x, y, a=1.0, wave=False, scale=1.0):
    av = AVATARS[0]
    if scale != 1.0:
        av = av.resize((int(AV_W * scale), int(AV_H * scale)), Image.LANCZOS)
    bob = math.sin(t * 1.6) * 7 * (2.2 if wave else 1.0)
    if wave:
        x += math.sin(t * 6) * 8
    # soft shadow
    sh = Image.new('RGBA', (av.width + 120, av.height + 120), (0, 0, 0, 0))
    sh.paste((0, 0, 0, 110), (60, 70), av.getchannel('A'))
    sh = sh.filter(ImageFilter.GaussianBlur(26))
    paste_rgba(img, sh, (x - 60, y + bob - 60), a)
    paste_rgba(img, av, (x, y + bob), a)


def scene_intro(img, t):
    avx = W - AV_W - 150
    p = out_cubic(prog(t, 0.9, 1.3))
    avatar(img, t, avx, 130 + (1 - p) * 120, a=p)
    text(img, (150, 280), 'HELLO, I\'M', SANS_B(32), ACCENT, a=out_cubic(prog(t, 0.4, 0.8)), tracking=7)
    for i, (word, t0) in enumerate((('Ali Mohammad', 0.9), ('Zaheer', 1.3))):
        p = out_expo(prog(t, t0, 1.1))
        text(img, (146, 345 + i * 140 + (1 - p) * 70), word, SERIF_B(118), TEXT, a=p)
    p = out_cubic(prog(t, 2.6, 0.9))
    text(img, (152, 665 + (1 - p) * 20), 'AI ANALYST  ·  GAME DEVELOPER', SANS_B(34), ACCENT, a=p, tracking=5)
    # accent rule grows
    ImageDraw.Draw(img).rectangle((152, 720, 152 + int(260 * out_cubic(prog(t, 3.0, 0.9))), 726), fill=ACCENT)
    p = out_cubic(prog(t, 3.8, 1.0))
    text(img, (152, 760 + (1 - p) * 20), 'I build 3D browser games and turn project', SANS(38), MUTED, a=p)
    text(img, (152, 810 + (1 - p) * 20), 'data into automation and insight.', SANS(38), MUTED, a=p)


def scene_about(img, t):
    tt = t - T_ABOUT
    avx = W - AV_W - 150
    exit_p = in_out(prog(t, 14.2, 0.8))
    avatar(img, t, avx + exit_p * 80, 130, a=1 - exit_p * 0.0, wave=(8.2 < t < 10.6))
    text(img, (150, 190), 'ABOUT ME', SANS_B(30), ACCENT, a=out_cubic(prog(tt, 0.1, 0.6)), tracking=7)
    p = out_expo(prog(tt, 0.3, 0.9))
    text(img, (146, 245 + (1 - p) * 40), 'Computer Science', SERIF_B(92), TEXT, a=p)
    p = out_expo(prog(tt, 0.55, 0.9))
    text(img, (146, 345 + (1 - p) * 40), 'meets applied AI.', SERIF_I(92), ACCENT, a=p)
    facts = [
        ('BS Computer Science', 'NED University of Engineering & Technology  ·  2023 – 2027'),
        ('Google AI Professional Certificate', 'Seven courses  ·  June 2026'),
        ('Looking for', 'An AI Analyst role: dashboards, reports, automation'),
    ]
    for i, (h, sub) in enumerate(facts):
        p = out_cubic(prog(tt, 1.6 + i * 1.0, 0.8))
        y = 520 + i * 150 + (1 - p) * 30
        rrect(img, (150, y, 1110, y + 118), 20, fill=SURFACE, outline=BORDER, width=2, a=p)
        ImageDraw.Draw(img).rectangle((150 + 2, y + 24, 150 + 8, y + 94), fill=mix(BG, ACCENT, p))
        text(img, (190, y + 18), h, SANS_B(36), TEXT, a=p)
        text(img, (190, y + 66), sub, SANS(27), MUTED, a=p)


def scene_projects(img, t):
    tt = t - P_START
    idx = min(3, int(max(0, tt) // P_LEN))
    loc = tt - idx * P_LEN
    # header
    text(img, (150, 92), 'SELECTED WORK', SANS_B(28), ACCENT, a=out_cubic(prog(tt, 0.0, 0.6)), tracking=7)
    text(img, (W - 150, 92), f'{idx + 1:02d} / 04', SANS_B(28), MUTED, a=out_cubic(prog(tt, 0.0, 0.6)), anchor='ra', tracking=4)
    # progress bar
    ImageDraw.Draw(img).rectangle((150, 150, W - 150, 153), fill=BORDER)
    total = prog(tt, 0, P_LEN * 4 - 0.6)
    ImageDraw.Draw(img).rectangle((150, 150, 150 + int((W - 300) * total), 153), fill=ACCENT)

    proj = PROJECTS[idx]
    enter = out_expo(prog(loc, 0.0, 0.9))
    leave = in_out(prog(loc, P_LEN - 0.45, 0.45)) if idx < 3 else 0
    dx_text = (1 - enter) * 160 - leave * 120
    ta = enter * (1 - leave)
    # big outlined numeral behind
    text(img, (150 + dx_text * 0.5, 430), proj['n'], SERIF_B(420), mix(BG, SURFACE, 1.0 + 0.2), a=ta)
    tsize = 106
    while text_w(proj['title'], SERIF_B(tsize)) > 940:
        tsize -= 4
    text(img, (150 + dx_text, 330 + (106 - tsize) // 2), proj['title'], SERIF_B(tsize), TEXT, a=ta)
    text(img, (154 + dx_text, 470), proj['sub'].upper(), SANS_B(30), ACCENT, a=ta * out_cubic(prog(loc, 0.25, 0.6)), tracking=6)
    for i, ln in enumerate(proj['lines']):
        p = out_cubic(prog(loc, 0.45 + i * 0.15, 0.7))
        text(img, (154 + dx_text, 540 + i * 52 + (1 - p) * 16), ln, SANS(38), MUTED, a=p * (1 - leave))
    x = 154 + dx_text
    for i, tg in enumerate(proj['tags']):
        p = out_back(prog(loc, 0.8 + i * 0.12, 0.5))
        x += chip(img, x, 700, tg, a=clamp(p) * (1 - leave)) + 14
    # visual panel
    pw, ph = 600, 680
    px = W - 150 - pw + (1 - enter) * 260 + leave * 220
    py = 210
    pa = enter * (1 - leave)
    rrect(img, (px, py, px + pw, py + ph), 34, fill=ARCH, a=pa)
    if pa > 0.02:
        panel = Image.new('RGB', (pw, ph), ARCH)
        pd = ImageDraw.Draw(panel)
        # faint grid
        for gx in range(0, pw, 50):
            pd.line((gx, 0, gx, ph), fill=mix(ARCH, BG, 0.25))
        for gy in range(0, ph, 50):
            pd.line((0, gy, pw, gy), fill=mix(ARCH, BG, 0.25))
        proj['icon'](panel, pw // 2, ph // 2, t, 1.0)
        m = Image.new('L', (pw * 2, ph * 2), 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, pw * 2 - 1, ph * 2 - 1), 68, fill=255)
        m = m.resize((pw, ph), Image.LANCZOS).point(lambda v: int(v * pa))
        img.paste(panel, (int(px), int(py)), m)


def scene_skills(img, t):
    tt = t - WIPES[1] - 0.5
    text(img, (150, 110), 'SKILLS', SANS_B(30), ACCENT, a=out_cubic(prog(tt, 0.0, 0.6)), tracking=7)
    p = out_expo(prog(tt, 0.15, 0.9))
    text(img, (146, 175 + (1 - p) * 40), 'What I work with', SERIF_B(86), TEXT, a=p)
    colw = (W - 300 - 2 * 40) // 3
    for c, (title, items) in enumerate(SKILLS):
        cx0 = 150 + c * (colw + 40)
        pc = out_cubic(prog(tt, 0.7 + c * 0.25, 0.8))
        y0 = 330 + (1 - pc) * 50
        rrect(img, (cx0, y0, cx0 + colw, y0 + 600), 26, fill=SURFACE, outline=BORDER, width=2, a=pc)
        text(img, (cx0 + 36, y0 + 34), title, SERIF_B(40), ACCENT, a=pc)
        ImageDraw.Draw(img).rectangle((cx0 + 36, y0 + 98, cx0 + 36 + int(80 * pc), y0 + 101), fill=ACCENT)
        for i, (name, lvl) in enumerate(items):
            pi = out_cubic(prog(tt, 1.2 + c * 0.25 + i * 0.22, 0.6))
            yy_ = y0 + 140 + i * 110 + (1 - pi) * 18
            text(img, (cx0 + 36, yy_), name, SANS_SB(33), TEXT, a=pi)
            tone = {'Basic': 0.3, 'Intermediate': 0.65, 'Workshop': 0.5, 'Certified': 0.95}[lvl]
            fill = mix(SURFACE, ACCENT, tone * 0.5)
            fw = text_w(lvl, SANS_SB(22)) + 28
            rrect(img, (cx0 + 36, yy_ + 50, cx0 + 36 + fw, yy_ + 50 + 36), 18, fill=fill, a=pi)
            text(img, (cx0 + 50, yy_ + 68), lvl, SANS_SB(22), TEXT, a=pi, anchor='lm')


def scene_achieve(img, t):
    tt = t - WIPES[2] - 0.5
    text(img, (150, 120), 'ACHIEVEMENTS', SANS_B(30), ACCENT, a=out_cubic(prog(tt, 0.0, 0.6)), tracking=7)
    p = out_expo(prog(tt, 0.15, 0.9))
    text(img, (146, 185 + (1 - p) * 40), 'Certified & hands-on', SERIF_B(86), TEXT, a=p)
    # two certificate cards
    cards = [
        ('Google AI Professional Certificate', 'Google (Coursera)  ·  June 2026',
         'Seven courses on AI for research, writing, data analysis and app building.'),
        ('n8n + AI Automation Workshop', 'Hands-on workshop',
         'Workflows, AI email & chat automation, OpenAI / Gemini / SerpAPI integrations.'),
    ]
    for i, (h, sub, body) in enumerate(cards):
        p = out_cubic(prog(tt, 0.8 + i * 0.4, 0.8))
        x0 = 150 + i * 870
        y0 = 340 + (1 - p) * 50
        rrect(img, (x0, y0, x0 + 840, y0 + 300), 26, fill=SURFACE, outline=BORDER, width=2, a=p)
        ImageDraw.Draw(img).rectangle((x0 + 2, y0 + 40, x0 + 8, y0 + 260), fill=mix(BG, ACCENT, p))
        text(img, (x0 + 44, y0 + 38), h, SERIF_B(40), TEXT, a=p)
        text(img, (x0 + 44, y0 + 100), sub, SANS_SB(26), ACCENT, a=p)
        text(img, (x0 + 44, y0 + 158), body[: body.rfind(' ', 0, 48)], SANS(28), MUTED, a=p)
        text(img, (x0 + 44, y0 + 200), body[body.rfind(' ', 0, 48) + 1:], SANS(28), MUTED, a=p)
    # counters
    stats = [(4, '', 'Projects built'), (20, '+', 'AI-assisted artifacts'), (3, '', 'Skill areas'), (7, '', 'Google AI courses')]
    for i, (val, suf, label) in enumerate(stats):
        p = out_cubic(prog(tt, 1.9 + i * 0.25, 0.7))
        k = out_cubic(prog(tt, 2.0 + i * 0.25, 1.6))
        x0 = 150 + i * 440
        y0 = 720 + (1 - p) * 30
        text(img, (x0, y0), f'{int(round(val * k))}{suf}', SERIF_B(120), ACCENT, a=p)
        text(img, (x0 + 4, y0 + 150), label, SANS_SB(28), MUTED, a=p)


def scene_outro(img, t):
    tt = t - WIPES[3] - 0.5
    avatar(img, t, 150, 215, a=out_cubic(prog(tt, 0.2, 0.9)), wave=(tt > 0.9 and tt < 3.2), scale=1.0)
    x0 = 150 + AV_W + 120
    p = out_expo(prog(tt, 0.3, 1.0))
    text(img, (x0 - 4, 250 + (1 - p) * 50), "Let's build", SERIF_B(128), TEXT, a=p)
    p = out_expo(prog(tt, 0.6, 1.0))
    text(img, (x0 - 4, 395 + (1 - p) * 50), 'something great.', SERIF_I(128), ACCENT, a=p)
    p = out_cubic(prog(tt, 1.4, 0.8))
    text(img, (x0, 580 + (1 - p) * 20), 'Ali Mohammad Zaheer', SANS_B(46), TEXT, a=p)
    text(img, (x0, 640 + (1 - p) * 20), 'AI analyst  ·  Game developer', SANS(34), MUTED, a=p)
    x = x0
    for i, lab in enumerate(['See my work', 'Chat with my AI', 'Get in touch']):
        pp = out_back(prog(tt, 2.0 + i * 0.2, 0.6))
        w_ = chip(img, x, 740, lab, a=clamp(pp), fnt=SANS_SB(28), fill=ACCENT if i == 0 else SURFACE,
                  outline=ACCENT if i == 0 else BORDER, color=BG if i == 0 else TEXT)
        x += w_ + 18
    # fade to black at the very end
    f = prog(t, DUR - 1.4, 1.2)
    if f > 0:
        img.paste(Image.new('RGB', img.size, BG2), (0, 0), Image.new('L', img.size, int(255 * in_out(f))))


def wipe(img, t):
    """Accent panel that sweeps across the screen at each scene change."""
    for w in WIPES:
        a, b = w - 0.45, w + 0.45
        if a <= t <= b:
            k = (t - a) / (b - a)
            if k < 0.5:
                x1 = int(W * in_out(k * 2))
                x0 = 0
            else:
                x0 = int(W * in_out((k - 0.5) * 2))
                x1 = W
            d = ImageDraw.Draw(img)
            d.rectangle((x0, 0, x1, H), fill=ACCENT)
            # darker trailing band
            edge = x1 if k < 0.5 else x0
            d.rectangle((edge - 60 if k < 0.5 else edge, 0, edge if k < 0.5 else edge + 60, H), fill=ACCENT_D)
            return


def render(t):
    img = BASE_IMG.copy()
    s = scene_at(t)
    draw_shapes(img, t, dim=0.6 if s in ('projects', 'skills', 'achieve') else 1.0)
    if s == 'intro':
        scene_intro(img, t)
    elif s == 'about':
        scene_intro_fade = 1.0
        scene_about(img, t)
        # keep name small in the corner as a lower-third
    elif s == 'projects':
        scene_projects(img, t)
    elif s == 'skills':
        scene_skills(img, t)
    elif s == 'achieve':
        scene_achieve(img, t)
    else:
        scene_outro(img, t)
    if t < 0.6:
        img.paste(Image.new('RGB', img.size, BG2), (0, 0), Image.new('L', img.size, int(255 * (1 - t / 0.6))))
    wipe(img, t)
    return img


def main():
    if PREVIEW:
        outdir = HERE / 'stills'
        outdir.mkdir(exist_ok=True)
        for sec in sys.argv[3].split(','):
            render(float(sec)).save(outdir / f'still_{float(sec):05.1f}.png')
        return
    import imageio_ffmpeg
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg, '-y', '-loglevel', 'error',
        '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
        '-i', AUDIO,
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '21', '-pix_fmt', 'yuv420p', '-profile:v', 'high',
        '-movflags', '+faststart', '-c:a', 'aac', '-b:a', '192k', '-shortest', str(OUT),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = int(DUR * FPS)
    for i in range(n):
        proc.stdin.write(render(i / FPS).tobytes())
        if i % 150 == 0:
            print(f'frame {i}/{n}', flush=True)
    proc.stdin.close()
    proc.wait()
    # poster = first nice frame of the intro
    render(3.5).convert('RGB').save(OUT.parent / 'poster.jpg', quality=88)
    print('done', OUT)


if __name__ == '__main__':
    main()
