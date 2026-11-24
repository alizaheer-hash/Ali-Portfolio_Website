"""
Builds the portfolio avatar in Blender (run headless or from Blender's Scripting tab).

    python build_avatar.py            # writes ali_avatar.blend, avatar.glb and preview renders

A stylised low-poly half-body character: short dark swept-up hair, round dark glasses, trimmed beard,
charcoal suit, white shirt, purple tie. Rigged with a small armature and two looping animations:
"Idle" (breathing + gentle head movement) and "Wave" (right arm waves, then returns).

Axes: the character faces -Y in Blender, which becomes +Z (towards the camera) in glTF.
Origin is at the bottom of the torso; total height is about 3.25 units.
"""
import math
import os
import sys

import bpy
import bmesh
from mathutils import Euler, Vector

OUT_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
GLB_PATH = os.environ.get("AVATAR_GLB", os.path.join(OUT_DIR, "avatar.glb"))
BLEND_PATH = os.path.join(OUT_DIR, "ali_avatar.blend")

# ----------------------------------------------------------------------------- scene reset
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = 24

# ----------------------------------------------------------------------------- materials
def hex_to_linear(h):
    h = h.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (*out, 1.0)


def make_material(name, hex_color, roughness=0.8, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = hex_to_linear(hex_color)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    mat.diffuse_color = hex_to_linear(hex_color)
    return mat


M = {
    "skin": make_material("Skin", "#B08064"),
    "skin_dark": make_material("SkinShade", "#8E5B45"),
    "hair": make_material("Hair", "#0F0B09", 0.55),
    "beard": make_material("Beard", "#241B17", 0.9),
    "suit": make_material("Suit", "#27323D", 0.85),
    "suit_light": make_material("SuitLapel", "#323F4C", 0.85),
    "shirt": make_material("Shirt", "#EFEBE4", 0.7),
    "tie": make_material("Tie", "#3C2B5E", 0.55),
    "tie_dot": make_material("TieDots", "#8C7BB5", 0.55),
    "frame": make_material("GlassesFrame", "#0E0E12", 0.25, 0.3),
    "eye": make_material("Eye", "#0B0A0A", 0.3),
    "strap": make_material("WatchStrap", "#9A6B3F", 0.6),
    "watch": make_material("WatchFace", "#D9DDE2", 0.25, 0.8),
    "button": make_material("Button", "#12171C", 0.4),
    "lip": make_material("Lip", "#8B4A3F", 0.7),
}

# ----------------------------------------------------------------------------- mesh helpers
parts = {}  # bone name -> list of objects


def add(obj, bone, mat):
    obj.data.materials.clear()
    obj.data.materials.append(M[mat])
    for p in obj.data.polygons:
        p.use_smooth = False
    parts.setdefault(bone, []).append(obj)
    return obj


def new_object(name, bm):
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def box(name, size, loc, bone, mat, rot=(0, 0, 0)):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    obj = new_object(name, bm)
    obj.rotation_euler = Euler(rot)
    obj.location = loc
    return add(obj, bone, mat)


def blob(name, scale, loc, bone, mat, subdiv=2, rot=(0, 0, 0)):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
    bmesh.ops.scale(bm, vec=scale, verts=bm.verts)
    obj = new_object(name, bm)
    obj.rotation_euler = Euler(rot)
    obj.location = loc
    return add(obj, bone, mat)


def limb(name, p1, p2, r1, r2, bone, mat, segments=8):
    p1, p2 = Vector(p1), Vector(p2)
    d = p2 - p1
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=segments, radius1=r1, radius2=r2, depth=d.length)
    obj = new_object(name, bm)
    obj.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    obj.location = (p1 + p2) / 2
    return add(obj, bone, mat)


