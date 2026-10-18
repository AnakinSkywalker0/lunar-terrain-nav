using System.Collections.Generic;
using System.Globalization;
using System.IO;
using UnityEngine;

namespace SensorTrust
{
    /// <summary>
    /// Side-by-side replay of descents recorded by the Python test bench (out/replay/replay_*.csv).
    /// Each variant shows the TRUE lander (solid) and the filter's ESTIMATED position (translucent ghost, with a line to truth).
    /// Sim coordinates: x east, y = tile row (north at 0), z = MSL height. Unity: x east, z north = 16000 - y, y = MSL.
    /// </summary>
    public class ReplayPlayer : MonoBehaviour
    {
        public string folder = "../../out/replay";
        public string[] variants = { "fixed", "pitfal", "trust" };
        public string[] labels = { "Fixed gate (HAKUTO-R style)", "PITFAL-style", "Trust layer" };
        public Color[] colors = { new Color(0.95f, 0.3f, 0.25f), new Color(1f, 0.75f, 0.2f), new Color(0.3f, 0.95f, 0.5f) };
        public float speed = 6f;
        public float tileSideM = 16000f;
        public Terrain terrain;

        class Row { public float t, x, y, z, ex, ey, ez, aglTrue, aglEst, gate, acc, r, fault, fuel; }
        class Track
        {
            public List<Row> rows = new List<Row>();
            public Transform body, ghost; public LineRenderer link, trail;
            public string label; public Color color;
            public float endT => rows.Count > 0 ? rows[rows.Count - 1].t : 0f;
        }

        readonly List<Track> tracks = new List<Track>();
        float clock;
        GUIStyle style;
        Camera cam;

        void Start()
        {
            string dir = Path.GetFullPath(Path.Combine(Application.dataPath, folder));
            for (int i = 0; i < variants.Length; i++)
            {
                string path = Path.Combine(dir, $"replay_{variants[i]}.csv");
                if (!File.Exists(path)) { Debug.LogWarning("[Replay] missing " + path); continue; }
                var tr = new Track { label = labels[i], color = colors[i] };
                var lines = File.ReadAllLines(path);
                for (int k = 1; k < lines.Length; k++)
                {
                    var f = lines[k].Split(',');
                    if (f.Length < 14) continue;
                    float P(int j) => float.Parse(f[j], CultureInfo.InvariantCulture);
                    tr.rows.Add(new Row { t = P(0), x = P(1), y = P(2), z = P(3), ex = P(4), ey = P(5), ez = P(6), aglTrue = P(7), aglEst = P(8), gate = P(9), acc = P(10), r = P(11), fault = P(12), fuel = P(13) });
                }
                Build(tr);
                tracks.Add(tr);
            }
            cam = Camera.main;
            if (cam != null) { var fc = cam.GetComponent<FollowCamera>(); if (fc != null) fc.enabled = false; }
            Debug.Log($"[Replay] loaded {tracks.Count} variants from {dir}");
        }

        void Build(Track t)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            go.name = "Replay_" + t.label; Destroy(go.GetComponent<Collider>());
            go.GetComponent<Renderer>().material.color = t.color;
            t.body = go.transform;
            var gh = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            gh.name = "Ghost_" + t.label; Destroy(gh.GetComponent<Collider>());
            var gm = gh.GetComponent<Renderer>().material;
            gm.color = new Color(t.color.r, t.color.g, t.color.b, 0.35f);
            gm.SetFloat("_Surface", 1); gm.renderQueue = 3000;
            t.ghost = gh.transform;
            t.link = MakeLine(go.transform, t.color, 0.6f);
            t.trail = MakeLine(go.transform, t.color, 0.25f);
            t.trail.positionCount = 0;
        }

        LineRenderer MakeLine(Transform parent, Color c, float alpha)
        {
            var g = new GameObject("line"); g.transform.SetParent(parent, false);
            var lr = g.AddComponent<LineRenderer>();
            lr.useWorldSpace = true; lr.material = new Material(Shader.Find("Sprites/Default"));
            lr.startColor = lr.endColor = new Color(c.r, c.g, c.b, alpha);
            lr.positionCount = 2; lr.numCapVertices = 2;
            return lr;
        }

        Vector3 ToUnity(float x, float y, float z) => new Vector3(x, z, tileSideM - y);

