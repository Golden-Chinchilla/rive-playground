#!/usr/bin/env python3
"""Convert the supplied character SVG into a clean, layered Rive RML scene.

This intentionally supports the small SVG path subset used by the character
(M/L/H/V/C/Z). It keeps the original SVG group names and paint values so the
generated RML remains easy to inspect and animate.
"""

from __future__ import annotations

import argparse
import math
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


TOKEN = re.compile(r"[MLHVCZmlhvcz]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")


@dataclass
class Anchor:
    x: float
    y: float
    incoming: tuple[float, float] | None = None
    outgoing: tuple[float, float] | None = None


def fmt(value: float) -> str:
    value = 0.0 if abs(value) < 1e-9 else value
    return f"{value:.4f}".rstrip("0").rstrip(".")


def parse_path(data: str) -> list[tuple[list[Anchor], bool]]:
    tokens = TOKEN.findall(data.replace(",", " "))
    result: list[tuple[list[Anchor], bool]] = []
    anchors: list[Anchor] = []
    i = 0
    command = ""
    x = y = start_x = start_y = 0.0

    def finish(closed: bool = False) -> None:
        nonlocal anchors
        if anchors:
            result.append((anchors, closed))
            anchors = []

    def number() -> float:
        nonlocal i
        value = float(tokens[i])
        i += 1
        return value

    while i < len(tokens):
        if tokens[i].isalpha():
            command = tokens[i]
            i += 1
        relative = command.islower()
        op = command.upper()
        if op == "M":
            nx, ny = number(), number()
            if relative:
                nx, ny = x + nx, y + ny
            finish()
            x, y = nx, ny
            start_x, start_y = x, y
            anchors.append(Anchor(x, y))
            command = "l" if relative else "L"
        elif op == "L":
            nx, ny = number(), number()
            if relative:
                nx, ny = x + nx, y + ny
            x, y = nx, ny
            anchors.append(Anchor(x, y))
        elif op == "H":
            nx = number()
            x = x + nx if relative else nx
            anchors.append(Anchor(x, y))
        elif op == "V":
            ny = number()
            y = y + ny if relative else ny
            anchors.append(Anchor(x, y))
        elif op == "C":
            c1x, c1y, c2x, c2y, nx, ny = (number() for _ in range(6))
            if relative:
                c1x, c1y = x + c1x, y + c1y
                c2x, c2y = x + c2x, y + c2y
                nx, ny = x + nx, y + ny
            anchors[-1].outgoing = (c1x, c1y)
            anchors.append(Anchor(nx, ny, incoming=(c2x, c2y)))
            x, y = nx, ny
        elif op == "Z":
            x, y = start_x, start_y
            finish(True)
            command = ""
        else:
            raise ValueError(f"Unsupported SVG command {command!r}")
    finish()
    return result


def color(value: str) -> str:
    value = value.lstrip("#")
    if len(value) == 6:
        return "FF" + value.upper()
    if len(value) == 8:
        return value[6:].upper() + value[:6].upper()
    raise ValueError(f"Unsupported SVG color {value!r}")


def handle(anchor: Anchor, point: tuple[float, float] | None) -> tuple[str, str]:
    if point is None:
        return "0", "0"
    dx, dy = point[0] - anchor.x, point[1] - anchor.y
    return fmt(math.atan2(dy, dx)), fmt(math.hypot(dx, dy))


def path_rml(
    element: ET.Element,
    inherited_fill: str | None,
    inherited_stroke: str | None,
    inherited_stroke_width: str | None,
    indent: str,
) -> list[str]:
    name = element.attrib.get("id", "Path")
    fill = element.attrib.get("fill", inherited_fill)
    stroke = element.attrib.get("stroke", inherited_stroke)
    if stroke and "fill" not in element.attrib:
        fill = None
    lines = [f'{indent}<Shape name="{name}">']
    for index, (anchors, closed) in enumerate(parse_path(element.attrib["d"])):
        lines.append(f'{indent}    <PointsPath isClosed="{str(closed).lower()}" name="Contour {index + 1}">')
        for anchor in anchors:
            in_rot, in_dist = handle(anchor, anchor.incoming)
            out_rot, out_dist = handle(anchor, anchor.outgoing)
            if anchor.incoming is None and anchor.outgoing is None:
                lines.append(f'{indent}        <StraightVertex x="{fmt(anchor.x)}" y="{fmt(anchor.y)}"/>')
            else:
                lines.append(
                    f'{indent}        <CubicDetachedVertex x="{fmt(anchor.x)}" y="{fmt(anchor.y)}" '
                    f'inRotation="{in_rot}" inDistance="{in_dist}" '
                    f'outRotation="{out_rot}" outDistance="{out_dist}"/>'
                )
        lines.append(f"{indent}    </PointsPath>")
    if fill and fill != "none":
        lines.append(f'{indent}    <Fill name="Fill"><SolidColor colorValue="{color(fill)}" name="Color"/></Fill>')
    if stroke and stroke != "none":
        width = element.attrib.get("stroke-width", inherited_stroke_width or "1")
        cap = element.attrib.get("stroke-linecap", "butt")
        lines.append(f'{indent}    <Stroke thickness="{width}" cap="{cap}" join="round" name="Stroke"><SolidColor colorValue="{color(stroke)}" name="Color"/></Stroke>')
    lines.append(f"{indent}</Shape>")
    return lines


