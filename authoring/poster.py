"""Font-free, editable vector UI for the Character Lab poster.

The small stroke alphabet is original geometry, not an embedded font. RML
children are in front-to-back order; helpers accept ordinary painter order.
Only element types already used by the character are needed here.
"""
from __future__ import annotations

import math
from html import escape

WIDTH, HEIGHT = 1280, 860
CHARACTER_X, CHARACTER_Y, CHARACTER_SCALE = 316, 120, 0.86
INK, PAPER, MUTED, LINE = 'FF111111', 'FFF7F7F4', 'FF777773', 'FFDADAD4'

# A 4 x 6 monoline alphabet. Separate polylines with a semicolon.
GLYPHS = {
    'A': '0,6 0,2 2,0 4,2 4,6;0,3.5 4,3.5',
    'B': '0,0 0,6 2.8,6 4,5 4,4 2.8,3 0,3;0,0 2.8,0 4,1 4,2 2.8,3',
    'C': '4,0.5 3,0 1,0 0,1 0,5 1,6 3,6 4,5.5',
    'D': '0,0 0,6 2.5,6 4,4.5 4,1.5 2.5,0 0,0',
    'E': '4,0 0,0 0,6 4,6;0,3 3,3',
    'F': '4,0 0,0 0,6;0,3 3,3',
    'G': '4,1 3,0 1,0 0,1 0,5 1,6 3,6 4,5 4,3.5 2.5,3.5',
    'H': '0,0 0,6;4,0 4,6;0,3 4,3',
    'I': '0,0 4,0;2,0 2,6;0,6 4,6',
    'J': '0,0 4,0 4,5 3,6 1,6 0,5 0,4',
    'K': '0,0 0,6;4,0 0,3 4,6',
    'L': '0,0 0,6 4,6',
    'M': '0,6 0,0 2,3 4,0 4,6',
    'N': '0,6 0,0 4,6 4,0',
    'O': '1,0 3,0 4,1 4,5 3,6 1,6 0,5 0,1 1,0',
    'P': '0,6 0,0 3,0 4,1 4,2 3,3 0,3',
    'Q': '1,0 3,0 4,1 4,5 3,6 1,6 0,5 0,1 1,0;2.5,4.5 4.5,6.5',
    'R': '0,6 0,0 3,0 4,1 4,2 3,3 0,3;2,3 4,6',
    'S': '4,0.5 3,0 1,0 0,1 0,2 1,3 3,3 4,4 4,5 3,6 1,6 0,5.5',
    'T': '0,0 4,0;2,0 2,6',
    'U': '0,0 0,5 1,6 3,6 4,5 4,0',
    'V': '0,0 2,6 4,0',
    'W': '0,0 0.7,6 2,3 3.3,6 4,0',
    'X': '0,0 4,6;4,0 0,6',
    'Y': '0,0 2,3 4,0;2,3 2,6',
    'Z': '0,0 4,0 0,6 4,6',
    '0': '1,0 3,0 4,1 4,5 3,6 1,6 0,5 0,1 1,0;1,4.5 3,1.5',
    '1': '0.5,1.5 2,0 2,6;0,6 4,6',
    '2': '0,1 1,0 3,0 4,1 4,2 0,6 4,6',
    '3': '0,0 4,0 2,3 4,4 4,5 3,6 0,6;1.5,3 2,3',
    '4': '3,6 3,0 0,4 4,4',
    '5': '4,0 0,0 0,3 3,3 4,4 4,5 3,6 0,6',
    '6': '4,0 1,0 0,1 0,5 1,6 3,6 4,5 4,4 3,3 0,3',
    '7': '0,0 4,0 1,6',
    '8': '1,0 3,0 4,1 4,2 3,3 1,3 0,2 0,1 1,0;1,3 0,4 0,5 1,6 3,6 4,5 4,4 3,3',
    '9': '4,3 1,3 0,2 0,1 1,0 3,0 4,1 4,5 3,6 0,6',
    '.': '2,5.7 2,6', ',': '2,5 1.5,6.5',
    '/': '0,6 4,0', '-': '0,3 4,3', '+': '0,3 4,3;2,1 2,5',
    ':': '2,1.5 2,1.7;2,4.5 2,4.7', '!': '2,0 2,3.7;2,5.7 2,6',
    '?': '0,1 1,0 3,0 4,1 4,2 2,3.5 2,4;2,5.7 2,6',
}


def number(value: float) -> str:
    return f'{value:.4f}'.rstrip('0').rstrip('.') or '0'


def paint(fill: str | None, stroke: str | None, width: float) -> str:
    result = f'<Fill><SolidColor colorValue="{fill}"/></Fill>' if fill else ''
    if stroke:
        result += (f'<Stroke thickness="{number(width)}" cap="round" join="round">'
                   f'<SolidColor colorValue="{stroke}"/></Stroke>')
    return result


