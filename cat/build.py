#!/usr/bin/env python3
"""Bake a seam-free, four-beat cat walk to native Rive path keyframes.

Only the Python standard library is required. Numeric property keys retain the
CLI-verified schema (archived by CI). SVGs are design proofs, not runtime renders.
"""
from __future__ import annotations
import argparse
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WIDTH, HEIGHT = 800, 560
FPS, FRAMES, SAMPLE_STEP = 60, 72, 1
STRIDE, STANCE, SWING_LIFT = 88., .62, 28.
FLOOR = 128.
INK, PAPER, SHADE = '#111111', '#ffffff', '#dedede'
TAU = math.tau
SVG = 'http://www.w3.org/2000/svg'
ET.register_namespace('', SVG)
TRANSFORM_KEYS = {'x': 13, 'y': 14, 'rotation': 15, 'scaleX': 16, 'scaleY': 17, 'opacity': 18}
VERTEX_KEYS = {'x': 24, 'y': 25, 'inRotation': 84, 'inDistance': 85, 'outRotation': 86, 'outDistance': 87}
LEG_PHASES = {'Near hind leg': 0., 'Near fore leg': .75,
              'Far hind leg': .50, 'Far fore leg': .25}
HIND_HIP, FORE_HIP = -78., 72.
KEY_POSES = tuple(range(0, FRAMES+1, FRAMES//8))


def fmt(n):
    return f'{n:.5f}'.rstrip('0').rstrip('.') or '0'


def element(tag, **attrs):
    return ET.Element(tag, {k: fmt(v) if isinstance(v, (int, float)) else str(v) for k, v in attrs.items()})


def group(name, children, x=0., y=0., rotation=0., scaleX=1., scaleY=1.):
    node = element('Node', name=name, x=x, y=y, rotation=rotation, scaleX=scaleX, scaleY=scaleY)
    node.extend(reversed(children))  # RML siblings draw front-to-back.
    return node


def vertices(d):
    tokens = re.findall(r'[MLCZ]|[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?', d)
    result, i, closed = [], 0, False
    while i < len(tokens):
        cmd = tokens[i]; i += 1
        if cmd == 'Z':
            closed = True
            continue
        count = {'M': 2, 'L': 2, 'C': 6}[cmd]
        values = list(map(float, tokens[i:i+count])); i += count
        if cmd == 'C':
            result[-1]['out'] = values[:2]
            result.append({'point': values[4:], 'in': values[2:4]})
        else:
            result.append({'point': values})
    if closed and len(result) > 1 and result[-1]['point'] == result[0]['point']:
        if 'in' in result[-1]: result[0]['in'] = result[-1]['in']
        result.pop()
    return result, closed


def paint(shape, fill, stroke, width):
    for tag, color in (('Fill', fill), ('Stroke', stroke)):
        if color is None: continue
        p = element(tag, **({'thickness': width, 'cap': 'round', 'join': 'round'} if tag == 'Stroke' else {}))
        p.append(element('SolidColor', colorValue='FF'+color.lstrip('#')))
        shape.append(p)


def path(name, d, fill=PAPER, stroke=INK, width=7.5):
    shape = element('Shape', name=name)
    vs, closed = vertices(d)
    curve = element('PointsPath', name=name+' contour', isClosed=str(closed).lower())
    for i, v in enumerate(vs):
        x, y = v['point']
        a = {'name': f'{name} point {i}', 'x': x, 'y': y}
        cubic = 'in' in v or 'out' in v
        if cubic:
            for side in ('in', 'out'):
                u, w = v.get(side, (x, y))
                a[side+'Rotation'] = math.atan2(w-y, u-x)
                a[side+'Distance'] = math.hypot(u-x, w-y)
        curve.append(element('CubicDetachedVertex' if cubic else 'StraightVertex', **a))
    shape.append(curve)
    paint(shape, fill, stroke, width)
    return shape


def ellipse(name, x, y, rx, ry, fill=INK):
    shape = element('Shape', name=name)
    shape.append(element('Ellipse', x=x, y=y, width=2*rx, height=2*ry))
    paint(shape, fill, None, 0)
    return shape


class Curve:
    """Cubic segments with explicit reversible topology; no boolean-path jitter."""
    def __init__(self, start):
        self.start = tuple(start)
        self.segments = []

    @property
    def end(self):
        return self.segments[-1][2] if self.segments else self.start

    def c(self, a, b, end):
        self.segments.append((tuple(a), tuple(b), tuple(end)))
        return self

    def extend(self, other):
        if math.dist(self.end, other.start) > .0001:
            raise ValueError('Contour endpoints do not meet')
        self.segments.extend(other.segments)
        return self

    def reverse(self):
        starts = [self.start]+[s[2] for s in self.segments[:-1]]
        out = Curve(self.end)
        for start, (a, b, _) in reversed(list(zip(starts, self.segments))):
            out.c(b, a, start)
        return out

    def transformed(self, transform):
        out = Curve(transform(*self.start))
        for a, b, end in self.segments:
            out.c(transform(*a), transform(*b), transform(*end))
        return out

    def d(self, closed=False):
        xy = lambda p: ' '.join(fmt(v) for v in p)
        return 'M '+xy(self.start)+' '+ ' '.join('C '+' '.join(xy(p) for p in s) for s in self.segments)+(' Z' if closed else '')


def foot(phase):
    p = phase % 1.
    if p < STANCE:
        return STRIDE*(.5-p/STANCE), FLOOR
    q = (p-STANCE)/(1-STANCE)
    m = -(1-STANCE)/STANCE
    u = -2*q**3+3*q*q + m*(2*q**3-3*q*q+q)
    return STRIDE*(u-.5), FLOOR-SWING_LIFT*math.sin(math.pi*q)**2


def load_y(phase, rear=False):
    # Compression after support exchange; fore/hind offset adds gentle pitch.
    return 3.8*math.cos(2*TAU*phase-(.45 if rear else -.45))


def limb(phase, rear, far, body_phase):
    """Left root -> heel -> rounded pad -> toe -> right root, all cubic.

    The near legs are spliced into the torso's ONE silhouette, not painted on
    top of a closed outlined body. This removes the root caps and double lines.
    """
    hx = (HIND_HIP if rear else FORE_HIP) + ((8 if rear else -4) if far else 0)
    by = load_y(body_phase, rear)
    dx, fy = foot(phase)
    fx = hx+dx
    # One long upper/lower sweep per side avoids little elbow bulges. Root
    # tangents are shared with the belly, so there is no cusp at attachment.
    left = (hx-(30 if rear else 10), (22 if rear else 53)+by)
    right = (hx+(12 if rear else 25), (53 if rear else 20)+by)
    if far:
        left = (left[0], left[1]-28)
        right = (right[0], right[1]-28)
    out = Curve(left)
    control = (left[0]+10, left[1]+23) if rear else (left[0]+18, left[1])
    out.c(control, (fx-24, fy-39), (fx-18, fy-15))
    out.c((fx-20, fy-5), (fx-12, fy), (fx-2, fy))
    out.c((fx+10, fy), (fx+20, fy-3), (fx+20, fy-11))
    out.c((fx+20, fy-18), (fx+13, fy-19), (fx+11, fy-23))
    control = (right[0]-18,right[1]) if rear else (right[0]-2,right[1]+28)
    out.c((fx+5, fy-42), control, right)
    return out


def head_transform(phase):
    angle = .016*math.sin(2*TAU*phase-.7)
    y = -56+load_y(phase)*.72
    def transform(x, yy):
        return 104+x*math.cos(angle)-yy*math.sin(angle), y+x*math.sin(angle)+yy*math.cos(angle)
    return transform, angle, y


def head_curve():
    # From back/shoulder junction clockwise over the ears, face and chin.
    p = Curve((-55., -18.))
    p.c((-66,-43),(-51,-67),(-42,-81))
    p.c((-35,-105),(-23,-140),(-12,-147))
    p.c((-3,-154),(14,-129),(27,-111))
    p.c((38,-129),(52,-145),(59,-145))
    p.c((70,-145),(79,-116),(76,-100))
    p.c((91,-89),(98,-65),(97,-43))
    p.c((99,-34),(111,-33),(111,-22))
    p.c((110,8),(80,32),(42,36))
    return p


def silhouette(phase):
    transform, _, _ = head_transform(phase)
    out = head_curve().transformed(transform)
    front = limb(phase+LEG_PHASES['Near fore leg'], False, False, phase).reverse()
    rear = limb(phase+LEG_PHASES['Near hind leg'], True, False, phase).reverse()
    tangent = front.segments[0][0]
    out.c(transform(26,38), tuple(front.start[k]-.8*(tangent[k]-front.start[k]) for k in (0,1)), front.start)
    out.extend(front)
    mid = (-2.,64+(load_y(phase)+load_y(phase,True))/2)
    out.c((front.end[0]-24,front.end[1]),(mid[0]+26,mid[1]),mid)
    out.c((mid[0]-26,mid[1]),(rear.start[0]+24,rear.start[1]),rear.start)
    out.extend(rear)
    by = load_y(phase,True)
    # Tail forms the same outer silhouette: no cap or joint across the rump.
    sway = .043*math.sin(TAU*phase-.6)
    def tail_t(x,y):
        return -119+x*math.cos(sway)-y*math.sin(sway), -35+by+x*math.sin(sway)+y*math.cos(sway)
    tail = Curve((-6,7))
    tail.c((-27,-10),(-48,-14),(-60,-50))
    tail.c((-67,-85),(-57,-105),(-77,-119))
    tail.c((-95,-125),(-116,-132),(-111,-151))
    tail.c((-107,-175),(-84,-179),(-65,-166))
    tail.c((-34,-146),(-32,-119),(-33,-93))
    tail.c((-36,-56),(-31,-40),(7,-35))
    moved = tail.transformed(tail_t)
    out.c((-118,by), (moved.start[0]+21,moved.start[1]+17), moved.start)
    out.extend(moved)
    out.c((moved.end[0]+30,moved.end[1]+2),(out.start[0]-30,out.start[1]+2),out.start)
    return out


def cat_scene(t):
    phase = (t/(FRAMES/FPS)) % 1.
    _, angle, head_y = head_transform(phase)
    body = path('Continuous cat silhouette', silhouette(phase).d(True))
    far_hind = path('Far hind leg', limb(phase+LEG_PHASES['Far hind leg'], True, True, phase).d(True), fill='#ededed')
    far_fore = path('Far fore leg', limb(phase+LEG_PHASES['Far fore leg'], False, True, phase).d(True), fill='#ededed')
    shade = Curve((-43.,52.))
    shade.c((-19,60),(21,60),(44,52)).c((22,65),(-22,65),(-43,52))
    shade = shade.transformed(lambda x,y: (x, y+load_y(phase,True)*(72-x)/150+load_y(phase)*(x+78)/150))
    belly = path('Belly shade',shade.d(True),fill=SHADE,stroke=None)
    details = group('Head follow-through', [
        path('Near ear ink', 'M -18 -122 C -18 -127 -14 -125 -11 -121 L 1 -104 L -16 -98 Z', fill=INK, stroke=None),
        path('Far ear fold', 'M 27 -111 C 44 -110 63 -107 76 -100', fill=None, width=6.5),
        path('Cheek crease', 'M -55 -18 C -51 -6 -46 3 -40 8', fill=None, width=7.5),
        ellipse('Profile eye', 65, -43, 8.5, 11.5),
        ellipse('Nose', 106, -29, 6.5, 5.),
        path('Smile', 'M 105 -24 C 113 -13 100 0 88 -7', fill=None, width=6.),
        path('Whisker top', 'M 18 -21 C 25 -21 32 -21 38 -21', fill=None, width=5.8),
        path('Whisker bottom', 'M 24 0 C 29 -3 35 -6 41 -8', fill=None, width=5.8),
    ], x=104, y=head_y, rotation=angle)
    art = element('Artboard', name='Cat Walk', id='0:2', width=WIDTH, height=HEIGHT, defaultStateMachineId='0:7', styleId='0:5')
    art.append(element('LayoutComponentStyle', id='0:5'))
    art.append(group('Cat', [far_hind, far_fore, body, belly, details], x=410, y=334))
    # Deliberate neutral backdrop for the CLI viewer too. No opaque pale oval
    # "shadow" that turns into a glowing platform against a dark viewer canvas.
    art.append(path('Preview background', f'M 0 0 L {WIDTH} 0 L {WIDTH} {HEIGHT} L 0 {HEIGHT} Z', fill='#f7f7f5', stroke=None))
    return art


def assign_ids(art):
    for i, node in enumerate(art.iter()):
        if 'id' not in node.attrib: node.set('id', f'0:{100+i}')


def build_rml():
    art = cat_scene(0.)
    assign_ids(art)
    frames = list(range(0, FRAMES+1, SAMPLE_STEP))
    poses = [list(cat_scene(f/FPS).iter()) for f in frames]
    original = list(art.iter())
    animation = element('LinearAnimation', name='Walk', id='0:6', duration=FRAMES, fps=FPS, loopValue='loop')
    for index, node in enumerate(original):
        keys = VERTEX_KEYS if node.tag.endswith('Vertex') else TRANSFORM_KEYS if node.tag in ('Node','Shape') else {}
        keyed = element('KeyedObject', objectId=node.attrib['id'])
        for attr, key in keys.items():
            if attr not in node.attrib: continue
            values = [float(p[index].attrib[attr]) for p in poses]
            if max(values)-min(values) < .0001: continue
            if attr.endswith('Rotation') or attr == 'rotation':
                for i in range(1,len(values)): values[i] += TAU*round((values[i-1]-values[i])/TAU)
            prop = element('KeyedProperty', propertyKey=key)
            for f,v in zip(frames,values):
                prop.append(element('KeyFrameDouble', frame=f, value=v, interpolationType='linear'))
            keyed.append(prop)
        if len(keyed): animation.append(keyed)
    art.append(animation)
    sm = element('StateMachine', name='Cat', id='0:7')
    layer = element('StateMachineLayer', name='Locomotion', id='0:8')
    entry = element('EntryState'); entry.append(element('StateTransition', stateToId='0:12'))
    layer.extend([entry, element('AnimationState', animationId='0:6', id='0:12', x=200), element('AnyState', x=200,y=-120), element('ExitState', x=400,y=-120)])
    sm.append(layer); art.append(sm)
    root = element('Rive', version='1',kind='fragment'); root.append(art)
    ET.indent(root,space='  ')
    return ET.tostring(root,encoding='unicode')+'\n'


def svg_at(t=0.):
    art = cat_scene(t)
    out = element('svg',xmlns=SVG,width=WIDTH,height=HEIGHT,viewBox=f'0 0 {WIDTH} {HEIGHT}')
    def draw(node,parent):
        a=node.attrib
        if node.tag not in ('Node','Shape'): return
        g=element('g',transform=f'translate({a.get("x",0)} {a.get("y",0)}) rotate({float(a.get("rotation",0))*180/math.pi}) scale({a.get("scaleX",1)} {a.get("scaleY",1)})')
        parent.append(g)
        if node.tag == 'Node':
            for child in reversed(list(node)): draw(child,g)
            return
        style={'fill':'none','stroke':'none'}
        for tag,key in (('Fill','fill'),('Stroke','stroke')):
            p=node.find(tag)
            if p is not None:
                style[key]='#'+p.find('SolidColor').attrib['colorValue'][-6:]
                if tag=='Stroke': style.update({'stroke-width':p.attrib['thickness'],'stroke-linejoin':'round','stroke-linecap':'round'})
        for p in node:
            if p.tag=='Ellipse':
                a=p.attrib; g.append(element('ellipse',cx=a['x'],cy=a['y'],rx=float(a['width'])/2,ry=float(a['height'])/2,**style))
            elif p.tag=='PointsPath':
                vs=list(p); d=[f'M {vs[0].attrib["x"]} {vs[0].attrib["y"]}']
                pairs=list(zip(vs,vs[1:]))
                if p.attrib['isClosed']=='true': pairs.append((vs[-1],vs[0]))
                for v,w in pairs:
                    def control(v,side):
                        a=v.attrib;r=float(a.get(side+'Rotation',0));z=float(a.get(side+'Distance',0))
                        return float(a['x'])+z*math.cos(r),float(a['y'])+z*math.sin(r)
                    if float(v.attrib.get('outDistance',0)) or float(w.attrib.get('inDistance',0)):
                        x,y=control(v,'out');u,z=control(w,'in');d.append(f'C {x} {y} {u} {z} {w.attrib["x"]} {w.attrib["y"]}')
                    else: d.append(f'L {w.attrib["x"]} {w.attrib["y"]}')
                if p.attrib['isClosed']=='true': d.append('Z')
                g.append(element('path',d=' '.join(d),**style))
    for child in reversed(list(art)): draw(child,out)
    return ET.tostring(out,encoding='unicode')


def contact_sheet():
    sheet=element(f'{{{SVG}}}svg',width=1200,height=840,viewBox='0 0 2400 1680')
    for i,f in enumerate(KEY_POSES):
        cell=element('g',transform=f'translate({i%3*WIDTH} {i//3*HEIGHT})')
        cell.extend(ET.fromstring(svg_at(f/FPS)))
        sheet.append(cell)
    return ET.tostring(sheet,encoding='unicode')+'\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    text=build_rml(); dest=ROOT/'scene.rml'
    if args.check:
        if not dest.exists() or dest.read_text()!=text: raise SystemExit('cat/scene.rml is stale; run python3 cat/build.py')
        print('Cat source and scene are synchronized.');return
    dest.write_text(text,encoding='utf-8')
    (ROOT/'build').mkdir(exist_ok=True)
    (ROOT/'build/design-proof.svg').write_text(svg_at(),encoding='utf-8')
    (ROOT/'build/contact-sheet.svg').write_text(contact_sheet(),encoding='utf-8')
    print(f'Wrote {dest}: {len(text):,} characters; {FRAMES/FPS:.1f}s walk.')


if __name__=='__main__': main()
