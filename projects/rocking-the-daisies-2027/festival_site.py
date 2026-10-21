"""
Rocking the Daisies 2027 - conceptual 3D festival site model
=============================================================

Builds a complete miniature-style festival site in Blender using bpy only:
terrain plinth, dam (lake), access road, walking paths, central arena with a
main stage and two secondary stages, four camping zones, parking, entrances,
facilities and vegetation. It then saves a .blend file and renders a
top-down orthographic PNG with Cycles.

This is a conceptual design study, not an official or surveyed site plan.
There is deliberately no text, signage, icons or labels anywhere in the scene.

How to run
----------
Command line (Blender 4.2 LTS or newer, including 5.x):

    blender --background --python festival_site.py -- --out ./output

Options (everything after the "--"):

    --stage layout|full    layout = terrain, water, roads, paths, arena ground
                           and camping grounds only (the "preview" stage);
                           full = everything (default)
    --views top,oblique    cameras to render (default: top)
    --res 4800             render width in pixels for the top view
    --samples 128          Cycles samples
    --no-render            build and save the .blend without rendering
    --seed 2027            random seed for scatter/placement

Inside Blender: open the Scripting workspace, open this file in the Text
Editor and press Run Script. Edit CONFIG below to change the options there.
Rendering a 4800 px image takes several minutes on a CPU; set
CONFIG["render"] = False if you only want the scene.

It also runs with the standalone `bpy` module from PyPI:

    pip install bpy   # Python version must match the bpy wheel
    python festival_site.py --out ./output

Scene conventions: 1 Blender unit = 1 metre, +Y = north (top of the map),
+X = east. The site is 1000 m x 660 m centred on the origin.
"""

import argparse
import math
import os
import random
import sys
import time

import bpy  # noqa: E402  (bpy must be imported before bmesh/mathutils in the pip module)
import bmesh
import numpy as np
from mathutils import Matrix, Vector
from mathutils import noise as mnoise

CONFIG = {
    "out_dir": None,          # None = "<folder of this script>/output"
    "stage": "full",          # "layout" or "full"
    "render": True,
    "views": ("top",),        # any of "top", "oblique"
    "res_x": 4800,
    "samples": 128,
    "seed": 2027,
    "blend_name": "rocking_the_daisies_2027_site.blend",
}

T0 = time.time()


def log(msg):
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


# =============================================================================
# 0. GENERIC HELPERS - colour, collections, materials
# =============================================================================

def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def col(hexstr, alpha=1.0):
    h = hexstr.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    return (srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b), alpha)


COLLS = {}
COLLECTION_NAMES = [
    "Terrain", "Roads and Paths", "Trees and Vegetation", "Main Arena",
    "Secondary Stages", "Camping General", "Camping Priority",
    "Camping Wildflower", "Glamping Village", "Parking", "Entrances",
    "Facilities", "Lake", "Lighting and Camera",
]
ASSET_COLL = "Asset Library (not rendered)"


def C(name):
    """Return (and lazily create) a top-level collection."""
    if name not in COLLS:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
        COLLS[name] = c
    return COLLS[name]


def reset_scene():
    """Remove everything so the script can be re-run in an open Blender."""
    ids = []
    for coll in (bpy.data.objects, bpy.data.meshes, bpy.data.materials,
                 bpy.data.lights, bpy.data.cameras, bpy.data.collections,
                 bpy.data.curves, bpy.data.worlds, bpy.data.images):
        ids.extend(list(coll))
    if ids:
        bpy.data.batch_remove(ids)
    COLLS.clear()
    MATS.clear()
    _INST_COUNT.clear()


MATS = {}


def _sock(sockets, name, typ=None):
    cands = [s for s in sockets if s.name == name and (typ is None or s.type == typ)]
    for s in cands:
        if getattr(s, "enabled", True):
            return s
    if cands:
        return cands[0]
    raise KeyError(name)


def _set(node, names, value):
    for n in names:
        s = node.inputs.get(n)
        if s is not None:
            s.default_value = value
            return


def _palette_ramp(ramp, palette):
    """Constant colour ramp with one swatch per palette entry (max 32)."""
    cr = ramp.color_ramp
    cr.interpolation = "CONSTANT"
    n = len(palette)
    els = cr.elements
    els[0].position = 0.0
    if n == 1:
        els[1].position = 1.0
        for e in els:
            e.color = col(palette[0])
        return
    els[1].position = 1.0 / n
    for i in range(2, n):
        els.new(i / n)
    for e in els:
        i = min(int(round(e.position * n)), n - 1)
        e.color = col(palette[i])


def material(name, color="#ffffff", rough=0.75, spec=0.35, metal=0.0,
             palette=None, noise=(), bump=0.0, bump_scale=0.6, emission=None,
             strength=0.0, attr=None, coat=0.0, speckle=None, alpha=1.0):
    """Principled material factory.

    palette  - list of hex colours picked per object (Object Info > Random);
               lets thousands of linked duplicates share one mesh + material.
    noise    - list of dicts {c2, scale, lo, hi, amt, blend} that mix a second
               colour in through procedural noise (object space, metres).
    speckle  - dict for wildflower dots via Voronoi cells.
    attr     - colour attribute name used as base colour (lake depth).
    """
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.new(name)
    if m.node_tree is None:
        m.use_nodes = True
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    bsdf = next(n for n in N if n.bl_idname == "ShaderNodeBsdfPrincipled")
    m.diffuse_color = col(color)
    _set(bsdf, ["Roughness"], rough)
    _set(bsdf, ["Metallic"], metal)
    _set(bsdf, ["Specular IOR Level", "Specular"], spec)
    if coat:
        _set(bsdf, ["Coat Weight", "Coat"], coat)
    if alpha < 1.0:
        _set(bsdf, ["Alpha"], alpha)
    tc = N.new("ShaderNodeTexCoord")
    cur = None
    if attr:
        a = N.new("ShaderNodeAttribute")
        a.attribute_name = attr
        cur = a.outputs["Color"]
    elif palette:
        oi = N.new("ShaderNodeObjectInfo")
        ramp = N.new("ShaderNodeValToRGB")
        _palette_ramp(ramp, palette)
        L.new(oi.outputs["Random"], ramp.inputs[0])
        cur = ramp.outputs[0]
    for nz in noise:
        tex = N.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = nz.get("scale", 0.05)
        tex.inputs["Detail"].default_value = nz.get("detail", 3.0)
        tex.inputs["Roughness"].default_value = nz.get("rough", 0.55)
        L.new(tc.outputs["Object"], tex.inputs["Vector"])
        ramp = N.new("ShaderNodeValToRGB")
        e = ramp.color_ramp.elements
        e[0].position, e[1].position = nz.get("lo", 0.4), nz.get("hi", 0.62)
        amt = nz.get("amt", 1.0)
        e[0].color, e[1].color = (0, 0, 0, 1), (amt, amt, amt, 1)
        L.new(tex.outputs[0], ramp.inputs[0])
        mix = N.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = nz.get("blend", "MIX")
        a_in, b_in = _sock(mix.inputs, "A", "RGBA"), _sock(mix.inputs, "B", "RGBA")
        if cur is None:
            a_in.default_value = col(color)
        else:
            L.new(cur, a_in)
        b_in.default_value = col(nz["c2"])
        L.new(ramp.outputs[0], _sock(mix.inputs, "Factor", "VALUE"))
        cur = _sock(mix.outputs, "Result", "RGBA")
    if speckle:
        # Voronoi cells -> sparse dots, each dot gets one of the flower colours
        vor = N.new("ShaderNodeTexVoronoi")
        vor.inputs["Scale"].default_value = speckle.get("scale", 1.6)
        L.new(tc.outputs["Object"], vor.inputs["Vector"])
        sep = N.new("ShaderNodeSeparateColor")
        L.new(vor.outputs["Color"], sep.inputs[0])
        small = N.new("ShaderNodeMath")
        small.operation = "LESS_THAN"
        small.inputs[1].default_value = speckle.get("size", 0.22)
        L.new(vor.outputs["Distance"], small.inputs[0])
        keep = N.new("ShaderNodeMath")
        keep.operation = "GREATER_THAN"
        keep.inputs[1].default_value = 1.0 - speckle.get("density", 0.35)
        L.new(sep.outputs[0], keep.inputs[0])
        both = N.new("ShaderNodeMath")
        both.operation = "MULTIPLY"
        L.new(small.outputs[0], both.inputs[0])
        L.new(keep.outputs[0], both.inputs[1])
        fr = N.new("ShaderNodeValToRGB")
        _palette_ramp(fr, speckle["colors"])
        L.new(sep.outputs[1], fr.inputs[0])
        mix = N.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        a_in, b_in = _sock(mix.inputs, "A", "RGBA"), _sock(mix.inputs, "B", "RGBA")
        if cur is None:
            a_in.default_value = col(color)
        else:
            L.new(cur, a_in)
        L.new(fr.outputs[0], b_in)
        L.new(both.outputs[0], _sock(mix.inputs, "Factor", "VALUE"))
        cur = _sock(mix.outputs, "Result", "RGBA")
    if cur is None:
        bsdf.inputs["Base Color"].default_value = col(color)
    else:
        L.new(cur, bsdf.inputs["Base Color"])
    if bump:
        bt = N.new("ShaderNodeTexNoise")
        bt.inputs["Scale"].default_value = bump_scale
        bt.inputs["Detail"].default_value = 6.0
        L.new(tc.outputs["Object"], bt.inputs["Vector"])
        b = N.new("ShaderNodeBump")
        b.inputs["Strength"].default_value = bump
        _set(b, ["Distance"], 0.2)
        L.new(bt.outputs[0], b.inputs["Height"])
        L.new(b.outputs["Normal"], bsdf.inputs["Normal"])
    if emission:
        _set(bsdf, ["Emission Color", "Emission"], col(emission))
        _set(bsdf, ["Emission Strength"], strength)
    MATS[name] = m
    return m


def screen_material(name, colors, strength=1.6, axis="X"):
    """LED wall: emissive gradient (no imagery, no text)."""
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.new(name)
    if m.node_tree is None:
        m.use_nodes = True
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    bsdf = next(n for n in N if n.bl_idname == "ShaderNodeBsdfPrincipled")
    tc = N.new("ShaderNodeTexCoord")
    mp = N.new("ShaderNodeMapping")
    if axis == "Y":
        mp.inputs["Rotation"].default_value = (0, 0, math.pi / 2)
    L.new(tc.outputs["Generated"], mp.inputs["Vector"])
    g = N.new("ShaderNodeTexGradient")
    L.new(mp.outputs[0], g.inputs["Vector"])
    ramp = N.new("ShaderNodeValToRGB")
    e = ramp.color_ramp.elements
    e[0].color, e[1].color = col(colors[0]), col(colors[-1])
    if len(colors) > 2:
        mid = e.new(0.5)
        mid.color = col(colors[1])
    L.new(g.outputs[1], ramp.inputs[0])
    L.new(ramp.outputs[0], bsdf.inputs["Base Color"])
    _set(bsdf, ["Emission Strength"], strength)
    L.new(ramp.outputs[0], bsdf.inputs.get("Emission Color") or bsdf.inputs["Emission"])
    _set(bsdf, ["Roughness"], 0.25)
    m.diffuse_color = col(colors[0])
    MATS[name] = m
    return m


def build_materials():
    """Restrained palette: natural greens, warm sand, muted zone tints."""
    material("terrain_grass", "#5e8f43", rough=0.95, spec=0.2, noise=[
        dict(c2="#4f7f38", scale=0.012, lo=0.42, hi=0.66, amt=0.85),
        dict(c2="#73a050", scale=0.035, lo=0.5, hi=0.7, amt=0.5),
        dict(c2="#6a8c45", scale=0.25, lo=0.45, hi=0.75, amt=0.3, detail=2.0)])
    material("plinth_soil", "#5a4636", rough=0.9)
    material("backdrop", "#d9d5cc", rough=0.95, spec=0.1)
    material("sand_arena", "#dcc391", rough=0.95, noise=[
        dict(c2="#cfb27c", scale=0.03, lo=0.45, hi=0.7, amt=0.8),
        dict(c2="#ecdcb6", scale=0.11, lo=0.55, hi=0.75, amt=0.6)])
    material("path_dirt", "#d6bd8a", rough=0.95, noise=[
        dict(c2="#c9ac78", scale=0.06, lo=0.45, hi=0.7, amt=0.7)])
    material("service_gravel", "#b3ab9b", rough=0.95, noise=[
        dict(c2="#a9a192", scale=0.08, lo=0.45, hi=0.7, amt=0.7)])
    material("plaza_paving", "#d4c8b0", rough=0.85, noise=[
        dict(c2="#c6b89c", scale=0.05, lo=0.45, hi=0.7, amt=0.6)])
    material("asphalt_road", "#55595e", rough=0.85, noise=[
        dict(c2="#4b4f54", scale=0.05, lo=0.45, hi=0.7, amt=0.6)])
    material("asphalt_lot", "#84878a", rough=0.85, noise=[
        dict(c2="#7a7d80", scale=0.04, lo=0.45, hi=0.7, amt=0.6)])
    material("road_marking", "#eeeee8", rough=0.6)
    material("kerb", "#cfcbc2", rough=0.8)
    material("verge_grass", "#7aa451", rough=0.95)
    # camping zone tints - muted and clearly separable
    material("zone_general", "#a596bb", rough=0.95, noise=[
        dict(c2="#9889ae", scale=0.04, lo=0.45, hi=0.7, amt=0.7)])
    material("zone_priority", "#cbb26c", rough=0.95, noise=[
        dict(c2="#c8ab5c", scale=0.04, lo=0.45, hi=0.7, amt=0.7)])
    material("zone_wildflower", "#9dbd7c", rough=0.95, noise=[
        dict(c2="#8fb070", scale=0.03, lo=0.45, hi=0.7, amt=0.8)],
        speckle=dict(scale=1.1, size=0.2, density=0.32,
                     colors=["#f4f1e6", "#f4f1e6", "#e9c84a", "#b9a2cf"]))
    material("zone_glamping", "#cf9d90", rough=0.95, noise=[
        dict(c2="#c69384", scale=0.04, lo=0.45, hi=0.7, amt=0.7)])
    material("zone_clearing", "#7eaa58", rough=0.95, noise=[
        dict(c2="#73a050", scale=0.03, lo=0.45, hi=0.7, amt=0.7)])
    material("lawn", "#76a352", rough=0.95)
    # water
    material("water", "#2a6f98", rough=0.06, spec=0.6, attr="depth_col",
             bump=0.04, bump_scale=0.35)
    material("shore_mud", "#b9a37a", rough=0.95, noise=[
        dict(c2="#a38d66", scale=0.2, lo=0.4, hi=0.7, amt=0.7)])
    material("beach_sand", "#e6d6ac", rough=0.95)
    # vegetation
    material("bark", "#6a5040", rough=0.9)
    material("leaf", "#4b7a34", rough=0.85, spec=0.25, palette=[
        "#3e6b30", "#4b7a35", "#58873c", "#355f2b", "#64904a", "#46743a",
        "#507f33", "#3b6630"], noise=[
        dict(c2="#2d5224", scale=0.9, lo=0.35, hi=0.75, amt=0.45, blend="MULTIPLY")])
    material("leaf_dark", "#2f5a2c", rough=0.85, spec=0.25, palette=[
        "#2c5229", "#335d2e", "#284b26", "#3a6634"], noise=[
        dict(c2="#20401e", scale=0.9, lo=0.35, hi=0.75, amt=0.4, blend="MULTIPLY")])
    material("shrub", "#5d8c3e", rough=0.9, palette=[
        "#5d8c3e", "#6c9846", "#4f7f37", "#7a9f4e", "#58843f"])
    material("reed", "#8f9a5a", rough=0.9, palette=["#8f9a5a", "#a19d63", "#7d8a4f"])
    material("rock", "#a19c92", rough=0.9)
    material("flower_mound", "#86ac5c", rough=0.95, speckle=dict(
        scale=2.2, size=0.34, density=0.85,
        colors=["#f6f3ea", "#f6f3ea", "#ecc94b", "#c3a6d6", "#f6f3ea"]))
    # tents and canvas
    material("tent", "#7a8f6a", rough=0.7, spec=0.3, palette=[
        "#7b8f68", "#c9b58b", "#6c8ba3", "#b4664c", "#8b8b86", "#4f7f7a",
        "#d9d1bf", "#a9783f", "#5f6f8a", "#9c5f5f", "#e1dccd", "#6f7d4c"])
    material("tent_priority", "#7a8f6a", rough=0.7, spec=0.3, palette=[
        "#5d7186", "#d3c7a6", "#7e8f6b", "#a46c52", "#3f6f73", "#cfc8b6"])
    material("canvas", "#ece4d0", rough=0.75, spec=0.3)
    material("canvas_khaki", "#cdbf9c", rough=0.75, spec=0.3)
    material("gazebo", "#f0eee6", rough=0.6, palette=[
        "#f0eee6", "#efe9da", "#6f9aa0", "#c7714f", "#f0eee6", "#e2c770", "#8aa37a"])
    material("timber", "#a07850", rough=0.8, noise=[
        dict(c2="#8b6644", scale=0.6, lo=0.4, hi=0.7, amt=0.6)])
    material("timber_dark", "#6e5038", rough=0.8)
    # structures
    material("stage_black", "#2a2b2f", rough=0.6)
    material("stage_roof", "#4a4d53", rough=0.45, spec=0.4)
    material("stage_deck", "#3b3c40", rough=0.7)
    material("truss", "#c3c7cc", rough=0.3, metal=0.85)
    material("speaker", "#1d1e21", rough=0.55)
    material("fixture", "#18191b", rough=0.4)
    material("lamp_warm", "#ffe2b0", rough=0.3, emission="#ffd59a", strength=3.0)
    material("membrane_teal", "#4f8c8a", rough=0.55)
    material("membrane_white", "#efede6", rough=0.55)
    material("fabric_accent", "#e2c25a", rough=0.6)
    material("cabin_white", "#ecebe5", rough=0.6)
    material("roof_grey", "#9ba1a6", rough=0.55)
    material("medical_red", "#c0453b", rough=0.55)
    material("container", "#6d8a9c", rough=0.55, palette=[
        "#6d8a9c", "#9c6d5a", "#7d8b6a", "#8f8f8a", "#b59a62", "#5a6f80"])
    material("portaloo", "#4f6f80", rough=0.55, palette=["#4f6f80", "#5f7f5a", "#4c6475"])
    material("plastic_white", "#e7e6e1", rough=0.5)
    material("glass", "#2b3640", rough=0.12, spec=0.6)
    material("metal_dark", "#3a3d42", rough=0.45, metal=0.6)
    material("rubber", "#1b1b1c", rough=0.8)
    material("car_paint", "#cccccc", rough=0.35, spec=0.5, coat=0.3, palette=[
        "#dcdcd8", "#3a3d42", "#8c9298", "#6b2f2f", "#2f4b6e", "#c9c4b8",
        "#1f2023", "#7d8b6b", "#a8a59c", "#5d6d7e", "#efefea", "#9a4f35"])
    material("van_white", "#e9e8e3", rough=0.4, spec=0.5)
    material("bus_body", "#e8e4d8", rough=0.4, spec=0.5, palette=["#e8e4d8", "#5d8a8a"])
    material("hivis", "#e2b437", rough=0.5)
    material("bin_green", "#4f7a4a", rough=0.6)
    material("bin_blue", "#3f6f9a", rough=0.6)
    material("bin_grey", "#6a6c6e", rough=0.6)
    material("skip", "#c98a3a", rough=0.6, palette=["#c98a3a", "#5f7f5a", "#4f6f80"])
    material("water_tank", "#5f7f92", rough=0.5)
    material("fence", "#c9ccd0", rough=0.4, metal=0.5)
    material("fence_mesh", "#d4d6d8", rough=0.5, metal=0.3, alpha=0.3)   # see-through mesh panels
    material("hay", "#d6bf7a", rough=0.95)
    material("fire_stone", "#8d877d", rough=0.9)
    material("info_yellow", "#e0c055", rough=0.55)
    screen_material("screen_main", ["#2c6f86", "#7b5ea7", "#e7b65a"], strength=1.8)
    screen_material("screen_side", ["#2f7f8c", "#e1c062"], strength=1.6, axis="Y")