def prism(name, pts_xz, y, thickness, bone, mat):
    """Flat polygon (given as x,z points) extruded along Y."""
    bm = bmesh.new()
    front = [bm.verts.new((x, y - thickness / 2, z)) for x, z in pts_xz]
    back = [bm.verts.new((x, y + thickness / 2, z)) for x, z in pts_xz]
    bm.faces.new(front)
    bm.faces.new(list(reversed(back)))
    n = len(pts_xz)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((front[i], front[j], back[j], back[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return add(new_object(name, bm), bone, mat)


def bevel_obj(obj, width, segments=1):
    bpy.context.view_layer.objects.active = obj
    mod = obj.modifiers.new("bevel", "BEVEL")
    mod.width = width
    mod.segments = segments
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=mod.name)


# ----------------------------------------------------------------------------- body (suit jacket + shirt + tie)
HEAD_C = Vector((0, 0, 2.62))

# Jacket torso: wider at the shoulders than the waist.
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=1.0)
for v in bm.verts:
    top = v.co.z > 0
    v.co.x *= 1.72 if top else 1.34
    v.co.y *= 0.82 if top else 0.72
    v.co.z = 1.95 if top else 0.0
torso = new_object("Jacket", bm)
bevel_obj(torso, 0.14)
add(torso, "Spine", "suit")

# Shoulder caps so the jacket line is not a hard box.
for sx in (-1, 1):
    blob(f"ShoulderCap{'L' if sx > 0 else 'R'}", (0.25, 0.29, 0.19), (sx * 0.84, 0, 1.78), "Spine", "suit", subdiv=1)

# Shirt V and lapels on the front (character faces -Y).
box("ShirtV", (0.62, 0.03, 1.1), (0, -0.425, 1.42), "Spine", "shirt")
for sx in (-1, 1):
    side = "L" if sx > 0 else "R"
    prism(f"Lapel{side}", [(sx * 0.10, 1.97), (sx * 0.30, 1.99), (sx * 0.62, 1.84), (sx * 0.46, 1.66), (sx * 0.34, 1.52), (sx * 0.08, 0.88)],
          -0.445, 0.045, "Spine", "suit_light")
# Collar flaps and neck opening.
for sx in (-1, 1):
    box(f"Collar{'L' if sx > 0 else 'R'}", (0.22, 0.2, 0.1), (sx * 0.15, -0.2, 1.98), "Spine", "shirt", rot=(0.0, 0.0, sx * -0.5))
# Tie: knot, blade, and a few pattern dots.
box("TieKnot", (0.16, 0.08, 0.14), (0, -0.445, 1.88), "Spine", "tie")
bm = bmesh.new()
pts = [(-0.08, 1.8), (0.08, 1.8), (0.14, 1.05), (0.0, 0.88), (-0.14, 1.05)]
vs = [bm.verts.new((x, -0.46, z)) for x, z in pts]
vb = [bm.verts.new((x, -0.435, z)) for x, z in pts]
bm.faces.new(vs)
bm.faces.new(list(reversed(vb)))
for i in range(5):
    j = (i + 1) % 5
    bm.faces.new((vs[i], vs[j], vb[j], vb[i]))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
add(new_object("TieBlade", bm), "Spine", "tie")
for i, (x, z) in enumerate([(-0.03, 1.62), (0.04, 1.45), (-0.04, 1.3), (0.03, 1.15), (0.0, 1.0)]):
    blob(f"TieDot{i}", (0.025, 0.012, 0.035), (x, -0.468, z), "Spine", "tie_dot", subdiv=1)
# Jacket buttons and a pocket flap.
for i, z in enumerate((0.72, 0.28)):
    limb(f"Button{i}", (0.0, -0.44, z), (0.0, -0.47, z), 0.045, 0.045, "Spine", "button", 8).rotation_euler = Euler((math.pi / 2, 0, 0))
box("PocketFlap", (0.34, 0.03, 0.07), (-0.45, -0.43, 0.88), "Spine", "suit_light")

# ----------------------------------------------------------------------------- neck
limb("Neck", (0, -0.02, 1.8), (0, -0.02, 2.14), 0.19, 0.17, "Neck", "skin", 10)

# ----------------------------------------------------------------------------- head
bm = bmesh.new()
bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
for v in bm.verts:
    v.co.x *= 0.52
    v.co.y *= 0.55
    v.co.z *= 0.62
    if v.co.z < 0:  # taper to a narrower jaw and chin
        k = 1 + v.co.z * 0.55
        v.co.x *= k
        v.co.y *= 0.78 + 0.22 * k
head = new_object("Head", bm)
head.location = HEAD_C
add(head, "Head", "skin")

# Hair: short sides, volume on top swept back, with a quiff.
bm = bmesh.new()
bmesh.ops.create_icosphere(bm, subdivisions=4, radius=1.0)
for v in bm.verts:
    v.co.x *= 0.575
    v.co.y *= 0.60
    v.co.z *= 0.70
    v.co.y += 0.05
    v.co.z += 0.10
    if v.co.z > 0.25:  # extra height on top, more at the front: a swept-up quiff
        v.co.z += 0.03 + 0.06 * max(0.0, -v.co.y)
doomed = []
for f in bm.faces:
    c = f.calc_center_median()
    gz = c.z + HEAD_C.z  # world z
    keep = (gz > 3.0) or (c.y > 0.05 and gz > 2.52) or (abs(c.x) > 0.36 and gz > 2.76 and c.y > -0.30)
    if not keep:
        doomed.append(f)
bmesh.ops.delete(bm, geom=doomed, context="FACES")
bm.verts.ensure_lookup_table()
for v in bm.verts:  # straighten the cut edge into a clean front hairline
    if v.is_boundary and v.co.y < -0.12:
        v.co.z = (2.97 - 0.55 * max(0.0, abs(v.co.x) - 0.30)) - HEAD_C.z
hair = new_object("HairCap", bm)
hair.location = HEAD_C
add(hair, "Head", "hair")
# Swept-up pompadour: a rounded wedge drawn from a side profile (y, z), rising at the front and sweeping back.
profile = [(-0.50, 2.95), (-0.60, 3.12), (-0.50, 3.32), (-0.18, 3.43), (0.22, 3.40), (0.42, 3.22), (0.40, 2.95)]
bmq = bmesh.new()
left = [bmq.verts.new((-0.36, y, z)) for y, z in profile]
right = [bmq.verts.new((0.36, y, z)) for y, z in profile]
bmq.faces.new(left)
bmq.faces.new(list(reversed(right)))
for i in range(len(profile)):
    j = (i + 1) % len(profile)
    bmq.faces.new((left[i], left[j], right[j], right[i]))
bmesh.ops.recalc_face_normals(bmq, faces=bmq.faces)
quiff = new_object("Pompadour", bmq)
bevel_obj(quiff, 0.09, 2)
add(quiff, "Head", "hair")

# Beard: a shell hugging the jaw, plus moustache; lips sit proud of it.
bm = bmesh.new()
bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0)
for v in bm.verts:
    v.co.x *= 0.535
    v.co.y *= 0.565
    v.co.z *= 0.635
    if v.co.z < 0:
        k = 1 + v.co.z * 0.55
        v.co.x *= k
        v.co.y *= 0.78 + 0.22 * k
