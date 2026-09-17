#!/usr/bin/env python3
"""Author an original vector cat and bake a four-beat walk to native Rive keys.

No bitmap, Luau script, font, external Python dependency, or runtime IK is used.
Rive property keys were checked with CLI 1.0.4 `rive schema`.
"""
from __future__ import annotations
import argparse
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WIDTH, HEIGHT = 800, 560
FPS, FRAMES, SAMPLE_STEP = 60, 72, 2
STRIDE, STANCE = 68.0, 0.66
SWING_LIFT = 18.0
FLOOR = 128.0
INK, PAPER, SHADE = '#111111', '#ffffff', '#d9d9d9'
TAU = math.tau
SVG = 'http://www.w3.org/2000/svg'
ET.register_namespace('', SVG)
TRANSFORM_KEYS = {'x': 13, 'y': 14, 'rotation': 15, 'scaleX': 16, 'scaleY': 17, 'opacity': 18}
VERTEX_KEYS = {'x': 24, 'y': 25, 'inRotation': 84, 'inDistance': 85, 'outRotation': 86, 'outDistance': 87}


def fmt(n: float) -> str:
    return f'{n:.5f}'.rstrip('0').rstrip('.') or '0'


def element(tag: str, **attrs) -> ET.Element:
    return ET.Element(tag, {k: fmt(v) if isinstance(v, (float, int)) else str(v) for k, v in attrs.items()})


def group(name: str, children: list[ET.Element], x=0., y=0., rotation=0., scaleX=1., scaleY=1.):
    node = element('Node', name=name, x=x, y=y, rotation=rotation, scaleX=scaleX, scaleY=scaleY)
    # RML sibling draw order is front-to-back, opposite SVG painter order.
    node.extend(reversed(children))
    return node


def vertices(d: str):
    """The authoring paths deliberately use only absolute M/L/C/Z commands."""
    tokens = re.findall(r'[MLCZ]|[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?', d)
    result, i, closed = [], 0, False
    while i < len(tokens):
        cmd = tokens[i]; i += 1
        if cmd == 'Z':
            closed = True
            continue
        count = {'M': 2, 'L': 2, 'C': 6}[cmd]
        values = [float(v) for v in tokens[i:i+count]]; i += count
        if cmd == 'C':
            result[-1]['out'] = values[:2]
            result.append({'point': values[4:], 'in': values[2:4]})
        else:
            result.append({'point': values})
    if closed and len(result) > 1 and result[-1]['point'] == result[0]['point']:
        if 'in' in result[-1]:
            result[0]['in'] = result[-1]['in']
        result.pop()
    return result, closed


def path(name: str, d: str, fill=PAPER, stroke=INK, width=8.):
    shape = element('Shape', name=name)
    vs, closed = vertices(d)
    curve = element('PointsPath', name=name+' contour', isClosed=str(closed).lower())
    for i, v in enumerate(vs):
        x, y = v['point']
        a = {'name': f'{name} point {i}', 'x': x, 'y': y}
        cubic = 'in' in v or 'out' in v
        if cubic:
            for side in ('in', 'out'):
                u, w = v.get(side, (x, y)); dx, dy = u-x, w-y
                a[side+'Rotation'] = math.atan2(dy, dx)
                a[side+'Distance'] = math.hypot(dx, dy)
        curve.append(element('CubicDetachedVertex' if cubic else 'StraightVertex', **a))
    shape.append(curve)
    paint(shape, fill, stroke, width)
    return shape


def paint(shape, fill, stroke, width):
    for tag, color in (('Fill', fill), ('Stroke', stroke)):
        if color is None:
            continue
        p = element(tag, **({'thickness': width, 'cap': 'round', 'join': 'round'} if tag == 'Stroke' else {}))
        p.append(element('SolidColor', colorValue='FF'+color.lstrip('#')))
        shape.append(p)


def ellipse(name, x, y, rx, ry, fill=INK, stroke=None, width=8.):
    shape = element('Shape', name=name)
    shape.append(element('Ellipse', x=x, y=y, width=rx*2, height=ry*2))
    paint(shape, fill, stroke, width)
    return shape


