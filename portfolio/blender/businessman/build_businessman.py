"""Build the website avatar: take the rigged businessman GLB (which ships with Idle, Walk, Nod and
LookAround), add three interaction clips (Greet, Bow, Ponder) and export it for the web.

    blender -b --python build_businessman.py -- <out.glb> [preview_dir]

The model's hands are clasped in the rest pose and are skinned together, so every new clip moves
both arms symmetrically (the clasp stays intact instead of tearing the mesh).
Rotations are authored in armature space (see rig_lib.py).
"""
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig_lib import Q, compose, key_pose, new_action  # noqa: E402
from split_hands import reskin_clasp  # noqa: E402

argv = sys.argv[sys.argv.index('--') + 1:]
OUT = os.path.abspath(argv[0])
PREVIEW = os.path.abspath(argv[1]) if len(argv) > 1 else None
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'source_businessman_rigged.glb')

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
bpy.context.scene.render.fps = 24
rig = bpy.data.objects['Armature']
for o in list(bpy.data.objects):  # the importer leaves a bone-shape helper sphere behind
    if o.type == 'MESH' and o.name != 'Businessman':
        bpy.data.objects.remove(o, do_unlink=True)

# Fix the fused-hands skinning first so the hands stay clean when the arms move.
reskin_clasp(bpy.data.objects['Businessman'])

KEYS = {'Spine', 'Spine1', 'Spine2', 'Neck', 'Head', 'RightArm', 'LeftArm', 'RightForeArm', 'LeftForeArm'}
REST = {}


def both(arm=0.0, fore=0.0):
    """Symmetric arm pose: raise (negative) both upper arms / forearms about the X axis."""
    d = {}
    if arm:
        d['RightArm'] = d['LeftArm'] = Q('x', arm)
    if fore:
        # forearm rotation is cumulative: parent's rotation plus the extra flex
        a = arm
        d['RightForeArm'] = d['LeftForeArm'] = Q('x', a + fore)
    return d


def torso(spine=0.0, spine1=0.0, spine2=0.0, head=0.0):
    """Forward lean (positive = bend forward), cumulative along the spine."""
    d = {}
    if spine:
        d['Spine'] = Q('x', spine)
    if spine1:
        d['Spine1'] = Q('x', spine + spine1)
    if spine2:
        d['Spine2'] = Q('x', spine + spine1 + spine2)
    if head:
        d['Head'] = Q('x', spine + spine1 + spine2 + head)
    return d


def merge(*ds):
    out = {}
    for d in ds:
        out.update(d)
    return out


def clip(name, frames):
    act = new_action(rig, name)
    act.use_fake_user = True
    for f, spec in frames:
        # arms must also sit under the spine's cumulative rotation, so add it to arm specs
        spec = dict(spec)
        lean = spec.get('Spine2') or spec.get('Spine1') or spec.get('Spine')
        key_pose(rig, f, spec, KEYS)
    return act


# ---- Greet: the hands lift together in front of the chest (a polite "salaam"), a small bow, release.
HANDS = merge(both(-8, -34), torso(spine=2, spine1=2))
GREET = [
    (1, {}),
    (14, merge(both(-8, -34), torso(spine=2, spine1=2, head=-4))),
    (28, merge(both(-10, -38), torso(spine=4, spine1=6, spine2=6, head=8))),
    (42, merge(both(-10, -38), torso(spine=4, spine1=6, spine2=6, head=8))),
    (54, merge(both(-8, -34), torso(spine=2, spine1=2, head=-2))),
    (72, {}),
]
# ---- Bow: a deeper formal bow.
BOW = [
    (1, {}),
    (20, merge(torso(spine=10, spine1=14, spine2=14, head=6))),
    (34, merge(torso(spine=11, spine1=15, spine2=15, head=8))),
    (56, {}),
]
# ---- Ponder: hands rise to the chest, the head tilts as if thinking, then relax.
TILT = {'Head': compose(Q('z', 9), Q('x', 6))}
PONDER = [
    (1, {}),
    (16, merge(both(-14, -50), TILT)),
    (30, merge(both(-15, -54), {'Head': compose(Q('z', -8), Q('x', 4))})),
    (46, merge(both(-14, -50), TILT)),
    (60, merge(both(-14, -50), {'Head': compose(Q('z', 4), Q('x', 8))})),
    (78, {}),
]

# Existing clips come in as plain actions; remember them before adding more.
existing = [a for a in bpy.data.actions if a.name in ('Idle', 'Walk', 'Nod', 'LookAround')]
new = [clip('Greet', GREET), clip('Bow', BOW), clip('Ponder', PONDER)]

# Put every clip on its own NLA track so the exporter writes them all as separate animations.
ad = rig.animation_data
ad.action = None
for t in list(ad.nla_tracks):
    ad.nla_tracks.remove(t)
for act in existing + new:
    tr = ad.nla_tracks.new()
    tr.name = act.name
    st = tr.strips.new(act.name, int(act.frame_range[0]), act)
    st.name = act.name

if PREVIEW:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import preview_lib as P
    os.makedirs(PREVIEW, exist_ok=True)
    cam = P.setup_scene()
    for tr in ad.nla_tracks:
        tr.mute = True
    for name, frames in (('Greet', (14, 35)), ('Bow', (30,)), ('Ponder', (16, 30))):
        for tr in ad.nla_tracks:
            tr.mute = tr.name != name
        for fr in frames:
            bpy.context.scene.frame_set(fr)
            P.shoot(cam, os.path.join(PREVIEW, f'{name}_{fr}.png'), loc=(0, -3.3, 1.25), target=(0, 0, 1.2), lens=50)
    for tr in ad.nla_tracks:
        tr.mute = False

bpy.ops.export_scene.gltf(
    filepath=OUT, export_format='GLB', export_animations=True,
    export_animation_mode='NLA_TRACKS', export_force_sampling=True, export_optimize_animation_size=True,
    export_image_format='AUTO', use_selection=False,
)
print('EXPORTED', OUT)
