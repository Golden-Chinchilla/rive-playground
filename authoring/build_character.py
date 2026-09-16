"""Convert the supplied SVG's absolute M/L/H/V/C/Z paths into editable Rive curves."""
import re, math, pathlib, xml.etree.ElementTree as E
from poster import build_poster, WIDTH, HEIGHT, CHARACTER_X, CHARACTER_Y, CHARACTER_SCALE
ROOT=pathlib.Path(__file__).resolve().parent.parent
svg=E.parse(ROOT/'source/character.svg').getroot()
props={}; neck=[]
def prop(n,v=0):
 if n not in props: props[n]=(f'0:{1000+len(props)}',v)
 return props[n][0]
def bind(n,key,v=0):return f'<DataBindContext sourcePathIds="0:40-{prop(n,v)}" propertyKey="{key}"/>'
def attrs(d):return ' '.join(f'{k}="{v}"' for k,v in d.items())
def path(d):
 t=re.findall(r'[MLHVCZmlhvcz]|[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?',d); vs=[]; i=0; close=False
 while i<len(t):
  cmd=t[i]; i+=1
  if cmd=='Z':close=True; continue
  n={'M':2,'L':2,'H':1,'V':1,'C':6}[cmd]
  a=list(map(float,t[i:i+n]));i+=n
  if cmd=='H': a=[a[0],vs[-1]['p'][1]]
  if cmd=='V': a=[vs[-1]['p'][0],a[0]]
  if cmd=='C':vs[-1]['out']=a[:2]; vs.append({'p':a[4:6],'in':a[2:4]})
  else:vs.append({'p':a})
 return vs,close
def shape(el,style,gid,index):
 st={**style,**el.attrib};name=st.get('id',f'{gid}-{index}');out=[f'<Shape name="{name}">']
 if el.tag.endswith('ellipse'):
  out += [f'<Ellipse x="{st["cx"]}" y="{st["cy"]}" width="{float(st["rx"])*2}" height="{float(st["ry"])*2}"/>']
 else:
  vs,closed=path(st['d']);out += [f'<PointsPath name="{name}-path" isClosed="{str(closed).lower()}">']
  for j,v in enumerate(vs):
   x,y=v['p'];at={'x':x,'y':y};typ='CubicDetachedVertex' if 'in'in v or 'out'in v else 'StraightVertex'
   for side in ['in','out']:
    if typ=='CubicDetachedVertex':
     q=v.get(side,v['p']); dx,dy=q[0]-x,q[1]-y
     at[side+'Rotation']=math.atan2(dy,dx);at[side+'Distance']=math.hypot(dx,dy)
   b=''
   if gid=='neck':
    pn=f'neck{len(neck)}';neck.append((pn,x,y));b=bind(pn+'X',24,x)+bind(pn+'Y',25,y)
   out += [f'<{typ} {attrs(at)}>{b}</{typ}>']
  out+=['</PointsPath>']
 if st.get('fill','none')!='none':out += [f'<Fill><SolidColor colorValue="FF{st["fill"].lstrip("#")}"/></Fill>']
 if st.get('stroke','none')!='none':out += [f'<Stroke thickness="{st.get("stroke-width",1)}" cap="{st.get("stroke-linecap","butt")}" join="round"><SolidColor colorValue="FF{st["stroke"].lstrip("#")}"/></Stroke>']
 return '\n'.join(out+['</Shape>'])
groups={}
for g in svg:
 if not g.tag.endswith('g'):continue
 gid=g.attrib['id'];groups[gid]='\n'.join(shape(el,{**svg.attrib,**g.attrib},gid,i) for i,el in reversed(list(enumerate(g))))
head=[]
for gid in reversed(list(groups)):
 if gid in ['background','neck']:continue
 b=''
 if gid in ['eyes','nose','mouth','glasses','glasses-shadows','lenses']:
  prefix='eyes' if gid=='eyes' else 'nose' if gid=='nose' else 'mouth' if gid=='mouth' else 'features'
  b=bind(prefix+'X',13)+bind(prefix+'Y',14)
 head += [f'<Node name="{gid}">{b}{groups[gid]}</Node>']
headbind=bind('headX',13,340)+bind('headY',14,450)+bind('headRotation',15)+bind('headScaleX',16,1)
foreground, background = build_poster(bind)
prop('mode', 0)
prop('motion', 1)
rml=['<Rive version="1" kind="fragment">',f'<Artboard name="Character Follow" id="0:2" width="{WIDTH}" height="{HEIGHT}" defaultStateMachineId="0:7" viewModelId="0:40" viewModelInstanceId="0:41" styleId="0:90"><LayoutComponentStyle id="0:90"/>', '<ScriptedDrawable name="Pointer follow controller" scriptAssetId="0:80"/>',foreground,f'<Node name="Character placement" x="{CHARACTER_X}" y="{CHARACTER_Y}" scaleX="{CHARACTER_SCALE}" scaleY="{CHARACTER_SCALE}">',f'<Node name="Head rig" x="340" y="450">{headbind}<Node x="-340" y="-450">'+''.join(head)+'</Node></Node>',f'<Node name="Anchored neck">{groups["neck"]}</Node>','</Node>',background, '<StateMachine name="Follow" id="0:7"><StateMachineLayer name="Tracking"><EntryState><StateTransition stateToId="0:12"/></EntryState><AnimationState x="220" y="0" id="0:12" animationId="0:20"/><AnyState x="220" y="-150"/><ExitState x="440" y="-150"/></StateMachineLayer></StateMachine><LinearAnimation name="Rest" id="0:20" duration="60"/>','</Artboard>','<ViewModel name="CharacterFollow" id="0:40" defaultInstanceId="0:41">']
for n,(pid,v) in props.items():rml += [f'<ViewModelPropertyNumber name="{n}" id="{pid}"/>']
rml+=['<ViewModelInstance name="Default" id="0:41" exports="true">']
for n,(pid,v) in props.items():rml += [f'<ViewModelInstanceNumber viewModelPropertyId="{pid}" propertyValue="{v}"/>']
rml+=['</ViewModelInstance></ViewModel>','<ScriptAsset name="follow" file="follow.luau" id="0:80"/>','</Rive>']
(ROOT/'scene.rml').write_text('\n'.join(rml))
(ROOT/'authoring/neck_data.txt').write_text('\n'.join(f'    {{ name = "{n}", x = {x}, y = {y} }},' for n,x,y in neck))