def poly(name, points, *, fill=None, stroke=INK, width=2, closed=False):
    vertices = ''.join(f'<StraightVertex x="{number(x)}" y="{number(y)}"/>' for x, y in points)
    return (f'<Shape name="{escape(name, quote=True)}"><PointsPath isClosed="{str(closed).lower()}">'
            f'{vertices}</PointsPath>{paint(fill, stroke, width)}</Shape>')


def rect(name, x, y, w, h, *, fill=PAPER, stroke=INK, width=2):
    return poly(name, [(x, y), (x+w, y), (x+w, y+h), (x, y+h)],
                fill=fill, stroke=stroke, width=width, closed=True)


def ellipse(name, x, y, w, h=None, *, fill=None, stroke=INK, width=2):
    if h is None:
        h = w
    return (f'<Shape name="{escape(name, quote=True)}"><Ellipse x="{number(x)}" y="{number(y)}" '
            f'width="{number(w)}" height="{number(h)}"/>{paint(fill, stroke, width)}</Shape>')


def group(name, children, *, x=0, y=0, rotation=0, bindings=''):
    return (f'<Node name="{escape(name, quote=True)}" x="{number(x)}" y="{number(y)}" '
            f'rotation="{number(rotation)}">{bindings}{"".join(reversed(children))}</Node>')


def text(value, x, y, size=12, *, color=INK, weight=None, tracking=3.1):
    """Render original monoline lettering without Text/FontAsset dependencies."""
    scale = size / 6
    width = weight if weight is not None else max(1.15, size * .105)
    shapes = []
    for index, char in enumerate(value.upper()):
        if char == ' ':
            continue
        if char not in GLYPHS:
            raise ValueError(f'Unsupported poster character: {char!r}')
        for contour, line in enumerate(GLYPHS[char].split(';')):
            points = [tuple(float(n) for n in p.split(',')) for p in line.split()]
            shapes.append(poly(f'{char}-{index}-{contour}',
                               [(x + index*(4*scale+tracking) + a*scale, y + b*scale)
                                for a, b in points], stroke=color, width=width))
    return group(f'Label: {value}', shapes)


def star(name, x, y, radius, *, spokes=8):
    pts = []
    for i in range(spokes * 2):
        a = i * math.pi / spokes
        r = radius if i % 2 == 0 else radius * .31
        pts.append((x + math.cos(a)*r, y + math.sin(a)*r))
    return poly(name, pts, fill=INK, stroke=None, closed=True)


