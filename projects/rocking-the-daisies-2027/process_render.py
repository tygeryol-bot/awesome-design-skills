"""
Rocking the Daisies 2027 - build-process frames
================================================

Builds the festival site with the same functions as festival_site.py, in the
brief's build order, records which objects every stage creates, and renders
one still per build step from the elevated orthographic camera. Objects are
revealed cumulatively, so the frames show the site model being assembled.
process_compose.py turns the frames into the process video.

Until stage 8 the frames are lit by a flat, neutral "workshop" light; the sun
and sky only arrive in stage 8 - the same point at which festival_site.py
creates its lights and cameras.

Run (Blender 4.2+ / 5.x, or the pip `bpy` module):
    blender --background --python process_render.py -- --out ./output/process_frames
    python process_render.py --out ./output/process_frames         # pip bpy
Options: --res 1920 (width, 16:9)  --samples 12  --seed 2027
         --only 1,2   re-render just these step indices (manifest is rewritten)
"""

import argparse
import json
import os
import sys
import time

import bpy  # noqa: E402  (bpy must be imported before bpy_extras in the pip module)
import numpy as np
from bpy_extras.object_utils import world_to_camera_view

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import festival_site as fs  # noqa: E402

STAGES = {
    0: "Planning",
    1: "Terrain and site boundaries",
    2: "Dam, roads and walking paths",
    3: "Main arena and stages",
    4: "Camping zones and tents",
    5: "Parking and entrances",
    6: "Trees and natural landscaping",
    7: "Facilities and smaller structures",
    8: "Materials, lighting and camera",
    9: "Final render",
}


def parse_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    elif os.path.basename(argv[0]).lower().startswith("blender"):
        argv = []
    else:
        argv = argv[1:]
    p = argparse.ArgumentParser()
    p.add_argument("--out", default=os.path.join(HERE, "output", "process_frames"))
    p.add_argument("--res", type=int, default=1920)
    p.add_argument("--samples", type=int, default=12)
    p.add_argument("--seed", type=int, default=fs.CONFIG["seed"])
    p.add_argument("--only", default="", help="comma-separated step indices to (re)render")
    a, _ = p.parse_known_args(argv)
    return a


def recorded(fn, *args):
    """Run a build function and return the objects it created."""
    before = set(bpy.data.objects.keys())
    fn(*args)
    return [o for o in bpy.data.objects if o.name not in before]


def split(objs, k, key):
    """Split objects into k spatially ordered chunks (reveal sweeps)."""
    objs = sorted(objs, key=key)
    return [list(c) for c in np.array_split(np.array(objs, dtype=object), k) if len(c)]


def named(objs, *prefixes):
    return [o for o in objs if o.name.startswith(prefixes)]


def not_named(objs, *prefixes):
    return [o for o in objs if not o.name.startswith(prefixes)]


def in_coll(objs, *names):
    return [o for o in objs if o.users_collection and o.users_collection[0].name in names]