def foot(phase: float):
    p = phase % 1.
    if p < STANCE:
        # Constant ground speed while planted: no backward skating.
        return STRIDE*(.5-p/STANCE), FLOOR
    q = (p-STANCE)/(1-STANCE)
    # Hermite swing matches the stance velocity at lift-off and touchdown.
    m = -(1-STANCE)/STANCE
    u = (-2*q**3+3*q**2) + m*(2*q**3-3*q**2+q)
    return STRIDE*(-.5+u), FLOOR - SWING_LIFT*math.sin(math.pi*q)**2


def knee(hx, hy, ax, ay, rear):
    # Two-link inverse kinematics, baked at authoring time only.
    a, b = (58., 54.) if rear else (54., 50.)
    dx, dy = ax-hx, ay-hy
    d = min(math.hypot(dx, dy), a+b-.01)
    ux, uy = dx/d, dy/d
    along = (a*a-b*b+d*d)/(2*d)
    height = math.sqrt(max(0., a*a-along*along))
    sign = 1 if rear else -1
    return hx+ux*along+sign*uy*height, hy+uy*along-sign*ux*height


def leg(name, phase, rear, far, body_y):
    hx = -56. if rear else 54.
    if far: hx += 8
    hy = 24.+body_y
    dx, fy = foot(phase)
    fx = hx+dx
    ax, ay = fx, fy-20.
    kx, ky = knee(hx, hy, ax, ay, rear)
    w = 22. if rear else 20.
    paw = 18.
    # Chunkier continuous outline keeps the original sticker-like proportions.
    d = (f'M {hx-w} {hy-18} '
         f'C {hx-w-4} {hy+8} {kx-12} {ky-16} {kx-12} {ky} '
         f'C {kx-12} {ky+12} {ax-12} {ay-14} {ax-11} {ay} '
         f'C {ax-13} {fy-4} {ax-7} {fy} {ax+4} {fy} '
         f'L {ax+paw} {fy} '
         f'C {ax+paw+10} {fy} {ax+paw+11} {fy-13} {ax+paw+4} {fy-17} '
         f'L {ax+10} {fy-19} '
         f'C {ax+10} {ay-18} {kx+12} {ky+12} {kx+12} {ky} '
         f'C {kx+12} {ky-18} {hx+w+4} {hy+8} {hx+w} {hy-18} Z')
    return path(name, d, fill=SHADE if far else PAPER, width=7.5)


