"""
The eve of Badr, rendered in Blender from the expedition's own data: an exhibition still and a
relief texture. Blender is a build-time asset factory here, never a source: everything drawn comes
from expeditions/dist/data/badr.json and stars.json, the files the site itself draws from, and the
files it writes are checked against those inputs by blender/check_fresh.py.

Run from the repository root on a Mac with Blender 5.2 (the render is not part of CI):

    /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python-exit-code 1 -P blender/badr_eve.py

It writes, in blender/out/:
    badr-eve.jpg        1920x1080: the valley at 21:39 local solar time on the eve of the tabular
                        candidate day, under the Moon and stars as computed, with the labels and a
                        provenance stamp drawn in
    badr-relief.png     960x960 grey relief of the same ground, lit from the north-west, north up,
                        edge to edge the terrain square; a texture, so no stamp: its provenance is
                        in the manifest
    badr.manifest.json  the inputs fingerprint (blender/inputs.py), the Blender version and the
                        files' sha256

Add `-- --preview DIR` to write half-size test renders to DIR instead, with no manifest.

The still follows the site's 3D view (expeditions/app/world.js) on purpose: the same units (1 unit
is 1 km, heights 2.5 times), the same eye, ground colours, fog and star sizes, so the still and the
live view agree. Only the look direction differs, level and a little to the south, so the Moon is
in frame. What Blender adds is the Moon's cast shadows and a print-size image. Nothing figurative:
no people, no tents, no wells; only the ground, the sky and labels.
"""

from __future__ import annotations

import base64
import json
import math
import sys
from array import array
from pathlib import Path

import bmesh
import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import inputs  # noqa: E402

CANDIDATE, UT = "tabular", "19:04"  # 21:39 local solar time, the Moon 23 degrees up in the east
EX = 2.5                            # height exaggeration, as world.js
EYE_DIST, EYE_PITCH = 11.0, 0.2     # world.js's starting eye: 11 km west of the centre, 0.2 rad up
LOOK_AZ, LOOK_ALT = 95.0, 0.0       # degrees; world.js looks due east and down at the centre
FOV_Y = 55.0
SKY_R = 90.0                        # the star sphere, as world.js
MOON_DEG, MOON_SCALE = 0.52, 2      # mean apparent diameter, and how much larger it is drawn
W, H, BAND = 1920, 1080, 176        # the still, and its stamp band at the bottom
RELIEF = 960
RELIEF_LIGHT = (45.0, 315.0)        # alt, az: the cartographers' north-west light

# world.js's colours are display values; Blender lights in linear ones (see lin()).
GROUND_LOW, GROUND_HIGH = (0.6, 0.49, 0.34), (0.43, 0.36, 0.29)
MOONLIGHT, STARLIGHT, MOON_DISC = (0.74, 0.82, 1.0), (1.0, 0.97, 0.9), (1.0, 0.98, 0.9)
SUNLIGHT = (1.0, 0.9, 0.75)
AMBIENT = 0.09
LAMP = math.pi  # a Blender sun of strength pi lights a white surface facing it to 1.0
INK, MUTED, BAND_RGB = (0.93, 0.91, 0.87), (0.62, 0.64, 0.7), (0.035, 0.04, 0.06)
CLASS_HEX = {"attested": "#e6b450", "located": "#2cb98f", "computed": "#6cb6ff", "schematic": "#9aa3b5"}
STAMP_OFF = ("date", "time", "render_time", "frame", "frame_range", "memory", "hostname", "camera",
             "lens", "scene", "marker", "filename", "sequencer_strip")


def lin(c):
    """A display value as the linear value that renders back to it (gamma 2.2), so products agree."""
    return tuple(v ** 2.2 for v in c)


def hex_rgb(h: str) -> tuple:
    return tuple(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))


def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return min(hi, max(lo, v))


def sky_dir(alt: float, az: float) -> Vector:
    """A direction in the sky (degrees; azimuth from north through east) as a unit vector, Z up."""
    a, z = math.radians(alt), math.radians(az)
    return Vector((math.sin(z) * math.cos(a), math.cos(z) * math.cos(a), math.sin(a)))


def local_time(ut: str, off: int) -> str:
    h, m = map(int, ut.split(":"))
    t = (h * 60 + m + off) % 1440
    return f"{t // 60:02d}:{t % 60:02d}"


