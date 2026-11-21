using System;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace SensorTrust.Editor
{
    /// <summary>Import the Blender visual asset into an isolated inspection scene.
    /// Does not modify the flight scenes, physics, sensors, or experiment outputs.</summary>
    public static class LanderArtPreview
    {
        const string Folder = "Assets/Art/Lander";
        const string ModelPath = Folder + "/LANTERN_Lander.fbx";

        static Material MakeMaterial(string name, Color color, float metal, float rough)
        {
            string path = Folder + "/Materials/" + name + ".mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null)
            {
                mat = new Material(Shader.Find("Standard"));
                AssetDatabase.CreateAsset(mat, path);
            }
            mat.color = color;
            mat.SetFloat("_Metallic", metal);
            mat.SetFloat("_Glossiness", 1f - rough);
            EditorUtility.SetDirty(mat);
            return mat;
        }

        [MenuItem("SensorTrust/Art/Open Lander Preview")]
        public static void Build()
        {
            if (EditorApplication.isPlaying || EditorApplication.isCompiling)
                throw new InvalidOperationException("Stop Play mode and finish compilation before building the preview.");
            if (UnityEngine.SceneManagement.SceneManager.GetActiveScene().isDirty)
                throw new InvalidOperationException("Save the current scene before opening the lander preview.");
            Directory.CreateDirectory(Folder + "/Materials");
            AssetDatabase.ImportAsset(ModelPath, ImportAssetOptions.ForceSynchronousImport);
            var importer = (ModelImporter)AssetImporter.GetAtPath(ModelPath);
            importer.importCameras = false;
            importer.importLights = false;
            importer.importAnimation = false;
            importer.addCollider = false;
            importer.globalScale = 1f;
            importer.SaveAndReimport();
            var materials = new System.Collections.Generic.Dictionary<string, Material>
            {
                ["MLI_Gold"] = MakeMaterial("MLI_Gold", new Color(.55f,.29f,.055f), .75f, .36f),
                ["Titanium"] = MakeMaterial("Titanium", new Color(.55f,.61f,.65f), .8f, .28f),
                ["Ceramic_White"] = MakeMaterial("Ceramic_White", new Color(.81f,.84f,.84f), .15f, .38f),
                ["Graphite"] = MakeMaterial("Graphite", new Color(.035f,.045f,.06f), .55f, .38f),
                ["Nozzle_Interior"] = MakeMaterial("Nozzle_Interior", new Color(.009f,.013f,.02f), .15f, .8f),
                ["Solar_Cells"] = MakeMaterial("Solar_Cells", new Color(.018f,.055f,.16f), .65f, .25f),
                ["Optics_Blue"] = MakeMaterial("Optics_Blue", new Color(.02f,.22f,.31f), .65f, .12f),
                ["Warning_Amber"] = MakeMaterial("Warning_Amber", new Color(.95f,.32f,.035f), .2f, .4f)
            };
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(ModelPath);
            if (model == null) throw new InvalidOperationException("Blender FBX is missing.");
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var visual = (GameObject)PrefabUtility.InstantiatePrefab(model);
            visual.name = "LANTERN Lander - Visual Concept";
            foreach (var r in visual.GetComponentsInChildren<Renderer>())
            {
                var slots = r.sharedMaterials;
                for (int i = 0; i < slots.Length; i++)
                {
                    if (slots[i] == null) continue;
                    foreach (var pair in materials)
                        if (slots[i].name.StartsWith(pair.Key, StringComparison.Ordinal))
                        { slots[i] = pair.Value; break; }
                }
                r.sharedMaterials = slots;
            }
            PrefabUtility.SaveAsPrefabAsset(visual, Folder + "/LANTERN_Lander_Visual.prefab");
            var bounds = new Bounds(visual.transform.position, Vector3.zero);
            foreach (var r in visual.GetComponentsInChildren<Renderer>()) bounds.Encapsulate(r.bounds);
            // FBX unit and orientation guard: six-metre span, roughly four metres high.
            if (bounds.size.y < 3.8f || bounds.size.y > 4.7f || bounds.size.x > 7f)
                throw new InvalidOperationException("Unexpected imported dimensions: " + bounds.size);
            var floor = GameObject.CreatePrimitive(PrimitiveType.Plane);
            floor.name = "Studio floor (presentation only)";
            floor.transform.position = new Vector3(0,-.015f,0);
            floor.transform.localScale = Vector3.one * 20;
            floor.GetComponent<Renderer>().sharedMaterial = MakeMaterial("Studio_Floor", new Color(.07f,.09f,.12f), 0f, .8f);
            RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Flat;
            RenderSettings.ambientLight = new Color(.42f,.45f,.52f);
            RenderSettings.fog = false;
            var key = new GameObject("Studio key").AddComponent<Light>();
            key.type = LightType.Directional;
            key.intensity = 1.4f;
            key.color = new Color(1,.94f,.86f);
            key.transform.rotation = Quaternion.Euler(45,-35,0);
            key.shadows = LightShadows.Soft;
            var fill = new GameObject("Studio fill").AddComponent<Light>();
            fill.type = LightType.Directional;
            fill.intensity = .6f;
            fill.color = new Color(.72f,.84f,1);
            fill.transform.rotation = Quaternion.Euler(35,140,0);
            var cam = new GameObject("Preview Camera").AddComponent<Camera>();
            cam.tag = "MainCamera";
            cam.transform.position = new Vector3(8,7,11);
            cam.transform.LookAt(new Vector3(0,1.85f,0));
            cam.orthographic = true;
            cam.orthographicSize = 3.6f;
            cam.nearClipPlane = .05f;
            cam.farClipPlane = 100f;
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = new Color(.04f,.06f,.09f);
            EditorSceneManager.SaveScene(scene, "Assets/Scenes/LanderPreview.unity");
            AssetDatabase.SaveAssets();
            Selection.activeGameObject = visual;
            if (SceneView.lastActiveSceneView != null) SceneView.lastActiveSceneView.Frame(bounds, false);
            Capture(cam);
            Debug.Log("LANTERN visual imported; bounds " + bounds.size + "; " + visual.GetComponentsInChildren<MeshRenderer>().Length + " mesh renderers. Flight scenes unchanged.");
        }

        static void Capture(Camera camera)
        {
            string path = Path.GetFullPath("../deliverables/lander/LANTERN_Lander_Unity.png");
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            var oldTarget = camera.targetTexture;
            var oldActive = RenderTexture.active;
            var target = new RenderTexture(1440,1100,24);
            var pixels = new Texture2D(1440,1100,TextureFormat.RGB24,false);
            try
            {
                camera.targetTexture = target;
                camera.Render();
                RenderTexture.active = target;
                pixels.ReadPixels(new Rect(0,0,1440,1100),0,0);
                pixels.Apply();
                File.WriteAllBytes(path,pixels.EncodeToPNG());
            }
            finally
            {
                camera.targetTexture = oldTarget;
                RenderTexture.active = oldActive;
                UnityEngine.Object.DestroyImmediate(pixels);
                target.Release();
                UnityEngine.Object.DestroyImmediate(target);
            }
        }
    }
}
