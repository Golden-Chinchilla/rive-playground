"""Structural tests plus real Rive pointer/data-binding regression tests.

Rive tests are skipped when the CLI is absent. Set RIVE_BIN to a specific
executable; no mocking of the runtime or pointer dispatch is involved.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
RIVE = os.environ.get('RIVE_BIN') or shutil.which('rive')


def generate():
    subprocess.run([sys.executable, str(ROOT/'authoring/build_character.py')],
                   cwd=ROOT, check=True, capture_output=True, text=True, timeout=20)


class PosterStructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        generate()
        cls.root = ET.parse(ROOT/'scene.rml').getroot()

    def test_reproducible_build(self):
        before = (ROOT/'scene.rml').read_bytes()
        generate()
        self.assertEqual(before, (ROOT/'scene.rml').read_bytes())

    def test_canvas_and_layer_order(self):
        art = self.root.find('Artboard')
        self.assertEqual((art.get('width'), art.get('height')), ('1280','860'))
        names = [n.get('name') for n in art.findall('Node')]
        self.assertEqual(names, ['Poster foreground','Character placement','Poster background'])

    def test_original_art_is_preserved(self):
        character = self.root.find('.//Node[@name="Character placement"]')
        self.assertEqual(len(character.findall('.//Shape')), 25)  # original 26 minus white background
        self.assertIsNotNone(character.find('.//Shape[@name="hair-silhouette"]'))
        self.assertIsNotNone(character.find('.//Node[@name="Anchored neck"]'))

    def test_binding_targets_exist_and_ids_are_unique(self):
        elements = [e for e in self.root.iter() if 'id' in e.attrib]
        self.assertEqual(len(elements), len({e.get('id') for e in elements}))
        props = {p.get('id') for p in self.root.findall('.//ViewModelPropertyNumber')}
        for b in self.root.findall('.//DataBindContext'):
            self.assertIn(b.get('sourcePathIds').split('-')[-1], props)
        instances = self.root.findall('.//ViewModelInstanceNumber')
        self.assertEqual(props, {i.get('viewModelPropertyId') for i in instances})

    def test_ui_landmarks_and_labels(self):
        names = {n.get('name') for n in self.root.iter()}
        for name in ['Greeting bubble','Field notes card','Personality card','Gaze tracker card',
                     'Mode controls','FOLLOW button','IDLE button','WANDER button','Reset button']:
            self.assertIn(name,names)
        self.assertNotIn('FontAsset', {n.tag for n in self.root.iter()})
        self.assertNotIn('ImageAsset', {n.tag for n in self.root.iter()})


@unittest.skipUnless(RIVE, 'Rive CLI unavailable; structural tests still run')
class NativeInteractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        generate()

    def run_scene(self, *gestures):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)/'state.json'
            p = subprocess.run([RIVE, str(ROOT), f'--data-dump={output}', *gestures],
                               cwd=ROOT, capture_output=True, text=True, timeout=45)
            self.assertEqual(p.returncode, 0, p.stdout+'\n'+p.stderr)
            data = json.loads(output.read_text())
            return {v['name']: v['value'] for v in data['viewModel']['properties']}

    def test_follow_moves_gaze_and_keeps_neck_base_fixed(self):
        values = self.run_scene('--pointer=move@1180,270','--advance=60')
        self.assertGreater(values['headX'], 345)
        self.assertGreater(values['gazeX'], 110)
        self.assertLess(values['gazeY'], 117)
        self.assertAlmostEqual(values['neck1X'],429.23,places=3)
        self.assertAlmostEqual(values['neck1Y'],667.06,places=3)
        self.assertAlmostEqual(values['neck10Y'],667,places=3)

    def test_idle_button_overrides_pointer(self):
        values = self.run_scene('--pointer=click@326,783', '--pointer=move@1180,270','--advance=60')
        self.assertEqual(values['mode'],1)
        self.assertAlmostEqual(values['modeX'],256,places=3)
        self.assertLess(abs(values['headX']-340),1)

    def test_wander_and_reset_buttons(self):
        values = self.run_scene('--pointer=click@506,783','--advance=60')
        self.assertEqual(values['mode'],2)
        self.assertAlmostEqual(values['modeX'],436,places=3)
        self.assertGreater(values['gazeX'],90)
        reset = self.run_scene('--pointer=click@506,783','--advance=60',
                               '--pointer=click@670,783','--advance=90')
        self.assertEqual(reset['mode'],0)
        self.assertAlmostEqual(reset['modeX'],76,places=3)
        self.assertAlmostEqual(reset['headX'],340,places=3)

    def test_release_outside_does_not_activate(self):
        values = self.run_scene('--pointer=down@506,783','--pointer=move@750,700',
                               '--pointer=up@750,700','--advance=60')
        self.assertEqual(values['mode'],0)

    def test_exit_returns_to_neutral(self):
        values = self.run_scene('--pointer=move@1100,240','--advance=60',
                               '--pointer=exit@1300,240','--advance=120')
        self.assertAlmostEqual(values['headX'],340,places=3)
        self.assertAlmostEqual(values['gazeX'],79,places=3)

    def test_reduced_motion_data_binding(self):
        values = self.run_scene('--data=motion=0','--data=mode=2',
                               '--pointer=move@1180,270','--advance=120')
        for key, expected in {'headX':340,'headY':450,'gazeX':79,'gazeY':117,
                              'bubbleY':116,'statusY':292,'modeX':436}.items():
            self.assertAlmostEqual(values[key],expected,places=3)


if __name__ == '__main__':
    unittest.main()