def link(ob, coll):
    coll.objects.link(ob)
    return ob


def hidden_from_rays(ob):
    """Seen by the camera only: casts no shadow and lights nothing (the HUD, the Moon, the stars)."""
    for k in ("shadow", "diffuse", "glossy", "transmission", "volume_scatter"):
        setattr(ob, f"visible_{k}", False)


def material(name: str):
    m = bpy.data.materials.new(name)
    if m.node_tree is None:
        m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    return m, nt, nt.nodes.new("ShaderNodeOutputMaterial")


def emission(name: str, rgb, strength: float = 1.0):
    m, nt, out = material(name)
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*rgb, 1)
    e.inputs["Strength"].default_value = strength
    nt.links.new(e.outputs[0], out.inputs["Surface"])
    return m


def world(name: str, rgb, strength: float):
    w = bpy.data.worlds.new(name)
    if w.node_tree is None:
        w.use_nodes = True
    bg = w.node_tree.nodes.get("Background") or w.node_tree.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (*rgb, 1)
    bg.inputs["Strength"].default_value = strength
    return w


def sun_lamp(name: str, d: Vector, rgb, strength: float, coll, angle_deg: float = 0.5):
    lt = bpy.data.lights.new(name, "SUN")
    lt.color, lt.energy, lt.angle = rgb, strength, math.radians(angle_deg)
    ob = link(bpy.data.objects.new(name, lt), coll)
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = d.to_track_quat("Z", "Y")  # a sun lamp shines down its -Z
    return ob


# ---------------------------------------------------------------- the ground


def heights(t: dict) -> array:
    h = array("H", base64.b64decode(t["h"]))
    if sys.byteorder == "big":
        h.byteswap()
    return h


def ground(t: dict, eye: Vector, coll):
    """world.js's terrain mesh in Blender axes (X east, Y north, Z up), with its ground colour and
    distance fog stored per vertex, as world.js computes them per pixel."""
    n, s = t["n"], t["size_km"]
    hs = heights(t)  # metres above base_m, so heights start at 0 as in world.js
    verts = [((i / (n - 1) - 0.5) * s, -(j / (n - 1) - 0.5) * s, hs[j * n + i] / 1000 * EX)
             for j in range(n) for i in range(n)]
    faces = [(a, a + n, a + n + 1, a + 1) for a in (j * n + i for j in range(n - 1) for i in range(n - 1))]
    me = bpy.data.meshes.new("Ground")
    me.from_pydata(verts, [], faces)
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    colour, fog = [], []
    for x, y, z in verts:
        k = clamp(z / 2)
        colour += [*lin(tuple(a + (b - a) * k for a, b in zip(GROUND_LOW, GROUND_HIGH))), 1.0]
        fog.append(clamp(((Vector((x, y, z)) - eye).length - 8) / 40, 0, 0.7))
    me.color_attributes.new("base", "FLOAT_COLOR", "POINT").data.foreach_set("color", colour)
    me.attributes.new("fog", "FLOAT", "POINT").data.foreach_set("value", fog)
    me.update()
    return link(bpy.data.objects.new("Ground", me), coll)


def ground_at(t: dict, hs: array, x: float, z: float) -> float:
    """world.js hAt() at the grid point nearest (x east, z south), as a Blender height."""
    n, s = t["n"], t["size_km"]
    gi = min(n - 1, max(0, round((x / s + 0.5) * (n - 1))))
    gj = min(n - 1, max(0, round((z / s + 0.5) * (n - 1))))
    return hs[gj * n + gi] / 1000 * EX