def cat_scene(t: float):
    phase = (t/(FRAMES/FPS)) % 1.
    wave = TAU*phase
    bob = -2.8*math.cos(2*wave)
    tail = path('Curled tail', 'M -2 9 C -48 9 -88 -11 -104 -48 C -119 -82 -112 -122 -127 -141 C -139 -156 -160 -144 -156 -126 C -152 -110 -167 -105 -171 -119 C -182 -151 -149 -175 -121 -164 C -87 -151 -77 -118 -76 -87 C -75 -49 -41 -13 -2 -12 Z')
    tail_node = group('Tail sway', [tail], x=-106, y=-8+bob, rotation=.07*math.sin(wave-.7))
    body = path('Body', 'M -122 -8 C -125 -60 -97 -102 -46 -112 C 12 -123 76 -108 108 -76 C 130 -54 136 -14 121 24 C 102 64 57 86 -4 86 C -67 86 -108 58 -120 14 C -123 6 -122 -1 -122 -8 Z')
    belly = path('Soft belly shade', 'M -94 38 C -46 65 32 60 87 28 C 76 55 32 75 -20 74 C -54 72 -79 58 -94 38 Z', fill=SHADE, stroke=None)
    # Keep the big round head and facial proportions close to the original sticker.
    head_parts = [
        path('Head', 'M -82 -28 C -96 -47 -103 -74 -100 -101 C -98 -118 -92 -131 -86 -142 L -92 -182 C -94 -198 -84 -205 -71 -193 L -34 -160 C -3 -169 30 -167 58 -157 L 92 -188 C 105 -199 114 -192 112 -175 L 108 -137 C 124 -118 132 -96 131 -72 C 129 -42 114 -16 92 0 C 72 13 45 20 14 20 C -31 20 -62 4 -82 -28 Z'),
        path('Left ear ink', 'M -78 -177 C -79 -183 -74 -184 -69 -179 L -46 -159 C -57 -153 -68 -148 -80 -146 Z', fill=INK, stroke=None),
        path('Right ear ink', 'M 66 -149 L 88 -173 C 92 -178 96 -175 96 -169 L 94 -139 Z', fill=INK, stroke=None),
        ellipse('Left eye', -22, -68, 7.5, 8.5),
        ellipse('Right eye', 58, -71, 7.5, 8.5),
        path('Nose', 'M 16 -57 C 25 -63 39 -63 47 -57 C 54 -52 40 -41 32 -41 C 24 -41 10 -51 16 -57 Z', fill=INK, stroke=None),
        path('Smile', 'M 3 -30 C 10 -15 32 -14 33 -40 C 37 -17 59 -16 66 -31', fill=None, width=6.5),
        path('Whisker left top', 'M -42 -52 C -56 -56 -72 -58 -87 -58', fill=None, width=5.8),
        path('Whisker left bottom', 'M -40 -38 C -55 -39 -71 -34 -84 -27', fill=None, width=5.8),
        path('Whisker right top', 'M 85 -52 C 100 -57 118 -58 131 -57', fill=None, width=5.8),
        path('Whisker right bottom', 'M 86 -40 C 100 -42 118 -41 130 -37', fill=None, width=5.8),
    ]
    head = group('Head follow-through', head_parts, x=74, y=-58+bob*.7, rotation=.014*math.sin(2*wave-.6))
    torso = group('Body bounce', [body, belly], y=bob, rotation=.009*math.sin(wave))
    # Anatomical left/right remain fixed; far limbs precede near limbs in depth.
    parts = [tail_node,
             leg('Far hind leg', phase+.50, True, True, bob),
             leg('Far fore leg', phase+.75, False, True, bob),
             leg('Near hind leg', phase, True, False, bob),
             leg('Near fore leg', phase+.25, False, False, bob),
             torso, head]
    art = element('Artboard', name='Cat Walk', id='0:2', width=WIDTH, height=HEIGHT, defaultStateMachineId='0:7', styleId='0:5')
    art.append(element('LayoutComponentStyle', id='0:5'))
    art.append(group('Cat', parts, x=404, y=344))
    art.append(ellipse('Ground shadow', 402, 478, 134, 10, fill='#e8e8e8'))
    return art


def assign_ids(art):
    for i, node in enumerate(art.iter()):
        if 'id' not in node.attrib:
            node.set('id', f'0:{100+i}')


def build_rml():
    art = cat_scene(0.)
    assign_ids(art)
    frames = list(range(0, FRAMES+1, SAMPLE_STEP))
    poses = [list(cat_scene(f/FPS).iter()) for f in frames]
    original = list(art.iter())
    animation = element('LinearAnimation', name='Walk', id='0:6', duration=FRAMES, fps=FPS, loopValue='loop')
    for index, node in enumerate(original):
        keys = VERTEX_KEYS if node.tag.endswith('Vertex') else TRANSFORM_KEYS if node.tag in ('Node', 'Shape') else {}
        keyed = element('KeyedObject', objectId=node.attrib['id'])
        for attr, key in keys.items():
            if attr not in node.attrib:
                continue
            values = [float(p[index].attrib[attr]) for p in poses]
            if max(values)-min(values) < 0.0001:
                continue
            if attr.endswith('Rotation') or attr == 'rotation':
                for i in range(1, len(values)):
                    values[i] += TAU*round((values[i-1]-values[i])/TAU)
            prop = element('KeyedProperty', propertyKey=key)
            for f, value in zip(frames, values):
                prop.append(element('KeyFrameDouble', frame=f, value=value, interpolationType='linear'))
            keyed.append(prop)
        if len(keyed):
            animation.append(keyed)
    art.append(animation)
    sm = element('StateMachine', name='Cat', id='0:7')
    layer = element('StateMachineLayer', name='Locomotion', id='0:8')
    entry = element('EntryState'); entry.append(element('StateTransition', stateToId='0:12'))
    layer.extend([entry, element('AnimationState', animationId='0:6', id='0:12', x=200), element('AnyState', x=200, y=-120), element('ExitState', x=400, y=-120)])
    sm.append(layer); art.append(sm)
    root = element('Rive', version='1', kind='fragment'); root.append(art)
    ET.indent(root, space='  ')
    return ET.tostring(root, encoding='unicode')+'\n'


