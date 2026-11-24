Put your Blender export here and name it:  avatar.glb

The website detects the file automatically. If it exists, it replaces the placeholder
avatar; if not, the built-in low-poly placeholder is shown.

Blender export tips (File > Export > glTF 2.0 (.glb)):
  - Format: glTF Binary (.glb)
  - Include: Selected Objects (select the armature and the mesh)
  - Transform: +Y Up (default)
  - Animation: tick "Animation" if you made an idle/wave action. The site plays the first
    clip whose name contains "idle", "wave" or "loop", otherwise the first clip.
  - Keep it small (under ~5 MB): apply modifiers, keep textures at 1024px or less.
  - Origin at the feet, about 2 units tall. If it looks too big or small in the page, change
    the scale in client/src/components/Hero3D.jsx (GLBAvatar).
