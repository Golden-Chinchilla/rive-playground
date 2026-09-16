"""Render this project's vector-only RML subset as an SVG design preview.

This is NOT a replacement for a Rive runtime screenshot. It exists so the
layout can be reviewed on systems whose headless GPU produces blank frames.
Optional --pose accepts the actual values from `rive . --data-dump=...`.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import xml.etree.ElementTree as E

ROOT = Path(__file__).resolve().parent.parent
SVG = 'http://www.w3.org/2000/svg'
E.register_namespace('', SVG)


def preview(scene=ROOT/'scene.rml', pose=None):
    rml = E.parse(scene).getroot()
    names = {p.attrib['id']: p.attrib['name'] for p in rml.findall('.//ViewModelPropertyNumber')}
    values = {p.attrib['viewModelPropertyId']: float(p.attrib['propertyValue'])
              for p in rml.findall('.//ViewModelInstanceNumber')}
    if pose:
        data = json.loads(Path(pose).read_text())
        by_name = {p['name']: p['value'] for p in data['viewModel']['properties']}
        values.update({pid: by_name[name] for pid, name in names.items() if name in by_name})
    art = rml.find('Artboard')
    out = E.Element(f'{{{SVG}}}svg', {'width': art.attrib['width'], 'height': art.attrib['height'],
                                      'viewBox': f'0 0 {art.attrib["width"]} {art.attrib["height"]}'})
    E.SubElement(out, f'{{{SVG}}}title').text = 'Character Lab — vector layout preview'
    mapping = {13: 'x', 14: 'y', 15: 'rotation', 16: 'scaleX', 17: 'scaleY', 18: 'opacity',
               24: 'x', 25: 'y'}
    def attrs(el):
        a = dict(el.attrib)
        for b in el.findall('DataBindContext'):
            key = int(b.attrib['propertyKey'])
            pid = b.attrib['sourcePathIds'].split('-')[-1]
            if key in mapping:
                a[mapping[key]] = str(values[pid])
        return a
    def draw(el, parent):
        a = attrs(el)
        if el.tag in ('Node', 'Shape'):
            transform = (f'translate({a.get("x",0)} {a.get("y",0)}) '
                         f'rotate({math.degrees(float(a.get("rotation",0)))}) '
                         f'scale({a.get("scaleX",1)} {a.get("scaleY",1)})')
            node = E.SubElement(parent, f'{{{SVG}}}g', {'transform': transform, 'opacity': a.get('opacity','1')})
            if 'name' in a:
                E.SubElement(node, f'{{{SVG}}}title').text = a['name']
            if el.tag == 'Node':
                for c in reversed(list(el)): draw(c, node)
                return
            style = {'fill': 'none', 'stroke': 'none'}
            for tag, key in [('Fill','fill'), ('Stroke','stroke')]:
                paint = el.find(tag)
                if paint is not None:
                    color = paint.find('SolidColor').attrib['colorValue']
                    style[key] = '#'+color[-6:]
                    style[key+'-opacity'] = str(int(color[:2],16)/255)
                    if key == 'stroke':
                        style.update({'stroke-width': paint.attrib.get('thickness','1'),
                                      'stroke-linecap': paint.attrib.get('cap','butt'),
                                      'stroke-linejoin': paint.attrib.get('join','miter')})
            for path in el:
                if path.tag == 'Ellipse':
                    p = attrs(path)
                    E.SubElement(node, f'{{{SVG}}}ellipse', dict(style, cx=p.get('x','0'), cy=p.get('y','0'),
                        rx=str(float(p['width'])/2), ry=str(float(p['height'])/2)))
                elif path.tag == 'PointsPath':
                    vs = [attrs(v) for v in path if v.tag.endswith('Vertex')]
                    if not vs: continue
                    d = [f'M{vs[0]["x"]},{vs[0]["y"]}']
                    pairs = list(zip(vs, vs[1:]))
                    if path.attrib.get('isClosed') == 'true': pairs.append((vs[-1],vs[0]))
                    for p,q in pairs:
                        px,py,qx,qy = map(float,(p['x'],p['y'],q['x'],q['y']))
                        po,qi = float(p.get('outDistance',0)),float(q.get('inDistance',0))
                        if po or qi:
                            pr,qr = float(p.get('outRotation',0)),float(q.get('inRotation',0))
                            d.append(f'C{px+po*math.cos(pr)},{py+po*math.sin(pr)} '
                                     f'{qx+qi*math.cos(qr)},{qy+qi*math.sin(qr)} {qx},{qy}')
                        else: d.append(f'L{qx},{qy}')
                    if path.attrib.get('isClosed') == 'true': d.append('Z')
                    E.SubElement(node, f'{{{SVG}}}path', dict(style,d=' '.join(d)))
    for child in reversed(list(art)): draw(child,out)
    return E.tostring(out, encoding='unicode')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pose', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT/'build/poster-preview.svg')
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(preview(pose=args.pose), encoding='utf-8')
    print(args.output)