# =============================================================================
# 1. GEOMETRY HELPERS - a small mesh builder + 2D polyline/polygon tools
# =============================================================================

def xf(loc=(0, 0, 0), rz=0.0, rx=0.0, ry=0.0):
    return (Matrix.Translation(Vector(loc)) @ Matrix.Rotation(rz, 4, "Z")
            @ Matrix.Rotation(ry, 4, "Y") @ Matrix.Rotation(rx, 4, "X"))


class MB:
    """Accumulates primitives into one mesh with per-face material indices."""

    def __init__(self):
        self.v, self.f, self.m, self.sm = [], [], [], []

    def add(self, verts, faces, mat=0, smooth=False, M=None):
        o = len(self.v)
        if M is not None:
            verts = [M @ Vector(p) for p in verts]
        self.v.extend(tuple(p) for p in verts)
        for fc in faces:
            self.f.append(tuple(i + o for i in fc))
            self.m.append(mat)
            self.sm.append(smooth)
        return self

    # --- primitives (all bottom-centred, local frame then transformed) ---
    def box(self, sx, sy, sz, loc=(0, 0, 0), rz=0.0, mat=0, top=(1.0, 1.0), M=None, rx=0.0, ry=0.0):
        hx, hy = sx / 2, sy / 2
        tx, ty = hx * top[0], hy * top[1]
        vs = [(-hx, -hy, 0), (hx, -hy, 0), (hx, hy, 0), (-hx, hy, 0),
              (-tx, -ty, sz), (tx, -ty, sz), (tx, ty, sz), (-tx, ty, sz)]
        fs = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        T = (M or Matrix()) @ xf(loc, rz, rx, ry)
        return self.add(vs, fs, mat, False, T)

    def cyl(self, r, h, loc=(0, 0, 0), seg=16, mat=0, r2=None, cap_top=True,
            cap_bot=False, smooth=True, rz=0.0, rx=0.0, ry=0.0, M=None, sy=1.0):
        r2 = r if r2 is None else r2
        vs, fs = [], []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            vs.append((r * math.cos(a), r * math.sin(a) * sy, 0))
        apex = r2 <= 1e-6
        if apex:
            vs.append((0, 0, h))
            for i in range(seg):
                fs.append((i, (i + 1) % seg, seg))
        else:
            for i in range(seg):
                a = 2 * math.pi * i / seg
                vs.append((r2 * math.cos(a), r2 * math.sin(a) * sy, h))
            for i in range(seg):
                j = (i + 1) % seg
                fs.append((i, j, seg + j, seg + i))
        T = (M or Matrix()) @ xf(loc, rz, rx, ry)
        self.add(vs, fs, mat, smooth, T)
        o = len(self.v) - len(vs)
        if cap_top and not apex:
            self.f.append(tuple(o + seg + i for i in range(seg)))
            self.m.append(mat)
            self.sm.append(False)
        if cap_bot:
            self.f.append(tuple(o + i for i in reversed(range(seg))))
            self.m.append(mat)
            self.sm.append(False)
        return self

    def dome(self, rx, ry, h, loc=(0, 0, 0), seg=14, rings=5, mat=0, rz=0.0, M=None, smooth=True):
        vs, fs = [], []
        for k in range(rings):
            ph = (math.pi / 2) * k / rings
            s, z = math.cos(ph), h * math.sin(ph)
            for i in range(seg):
                a = 2 * math.pi * i / seg
                vs.append((rx * s * math.cos(a), ry * s * math.sin(a), z))
        vs.append((0, 0, h))
        top = len(vs) - 1
        for k in range(rings - 1):
            for i in range(seg):
                j = (i + 1) % seg
                fs.append((k * seg + i, k * seg + j, (k + 1) * seg + j, (k + 1) * seg + i))
        k = rings - 1
        for i in range(seg):
            fs.append((k * seg + i, k * seg + (i + 1) % seg, top))
        return self.add(vs, fs, mat, smooth, (M or Matrix()) @ xf(loc, rz))

    def blob(self, r, loc=(0, 0, 0), sub=2, scale=(1, 1, 1), amp=0.18, freq=1.3, seed=0.0, mat=0, M=None):
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0)
        vs = []
        for v in bm.verts:
            n = v.co.normalized()
            d = 1.0 + amp * mnoise.noise(n * freq + Vector((seed, seed * 1.7, seed * 0.3)))
            vs.append((n.x * r * d * scale[0], n.y * r * d * scale[1], n.z * r * d * scale[2]))
        fs = [tuple(v.index for v in f.verts) for f in bm.faces]
        bm.free()
        return self.add(vs, fs, mat, True, (M or Matrix()) @ xf(loc))

    def prism(self, w, l, h, loc=(0, 0, 0), rz=0.0, mat=0, M=None, ridge=1.0):
        """Triangular prism, ridge along local Y (gable roof / ridge tent)."""
        hw, hl = w / 2, l / 2
        rl = hl * ridge
        vs = [(-hw, -hl, 0), (hw, -hl, 0), (0, -rl, h), (-hw, hl, 0), (hw, hl, 0), (0, rl, h)]
        fs = [(0, 1, 2), (4, 3, 5), (1, 4, 5, 2), (3, 0, 2, 5), (0, 3, 4, 1)]
        return self.add(vs, fs, mat, False, (M or Matrix()) @ xf(loc, rz))

    def beam(self, p0, p1, w=0.1, mat=0, d=None):
        """Square-section bar between two points (trusses, poles, rails)."""
        p0, p1 = Vector(p0), Vector(p1)
        ax = p1 - p0
        if ax.length < 1e-6:
            return self
        ax_n = ax.normalized()
        up = Vector((0, 0, 1)) if abs(ax_n.z) < 0.95 else Vector((1, 0, 0))
        u = ax_n.cross(up).normalized() * (w / 2)
        v = ax_n.cross(u).normalized() * ((d or w) / 2)
        c = [p0 - u - v, p0 + u - v, p0 + u + v, p0 - u + v]
        vs = c + [q + ax for q in c]
        fs = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        return self.add(vs, fs, mat, False)

    def truss(self, p0, p1, size=0.5, chord=0.07, step=1.0, mat=0):
        """Four-chord box truss with zig-zag lacing on each face."""
        p0, p1 = Vector(p0), Vector(p1)
        ax = p1 - p0
        L = ax.length
        if L < 1e-6:
            return self
        a = ax.normalized()
        up = Vector((0, 0, 1)) if abs(a.z) < 0.95 else Vector((1, 0, 0))
        u = a.cross(up).normalized() * (size / 2)
        v = a.cross(u).normalized() * (size / 2)
        corners = [-u - v, u - v, u + v, -u + v]
        for c in corners:
            self.beam(p0 + c, p1 + c, chord, mat)
        n = max(1, int(L / step))
        for k in range(4):
            c0, c1 = corners[k], corners[(k + 1) % 4]
            for i in range(n):
                t0, t1 = i / n, (i + 1) / n
                a0 = p0 + ax * t0 + (c0 if i % 2 == 0 else c1)
                a1 = p0 + ax * t1 + (c1 if i % 2 == 0 else c0)
                self.beam(a0, a1, chord * 0.6, mat)
        return self

    def build(self, name, mats, bevel=0.0, bevel_angle=40.0):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, [], self.f)
        me.polygons.foreach_set("material_index", self.m)
        me.polygons.foreach_set("use_smooth", self.sm)
        for mt in mats:
            me.materials.append(mt)
        if bevel > 0:
            bevel_mesh(me, bevel, bevel_angle)
        me.update()
        return me


def bevel_mesh(me, width, angle=40.0):
    bm = bmesh.new()
    bm.from_mesh(me)
    lim = math.radians(angle)
    edges = [e for e in bm.edges if e.is_manifold and e.calc_face_angle(0.0) > lim]
    if edges:
        bmesh.ops.bevel(bm, geom=edges, offset=width, offset_type="OFFSET",
                        segments=1, profile=0.5, affect="EDGES", clamp_overlap=True)
    bm.to_mesh(me)
    bm.free()


_INST_COUNT = {}


def new_object(name, data, coll, loc=(0, 0, 0), rz=0.0, scale=None):
    ob = bpy.data.objects.new(name, data)
    ob.location = loc
    ob.rotation_euler = (0, 0, rz)
    if scale is not None:
        ob.scale = scale if hasattr(scale, "__len__") else (scale, scale, scale)
    coll.objects.link(ob)
    return ob


def place(mesh, coll, x, y, z=0.0, rz=0.0, s=1.0, sz=None):
    """Linked duplicate: a new object that shares `mesh` (instanced by Cycles)."""
    k = _INST_COUNT.get(mesh.name, 0)
    _INST_COUNT[mesh.name] = k + 1
    ob = bpy.data.objects.new(f"{mesh.name}.{k:04d}", mesh)
    ob.location = (x, y, z)
    ob.rotation_euler = (0, 0, rz)
    if s != 1.0 or sz is not None:
        ob.scale = (s, s, sz if sz is not None else s)
    coll.objects.link(ob)
    return ob


# ---- 2D tools ---------------------------------------------------------------

def chaikin(pts, iters=2, closed=True):
    P = [tuple(p) for p in pts]
    for _ in range(iters):
        Q = []
        n = len(P)
        rng = range(n) if closed else range(n - 1)
        if not closed:
            Q.append(P[0])
        for i in rng:
            a, b = P[i], P[(i + 1) % n]
            Q.append((0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]))
            Q.append((0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1]))
        if not closed:
            Q.append(P[-1])
        P = Q
    return P


def catmull(pts, step=2.0, closed=False):
    """Centripetal-ish Catmull-Rom spline sampled roughly every `step` metres."""
    P = [Vector((p[0], p[1])) for p in pts]
    if len(P) < 2:
        return [tuple(p) for p in P]
    if closed:
        ext = [P[-1]] + P + [P[0], P[1]]
    else:
        ext = [P[0] * 2 - P[1]] + P + [P[-1] * 2 - P[-2]]
    out = []
    nseg = len(P) if closed else len(P) - 1
    for i in range(nseg):
        p0, p1, p2, p3 = ext[i], ext[i + 1], ext[i + 2], ext[i + 3]
        n = max(2, int((p2 - p1).length / step))
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            q = 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                       + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)
            out.append((q.x, q.y))
    if not closed:
        out.append((P[-1].x, P[-1].y))
    return out


def resample(pts, step, closed=False):
    P = np.asarray(pts, dtype=float)
    if closed:
        P = np.vstack([P, P[:1]])
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    total = s[-1]
    n = max(2, int(total / step))
    t = np.linspace(0, total, n + (0 if closed else 1), endpoint=not closed)
    x = np.interp(t, s, P[:, 0])
    y = np.interp(t, s, P[:, 1])
    return list(zip(x, y)), total


def signed_area(poly):
    P = np.asarray(poly)
    x, y = P[:, 0], P[:, 1]
    return 0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)


def ccw(poly):
    return list(poly) if signed_area(poly) > 0 else list(reversed(poly))


def offset_poly(poly, d):
    """Offset a CCW closed polygon outward by d (miter, clamped)."""
    P = np.asarray(ccw(poly), dtype=float)
    prev, nxt = np.roll(P, 1, axis=0), np.roll(P, -1, axis=0)
    t1 = P - prev
    t2 = nxt - P
    t1 /= np.linalg.norm(t1, axis=1)[:, None] + 1e-9
    t2 /= np.linalg.norm(t2, axis=1)[:, None] + 1e-9
    n1 = np.stack([t1[:, 1], -t1[:, 0]], 1)
    n2 = np.stack([t2[:, 1], -t2[:, 0]], 1)
    nm = n1 + n2
    nm /= np.linalg.norm(nm, axis=1)[:, None] + 1e-9
    cosh = np.clip(np.sum(nm * n1, axis=1), 0.5, 1.0)
    return [tuple(p) for p in P + nm * (d / cosh)[:, None]]


def ellipse(cx, cy, rx, ry, n=160, a0=0.0, a1=2 * math.pi):
    closed = abs((a1 - a0) - 2 * math.pi) < 1e-6
    k = n if closed else n + 1
    return [(cx + rx * math.cos(a0 + (a1 - a0) * i / n), cy + ry * math.sin(a0 + (a1 - a0) * i / n))
            for i in range(k)]


def perturb(poly, amp, freq=0.02, seed=0.0):
    """Organic edge: push vertices along their normal using Perlin noise."""
    P = np.asarray(ccw(poly), dtype=float)
    prev, nxt = np.roll(P, 1, axis=0), np.roll(P, -1, axis=0)
    t = nxt - prev
    t /= np.linalg.norm(t, axis=1)[:, None] + 1e-9
    nrm = np.stack([t[:, 1], -t[:, 0]], 1)
    out = []
    for p, n in zip(P, nrm):
        d = amp * mnoise.noise(Vector((p[0] * freq, p[1] * freq, seed)))
        out.append((p[0] + n[0] * d, p[1] + n[1] * d))
    return out


def rounded_rect(x0, y0, x1, y1, r, n=6):
    pts = []
    for cx, cy, a0 in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def dist_to_polyline(px, py, poly, closed=True, chunk=40000):
    """Vectorised distance from many points to a polyline."""
    P = np.asarray(poly, dtype=float)
    A = P if closed else P[:-1]
    B = np.roll(P, -1, axis=0) if closed else P[1:]
    out = np.empty(px.shape[0])
    AB = B - A
    L2 = np.maximum(np.sum(AB * AB, axis=1), 1e-12)
    for s in range(0, px.shape[0], chunk):
        x = px[s:s + chunk, None]
        y = py[s:s + chunk, None]
        t = np.clip(((x - A[:, 0]) * AB[:, 0] + (y - A[:, 1]) * AB[:, 1]) / L2, 0, 1)
        dx = x - (A[:, 0] + t * AB[:, 0])
        dy = y - (A[:, 1] + t * AB[:, 1])
        out[s:s + chunk] = np.sqrt(np.min(dx * dx + dy * dy, axis=1))
    return out


def points_in_poly(px, py, poly):
    P = np.asarray(poly, dtype=float)
    inside = np.zeros(px.shape, dtype=bool)
    xj, yj = P[-1]
    for xi, yi in P:
        cond = ((yi > py) != (yj > py))
        with np.errstate(divide="ignore", invalid="ignore"):
            xint = (xj - xi) * (py - yi) / (yj - yi + 1e-12) + xi
        inside ^= cond & (px < xint)
        xj, yj = xi, yi
    return inside


def in_poly(x, y, poly):
    return bool(points_in_poly(np.array([x]), np.array([y]), poly)[0])


class Grid:
    """1 m occupancy grid over the site, used to keep things off paths etc."""

    def __init__(self, x0, y0, x1, y1, res=1.0):
        self.x0, self.y0, self.res = x0, y0, res
        self.nx, self.ny = int((x1 - x0) / res), int((y1 - y0) / res)
        xs = x0 + (np.arange(self.nx) + 0.5) * res
        ys = y0 + (np.arange(self.ny) + 0.5) * res
        self.X, self.Y = np.meshgrid(xs, ys)

    def empty(self):
        return np.zeros((self.ny, self.nx), dtype=bool)

    def _window(self, xmin, ymin, xmax, ymax):
        i0 = max(0, int((xmin - self.x0) / self.res) - 1)
        i1 = min(self.nx, int((xmax - self.x0) / self.res) + 2)
        j0 = max(0, int((ymin - self.y0) / self.res) - 1)
        j1 = min(self.ny, int((ymax - self.y0) / self.res) + 2)
        return j0, j1, i0, i1

    def poly(self, mask, poly):
        P = np.asarray(poly)
        j0, j1, i0, i1 = self._window(P[:, 0].min(), P[:, 1].min(), P[:, 0].max(), P[:, 1].max())
        if j1 <= j0 or i1 <= i0:
            return
        X, Y = self.X[j0:j1, i0:i1], self.Y[j0:j1, i0:i1]
        mask[j0:j1, i0:i1] |= points_in_poly(X.ravel(), Y.ravel(), poly).reshape(X.shape)

    def line(self, mask, pts, width, closed=False):
        """Stamp a disc stencil along the resampled polyline (vectorised)."""
        r = width / 2
        P, _ = resample(pts, max(0.4, min(1.0, r / 2)), closed)
        P = np.asarray(P)
        k = int(math.ceil(r / self.res))
        di, dj = np.meshgrid(np.arange(-k, k + 1), np.arange(-k, k + 1))
        sel = (di ** 2 + dj ** 2) * self.res ** 2 <= r * r + 0.25
        di, dj = di[sel], dj[sel]
        I = ((P[:, 0] - self.x0) / self.res).astype(int)[:, None] + di[None, :]
        J = ((P[:, 1] - self.y0) / self.res).astype(int)[:, None] + dj[None, :]
        ok = (I >= 0) & (I < self.nx) & (J >= 0) & (J < self.ny)
        mask[J[ok], I[ok]] = True

    def circle(self, mask, x, y, r):
        j0, j1, i0, i1 = self._window(x - r, y - r, x + r, y + r)
        X, Y = self.X[j0:j1, i0:i1], self.Y[j0:j1, i0:i1]
        mask[j0:j1, i0:i1] |= (X - x) ** 2 + (Y - y) ** 2 <= r * r

    def rect(self, mask, x, y, sx, sy, rz=0.0, pad=0.0):
        c, s = math.cos(rz), math.sin(rz)
        hx, hy = sx / 2 + pad, sy / 2 + pad
        R = math.hypot(hx, hy)
        j0, j1, i0, i1 = self._window(x - R, y - R, x + R, y + R)
        X, Y = self.X[j0:j1, i0:i1] - x, self.Y[j0:j1, i0:i1] - y
        lx, ly = X * c + Y * s, -X * s + Y * c
        mask[j0:j1, i0:i1] |= (np.abs(lx) <= hx) & (np.abs(ly) <= hy)

    def hit(self, mask, x, y, r=0.0):
        pts = [(x, y)]
        if r > 0:
            pts += [(x + r * math.cos(a), y + r * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 8, endpoint=False)]
        for px, py in pts:
            i = int((px - self.x0) / self.res)
            j = int((py - self.y0) / self.res)
            if i < 0 or j < 0 or i >= self.nx or j >= self.ny:
                return True
            if mask[j, i]:
                return True
        return False