def night_ground(fog_rgb, ambient: float):
    """Moonlit diffuse plus world.js's flat ambient, faded to the fog colour with distance."""
    m, nt, out = material("Ground at night")
    base = nt.nodes.new("ShaderNodeAttribute")
    base.attribute_name = "base"
    fog = nt.nodes.new("ShaderNodeAttribute")
    fog.attribute_name = "fog"
    lit = nt.nodes.new("ShaderNodeBsdfDiffuse")
    amb = nt.nodes.new("ShaderNodeEmission")
    amb.inputs["Strength"].default_value = ambient
    add = nt.nodes.new("ShaderNodeAddShader")
    haze = nt.nodes.new("ShaderNodeEmission")
    haze.inputs["Color"].default_value = (*fog_rgb, 1)
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(base.outputs["Color"], lit.inputs["Color"])
    nt.links.new(base.outputs["Color"], amb.inputs["Color"])
    nt.links.new(lit.outputs[0], add.inputs[0])
    nt.links.new(amb.outputs[0], add.inputs[1])
    nt.links.new(fog.outputs["Fac"], mix.inputs[0])
    nt.links.new(add.outputs[0], mix.inputs[1])
    nt.links.new(haze.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return m


def white_ground():
    m, nt, out = material("Relief")
    d = nt.nodes.new("ShaderNodeBsdfDiffuse")
    d.inputs["Color"].default_value = (1, 1, 1, 1)
    nt.links.new(d.outputs[0], out.inputs["Surface"])
    return m


# ---------------------------------------------------------------- the sky


def star_field(stars: list, fr: dict, lat: float, dark: float, moon_up: bool, coll):
    """world.js's stars: the same positions, sizes and brightness, as small glowing spheres on the
    sky sphere. Sizes are world.js point sizes taken as pixels of this 1080-high frame."""
    bm = bmesh.new()
    glow = bm.verts.layers.float_color.new("glow")
    px = 2 * SKY_R * math.tan(math.radians(FOV_Y / 2)) / H
    for ra, dec, mag in stars:
        ha, d = math.radians(fr["lst"] - ra), math.radians(dec)
        alt = math.asin(math.sin(lat) * math.sin(d) + math.cos(lat) * math.cos(d) * math.cos(ha))
        if alt < -0.02:
            continue
        az = math.atan2(-math.sin(ha) * math.cos(d), math.cos(lat) * math.sin(d) - math.sin(lat) * math.cos(d) * math.cos(ha))
        size = max(1.8, (5.8 - mag) * 1.5)
        a = min(1, 2.512 ** -(mag - 1.6) * 1.6 + 0.2) * dark * min(1, alt / math.radians(8) + 0.25) * (0.55 if moon_up else 1)
        if a <= 0:
            continue
        p = sky_dir(math.degrees(alt), math.degrees(az)) * SKY_R
        made = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=size * 0.3 * px, matrix=Matrix.Translation(p))
        rgb = lin(tuple(c * a for c in STARLIGHT))
        for v in made["verts"]:
            v[glow] = (*rgb, 1)
    me = bpy.data.meshes.new("Stars")
    bm.to_mesh(me)
    bm.free()
    m, nt, out = material("Starlight")
    at = nt.nodes.new("ShaderNodeAttribute")
    at.attribute_name = "glow"
    e = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(at.outputs["Color"], e.inputs["Color"])
    nt.links.new(e.outputs[0], out.inputs["Surface"])
    me.materials.append(m)
    ob = link(bpy.data.objects.new("Stars", me), coll)
    hidden_from_rays(ob)
    return ob


def moon_disc(md: Vector, coll):
    bm = bmesh.new()
    r = SKY_R * math.tan(math.radians(MOON_DEG * MOON_SCALE / 2))
    bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=24, radius=r, matrix=Matrix.Translation(md * SKY_R))
    me = bpy.data.meshes.new("Moon")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(emission("Moon", lin(MOON_DISC)))
    ob = link(bpy.data.objects.new("Moon", me), coll)
    hidden_from_rays(ob)
    return ob


# ---------------------------------------------------------------- labels and stamp


