#!/usr/bin/env python3
"""Author a consistent side-profile cat and bake a four-beat walk to Rive keys.

No bitmap, Luau script, font, external Python dependency, or runtime IK is used.
Existing Rive property keys are retained from the CLI-verified project.
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
STRIDE, STANCE = 96.0, 0.66
SWING_LIFT = 24.0
FLOOR = 128.0
INK, PAPER, SHADE = '#111111', '#ffffff', '#d9d9d9'
TAU = math.tau
SVG = 'http://www.w3.org/2000/svg'
ET.register_namespace('', SVG)
TRANSFORM_KEYS = {'x': 13, 'y': 14, 'rotation': 15, 'scaleX': 16, 'scaleY': 17, 'opacity': 18}
VERTEX_KEYS = {'x': 24, 'y': 25, 'inRotation': 84, 'inDistance': 85, 'outRotation': 86, 'outDistance': 87}
# Fixed anatomical identities. Touchdowns: near hind -> near fore -> far hind -> far fore.
LEG_PHASES = {'Near hind leg': 0., 'Near fore leg': .75,
              'Far hind leg': .50, 'Far fore leg': .25}
HIND_HIP, FORE_HIP, HIP_Y = -76., 64., 24.
KEY_POSES = tuple(range(0, FRAMES+1, FRAMES//8))  # 0..72; last pose closes the loop.


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
        # Constant ground speed while planted; matched by the optional web travel.
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
    distance = math.hypot(dx, dy)
    if not abs(a-b) < distance < a+b:
        raise ValueError(f'Unreachable paw target: {distance:.3f} for links {a}, {b}')
    ux, uy = dx/distance, dy/distance
    along = (a*a-b*b+distance*distance)/(2*distance)
    height = math.sqrt(max(0., a*a-along*along))
    sign = 1 if rear else -1
    return hx+ux*along+sign*uy*height, hy+uy*along-sign*ux*height


def leg(name, phase, rear, far, body_y):
    hx = HIND_HIP if rear else FORE_HIP
    if far: hx += 8
    hy = HIP_Y+body_y
    dx, fy = foot(phase)
    ax, ay = hx+dx, fy-20.
    kx, ky = knee(hx, hy, ax, ay, rear)
    # Soften the IK bend into the rounded, short-limbed reference silhouette.
    # The raw two-link solution remains available for reachability checks.
    kx = .25*kx + .75*(hx+ax)/2
    ky = .25*ky + .75*(hy+ay)/2
    w = 30. if rear else 28.
    paw = 20.
    # One continuous closed contour per limb, not overlapping capsule joints.
    d = (f'M {hx-w} {hy+16} '
         f'C {hx-w-4} {hy+30} {kx-18} {ky-17} {kx-18} {ky} '
         f'C {kx-18} {ky+13} {ax-17} {ay-12} {ax-16} {ay} '
         f'C {ax-18} {fy-4} {ax-8} {fy} {ax+4} {fy} '
         f'L {ax+paw} {fy} '
         f'C {ax+paw+11} {fy} {ax+paw+12} {fy-14} {ax+paw+4} {fy-18} '
         f'L {ax+14} {fy-21} '
         f'C {ax+15} {ay-15} {kx+18} {ky+13} {kx+18} {ky} '
         f'C {kx+18} {ky-17} {hx+w+4} {hy+30} {hx+w} {hy+16}')
    if far:
        return path(name, d+' Z', fill='#ededed', width=7.5)
    # Closed fill + open outline gives round attachment ends without a black
    # cap through the torso. Both paths share exactly the same animated geometry.
    return group(name+' limb', [path(name, d+' Z', stroke=None),
                                path(name+' outline', d, fill=None, width=7.5)])


def cat_scene(t: float):
    """The same right-facing model at every time, with four independent limbs."""
    phase = (t/(FRAMES/FPS)) % 1.
    wave = TAU*phase
    bob = -2.8*math.cos(2*wave)
    tail = path('Curled tail',
        'M 12 8 C -22 12 -48 -6 -57 -36 '
        'C -66 -66 -58 -95 -74 -112 '
        'C -84 -123 -102 -122 -109 -137 '
        'C -119 -160 -96 -179 -77 -173 '
        'C -37 -160 -28 -127 -30 -96 '
        'C -33 -57 -24 -25 12 -20 Z')
    tail_node = group('Tail sway', [tail], x=-116, y=-24+bob,
                      rotation=.045*math.sin(wave-.7))
    body = path('Body',
        'M -119 -50 C -94 -73 -51 -69 -19 -66 '
        'C 12 -64 37 -65 60 -78 C 81 -88 107 -73 110 -43 '
        'C 117 -4 98 34 76 52 C 48 78 -5 79 -49 71 '
        'C -91 65 -119 50 -126 23 C -134 -4 -131 -29 -119 -50 Z')
    belly = path('Soft belly shade',
        'M -105 41 C -52 66 28 65 83 37 '
        'C 62 67 5 74 -47 64 C -73 60 -94 51 -105 41 Z',
        fill=SHADE, stroke=None)
    # A single oval eye, small muzzle, two whiskers and upright rounded ears
    # follow the supplied nine-panel reference; the face never turns frontal.
    head_parts = [
        path('Far ear',
            'M 19 -107 C 30 -132 48 -151 58 -153 '
            'C 70 -154 79 -126 77 -102 Z'),
        path('Head',
            'M -42 26 C -61 5 -62 -27 -51 -53 '
            'C -46 -65 -41 -73 -39 -78 '
            'C -34 -101 -23 -139 -11 -148 '
            'C -3 -154 15 -132 31 -110 '
            'C 64 -110 90 -91 96 -64 '
            'C 100 -50 98 -37 98 -29 '
            'C 113 -25 114 -13 108 1 '
            'C 99 25 73 39 42 40 '
            'C 26 41 18 43 17 61 '
            'C -6 64 -27 49 -42 26 Z'),
        path('Near ear ink',
            'M -17 -125 C -18 -129 -15 -130 -12 -125 '
            'L 2 -106 C -4 -104 -9 -102 -15 -100 Z', fill=INK, stroke=None),
        path('Chin shade',
            'M -20 37 C -7 43 8 45 27 42 '
            'C 20 46 18 53 17 61 C 1 59 -13 50 -20 37 Z',
            fill=SHADE, stroke=None),
        ellipse('Profile eye', 65, -35, 8.5, 12.),
        ellipse('Nose', 102, -25, 7., 5.5),
        path('Smile', 'M 101 -19 C 113 -7 98 6 86 -1', fill=None, width=6.),
        path('Whisker top', 'M 18 -18 L 38 -18', fill=None, width=5.8),
        path('Whisker bottom', 'M 24 3 L 41 -5', fill=None, width=5.8),
    ]
    head = group('Head follow-through', head_parts, x=102, y=-62+bob*.7,
                 rotation=.012*math.sin(2*wave-.6))
    torso = group('Body bounce', [body, belly], y=bob)
    # Near limbs paint over the belly; far limbs remain behind the torso.
    parts = [tail_node,
             leg('Far hind leg', phase+LEG_PHASES['Far hind leg'], True, True, bob),
             leg('Far fore leg', phase+LEG_PHASES['Far fore leg'], False, True, bob),
             torso,
             leg('Near hind leg', phase+LEG_PHASES['Near hind leg'], True, False, bob),
             leg('Near fore leg', phase+LEG_PHASES['Near fore leg'], False, False, bob),
             head]
    art = element('Artboard', name='Cat Walk', id='0:2', width=WIDTH, height=HEIGHT,
                  defaultStateMachineId='0:7', styleId='0:5')
    art.append(element('LayoutComponentStyle', id='0:5'))
    art.append(group('Cat', parts, x=410, y=334))
    art.append(ellipse('Ground shadow', 410, 472, 150, 8, fill='#e8e8e8'))
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
                if p.attrib['isClosed']=='true': pairs.append((vs[-1], vs[0]))
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


def contact_sheet():
    """Nine review poses in row-major order, including the duplicated end pose."""
    sheet = element(f'{{{SVG}}}svg', width=1200, height=840, viewBox='0 0 2400 1680')
    for i, frame in enumerate(KEY_POSES):
        cell = element('g', transform=f'translate({(i%3)*WIDTH} {(i//3)*HEIGHT})')
        cell.append(element('rect', x=8, y=8, width=WIDTH-16, height=HEIGHT-16, fill='#f4f4f4'))
        pose = ET.fromstring(svg_at(frame/FPS))
        cell.extend(pose)
        sheet.append(cell)
    return ET.tostring(sheet, encoding='unicode')+'\n'


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
    (ROOT/'build/contact-sheet.svg').write_text(contact_sheet(), encoding='utf-8')
    print(f'Wrote {dest}: {len(scene):,} characters; {FRAMES/FPS:.1f}s seamless walk.')


if __name__ == '__main__':
    main()
