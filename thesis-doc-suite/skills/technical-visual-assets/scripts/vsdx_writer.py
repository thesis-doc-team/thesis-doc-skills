#!/usr/bin/env python3
"""Minimal standards-based VSDX writer (Visio 2013+ Open Packaging format).

Why this exists
---------------
The project requires a real Visio file even on machines without Visio installed.
This writer produces a native ``.vsdx`` package from the same routed spec used
for SVG/draw.io: native shapes for nodes, native polyline shapes with arrowheads
for connectors, native text shapes for bilingual captions.  It is not an image
embedded in a Visio wrapper.

Honesty rule
------------
A package can be structurally valid without this machine having Visio.  The
writer therefore reports ``vsdx_verification = pending-visio-open`` unless a
real Visio COM open/save check has actually run.  It never claims "Visio opened
and approved" from ZIP/XML checks alone.
"""
from __future__ import annotations

import datetime as _dt
import html
import json
import math
import struct
import subprocess
import sys
import zipfile
from pathlib import Path

MAIN = "http://schemas.microsoft.com/office/visio/2012/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
CT = "http://schemas.openxmlformats.org/package/2006/content-types"
CP = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
DC = "http://purl.org/dc/elements/1.1/"
DCTERMS = "http://purl.org/dc/terms/"
XSI = "http://www.w3.org/2001/XMLSchema-instance"
EP = "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"

MM_IN = 25.4
CAPTION_SPACE_MM = 18.0
VISIO_PATHS = [
    r"C:\Program Files\Microsoft Office\root\Office16\VISIO.EXE",
    r"C:\Program Files (x86)\Microsoft Office\root\Office16\VISIO.EXE",
]


def _e(value):
    return html.escape(str(value), quote=True)


def _num(value, digits=4):
    return f"{float(value):.{digits}f}".rstrip("0").rstrip(".")


def visio_available():
    return any(Path(p).is_file() for p in VISIO_PATHS)


def _shape_common(shape_id, name, pin_x, pin_y, width, height, text="",
                  font_pt=9.5, fill="#FFFFFF", line="#000000", end_arrow=0,
                  no_line=False, no_fill=False, rounded=0.0, geometry=None):
    """Build one <Shape> in page inches.  Local geometry origin is bottom-left."""
    width = max(0.001, float(width))
    height = max(0.001, float(height))
    text = str(text or "")
    geom = geometry or []
    geom_xml = []
    if geom:
        geom_xml.append('<Geometry IX="0"><NoFill>%d</NoFill><NoLine>%d</NoLine>'
                        '<NoShow>0</NoShow><NoSnap>0</NoSnap>' %
                        (1 if no_fill else 0, 1 if no_line else 0))
        for i, (x, y) in enumerate(geom, 1):
            tag = "MoveTo" if i == 1 else "LineTo"
            geom_xml.append('<%s IX="%d"><X>%s</X><Y>%s</Y></%s>' %
                            (tag, i, _num(x), _num(y), tag))
        geom_xml.append("</Geometry>")
    else:
        geom_xml.append('<Geometry IX="0"><NoFill>%d</NoFill><NoLine>%d</NoLine>'
                        '<NoShow>0</NoShow><NoSnap>0</NoSnap></Geometry>' %
                        (1 if no_fill else 0, 1 if no_line else 0))
    return (
        '<Shape ID="%s" NameU="%s" Type="Shape" LineStyle="0" FillStyle="0" TextStyle="0">'
        '<XForm><PinX>%s</PinX><PinY>%s</PinY><Width>%s</Width><Height>%s</Height>'
        '<LocPinX>%s</LocPinX><LocPinY>%s</LocPinY><Angle>0</Angle><FlipX>0</FlipX>'
        '<FlipY>0</FlipY><ResizeMode>0</ResizeMode></XForm>'
        '<Fill><FillForegnd>%s</FillForegnd><FillBkgnd>%s</FillBkgnd><FillPattern>%d</FillPattern></Fill>'
        '<Line><LineColor>%s</LineColor><LineWeight>0.01</LineWeight><LinePattern>1</LinePattern>'
        '<Rounding>%s</Rounding><EndArrowSize>2</EndArrowSize><BeginArrow>0</BeginArrow>'
        '<EndArrow>%d</EndArrow></Line>'
        '<Char><Font>SimSun</Font><Size>%s</Size><Color>#000000</Color><Style>0</Style></Char>'
        '<Para><HorzAlign>1</HorzAlign><VertAlign>1</VertAlign></Para>'
        '<Text>%s</Text>%s</Shape>' % (
            _e(shape_id), _e(name), _num(pin_x), _num(pin_y), _num(width), _num(height),
            _num(width / 2.0), _num(height / 2.0), fill, fill,
            0 if no_fill else 1, line, _num(rounded, 4), int(end_arrow),
            _num(max(0.01, float(font_pt) / 72.0), 4),
            _e(text), "".join(geom_xml)))


