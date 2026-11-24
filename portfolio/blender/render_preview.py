"""
Renders preview images of the avatar.
    python render_preview.py front out.png            # front view, rest pose
    python render_preview.py front out.png Wave 30    # front view of the Wave animation at frame 30
    python render_preview.py three_quarter out.png
    python render_preview.py face out.png             # close-up of the head
"""
import math
import os
import sys

import bpy
from mathutils import Vector

view, out = sys.argv[1], sys.argv[2]
anim = sys.argv[3] if len(sys.argv) > 3 else None
frame = int(sys.argv[4]) if len(sys.argv) > 4 else 1

here = os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.open_mainfile(filepath=os.path.join(here, "ali_avatar.blend"))
scene = bpy.context.scene
rig = bpy.data.objects["AvatarRig"]

# Choose which animation is evaluated by muting the other NLA track.
for tr in rig.animation_data.nla_tracks:
    tr.mute = anim is None or tr.name != anim
scene.frame_set(frame)

# World colour = the warm arch colour used on the website.
world = bpy.data.worlds.new("W")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.815, 0.584, 0.392, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.9
scene.world = world

# Lights
sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
sun.data.energy = 3.2
sun.rotation_euler = (math.radians(55), 0, math.radians(-35))
bpy.context.collection.objects.link(sun)
fill = bpy.data.objects.new("Fill", bpy.data.lights.new("Fill", "AREA"))
fill.data.energy = 120
fill.data.size = 5
fill.location = (-4, -6, 2)
fill.rotation_euler = (math.radians(80), 0, math.radians(-30))
bpy.context.collection.objects.link(fill)

cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
bpy.context.collection.objects.link(cam)
scene.camera = cam
if view == "front":
    cam.location, target, lens = (0, -11, 1.7), Vector((0, 0, 1.65)), 50
elif view == "three_quarter":
    cam.location, target, lens = (6.2, -9.0, 2.3), Vector((0, 0, 1.65)), 50
elif view == "face":
    cam.location, target, lens = (0.0, -6.0, 2.7), Vector((0, 0, 2.65)), 85
else:
    raise SystemExit("unknown view")
cam.data.lens = lens
cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()

scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 48
scene.cycles.use_denoising = True
scene.render.resolution_x = 640 if view != "face" else 700
scene.render.resolution_y = 840 if view != "face" else 700
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = out
bpy.ops.render.render(write_still=True)
print("rendered", out)