doomed = []
for f in bm.faces:
    c = f.calc_center_median()
    gz = c.z + HEAD_C.z
    keep = gz < (2.36 - 0.12 * max(0.0, abs(c.x) - 0.25) * 4) and c.y < 0.12 and gz > 1.93
    if not keep:
        doomed.append(f)
bmesh.ops.delete(bm, geom=doomed, context="FACES")
beard = new_object("Beard", bm)
beard.location = HEAD_C
add(beard, "Head", "beard")
box("Moustache", (0.24, 0.045, 0.05), (0, -0.525, 2.415), "Head", "beard", rot=(0.15, 0, 0))
box("Lips", (0.15, 0.03, 0.03), (0, -0.535, 2.33), "Head", "lip")

# Face details.
cone = limb("Nose", (0, -0.47, 2.60), (0, -0.60, 2.50), 0.075, 0.03, "Head", "skin", 4)
for sx in (-1, 1):
    blob(f"Eye{'L' if sx > 0 else 'R'}", (0.045, 0.02, 0.05), (sx * 0.2, -0.50, 2.69), "Head", "eye", subdiv=1)
    box(f"Brow{'L' if sx > 0 else 'R'}", (0.2, 0.035, 0.045), (sx * 0.2, -0.50, 2.81), "Head", "hair", rot=(0, sx * -0.12, 0))
    blob(f"Ear{'L' if sx > 0 else 'R'}", (0.06, 0.09, 0.14), (sx * 0.52, 0.03, 2.58), "Head", "skin", subdiv=1)