        Row At(Track t, float time)
        {
            var r = t.rows;
            if (r.Count == 0) return null;
            if (time >= r[r.Count - 1].t) return r[r.Count - 1];
            int lo = 0, hi = r.Count - 1;
            while (hi - lo > 1) { int mid = (lo + hi) / 2; if (r[mid].t <= time) lo = mid; else hi = mid; }
            var a = r[lo]; var b = r[hi]; float u = Mathf.InverseLerp(a.t, b.t, time);
            return new Row
            {
                t = time, x = Mathf.Lerp(a.x, b.x, u), y = Mathf.Lerp(a.y, b.y, u), z = Mathf.Lerp(a.z, b.z, u),
                ex = Mathf.Lerp(a.ex, b.ex, u), ey = Mathf.Lerp(a.ey, b.ey, u), ez = Mathf.Lerp(a.ez, b.ez, u),
                aglTrue = Mathf.Lerp(a.aglTrue, b.aglTrue, u), aglEst = Mathf.Lerp(a.aglEst, b.aglEst, u),
                gate = Mathf.Lerp(a.gate, b.gate, u), acc = b.acc, r = b.r, fault = b.fault, fuel = Mathf.Lerp(a.fuel, b.fuel, u)
            };
        }

        void LateUpdate()
        {
            if (tracks.Count == 0) return;
            float maxT = 0f; foreach (var t in tracks) maxT = Mathf.Max(maxT, t.endT);
            clock = Mathf.Min(clock + Time.deltaTime * speed, maxT + 3f);
            Vector3 min = Vector3.one * float.MaxValue, max = Vector3.one * float.MinValue;
            foreach (var t in tracks)
            {
                var r = At(t, clock); if (r == null) continue;
                var pos = ToUnity(r.x, r.y, r.z); var est = ToUnity(r.ex, r.ey, r.ez);
                t.body.position = pos; t.ghost.position = est;
                t.link.SetPosition(0, pos); t.link.SetPosition(1, est);
                min = Vector3.Min(min, Vector3.Min(pos, est)); max = Vector3.Max(max, Vector3.Max(pos, est));
            }
            // frame all variants
            Vector3 c = (min + max) * 0.5f; float spread = Mathf.Max((max - min).magnitude, 30f);
            if (cam != null)
            {
                float d = spread * 1.1f + 60f;
                cam.transform.position = Vector3.Lerp(cam.transform.position, c + new Vector3(-0.35f, 0.35f, -1f).normalized * d, 0.15f);
                cam.transform.LookAt(c);
                float vis = Mathf.Max(1f, d * 0.012f);
                foreach (var t in tracks) { t.body.localScale = new Vector3(2.4f, 1f, 2.4f) * vis; t.ghost.localScale = Vector3.one * 3f * vis; foreach (var lr in new[] { t.link, t.trail }) lr.widthMultiplier = vis * 0.25f; }
            }
            foreach (var t in tracks)
            {
                var r = At(t, clock); if (r == null) continue;
                t.trail.positionCount += 1; t.trail.SetPosition(t.trail.positionCount - 1, ToUnity(r.x, r.y, r.z));
                if (t.trail.positionCount > 4000) t.trail.positionCount = 4000;
            }
        }

        void OnGUI()
        {
            if (tracks.Count == 0) return;
            if (style == null) style = new GUIStyle(GUI.skin.label);
            style.fontSize = Mathf.Max(14, Mathf.RoundToInt(Screen.height * 0.026f));
            float lineH = style.fontSize * 1.35f;
            var box = new Rect(8, 8, style.fontSize * 36f, lineH * (tracks.Count * 3 + 2));
            var prev = GUI.color; GUI.color = new Color(0, 0, 0, 0.7f); GUI.DrawTexture(box, Texture2D.whiteTexture); GUI.color = prev;
            float y = box.y + 6;
            style.normal.textColor = Color.white;
            GUI.Label(new Rect(box.x + 8, y, box.width, lineH), $"t = {clock:F0} s     solid = true lander, ghost = filter estimate", style); y += lineH;
            foreach (var t in tracks)
            {
                var r = At(t, clock); if (r == null) continue;
                bool ended = clock >= t.endT;
                style.normal.textColor = t.color;
                GUI.Label(new Rect(box.x + 8, y, box.width, lineH), t.label + (ended ? "   (touchdown / end)" : ""), style); y += lineH;
                style.normal.textColor = Color.white;
                GUI.Label(new Rect(box.x + 8, y, box.width, lineH), $"  AGL true {r.aglTrue:F0} m   est {r.aglEst:F0} m   error {r.aglEst - r.aglTrue:F0} m", style); y += lineH;
                GUI.Label(new Rect(box.x + 8, y, box.width, lineH), $"  gate +-{r.gate:F0} m   altimeter {(r.acc > 0.5 ? "used" : "rejected")}   fuel {r.fuel:F0} kg", style); y += lineH;
            }
        }
    }
}
