"""
Rocking the Daisies 2027 - build-process video
===============================================

Turns the frames rendered by process_render.py into an MP4 timelapse of the
site model being built:

  planning diagram (zones, routes, footprints, projected into the camera view)
  -> every build step dissolving into the next (stages 1-7)
  -> stage 8: the sun, sky and final colour management arrive
  -> camera move to the final top-down 4800 x 3200 render, with a slow
     zoom over the arena and the glamping village (stage 9)

Writes two files: a clean version with no text at all, and a version with
small stage captions and a progress bar.

Needs: Python 3 with numpy + Pillow, and ffmpeg on PATH.
    python3 process_compose.py --frames ./output/process_frames \
        --final ./output/rtd2027_site_top.png --out ./output/process
"""

import argparse
import json
import os
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FPS = 30

PLAN_STYLE = {   # fill, outline
    "site": ("#f1eee6", None),
    "grid": (None, "#dcd7cb"),
    "zone_general": ("#b9aed0", "#9a8db5"),
    "zone_wildflower": ("#bcd3a4", "#97b47c"),
    "zone_priority": ("#dfcb8c", "#c2a95f"),
    "zone_glamping": ("#dfb6aa", "#c3907f"),
    "zone_clearing": ("#b0cd92", "#8fae70"),
    "arena": ("#e8d6a9", "#c9b07a"),
    "lake": ("#86b7cf", "#4d84a6"),
    "lot": ("#a8abae", None),
    "plaza": ("#cfc5b2", None),
    "yard": ("#bdb6a8", None),
    "road": ("#62666b", None),
    "service": ("#9d978b", None),
    "path": ("#c6a266", None),
}
PLAN_LAYERS = [
    ("site", "grid"),
    ("zone_general", "zone_wildflower", "zone_priority", "zone_glamping", "zone_clearing", "arena", "lake"),
    ("lot", "plaza", "yard", "road", "service", "path"),
]


