#!/usr/bin/env python3
"""Exercise the real compiled .riv in Chromium and capture its rendered loop.

Install test-only dependencies: pip install playwright Pillow
Use --runtime for an unpacked @rive-app/canvas@2.42.1 npm package.
--offline-html tests a self-contained copy where network serving is unavailable.
"""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import json
from pathlib import Path
import shutil
import threading
import xml.etree.ElementTree as ET
from PIL import Image, ImageChops, ImageStat
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path)
    parser.add_argument('--offline-html', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT/'build/browser')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    animation = ET.parse(ROOT/'scene.rml').find('.//LinearAnimation')
    cycle = int(animation.get('duration'))/int(animation.get('fps'))
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *_): pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(ROOT/'web')))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    checks, errors = [], []
    with sync_playwright() as p:
        binary = shutil.which('chromium') or shutil.which('google-chrome')
        browser = p.chromium.launch(executable_path=binary, headless=True, args=['--no-sandbox'])
        page = browser.new_page(viewport={'width': 1280, 'height': 900}, device_scale_factor=1)
        page.on('pageerror', lambda e: errors.append(str(e)))
        def local_runtime(route):
            name = route.request.url.split('/')[-1]
            file = args.runtime/name
            if not file.is_file():
                route.abort(); return
            mime = 'application/wasm' if name.endswith('.wasm') else 'text/javascript'
            route.fulfill(path=str(file), content_type=mime, headers={'Access-Control-Allow-Origin': '*'})
        if args.runtime:
            page.route('https://unpkg.com/@rive-app/canvas@2.42.1/**', local_runtime)
        def load():
            if args.offline_html:
                page.set_content(args.offline_html.read_text(), wait_until='load')
            else:
                page.goto(f'http://127.0.0.1:{server.server_port}/')
            page.wait_for_function('window.catDemo && catDemo.ready', timeout=20000)
        def pose(t):
            # Bypass the demo's modulo time wrapping: t=cycle tests the actual
            # final Rive keyframe, rather than accidentally re-testing frame 0.
            page.evaluate('(t) => { catDemo.seek(0); catDemo.player.scrub("Walk", t); }', t)
            page.wait_for_timeout(65)
            return page.locator('canvas').screenshot()
        load()
        checks.append('compiled .riv loads in the official Canvas runtime')
        assert page.locator('#travel').get_attribute('aria-pressed') == 'false'
        checks.append('default mode is the centered in-place walk loop')
        zero = pose(0)
        pixels = Image.open(BytesIO(zero)).convert('RGB')
        assert sum(pixels.convert('L').histogram()[:100]) > 1000, 'Blank Rive render'
        checks.append('actual rasterized cat is not a blank frame')
        quarter = pose(cycle/4)
        assert zero != quarter, 'Walk pose does not change'
        endpoint = Image.open(BytesIO(pose(cycle))).convert('RGB')
        seam_error = max(ImageStat.Stat(ImageChops.difference(pixels, endpoint)).mean)
        assert seam_error < .1, f'Native first/last keyframes differ: {seam_error}'
        checks.extend(['native walk pose changes', 'native final keyframe closes the loop without JS modulo'])
        pose(0)
        page.screenshot(path=str(args.output/'desktop.png'), full_page=True)
        page.locator('#travel').click()
        page.locator('#play').click()
        x0 = page.evaluate('catDemo.x')
        page.wait_for_timeout(300)
        assert page.evaluate('catDemo.x') > x0+5
        page.locator('#play').click(); page.wait_for_timeout(100)
        x0 = page.evaluate('catDemo.x'); paused = page.locator('canvas').screenshot()
        page.wait_for_timeout(150)
        assert page.evaluate('catDemo.x') == x0
        assert paused == page.locator('canvas').screenshot()
        checks.extend(['forward travel', 'pause freezes pose and position'])
        page.locator('#travel').click()
        page.locator('#play').click(); x0 = page.evaluate('catDemo.x')
        before = page.locator('canvas').screenshot(); page.wait_for_timeout(300)
        assert page.evaluate('catDemo.x') == x0
        assert before != page.locator('canvas').screenshot()
        page.locator('#play').click()
        checks.append('in-place mode animates without translation')
        page.locator('#direction').click()
        assert 'scaleX(-1)' in page.locator('#actor').get_attribute('style')
        checks.append('left/right mirroring')
        page.locator('#travel').click(); page.locator('#play').click()
        x0 = page.evaluate('catDemo.x'); page.wait_for_timeout(300)
        assert page.evaluate('catDemo.x') < x0-5
        page.locator('#play').click(); page.locator('#travel').click()
        page.locator('#direction').click()
        checks.append('left-facing travel moves left, not backwards')
        keyframes = [Image.open(BytesIO(pose(i*cycle/8))).convert('RGB') for i in range(9)]
        assert len({frame.tobytes() for frame in keyframes[:8]}) == 8
        checks.append('eight distinct native poses plus the closing pose')
        tile = max(keyframes[0].size)
        sheet = Image.new('RGB', (tile*3, tile*3), 'white')
        for i, frame in enumerate(keyframes):
            sheet.paste(frame, ((i%3)*tile, (i//3)*tile+(tile-frame.height)//2))
            frame.save(args.output/f'keyframe-{i+1:02d}.png')
        sheet.save(args.output/'contact-sheet.png')
        frames = []
        for i in range(36):
            frames.append(Image.open(BytesIO(pose(i*cycle/36))).convert('RGB'))
        # Exclude the duplicated endpoint so the GIF never holds the seam twice.
        frames[0].save(args.output/'walking-cat.gif', save_all=True, append_images=frames[1:], duration=[30,30,40]*12, loop=0, disposal=2)
        frames[0].save(args.output/'cat.png')
        page.set_viewport_size({'width': 390, 'height': 844})
        pose(0)
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.screenshot(path=str(args.output/'mobile.png'), full_page=True)
        checks.append('mobile page has no horizontal overflow')
        # A separate page avoids reusing a WASM instance on a live document.
        page.close()
        page = browser.new_page(viewport={'width': 1280, 'height': 900}, reduced_motion='reduce')
        page.on('pageerror', lambda e: errors.append(str(e)))
        if args.runtime:
            page.route('https://unpkg.com/@rive-app/canvas@2.42.1/**', local_runtime)
        load()
        assert not page.evaluate('catDemo.running')
        checks.append('reduced-motion preference starts paused')
        assert not errors, errors
        checks.append('no uncaught browser exceptions')
        browser.close()
    server.shutdown()
    result = {'passed': len(checks), 'checks': checks, 'errors': errors,
              'seam_max_mean_channel_error': seam_error,
              'renderer': '@rive-app/canvas 2.42.1, real compiled walking-cat.riv',
              'mode': 'embedded assets' if args.offline_html else 'HTTP with locally pinned runtime'}
    (args.output/'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