def _node_geometry(shape, w, h):
    if shape == "diamond":
        return [(w / 2, h), (w, h / 2), (w / 2, 0), (0, h / 2), (w / 2, h)]
    return [(0, 0), (w, 0), (w, h), (0, h), (0, 0)]


def _text_shape(shape_id, text, pin_x, pin_y, width, height, font_pt):
    return _shape_common(shape_id, f"Text.{shape_id}", pin_x, pin_y, width, height,
                         text=text, font_pt=font_pt, no_line=True, no_fill=True,
                         geometry=[(0, 0), (width, 0), (width, height), (0, height), (0, 0)])


def _edge_shape(shape_id, edge, page_h_in, font_pt):
    pts = edge.get("points") or []
    if len(pts) < 2:
        raise ValueError("edge has no points")
    xs = [float(p[0]) for p in pts]
    ys = [float(p[1]) for p in pts]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    w_in = max(0.001, (max_x - min_x) / MM_IN)
    h_in = max(0.001, (max_y - min_y) / MM_IN)
    pin_x = ((min_x + max_x) / 2.0) / MM_IN
    pin_y = page_h_in - ((min_y + max_y) / 2.0) / MM_IN
    geom = []
    for x, y in pts:
        gx = (float(x) - min_x) / MM_IN
        gy = (max_y - float(y)) / MM_IN
        # avoid degenerate local coordinates when the path is one straight line
        if max_x - min_x < 0.01:
            gx = w_in / 2.0
        if max_y - min_y < 0.01:
            gy = h_in / 2.0
        geom.append((gx, gy))
    return _shape_common(shape_id, f"Edge.{shape_id}", pin_x, pin_y, w_in, h_in,
                         text="", font_pt=font_pt, fill="#FFFFFF", line="#000000",
                         end_arrow=4, no_fill=True, geometry=geom)