class Hud:
    """Flat shapes and text on a plane just in front of the camera, placed in pixels from the top
    left of the frame: labels and the stamp drawn into the render, not pasted on afterwards."""

    def __init__(self, cam, coll, depth: float = 0.1):
        self.cam, self.coll, self.d = cam, coll, depth
        self.px = 2 * depth * math.tan(math.radians(FOV_Y / 2)) / H
        self.mats: dict = {}

    def _mat(self, rgb):
        if rgb not in self.mats:
            self.mats[rgb] = emission(f"Ink {len(self.mats)}", lin(rgb))
        return self.mats[rgb]

    def _place(self, ob, x: float, y: float, rgb, behind: float = 1.0):
        ob.parent = self.cam
        ob.location = ((x - W / 2) * self.px, (H / 2 - y) * self.px, -self.d * behind)
        ob.data.materials.append(self._mat(rgb))
        hidden_from_rays(ob)
        return ob

    def text(self, body: str, x: float, y: float, size: float, rgb, align: str = "LEFT", max_w: float = 0) -> float:
        """Text with its vertical middle at y; returns its width in pixels."""
        cu = bpy.data.curves.new("Text", "FONT")
        cu.body, cu.size, cu.align_x, cu.align_y = body, size * self.px, align, "CENTER"
        ob = link(bpy.data.objects.new("Text", cu), self.coll)
        self._place(ob, x, y, rgb)
        bpy.context.view_layer.update()
        w = ob.dimensions.x / self.px
        if max_w and w > max_w:
            ob.scale = (max_w / w,) * 3
            w = max_w
        return w

    def _flat(self, name: str, bm, rgb, x: float, y: float, behind: float = 1.0):
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        ob = link(bpy.data.objects.new(name, me), self.coll)
        return self._place(ob, x, y, rgb, behind)

    def dot(self, x: float, y: float, r: float, rgb):
        bm = bmesh.new()
        bmesh.ops.create_circle(bm, cap_ends=True, segments=32, radius=r * self.px)
        return self._flat("Dot", bm, rgb, x, y)

    def band(self, top: float, rgb):
        bm = bmesh.new()
        hw, hh = W / 2 * self.px * 1.01, (H - top + 20) / 2 * self.px  # runs past the bottom edge
        for p in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)):
            bm.verts.new((*p, 0))
        bm.faces.new(bm.verts)
        return self._flat("Band", bm, rgb, W / 2, (top + H + 20) / 2, behind=1.002)

    def row(self, y: float, parts: list, size: float, x0: float = 44, max_w: float = W - 88):
        """Provenance segments on one line: a class-coloured dot, then the text."""
        x = x0
        for cls, body in parts:
            self.dot(x + 6, y, 6, hex_rgb(CLASS_HEX[cls]))
            x += 20 + self.text(body, x + 20, y, size, INK, max_w=max_w - (x - x0) - 20) + 28


def project(scene, cam, p: Vector):
    """A scene point as frame pixels from the top left, or None when it is off frame or behind."""
    u, v, depth = world_to_camera_view(scene, cam, p)
    if depth <= 0 or not (-0.01 <= u <= 1.01 and -0.01 <= v <= 1.01):
        return None
    return u * W, (1 - v) * H


# ---------------------------------------------------------------- the renders


def scene_setup():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    r = scene.render
    r.use_stamp = False
    r.use_stamp_note = True
    for k in STAMP_OFF:
        if hasattr(r, f"use_stamp_{k}"):
            setattr(r, f"use_stamp_{k}", False)
    return scene


def collection(scene, name: str):
    c = bpy.data.collections.new(name)
    scene.collection.children.link(c)
    return c