# Glasses: round-rect dark frames, bridge, and temple arms.
for sx in (-1, 1):
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=False, radius=1, segments=14)
    bm.free()
    tor = bpy.data.meshes.new("rim")
    bmt = bmesh.new()
    # build a torus manually (ring of 14 x tube of 6)
    major, minor = 0.125, 0.016
    ring = []
    for i in range(14):
        a = 2 * math.pi * i / 14
        row = []
        for j in range(6):
            b = 2 * math.pi * j / 6
            r = major + minor * math.cos(b)
            x = r * math.cos(a) * 1.25
            z = r * math.sin(a) * 0.9
            y = minor * math.sin(b)
            row.append(bmt.verts.new((x, y, z)))
        ring.append(row)
    for i in range(14):
        for j in range(6):
            bmt.faces.new((ring[i][j], ring[(i + 1) % 14][j], ring[(i + 1) % 14][(j + 1) % 6], ring[i][(j + 1) % 6]))
    bmesh.ops.recalc_face_normals(bmt, faces=bmt.faces)
    rim = new_object(f"Rim{'L' if sx > 0 else 'R'}", bmt)
    rim.location = (sx * 0.215, -0.545, 2.69)
    add(rim, "Head", "frame")
    # temple arm from the rim's outer edge back to the ear
    limb(f"Temple{'L' if sx > 0 else 'R'}", (sx * 0.37, -0.53, 2.70), (sx * 0.53, -0.02, 2.66), 0.014, 0.014, "Head", "frame", 6)
box("Bridge", (0.10, 0.02, 0.022), (0, -0.55, 2.72), "Head", "frame")

# ----------------------------------------------------------------------------- arms
def arm(side):
    s = 1 if side == "L" else -1
    sh = (s * 0.92, 0.0, 1.70)
    el = (s * 0.99, -0.05, 0.95)
    wr = (s * 0.92, -0.22, 0.34)
    up, fo = f"UpperArm.{side}", f"Forearm.{side}"
    limb(f"Sleeve{side}", sh, el, 0.21, 0.185, up, "suit", 8)
    blob(f"Elbow{side}", (0.185, 0.185, 0.185), el, up, "suit", subdiv=1)
    limb(f"Forearm{side}", el, wr, 0.185, 0.16, fo, "suit", 8)
    limb(f"Cuff{side}", (wr[0], wr[1], wr[2] + 0.05), (wr[0], wr[1] - 0.02, wr[2] - 0.0), 0.165, 0.15, fo, "shirt", 8)
    blob(f"Hand{side}", (0.14, 0.10, 0.2), (wr[0], wr[1] - 0.025, wr[2] - 0.12), fo, "skin", subdiv=1)
    blob(f"Thumb{side}", (0.05, 0.05, 0.11), (wr[0] + s * -0.11, wr[1] - 0.07, wr[2] - 0.1), fo, "skin", subdiv=1)
    if side == "L":  # watch on his left wrist (viewer's right)
        limb("WatchStrap", (wr[0], wr[1] - 0.003, wr[2] + 0.1), (wr[0], wr[1] - 0.003, wr[2] + 0.02), 0.185, 0.185, fo, "strap", 8)
        c = limb("WatchFace", (wr[0] + 0.17, wr[1], wr[2] + 0.07), (wr[0] + 0.22, wr[1], wr[2] + 0.07), 0.085, 0.085, fo, "watch", 10)


arm("L")
arm("R")

# ----------------------------------------------------------------------------- armature
arm_data = bpy.data.armatures.new("AvatarRig")
rig = bpy.data.objects.new("AvatarRig", arm_data)
bpy.context.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode="EDIT")
eb = arm_data.edit_bones


def bone(name, head, tail, parent=None, roll=0.0):
    b = eb.new(name)
    b.head, b.tail = head, tail
    b.roll = roll
    if parent:
        b.parent = eb[parent]
    return b


bone("Spine", (0, 0, 0.1), (0, 0, 1.7))
bone("Neck", (0, 0, 1.8), (0, 0, 2.14), "Spine")
bone("Head", (0, 0, 2.14), (0, 0, 3.2), "Neck")
for side in ("L", "R"):
    s = 1 if side == "L" else -1
    bone(f"UpperArm.{side}", (s * 0.92, 0, 1.70), (s * 0.99, -0.05, 0.95), "Spine")
    bone(f"Forearm.{side}", (s * 0.99, -0.05, 0.95), (s * 0.92, -0.22, 0.34), f"UpperArm.{side}")