def svg_at(t=0.):
    """Design proof from authoring geometry; NOT a native Rive runtime render."""
    art = cat_scene(t)
    out = element('svg', xmlns=SVG, width=WIDTH, height=HEIGHT, viewBox=f'0 0 {WIDTH} {HEIGHT}')
    def draw(node, parent):
        a = node.attrib
        if node.tag not in ('Node', 'Shape'):
            return
        g = element('g', transform=f'translate({a.get("x",0)} {a.get("y",0)}) rotate({float(a.get("rotation",0))*180/math.pi}) scale({a.get("scaleX",1)} {a.get("scaleY",1)})')
        parent.append(g)
        if node.tag == 'Node':
            for child in reversed(list(node)): draw(child, g)
            return
        style = {'fill': 'none', 'stroke': 'none'}
        for tag, key in (('Fill','fill'), ('Stroke','stroke')):
            p = node.find(tag)
            if p is not None:
                style[key] = '#'+p.find('SolidColor').attrib['colorValue'][-6:]
                if tag == 'Stroke':
                    style.update({'stroke-width': p.attrib['thickness'], 'stroke-linejoin': 'round', 'stroke-linecap': 'round'})
        for p in node:
            if p.tag == 'Ellipse':
                a = p.attrib
                g.append(element('ellipse', cx=a['x'], cy=a['y'], rx=float(a['width'])/2, ry=float(a['height'])/2, **style))
            elif p.tag == 'PointsPath':
                vs = list(p); d = [f'M {vs[0].attrib["x"]} {vs[0].attrib["y"]}']
                pairs = list(zip(vs, vs[1:]))
                if p.attrib['isClosed'] == 'true': pairs.append((vs[-1], vs[0]))
                for v, w in pairs:
                    def control(v, side):
                        a=v.attrib; r=float(a.get(side+'Rotation',0)); z=float(a.get(side+'Distance',0))
                        return float(a['x'])+z*math.cos(r),float(a['y'])+z*math.sin(r)
                    if float(v.attrib.get('outDistance',0)) or float(w.attrib.get('inDistance',0)):
                        x,y=control(v,'out');u,z=control(w,'in')
                        d.append(f'C {x} {y} {u} {z} {w.attrib["x"]} {w.attrib["y"]}')
                    else: d.append(f'L {w.attrib["x"]} {w.attrib["y"]}')
                if p.attrib['isClosed']=='true': d.append('Z')
                g.append(element('path', d=' '.join(d), **style))
    for c in reversed(list(art)): draw(c,out)
    return ET.tostring(out, encoding='unicode')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Fail if the checked-in RML is stale.')
    args = parser.parse_args()
    scene = build_rml()
    dest = ROOT/'scene.rml'
    if args.check:
        if not dest.exists() or dest.read_text() != scene:
            raise SystemExit('cat/scene.rml is stale; run python3 cat/build.py')
        print('Cat source and scene are synchronized.')
        return
    dest.write_text(scene, encoding='utf-8')
    (ROOT/'build').mkdir(exist_ok=True)
    (ROOT/'build/design-proof.svg').write_text(svg_at(), encoding='utf-8')
    print(f'Wrote {dest}: {len(scene):,} characters; {FRAMES/FPS:.1f}s seamless walk.')


if __name__ == '__main__':
    main()