def write(scene, path: Path, fmt: str, mode: str, note: str):
    s = scene.render.image_settings
    s.file_format, s.color_mode = fmt, mode
    if fmt == "JPEG":
        s.quality = 90
    else:
        s.color_depth, s.compression = "8", 90
    scene.render.stamp_note_text = note
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    preview = Path(argv[argv.index("--preview") + 1]).resolve() if "--preview" in argv else None
    out = preview or inputs.OUT
    out.mkdir(parents=True, exist_ok=True)

    badr, stars = inputs.load()
    fp = inputs.fingerprint()
    t, sky = badr["world"]["terrain"], badr["sky"]
    cand = next(c for c in sky["candidates"] if c["key"] == CANDIDATE)
    fr = next(f for f in cand["frames"] if f["ut"] == UT)
    local = local_time(UT, cand["local_offset_minutes"])
    lat = math.radians(badr["world"]["anchor"]["lat"])

    scene = scene_setup()
    scene.render.resolution_x, scene.render.resolution_y = W, H
    scene.render.resolution_percentage = 50 if preview else 100
    still, relief_c = collection(scene, "Still"), collection(scene, "Relief")

    # The eye of world.js: west of the centre, looking east.
    hs = heights(t)
    n = t["n"]
    y_c = hs[(n >> 1) * n + (n >> 1)] / 1000 * EX
    eye = Vector((-EYE_DIST * math.cos(EYE_PITCH), 0, y_c + EYE_DIST * math.sin(EYE_PITCH)))
    terrain = ground(t, eye, scene.collection)

    # The sky of world.js for this frame.
    sun_alt, (moon_alt, moon_az) = fr["sun"][0], fr["moon"]
    tw, dark = clamp((sun_alt + 12) / 18), clamp((-sun_alt - 4) / 12)
    fog = (0.015 + 0.3 * tw, 0.02 + 0.38 * tw, 0.045 + 0.55 * tw)
    moon_i = cand["moon_illuminated_pct"] / 100 * min(1, moon_alt / 6) * (1 - tw) if moon_alt > 0 else 0
    sun_i = clamp((sun_alt + 2) / 10)
    md = sky_dir(moon_alt, moon_az)
    night = world("Night", lin(fog), 1.0)
    if moon_i > 0:
        sun_lamp("Moonlight", md, lin(MOONLIGHT), LAMP * (1.15 * moon_i) ** 2.2, still)
    if sun_i > 0:
        sun_lamp("Sunlight", sky_dir(*fr["sun"]), lin(SUNLIGHT), LAMP * (1.05 * sun_i) ** 2.2, still)
    star_field(stars["stars"], fr, lat, dark, moon_alt > 0, still)
    if moon_alt > -1:
        moon_disc(md, still)

    cd = bpy.data.cameras.new("Eye")
    cd.sensor_fit, cd.angle_y, cd.clip_start, cd.clip_end = "VERTICAL", math.radians(FOV_Y), 0.01, 300
    cam = link(bpy.data.objects.new("Eye", cd), still)
    cam.location = eye
    cam.rotation_mode = "QUATERNION"
    cam.rotation_quaternion = sky_dir(LOOK_ALT, LOOK_AZ).to_track_quat("-Z", "Y")
    scene.camera = cam
    bpy.context.view_layer.update()

    # Labels where world.js puts them: places inside the square on the ground, places outside it
    # on the square's edge in their direction, the Moon's height beside the Moon.
    hud = Hud(cam, still)
    s = t["size_km"]
    for lb in badr["world"]["labels"]:
        x, z = lb["x"], lb["z"]
        if not lb["inside"]:
            x, z = math.sin(math.radians(lb["deg"])) * s * 0.47, -math.cos(math.radians(lb["deg"])) * s * 0.47
        at = project(scene, cam, Vector((x, -z, ground_at(t, hs, x, z) + 0.18)))
        if at:
            hud.dot(*at, 5, hex_rgb(CLASS_HEX[lb["class"]]))
            hud.text(lb["name"] if lb["inside"] else f"towards {lb['name']}, {round(lb['km'])} km",
                     at[0], at[1] - 20, 22, INK, align="CENTER")
    at = project(scene, cam, md * SKY_R) if moon_alt > -1 else None
    if at:
        hud.text(f"Moon {round(moon_alt)}° up", at[0], at[1] + 30, 20, INK, align="CENTER")

    # The stamp: what each part of the picture is, by provenance class.
    src, method = badr["source"], sky["method"].split(";")[0]
    top = H - BAND
    hud.band(top, BAND_RGB)
    hud.text(f"{badr['title']}: {local} local solar time, the evening before {cand['day']}, "
             f"the tabular candidate day", 44, top + 30, 26, INK, max_w=W - 88)
    hud.row(top + 66, [("attested", f"Attested: {src['work']}, {sky['page']} (page provisional), says "
                                    f"“{sky['text_en']}”. The day drawn is the tabular candidate, a "
                                    f"{cand['weekday']}; we do not correct the text.")], 18)
    hud.row(top + 94, [("computed", f"Computed: the Moon ({cand['moon_illuminated_pct']}% lit), stars and moonlight by "
                                    f"{method} under the stated crescent rule; the ground from present-day "
                                    f"elevation, heights 2.5 times; the directions to Madinah and Makkah.")], 18)
    hud.row(top + 122, [("located", "Located: Badr, a proposed gazetteer point (al-Thurayya)."),
                        ("schematic", f"Schematic: the labels, and the Moon drawn {MOON_SCALE} times its size. "
                                      "No people are shown.")], 18)
    hud.text(f"al-Marṣad · Blender {bpy.app.version_string} · blender/badr_eve.py from "
             f"expeditions/dist/data · inputs {fp[:12]} · stars HYG v4.1 (CC BY-SA 4.0) · places "
             f"al-Thurayya Project (CC BY 4.0) · terrain Mapzen terrain tiles, from SRTM",
             44, top + 152, 14, MUTED, max_w=W - 88)

    terrain.data.materials.append(night_ground(lin(fog), lin((AMBIENT + 0.35 * sun_i,))[0]))
    scene.world = night
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 16 if preview else 64
    relief_c.hide_render = True
    eve = out / "badr-eve.jpg"
    write(scene, eve, "JPEG", "RGB", f"al-Marṣad: {badr['title']}, {local} local solar time; "
                                     f"rendered from expeditions/dist/data, inputs sha256 {fp}")

    # The relief: the same ground in white, from straight above, lit from the north-west.
    still.hide_render, relief_c.hide_render = True, False
    terrain.data.materials[0] = white_ground()
    scene.world = world("Sky", (1, 1, 1), 0.1)
    sun_lamp("Relief light", sky_dir(*RELIEF_LIGHT), (1, 1, 1), LAMP * 0.8, relief_c, angle_deg=1.0)
    rd = bpy.data.cameras.new("Above")
    rd.type, rd.ortho_scale, rd.clip_start, rd.clip_end = "ORTHO", s, 1, 100
    top_cam = link(bpy.data.objects.new("Above", rd), relief_c)
    top_cam.location = (0, 0, 40)
    scene.camera = top_cam
    scene.render.resolution_x = scene.render.resolution_y = RELIEF
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 32 if preview else 128
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        scene.cycles.device = "GPU"
    except Exception:
        scene.cycles.device = "CPU"
    rel = out / "badr-relief.png"
    write(scene, rel, "PNG", "BW", f"al-Marṣad: {badr['title']} relief from present-day elevation, heights "
                                   f"{EX} times, light from {RELIEF_LIGHT[1]:g}°/{RELIEF_LIGHT[0]:g}°; inputs sha256 {fp}")

    if preview:
        print(f"preview written to {out}")
        return
    manifest = {
        "about": "Blender renders of the eve of Badr, made by blender/badr_eve.py from expeditions/dist/data "
                 "and checked by blender/check_fresh.py. The data is the source; these files are drawn from it.",
        "command": inputs.COMMAND,
        "blender": bpy.app.version_string,
        "inputs_sha256": fp,
        "frame": {"candidate": CANDIDATE, "day": cand["day"], "ut": UT, "local_solar_time": local,
                  "moon_alt_az": fr["moon"], "sun_alt_az": fr["sun"]},
        "outputs": {
            "badr-eve.jpg": {
                "sha256": inputs.file_sha(eve), "pixels": [W, H],
                "shows": "The valley of Badr seen from the west, the Moon and stars as computed, labels, and a provenance stamp.",
                "classes": {
                    "attested": "the date the text gives, quoted in the stamp",
                    "computed": "the Moon, the stars, the moonlight and shadows, the ground (present-day elevation, heights "
                                f"{EX} times), the directions to Madinah and Makkah",
                    "located": "Badr, a proposed gazetteer point",
                    "schematic": f"the labels, the stamp, and the Moon's size ({MOON_SCALE} times)",
                },
            },
            "badr-relief.png": {
                "sha256": inputs.file_sha(rel), "pixels": [RELIEF, RELIEF],
                "shows": f"Grey relief of the terrain square, {s} km a side, north up, the top-left pixel at the "
                         f"north-west corner; lit from azimuth {RELIEF_LIGHT[1]:g}, altitude {RELIEF_LIGHT[0]:g}, with sky light.",
                "classes": {"computed": f"present-day elevation, heights {EX} times; the light is a convention, not the sky of any date"},
            },
        },
        "credits": [
            t["source"],
            "Places: al-Thurayya Project, althurayya.github.io (CC BY 4.0)",
            stars["source"],
            sky["method"],
        ],
    }
    inputs.MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {eve.name}, {rel.name}, {inputs.MANIFEST.name}")


main()
