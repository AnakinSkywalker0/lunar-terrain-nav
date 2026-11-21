# LANTERN lander visual concept

Created 2026-10-21 in Blender 4.5.11 using `tools/build_lander_art.py`.
An original robotic lunar lander illustration, not a mission replica or an
engineering-validated design.

- Editable source: `LANTERN_Lander.blend` (includes the studio lighting stage).
- Unity geometry: `../../LANTERN/Assets/Art/Lander/LANTERN_Lander.fbx`.
- Unity visual prefab: `LANTERN_Lander_Visual.prefab` alongside the FBX.
- Unity inspection scene: `Assets/Scenes/LanderPreview.unity`.
- Preview renders: `../../deliverables/lander/`.
- Rebuild: run Blender in background with `--python tools/build_lander_art.py`,
  then use Unity menu `SensorTrust/Art/Open Lander Preview` after saving your scene.

The model has a gold thermal-blanket bus, four triangulated landing legs,
footpads, an engine bell, tanks, solar wings, communications equipment and
illustrative navigation optics. Units are metres, origin at ground level;
Blender uses Z up and the FBX converts to Unity Y up.

The prefab is visual only. No collision shapes, controller, sensor extrinsics,
mass properties or flight validation are supplied by the art asset. Attach it
to a tested vehicle only after checking those separately. The existing Site04
flight and replay scenes were not edited.

Blender's procedural foil bump is visible in the Blender render. Unity uses
portable base-colour/metallic materials and the geometry's shallow foil folds.
Studio lighting is for inspecting the model, not a lunar illumination test.

The build script and Unity import were run, both renders inspected, import
dimensions checked and the Unity console checked with no errors or warnings
returned. No training or flight experiment was run as part of creating this art.
