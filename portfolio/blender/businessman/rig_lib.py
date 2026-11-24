"""Helpers for posing the Mixamo-style businessman rig with rotations expressed in armature space.

Pose bones rotate in their own (rolled) local frames, which makes hand-authoring awkward. Here every
pose is described as a *cumulative* armature-space rotation per bone (X = character's left,
Y = backwards, Z = up; the character faces -Y). The helper converts that into the local rotation
Blender needs:   q_local = R_b^-1 * D_parent^-1 * D_b * R_b   (R_b = bone rest rotation).
"""
import math
import bpy
from mathutils import Quaternion

IDENT = Quaternion((1, 0, 0, 0))
AXES = {'x': (1, 0, 0), 'y': (0, 1, 0), 'z': (0, 0, 1)}


def Q(axis, deg):
    return Quaternion(AXES[axis], math.radians(deg))


def compose(*qs):
    out = IDENT.copy()
    for q in qs:
        out = out @ q
    return out


def set_pose(rig, spec, keys):
    """spec: {bone: cumulative armature-space delta}. Bones not listed inherit their parent's delta."""
    cum = {}
    for pb in rig.pose.bones:  # parents come before children
        parent = pb.parent
        base = cum[parent.name] if parent else IDENT
        cum[pb.name] = spec.get(pb.name, base)
        if pb.name in keys:
            R = pb.bone.matrix_local.to_quaternion()
            q = R.inverted() @ base.inverted() @ cum[pb.name] @ R
            pb.rotation_mode = 'QUATERNION'
            pb.rotation_quaternion = q


def key_pose(rig, frame, spec, keys):
    set_pose(rig, spec, keys)
    for name in keys:
        rig.pose.bones[name].keyframe_insert('rotation_quaternion', frame=frame)


def new_action(rig, name):
    act = bpy.data.actions.new(name)
    rig.animation_data_create()
    rig.animation_data.action = act
    return act
