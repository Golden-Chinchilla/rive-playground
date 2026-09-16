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
STRIDE, STANCE = 104.0, 0.64
FLOOR = 103.0
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
    return STRIDE*(-.5+u), FLOOR - 34*math.sin(math.pi*q)**2


def knee(hx, hy, ax, ay, rear):
    # Two-link inverse kinematics, baked at authoring time only.
    a, b = (76., 69.) if rear else (72., 73.)
    dx, dy = ax-hx, ay-hy
    d = min(math.hypot(dx, dy), a+b-.01)
    ux, uy = dx/d, dy/d
    along = (a*a-b*b+d*d)/(2*d)
    height = math.sqrt(max(0., a*a-along*along))
    sign = 1 if rear else -1
    return hx+ux*along+sign*uy*height, hy+uy*along-sign*ux*height


def leg(name, phase, rear, far, body_y):
    hx = -91. if rear else 78.
    if far: hx += 11
    hy = -25.+body_y
    dx, fy = foot(phase)
    fx = hx+dx
    ax, ay = fx, fy-20.
    kx, ky = knee(hx, hy, ax, ay, rear)
    w = 17. if rear else 14.
    # One closed outline per leg avoids visible hinges between rigid pieces.
    d = (f'M {hx-w} {hy-14} '
         f'C {hx-w-6} {hy+20} {kx-13} {ky-21} {kx-13} {ky} '
         f'C {kx-13} {ky+19} {ax-12} {ay-20} {ax-12} {ay} '
         f'C {ax-16} {fy-4} {ax-8} {fy} {ax+7} {fy} '
         f'L {ax+25} {fy} '
         f'C {ax+39} {fy} {ax+39} {fy-19} {ax+25} {fy-22} '
         f'L {ax+12} {fy-24} '
         f'C {ax+12} {ay-24} {kx+14} {ky+20} {kx+14} {ky} '
         f'C {kx+14} {ky-23} {hx+w+8} {hy+13} {hx+w} {hy-14} Z')
    return path(name, d, fill=SHADE if far else PAPER, width=7.5)


def cat_scene(t: float):
    phase = (t/(FRAMES/FPS)) % 1.
    wave = TAU*phase
    bob = -2.8*math.cos(2*wave)
    tail = path('Curled tail', 'M 2 13 C -54 22 -108 -8 -121 -55 C -132 -92 -116 -129 -132 -145 C -148 -161 -174 -148 -171 -128 C -167 -111 -186 -108 -193 -124 C -210 -163 -164 -195 -133 -182 C -92 -165 -89 -137 -92 -103 C -96 -62 -49 -14 0 -16 Z')
    tail_node = group('Tail sway', [tail], x=-112, y=-56+bob, rotation=.085*math.sin(wave-.8))
    body = path('Body', 'M -133 -41 C -150 -90 -116 -133 -66 -139 C -12 -151 53 -136 92 -120 C 122 -104 139 -67 121 -32 C 96 4 53 18 -7 14 C -75 16 -112 -3 -133 -41 Z')
    belly = path('Soft belly shade', 'M -116 -20 C -49 21 42 3 91 -30 C 79 10 18 26 -39 16 C -80 9 -104 -2 -116 -20 Z', fill=SHADE, stroke=None)
    # The oversized head, dot eyes, black ears and broad line echo the reference.
    head_parts = [
        path('Head', 'M -77 -51 C -96 -75 -99 -105 -89 -128 L -96 -189 C -98 -207 -87 -215 -73 -201 L -29 -161 C -3 -168 23 -167 48 -156 L 79 -190 C 94 -207 110 -201 109 -181 L 107 -122 C 131 -91 133 -59 116 -32 C 97 -1 62 11 16 9 C -25 9 -55 -13 -77 -51 Z'),
        path('Left ear ink', 'M -77 -185 C -78 -191 -73 -192 -68 -186 L -43 -163 C -52 -157 -63 -152 -73 -151 Z', fill=INK, stroke=None),
        path('Right ear ink', 'M 66 -153 L 92 -181 C 96 -186 99 -183 99 -177 L 97 -142 Z', fill=INK, stroke=None),
        ellipse('Left eye', -22, -80, 7, 8),
        ellipse('Right eye', 65, -84, 7, 8),
        path('Nose', 'M 31 -64 C 38 -68 49 -68 56 -65 C 63 -61 49 -48 44 -48 C 39 -48 25 -59 31 -64 Z', fill=INK, stroke=None),
        path('Smile', 'M 15 -37 C 23 -25 43 -27 44 -46 C 47 -25 68 -25 74 -40', fill=None, width=6),
        path('Whisker left top', 'M -46 -55 C -59 -59 -73 -60 -85 -60', fill=None, width=5.5),
        path('Whisker left bottom', 'M -47 -42 C -60 -42 -72 -38 -79 -34', fill=None, width=5.5),
        path('Whisker right top', 'M 99 -59 C 111 -64 127 -65 139 -64', fill=None, width=5.5),
        path('Whisker right bottom', 'M 100 -46 C 111 -48 128 -47 139 -44', fill=None, width=5.5),
    ]
    head = group('Head follow-through', head_parts, x=98, y=-82+bob*.75, rotation=.018*math.sin(2*wave-.65))
    torso = group('Body bounce', [body, belly], y=bob, rotation=.012*math.sin(wave))
    # Anatomical left/right remain fixed; far limbs precede near limbs in depth.
    parts = [tail_node,
             leg('Far hind leg', phase+.50, True, True, bob),
             leg('Far fore leg', phase+.75, False, True, bob),
             leg('Near hind leg', phase, True, False, bob),
             leg('Near fore leg', phase+.25, False, False, bob),
             torso, head]
    art = element('Artboard', name='Cat Walk', id='0:2', width=WIDTH, height=HEIGHT, defaultStateMachineId='0:7', styleId='0:5')
    art.append(element('LayoutComponentStyle', id='0:5'))
    art.append(group('Cat', parts, x=409, y=369))
    art.append(ellipse('Ground shadow', 405, 478, 151, 9, fill='#e8e8e8'))
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