def ease(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def font(size, weight="Regular"):
    for path in (f"/usr/share/fonts/opentype/inter/Inter-{weight}.otf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size)


def draw_plan(base, shapes, upto, ss=2):
    """Composite plan layers 0..upto onto `base` (anti-aliased by supersampling)."""
    W, H = base.size
    layer = Image.new("RGBA", (W * ss, H * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    wanted = set(k for L in PLAN_LAYERS[:upto + 1] for k in L)
    for kind in [k for L in PLAN_LAYERS for k in L]:
        if kind not in wanted:
            continue
        fill, outline = PLAN_STYLE[kind]
        for k, pts in shapes:
            if k != kind:
                continue
            P = [(x * ss, y * ss) for x, y in pts]
            if kind == "grid":
                d.line(P, fill=outline, width=ss)
            else:
                d.polygon(P, fill=fill, outline=outline, width=2 * ss if outline else 0)
    layer = layer.resize((W, H), Image.LANCZOS)
    out = base.convert("RGBA")
    out.alpha_composite(layer)
    return out.convert("RGB")


class Output:
    def __init__(self, path, W, H):
        self.p = subprocess.Popen(
            ["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
             "-crf", "19", "-pix_fmt", "yuv420p", "-movflags", "+faststart", path],
            stdin=subprocess.PIPE)

    def write(self, arr):
        self.p.stdin.write(arr.tobytes())

    def close(self):
        self.p.stdin.close()
        self.p.wait()


class Captioner:
    def __init__(self, W, H, stages, total_steps):
        self.W, self.H = W, H
        self.stages = stages
        self.total = total_steps
        k = W / 1920
        self.k = k
        self.f_title = font(int(15 * k), "SemiBold")
        self.f_stage = font(int(26 * k), "SemiBold")
        self.f_cap = font(int(21 * k), "Regular")
        self.cache = {}

    def overlay(self, stage, caption, progress):
        key = (stage, caption, round(progress, 3))
        if key in self.cache:
            return self.cache[key]
        W, H, k = self.W, self.H, self.k
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.text((int(40 * k), int(30 * k)), "ROCKING THE DAISIES 2027  ·  CONCEPTUAL SITE MODEL  ·  BUILD PROCESS",
               font=self.f_title, fill=(40, 40, 40, 200))
        label = f"STAGE {stage}  ·  {self.stages[str(stage)].upper()}" if stage else "PLANNING"
        tw = max(d.textlength(label, font=self.f_stage), d.textlength(caption, font=self.f_cap))
        x0, y1 = int(40 * k), H - int(46 * k)
        y0 = y1 - int(92 * k)
        d.rounded_rectangle((x0, y0, x0 + tw + int(48 * k), y1), radius=int(10 * k), fill=(250, 249, 246, 225))
        d.text((x0 + int(24 * k), y0 + int(16 * k)), label, font=self.f_stage, fill=(34, 34, 34, 255))
        d.text((x0 + int(24 * k), y0 + int(52 * k)), caption, font=self.f_cap, fill=(85, 85, 85, 255))
        bh = max(3, int(5 * k))
        d.rectangle((0, H - bh, W, H), fill=(0, 0, 0, 30))
        d.rectangle((0, H - bh, int(W * progress), H), fill=(46, 46, 46, 190))
        arr = np.asarray(im).astype(np.float32)
        self.cache = {key: arr}          # one entry is enough: captions change rarely
        return arr

    def apply(self, frame, stage, caption, progress):
        o = self.overlay(stage, caption, progress)
        a = o[..., 3:4] / 255.0
        return (frame.astype(np.float32) * (1 - a) + o[..., :3] * a).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", default=os.path.join(HERE, "output", "process_frames"))
    ap.add_argument("--final", default=os.path.join(HERE, "output", "rtd2027_site_top.png"))
    ap.add_argument("--out", default=os.path.join(HERE, "output", "process"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    man = json.load(open(os.path.join(a.frames, "manifest.json")))
    W, H = man["width"], man["height"]
    steps = man["steps"]
    imgs = [np.asarray(Image.open(os.path.join(a.frames, s["file"])).convert("RGB")) for s in steps]

    # planning diagram, built up in three layers on the empty display base
    base = Image.fromarray(imgs[0])
    plans = [np.asarray(draw_plan(base, man["plan"], i)) for i in range(len(PLAN_LAYERS))]

    # final top-down render, viewed through a moving 16:9 window
    still = Image.open(a.final).convert("RGB")
    SW, SH = still.size
    bgc = still.getpixel((8, 8))
    pad = max(SW, SH)
    canvas = Image.new("RGB", (SW + 2 * pad, SH + 2 * pad), bgc)
    canvas.paste(still, (pad, pad))
    ppm = SW / 1075.0                                   # top camera: 1075 m across the frame

    def world_px(x, y):
        return SW / 2 + x * ppm, SH / 2 - (y + 2.0) * ppm

    fit = H / SH

    def view(cx, cy, s):
        w, h = W / s, H / s
        box = (pad + cx - w / 2, pad + cy - h / 2, pad + cx + w / 2, pad + cy + h / 2)
        return np.asarray(canvas.resize((W, H), Image.LANCZOS, box=box, reducing_gap=2.0))

    shots = {"full": (SW / 2, SH / 2, fit),
             "arena": (*world_px(0, 20), fit * 2.6),
             "glamping": (*world_px(330, -120), fit * 2.6)}

    outs = {"clean": Output(os.path.join(a.out, "rtd2027_build_process.mp4"), W, H),
            "captioned": Output(os.path.join(a.out, "rtd2027_build_process_captioned.mp4"), W, H)}
    cap = Captioner(W, H, man["stages"], len(steps))
    state = {"stage": 0, "caption": steps[0]["caption"], "progress": 0.0, "n": 0}

    def emit(frame):
        outs["clean"].write(frame)
        outs["captioned"].write(cap.apply(frame, state["stage"], state["caption"], state["progress"]))
        state["n"] += 1

    def hold(img, n):
        for _ in range(n):
            emit(img)

    def fade(a_img, b_img, n):
        A, B = a_img.astype(np.float32), b_img.astype(np.float32)
        for i in range(n):
            t = ease((i + 1) / n)
            emit((A * (1 - t) + B * t).astype(np.uint8))

    def move(s0, s1, n):
        for i in range(n):
            t = ease((i + 1) / n)
            cx = s0[0] + (s1[0] - s0[0]) * t
            cy = s0[1] + (s1[1] - s0[1]) * t
            s = s0[2] * (s1[2] / s0[2]) ** t         # geometric zoom feels linear
            emit(view(cx, cy, s))

    def set_step(i):
        state.update(stage=steps[i]["stage"], caption=steps[i]["caption"], progress=i / (len(steps) + 1))

    # 0 - planning
    set_step(0)
    hold(imgs[0], 15)
    fade(imgs[0], plans[0], 20)
    hold(plans[0], 20)
    for k in (1, 2):
        fade(plans[k - 1], plans[k], 20)
        hold(plans[k], 30 if k == 2 else 20)
    # 1-7 - build steps
    prev = plans[-1]
    for i in range(1, len(steps) - 1):
        set_step(i)
        new_stage = steps[i]["stage"] != steps[i - 1]["stage"]
        fade(prev, imgs[i], 30 if i == 1 else 14)
        hold(imgs[i], 30 if new_stage else 14)
        prev = imgs[i]
    # 8 - lighting
    set_step(len(steps) - 1)
    fade(prev, imgs[-1], 45)
    hold(imgs[-1], 45)
    # 8 - camera: to the top-down orthographic view
    state.update(caption="Top-down orthographic camera", progress=len(steps) / (len(steps) + 1))
    full = view(*shots["full"])
    fade(imgs[-1], full, 36)
    hold(full, 24)
    # 9 - final render, slow zoom
    state.update(stage=9, caption="Final 4800 x 3200 Cycles render", progress=1.0)
    hold(full, 12)
    move(shots["full"], shots["arena"], 120)
    hold(view(*shots["arena"]), 24)
    move(shots["arena"], shots["glamping"], 96)
    hold(view(*shots["glamping"]), 24)
    move(shots["glamping"], shots["full"], 96)
    hold(full, 60)
    for o in outs.values():
        o.close()
    print(f"wrote {state['n']} frames ({state['n'] / FPS:.1f}s) to {a.out}")


if __name__ == "__main__":
    main()
