"""Structural, contact and contour regressions; Python standard library only."""
import importlib.util
import math
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('cat_build', ROOT/'build.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


def sample(curve, steps=8):
    result, start = [], curve.start
    for a, b, end in curve.segments:
        for i in range(steps):
            t = i/steps; u = 1-t
            result.append(tuple(u**3*start[k]+3*u*u*t*a[k]+3*u*t*t*b[k]+t**3*end[k] for k in (0,1)))
        start = end
    return result


def inside(p, polygon):
    x, y = p; hit = False
    for a, b in zip(polygon, polygon[1:]+polygon[:1]):
        if (a[1]>y) != (b[1]>y) and x < (b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:
            hit = not hit
    return hit


def crossings(points):
    edges = list(zip(points, points[1:]+points[:1]))
    cross = lambda a,b,c: (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    for i,(a,b) in enumerate(edges):
        for j in range(i+2,len(edges)):
            if i == 0 and j == len(edges)-1: continue
            c,d = edges[j]
            if max(a[0],b[0])<min(c[0],d[0]) or max(c[0],d[0])<min(a[0],b[0]): continue
            if max(a[1],b[1])<min(c[1],d[1]) or max(c[1],d[1])<min(a[1],b[1]): continue
            if cross(a,b,c)*cross(a,b,d)<-1e-9 and cross(c,d,a)*cross(c,d,b)<-1e-9:
                return True
    return False


class WalkingCatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = build.build_rml()
        cls.scene = ET.fromstring(cls.text)

    def test_artboard_and_default_state_machine(self):
        art = self.scene.find('Artboard')
        self.assertEqual(art.get('name'),'Cat Walk')
        self.assertEqual(art.get('defaultStateMachineId'),'0:7')
        self.assertEqual(art.find('StateMachine').get('name'),'Cat')

    def test_native_loop_configuration(self):
        animation = self.scene.find('.//LinearAnimation')
        self.assertEqual(animation.get('name'),'Walk')
        self.assertEqual(animation.get('loopValue'),'loop')
        self.assertEqual(int(animation.get('duration')),72)
        self.assertEqual(int(animation.get('fps')),60)

    def test_vector_only(self):
        tags = {n.tag for n in self.scene.iter()}
        self.assertFalse({'ImageAsset','ScriptAsset','FontAsset'} & tags)
        self.assertIn('CubicDetachedVertex',tags)

    def test_one_near_silhouette_replaces_overlapping_body_and_leg_caps(self):
        shapes = {n.get('name'):n for n in self.scene.iter('Shape')}
        self.assertIn('Continuous cat silhouette',shapes)
        for obsolete in ('Body','Near hind leg outline','Near fore leg outline','Head'):
            self.assertNotIn(obsolete,shapes)
        main = shapes['Continuous cat silhouette']
        self.assertEqual(len(main.findall('PointsPath')),1)
        self.assertEqual(main.find('PointsPath').get('isClosed'),'true')
        self.assertEqual(len(main.findall('Stroke')),1)
        self.assertIn('Far hind leg',shapes); self.assertIn('Far fore leg',shapes)

    def test_four_anatomical_phases_and_contours_remain_independent(self):
        self.assertEqual(len(build.LEG_PHASES),4)
        curves = []
        for name, phase in build.LEG_PHASES.items():
            curves.append(build.limb(phase,'hind' in name,'Far' in name,0).d())
        self.assertEqual(len(set(curves)),4)
        touchdown = sorted(((-p)%1,n) for n,p in build.LEG_PHASES.items())
        self.assertEqual([n for _,n in touchdown],['Near hind leg','Near fore leg','Far hind leg','Far fore leg'])
        for i in range(240):
            self.assertGreaterEqual(sum((i/240+p)%1<build.STANCE for p in build.LEG_PHASES.values()),2)

    def test_paws_are_cubic_not_boot_shaped_polygon_soles(self):
        for rear in (False,True):
            for i in range(72):
                d = build.limb(i/72,rear,False,i/72).d()
                self.assertNotIn('L',d)
                self.assertEqual(d.count('C'),5)

    def test_outer_silhouette_never_self_intersects_between_keys(self):
        # Half-frame poses catch folds/crossings hidden by nine-pose reviews.
        for i in range(144):
            self.assertFalse(crossings(sample(build.silhouette(i/144))),f'phase {i}/144')

    def test_far_leg_closing_caps_stay_buried_in_torso(self):
        for i in range(144):
            phase = i/144; polygon = sample(build.silhouette(phase),12)
            for rear,name in ((True,'Far hind leg'),(False,'Far fore leg')):
                curve = build.limb(phase+build.LEG_PHASES[name],rear,True,phase)
                for j in range(9):
                    p = tuple(curve.start[k]*(1-j/8)+curve.end[k]*j/8 for k in (0,1))
                    self.assertTrue(inside(p,polygon),(phase,name,p))

    def test_belly_to_near_leg_junctions_have_matching_tangents(self):
        for i in range(72):
            segments = build.silhouette(i/72).segments
            # head(8), chest(1), fore(5), belly(2), hind(5)
            for index in (8,13,15):
                _,before,p = segments[index]
                after,_,_ = segments[index+1]
                v = (p[0]-before[0],p[1]-before[1])
                w = (after[0]-p[0],after[1]-p[1])
                cosine = sum(a*b for a,b in zip(v,w))/(math.hypot(*v)*math.hypot(*w))
                self.assertGreater(cosine,.9999,(i,index))

    def test_head_geometry_is_rigid_even_in_the_shared_silhouette(self):
        base = build.head_curve()
        for i in range(73):
            transform,_,_ = build.head_transform(i/72)
            expected = base.transformed(transform)
            actual = build.silhouette(i/72)
            self.assertEqual(actual.start,expected.start)
            self.assertEqual(actual.segments[:8],expected.segments)

    def test_head_details_keep_identical_local_geometry(self):
        def geometry(t):
            node = next(n for n in build.cat_scene(t).iter('Node') if n.get('name')=='Head follow-through')
            return [ET.tostring(n) for n in node]
        for i in range(73): self.assertEqual(geometry(i/60),geometry(0))

    def test_fore_and_hind_load_offsets_add_pitch_not_only_global_bobbing(self):
        values = [build.load_y(i/72)-build.load_y(i/72,True) for i in range(72)]
        self.assertGreater(max(values)-min(values),5)
        self.assertLess(max(abs(v) for v in values),8)

    def test_no_bright_ground_pad_and_cli_background_is_explicit(self):
        shapes = {n.get('name'):n for n in self.scene.iter('Shape')}
        self.assertNotIn('Ground shadow',shapes)
        color = shapes['Preview background'].find('Fill/SolidColor').get('colorValue')
        self.assertEqual(color,'FFf7f7f5')

    def test_all_keyed_properties_close_the_loop(self):
        for prop in self.scene.iter('KeyedProperty'):
            keys = list(prop)
            self.assertEqual(int(keys[0].get('frame')),0)
            self.assertEqual(int(keys[-1].get('frame')),72)
            delta = float(keys[-1].get('value'))-float(keys[0].get('value'))
            if int(prop.get('propertyKey')) in (15,84,86): delta=math.remainder(delta,math.tau)
            self.assertAlmostEqual(delta,0,places=4)

    def test_native_keys_are_sampled_every_frame_without_a_duplicate_hold(self):
        for prop in self.scene.iter('KeyedProperty'):
            self.assertEqual([int(k.get('frame')) for k in prop],list(range(73)))
            self.assertTrue(all(k.get('interpolationType')=='linear' for k in prop))

    def test_planted_feet_match_forward_translation(self):
        period=build.FRAMES/build.FPS; velocity=build.STRIDE/(build.STANCE*period)
        for p in (.05,.2,.45,.6):
            x,y=build.foot(p);xx,yy=build.foot(p+.0001/period)
            self.assertAlmostEqual(xx+velocity*.0001,x)
            self.assertEqual(y,build.FLOOR);self.assertEqual(yy,build.FLOOR)

    def test_contact_position_and_velocity_are_continuous(self):
        eps=1e-6
        for p in (0.,build.STANCE,1.):
            left=build.foot(p-eps);middle=build.foot(p);right=build.foot(p+eps)
            for k in (0,1):
                self.assertAlmostEqual(left[k],right[k],places=2)
                self.assertAlmostEqual((middle[k]-left[k])/eps,(right[k]-middle[k])/eps,delta=.02)

    def test_swing_has_clear_lift(self):
        x,y=build.foot(build.STANCE+(1-build.STANCE)/2)
        self.assertAlmostEqual(x,0);self.assertEqual(y,build.FLOOR-build.SWING_LIFT)

    def test_ids_unique_and_key_targets_exist(self):
        ids=[n.get('id') for n in self.scene.iter() if n.get('id')]
        self.assertEqual(len(ids),len(set(ids)))
        for n in self.scene.iter('KeyedObject'): self.assertIn(n.get('objectId'),ids)

    def test_pose_topology_finite_and_periodic(self):
        original=[(n.tag,n.get('name')) for n in build.cat_scene(0).iter()]
        for f in range(73):
            nodes=list(build.cat_scene(f/60).iter())
            self.assertEqual([(n.tag,n.get('name')) for n in nodes],original)
            for n in nodes:
                for k in ('x','y','inDistance','outDistance','rotation'):
                    if k in n.attrib:self.assertTrue(math.isfinite(float(n.get(k))))
        self.assertEqual(ET.tostring(build.cat_scene(0)),ET.tostring(build.cat_scene(1.2)))
        self.assertNotEqual(ET.tostring(build.cat_scene(0)),ET.tostring(build.cat_scene(.3)))

    def test_nine_pose_sheet_includes_the_closing_pose(self):
        self.assertEqual(build.KEY_POSES,tuple(range(0,73,9)))
        sheet=ET.fromstring(build.contact_sheet());self.assertEqual(len(sheet),9)
        self.assertEqual([ET.tostring(n) for n in sheet[0]],[ET.tostring(n) for n in sheet[-1]])

    def test_web_speed_matches_the_authored_walk(self):
        text=(ROOT/'web/index.html').read_text()
        cycle=re.search(r'const cycle = ([0-9.]+);',text)
        speed=re.search(r'const unitsPerSecond = ([0-9.]+) / \(([0-9.]+) \* cycle\);',text)
        self.assertIsNotNone(cycle);self.assertIsNotNone(speed)
        self.assertAlmostEqual(float(cycle[1]),build.FRAMES/build.FPS)
        self.assertAlmostEqual(float(speed[1]),build.STRIDE)
        self.assertAlmostEqual(float(speed[2]),build.STANCE)

    def test_generated_scene_is_reproducible(self):
        self.assertEqual((ROOT/'scene.rml').read_text(),self.text)


if __name__=='__main__':unittest.main()
