using System.IO;
using UnityEditor;
using UnityEngine;

namespace SensorTrust
{
    /// <summary>
    /// Renders paired nadir images for the camera-reliability survey: a "live" image at the true position with the true Sun
    /// and a wider "reference" image from the onboard map with a slightly wrong Sun. Python measures how well a landmark
    /// matcher recovers the offset as a function of the lit fraction (sim/cam_survey_match.py).
    /// </summary>
    public static class CameraSurvey
    {
        [System.Serializable] class Item { public int id; public float x, z, y_sim, agl, ground, lit, rough, dx, dz, dsun_el, dsun_az; }
        [System.Serializable] class Plan { public Item[] items; }

        [MenuItem("SensorTrust/Run Camera Survey")]
        public static void Run()
        {
            string root = Path.GetFullPath(Path.Combine(Application.dataPath, "../../out/camera_survey"));
            var plan = JsonUtility.FromJson<Plan>(File.ReadAllText(Path.Combine(root, "positions.json")));
            Directory.CreateDirectory(Path.Combine(root, "img"));

            var sun = GameObject.Find("Sun");
            if (sun == null) { Debug.LogError("[CameraSurvey] no Sun in scene"); return; }
            var savedRot = sun.transform.rotation;
            float savedRefl = RenderSettings.reflectionIntensity, savedAmb = RenderSettings.ambientIntensity;
            RenderSettings.reflectionIntensity = 0f;   // no skybox light leaking into the lunar shadows
            RenderSettings.ambientIntensity = 0f;
            var go = new GameObject("SurveyCam");
            var cam = go.AddComponent<Camera>();
            cam.clearFlags = CameraClearFlags.SolidColor; cam.backgroundColor = Color.black;
            cam.nearClipPlane = 1f; cam.farClipPlane = 20000f; cam.allowHDR = false;
            float fovLive = 40f;
            float fovRef = 2f * Mathf.Atan(1.5f * Mathf.Tan(fovLive * 0.5f * Mathf.Deg2Rad)) * Mathf.Rad2Deg;
            int n = 0;
            try
            {
                foreach (var it in plan.items)
                {
                    float y = it.ground + it.agl;
                    // live: true Sun, displaced by the unknown navigation error
                    sun.transform.rotation = Quaternion.Euler(2.0f, 90f, 0f);
                    Render(cam, new Vector3(it.x + it.dx, y, it.z + it.dz), fovLive, 512, Path.Combine(root, "img", $"{it.id}_live.png"));
                    // reference: onboard-map prediction at the nominal position with a slightly wrong Sun
                    sun.transform.rotation = Quaternion.Euler(2.0f + it.dsun_el, 90f + it.dsun_az, 0f);
                    Render(cam, new Vector3(it.x, y, it.z), fovRef, 768, Path.Combine(root, "img", $"{it.id}_ref.png"));
                    n++;
                }
            }
            finally
            {
                sun.transform.rotation = savedRot;
                RenderSettings.reflectionIntensity = savedRefl; RenderSettings.ambientIntensity = savedAmb;
                Object.DestroyImmediate(go);
            }
            Debug.Log($"[CameraSurvey] rendered {n} pairs to {root}");
        }

        static void Render(Camera cam, Vector3 pos, float fov, int px, string path)
        {
            cam.transform.position = pos;
            cam.transform.rotation = Quaternion.Euler(90f, 0f, 0f);
            cam.fieldOfView = fov; cam.aspect = 1f;
            var rt = new RenderTexture(px, px, 24, RenderTextureFormat.ARGB32);
            cam.targetTexture = rt;
            cam.Render();
            RenderTexture.active = rt;
            var tex = new Texture2D(px, px, TextureFormat.RGB24, false);
            tex.ReadPixels(new Rect(0, 0, px, px), 0, 0);
            tex.Apply();
            File.WriteAllBytes(path, tex.EncodeToPNG());
            cam.targetTexture = null; RenderTexture.active = null;
            Object.DestroyImmediate(tex); rt.Release(); Object.DestroyImmediate(rt);
        }
    }
}