class SpatialHash:
    """Minimum-distance checks for scattered items (trees, tents)."""

    def __init__(self, cell=8.0):
        self.cell, self.d = cell, {}

    def ok(self, x, y, r, factor=1.0):
        ci, cj = int(x // self.cell), int(y // self.cell)
        for i in range(ci - 2, ci + 3):
            for j in range(cj - 2, cj + 3):
                for (qx, qy, qr) in self.d.get((i, j), ()):
                    if (qx - x) ** 2 + (qy - y) ** 2 < ((r + qr) * factor) ** 2:
                        return False
        return True

    def add(self, x, y, r):
        self.d.setdefault((int(x // self.cell), int(y // self.cell)), []).append((x, y, r))


# ---- mesh builders for ground layers -----------------------------------------

def slab(name, poly, z_top, z_bot, mat, coll, bevel=0.0):
    """Extruded polygon (zones, plazas, parking). Top face is an n-gon."""
    poly = ccw(poly)
    n = len(poly)
    vs = [(x, y, z_top) for x, y in poly] + [(x, y, z_bot) for x, y in poly]
    fs = [tuple(range(n))]
    for i in range(n):
        j = (i + 1) % n
        fs.append((n + i, n + j, j, i))
    me = bpy.data.meshes.new(name)
    me.from_pydata(vs, [], fs)
    me.materials.append(mat)
    me.update()
    ob = new_object(name, me, coll)
    if bevel > 0:
        md = ob.modifiers.new("Bevel", "BEVEL")
        md.width = bevel
        md.segments = 2
        md.limit_method = "ANGLE"
    return ob


def ribbon(mb, pts, width, z_top, z_bot, mat=0, closed=False, caps=True):
    """Raised strip along a polyline (paths, roads), with rounded end caps."""
    P = np.asarray(pts, dtype=float)
    n = len(P)
    if n < 2:
        return
    if closed:
        T = np.roll(P, -1, axis=0) - np.roll(P, 1, axis=0)
    else:
        T = np.empty_like(P)
        T[1:-1] = P[2:] - P[:-2]
        T[0] = P[1] - P[0]
        T[-1] = P[-1] - P[-2]
    T /= np.linalg.norm(T, axis=1)[:, None] + 1e-9
    Nn = np.stack([-T[:, 1], T[:, 0]], 1)
    Lp = P + Nn * width / 2
    Rp = P - Nn * width / 2
    vs = ([(x, y, z_top) for x, y in Lp] + [(x, y, z_top) for x, y in Rp]
          + [(x, y, z_bot) for x, y in Lp] + [(x, y, z_bot) for x, y in Rp])
    LT, RT, LB, RB = 0, n, 2 * n, 3 * n
    fs = []
    m = n if closed else n - 1
    for i in range(m):
        j = (i + 1) % n
        fs.append((LT + i, RT + i, RT + j, LT + j))
        fs.append((LB + i, LT + i, LT + j, LB + j))
        fs.append((RB + j, RT + j, RT + i, RB + i))
    mb.add(vs, fs, mat)
    if caps and not closed:
        for end, sign in ((0, -1.0), (n - 1, 1.0)):
            c = P[end]
            t = T[end] * sign
            nn = Nn[end]
            arc = []
            for k in range(9):
                ph = math.pi * k / 8
                # from left edge, around the end, to the right edge
                d = nn * math.cos(ph) + t * math.sin(ph)
                arc.append((c[0] + d[0] * width / 2, c[1] + d[1] * width / 2))
            cv = [(c[0], c[1], z_top)] + [(x, y, z_top) for x, y in arc] + [(x, y, z_bot) for x, y in arc]
            cf = []
            for k in range(8):
                tri = (0, 1 + k, 2 + k)
                a = np.array(arc[k]) - c
                b = np.array(arc[k + 1]) - c
                if a[0] * b[1] - a[1] * b[0] < 0:
                    tri = (0, 2 + k, 1 + k)
                cf.append(tri)
                cf.append((10 + k, 1 + k, 2 + k, 11 + k))
            mb.add(cv, cf, mat)


# =============================================================================
# 2. SITE LAYOUT (metres). Everything below derives from these numbers.
# =============================================================================

X0, X1, Y0, Y1 = -500.0, 500.0, -330.0, 330.0
PLINTH = 10.0
Z = dict(zone=0.12, arena=0.16, service=0.24, path=0.28, glamp_path=0.3,
         lot=0.3, plaza=0.32, road=0.34, mark=0.36)

ARENA_C = (0.0, 10.0)
ARENA_R = (200.0, 130.0)
RING_R = (216.0, 146.0)


def arena_pt(deg, rx=ARENA_R[0], ry=ARENA_R[1]):
    a = math.radians(deg)
    return (ARENA_C[0] + rx * math.cos(a), ARENA_C[1] + ry * math.sin(a))


def ring_pt(deg):
    return arena_pt(deg, *RING_R)


def road_y(x):
    return -293.0 + 5.0 * math.cos(x / 330.0)


ROAD_W = 10.0
ROAD_PTS = [(x, road_y(x)) for x in np.linspace(X0, X1, 101)]

LOT_A = (-390.0, -262.0, -168.0, -188.0)      # x0, y0, x1, y1
LOT_B = (-130.0, -262.0, 80.0, -188.0)
STAFF_LOT = (-445.0, -168.0, -368.0, -100.0)
SHUTTLE_C, SHUTTLE_R = (150.0, -226.0), 20.0
ENTRANCE_X = -10.0
PLAZA = rounded_rect(-78.0, -186.0, 58.0, -121.0, 8.0)
PRIORITY_GATE = (212.0, -58.0)
COMPOUND = (-440.0, -78.0, -345.0, -22.0)
WASTE_DEPOT = (-292.0, -50.0, -252.0, -20.0)

LAKE = [(70, 262), (110, 278), (175, 282), (235, 276), (278, 262), (296, 238),
        (288, 208), (266, 186), (234, 172), (198, 174), (165, 186), (128, 198),
        (96, 214), (74, 236)]

ZONE_GENERAL = [(-300, 186), (-292, 245), (-262, 282), (-205, 298), (-120, 302),
                (-40, 300), (8, 286), (26, 252), (24, 212), (6, 186), (-40, 176),
                (-120, 174), (-200, 172), (-262, 174)]
ZONE_WILDFLOWER = [(-446, 22), (-448, 80), (-425, 125), (-385, 152), (-330, 162),
                   (-275, 158), (-246, 140), (-238, 100), (-244, 55), (-262, 24),
                   (-320, 16), (-400, 14)]
ZONE_PRIORITY = [(250, 100), (300, 112), (380, 114), (448, 108), (466, 80), (466, 0),
                 (458, -30), (420, -40), (320, -40), (268, -34), (248, -10), (242, 50)]
GLAMP = (242.0, -252.0, 468.0, -62.0)
ZONE_GLAMPING = rounded_rect(*GLAMP, 14.0)
CLEARING_C, CLEARING_R = (390.0, 200.0), (76.0, 60.0)

# Pedestrian paths: (name, control points, width)
PATHS = [
    ("gen_west", [ring_pt(135), (-165, 150), (-178, 178), (-172, 230), (-160, 300), (-150, 314)], 6.0),
    ("gen_east", [ring_pt(105), (-62, 170), (-60, 230), (-52, 300), (-48, 315)], 6.0),
    ("gen_cross", [(-292, 232), (-230, 236), (-170, 232), (-110, 238), (-60, 232), (0, 240), (30, 236), (58, 232)], 5.0),
    ("wild_main", [ring_pt(165), (-238, 58), (-275, 78), (-322, 92), (-375, 86), (-420, 70), (-472, 62)], 6.0),
    ("wild_north", [(-322, 92), (-338, 128), (-322, 158), (-302, 180), (-294, 210), (-292, 232)], 4.5),
    ("wild_south", [(-318, -178), (-322, -120), (-326, -60), (-322, -2), (-305, 30), (-300, 60), (-322, 92)], 5.0),
    ("lot_link", [(-385, -178), (-300, -178), (-200, -176), (-120, -174), (-70, -170)], 5.5),
    ("arena_sw", [ring_pt(-135), (-185, -120), (-225, -150), (-262, -172), (-280, -178)], 5.0),
    ("shuttle_link", [(150, -204), (118, -186), (80, -174), (50, -166)], 6.0),
    ("lake_link", [ring_pt(70), (80, 165), (88, 185), (96, 200)], 6.0),
    ("prio_link", [ring_pt(10), (235, 40), (262, 45)], 6.0),
    ("prio_main", [(262, 45), (300, 40), (350, 46), (400, 40), (440, 42), (486, 40)], 5.0),
    ("prio_ns", [(350, -48), (348, 0), (350, 46), (352, 90), (350, 125), (358, 136)], 4.5),
    ("prio_gate_n", [PRIORITY_GATE, (226, -46), (248, -38), (272, -28)], 6.0),
    ("prio_gate_arena", [PRIORITY_GATE, (188, -74), ring_pt(-45)], 6.0),
    ("prio_gate_glamp", [PRIORITY_GATE, (232, -70), (252, -78)], 5.0),
    ("entrance_spine", [(ENTRANCE_X, -186), (ENTRANCE_X, -118)], 10.0),
]
LAKE_LOOP_OFFSET = 14.0
CLEARING_LOOP_R = (92.0, 74.0)

# Gravel service / emergency network (vehicle capable)
SERVICE = [
    ("service_road", [(-450, -292), (-455, -230), (-456, -120), (-455, -40), (-448, -12),
                      (-425, -3), (-370, -2), (-300, 0), (-250, 3), (-205, 8)], 7.0),
    ("arena_service", [(-202, 8), (-188, 48), (-160, 84), (-115, 112), (-62, 124), (-30, 126)], 6.0),
    ("perimeter_track", [(-455, -5), (-472, 60), (-472, 180), (-450, 262), (-395, 305), (-300, 314),
                         (-150, 316), (0, 316), (150, 314), (300, 314), (410, 306), (470, 270),
                         (484, 180), (486, 40), (485, -100), (482, -220), (478, -268), (470, -290)], 6.0),
    ("compound_spur", [(-395, -22), (-395, -4)], 7.0),
    ("staff_spur", [(-455, -134), (-445, -134)], 7.0),
    ("depot_spur", [(-272, -20), (-272, 0)], 6.0),
]

# Asphalt spurs from the public road
SPURS = [
    ("lot_a_drive", [(-279, road_y(-279)), (-279, -262)], 9.0),
    ("lot_b_drive", [(-60, road_y(-60)), (-60, -262)], 9.0),
    ("shuttle_spur", [(150, road_y(150)), (150, -244)], 9.0),
    ("priority_lane", [(210, road_y(210)), (211, -200), (212, -120), (212, -86)], 7.0),
]

GLAMP_PATHS = [
    ("glamp_ns", [(355, -64), (355, -250)], 4.0),
    ("glamp_ew", [(244, -155), (466, -155)], 4.0),
]
GLAMP_LOOP = rounded_rect(GLAMP[0] + 10, GLAMP[1] + 10, GLAMP[2] - 10, GLAMP[3] - 10, 10.0)

ARENA_GATES = [(-90, 8.0), (-135, 3.0), (-45, 3.0), (10, 3.0), (70, 3.0), (105, 3.0),
               (135, 3.0), (165, 3.0), (180, 4.0)]


# =============================================================================
# 3. PLANNING - smooth shapes + occupancy masks shared by all build stages
# =============================================================================

class Plan:
    pass


def mesh_from_np(name, verts, quads):
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(verts))
    me.vertices.foreach_set("co", np.ascontiguousarray(verts, dtype=np.float32).ravel())
    me.loops.add(quads.size)
    me.loops.foreach_set("vertex_index", np.ascontiguousarray(quads, dtype=np.int32).ravel())
    me.polygons.add(len(quads))
    me.polygons.foreach_set("loop_start", np.arange(0, quads.size, 4, dtype=np.int32))
    me.update(calc_edges=True)
    return me


def smooth_path(pts, closed=False):
    return catmull(pts, step=2.0, closed=closed)


def make_plan(seed):
    log("planning layout and occupancy masks")
    P = Plan()
    P.rng = random.Random(seed)
    P.seed = seed
    lake = chaikin(LAKE, 3)
    lake = perturb(lake, 3.0, freq=0.045, seed=seed * 0.001 + 0.3)
    lake = chaikin(lake, 1)
    P.lake, _ = resample(lake, 2.0, closed=True)
    P.lake = ccw(P.lake)
    P.arena = perturb(ellipse(*ARENA_C, *ARENA_R, n=260), 2.2, freq=0.04, seed=1.7)
    P.zones = {
        "general": chaikin(perturb(chaikin(ZONE_GENERAL, 2), 2.0, 0.05, 2.1), 2),
        "wildflower": chaikin(perturb(chaikin(ZONE_WILDFLOWER, 2), 2.5, 0.05, 3.3), 2),
        "priority": chaikin(perturb(chaikin(ZONE_PRIORITY, 2), 1.5, 0.05, 4.4), 2),
        "glamping": ZONE_GLAMPING,
        "clearing": perturb(ellipse(*CLEARING_C, *CLEARING_R, n=120), 2.0, 0.05, 5.5),
    }
    # path centrelines (smoothed)
    P.paths = [(n, smooth_path(p), w) for n, p, w in PATHS]
    P.paths.append(("arena_ring", ellipse(*ARENA_C, *RING_R, n=240), 7.0, ))
    P.paths.append(("lake_loop", resample(offset_poly(P.lake, LAKE_LOOP_OFFSET), 2.0, True)[0], 4.5))
    P.paths.append(("clearing_loop", ellipse(*CLEARING_C, *CLEARING_LOOP_R, n=140), 4.5))
    P.closed = {"arena_ring", "lake_loop", "clearing_loop"}
    P.service = [(n, smooth_path(p), w) for n, p, w in SERVICE]
    P.spurs = [(n, smooth_path(p), w) for n, p, w in SPURS]
    P.glamp_paths = [(n, p, w) for n, p, w in GLAMP_PATHS] + [("glamp_loop", GLAMP_LOOP, 4.0)]

    g = Grid(X0, Y0, X1, Y1, 1.0)
    P.g = g
    paths = g.empty()
    for n, pts, w in P.paths + P.service + P.spurs + P.glamp_paths:
        g.line(paths, pts, w + 3.0, closed=(n in P.closed or n == "glamp_loop"))
    g.line(paths, ROAD_PTS, ROAD_W + 10.0)
    P.m_paths = paths
    hard = g.empty()
    for lot in (LOT_A, LOT_B, STAFF_LOT):
        g.poly(hard, rounded_rect(lot[0] - 3, lot[1] - 3, lot[2] + 3, lot[3] + 3, 6))
    g.poly(hard, offset_poly(PLAZA, 3))
    g.poly(hard, rounded_rect(COMPOUND[0] - 3, COMPOUND[1] - 3, COMPOUND[2] + 3, COMPOUND[3] + 3, 4))
    g.poly(hard, rounded_rect(WASTE_DEPOT[0] - 3, WASTE_DEPOT[1] - 3, WASTE_DEPOT[2] + 3, WASTE_DEPOT[3] + 3, 4))
    g.circle(hard, *SHUTTLE_C, SHUTTLE_R + 12)
    g.rect(hard, PRIORITY_GATE[0], PRIORITY_GATE[1] - 18, 34, 30)
    P.m_hard = hard
    water = g.empty()
    g.poly(water, offset_poly(P.lake, 8.0))
    P.m_water = water
    arena = g.empty()
    g.poly(arena, ellipse(*ARENA_C, ARENA_R[0] + 4, ARENA_R[1] + 4, n=120))
    P.m_arena = arena
    P.m_zone = {}
    for k, poly in P.zones.items():
        m = g.empty()
        g.poly(m, poly)
        P.m_zone[k] = m
    P.m_struct = g.empty()     # facility footprints, filled while planning
    P.m_trees = g.empty()      # tree trunks/canopies, for tent avoidance
    return P


# =============================================================================
# 4. STAGE 1 - TERRAIN AND SITE BOUNDARY
# =============================================================================

def build_terrain(P):
    log("stage 1: terrain plinth")
    coll = C("Terrain")
    res = 2.0
    nx, ny = int((X1 - X0) / res), int((Y1 - Y0) / res)
    xs, ys = np.linspace(X0, X1, nx + 1), np.linspace(Y0, Y1, ny + 1)
    VX, VY = np.meshgrid(xs, ys)
    verts = np.stack([VX.ravel(), VY.ravel(), np.zeros(VX.size)], 1)
    CX, CY = np.meshgrid((xs[:-1] + xs[1:]) / 2, (ys[:-1] + ys[1:]) / 2)
    hole = points_in_poly(CX.ravel(), CY.ravel(), offset_poly(P.lake, 4.5)).reshape(CX.shape)
    j, i = np.nonzero(~hole)
    v00 = j * (nx + 1) + i
    quads = np.stack([v00, v00 + 1, v00 + nx + 2, v00 + nx + 1], 1)
    me = mesh_from_np("Terrain_Grass", verts, quads)
    me.materials.append(MATS["terrain_grass"])
    new_object("Terrain_Grass", me, coll)
    # model plinth: four walls + base (open top so the lake basin can show)
    mb = MB()
    z0, z1 = -PLINTH, -0.001
    c = [(X0, Y0), (X1, Y0), (X1, Y1), (X0, Y1)]
    vs = [(x, y, z0) for x, y in c] + [(x, y, z1) for x, y in c]
    mb.add(vs, [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (0, 3, 2, 1)])
    new_object("Terrain_Plinth", mb.build("Terrain_Plinth", [MATS["plinth_soil"]], bevel=0.5), coll)
    # neutral display base the model sits on
    mb = MB().box(1800, 1300, 0.2, loc=(0, 0, -PLINTH - 0.2))
    new_object("Display_Base", mb.build("Display_Base", [MATS["backdrop"]]), coll)


# =============================================================================
# 5. STAGE 2 - DAM, ROADS AND WALKING PATHS
# =============================================================================

def build_lake(P):
    log("stage 2: dam / lake")
    coll = C("Lake")
    L = P.lake
    mid = offset_poly(L, 2.0)
    outer = offset_poly(L, 7.0)
    n = len(L)
    mb = MB()
    vs = [(x, y, -0.65) for x, y in L] + [(x, y, 0.05) for x, y in mid] + [(x, y, 0.05) for x, y in outer]
    fs_mud, fs_grass = [], []
    for i in range(n):
        j = (i + 1) % n
        fs_mud.append((i, j, n + j, n + i))
        fs_grass.append((n + i, n + j, 2 * n + j, 2 * n + i))
    mb.add(vs, fs_mud, 0)
    mb.f.extend(tuple(x + 0 for x in f) for f in fs_grass)
    mb.m.extend([1] * n)
    mb.sm.extend([False] * n)
    new_object("Lake_Shore", mb.build("Lake_Shore", [MATS["shore_mud"], MATS["terrain_grass"]]), coll)
    # water surface: 1 m grid whose ragged edge hides under the shore slope
    Pz = np.asarray(L)
    xs = np.arange(Pz[:, 0].min() - 4, Pz[:, 0].max() + 5, 1.0)
    ys = np.arange(Pz[:, 1].min() - 4, Pz[:, 1].max() + 5, 1.0)
    VX, VY = np.meshgrid(xs, ys)
    CX, CY = VX[:-1, :-1] + 0.5, VY[:-1, :-1] + 0.5
    inside = points_in_poly(CX.ravel(), CY.ravel(), offset_poly(L, 1.8)).reshape(CX.shape)
    j, i = np.nonzero(inside)
    W = len(xs)
    v00 = j * W + i
    quads = np.stack([v00, v00 + 1, v00 + W + 1, v00 + W], 1)
    used = np.unique(quads)
    remap = -np.ones(VX.size, dtype=np.int64)
    remap[used] = np.arange(len(used))
    verts = np.stack([VX.ravel()[used], VY.ravel()[used], np.full(len(used), -0.3)], 1)
    me = mesh_from_np("Lake_Water", verts, remap[quads])
    d = dist_to_polyline(verts[:, 0], verts[:, 1], L, closed=True)
    ins = points_in_poly(verts[:, 0], verts[:, 1], L)
    d = np.where(ins, d, 0.0)
    t = np.clip(d / 60.0, 0, 1) ** 0.75
    shallow, deep, edge = np.array(col("#5c9fb2")), np.array(col("#2f6f98")), np.array(col("#86b6b4"))
    cols = shallow[None, :] * (1 - t[:, None]) + deep[None, :] * t[:, None]
    e = np.clip(1 - d / 2.5, 0, 1)[:, None]
    cols = cols * (1 - e) + edge[None, :] * e
    cols[:, 3] = 1.0
    ca = me.color_attributes.new("depth_col", "FLOAT_COLOR", "POINT")
    ca.data.foreach_set("color", cols.astype(np.float32).ravel())
    me.materials.append(MATS["water"])
    new_object("Lake_Water", me, coll)


def build_roads_paths(P):
    log("stage 2: roads, service routes and walking paths")
    coll = C("Roads and Paths")
    # public access road + gravel shoulders + markings
    mb = MB()
    ribbon(mb, ROAD_PTS, ROAD_W, Z["road"], -0.2, 0, caps=False)
    new_object("Access_Road", mb.build("Access_Road", [MATS["asphalt_road"]]), coll)
    mb = MB()
    ribbon(mb, ROAD_PTS, ROAD_W + 3.0, Z["road"] - 0.06, -0.2, 0, caps=False)
    new_object("Access_Road_Shoulders", mb.build("Access_Road_Shoulders", [MATS["service_gravel"]]), coll)
    pts, _ = resample(ROAD_PTS, 0.5)
    pts = np.asarray(pts)
    T = np.gradient(pts, axis=0)
    T /= np.linalg.norm(T, axis=1)[:, None]
    Nn = np.stack([-T[:, 1], T[:, 0]], 1)
    mb = MB()
    for side in (-1, 1):
        ribbon(mb, pts + Nn * side * (ROAD_W / 2 - 0.5), 0.2, Z["mark"], Z["road"] - 0.01, 0, caps=False)
    s = 0.0
    seg = []
    for k in range(1, len(pts)):
        s += 0.5
        if (s % 9.0) < 3.0:
            seg.append(pts[k])
        elif seg:
            if len(seg) > 1:
                ribbon(mb, seg, 0.22, Z["mark"], Z["road"] - 0.01, 0, caps=False)
            seg = []
    new_object("Access_Road_Markings", mb.build("Access_Road_Markings", [MATS["road_marking"]]), coll)
    # asphalt spurs (parking drives, shuttle spur, priority lane)
    mb = MB()
    for i, (n, pts2, w) in enumerate(P.spurs):
        ribbon(mb, pts2, w, Z["road"] - 0.005 * (i + 1), -0.2, 0, caps=False)
    new_object("Access_Spurs", mb.build("Access_Spurs", [MATS["asphalt_road"]]), coll)
    # gravel service / emergency network
    mb = MB()
    for i, (n, pts2, w) in enumerate(P.service):
        z = Z["arena"] + 0.08 if n == "arena_service" else Z["service"]
        ribbon(mb, pts2, w, z + 0.002 * i, -0.1, 0)
    new_object("Service_Emergency_Routes", mb.build("Service_Emergency_Routes", [MATS["service_gravel"]], bevel=0.12), coll)
    # pedestrian path network (one mesh, tiny z offsets avoid coplanar overlaps)
    mb = MB()
    for i, (n, pts2, w) in enumerate(P.paths):
        ribbon(mb, pts2, w, Z["path"] + 0.002 * i, -0.1, 0, closed=(n in P.closed))
    new_object("Walking_Paths", mb.build("Walking_Paths", [MATS["path_dirt"]], bevel=0.15), coll)
    mb = MB()
    for i, (n, pts2, w) in enumerate(P.glamp_paths):
        ribbon(mb, pts2, w, Z["glamp_path"] + 0.002 * i, -0.1, 0, closed=(n == "glamp_loop"))
    new_object("Glamping_Paths", mb.build("Glamping_Paths", [MATS["path_dirt"]], bevel=0.12), C("Glamping Village"))


# =============================================================================
# 6. STAGE 3 / 4 - ARENA GROUND, CAMPING GROUNDS, HARD STANDINGS
# =============================================================================

def build_grounds(P):
    log("stage 3/4: arena and camping grounds")
    slab("Arena_Sand", P.arena, Z["arena"], -0.2, MATS["sand_arena"], C("Main Arena"), bevel=0.3)
    zc = {"general": ("Camping General", "zone_general"),
          "wildflower": ("Camping Wildflower", "zone_wildflower"),
          "priority": ("Camping Priority", "zone_priority"),
          "glamping": ("Glamping Village", "zone_glamping"),
          "clearing": ("Trees and Vegetation", "zone_clearing")}
    for k, poly in P.zones.items():
        cname, mname = zc[k]
        slab(f"Ground_{k.title()}", poly, Z["zone"], -0.2, MATS[mname], C(cname), bevel=0.15)
    # hard standings: entrance plaza, compound yards, waste depot
    slab("Entrance_Plaza", PLAZA, Z["plaza"], -0.2, MATS["plaza_paving"], C("Entrances"), bevel=0.15)
    slab("Production_Medical_Yard", rounded_rect(*COMPOUND, 4), Z["service"], -0.2,
         MATS["service_gravel"], C("Facilities"), bevel=0.12)
    slab("Waste_Recycling_Depot_Yard", rounded_rect(*WASTE_DEPOT, 3), Z["service"], -0.2,
         MATS["service_gravel"], C("Facilities"), bevel=0.12)
    # priority drop-off apron in front of the priority gate
    slab("Priority_DropOff", rounded_rect(PRIORITY_GATE[0] - 15, PRIORITY_GATE[1] - 32,
                                          PRIORITY_GATE[0] + 15, PRIORITY_GATE[1] - 12, 6),
         Z["lot"], -0.2, MATS["asphalt_lot"], C("Entrances"), bevel=0.1)


def build_parking_ground(P):
    log("stage 5: parking surfaces")
    coll = C("Parking")
    for name, lot in (("Parking_A", LOT_A), ("Parking_B", LOT_B), ("Staff_Parking", STAFF_LOT)):
        slab(name, rounded_rect(*lot, 6), Z["lot"], -0.2, MATS["asphalt_lot"], coll, bevel=0.12)
        slab(name + "_Kerb", rounded_rect(lot[0] - 1.2, lot[1] - 1.2, lot[2] + 1.2, lot[3] + 1.2, 7),
             Z["lot"] - 0.02, -0.2, MATS["kerb"], coll)
    # shuttle drop-off and turning circle
    mb = MB()
    ribbon(mb, ellipse(*SHUTTLE_C, SHUTTLE_R, SHUTTLE_R, n=72), 10.0, Z["road"], -0.2, 0, closed=True)
    new_object("Shuttle_Turning_Loop", mb.build("Shuttle_Turning_Loop", [MATS["asphalt_road"]]), coll)
    slab("Shuttle_Island", ellipse(*SHUTTLE_C, SHUTTLE_R - 5.4, SHUTTLE_R - 5.4, n=48),
         Z["road"] + 0.15, -0.2, MATS["lawn"], coll, bevel=0.1)
    slab("Shuttle_Island_Kerb", ellipse(*SHUTTLE_C, SHUTTLE_R - 4.8, SHUTTLE_R - 4.8, n=48),
         Z["road"] + 0.1, -0.2, MATS["kerb"], coll)
    # shuttle passenger platform on the north side of the loop
    cx, cy = SHUTTLE_C
    slab("Shuttle_Platform", rounded_rect(cx - 22, cy + 25.5, cx + 14, cy + 31, 2),
         Z["plaza"], -0.2, MATS["plaza_paving"], coll, bevel=0.1)


# =============================================================================
# 9. LIGHTING, CAMERA AND RENDER SETTINGS
# =============================================================================

def build_lighting_camera():
    log("stage 8: lighting, world and cameras")
    coll = C("Lighting and Camera")
    sc = bpy.context.scene
    # soft late-morning sun from the north-west (top-left of the map)
    sun_d = bpy.data.lights.new("Sun", "SUN")
    sun_d.energy = 4.2
    sun_d.angle = math.radians(3.0)
    sun_d.color = (1.0, 0.97, 0.92)
    sun = new_object("Sun", sun_d, coll)
    d = Vector((0.5, -0.56, -0.6)).normalized()
    sun.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    # world: soft sky fill for ambient occlusion-like contact shading
    w = bpy.data.worlds.new("Sky")
    sc.world = w
    if w.node_tree is None:
        w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.bl_idname == "ShaderNodeBackground")
    bg.inputs["Color"].default_value = col("#c9dbe8")
    bg.inputs["Strength"].default_value = 0.9
    # cameras
    cam_d = bpy.data.cameras.new("Camera_Top")
    cam_d.type = "ORTHO"
    cam_d.ortho_scale = 1075.0
    cam_d.clip_start, cam_d.clip_end = 1.0, 3000.0
    top = new_object("Camera_Top", cam_d, coll, loc=(0, -2.0, 900.0))
    cam2 = bpy.data.cameras.new("Camera_Oblique")
    cam2.type = "ORTHO"
    cam2.ortho_scale = 1030.0
    cam2.clip_start, cam2.clip_end = 1.0, 4000.0
    obl = new_object("Camera_Oblique", cam2, coll)
    tilt = math.radians(50.0)
    dist = 1500.0
    obl.location = (0, -dist * math.sin(tilt) - 6.0, dist * math.cos(tilt))
    obl.rotation_euler = (tilt, 0, 0)
    sc.camera = top
    return top, obl


def setup_render(samples, res_x, res_y):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    cy = sc.cycles
    cy.device = "CPU"
    cy.samples = samples
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.03
    cy.use_denoising = True
    try:
        cy.denoiser = "OPENIMAGEDENOISE"
    except Exception:
        pass
    cy.max_bounces = 4
    cy.diffuse_bounces = 2
    cy.glossy_bounces = 2
    cy.transmission_bounces = 2
    cy.transparent_max_bounces = 4
    cy.caustics_reflective = False
    cy.caustics_refractive = False
    sc.render.resolution_x = res_x
    sc.render.resolution_y = res_y
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    sc.render.image_settings.compression = 40
    # Khronos PBR Neutral keeps the restrained palette's hues (Blender 4.2+)
    for vt in ("Khronos PBR Neutral", "AgX", "Filmic"):
        try:
            sc.view_settings.view_transform = vt
            break
        except TypeError:
            continue
    sc.view_settings.look = "None"
    sc.view_settings.exposure = -0.7
    sc.render.film_transparent = False


def render_view(cam, path, res_x, res_y):
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = res_x, res_y
    sc.render.filepath = path
    log(f"rendering {os.path.basename(path)} at {res_x}x{res_y}")
    t = time.time()
    bpy.ops.render.render(write_still=True)
    log(f"  done in {time.time() - t:.0f}s -> {path}")


# =============================================================================
# 7. REUSABLE ASSETS - each is one mesh, placed many times as linked duplicates
# =============================================================================

def _mi(mb, name):
    """Material index by name inside a builder (adds the slot on first use)."""
    if not hasattr(mb, "names"):
        mb.names = []
    if name not in mb.names:
        mb.names.append(name)
    return mb.names.index(name)


def _done(mb, name, bevel=0.0, angle=40.0):
    return mb.build(name, [MATS[n] for n in mb.names], bevel=bevel, bevel_angle=angle)


A = {}


def asset_tree(name, seed, clumps=3, h=8.0, cr=3.6, flat=0.82, leaf="leaf", spread=0.42, trunk=0.28):
    rnd = random.Random(seed)
    mb = MB()
    mb.cyl(trunk, h * 0.6, seg=7, mat=_mi(mb, "bark"), r2=trunk * 0.6)
    for i in range(clumps):
        a = rnd.uniform(0, 2 * math.pi)
        rr = 0.0 if i == 0 else cr * spread * rnd.uniform(0.55, 1.0)
        r = cr * (0.78 if i == 0 else rnd.uniform(0.55, 0.72))
        z = h * 0.66 + (0 if i == 0 else rnd.uniform(-0.6, 0.9))
        mb.blob(r, (rr * math.cos(a), rr * math.sin(a), z), sub=3, scale=(1, 1, flat),
                amp=0.17, freq=1.5, seed=seed * 3.1 + i, mat=_mi(mb, leaf))
    return _done(mb, name)


def asset_conifer(name, seed, h=11.0, r=2.6):
    mb = MB()
    mb.cyl(0.25, h * 0.3, seg=6, mat=_mi(mb, "bark"))
    for k, (zf, rf) in enumerate(((0.18, 1.0), (0.42, 0.78), (0.64, 0.55))):
        mb.cyl(r * rf, h * 0.42, (0, 0, h * zf), seg=10, r2=0.0, mat=_mi(mb, "leaf_dark"), cap_top=False, cap_bot=True)
    return _done(mb, name)


def asset_umbrella(name, seed):
    """Flat-topped acacia-like tree - a nod to the Western Cape setting."""
    rnd = random.Random(seed)
    mb = MB()
    b = _mi(mb, "bark")
    mb.cyl(0.3, 4.8, seg=7, mat=b, r2=0.2)
    for a in (0.3, 2.4, 4.4):
        mb.beam((0, 0, 4.0), (1.8 * math.cos(a), 1.8 * math.sin(a), 6.0), 0.22, b)
    lf = _mi(mb, "leaf")
    for i in range(5):
        a = i * 1.3 + rnd.uniform(0, 0.4)
        rr = 0 if i == 0 else 2.2
        mb.blob(2.6 if i == 0 else 2.1, (rr * math.cos(a), rr * math.sin(a), 6.2), sub=3,
                scale=(1, 1, 0.42), amp=0.15, seed=seed + i, mat=lf)
    return _done(mb, name)


def asset_shrub(name, seed, n=3, r=1.0):
    rnd = random.Random(seed)
    mb = MB()
    m = _mi(mb, "shrub")
    for i in range(n):
        a = rnd.uniform(0, 6.28)
        rr = 0 if i == 0 else r * 0.6
        mb.blob(r * rnd.uniform(0.7, 1.0), (rr * math.cos(a), rr * math.sin(a), r * 0.45), sub=2,
                scale=(1, 1, 0.75), amp=0.2, seed=seed + i * 2.3, mat=m)
    return _done(mb, name)


def asset_reeds(name, seed):
    rnd = random.Random(seed)
    mb = MB()
    m = _mi(mb, "reed")
    mb.blob(1.0, (0, 0, 0.2), sub=2, scale=(1.2, 0.9, 0.45), amp=0.25, seed=seed, mat=m)
    for i in range(14):
        a, rr = rnd.uniform(0, 6.28), rnd.uniform(0, 0.9)
        mb.cyl(0.07, rnd.uniform(1.2, 2.0), (rr * math.cos(a), rr * math.sin(a), 0.1), seg=4, r2=0.0, mat=m,
               rx=rnd.uniform(-0.15, 0.15), ry=rnd.uniform(-0.15, 0.15))
    return _done(mb, name)


def asset_rock(name, seed):
    mb = MB()
    mb.blob(1.0, (0, 0, 0.15), sub=1, scale=(1.3, 1.0, 0.6), amp=0.3, freq=0.9, seed=seed, mat=_mi(mb, "rock"))
    return _done(mb, name)


def asset_flower_mound(name, seed):
    mb = MB()
    mb.blob(2.2, (0, 0, -0.25), sub=3, scale=(1.0, 0.8, 0.28), amp=0.2, seed=seed, mat=_mi(mb, "flower_mound"))
    return _done(mb, name)


# ---- tents -------------------------------------------------------------------

def asset_tent_dome(name, mat="tent"):
    mb = MB()
    m = _mi(mb, mat)
    mb.dome(1.5, 1.3, 1.25, seg=12, rings=4, mat=m)
    mb.dome(0.75, 0.8, 0.85, (0, -1.05, 0), seg=10, rings=3, mat=m)
    return _done(mb, name)


def asset_tent_tunnel(name, mat="tent"):
    mb = MB()
    mb.dome(1.25, 2.3, 1.25, seg=14, rings=4, mat=_mi(mb, mat))
    return _done(mb, name)


def asset_tent_ridge(name, mat="tent"):
    mb = MB()
    m = _mi(mb, mat)
    mb.prism(2.3, 3.0, 1.5, mat=m)
    mb.prism(1.6, 0.9, 1.1, (0, -1.9, 0), mat=m, ridge=0.2)
    return _done(mb, name, bevel=0.03)


def asset_tent_family(name, mat="tent"):
    mb = MB()
    m = _mi(mb, mat)
    mb.box(3.8, 3.4, 1.05, mat=m)
    mb.prism(4.0, 3.6, 1.0, (0, 0, 1.05), mat=m, rz=math.pi / 2)
    mb.box(3.4, 1.6, 0.06, (0, -2.4, 1.35), rx=-0.25, mat=m)
    for sx in (-1.6, 1.6):
        mb.beam((sx, -3.1, 0), (sx, -3.1, 1.15), 0.05, _mi(mb, "metal_dark"))
    return _done(mb, name, bevel=0.03)


def asset_gazebo(name, size=3.0, mat="gazebo", legs=2.2):
    mb = MB()
    m = _mi(mb, mat)
    s2 = size / 2 - 0.05
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.beam((sx * s2, sy * s2, 0), (sx * s2, sy * s2, legs), 0.06, _mi(mb, "fence"))
    mb.box(size, size, 0.22, (0, 0, legs - 0.2), mat=m)
    mb.box(size, size, size * 0.3, (0, 0, legs), mat=m, top=(0.06, 0.06))
    return _done(mb, name, bevel=0.02)


def asset_bell_tent(name):
    mb = MB()
    c = _mi(mb, "canvas")
    mb.cyl(2.6, 0.85, seg=20, mat=c, cap_top=False)
    mb.cyl(2.78, 2.35, (0, 0, 0.85), seg=20, r2=0.06, mat=c)
    mb.box(1.0, 0.3, 1.3, (0, -2.55, 0), mat=_mi(mb, "canvas_khaki"), top=(0.4, 1.0))
    mb.cyl(0.05, 0.45, (0, 0, 3.1), seg=6, mat=_mi(mb, "timber_dark"))
    return _done(mb, name)


def asset_safari_tent(name):
    mb = MB()
    t, k = _mi(mb, "timber"), _mi(mb, "canvas_khaki")
    mb.box(6.4, 7.6, 0.45, (0, -0.6, 0), mat=t)
    mb.box(4.6, 4.8, 1.9, (0, 0.6, 0.45), mat=k)
    mb.prism(5.4, 6.6, 1.35, (0, -0.3, 2.3), mat=k)
    for sx in (-2.5, 2.5):
        mb.beam((sx, -3.6, 0.45), (sx, -3.6, 2.35), 0.1, _mi(mb, "timber_dark"))
    mb.box(1.6, 0.8, 0.45, (-1.2, -2.6, 0.45), mat=_mi(mb, "timber_dark"))
    return _done(mb, name, bevel=0.03)


def asset_prepitched(name):
    mb = MB()
    c = _mi(mb, "canvas")
    mb.box(3.4, 3.0, 1.0, mat=c)
    mb.prism(3.6, 3.2, 1.05, (0, 0, 1.0), mat=c, rz=math.pi / 2)
    mb.box(1.2, 0.08, 1.4, (0, -1.54, 0), mat=_mi(mb, "canvas_khaki"))
    return _done(mb, name, bevel=0.03)


def stretch_tent(mb, sx, sy, poles, z0=0.0, mat="membrane_white", edge_h=2.4, sigma=3.0, ox=0.0, oy=0.0):
    """Organic stretch-tent fabric: a superellipse grid lifted by internal poles."""
    m = _mi(mb, mat)
    nx, ny = int(sx / 0.6), int(sy / 0.6)
    a, b = sx / 2, sy / 2
    idx = {}
    vs = []
    for j in range(ny + 1):
        for i in range(nx + 1):
            x, y = -a + sx * i / nx, -b + sy * j / ny
            e = (abs(x / a) ** 3 + abs(y / b) ** 3)
            if e > 1.02:
                continue
            h = edge_h - 1.2 * e ** 3
            for px, py, ph in poles:
                h += ph * math.exp(-((x - px) ** 2 + (y - py) ** 2) / (sigma * sigma))
            idx[(i, j)] = len(vs)
            vs.append((ox + x, oy + y, z0 + h))
    fs = []
    for j in range(ny):
        for i in range(nx):
            q = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
            if all(k in idx for k in q):
                fs.append(tuple(idx[k] for k in q))
    mb.add(vs, fs, m, smooth=True)
    for px, py, ph in poles:
        mb.cyl(0.12, edge_h + ph, (ox + px, oy + py, z0), seg=6, mat=_mi(mb, "fence"))


def asset_stretch_bar(name):
    mb = MB()
    stretch_tent(mb, 22, 15, [(-5.0, 0, 3.8), (5.0, 0, 3.8)], sigma=2.4)
    w = _mi(mb, "timber_dark")
    mb.box(12, 1.0, 1.1, (0, -3.0, 0), mat=w)
    mb.box(12, 1.0, 1.1, (0, 3.0, 0), mat=w)
    mb.box(1.0, 5.0, 1.1, (-5.5, 0, 0), mat=w)
    mb.box(1.0, 5.0, 1.1, (5.5, 0, 0), mat=w)
    mb.box(2.4, 2.4, 2.6, (0, 0, 0), mat=_mi(mb, "container"))
    return _done(mb, name)


def asset_stretch_lounge(name):
    mb = MB()
    stretch_tent(mb, 16, 11, [(-3, 0, 2.8), (3, 0, 2.8)], mat="canvas")
    t = _mi(mb, "timber")
    mb.box(13, 8, 0.25, mat=t)
    h = _mi(mb, "hay")
    for k in range(6):
        a = k / 6 * 2 * math.pi
        mb.box(1.2, 0.6, 0.5, (3.6 * math.cos(a), 2.4 * math.sin(a), 0.25), rz=a, mat=h)
    return _done(mb, name)


# ---- food, bars, seating ---------------------------------------------------------

def asset_stall(name):
    mb = MB()
    g = _mi(mb, "gazebo")
    s2 = 1.45
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.beam((sx * s2, sy * s2, 0), (sx * s2, sy * s2, 2.2), 0.06, _mi(mb, "fence"))
    mb.box(3.0, 3.0, 0.22, (0, 0, 2.0), mat=g)
    mb.box(3.0, 3.0, 0.9, (0, 0, 2.2), mat=g, top=(0.06, 0.06))
    mb.box(2.8, 0.6, 1.0, (0, -1.15, 0), mat=_mi(mb, "timber"))
    mb.box(2.6, 0.7, 0.9, (0, 1.0, 0), mat=_mi(mb, "plastic_white"))
    return _done(mb, name, bevel=0.02)


def asset_food_truck(name):
    mb = MB()
    p = _mi(mb, "truck_paint")
    _wheels(mb, (-1.9, 1.9), 1.1, r=0.42, w=0.28)
    mb.box(5.4, 2.4, 2.5, (-0.6, 0, 0.55), mat=p)
    mb.box(1.8, 2.3, 1.9, (3.0, 0, 0.55), mat=p, top=(0.85, 1.0))
    mb.box(0.08, 2.0, 0.8, (3.86, 0, 1.55), mat=_mi(mb, "glass"))
    mb.box(3.4, 0.08, 1.0, (-0.8, -1.22, 1.4), mat=_mi(mb, "glass"))
    mb.box(3.6, 1.1, 0.06, (-0.8, -1.7, 2.5), rx=0.35, mat=p)
    mb.box(5.5, 2.45, 0.08, (-0.6, 0, 3.05), mat=_mi(mb, "plastic_white"))
    return _done(mb, name, bevel=0.04)


def asset_picnic(name):
    mb = MB()
    t = _mi(mb, "timber")
    mb.box(2.0, 0.8, 0.06, (0, 0, 0.72), mat=t)
    for y in (-0.7, 0.7):
        mb.box(2.0, 0.3, 0.05, (0, y, 0.44), mat=t)
    for x in (-0.8, 0.8):
        mb.beam((x, -0.75, 0), (x, 0.0, 0.74), 0.06, t)
        mb.beam((x, 0.75, 0), (x, 0.0, 0.74), 0.06, t)
    return _done(mb, name)


def asset_hay_bale(name):
    mb = MB()
    mb.cyl(0.65, 1.2, (-0.6, 0, 0.65), seg=14, ry=math.pi / 2, mat=_mi(mb, "hay"), cap_bot=True)
    return _done(mb, name)


# ---- facilities ----------------------------------------------------------------

def asset_toilet_block(name, n=6):
    mb = MB()
    c, w = _mi(mb, "portaloo"), _mi(mb, "plastic_white")
    for row in (-1, 1):
        for i in range(n):
            x = (i - (n - 1) / 2) * 1.3
            y = row * 0.66
            mb.box(1.22, 1.22, 2.2, (x, y, 0), mat=c)
            mb.box(1.26, 1.26, 0.14, (x, y, 2.2), mat=w, top=(0.85, 0.85))
            mb.cyl(0.05, 0.4, (x + 0.35, y, 2.3), seg=6, mat=w)
    return _done(mb, name, bevel=0.03)


def asset_shower_block(name):
    mb = MB()
    c = _mi(mb, "container")
    mb.box(6.06, 2.44, 2.6, (0, -2.4, 0), mat=c)
    mb.box(6.06, 2.44, 2.6, (0, 2.4, 0), mat=c)
    mb.box(6.4, 2.4, 0.2, (0, 0, 0), mat=_mi(mb, "timber"))
    mb.box(7.0, 7.8, 0.14, (0, 0, 2.85), mat=_mi(mb, "roof_grey"))
    for sx in (-3.2, 3.2):
        mb.beam((sx, -1.1, 0.2), (sx, -1.1, 2.85), 0.1, _mi(mb, "metal_dark"))
        mb.beam((sx, 1.1, 0.2), (sx, 1.1, 2.85), 0.1, _mi(mb, "metal_dark"))
    mb.cyl(0.9, 1.4, (1.8, 2.4, 2.99), seg=14, mat=_mi(mb, "water_tank"))
    return _done(mb, name, bevel=0.04)


def asset_water_point(name):
    mb = MB()
    t, m = _mi(mb, "water_tank"), _mi(mb, "metal_dark")
    for sx in (-0.55, 0.55):
        for sy in (-0.55, 0.55):
            mb.beam((sx, sy + 0.8, 0), (sx, sy + 0.8, 0.8), 0.08, m)
    mb.cyl(0.85, 1.6, (0, 0.8, 0.8), seg=16, mat=t)
    mb.box(2.6, 0.6, 0.85, (0, -0.6, 0), mat=_mi(mb, "plastic_white"))
    for x in (-0.9, -0.3, 0.3, 0.9):
        mb.beam((x, -0.6, 0.85), (x, -0.6, 1.2), 0.05, m)
    return _done(mb, name, bevel=0.02)


def asset_info_kiosk(name):
    mb = MB()
    w, y = _mi(mb, "cabin_white"), _mi(mb, "info_yellow")
    mb.cyl(2.0, 2.5, seg=6, mat=w, smooth=False)
    mb.cyl(2.04, 0.7, (0, 0, 1.2), seg=6, mat=_mi(mb, "glass"), smooth=False, cap_top=False)
    mb.cyl(2.75, 1.5, (0, 0, 2.5), seg=6, r2=0.0, mat=y, smooth=False, cap_bot=True)
    mb.box(3.4, 2.4, 2.4, (2.9, 0, 0), mat=w)
    mb.box(3.7, 2.7, 0.16, (2.9, 0, 2.4), mat=y)
    return _done(mb, name, bevel=0.03)


def asset_bins(name):
    mb = MB()
    for i, m in enumerate(("bin_green", "bin_blue", "bin_grey")):
        k = _mi(mb, m)
        x = (i - 1) * 0.72
        mb.box(0.6, 0.72, 1.0, (x, 0, 0), mat=k, top=(1.05, 1.05))
        mb.box(0.64, 0.78, 0.06, (x, 0, 1.0), mat=k)
    mb.box(2.4, 0.08, 1.2, (0, 0.5, 0), mat=_mi(mb, "timber"))
    return _done(mb, name, bevel=0.02)


def asset_skip(name):
    mb = MB()
    mb.box(4.0, 1.8, 1.5, mat=_mi(mb, "skip"), top=(1.18, 1.1))
    mb.box(4.4, 1.85, 0.05, (0, 0, 1.46), mat=_mi(mb, "metal_dark"))
    return _done(mb, name, bevel=0.03)


def asset_container(name, length=6.06):
    mb = MB()
    c = _mi(mb, "container")
    mb.box(length, 2.44, 2.59, mat=c)
    d = _mi(mb, "metal_dark")
    for x in (-length / 2 + 0.02, length / 2 - 0.02):
        mb.box(0.06, 2.2, 2.3, (x, 0, 0.12), mat=d)
    return _done(mb, name, bevel=0.04)


def asset_portacabin(name, roof="roof_grey"):
    mb = MB()
    w = _mi(mb, "cabin_white")
    mb.box(9.6, 3.0, 2.6, (0, 0, 0.2), mat=w)
    mb.box(9.9, 3.3, 0.16, (0, 0, 2.8), mat=_mi(mb, roof))
    g = _mi(mb, "glass")
    for x in (-3.2, 0.0, 3.2):
        mb.box(1.6, 3.06, 0.8, (x, 0, 1.3), mat=g)
    mb.box(1.0, 0.8, 0.2, (-4.0, -1.9, 0.0), mat=_mi(mb, "metal_dark"))
    return _done(mb, name, bevel=0.03)


def asset_generator(name):
    mb = MB()
    mb.box(4.2, 1.7, 2.1, (0, 0, 0.2), mat=_mi(mb, "container"))
    mb.box(4.4, 1.9, 0.2, mat=_mi(mb, "metal_dark"))
    mb.cyl(0.12, 0.8, (1.4, 0.3, 2.3), seg=8, mat=_mi(mb, "metal_dark"))
    mb.cyl(0.6, 2.0, (-4.3, 0, 0.62), seg=12, ry=math.pi / 2, mat=_mi(mb, "plastic_white"), cap_bot=True)
    return _done(mb, name, bevel=0.03)


def asset_light_tower(name):
    mb = MB()
    mb.box(2.6, 1.5, 1.1, (0, 0, 0.25), mat=_mi(mb, "hivis"))
    m = _mi(mb, "metal_dark")
    mb.beam((0, 0, 1.3), (0, 0, 9.5), 0.22, m)
    mb.box(2.4, 0.35, 0.45, (0, 0, 9.4), mat=m)
    lw = _mi(mb, "lamp_warm")
    for x in (-0.9, -0.3, 0.3, 0.9):
        mb.box(0.5, 0.18, 0.5, (x, -0.24, 9.4), mat=lw, rx=-0.3)
    return _done(mb, name, bevel=0.02)


def asset_lantern(name):
    mb = MB()
    mb.cyl(0.06, 2.6, seg=6, mat=_mi(mb, "metal_dark"))
    mb.blob(0.22, (0, 0, 2.75), sub=1, amp=0.0, mat=_mi(mb, "lamp_warm"))
    return _done(mb, name)


def asset_fire_pit(name):
    mb = MB()
    s = _mi(mb, "fire_stone")
    for k in range(9):
        a = k / 9 * 2 * math.pi
        mb.blob(0.28, (1.1 * math.cos(a), 1.1 * math.sin(a), 0.05), sub=1, amp=0.2, seed=k, mat=s)
    mb.cyl(0.9, 0.08, seg=12, mat=_mi(mb, "metal_dark"))
    t = _mi(mb, "hay")
    for k in range(6):
        a = k / 6 * 2 * math.pi + 0.3
        mb.box(1.2, 0.35, 0.42, (3.0 * math.cos(a), 3.0 * math.sin(a), 0), rz=a + math.pi / 2, mat=t)
    return _done(mb, name)


def asset_ticket_booth(name):
    mb = MB()
    mb.box(2.6, 2.4, 2.5, mat=_mi(mb, "cabin_white"))
    mb.box(1.8, 0.06, 0.9, (0, -1.22, 1.1), mat=_mi(mb, "glass"))
    mb.box(3.2, 3.4, 0.14, (0, -0.4, 2.5), mat=_mi(mb, "info_yellow"))
    return _done(mb, name, bevel=0.03)


def asset_bus_shelter(name):
    mb = MB()
    m = _mi(mb, "metal_dark")
    for x in (-2.8, 0, 2.8):
        mb.beam((x, 0.6, 0), (x, 0.6, 2.5), 0.1, m)
    mb.box(6.2, 2.0, 0.12, (0, 0.1, 2.5), mat=_mi(mb, "info_yellow"), rx=0.05)
    mb.box(6.0, 0.06, 1.8, (0, 0.62, 0.4), mat=_mi(mb, "glass"))
    mb.box(4.0, 0.45, 0.45, (0, 0.3, 0), mat=_mi(mb, "timber"))
    return _done(mb, name, bevel=0.02)


# ---- vehicles -------------------------------------------------------------------

def _wheels(mb, xs, half_track, r=0.33, w=0.24):
    k = _mi(mb, "rubber")
    for x in xs:
        for side in (-1, 1):
            # cylinder axis is rotated onto -Y, so it extends from y toward -y by w
            y = half_track if side > 0 else -half_track + w
            mb.cyl(r, w, (x, y, r), seg=10, rx=math.pi / 2, mat=k, cap_bot=True)


def asset_car(name):
    mb = MB()
    p = _mi(mb, "car_paint")
    _wheels(mb, (-1.35, 1.35), 0.8)
    mb.box(4.3, 1.78, 0.72, (0, 0, 0.3), mat=p)
    mb.box(2.5, 1.62, 0.58, (-0.2, 0, 1.02), mat=_mi(mb, "glass"), top=(0.72, 0.86))
    mb.box(1.6, 1.36, 0.06, (-0.25, 0, 1.58), mat=p)
    return _done(mb, name, bevel=0.06)


def asset_van(name, body="van_white"):
    mb = MB()
    p = _mi(mb, body)
    _wheels(mb, (-1.6, 1.7), 0.85, r=0.36)
    mb.box(5.1, 1.95, 1.9, (-0.2, 0, 0.35), mat=p)
    mb.box(0.9, 1.9, 1.2, (2.75, 0, 0.35), mat=p, top=(0.6, 1.0))
    mb.box(0.05, 1.7, 0.6, (2.42, 0, 1.75), mat=_mi(mb, "glass"))
    return _done(mb, name, bevel=0.06)


def asset_ambulance(name):
    mb = MB()
    p = _mi(mb, "van_white")
    _wheels(mb, (-1.6, 1.7), 0.85, r=0.36)
    mb.box(5.1, 1.95, 2.1, (-0.2, 0, 0.35), mat=p)
    mb.box(0.9, 1.9, 1.3, (2.75, 0, 0.35), mat=p, top=(0.6, 1.0))
    mb.box(5.14, 1.99, 0.3, (-0.2, 0, 1.0), mat=_mi(mb, "hivis"))
    mb.box(1.2, 0.5, 0.16, (1.6, 0, 2.45), mat=_mi(mb, "medical_red"))
    return _done(mb, name, bevel=0.06)


def asset_bus(name):
    mb = MB()
    p = _mi(mb, "bus_body")
    _wheels(mb, (-3.8, 3.6), 1.15, r=0.5, w=0.3)
    mb.box(12.0, 2.55, 2.9, (0, 0, 0.4), mat=p)
    mb.box(11.6, 2.6, 0.95, (0.1, 0, 1.75), mat=_mi(mb, "glass"))
    mb.box(11.0, 2.2, 0.16, (0, 0, 3.3), mat=_mi(mb, "plastic_white"))
    return _done(mb, name, bevel=0.08)


def asset_truck(name):
    mb = MB()
    _wheels(mb, (-5.5, -4.2, 3.0, 6.6), 1.1, r=0.5, w=0.3)
    mb.box(13.6, 2.55, 3.4, (-0.6, 0, 1.1), mat=_mi(mb, "plastic_white"))
    mb.box(2.4, 2.5, 2.8, (7.4, 0, 0.6), mat=_mi(mb, "container"), top=(0.9, 1.0))
    mb.box(0.05, 2.2, 0.9, (8.62, 0, 2.0), mat=_mi(mb, "glass"))
    return _done(mb, name, bevel=0.06)


def build_assets():
    log("building reusable asset library")
    material("truck_paint", "#d9c9a3", rough=0.45, palette=["#d9c9a3", "#8fb3ae", "#c98f7a", "#e2d6c0", "#7f9fb8", "#a7b98a"])
    A["tree_a"] = asset_tree("Tree_Round_A", 1, clumps=3, h=8.0, cr=3.6)
    A["tree_b"] = asset_tree("Tree_Round_B", 2, clumps=5, h=9.0, cr=4.0, spread=0.5)
    A["tree_c"] = asset_tree("Tree_Round_C", 3, clumps=2, h=10.0, cr=3.2, flat=0.95)
    A["tree_d"] = asset_tree("Tree_Broad_D", 4, clumps=4, h=7.5, cr=3.8, flat=0.7, spread=0.55)
    A["umbrella"] = asset_umbrella("Tree_Umbrella", 5)
    A["conifer"] = asset_conifer("Tree_Conifer", 6)
    A["poplar"] = asset_tree("Tree_Poplar", 7, clumps=2, h=12.0, cr=2.2, flat=1.9, spread=0.2, trunk=0.2)
    A["shrub_a"] = asset_shrub("Shrub_A", 11, 3, 1.0)
    A["shrub_b"] = asset_shrub("Shrub_B", 12, 4, 1.2)
    A["reeds"] = asset_reeds("Reed_Clump", 21)
    A["rock"] = asset_rock("Rock", 31)
    A["flowers"] = asset_flower_mound("Wildflower_Mound", 41)
    A["dome"] = asset_tent_dome("Tent_Dome")
    A["tunnel"] = asset_tent_tunnel("Tent_Tunnel")
    A["ridge"] = asset_tent_ridge("Tent_Ridge")
    A["family"] = asset_tent_family("Tent_Family")
    A["dome_p"] = asset_tent_dome("Tent_Dome_Priority", "tent_priority")
    A["tunnel_p"] = asset_tent_tunnel("Tent_Tunnel_Priority", "tent_priority")
    A["family_p"] = asset_tent_family("Tent_Family_Priority", "tent_priority")
    A["gazebo"] = asset_gazebo("Gazebo_3m")
    A["gazebo_white"] = asset_gazebo("Gazebo_6m_White", 6.0, "membrane_white", 2.5)
    A["bell"] = asset_bell_tent("Glamping_Bell_Tent")
    A["safari"] = asset_safari_tent("Glamping_Safari_Tent")
    A["prepitched"] = asset_prepitched("PrePitched_Tent")
    A["bar"] = asset_stretch_bar("Bar_Stretch_Tent")
    A["lounge"] = asset_stretch_lounge("Lounge_Stretch_Tent")
    A["stall"] = asset_stall("Food_Stall")
    A["food_truck"] = asset_food_truck("Food_Truck")
    A["picnic"] = asset_picnic("Picnic_Table")
    A["hay"] = asset_hay_bale("Hay_Bale")
    A["toilets"] = asset_toilet_block("Toilet_Block", 6)
    A["toilets_s"] = asset_toilet_block("Toilet_Block_Small", 3)
    A["showers"] = asset_shower_block("Shower_Block")
    A["water"] = asset_water_point("Water_Point")
    A["info"] = asset_info_kiosk("Info_LostProperty_Kiosk")
    A["bins"] = asset_bins("Waste_Recycling_Bins")
    A["skip"] = asset_skip("Recycling_Skip")
    A["container"] = asset_container("Container_6m")
    A["container12"] = asset_container("Container_12m", 12.19)
    A["cabin"] = asset_portacabin("Portacabin")
    A["medical"] = asset_portacabin("Medical_Cabin", roof="medical_red")
    A["generator"] = asset_generator("Generator")
    A["light_tower"] = asset_light_tower("Lighting_Tower")
    A["lantern"] = asset_lantern("Lantern_Post")
    A["fire_pit"] = asset_fire_pit("Fire_Pit_Circle")
    A["booth"] = asset_ticket_booth("Ticket_Booth")
    A["shelter"] = asset_bus_shelter("Bus_Shelter")
    A["car"] = asset_car("Car")
    A["van"] = asset_van("Van")
    A["ambulance"] = asset_ambulance("Ambulance")
    A["bus"] = asset_bus("Shuttle_Bus")
    A["truck"] = asset_truck("Production_Truck")
    # one visible-in-file reference object per asset in a library collection
    lib = C(ASSET_COLL)
    for k, me in A.items():
        new_object("ASSET_" + me.name, me, lib)
    lc = bpy.context.view_layer.layer_collection.children.get(ASSET_COLL)
    if lc:
        lc.exclude = True


# =============================================================================
# 8. PLACEMENT HELPERS
# =============================================================================

def ground_z(P, x, y):
    """Top of whatever ground layer is at (x, y)."""
    g = P.g
    i, j = int((x - g.x0) / g.res), int((y - g.y0) / g.res)
    if not (0 <= i < g.nx and 0 <= j < g.ny):
        return 0.0
    if in_poly(x, y, PLAZA):
        return Z["plaza"]
    for lot in (LOT_A, LOT_B, STAFF_LOT):
        if lot[0] <= x <= lot[2] and lot[1] <= y <= lot[3]:
            return Z["lot"]
    for r in (COMPOUND, WASTE_DEPOT):
        if r[0] <= x <= r[2] and r[1] <= y <= r[3]:
            return Z["service"]
    if (x - ARENA_C[0]) ** 2 / ARENA_R[0] ** 2 + (y - ARENA_C[1]) ** 2 / ARENA_R[1] ** 2 <= 1.0:
        return Z["arena"]
    for k, m in P.m_zone.items():
        if m[j, i]:
            return Z["zone"]
    return 0.0


def free_spot(P, x, y, r, masks, step=2.0, tries=60):
    """Spiral search for the nearest spot clear of all `masks` within radius r."""
    g = P.g
    for k in range(tries):
        if k == 0:
            cx, cy = x, y
        else:
            a = k * 2.399963
            d = step * math.sqrt(k)
            cx, cy = x + d * math.cos(a), y + d * math.sin(a)
        if not any(g.hit(m, cx, cy, r) for m in masks):
            return cx, cy
    return None


def path_angle_near(P, x, y):
    """Tangent angle of the closest path segment (to align buildings)."""
    pts, ang = P.path_pts, P.path_ang
    k = int(np.argmin((pts[:, 0] - x) ** 2 + (pts[:, 1] - y) ** 2))
    return float(ang[k])


def index_paths(P):
    pts, ang = [], []
    for n, pl, w in P.paths + P.service + P.glamp_paths:
        A_ = np.asarray(pl)
        if len(A_) < 2:
            continue
        d = np.gradient(A_, axis=0)
        pts.append(A_)
        ang.append(np.arctan2(d[:, 1], d[:, 0]))
    P.path_pts = np.vstack(pts)
    P.path_ang = np.concatenate(ang)


def stamp(P, x, y, sx, sy, rz=0.0, pad=1.0):
    P.g.rect(P.m_struct, x, y, sx, sy, rz, pad)


def fence_line(mb, pts, h=2.0, panel=3.5, feet=True, mat="fence_mesh", closed=False):
    """Heras-style temporary fencing along a polyline (one merged mesh)."""
    P_, _ = resample(pts, panel, closed=closed)
    if closed:
        P_ = P_ + [P_[0]]
    m = _mi(mb, mat)
    f = _mi(mb, "metal_dark")
    for a, b in zip(P_[:-1], P_[1:]):
        z = a[2] if len(a) > 2 else 0.0
        mb.beam((a[0], a[1], z + 0.12 + h / 2), (b[0], b[1], z + 0.12 + h / 2), 0.08, m, d=h)
        if feet:
            ang = math.atan2(b[1] - a[1], b[0] - a[0])
            mb.box(0.7, 0.22, 0.14, (a[0], a[1], z), rz=ang, mat=f)


def barrier_line(mb, pts, h=1.1, z=0.0):
    P_, _ = resample(pts, 2.3)
    m = _mi(mb, "fence")
    for a, b in zip(P_[:-1], P_[1:]):
        mb.beam((a[0], a[1], z + h - 0.05), (b[0], b[1], z + h - 0.05), 0.07, m)
        mb.beam((a[0], a[1], z + 0.15), (b[0], b[1], z + 0.15), 0.07, m)
        ang = math.atan2(b[1] - a[1], b[0] - a[0])
        mb.box(0.12, 0.6, 0.1, (a[0], a[1], z), rz=ang, mat=m)
        mb.beam((a[0], a[1], z), (a[0], a[1], z + h), 0.06, m)


def place_local(mesh, coll, origin, rz, lx, ly, lz=0.0, lrz=0.0, s=1.0):
    """Place an asset in a rotated local frame (used for stage compounds)."""
    c, s_ = math.cos(rz), math.sin(rz)
    return place(mesh, coll, origin[0] + lx * c - ly * s_, origin[1] + lx * s_ + ly * c, lz, rz + lrz, s)


def face_towards(x, y, tx, ty):
    """Asset fronts face local -Y; return rz so the front points at (tx, ty)."""
    return math.atan2(ty - y, tx - x) + math.pi / 2


# =============================================================================
# 9a. STAGE 3 - MAIN ARENA AND STAGES
# =============================================================================

MAIN_STAGE = (0.0, 96.0)
WEST_STAGE = (-160.0, 4.0)
EAST_STAGE = (160.0, 4.0)


def line_array(mb, top, n=10, w=1.3, d=0.9, h=0.42, mat=0):
    x, y, z = top
    ang, yy = 0.0, y
    for i in range(n):
        ang += math.radians(1.2 + i * 0.9)
        yy -= math.sin(ang) * h * 0.5
        mb.box(w, d, h, (x, yy, z - (i + 1) * h * 0.98), rx=-ang, mat=mat)


def screen_unit(mb, cx, cy, z, w, h, mat_screen, legs=True, depth=0.6):
    mb.box(w + 0.4, depth, h + 0.4, (cx, cy, z - 0.2), mat=_mi(mb, "stage_black"))
    mb.box(w, 0.08, h, (cx, cy - depth / 2 - 0.02, z), mat=_mi(mb, mat_screen))
    if legs:
        for sx in (-w / 2 + 0.3, w / 2 - 0.3):
            mb.truss((cx + sx, cy + 0.8, Z["arena"]), (cx + sx, cy + 0.8, z + h * 0.6), 0.45, 0.06, 1.0, _mi(mb, "truss"))


def heads_along(mb, p0, p1, n, z):
    m = _mi(mb, "fixture")
    for k in range(n):
        t = (k + 0.5) / n
        x, y = p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t
        mb.box(0.36, 0.3, 0.3, (x, y, z - 0.7), mat=m)
        mb.cyl(0.16, 0.36, (x, y, z - 0.38), seg=8, mat=m)


def build_main_stage(P):
    log("stage 3: main stage")
    coll = C("Main Arena")
    z0 = Z["arena"]
    mb = MB()
    deck, blk, tr, spk = (_mi(mb, n) for n in ("stage_deck", "stage_black", "truss", "speaker"))
    mb.box(32, 16, 2.2, (0, 0, z0), mat=deck)
    mb.box(11, 6, 2.0, (0, -10.5, z0), mat=deck)
    for sx in (-1, 1):
        mb.box(9.5, 14, 2.2, (sx * 21.2, 1.0, z0), mat=blk)
        mb.box(4, 8, 2.2, (sx * 9, 11.5, z0), mat=blk, top=(1, 0.6))   # loading ramps
    H = 17.0
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.truss((sx * 18, sy * 8.6, z0), (sx * 18, sy * 8.6, z0 + H), 0.9, 0.1, 1.3, tr)
            mb.box(2.2, 2.2, 0.5, (sx * 18, sy * 8.6, z0), mat=blk)
    zt = z0 + H - 0.5
    C4 = [(-18, -8.6), (18, -8.6), (18, 8.6), (-18, 8.6)]
    for i in range(4):
        a, b = C4[i], C4[(i + 1) % 4]
        mb.truss((a[0], a[1], zt), (b[0], b[1], zt), 0.8, 0.09, 1.3, tr)
    for x in (-9, 0, 9):
        mb.truss((x, -8.6, zt), (x, 8.6, zt), 0.6, 0.07, 1.3, tr)
    mb.prism(20.0, 39.0, 2.8, (0, 0, zt + 0.45), rz=math.pi / 2, mat=_mi(mb, "stage_roof"))
    mb.box(38.0, 0.3, 1.6, (0, -9.9, zt - 0.6), mat=blk)                      # front header
    for x in (-12, -4, 4, 12):
        mb.truss((x - 3.5, -6.0, zt - 3.2), (x + 3.5, -6.0, zt - 3.2), 0.5, 0.06, 1.0, tr)
    heads_along(mb, (-16, -6.0), (16, -6.0), 16, zt - 3.1)
    heads_along(mb, (-16, 2.5), (16, 2.5), 12, zt)
    for sx in (-1, 1):
        line_array(mb, (sx * 20.6, -9.6, zt - 0.6), n=12, mat=spk)
        line_array(mb, (sx * 23.0, -7.0, zt - 1.6), n=9, w=1.1, mat=spk)
        screen_unit(mb, sx * 29.5, -5.5, z0 + 6.0, 8.2, 5.0, "screen_side")
    screen_unit(mb, 0, 7.6, z0 + 2.6, 24.0, 9.6, "screen_main", legs=False)
    for x in list(np.arange(-16.5, -6.5, 1.6)) + list(np.arange(7.0, 17.0, 1.6)):
        mb.box(1.3, 1.0, 1.2, (x, -9.0, z0), mat=spk)
    for sx in (-1, 1):
        mb.box(1.4, 1.2, 0.9, (sx * 7.5, -12.8, z0), mat=spk)
    # front-of-stage crowd barrier
    arc = [(x, -15.5 - 0.004 * x * x) for x in np.linspace(-24, 24, 25)]
    barrier_line(mb, arc, z=z0)
    me = _done(mb, "Main_Stage")
    # modest model-scale exaggeration so the main stage reads from above
    new_object("Main_Stage", me, coll, loc=(*MAIN_STAGE, 0.0), scale=1.3)

    # front of house and delay towers
    mb = MB()
    fx, fy = 0.0, 38.0
    mb.box(10, 8, 0.8, (fx, fy, z0), mat=_mi(mb, "stage_deck"))
    mb.box(10.6, 8.6, 0.3, (fx, fy, z0 + 3.3), mat=_mi(mb, "stage_roof"), top=(0.9, 0.9))
    for sx in (-4.8, 4.8):
        for sy in (-3.8, 3.8):
            mb.beam((fx + sx, fy + sy, z0 + 0.8), (fx + sx, fy + sy, z0 + 3.3), 0.15, _mi(mb, "truss"))
    mb.box(6, 1.2, 1.0, (fx, fy - 1.0, z0 + 0.8), mat=_mi(mb, "fixture"))
    barrier_line(mb, rounded_rect(fx - 7, fy - 6, fx + 7, fy + 6, 2), z=z0)
    for sx in (-1, 1):
        x, y = sx * 48.0, 16.0
        mb.truss((x - 1, y, z0), (x - 1, y, z0 + 9.5), 0.6, 0.07, 1.0, _mi(mb, "truss"))
        mb.truss((x + 1, y, z0), (x + 1, y, z0 + 9.5), 0.6, 0.07, 1.0, _mi(mb, "truss"))
        mb.box(3.0, 1.2, 0.3, (x, y, z0 + 9.5), mat=_mi(mb, "stage_black"))
        line_array(mb, (x, y - 0.4, z0 + 9.4), n=6, w=1.0, mat=_mi(mb, "speaker"))
        mb.box(3.2, 2.2, 0.4, (x, y, z0), mat=_mi(mb, "stage_black"))
    for sx in (-1, 1):
        x, y = sx * 64.0, -38.0
        mb.truss((x, y - 1, z0), (x, y - 1, z0 + 8.5), 0.6, 0.07, 1.0, _mi(mb, "truss"))
        mb.box(2.6, 2.0, 0.3, (x, y, z0 + 8.5), mat=_mi(mb, "stage_black"))
        line_array(mb, (x, y - 0.4, z0 + 8.4), n=5, w=1.0, mat=_mi(mb, "speaker"))
        mb.box(2.8, 2.2, 0.4, (x, y, z0), mat=_mi(mb, "stage_black"))
    new_object("Main_FOH_and_Delay_Towers", _done(mb, "Main_FOH_and_Delay_Towers"), coll)
    # raised VIP viewing deck (west) and accessible viewing platform (east)
    mb = MB()
    t = _mi(mb, "timber")
    vx, vy = -82.0, 70.0
    mb.box(26, 12, 1.2, (vx, vy, z0), mat=t)
    mb.box(4, 6, 1.2, (vx + 15, vy - 2, z0), mat=t, top=(1.0, 0.2))
    barrier_line(mb, [(vx - 13, vy - 6), (vx + 13, vy - 6)], z=z0 + 1.2)
    stretch_tent(mb, 14, 9, [(-2.5, 1.5, 2.2), (2.5, 1.5, 2.2)], z0=z0 + 1.2, mat="canvas", ox=vx, oy=vy)
    ax, ay = 82.0, 66.0
    mb.box(16, 8, 1.0, (ax, ay, z0), mat=t)
    mb.box(14, 2.5, 1.0, (ax - 14, ay - 2.8, z0), mat=t, top=(1.0, 1.0))
    barrier_line(mb, [(ax - 8, ay - 4), (ax + 8, ay - 4), (ax + 8, ay + 4)], z=z0 + 1.0)
    new_object("Viewing_Decks_VIP_and_Accessible", _done(mb, "Viewing_Decks_VIP_and_Accessible"), coll)
    stamp(P, vx, vy, 28, 14)
    stamp(P, ax - 4, ay, 30, 10)

    # backstage compound behind the main stage (inside arena fence)
    bx, by = MAIN_STAGE
    place(A["truck"], coll, bx - 40, by + 21, z0, 0.0)
    place(A["truck"], coll, bx + 42, by + 20, z0, math.pi)
    for x in (-22, -9, 9, 22):
        place(A["cabin"], coll, bx + x * 1.15, by + 31, z0, 0.0)
    for x in (-58, -52):
        place(A["container"], coll, bx + x, by + 21, z0, math.pi / 2)
    for x in (52, 58):
        place(A["container"], coll, bx + x, by + 20, z0, math.pi / 2)
    place(A["generator"], coll, bx - 30, by + 13, z0, 0.0)
    place(A["generator"], coll, bx + 30, by + 13, z0, 0.0)
    place(A["gazebo_white"], coll, bx - 4, by + 21, z0, 0.0)
    place(A["gazebo_white"], coll, bx + 4, by + 21, z0, 0.0)
    mb = MB()
    fence_line(mb, [(bx - 37, by + 12), (bx - 62, by + 12), (bx - 62, by + 35), (bx + 62, by + 35),
                    (bx + 62, by + 12), (bx + 37, by + 12)])
    new_object("Backstage_Fence", _done(mb, "Backstage_Fence"), coll, loc=(0, 0, z0))


def build_secondary_stage(P, which):
    coll = C("Secondary Stages")
    z0 = Z["arena"]
    mb = MB()
    deck, blk, tr, spk = (_mi(mb, n) for n in ("stage_deck", "stage_black", "truss", "speaker"))
    mb.box(18, 11, 1.6, (0, 0, z0), mat=deck)
    mb.box(6, 3, 1.4, (0, -7, z0), mat=deck)
    if which == "west":
        # arched shell roof (membrane) on a curved truss
        name, centre, rz = "West_Stage_Arch", WEST_STAGE, math.pi / 2
        n = 18
        vs, fs = [], []
        for k in range(n + 1):
            ph = math.pi * k / n
            for yy, sc in ((-6.5, 1.0), (6.0, 0.86)):
                vs.append((11.5 * sc * math.cos(ph), yy, z0 + 1.0 + 11.0 * sc * math.sin(ph)))
        for k in range(n):
            a = 2 * k
            fs.append((a, a + 2, a + 3, a + 1))
        mb.add(vs, fs, _mi(mb, "membrane_white"), smooth=True)
        prev = None
        for k in range(n + 1):
            ph = math.pi * k / n
            p = (11.9 * math.cos(ph), -6.7, z0 + 1.0 + 11.4 * math.sin(ph))
            if prev:
                mb.truss(prev, p, 0.5, 0.06, 1.0, tr)
            prev = p
        heads_along(mb, (-7, -4.0), (7, -4.0), 8, z0 + 10.5)
        screen_unit(mb, 0, 5.2, z0 + 2.0, 12.0, 5.6, "screen_main", legs=False)
    else:
        name, centre, rz = "East_Stage_Gable", EAST_STAGE, -math.pi / 2
        H = 11.0
        for sx in (-1, 1):
            for sy in (-1, 1):
                mb.truss((sx * 10, sy * 5.8, z0), (sx * 10, sy * 5.8, z0 + H), 0.7, 0.08, 1.2, tr)
        zt = z0 + H - 0.4
        C4 = [(-10, -5.8), (10, -5.8), (10, 5.8), (-10, 5.8)]
        for i in range(4):
            a, b = C4[i], C4[(i + 1) % 4]
            mb.truss((a[0], a[1], zt), (b[0], b[1], zt), 0.6, 0.07, 1.2, tr)
        mb.prism(13.0, 21.5, 2.4, (0, 0, zt + 0.35), rz=math.pi / 2, mat=_mi(mb, "membrane_teal"))
        heads_along(mb, (-9, -5.8), (9, -5.8), 10, zt)
        screen_unit(mb, 0, 5.0, z0 + 2.0, 14.0, 5.4, "screen_main", legs=False)
    for sx in (-1, 1):
        mb.box(1.6, 1.4, 4.2, (sx * 11.4, -4.6, z0), mat=spk)
        mb.box(1.6, 1.6, 1.2, (sx * 11.4, -7.0, z0), mat=spk)
        screen_unit(mb, sx * 16.0, -3.5, z0 + 3.2, 4.8, 2.8, "screen_side")
    arc = [(x, -10.5 - 0.006 * x * x) for x in np.linspace(-14, 14, 15)]
    barrier_line(mb, arc, z=z0)
    # FOH riser 34 m in front of the stage
    mb.box(6, 5, 0.6, (0, -34, z0), mat=deck)
    mb.box(6.6, 5.6, 0.24, (0, -34, z0 + 3.0), mat=_mi(mb, "stage_roof"))
    for sx in (-2.9, 2.9):
        for sy in (-2.4, 2.4):
            mb.beam((sx, -34 + sy, z0 + 0.6), (sx, -34 + sy, z0 + 3.0), 0.12, tr)
    new_object(name, _done(mb, name), coll, loc=(*centre, 0.0), rz=rz, scale=1.25)
    # small backstage behind each secondary stage
    place_local(A["container"], coll, centre, rz, -7, 16, z0, 0.0)
    place_local(A["cabin"], coll, centre, rz, 7, 17, z0, 0.0)
    place_local(A["generator"], coll, centre, rz, 0, 22, z0, 0.0)


def build_arena_details(P):
    log("stage 3: arena food, bars, production structures")
    coll = C("Main Arena")
    z0 = Z["arena"]
    rng = random.Random(P.seed + 3)
    cx, cy = ARENA_C
    for sx in (-1, 1):
        place(A["bar"], coll, sx * 96, -66, z0, sx * 0.25)
        stamp(P, sx * 96, -66, 24, 16, sx * 0.25)
    # food and beverage arcs on the south-west and south-east of the arena
    for a0, a1 in ((204, 246), (294, 336)):
        for row, (kx, ky, n) in enumerate(((0.91, 0.875, 13), (0.85, 0.80, 9))):
            for k in range(n):
                ang = a0 + (a1 - a0) * (k + 0.5 * row) / (n - 1 + row)
                x, y = arena_pt(ang, ARENA_R[0] * kx, ARENA_R[1] * ky)
                rz = face_towards(x, y, cx, cy - 10) + (math.pi if row else 0.0)
                asset = A["food_truck"] if (k + row) % 3 == 1 else A["stall"]
                place(asset, coll, x, y, z0, rz)
                stamp(P, x, y, 7, 5, rz)
        # picnic tables in front of each arc
        for k in range(16):
            ang = a0 + 4 + (a1 - a0 - 8) * rng.random()
            kk = rng.uniform(0.66, 0.76)
            x, y = arena_pt(ang, ARENA_R[0] * kk, ARENA_R[1] * (kk - 0.04))
            if P.g.hit(P.m_struct, x, y, 1.5):
                continue
            place(A["picnic"], coll, x, y, z0, rng.uniform(-0.3, 0.3))
            stamp(P, x, y, 2.0, 2.0, pad=0.3)
    for sx in (-1, 1):
        place(A["bins"], coll, sx * 82, -80, z0, 0.0)
        place(A["bins"], coll, sx * 110, -52, z0, 0.0)
        for k in range(6):
            place(A["hay"], coll, sx * (96 + rng.uniform(-14, 14)), -84 + rng.uniform(-4, 3), z0, rng.uniform(0, 3))
    # information / lost property and first aid post near the arena gate
    place(A["info"], coll, -34, -98, z0, 0.0)
    place(A["medical"], coll, 34, -100, z0, 0.0)
    place(A["gazebo_white"], coll, 34, -91, z0, 0.0)
    for x, y, rz in ((-150, -52, 0.6), (150, -52, -0.6), (-118, 88, -0.5), (118, 88, 0.5)):
        place(A["toilets"], coll, x, y, z0, rz)
        place(A["bins"], coll, x + 6, y + 3, z0, rz)
    for x, y in ((-52, -104), (52, -104), (-108, 60), (108, 60)):
        place(A["water"], coll, x, y, z0, 0.0)
    for ang in (22, 62, 118, 158, 202, 245, 295, 338):
        x, y = arena_pt(ang, ARENA_R[0] * 0.95, ARENA_R[1] * 0.93)
        place(A["light_tower"], coll, x, y, z0, face_towards(x, y, cx, cy) + math.pi)
    # arena perimeter fence with gaps at every gate
    mb = MB()
    gaps = [(a - w, a + w) for a, w in ARENA_GATES]

    def in_gap(deg):
        for a0, a1 in gaps:
            if a0 <= deg <= a1 or a0 <= deg - 360 <= a1 or a0 <= deg + 360 <= a1:
                return True
        return False
    run = []
    for k in range(721):
        deg = -180 + k * 0.5
        x, y = arena_pt(deg, ARENA_R[0] + 1.5, ARENA_R[1] + 1.5)
        if in_gap(deg):
            if len(run) > 1:
                fence_line(mb, run)
            run = []
        else:
            run.append((x, y))
    if len(run) > 1:
        fence_line(mb, run)
    new_object("Arena_Perimeter_Fence", _done(mb, "Arena_Perimeter_Fence"), coll)


# =============================================================================
# 9b. STAGE 4 - CAMPING ZONES
# =============================================================================

def tent_rows(P, zone, coll, kinds, spacing, angle, block_rows, lane, skip, z, seed,
              inset=3.0, jitter=0.5, gap_noise=0.42, extra_masks=()):
    rng = random.Random(seed)
    poly = P.zones[zone]
    inner = offset_poly(poly, -inset)
    Pp = np.asarray(poly)
    c, s = math.cos(angle), math.sin(angle)
    u = Pp[:, 0] * c + Pp[:, 1] * s
    v = -Pp[:, 0] * s + Pp[:, 1] * c
    dx, dy = spacing
    names, weights = zip(*kinds)
    masks = [P.m_paths, P.m_struct, P.m_water, P.m_arena, P.m_hard, P.m_trees] + list(extra_masks)
    placed = 0
    j = 0
    vv = v.min()
    while vv < v.max():
        uu = u.min() + (dx / 2 if j % 2 else 0) + rng.uniform(0, 1.0)
        while uu < u.max():
            x = uu * c - vv * s + rng.uniform(-jitter, jitter)
            y = uu * s + vv * c + rng.uniform(-jitter, jitter)
            uu += dx
            if rng.random() < skip:
                continue
            if mnoise.noise(Vector((x * 0.035, y * 0.035, seed * 0.01))) > gap_noise:
                continue
            if not in_poly(x, y, inner):
                continue
            if any(P.g.hit(m, x, y, 1.6) for m in masks):
                continue
            k = rng.choices(names, weights)[0]
            rz = angle + (0 if (j // 1) % 2 == 0 else math.pi) + rng.uniform(-0.18, 0.18)
            place(A[k], coll, x, y, z, rz)
            placed += 1
        j += 1
        vv += dy + (lane if j % block_rows == 0 else 0)
    return placed


def build_camping(P):
    log("stage 4: camping zones and tents")
    z = Z["zone"]
    n1 = tent_rows(P, "general", C("Camping General"),
                   [("dome", 0.42), ("tunnel", 0.22), ("ridge", 0.2), ("family", 0.1), ("gazebo", 0.06)],
                   (5.2, 6.0), 0.05, 3, 4.5, 0.06, z, P.seed + 11, gap_noise=0.5)
    n2 = tent_rows(P, "priority", C("Camping Priority"),
                   [("dome_p", 0.35), ("tunnel_p", 0.25), ("family_p", 0.28), ("gazebo", 0.12)],
                   (9.5, 10.5), -0.03, 2, 6.0, 0.08, z, P.seed + 12, gap_noise=0.55)
    # wildflower: small friend-groups of tents around a shared gazebo, among trees
    coll = C("Camping Wildflower")
    rng = random.Random(P.seed + 13)
    poly = P.zones["wildflower"]
    inner = offset_poly(poly, -5)
    Pp = np.asarray(poly)
    sh = SpatialHash(20)
    masks = [P.m_paths, P.m_struct, P.m_trees]
    n3 = 0
    for _ in range(3000):
        x = rng.uniform(Pp[:, 0].min(), Pp[:, 0].max())
        y = rng.uniform(Pp[:, 1].min(), Pp[:, 1].max())
        if not in_poly(x, y, inner) or not sh.ok(x, y, 7.5) or any(P.g.hit(m, x, y, 2.5) for m in masks):
            continue
        sh.add(x, y, 7.5)
        if rng.random() < 0.45:
            place(A["gazebo"], coll, x, y, z, rng.uniform(0, 1.5))
        k = rng.randint(3, 6)
        a0 = rng.uniform(0, 2 * math.pi)
        for t in range(k):
            a = a0 + 2 * math.pi * t / k + rng.uniform(-0.2, 0.2)
            r = rng.uniform(4.6, 6.4)
            tx, ty = x + r * math.cos(a), y + r * math.sin(a)
            if not in_poly(tx, ty, inner) or any(P.g.hit(m, tx, ty, 1.5) for m in masks):
                continue
            kind = rng.choices(["dome", "tunnel", "ridge", "family"], [0.4, 0.25, 0.2, 0.15])[0]
            place(A[kind], coll, tx, ty, z, face_towards(tx, ty, x, y) + rng.uniform(-0.2, 0.2))
            n3 += 1
        P.g.circle(P.m_struct, x, y, 7.5)      # keeps flowers/shrubs out of the camp group
    log(f"  tents: general {n1}, priority {n2}, wildflower {n3}")
    build_glamping(P)


def build_glamping(P):
    coll = C("Glamping Village")
    z = Z["zone"]
    rng = random.Random(P.seed + 14)
    # reception tent just inside the glamping gate (reserved before the rows)
    place(A["safari"], coll, 266, -92, z, math.pi / 2)
    stamp(P, 266, -92, 8, 7, 0.0, pad=1.5)
    # NW quadrant - pre-pitched tents in tidy rows
    n = 0
    for j, y in enumerate(np.arange(-84, -146, -9.0)):
        for x in np.arange(268, 346, 7.4):
            if P.g.hit(P.m_paths, x, y, 1.8) or P.g.hit(P.m_struct, x, y, 2.0):
                continue
            place(A["prepitched"], coll, x, y, z, 0.0 if j % 2 else math.pi)
            n += 1
    # NE quadrant - bell tents in rings around fire pits
    for rx, ry in ((386, -112), (436, -112)):
        place(A["fire_pit"], coll, rx, ry, z, 0.0)
        for k in range(7):
            a = 2 * math.pi * k / 7 + 0.2
            tx, ty = rx + 15 * math.cos(a), ry + 14 * math.sin(a)
            if P.g.hit(P.m_paths, tx, ty, 2.0):
                continue
            place(A["bell"], coll, tx, ty, z, face_towards(tx, ty, rx, ry))
            n += 1
    # SW quadrant - safari tents on decks facing a shared lawn
    for x in (268, 286, 304, 322, 340):
        place(A["safari"], coll, x, -176, z, math.pi)
        place(A["safari"], coll, x, -224, z, 0.0)
        n += 2
    place(A["fire_pit"], coll, 309, -200, z, 0.0)
    # SE quadrant - reception lounge, showers, toilets
    place(A["lounge"], coll, 410, -192, z, 0.0, 1.4)
    place(A["showers"], coll, 380, -230, z, math.pi / 2)
    place(A["showers"], coll, 396, -230, z, math.pi / 2)
    place(A["toilets"], coll, 432, -232, z, 0.0)
    place(A["water"], coll, 448, -205, z, -math.pi / 2)
    place(A["bins"], coll, 446, -176, z, -math.pi / 2)
    for k in range(9):
        a = math.radians(200 + 140 * k / 8)
        place(A["hay"], coll, 410 + 17 * math.cos(a), -192 - 13 * math.sin(a), z, a)
    # planting beds along the shared paths
    for n_, pl, w in P.glamp_paths:
        pts, _ = resample(pl, 11.0, closed=(n_ == "glamp_loop"))
        for k, (x, y) in enumerate(pts):
            if k % 2:
                continue
            a = path_angle_near(P, x, y) - math.pi / 2
            px, py = x + 4.2 * math.cos(a), y + 4.2 * math.sin(a)
            if not P.g.hit(P.m_struct, px, py, 1.5):
                place(A["flowers"], coll, px, py, z - 0.15, rng.uniform(0, 6.28), 0.55)
    # lantern posts along the shared paths
    for n_, pl, w in P.glamp_paths:
        pts, _ = resample(pl, 16.0, closed=(n_ == "glamp_loop"))
        for k, (x, y) in enumerate(pts):
            a = path_angle_near(P, x, y)
            place(A["lantern"], coll, x + 3.0 * math.cos(a + math.pi / 2), y + 3.0 * math.sin(a + math.pi / 2), z)
    log(f"  glamping units: {n}")


# =============================================================================
# 9c. STAGE 5 - PARKING AND ENTRANCES
# =============================================================================

def parking_lot(P, lot, name, fill=0.6, seed=0, vehicles=("car",)):
    coll = C("Parking")
    rng = random.Random(seed)
    x0, y0, x1, y1 = lot
    z = Z["lot"]
    bw, bd = 2.6, 5.2
    xm = (x0 + x1) / 2
    xs = [x for x in np.arange(x0 + 9 + bw / 2, x1 - 9, bw) if abs(x - xm) > 5.0]
    mk = MB()
    isl = MB()
    m_mark = _mi(mk, "road_marking")
    rows = []
    for yb in (y0 + 8.0, y0 + 27.3, y0 + 46.6):
        rows.append((yb, 1))                    # cars nose north toward the island
        rows.append((yb + 7.6, -1))
        half = (xm - 5.0) - (x0 + 9.0)
        for xc in (x0 + 9.0 + half / 2, x1 - 9.0 - half / 2):
            isl.box(half, 2.4, 0.35, (xc, yb + 6.4, z), mat=_mi(isl, "kerb"))
            isl.box(half - 0.4, 2.0, 0.37, (xc, yb + 6.4, z), mat=_mi(isl, "lawn"))
        for x in np.arange(x0 + 14, x1 - 9, 13.0):
            if abs(x - xm) > 6:
                P.lot_trees.append((x + rng.uniform(-1, 1), yb + 6.4, z + 0.37))
    if y1 - y0 > 70:
        rows.append((y0 + 65.9, 1))
    lines = sorted({round(x + d, 2) for x in xs for d in (-bw / 2, bw / 2)})
    for yb, facing in rows:
        for xl in lines:
            mk.box(0.16, bd - 0.4, 0.02, (xl, yb + bd / 2, z), mat=m_mark)
        for x in xs:
            if rng.random() < fill:
                kind = rng.choices(vehicles, [1.0] * len(vehicles))[0]
                rz = (0 if facing > 0 else math.pi) + math.pi / 2 + rng.uniform(-0.04, 0.04)
                place(A[kind], coll, x + rng.uniform(-0.15, 0.15), yb + bd / 2, z, rz)
    new_object(name + "_Bay_Markings", _done(mk, name + "_Bay_Markings"), coll)
    new_object(name + "_Islands", _done(isl, name + "_Islands", bevel=0.08), coll)


def build_parking(P):
    log("stage 5: parking bays, vehicles and shuttle drop-off")
    P.lot_trees = []
    parking_lot(P, LOT_A, "Parking_A", 0.62, P.seed + 21)
    parking_lot(P, LOT_B, "Parking_B", 0.55, P.seed + 22)
    parking_lot(P, STAFF_LOT, "Staff_Parking", 0.5, P.seed + 23, vehicles=("van", "car", "van"))
    coll = C("Parking")
    cx, cy = SHUTTLE_C
    for x in (cx - 15, cx - 6, cx + 3):
        place(A["shelter"], coll, x, cy + 27.5, Z["plaza"], 0.0)
    for ang in (120.0, 72.0):
        a = math.radians(ang)
        place(A["bus"], coll, cx + SHUTTLE_R * math.cos(a), cy + SHUTTLE_R * math.sin(a), Z["road"], a + math.pi / 2)
    place(A["tree_c"], coll, cx, cy, Z["road"] + 0.15, 0.0, 0.9)
    for (x, y) in ((LOT_A[0] + 4, LOT_A[3] - 3), (LOT_B[2] - 4, LOT_B[3] - 3)):
        place(A["light_tower"], coll, x, y, Z["lot"], 0.0)


def gate_portal(mb, xs, y, z, h=9.0, fascia="membrane_white"):
    tr = _mi(mb, "truss")
    for x in xs:
        mb.truss((x, y, z), (x, y, z + h), 0.9, 0.09, 1.2, tr)
        mb.box(1.8, 1.8, 0.5, (x, y, z), mat=_mi(mb, "stage_black"))
    mb.truss((xs[0] - 0.6, y, z + h - 0.4), (xs[-1] + 0.6, y, z + h - 0.4), 0.8, 0.09, 1.2, tr)
    w = xs[-1] - xs[0] + 2.0
    xc = (xs[0] + xs[-1]) / 2
    mb.box(w, 0.2, 2.2, (xc, y - 0.6, z + h - 3.0), mat=_mi(mb, fascia))
    mb.box(w, 0.22, 0.5, (xc, y - 0.62, z + h - 3.6), mat=_mi(mb, "fabric_accent"))


def build_entrances(P):
    log("stage 5: main and priority entrances")
    coll = C("Entrances")
    z = Z["plaza"]
    ex = ENTRANCE_X
    mb = MB()
    gate_portal(mb, [ex - 36, ex - 12, ex + 12, ex + 36], -150.0, z)
    for k in range(-6, 7):
        barrier_line(mb, [(ex + k * 6.0, -183.0), (ex + k * 6.0, -158.0)], z=z)
    barrier_line(mb, [(ex - 44, -152), (ex - 37, -152)], z=z)
    barrier_line(mb, [(ex + 37, -152), (ex + 44, -152)], z=z)
    new_object("Main_Entrance_Gate", _done(mb, "Main_Entrance_Gate"), coll)
    for x in (ex - 27, ex - 9, ex + 9, ex + 27):
        place(A["gazebo_white"], coll, x, -139, z, 0.0)
    for y in (-178, -168, -158, -148, -138):
        place(A["booth"], coll, -70, y, z, math.pi / 2)
    place(A["info"], coll, 42, -132, z, math.pi)
    place(A["toilets"], coll, 44, -176, z, 0.0)
    place(A["bins"], coll, 30, -170, z, 0.0)
    place(A["bins"], coll, -52, -134, z, 0.0)
    place(A["water"], coll, 28, -132, z, 0.0)
    place(A["light_tower"], coll, -60, -128, z, 0.3)
    place(A["light_tower"], coll, 50, -150, z, -0.3)
    for x, y in ((-68, -126), (52, -124), (-30, -125), (12, -125)):
        place(A["flowers"], coll, x, y, z, 0.0, 0.8)
    # priority entrance: compact gate, booth and search tents off the drop-off
    gx, gy = PRIORITY_GATE
    mb = MB()
    gate_portal(mb, [gx - 9, gx + 9], gy - 9, Z["lot"], h=7.5)
    barrier_line(mb, [(gx - 3, gy - 22), (gx - 3, gy - 12)], z=Z["lot"])
    barrier_line(mb, [(gx + 3, gy - 22), (gx + 3, gy - 12)], z=Z["lot"])
    new_object("Priority_Entrance_Gate", _done(mb, "Priority_Entrance_Gate"), coll)
    place(A["booth"], coll, gx - 11, gy - 16, Z["lot"], math.pi / 2)
    place(A["booth"], coll, gx + 11, gy - 16, Z["lot"], -math.pi / 2)
    place(A["gazebo"], coll, gx + 11, gy - 25, Z["lot"], 0.0)
    place(A["car"], coll, gx - 8, gy - 27, Z["lot"], 0.0)
    place(A["bins"], coll, gx - 14, gy - 6, 0.0, 0.0)


# =============================================================================
# 9d. STAGE 7 - FACILITIES AND SMALLER STRUCTURES
# =============================================================================

def plan_facilities(P):
    """Reserve footprints for camping facilities before tents and trees."""
    specs = [
        # zone, kind, x, y
        ("general", "toilets", -236, 200), ("general", "toilets", -118, 196), ("general", "toilets", -24, 204),
        ("general", "toilets", -232, 268), ("general", "toilets", -112, 284), ("general", "toilets", -14, 272),
        ("general", "showers", -196, 252), ("general", "showers", -84, 252),
        ("general", "water", -200, 214), ("general", "water", -90, 214), ("general", "water", -10, 222),
        ("general", "water", -250, 248), ("general", "water", -140, 260), ("general", "water", -40, 262),
        ("general", "bins", -150, 200), ("general", "bins", -40, 196), ("general", "bins", -200, 280),
        ("general", "bins", -80, 286), ("general", "light_tower", -128, 225), ("general", "light_tower", -20, 236),
        ("general", "info", -268, 214),
        ("wildflower", "toilets", -300, 42), ("wildflower", "toilets", -410, 104),
        ("wildflower", "showers", -360, 44), ("wildflower", "water", -282, 112),
        ("wildflower", "water", -398, 64), ("wildflower", "water", -334, 140),
        ("wildflower", "bins", -268, 70), ("wildflower", "bins", -380, 120),
        ("priority", "toilets", 300, 0), ("priority", "toilets", 424, 82), ("priority", "showers", 298, 84),
        ("priority", "showers", 420, -14), ("priority", "water", 330, 18), ("priority", "water", 398, 4),
        ("priority", "water", 380, 92), ("priority", "bins", 280, 30), ("priority", "bins", 440, 50),
        ("priority", "stall", 272, 70), ("priority", "light_tower", 350, 64),
    ]
    sizes = {"toilets": (9, 4), "showers": (8, 9), "water": (4, 4), "bins": (3, 2),
             "light_tower": (4, 3), "info": (8, 5), "stall": (5, 5)}
    P.facilities = []
    for zone, kind, x, y in specs:
        sx, sy = sizes[kind]
        spot = free_spot(P, x, y, max(sx, sy) / 2 + 0.5, [P.m_paths, P.m_struct, P.m_water])
        if spot is None:
            continue
        x, y = spot
        rz = path_angle_near(P, x, y)
        P.facilities.append((zone, kind, x, y, rz))
        stamp(P, x, y, sx, sy, rz, pad=2.0)


def build_facilities(P):
    log("stage 7: facilities, compounds and smaller structures")
    zc = {"general": "Camping General", "wildflower": "Camping Wildflower", "priority": "Camping Priority"}
    for zone, kind, x, y, rz in P.facilities:
        place(A[kind], C(zc[zone]), x, y, ground_z(P, x, y), rz)
    coll = C("Facilities")
    z = Z["service"]
    # production + medical compound (west), fenced, off the service road
    x0, y0, x1, y1 = COMPOUND
    for y in (y1 - 8, y1 - 20):
        place(A["medical"], coll, x0 + 14, y, z, 0.0)
    place(A["gazebo_white"], coll, x0 + 32, y1 - 14, z, 0.0)
    place(A["ambulance"], coll, x0 + 8, y0 + 10, z, math.pi / 2)
    place(A["ambulance"], coll, x0 + 14, y0 + 10, z, math.pi / 2)
    place(A["ambulance"], coll, x0 + 20, y0 + 10, z, math.pi / 2)
    place(A["cabin"], coll, x1 - 22, y1 - 8, z, 0.0)
    place(A["cabin"], coll, x1 - 22, y1 - 8, z + 3.0, 0.0)           # two-storey site office
    place(A["cabin"], coll, x1 - 22, y1 - 20, z, 0.0)
    for k in range(4):
        place(A["container"], coll, x0 + 42 + k * 3.4, y0 + 8, z, math.pi / 2)
    place(A["generator"], coll, x1 - 8, y0 + 12, z, math.pi / 2)
    place(A["water"], coll, x1 - 8, y1 - 30, z, 0.0)
    mb = MB()
    mb.cyl(2.6, 3.2, (x1 - 8, y1 - 40, z), seg=20, mat=_mi(mb, "water_tank"))
    gx = -395.0
    fence_line(mb, [(gx - 5, y1 + 1.5), (x0 - 1.5, y1 + 1.5), (x0 - 1.5, y0 - 1.5), (x1 + 1.5, y0 - 1.5),
                    (x1 + 1.5, y1 + 1.5), (gx + 5, y1 + 1.5)])
    new_object("Compound_Fence_and_Tank", _done(mb, "Compound_Fence_and_Tank"), coll, loc=(0, 0, z))
    # staff catering
    place(A["gazebo_white"], coll, x0 + 52, y1 - 26, z, 0.0)
    place(A["picnic"], coll, x0 + 50, y1 - 26, z + 0.0, 0.0)
    # waste and recycling depot
    x0, y0, x1, y1 = WASTE_DEPOT
    for k in range(4):
        place(A["skip"], coll, x0 + 6 + k * 9.5, y0 + 6, z, 0.0)
    place(A["container12"], coll, x0 + 12, y1 - 6, z, 0.0)
    place(A["container12"], coll, x0 + 28, y1 - 6, z, 0.0)
    place(A["bins"], coll, x1 - 3, y0 + 14, z, math.pi / 2)


# =============================================================================
# 9e. STAGE 6 - TREES AND NATURAL LANDSCAPING
# =============================================================================

TREE_KINDS = [("tree_a", 0.26), ("tree_b", 0.2), ("tree_c", 0.14), ("tree_d", 0.16),
              ("umbrella", 0.08), ("conifer", 0.08), ("poplar", 0.08)]
TREE_R = {"tree_a": 3.6, "tree_b": 4.4, "tree_c": 3.2, "tree_d": 4.2, "umbrella": 4.6, "conifer": 2.6, "poplar": 2.2}


def plan_trees(P):
    log("planning trees")
    rng = random.Random(P.seed + 31)
    g = P.g
    blocked = P.m_paths | P.m_hard | P.m_water | P.m_arena | P.m_struct
    for k in ("general", "glamping", "priority"):
        blocked = blocked | P.m_zone[k]
    road = g.empty()
    g.line(road, ROAD_PTS, ROAD_W + 9.0)
    blocked |= road
    sh = SpatialHash(10)
    trees = []
    names, weights = zip(*TREE_KINDS)

    def try_add(x, y, kind, r, factor=0.78):
        if g.hit(blocked, x, y, r * 0.45) or not sh.ok(x, y, r, factor):
            return False
        sh.add(x, y, r)
        trees.append((kind, x, y, r))
        g.circle(P.m_trees, x, y, r * 0.8)
        return True
    # ring of shade trees between the arena fence and the ring path
    gates = [a for a, w in ARENA_GATES]
    for k in range(200):
        deg = -180 + k * 1.8 + rng.uniform(-0.5, 0.5)
        if any(abs(((deg - a + 180) % 360) - 180) < 7 for a in gates) or -112 < deg < -68 or 75 < deg < 105:
            continue
        x, y = arena_pt(deg, ARENA_R[0] + 8.5, ARENA_R[1] + 8.0)
        r = rng.uniform(2.6, 3.4)
        if sh.ok(x, y, r, 1.05) and not g.hit(P.m_paths, x, y, 1.0):
            sh.add(x, y, r)
            trees.append(("tree_a" if k % 3 else "tree_c", x, y, r))
    # a few shade trees just inside the arena edge, clear of stages and stalls
    for k in range(60):
        deg = rng.uniform(-180, 180)
        if any(abs(((deg - a + 180) % 360) - 180) < 12 for a in gates + [0, 180]) or 50 < deg < 130:
            continue
        kk = rng.uniform(0.9, 0.95)
        x, y = arena_pt(deg, ARENA_R[0] * kk, ARENA_R[1] * kk)
        r = rng.uniform(3.0, 4.0)
        if sh.ok(x, y, r, 1.4) and not g.hit(P.m_struct, x, y, r):
            sh.add(x, y, r)
            trees.append(("tree_b", x, y, r))
    # scattered woodland: dense perimeter belt, noise clusters, isolated trees
    for _ in range(140000):
        x, y = rng.uniform(X0 + 2, X1 - 2), rng.uniform(Y0 + 2, Y1 - 2)
        de = min(x - X0, X1 - x, y - Y0, Y1 - y)
        belt = 1.0 if de < 20 else max(0.0, 1.0 - (de - 20) / 14.0)
        n = mnoise.noise(Vector((x * 0.012, y * 0.012, 3.1)))
        clusters = min(1.0, max(0.0, (n - 0.16) / 0.3))
        dens = max(0.9 * belt, 0.62 * clusters, 0.02)
        i, j = int((x - g.x0)), int((y - g.y0))
        if P.m_zone["wildflower"][j, i]:
            dens = 0.012 + 0.07 * clusters
        elif P.m_zone["clearing"][j, i]:
            dens = 0.02
        if rng.random() > dens:
            continue
        kind = rng.choices(names, weights)[0]
        r = TREE_R[kind] * rng.uniform(0.8, 1.25)
        try_add(x, y, kind, r)
    # a few deliberate shade trees in priority camping and the glamping lawns
    for x, y in ((300, 60), (410, 25), (330, 100), (440, -25), (285, -5),
                 (280, -200), (338, -200), (380, -140), (430, -140), (372, -196)):
        trees.append(("tree_b", x, y, 3.8))
        g.circle(P.m_trees, x, y, 3.5)
    P.trees = trees
    log(f"  planned {len(trees)} trees")


def build_vegetation(P):
    log("stage 6: trees, shrubs, reeds and wildflowers")
    coll = C("Trees and Vegetation")
    rng = random.Random(P.seed + 41)
    for kind, x, y, r in P.trees:
        s = r / TREE_R[kind]
        z = ground_z(P, x, y)
        place(A[kind], coll, x, y, z, rng.uniform(0, 2 * math.pi), s, s * rng.uniform(0.9, 1.12))
    for x, y, z in getattr(P, "lot_trees", []):
        place(A["tree_c"], coll, x, y, z, rng.uniform(0, 6.28), 0.75)
    # shrubs: along path edges and woodland margins
    g = P.g
    blocked = P.m_paths | P.m_hard | P.m_water | P.m_arena | P.m_struct
    for k in ("general", "glamping", "priority"):
        blocked = blocked | P.m_zone[k]
    n = 0
    sh = SpatialHash(6)
    for _ in range(30000):
        x, y = rng.uniform(X0 + 2, X1 - 2), rng.uniform(Y0 + 2, Y1 - 2)
        if g.hit(blocked, x, y, 1.2) or g.hit(P.m_trees, x, y, 0.5):
            continue
        if mnoise.noise(Vector((x * 0.02, y * 0.02, 8.2))) < 0.05:
            continue
        r = rng.uniform(0.9, 1.8)
        if not sh.ok(x, y, r, 1.2):
            continue
        sh.add(x, y, r)
        place(A["shrub_a" if rng.random() < 0.6 else "shrub_b"], coll, x, y, ground_z(P, x, y),
              rng.uniform(0, 6.28), r)
        n += 1
        if n > 1400:
            break
    # wildflower mounds - the daisies - in the wildflower camp and meadow margins
    for _ in range(4000):
        x, y = rng.uniform(-450, -235), rng.uniform(10, 165)
        if not in_poly(x, y, P.zones["wildflower"]) or g.hit(P.m_paths, x, y, 2) or g.hit(P.m_trees, x, y, 2) \
                or g.hit(P.m_struct, x, y, 2) or rng.random() > 0.35:
            continue
        place(A["flowers"], coll, x, y, Z["zone"] - 0.15, rng.uniform(0, 6.28), rng.uniform(0.6, 1.1))
    for _ in range(160):
        a = rng.uniform(0, 2 * math.pi)
        rr = rng.uniform(0.8, 1.02)
        x = CLEARING_C[0] + CLEARING_R[0] * rr * math.cos(a)
        y = CLEARING_C[1] + CLEARING_R[1] * rr * math.sin(a)
        if not g.hit(P.m_paths, x, y, 2):
            place(A["flowers"], coll, x, y, Z["zone"] - 0.15, rng.uniform(0, 6.28), rng.uniform(0.5, 0.9))
    # reeds and rocks along the dam shoreline
    lake = C("Lake")
    pts, _ = resample(P.lake, 5.0, closed=True)
    cx = np.mean(np.asarray(P.lake)[:, 0])
    cy = np.mean(np.asarray(P.lake)[:, 1])
    for x, y in pts:
        if rng.random() < 0.45:
            continue
        d = math.hypot(x - cx, y - cy)
        ox, oy = (cx - x) / d, (cy - y) / d
        k = rng.uniform(-0.5, 1.5)
        place(A["reeds"], lake, x + ox * k, y + oy * k, -0.4, rng.uniform(0, 6.28), rng.uniform(0.8, 1.4))
    for k in range(14):
        x, y = pts[rng.randrange(len(pts))]
        place(A["rock"], lake, x, y, -0.2, rng.uniform(0, 6.28), rng.uniform(0.6, 1.4))


def build_lake_features(P):
    """Jetty and a small beach at the south shore of the dam."""
    coll = C("Lake")
    L = np.asarray(P.lake)
    target = np.array([205.0, 170.0])
    k = int(np.argmin(np.sum((L - target) ** 2, axis=1)))
    sx, sy = L[k]
    cx, cy = L[:, 0].mean(), L[:, 1].mean()
    d = math.hypot(cx - sx, cy - sy)
    ux, uy = (cx - sx) / d, (cy - sy) / d
    rz = math.atan2(uy, ux) - math.pi / 2
    mb = MB()
    t, p = _mi(mb, "timber"), _mi(mb, "timber_dark")
    mb.box(3.2, 20.0, 0.25, (0, 7.0, 0.35), mat=t)
    mb.box(9.0, 4.0, 0.25, (0, 18.0, 0.35), mat=t)
    for yy in np.arange(0, 20, 3.0):
        for xx in (-1.4, 1.4):
            mb.cyl(0.14, 1.0, (xx, yy, -0.6), seg=6, mat=p)
    new_object("Dam_Jetty", _done(mb, "Dam_Jetty", bevel=0.03), coll, loc=(sx - ux * 3, sy - uy * 3, 0), rz=rz)
    tx, ty = -uy, ux
    bc = (sx - ux * 6.5, sy - uy * 6.5)
    beach = [(bc[0] + tx * 12 * math.cos(a) + ux * 5.5 * math.sin(a),
              bc[1] + ty * 12 * math.cos(a) + uy * 5.5 * math.sin(a))
             for a in np.linspace(0, 2 * math.pi, 40, endpoint=False)]
    slab("Dam_Beach", chaikin(beach, 2), 0.07, -0.3, MATS["beach_sand"], coll, bevel=0.2)


def build_clearing(P):
    """Open grass clearing east of the dam: wellness decks and hay-bale circles."""
    coll = C("Trees and Vegetation")
    z = Z["zone"]
    mb = MB()
    cx, cy = CLEARING_C
    for dx, dy in ((-30, 10), (25, -18)):
        mb.cyl(7.0, 0.35, (cx + dx, cy + dy, z), seg=8, mat=_mi(mb, "timber"), smooth=False)
    new_object("Clearing_Wellness_Decks", _done(mb, "Clearing_Wellness_Decks", bevel=0.05), coll)
    for dx, dy in ((20, 25), (-20, -25)):
        place(A["fire_pit"], coll, cx + dx, cy + dy, z, 0.0)


def build_full(P):
    index_paths(P)
    build_assets()
    plan_facilities(P)
    # Stage 3 - arena structures
    build_main_stage(P)
    build_secondary_stage(P, "west")
    build_secondary_stage(P, "east")
    build_arena_details(P)
    # Stage 5 - parking and entrances (before trees so lots get island trees)
    build_parking(P)
    build_entrances(P)
    # Stage 6/7 planning order: trees first so tents can avoid them
    plan_trees(P)
    # Stage 4 - camping tents
    build_camping(P)
    # Stage 6 - vegetation and natural features
    build_vegetation(P)
    build_lake_features(P)
    build_clearing(P)
    # Stage 7 - facilities
    build_facilities(P)


# =============================================================================
# 10. MAIN
# =============================================================================

def parse_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    elif os.path.basename(argv[0]).lower().startswith("blender") or bpy.app.binary_path and argv[0] == bpy.app.binary_path:
        argv = []
    else:
        argv = argv[1:]
    p = argparse.ArgumentParser(description="Rocking the Daisies 2027 site model")
    p.add_argument("--out", default=CONFIG["out_dir"])
    p.add_argument("--stage", choices=["layout", "full"], default=CONFIG["stage"])
    p.add_argument("--views", default=",".join(CONFIG["views"]))
    p.add_argument("--res", type=int, default=CONFIG["res_x"])
    p.add_argument("--samples", type=int, default=CONFIG["samples"])
    p.add_argument("--seed", type=int, default=CONFIG["seed"])
    p.add_argument("--no-render", action="store_true")
    a, _ = p.parse_known_args(argv)
    a.render = CONFIG["render"] and not a.no_render
    return a


def default_out_dir():
    here = None
    try:
        f = os.path.abspath(__file__)
        if os.path.isfile(f):
            here = os.path.dirname(f)
    except NameError:
        pass
    if here is None and bpy.data.filepath:
        here = os.path.dirname(bpy.data.filepath)
    return os.path.join(here or os.getcwd(), "output")


def main():
    a = parse_args()
    out = os.path.abspath(a.out or default_out_dir())
    os.makedirs(out, exist_ok=True)
    reset_scene()
    for n in COLLECTION_NAMES:
        C(n)
    build_materials()
    P = make_plan(a.seed)

    # Stage 1-4 ground layers (always built)
    build_terrain(P)
    build_lake(P)
    build_roads_paths(P)
    build_grounds(P)
    build_parking_ground(P)
    if a.stage == "full":
        build_full(P)

    top, obl = build_lighting_camera()
    res_x = a.res
    setup_render(a.samples, res_x, int(res_x * 2 / 3))
    tag = "" if a.stage == "full" else "_layout_preview"
    blend = os.path.join(out, CONFIG["blend_name"].replace(".blend", f"{tag}.blend"))
    stats(out)
    bpy.ops.wm.save_as_mainfile(filepath=blend, compress=True)
    log(f"saved {blend}")
    if a.render:
        views = [v.strip() for v in a.views.split(",") if v.strip()]
        if "top" in views:
            render_view(top, os.path.join(out, f"rtd2027_site_top{tag}.png"), res_x, int(res_x * 2 / 3))
        if "oblique" in views:
            ox = min(res_x, 3840)
            render_view(obl, os.path.join(out, f"rtd2027_site_oblique{tag}.png"), ox, int(ox * 9 / 16))
    log("finished")


def stats(out):
    n_obj = len(bpy.data.objects)
    n_mesh = len(bpy.data.meshes)
    lines = [f"objects: {n_obj}", f"unique meshes: {n_mesh}"]
    for c in COLLECTION_NAMES:
        lines.append(f"  {c}: {len(C(c).all_objects)} objects")
    log("scene stats\n" + "\n".join(lines))


if __name__ == "__main__":
    main()