def build_and_plan_steps(seed):
    fs.reset_scene()
    for n in fs.COLLECTION_NAMES:
        fs.C(n)
    fs.build_materials()
    P = fs.make_plan(seed)
    terrain = recorded(fs.build_terrain, P)
    lake = recorded(fs.build_lake, P)
    # excavated basin floor, so the terrain step shows a dug-out dam instead of
    # an open hole into the hollow plinth (hidden under the water afterwards)
    basin = fs.slab("Lake_Basin_Floor", fs.offset_poly(P.lake, 4.6), -0.7, -1.2,
                    fs.MATS["shore_mud"], fs.C("Lake"))
    roads = recorded(fs.build_roads_paths, P)
    grounds = recorded(fs.build_grounds, P)
    park_ground = recorded(fs.build_parking_ground, P)
    fs.index_paths(P)
    fs.build_assets()
    fs.plan_facilities(P)
    main = recorded(fs.build_main_stage, P)
    west = recorded(fs.build_secondary_stage, P, "west")
    east = recorded(fs.build_secondary_stage, P, "east")
    arena = recorded(fs.build_arena_details, P)
    parking = recorded(fs.build_parking, P)
    entrances = recorded(fs.build_entrances, P)
    fs.plan_trees(P)
    camping = recorded(fs.build_camping, P)
    veg = recorded(fs.build_vegetation, P)
    lake_feat = recorded(fs.build_lake_features, P)
    clearing = recorded(fs.build_clearing, P)
    facilities = recorded(fs.build_facilities, P)

    x_key = lambda o: o.location.x                                  # noqa: E731
    y_key = lambda o: -o.location.y                                 # noqa: E731
    edge_key = lambda o: min(o.location.x - fs.X0, fs.X1 - o.location.x,   # noqa: E731
                             o.location.y - fs.Y0, fs.Y1 - o.location.y)
    yards = named(grounds, "Production_Medical_Yard", "Waste_Recycling_Depot_Yard")
    hard = named(grounds, "Entrance_Plaza", "Priority_DropOff")
    zone_grounds = named(grounds, "Ground_")
    food = named(arena, "Food_Stall", "Food_Truck", "Bar_Stretch", "Picnic", "Hay_Bale", "Waste_Recycling_Bins")
    vehicles = named(parking, "Car.", "Van.", "Shuttle_Bus", "Tree_")
    trees = named(veg, "Tree_")

    S = []  # (stage, caption, objects revealed at this step)
    S.append((0, "Display base and the planning pass: zones, routes and occupancy masks",
              named(terrain, "Display_Base")))
    S.append((1, "1000 x 660 m terrain on a model plinth, with the dam basin cut out",
              not_named(terrain, "Display_Base") + [basin] + named(lake, "Lake_Shore")))
    S.append((2, "Dam: water surface with depth gradient", named(lake, "Lake_Water")))
    S.append((2, "Public access road, markings and asphalt spurs", named(roads, "Access_")))
    S.append((2, "Gravel service and emergency routes", named(roads, "Service_")))
    S.append((2, "Pedestrian path network", named(roads, "Walking_", "Glamping_Paths")))
    S.append((3, "Arena ground", named(grounds, "Arena_Sand")))
    S.append((3, "Main stage: deck, truss roof, PA, screens and lighting rig", main))
    S.append((3, "Secondary stages: arched shell and gable roof", west + east))
    S.append((3, "Arena fence, FOH, delay towers, lighting and services", [o for o in arena if o not in food]))
    S.append((3, "Food courts, bars and seating", food))
    S.append((4, "Camping grounds", zone_grounds))
    cg = in_coll(camping, "Camping General")
    for i, c in enumerate(split(cg, 3, x_key)):
        S.append((4, f"General camping - tent rows ({i + 1}/3)", c))
    for i, c in enumerate(split(in_coll(camping, "Camping Wildflower"), 2, x_key)):
        S.append((4, f"Wildflower camping - friend-group camps ({i + 1}/2)", c))
    for i, c in enumerate(split(in_coll(camping, "Camping Priority"), 2, y_key)):
        S.append((4, f"Priority camping - spaced pitches ({i + 1}/2)", c))
    for i, c in enumerate(split(in_coll(camping, "Glamping Village"), 2, y_key)):
        S.append((4, f"Pre-pitched and glamping village ({i + 1}/2)", c))
    S.append((5, "Car parks, entrance plaza and shuttle loop", park_ground + hard))
    S.append((5, "Parking bays, planted islands and shuttle stops", [o for o in parking if o not in vehicles]))
    for i, c in enumerate(split(vehicles, 2, x_key)):
        S.append((5, f"Vehicles ({i + 1}/2)", c))
    S.append((5, "Main and priority entrances", entrances))
    for i, c in enumerate(split(trees, 4, edge_key)):
        S.append((6, f"Woodland belt and tree clusters ({i + 1}/4)", c))
    S.append((6, "Shrubs, wildflower mounds, reeds and rocks", not_named(veg, "Tree_")))
    S.append((6, "Jetty, beach and the clearing", lake_feat + clearing))
    S.append((7, "Production, medical and waste compounds", yards + in_coll(facilities, "Facilities")))
    S.append((7, "Toilets, showers, water points and info in the camps",
              [o for o in facilities if o not in in_coll(facilities, "Facilities")]))
    covered = {o.name for _, _, objs in S for o in objs}
    leftovers = [o for o in bpy.data.objects if o.type == "MESH" and o.name not in covered
                 and not o.name.startswith("ASSET_")]
    if leftovers:
        S[-1] = (S[-1][0], S[-1][1], S[-1][2] + leftovers)
    return P, S


