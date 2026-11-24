"""The source model is skinned with the two clasped hands fused: the finger shells sit on top of each
other in the clasp and carry the wrong (or mixed) weights, so raising the right arm drags the left
hand's fingers and the jacket with it (long ribbons of skin). This re-skins every small shell in the
clasp zone rigidly to the hand it geometrically belongs to."""
import bmesh
import bpy

HAND_BONES = ('RightHand', 'LeftHand')


def reskin_clasp(mesh_obj, verbose=True):
    me = mesh_obj.data
    names = {g.index: g.name for g in mesh_obj.vertex_groups}
    vg = {g.name: g for g in mesh_obj.vertex_groups}
    bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
    seen, comps = set(), []
    for v in bm.verts:
        if v.index in seen:
            continue
        stack, comp = [v], []
        seen.add(v.index)
        while stack:
            x = stack.pop(); comp.append(x.index)
            for e in x.link_edges:
                o = e.other_vert(x)
                if o.index not in seen:
                    seen.add(o.index); stack.append(o)
        comps.append(comp)
    moved = {'R': 0, 'L': 0}
    for comp in comps:
        if len(comp) > 700:
            continue
        cos = [me.vertices[i].co for i in comp]
        cx = sum(c.x for c in cos) / len(cos); cy = sum(c.y for c in cos) / len(cos); cz = sum(c.z for c in cos) / len(cos)
        if not (0.70 < cz < 1.10 and abs(cx) < 0.20 and cy < -0.02):
            continue
        r = l = 0.0
        for i in comp:
            for g in me.vertices[i].groups:
                if names[g.group] in ('RightHand', 'RightForeArm'):
                    r += g.weight
                elif names[g.group] in ('LeftHand', 'LeftForeArm'):
                    l += g.weight
        if r + l < 0.3 * len(comp):  # not a hand shell (buttons, pocket, belt...)
            continue
        side = 'R' if (r - l) / max(r + l, 1e-6) > 0.25 else 'L' if (l - r) / max(r + l, 1e-6) > 0.25 else ('R' if cx < 0 else 'L')
        target = 'RightHand' if side == 'R' else 'LeftHand'
        for i in comp:
            for g in names.values():
                try:
                    vg[g].remove([i])
                except RuntimeError:
                    pass
            vg[target].add([i], 1.0, 'REPLACE')
        moved[side] += len(comp)
    bm.free()
    if verbose:
        print('RESKIN right-hand verts', moved['R'], 'left-hand verts', moved['L'])


def _seg_t_d(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
    return t, (p - (a + ab * t)).length


def reskin_forearm(rig, mesh_obj, r_full=0.062, r_out=0.105, x_max=-0.115, verbose=True):
    """Sleeve vertices around the right arm are partly skinned to the torso (the arm lies across the
    belly in the rest pose, and the sleeve geometry sits close to the jacket). Blend those vertices
    towards the arm bone they sit next to so the sleeve follows the arm instead of tearing."""
    names = {g.index: g.name for g in mesh_obj.vertex_groups}
    vg = {g.name: g for g in mesh_obj.vertex_groups}
    segs = {n: (rig.data.bones[n].head_local.copy(), rig.data.bones[n].tail_local.copy()) for n in ('RightForeArm',)}
    n_fixed = 0
    for v in mesh_obj.data.vertices:
        ws = {names[g.group]: g.weight for g in v.groups if g.weight > 1e-4}
        if ws.get('RightHand', 0) > 0.5:
            continue
        best = None
        for bone, (a, b) in segs.items():
            t, d = _seg_t_d(v.co, a, b)
            if bone == 'RightArm' and t < 0.35:
                continue  # leave the shoulder cap to the original (smooth) weights
            if best is None or d < best[1]:
                best = (bone, d, t)
        if best is None or best[1] > r_out:
            continue
        if best[1] > r_full and v.co.x > x_max:
            continue  # only the tight sleeve radius applies near the midline (keeps the belly still)
        bone, d, t = best
        f = 1.0 if d <= r_full else 1.0 - (d - r_full) / (r_out - r_full)
        f = f * f * (3 - 2 * f)
        new = {k: w * (1 - f) for k, w in ws.items()}
        # near the elbow share the load between upper arm and forearm
        if bone == 'RightForeArm':
            s = min(1.0, t / 0.3)
            new['RightForeArm'] = new.get('RightForeArm', 0) + f * s
            new['RightArm'] = new.get('RightArm', 0) + f * (1 - s)
        else:
            new['RightArm'] = new.get('RightArm', 0) + f
        total = sum(new.values())
        for g in names.values():
            try:
                vg[g].remove([v.index])
            except RuntimeError:
                pass
        for k, w in new.items():
            if w > 1e-4:
                vg[k].add([v.index], w / total, 'REPLACE')
        n_fixed += 1
    if verbose:
        print('RESKIN sleeve verts', n_fixed)