def build_poster(bind):
    """Return foreground/background nodes, registering UI data bindings."""
    back = [rect('Paper', 0, 0, WIDTH, HEIGHT, stroke=None)]
    # A restrained editorial frame rather than a full-screen dashboard.
    back += [poly('Header rule', [(48, 83), (1232, 83)], width=1.5),
             star('Lab mark', 61, 49, 14),
             text('CHARACTER / LAB', 90, 44, 14, weight=1.8),
             text('AN INTERACTIVE PORTRAIT', 880, 45, 11),
             text('VOL. 01', 1153, 45, 11)]
    # The dot field and ring sit behind the character, not over its face.
    back += [ellipse('Portrait disk', 646, 440, 526, fill='FFECECE6', stroke=None),
             ellipse('Portrait orbit', 646, 440, 554, stroke=INK, width=1.6)]
    for i in range(7):
        for j in range(5):
            back.append(ellipse(f'Dot field {i}-{j}', 370+i*17, 589+j*17, 2.2,
                                fill='FFB0B0A8', stroke=None))
    back += [text('LOOK', 60, 161, 69, weight=11, tracking=13),
             text('ALIVE.', 60, 251, 69, weight=11, tracking=13),
             text('A LITTLE PERSONALITY.', 61, 365, 11),
             text('A LOT OF CURIOSITY.', 61, 386, 11),
             text('01 / CHARACTER STUDIES', 61, 423, 9, color=MUTED),
             star('Orbit spark', 885, 619, 24),
             poly('Orbit tick top', [(646, 151), (646, 167)], width=2),
             poly('Orbit tick right', [(923, 440), (938, 440)], width=2),
             text('NOT JUST A PRETTY FACE.', 450, 716, 10, color=MUTED)]

    front = []
    # A note card with a deliberate offset hard shadow.
    note = [rect('Note shadow', 6, 6, 248, 185, fill=INK, stroke=None),
            rect('Note paper', 0, 0, 248, 185, fill='FFFFFFFF', width=2.5),
            text('FIELD NOTES', 18, 20, 11),
            poly('Note rule', [(18, 44), (230, 44)], stroke=LINE, width=1.5),
            text('MOVE YOUR', 18, 66, 17, weight=2),
            text('CURSOR.', 18, 94, 17, weight=2),
            text('I WILL FOLLOW.', 18, 140, 10, color=MUTED),
            poly('Note arrow', [(205, 150), (223, 132), (211, 132)], width=2),
            poly('Note arrow tail', [(223, 132), (223, 144)], width=2)]
    front.append(group('Field notes card', note, x=58, y=474, rotation=-.025))

    bubble = [rect('Bubble shadow', 5, 5, 216, 80, fill=INK, stroke=None),
              poly('Bubble paper', [(0,0), (216,0), (216,80), (49,80), (24,101), (28,80), (0,80)],
                   fill='FFFFFFFF', closed=True, width=2.5),
              text('OH, HELLO.', 21, 30, 20, weight=2.2)]
    front.append(group('Greeting bubble', bubble, x=839, y=116,
                       bindings=bind('bubbleY', 14, 116)))

    status = [rect('Status shadow', 6, 6, 266, 156, fill=INK, stroke=None),
              rect('Status paper', 0, 0, 266, 156, fill='FFFFFFFF', width=2.5),
              text('IN MY HEAD', 20, 19, 10, color=MUTED),
              text('CURIOUS.', 20, 48, 27, weight=3, tracking=4),
              poly('Status divider', [(20, 97), (246, 97)], stroke=LINE, width=1),
              ellipse('Status dot', 25, 122, 7, fill=INK, stroke=None),
              text('MADE TO NOTICE.', 40, 118, 10)]
    front.append(group('Personality card', status, x=953, y=292,
                       bindings=bind('statusY', 14, 292)))

    tracker = [rect('Tracker paper', 0, 0, 266, 204, fill='FFFFFFFF', width=2.5),
               text('GAZE TRACKER', 20, 20, 11),
               poly('Tracker divider', [(20, 45), (246, 45)], stroke=LINE, width=1),
               rect('Gaze field', 20, 62, 118, 110, fill=PAPER, stroke=LINE, width=1),
               poly('Gaze axis X', [(20,117), (138,117)], stroke=LINE, width=1),
               poly('Gaze axis Y', [(79,62), (79,172)], stroke=LINE, width=1),
               ellipse('Gaze center', 79, 117, 48, stroke=LINE, width=1),
               text('X', 156, 80, 10), text('Y', 156, 127, 10),
               poly('X meter track', [(179,85),(245,85)], stroke=LINE, width=4),
               poly('Y meter track', [(179,132),(245,132)], stroke=LINE, width=4),
               text('EYES FIRST. HEAD SECOND.', 20, 187, 8, color=MUTED)]
    tracker += [group('Gaze dot', [ellipse('Gaze ring', 0, 0, 18, fill='FFFFFFFF', width=1.8),
                                   ellipse('Gaze core', 0, 0, 6, fill=INK, stroke=None)],
                      x=79, y=117, bindings=bind('gazeX', 13, 79)+bind('gazeY', 14, 117)),
                group('X meter thumb', [ellipse('X thumb', 0, 85, 7, fill=INK, stroke=None)],
                      x=212, bindings=bind('meterX', 13, 212)),
                group('Y meter thumb', [ellipse('Y thumb', 0, 132, 7, fill=INK, stroke=None)],
                      x=212, bindings=bind('meterY', 13, 212))]
    front.append(group('Gaze tracker card', tracker, x=953, y=487))

    # Keep hit regions in one predictable strip; coordinates are tested in tests/.
    controls = [rect('Control strip', 48, 748, 1184, 74, fill='FFFFFFFF', width=2.5),
                text('PLAY WITH ME', 52, 733, 9, color=MUTED)]
    for index, label in enumerate(('FOLLOW', 'IDLE', 'WANDER')):
        x = 64 + index*180
        controls += [rect(f'{label} button', x, 760, 164, 49, fill=PAPER, width=1.5),
                     text(f'0{index+1}', x+12, 779, 9, color=MUTED),
                     text(label, x+42, 777, 13, weight=1.6)]
    controls += [group('Selected mode underline', [rect('Mode ink', 0, 804, 140, 4, fill=INK, stroke=None)],
                       x=76, bindings=bind('modeX', 13, 76)),
                 rect('Reset button', 613, 760, 118, 49, fill='FFFFFFFF', width=1.5),
                 text('RESET', 641, 778, 13, weight=1.6),
                 text('MOVE / EXPLORE / REPEAT', 773, 779, 10, color=MUTED),
                 star('Footer spark', 1198, 785, 15)]
    front.append(group('Mode controls', controls))
    front += [text('BUILT FROM CURIOSITY.', 49, 840, 8, color=MUTED),
              text('BLACK / WHITE / VERY MUCH ALIVE', 977, 840, 8, color=MUTED)]
    return group('Poster foreground', front), group('Poster background', back)