def build_parts(spec):
    w_mm = float(spec["width_mm"])
    h_mm = float(spec["height_mm"])
    font_pt = float(spec.get("font_pt", 9.5))
    page_w_in = w_mm / MM_IN
    page_h_in = (h_mm + CAPTION_SPACE_MM) / MM_IN
    cap = spec.get("_caption") or {}
    page_name = (cap.get("caption_zh") or "Page-1")[:60]

    shapes = []
    sid = 1
    for n in spec.get("nodes", []):
        x, y, nw, nh = (float(n[k]) for k in ("x", "y", "w", "h"))
        width, height = nw / MM_IN, nh / MM_IN
        pin_x = (x + nw / 2.0) / MM_IN
        pin_y = page_h_in - (y + nh / 2.0) / MM_IN
        geom = _node_geometry(n.get("shape", "rect"), width, height)
        rounded = height / 2.0 if n.get("shape") == "pill" else 0.0
        shapes.append(_shape_common(sid, f"Node.{n['id']}", pin_x, pin_y, width, height,
                                    text=n.get("label", ""), font_pt=font_pt,
                                    rounded=rounded, geometry=geom))
        sid += 1
    for e in spec.get("edges", []):
        shapes.append(_edge_shape(sid, e, page_h_in, font_pt))
        sid += 1
        pos = e.get("label_pos")
        if e.get("label") and pos:
            lx = float(pos["x"]) / MM_IN
            ly = page_h_in - float(pos["y"]) / MM_IN
            shapes.append(_text_shape(sid, str(e["label"]), lx, ly,
                                      max(0.2, float(pos["w"]) / MM_IN),
                                      max(0.12, float(pos["h"]) / MM_IN), font_pt))
            sid += 1
    # Native caption text below the diagram; still editable text, not pixels.
    if cap.get("caption_zh_full"):
        shapes.append(_text_shape(sid, cap["caption_zh_full"], page_w_in / 2.0,
                                  12.0 / MM_IN, page_w_in - 0.2, 0.28, 10.5))
        sid += 1
    if cap.get("caption_en_full"):
        shapes.append(_text_shape(sid, cap["caption_en_full"], page_w_in / 2.0,
                                  6.0 / MM_IN, page_w_in - 0.2, 0.28, 10.5))
        sid += 1

    page_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<PageContents xmlns="%s" xml:space="preserve"><Shapes>%s</Shapes></PageContents>' %
        (MAIN, "".join(shapes)))

    pages_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Pages xmlns="%s" xmlns:r="%s" xml:space="preserve">'
        '<Page ID="0" NameU="%s" Name="%s" ViewScale="-1" ViewCenterX="%s" ViewCenterY="%s">'
        '<PageSheet LineStyle="0" FillStyle="0" TextStyle="0">'
        '<PageWidth>%s</PageWidth><PageHeight>%s</PageHeight><PageScale>1</PageScale>'
        '<DrawingScale>1</DrawingScale><DrawingSizeType>3</DrawingSizeType>'
        '<DrawingScaleType>0</DrawingScaleType><InhibitSnap>0</InhibitSnap>'
        '<UIVisibility>0</UIVisibility><ShdwOffsetX>0.125</ShdwOffsetX>'
        '<ShdwOffsetY>-0.125</ShdwOffsetY></PageSheet><Rel r:id="rId1"/></Page>'
        '</Pages>' % (MAIN, REL, _e(page_name), _e(page_name),
                      _num(page_w_in / 2.0), _num(page_h_in / 2.0),
                      _num(page_w_in), _num(page_h_in)))

    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<VisioDocument xmlns="%s" xml:space="preserve">'
        '<DocumentSettings TopPage="0" DefaultTextStyle="0" DefaultLineStyle="0" '
        'DefaultFillStyle="0" DefaultGuideStyle="0"><GlueSettings>9</GlueSettings>'
        '<SnapSettings>65847</SnapSettings><SnapExtensions>34</SnapExtensions>'
        '<SnapAngles/><DynamicGridEnabled>1</DynamicGridEnabled>'
        '<TabStopWidth>0.5</TabStopWidth><ProtectStyles>0</ProtectStyles>'
        '<ProtectShapes>0</ProtectShapes><ProtectMasters>0</ProtectMasters>'
        '<ProtectBkgnds>0</ProtectBkgnds></DocumentSettings>'
        '<Colors><ColorEntry IX="0" RGB="#000000"/><ColorEntry IX="1" RGB="#FFFFFF"/></Colors>'
        '<FaceNames><FaceName NameU="SimSun" UnicodeRanges="-536859905 -1073732485 9 0" '
        'CharSets="1073742336" Panose="2 2 6 3 5 2 2 2 2 4" Flags="325"/></FaceNames>'
        '<StyleSheets><StyleSheet ID="0" NameU="No Style" IsCustomName="1">'
        '<Line><LineWeight>0.01</LineWeight><LineColor>#000000</LineColor>'
        '<LinePattern>1</LinePattern><Rounding>0</Rounding><EndArrowSize>2</EndArrowSize>'
        '<BeginArrow>0</BeginArrow><EndArrow>0</EndArrow></Line>'
        '<Fill><FillForegnd>#FFFFFF</FillForegnd><FillBkgnd>#FFFFFF</FillBkgnd>'
        '<FillPattern>1</FillPattern></Fill>'
        '<Text><Font>SimSun</Font><Size>0.12</Size><Color>#000000</Color>'
        '<Style>0</Style></Text><Para><HorzAlign>1</HorzAlign><VertAlign>1</VertAlign></Para>'
        '</StyleSheet></StyleSheets>'
        '<DocumentSheet NameU="TheDoc" LineStyle="0" FillStyle="0" TextStyle="0">'
        '<PageWidth>8.5</PageWidth><PageHeight>11</PageHeight><PageScale>1</PageScale>'
        '<DrawingScale>1</DrawingScale><DrawingSizeType>3</DrawingSizeType>'
        '<DrawingScaleType>0</DrawingScaleType></DocumentSheet>'
        '</VisioDocument>' % MAIN)

    windows_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Windows xmlns="%s" ClientWidth="1600" ClientHeight="900">'
        '<Window ID="0" WindowType="Drawing" WindowState="1073741824" WindowLeft="0" '
        'WindowTop="0" WindowWidth="1600" WindowHeight="900" ContainerType="Page" '
        'Page="0" ViewScale="-1" ViewCenterX="%s" ViewCenterY="%s"/></Windows>' %
        (MAIN, _num(page_w_in / 2.0), _num(page_h_in / 2.0)))

    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Types xmlns="%s">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/visio/document.xml" ContentType="application/vnd.ms-visio.drawing.main+xml"/>'
        '<Override PartName="/visio/pages/pages.xml" ContentType="application/vnd.ms-visio.pages+xml"/>'
        '<Override PartName="/visio/pages/page1.xml" ContentType="application/vnd.ms-visio.page+xml"/>'
        '<Override PartName="/visio/windows.xml" ContentType="application/vnd.ms-visio.windows+xml"/>'
        '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
        '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
        '</Types>' % CT)

    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="%s">'
        '<Relationship Id="rId1" Type="http://schemas.microsoft.com/visio/2010/relationships/document" Target="visio/document.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
        '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
        '</Relationships>' % PKG_REL)

    document_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="%s">'
        '<Relationship Id="rId1" Type="http://schemas.microsoft.com/visio/2010/relationships/pages" Target="pages/pages.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.microsoft.com/visio/2010/relationships/windows" Target="windows.xml"/>'
        '</Relationships>' % PKG_REL)

    pages_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="%s">'
        '<Relationship Id="rId1" Type="http://schemas.microsoft.com/visio/2010/relationships/page" Target="page1.xml"/>'
        '</Relationships>' % PKG_REL)

    page1_rels = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="%s"/>\n' % PKG_REL

    now = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    core_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<cp:coreProperties xmlns:cp="%s" xmlns:dc="%s" xmlns:dcterms="%s" xmlns:xsi="%s">'
        '<dc:title>%s</dc:title><dc:creator>technical-visual-assets</dc:creator>'
        '<cp:lastModifiedBy>technical-visual-assets</cp:lastModifiedBy>'
        '<dcterms:created xsi:type="dcterms:W3CDTF">%s</dcterms:created>'
        '<dcterms:modified xsi:type="dcterms:W3CDTF">%s</dcterms:modified>'
        '</cp:coreProperties>' % (CP, DC, DCTERMS, XSI,
                                  _e(cap.get("caption_zh_full") or page_name), now, now))

    app_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Properties xmlns="%s" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
        '<Application>Microsoft Visio</Application><AppVersion>16.0000</AppVersion>'
        '<Company>technical-visual-assets</Company></Properties>' % EP)

    return {
        "[Content_Types].xml": content_types,
        "_rels/.rels": root_rels,
        "docProps/core.xml": core_xml,
        "docProps/app.xml": app_xml,
        "visio/document.xml": document_xml,
        "visio/_rels/document.xml.rels": document_rels,
        "visio/pages/pages.xml": pages_xml,
        "visio/pages/_rels/pages.xml.rels": pages_rels,
        "visio/pages/page1.xml": page_xml,
        "visio/pages/_rels/page1.xml.rels": page1_rels,
        "visio/windows.xml": windows_xml,
    }


