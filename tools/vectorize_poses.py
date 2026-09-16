"""Trace the three CC-BY reference PNG poses into native RML paths."""

from pathlib import Path
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "tools/scene_template.xml"
OUTPUT = ROOT / "scene.rml"
SCALE = 0.46
ORIGIN_X = 500
ORIGIN_Y = 455

POSES = [
    ("Center", ROOT / "references/pose-center.png", "0:400", "0:211", 1),
    ("Left", ROOT / "references/pose-left.png", "0:500", "0:212", 0),
    ("Right", ROOT / "references/pose-right.png", "0:600", "0:213", 0),
]

LAYERS = [
    ("Black", "FF000000", lambda gray, alpha: (alpha > 56) & (gray < 96)),
    ("White", "FFFFFFFF", lambda gray, alpha: (alpha > 56) & (gray >= 238)),
    ("Shadow", "FFC7C7C7", lambda gray, alpha: (alpha > 56) & (gray >= 96) & (gray < 238)),
]


def number(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def trace(mask: np.ndarray) -> list[np.ndarray]:
    binary = (mask.astype(np.uint8) * 255)
    contours, _ = cv2.findContours(binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    paths: list[np.ndarray] = []
    for contour in contours:
        if abs(cv2.contourArea(contour)) < 7:
            continue
        simplified = cv2.approxPolyDP(contour, 1.35, True).reshape(-1, 2)
        if len(simplified) >= 3:
            paths.append(simplified)
    return paths


def pose_xml(name: str, source: Path, node_id: str, opacity_property: str, authored_opacity: int) -> list[str]:
    image = cv2.imread(str(source), cv2.IMREAD_UNCHANGED)
    if image is None or image.shape[2] != 4:
        raise RuntimeError(f"Unable to read RGBA reference: {source}")
    gray = image[:, :, 0]
    alpha = image[:, :, 3]
    lines = [
        f'            <Node opacity="{authored_opacity}" name="Pose {name}" id="{node_id}">',
        f'                <DataBindContext sourcePathIds="0:200-{opacity_property}" propertyKey="18"/>',
    ]
    for layer_name, color, selector in LAYERS:
        paths = trace(selector(gray, alpha))
        lines.append(f'                <Shape name="{name} {layer_name}">')
        for contour in paths:
            lines.append('                    <PointsPath isClosed="true" name="Contour">')
            for x, y in contour:
                px = (float(x) - ORIGIN_X) * SCALE
                py = (float(y) - ORIGIN_Y) * SCALE
                lines.append(f'                        <StraightVertex x="{number(px)}" y="{number(py)}"/>')
            lines.append('                    </PointsPath>')
        lines.append(f'                    <Fill fillRule="evenOdd" name="Fill"><SolidColor colorValue="{color}" name="Color"/></Fill>')
        lines.append('                </Shape>')
    lines.append('            </Node>')
    return lines


document = []
for pose in POSES:
    document.extend(pose_xml(*pose))
template = TEMPLATE.read_text(encoding="utf-8")
generated = "\n".join(document)
if "<!-- GENERATED_POSES -->" not in template:
    raise RuntimeError("Template marker is missing")
OUTPUT.write_text(template.replace("<!-- GENERATED_POSES -->", generated), encoding="utf-8")
print(f"wrote {OUTPUT} ({OUTPUT.stat().st_size} bytes)")
