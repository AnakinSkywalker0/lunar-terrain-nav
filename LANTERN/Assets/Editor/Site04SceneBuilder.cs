using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace SensorTrust.Editor
{
    /// <summary>Builds the Site04 scene: DEM terrain, low Sun, lunar gravity, lander.</summary>
    public static class Site04SceneBuilder
    {
        const string RawPath = "Assets/Terrain/site04_height.raw";
        const string MetaPath = "Assets/Terrain/site04_height.json";
        const string DataPath = "Assets/Terrain/Site04TerrainData.asset";
        const string ScenePath = "Assets/Scenes/Site04.unity";

        [System.Serializable] class Meta { public int resolution; public float side_m, min_m, max_m; }

        [MenuItem("SensorTrust/Build Site04 Scene")]
        public static void Build()
        {
            var meta = JsonUtility.FromJson<Meta>(File.ReadAllText(MetaPath));
            var bytes = File.ReadAllBytes(RawPath);
            int n = meta.resolution;
            var heights = new float[n, n];
            for (int z = 0; z < n; z++)
                for (int x = 0; x < n; x++)
                {
                    int i = (z * n + x) * 2;
                    heights[z, x] = (bytes[i] | (bytes[i + 1] << 8)) / 65535f;
                }

            float range = meta.max_m - meta.min_m;
            var td = AssetDatabase.LoadAssetAtPath<TerrainData>(DataPath);
            if (td == null)
            {
                td = new TerrainData();
                AssetDatabase.CreateAsset(td, DataPath);
            }
            td.heightmapResolution = n;
            td.size = new Vector3(meta.side_m, range, meta.side_m);
            td.SetHeights(0, 0, heights);
            EditorUtility.SetDirty(td);

            Directory.CreateDirectory("Assets/Scenes");
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

            // Terrain origin y = DEM minimum, so world Y equals elevation in metres.
            var terrainGo = Terrain.CreateTerrainGameObject(td);
            terrainGo.name = "Site04 Terrain";
            terrainGo.transform.position = new Vector3(0f, meta.min_m, 0f);
            var terrain = terrainGo.GetComponent<Terrain>();
            terrain.heightmapPixelError = 5f;
            terrain.drawInstanced = true;

            // Sun 2 deg above the south-east horizon: light travels toward the north-west.
            var sunGo = new GameObject("Sun");
            var sun = sunGo.AddComponent<Light>();
            sun.type = LightType.Directional;
            sun.intensity = 2.0f;
            sun.shadows = LightShadows.Soft;
            sun.shadowStrength = 1f;
            sunGo.transform.rotation = Quaternion.Euler(2f, 315f, 0f);
            RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Flat;
            RenderSettings.ambientLight = Color.black;
            QualitySettings.shadowDistance = 20000f;
            QualitySettings.shadowCascades = 4;

            // Lander: 500 m above the flattest site (45 m window max slope 2.8 deg) found near the tile centre.
            // The centre itself is 33 deg. Tile coords: x east, z north, metres.
            var lander = BuildLander();
            float cx = 6198f, cz = 8512f;
            float ground = terrain.SampleHeight(new Vector3(cx, 0, cz)) + meta.min_m;
            lander.transform.position = new Vector3(cx, ground + 102500f, cz);   // 102.5 km above the surface, dropped from rest

            var cam = new GameObject("Main Camera") { tag = "MainCamera" };
            var c = cam.AddComponent<Camera>();
            c.clearFlags = CameraClearFlags.SolidColor;
            c.backgroundColor = Color.black;
            c.farClipPlane = 40000f;
            c.nearClipPlane = 0.5f;
            cam.AddComponent<FollowCamera>().target = lander.transform;

            var hud = new GameObject("HUD").AddComponent<LanderHud>();
            hud.lander = lander.GetComponent<LanderController>();
            hud.terrain = terrain;
            hud.lumen = lander.GetComponent<Lumen.LumenModule>();

            var ap = lander.AddComponent<DescentAutopilot>();
            ap.terrain = terrain;
            var tel = lander.AddComponent<TelemetryLogger>();
            tel.lander = lander.GetComponent<LanderController>();
            tel.autopilot = ap;
            tel.lumen = hud.lumen;
            tel.terrain = terrain;

            Physics.gravity = new Vector3(0f, -1.62f, 0f);
            EditorSceneManager.SaveScene(scene, ScenePath);
            EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(ScenePath, true) };
            AssetDatabase.SaveAssets();
            Debug.Log($"Site04 scene built: {n}x{n} DEM, {meta.min_m:F0}..{meta.max_m:F0} m, gravity 1.62 m/s^2");
        }

        static GameObject BuildLander()
        {
            var root = new GameObject("Lander");
            var body = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            body.name = "Body";
            body.transform.SetParent(root.transform, false);
            body.transform.localScale = new Vector3(2.4f, 1.0f, 2.4f);
            body.transform.localPosition = new Vector3(0, 2.0f, 0);

            for (int i = 0; i < 4; i++)
            {
                float a = i * 90f * Mathf.Deg2Rad;
                var leg = GameObject.CreatePrimitive(PrimitiveType.Capsule);
                leg.name = "Leg" + i;
                leg.transform.SetParent(root.transform, false);
                leg.transform.localPosition = new Vector3(Mathf.Cos(a) * 1.6f, 1.0f, Mathf.Sin(a) * 1.6f);
                leg.transform.localScale = new Vector3(0.2f, 1.0f, 0.2f);
                leg.transform.localRotation = Quaternion.Euler(Mathf.Sin(a) * -20f, 0, Mathf.Cos(a) * 20f);
            }

            var rb = root.AddComponent<Rigidbody>();
            rb.interpolation = RigidbodyInterpolation.Interpolate;
            rb.collisionDetectionMode = CollisionDetectionMode.ContinuousDynamic;
            rb.centerOfMass = new Vector3(0, 1.8f, 0);
            root.AddComponent<LanderController>();
            root.AddComponent<Lumen.LidarScanner>();
            root.AddComponent<Lumen.LumenModule>().map = Object.FindFirstObjectByType<Terrain>();
            return root;
        }

        /// <summary>Headless check: scan from 500 m AGL with a known position error and see if LUMEN recovers it.</summary>
        public static void LumenSelfTest()
        {
            Build();
            var lumen = Object.FindFirstObjectByType<Lumen.LumenModule>();
            Physics.SyncTransforms();
            lumen.RunScan();
            var r = lumen.Last;
            var want = new Vector2(-lumen.positionErrorM.x, -lumen.positionErrorM.z);
            Debug.Log($"LUMEN self-test: points={lumen.LastPointCount} cells={r.cellsUsed} valid={r.valid} " +
                      $"shift=({r.shiftXZ.x:F1},{r.shiftXZ.y:F1}) expected=({want.x:F1},{want.y:F1}) " +
                      $"rms={r.rmsM:F2} m conf={r.confidence:F2}");
        }
    }
}