def plan_overlay(P, cam, sc, W, H):
    """Site plan projected into the oblique camera (pixel-space shapes)."""
    def proj(pts, z=0.0):
        out = []
        for x, y in pts:
            v = world_to_camera_view(sc, cam, fs.Vector((x, y, z)))
            out.append((round(v.x * W, 2), round((1 - v.y) * H, 2)))
        return out

    def ribbon_quads(pts, w, closed=False):
        Pt = np.asarray(pts, dtype=float)
        if closed:
            T = np.roll(Pt, -1, 0) - np.roll(Pt, 1, 0)
        else:
            T = np.gradient(Pt, axis=0)
        T /= np.linalg.norm(T, axis=1)[:, None] + 1e-9
        N = np.stack([-T[:, 1], T[:, 0]], 1) * w / 2
        L, R = proj(Pt + N), proj(Pt - N)
        n = len(Pt) if closed else len(Pt) - 1
        return [[L[i], L[(i + 1) % len(Pt)], R[(i + 1) % len(Pt)], R[i]] for i in range(n)]

    shapes = []
    shapes.append(("site", proj([(fs.X0, fs.Y0), (fs.X1, fs.Y0), (fs.X1, fs.Y1), (fs.X0, fs.Y1)])))
    for x in range(int(fs.X0), int(fs.X1) + 1, 50):
        shapes.append(("grid", proj([(x, fs.Y0), (x, fs.Y1)])))
    for y in range(int(fs.Y0) + 30, int(fs.Y1), 50):
        shapes.append(("grid", proj([(fs.X0, y), (fs.X1, y)])))
    for k, poly in P.zones.items():
        shapes.append((f"zone_{k}", proj(poly)))
    shapes.append(("arena", proj(P.arena)))
    shapes.append(("lake", proj(P.lake)))
    for lot in (fs.LOT_A, fs.LOT_B, fs.STAFF_LOT):
        shapes.append(("lot", proj(fs.rounded_rect(*lot, 6))))
    shapes.append(("plaza", proj(fs.PLAZA)))
    for r in (fs.COMPOUND, fs.WASTE_DEPOT):
        shapes.append(("yard", proj(fs.rounded_rect(*r, 4))))
    shapes.append(("lot", proj(fs.ellipse(*fs.SHUTTLE_C, fs.SHUTTLE_R + 5, fs.SHUTTLE_R + 5, n=48))))
    for q in ribbon_quads(fs.ROAD_PTS, fs.ROAD_W):
        shapes.append(("road", q))
    for n, pts, w in P.spurs:
        shapes += [("road", q) for q in ribbon_quads(pts, w)]
    for n, pts, w in P.service:
        shapes += [("service", q) for q in ribbon_quads(pts, w)]
    for n, pts, w in P.paths:
        shapes += [("path", q) for q in ribbon_quads(pts, w, n in P.closed)]
    for n, pts, w in P.glamp_paths:
        shapes += [("path", q) for q in ribbon_quads(pts, w, n == "glamp_loop")]
    return shapes


def main():
    a = parse_args()
    os.makedirs(a.out, exist_ok=True)
    P, steps = build_and_plan_steps(a.seed)
    top, obl = fs.build_lighting_camera()
    W, H = a.res, int(a.res * 9 / 16)
    fs.setup_render(a.samples, W, H)
    sc = bpy.context.scene
    sc.camera = obl
    sc.render.use_persistent_data = True
    sc.cycles.adaptive_threshold = 0.05
    sc.render.filepath = ""
    # flat neutral workshop light for the build steps (stage 8 brings the sun)
    sun = bpy.data.objects["Sun"]
    bg = next(n for n in sc.world.node_tree.nodes if n.bl_idname == "ShaderNodeBackground")
    final_light = (tuple(bg.inputs["Color"].default_value), bg.inputs["Strength"].default_value)
    sun.hide_render = True
    bg.inputs["Color"].default_value = fs.col("#f4f3f0")
    bg.inputs["Strength"].default_value = 1.75

    bpy.context.view_layer.update()          # camera matrix_world must be current for projection
    revealable = [o for _, _, objs in steps for o in objs]
    for o in revealable:
        o.hide_render = True
    manifest = {"width": W, "height": H, "stages": STAGES, "steps": [],
                "plan": plan_overlay(P, obl, sc, W, H)}
    only = {int(k) for k in a.only.split(",") if k.strip()}
    for i, (stage, caption, objs) in enumerate(steps):
        for o in objs:
            o.hide_render = False
        path = os.path.join(a.out, f"step_{i:02d}.png")
        if not only or i in only:
            sc.render.filepath = path
            t = time.time()
            bpy.ops.render.render(write_still=True)
            fs.log(f"step {i:02d} [stage {stage}] {caption} - {len(objs)} objects, {time.time() - t:.0f}s")
        manifest["steps"].append({"file": os.path.basename(path), "stage": stage, "caption": caption,
                                  "objects": len(objs)})
    # stage 8: final materials, sun and sky
    sun.hide_render = False
    bg.inputs["Color"].default_value = final_light[0]
    bg.inputs["Strength"].default_value = final_light[1]
    path = os.path.join(a.out, f"step_{len(steps):02d}.png")
    if not only or len(steps) in only:
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
    manifest["steps"].append({"file": os.path.basename(path), "stage": 8,
                              "caption": "Sun, sky and colour management applied", "objects": 0})
    with open(os.path.join(a.out, "manifest.json"), "w") as f:
        json.dump(manifest, f)
    fs.log(f"wrote {len(manifest['steps'])} frames and manifest to {a.out}")


if __name__ == "__main__":
    main()