def write_vsdx(spec, output):
    parts = build_parts(spec)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, payload in parts.items():
            z.writestr(name, payload.encode("utf-8"))
    report = validate_vsdx(output)
    report["path"] = str(output)
    return report


def validate_vsdx(path):
    """Structural validation only; never claims Visio opened the file."""
    p = Path(path)
    if not p.is_file():
        return {"status": "MISSING", "issues": ["file does not exist"]}
    issues = []
    required = {"[Content_Types].xml", "_rels/.rels", "docProps/core.xml",
                "docProps/app.xml", "visio/document.xml", "visio/_rels/document.xml.rels",
                "visio/pages/pages.xml", "visio/pages/_rels/pages.xml.rels",
                "visio/pages/page1.xml"}
    try:
        with zipfile.ZipFile(p) as z:
            names = set(z.namelist())
            missing = sorted(required - names)
            if missing:
                issues.append("missing parts: " + ", ".join(missing))
            for name in names:
                if name.endswith(".xml") or name.endswith(".rels"):
                    try:
                        import xml.etree.ElementTree as ET
                        ET.fromstring(z.read(name))
                    except Exception as exc:  # noqa: BLE001
                        issues.append(f"invalid XML {name}: {exc}")
            shape_count = 0
            if "visio/pages/page1.xml" in names:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(z.read("visio/pages/page1.xml"))
                shape_count = len(root.findall(f".//{{{MAIN}}}Shape"))
                if shape_count == 0:
                    issues.append("page1.xml has no shapes")
            ct = z.read("[Content_Types].xml").decode("utf-8") if "[Content_Types].xml" in names else ""
            for part in ("/visio/document.xml", "/visio/pages/pages.xml", "/visio/pages/page1.xml"):
                if part not in ct:
                    issues.append("content type override missing: " + part)
            # Every relationship target must exist in the package.
            for relname in [n for n in names if n.endswith(".rels")]:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(z.read(relname))
                rp = Path(relname)
                if rp.name == ".rels" and rp.parent.name == "_rels" and len(rp.parts) == 2:
                    base = Path(".")
                else:
                    base = rp.parent.parent
                for rel in root:
                    target = rel.attrib.get("Target", "")
                    if not target or target.startswith("http") or target.startswith("/"):
                        continue
                    resolved = (base / target).as_posix().lstrip("./")
                    if resolved not in names:
                        issues.append(f"relationship target missing: {relname} -> {target}")
    except (OSError, zipfile.BadZipFile) as exc:
        return {"status": "INVALID", "issues": [str(exc)]}
    return {
        "status": "STRUCTURALLY_VALID_VSDX" if not issues else "INVALID_VSDX",
        "issues": issues,
        "shape_count": shape_count,
        "visio_installed": visio_available(),
        "visio_open_verification": "pending-visio-open" if not visio_available() else "not-run",
        "native_visio_format": True,
        "notice": "VSDX 包结构与 XML 已检查；是否能在本机 Visio 打开仍需 Visio/WPS 实际验证。",
    }


def main():
    import argparse
    ap = argparse.ArgumentParser(description="根据已布线的 spec 生成原生 VSDX")
    ap.add_argument("--spec", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    spec = json.loads(Path(args.spec).read_text("utf-8"))
    report = write_vsdx(spec, args.out)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("status") == "STRUCTURALLY_VALID_VSDX" else 2


if __name__ == "__main__":
    raise SystemExit(main())