bpy.ops.object.mode_set(mode="OBJECT")

# Join meshes that share a bone, then skin each to its bone with weight 1.0.
bpy.ops.object.select_all(action="DESELECT")
skinned = []
for bone_name, objs in parts.items():
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    obj.name = f"Mesh_{bone_name}"
    vg = obj.vertex_groups.new(name=bone_name)
    vg.add(list(range(len(obj.data.vertices))), 1.0, "REPLACE")
    mod = obj.modifiers.new("Armature", "ARMATURE")
    mod.object = rig
    obj.parent = rig
    skinned.append(obj)

# ----------------------------------------------------------------------------- animations
rig.rotation_mode = "XYZ"
for pb in rig.pose.bones:
    pb.rotation_mode = "XYZ"

FPS, LOOP = 24, 96  # 4 second loops
ad = rig.animation_data_create()


def key(pbname, frame, euler):
    pb = rig.pose.bones[pbname]
    pb.rotation_euler = Euler(euler)
    pb.keyframe_insert("rotation_euler", frame=frame)


def reset_pose():
    for pb in rig.pose.bones:
        pb.rotation_euler = Euler((0, 0, 0))


def finish(action):
    action.use_fake_user = True
    track = ad.nla_tracks.new()
    track.name = action.name
    strip = track.strips.new(action.name, 1, action)
    track.mute = False
    ad.action = None


# Idle: gentle breathing, head drift, tiny arm sway.
idle = bpy.data.actions.new("Idle")
ad.action = idle
reset_pose()
for f, spine_x, head_z, head_x, arm_x in [(1, 0, 0, 0, 0), (25, 0.012, 0.07, -0.025, 0.02), (49, 0, 0, 0.0, 0), (73, 0.012, -0.07, 0.02, 0.02), (97, 0, 0, 0, 0)]:
    key("Spine", f, (spine_x, 0, head_z * 0.3))
    key("Neck", f, (head_x * 0.5, 0, head_z * 0.5))
    key("Head", f, (head_x, 0, head_z * 0.8))
    for side in ("L", "R"):
        key(f"UpperArm.{side}", f, (arm_x, 0, 0))
        key(f"Forearm.{side}", f, (arm_x * 0.6, 0, 0))
finish(idle)

# Wave: right arm (his right, -X) lifts and waves, then returns.
wave = bpy.data.actions.new("Wave")
ad.action = wave
reset_pose()
RAISE = float(os.environ.get("WAVE_RAISE", "1.0"))   # upper arm out to the side (radians)
BEND = float(os.environ.get("WAVE_BEND", "1.6"))     # forearm bent up at the elbow
SWING = 0.40                                          # how far the hand swings while waving
frames = [
    (1, 0, 0),
    (14, RAISE, BEND),
    (22, RAISE, BEND + SWING),
    (30, RAISE, BEND - SWING),
    (38, RAISE, BEND + SWING),
    (46, RAISE, BEND - SWING),
    (54, RAISE, BEND + SWING),
    (62, RAISE, BEND),
    (80, 0, 0),
    (97, 0, 0),
]
for f, up, fo in frames:
    key("UpperArm.R", f, (0, 0, up))
    key("Forearm.R", f, (0, 0, fo))
    head_turn = 0.10 if 10 < f < 70 else 0.0
    key("Head", f, (0, 0, head_turn))
    key("Neck", f, (0, 0, head_turn * 0.4))
    key("Spine", f, (0, 0, 0))
    key("UpperArm.L", f, (0, 0, 0))
    key("Forearm.L", f, (0, 0, 0))
finish(wave)
reset_pose()

# ----------------------------------------------------------------------------- save, export, preview
bpy.ops.object.select_all(action="DESELECT")
rig.select_set(True)
for o in skinned:
    o.select_set(True)
bpy.context.view_layer.objects.active = rig

bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
print("saved", BLEND_PATH)

bpy.ops.export_scene.gltf(
    filepath=GLB_PATH,
    export_format="GLB",
    use_selection=True,
    export_animations=True,
    export_animation_mode="NLA_TRACKS",
    export_skins=True,
    export_apply=False,
    export_yup=True,
)
print("exported", GLB_PATH, os.path.getsize(GLB_PATH), "bytes")