def ellipse_rml(element: ET.Element, inherited_fill: str | None, indent: str) -> list[str]:
    name = element.attrib.get("id", "Ellipse")
    fill = element.attrib.get("fill", inherited_fill or "#000000")
    cx, cy = element.attrib["cx"], element.attrib["cy"]
    width, height = float(element.attrib["rx"]) * 2, float(element.attrib["ry"]) * 2
    return [
        f'{indent}<Shape x="{cx}" y="{cy}" name="{name}">',
        f'{indent}    <Ellipse width="{fmt(width)}" height="{fmt(height)}" originX="0.5" originY="0.5" name="Path"/>',
        f'{indent}    <Fill name="Fill"><SolidColor colorValue="{color(fill)}" name="Color"/></Fill>',
        f'{indent}</Shape>',
    ]


def group_rml(group: ET.Element, indent: str, eye_bind: bool = False) -> list[str]:
    name = group.attrib.get("id", "Group")
    inherited_fill = group.attrib.get("fill")
    inherited_stroke = group.attrib.get("stroke")
    inherited_stroke_width = group.attrib.get("stroke-width")
    attrs = ' x="0" y="0"' if eye_bind else ""
    lines = [f'{indent}<Node{attrs} name="SVG {name}">']
    if eye_bind:
        lines += [
            f'{indent}    <DataBindContext sourcePathIds="0:200-0:205" propertyKey="13"/>',
            f'{indent}    <DataBindContext sourcePathIds="0:200-0:206" propertyKey="14"/>',
        ]
    children = list(group)
    for child in reversed(children):
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "path":
            lines.extend(path_rml(child, inherited_fill, inherited_stroke, inherited_stroke_width, indent + "    "))
        elif tag == "ellipse":
            lines.extend(ellipse_rml(child, inherited_fill, indent + "    "))
    lines.append(f"{indent}</Node>")
    return lines


def build(svg_path: Path) -> str:
    root = ET.parse(svg_path).getroot()
    groups = {g.attrib.get("id"): g for g in list(root) if g.tag.rsplit("}", 1)[-1] == "g"}
    head_order = [g.attrib.get("id") for g in list(root) if g.tag.rsplit("}", 1)[-1] == "g" and g.attrib.get("id") not in {"background", "neck"}]
    lines = [
        '<Rive version="1" kind="fragment">',
        '    <Artboard defaultStateMachineId="0:7" viewModelId="0:200" clip="true" width="668" height="816" styleId="0:5" name="SVG Mouse Follow" id="0:2">',
        '        <Fill name="Background"><SolidColor colorValue="FFFFFFFF" name="White"/></Fill>',
        '        <LayoutComponentStyle name="Artboard Style" id="0:5"/>',
        '        <LayoutComponent width="668" height="816" styleId="0:11" name="Pointer Input" id="0:10">',
        '            <LayoutComponentStyle layoutWidthScaleType="1" layoutHeightScaleType="1" widthUnitsValue="3" heightUnitsValue="3" name="Pointer Style" id="0:11"/>',
        '            <ScriptedLayout scriptAssetId="0:300" name="Continuous Pointer Follow" id="0:12"/>',
        '        </LayoutComponent>',
        '',
        '        <Node name="Static Neck">',
    ]
    lines.extend(group_rml(groups["neck"], "            ")[1:-1])
    lines += [
        '        </Node>',
        '',
        '        <Node x="334" y="350" name="Head Follow" id="0:30">',
        '            <DataBindContext sourcePathIds="0:200-0:202" propertyKey="13"/>',
        '            <DataBindContext sourcePathIds="0:200-0:203" propertyKey="14"/>',
        '            <DataBindContext sourcePathIds="0:200-0:204" propertyKey="15"/>',
        '            <Node x="-334" y="-350" name="SVG Head Artwork">',
    ]
    for group_name in reversed(head_order):
        lines.extend(group_rml(groups[group_name], "                ", eye_bind=group_name == "eyes"))
    lines += [
        '            </Node>',
        '        </Node>',
        '',
        '        <StateMachine name="Mouse Follow" id="0:7">',
        '            <StateMachineLayer name="Active" id="0:8">',
        '                <AnyState x="300" y="-100"/><ExitState x="400" y="-100"/>',
        '                <EntryState x="0" y="0"/>',
        '            </StateMachineLayer>',
        '        </StateMachine>',
        '    </Artboard>',
        '',
        '    <ViewModel defaultInstanceId="0:201" name="CharacterMotion" id="0:200">',
        '        <ViewModelPropertyNumber name="headX" id="0:202"/>',
        '        <ViewModelPropertyNumber name="headY" id="0:203"/>',
        '        <ViewModelPropertyNumber name="headRotation" id="0:204"/>',
        '        <ViewModelPropertyNumber name="eyeX" id="0:205"/>',
        '        <ViewModelPropertyNumber name="eyeY" id="0:206"/>',
        '        <ViewModelInstance exports="true" name="Default" id="0:201">',
        '            <ViewModelInstanceNumber propertyValue="334" viewModelPropertyId="0:202"/>',
        '            <ViewModelInstanceNumber propertyValue="350" viewModelPropertyId="0:203"/>',
        '            <ViewModelInstanceNumber propertyValue="0" viewModelPropertyId="0:204"/>',
        '            <ViewModelInstanceNumber propertyValue="0" viewModelPropertyId="0:205"/>',
        '            <ViewModelInstanceNumber propertyValue="0" viewModelPropertyId="0:206"/>',
        '        </ViewModelInstance>',
        '    </ViewModel>',
        '    <ScriptAsset file="track.luau" name="Pointer tracking" id="0:300"/>',
        '</Rive>',
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("svg", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.write_text(build(args.svg), encoding="utf-8")


if __name__ == "__main__":
    main()
