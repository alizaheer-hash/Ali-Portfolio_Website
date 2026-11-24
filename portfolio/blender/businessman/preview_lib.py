import bpy, math
from mathutils import Vector

def setup_scene(bg=(0.16, 0.13, 0.10)):
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_WORKBENCH'
    sh = scene.display.shading
    sh.light = 'STUDIO'; sh.color_type = 'TEXTURE'; sh.show_shadows = False
    scene.render.film_transparent = False
    world = bpy.data.worlds.new('W'); world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (*bg, 1)
    scene.world = world
    scene.render.resolution_x, scene.render.resolution_y = 600, 800
    cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam'))
    bpy.context.collection.objects.link(cam)
    scene.camera = cam
    return cam

def shoot(cam, path, loc=(0, -4.2, 1.0), target=(0, 0, 0.95), lens=45):
    cam.location = loc; cam.data.lens = lens
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
