using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace SensorTrust
{
    public static class ReplaySceneBuilder
    {
        [MenuItem("SensorTrust/Build Replay Scene")]
        public static void Build()
        {
            var scene = EditorSceneManager.OpenScene("Assets/Scenes/Site04.unity");
            foreach (var n in new[] { "Lander", "HUD" })
            {
                var go = GameObject.Find(n);
                if (go != null) go.SetActive(false);
            }
            var cam = Camera.main;
            if (cam != null) cam.farClipPlane = 60000f;
            var rp = new GameObject("Replay").AddComponent<ReplayPlayer>();
            rp.terrain = Object.FindFirstObjectByType<Terrain>();
            RenderSettings.ambientLight = new Color(0.12f, 0.12f, 0.14f);
            EditorSceneManager.SaveScene(scene, "Assets/Scenes/Site04Replay.unity", true);
            Debug.Log("Site04Replay.unity built");
        }
    }
}
