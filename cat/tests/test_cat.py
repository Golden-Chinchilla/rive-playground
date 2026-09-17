"""Geometry and compiled-animation invariants; standard-library-only tests."""
import importlib.util
import math
import re
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('cat_build', ROOT/'build.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class WalkingCatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = build.build_rml()
        cls.scene = ET.fromstring(cls.text)

    def test_artboard_and_default_state_machine(self):
        art = self.scene.find('Artboard')
        self.assertEqual(art.get('name'), 'Cat Walk')
        self.assertEqual(art.get('defaultStateMachineId'), '0:7')
        self.assertEqual(art.find('StateMachine').get('name'), 'Cat')

    def test_vector_only(self):
        tags = {n.tag for n in self.scene.iter()}
        self.assertNotIn('ImageAsset', tags)
        self.assertNotIn('ScriptAsset', tags)
        self.assertNotIn('FontAsset', tags)
        self.assertIn('CubicDetachedVertex', tags)

    def test_four_independent_legs(self):
        names = {n.get('name') for n in self.scene.iter('Shape')}
        self.assertTrue({'Far hind leg', 'Far fore leg', 'Near hind leg', 'Near fore leg'} <= names)

    def test_native_loop_configuration(self):
        animation = self.scene.find('.//LinearAnimation')
        self.assertEqual(animation.get('name'), 'Walk')
        self.assertEqual(animation.get('loopValue'), 'loop')
        self.assertEqual(int(animation.get('duration')), 72)
        self.assertEqual(int(animation.get('fps')), 60)

    def test_all_keyed_properties_close_the_loop(self):
        for prop in self.scene.iter('KeyedProperty'):
            keys = list(prop)
            self.assertEqual(int(keys[0].get('frame')), 0)
            self.assertEqual(int(keys[-1].get('frame')), 72)
            delta = float(keys[-1].get('value')) - float(keys[0].get('value'))
            if int(prop.get('propertyKey')) in (15, 84, 86):
                delta = math.remainder(delta, math.tau)
            self.assertAlmostEqual(delta, 0, places=4)

    def test_planted_feet_do_not_slide_when_translated(self):
        period = build.FRAMES/build.FPS
        velocity = build.STRIDE/(build.STANCE*period)
        dt = .001
        for phase in (.05, .20, .45, .60):
            x, y = build.foot(phase)
            next_x, next_y = build.foot(phase+dt/period)
            self.assertAlmostEqual(next_x+velocity*dt, x)
            self.assertEqual(y, build.FLOOR)
            self.assertEqual(next_y, build.FLOOR)

    def test_swing_lifts_off_ground(self):
        x, y = build.foot(build.STANCE+(1-build.STANCE)/2)
        self.assertGreater(build.SWING_LIFT, 0)
        self.assertAlmostEqual(x, 0)
        self.assertAlmostEqual(y, build.FLOOR-build.SWING_LIFT)
        self.assertLess(y, build.FLOOR)

    def test_pose_is_periodic_and_changes(self):
        encode = lambda t: ET.tostring(build.cat_scene(t))
        self.assertEqual(encode(0), encode(1.2))
        self.assertNotEqual(encode(0), encode(.3))

    def test_all_key_targets_exist_and_ids_are_unique(self):
        ids = [n.get('id') for n in self.scene.iter() if n.get('id')]
        self.assertEqual(len(ids), len(set(ids)))
        for node in self.scene.iter('KeyedObject'):
            self.assertIn(node.get('objectId'), ids)

    def test_web_speed_matches_baked_stride(self):
        html = (ROOT/'web/index.html').read_text()
        cycle = re.search(r'const cycle = ([0-9.]+);', html)
        speed = re.search(r'const unitsPerSecond = ([0-9.]+) / \(([0-9.]+) \* cycle\);', html)
        self.assertIsNotNone(cycle)
        self.assertIsNotNone(speed)
        self.assertAlmostEqual(float(cycle[1]), build.FRAMES/build.FPS)
        self.assertAlmostEqual(float(speed[1]), build.STRIDE)
        self.assertAlmostEqual(float(speed[2]), build.STANCE)

    def test_short_stride_paws_stay_reachable(self):
        for rear in (False, True):
            hx = -56. if rear else 54.
            a, b = (58., 54.) if rear else (54., 50.)
            for i in range(361):
                phase = i/360
                bob = -2.8*math.cos(2*math.tau*phase)
                dx, fy = build.foot(phase)
                hy = 24.+bob
                ax, ay = hx+dx, fy-20.
                self.assertLess(math.hypot(ax-hx, ay-hy), a+b-.01)
                kx, ky = build.knee(hx, hy, ax, ay, rear)
                self.assertAlmostEqual(math.hypot(kx-hx, ky-hy), a)
                self.assertAlmostEqual(math.hypot(ax-kx, ay-ky), b)

    def test_pose_topology_and_coordinates_are_stable(self):
        original = [(n.tag, n.get('name')) for n in build.cat_scene(0).iter()]
        for frame in range(build.FRAMES+1):
            nodes = list(build.cat_scene(frame/build.FPS).iter())
            self.assertEqual([(n.tag, n.get('name')) for n in nodes], original)
            for node in nodes:
                for key in ('x', 'y', 'inDistance', 'outDistance', 'rotation'):
                    if key in node.attrib:
                        self.assertTrue(math.isfinite(float(node.attrib[key])))

    def test_generated_scene_is_reproducible(self):
        self.assertEqual((ROOT/'scene.rml').read_text(), self.text)


if __name__ == '__main__':
    unittest.main()
