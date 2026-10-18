using System.Collections.Generic;
using UnityEngine;

namespace SensorTrust.Lumen
{
    /// <summary>
    /// Simulated scanning lidar: a beams x beams grid, each beam one raycast against the terrain,
    /// with range noise and dropouts. Works in shadow (it brings its own light).
    /// </summary>
    public class LidarScanner : MonoBehaviour
    {
        public int beams = 64;
        public float fovDeg = 40f;
        public float maxRangeM = 3000f;
        public float rangeNoiseBaseM = 0.05f;
        public float rangeNoisePerM = 0.001f;   // sigma grows with range
        [Range(0f, 1f)] public float dropoutProb = 0.02f;
        public int seed = 1;

        TerrainCollider terrainCollider;
        System.Random rng;

        void Awake()
        {
            rng = new System.Random(seed);
        }

        TerrainCollider Ground()
        {
            if (terrainCollider == null)
            {
                var t = FindFirstObjectByType<Terrain>();
                if (t != null) terrainCollider = t.GetComponent<TerrainCollider>();
            }
            return terrainCollider;
        }

        float Gauss()
        {
            double u1 = 1.0 - rng.NextDouble(), u2 = rng.NextDouble();
            return (float)(System.Math.Sqrt(-2.0 * System.Math.Log(u1)) * System.Math.Cos(2.0 * System.Math.PI * u2));
        }

        /// <summary>One full scan. Returns world-space hit points as the lidar reports them (noisy).</summary>
        public List<Vector3> Scan(Transform sensorFrame = null)
        {
            if (rng == null) rng = new System.Random(seed);
            var pts = new List<Vector3>(beams * beams);
            var col = Ground();
            if (col == null) return pts;
            var frame = sensorFrame != null ? sensorFrame : transform;
            Vector3 origin = frame.position;
            float half = fovDeg * 0.5f;

            for (int a = 0; a < beams; a++)
            {
                float az = Mathf.Lerp(-half, half, a / (float)(beams - 1));
                for (int b = 0; b < beams; b++)
                {
                    if (rng.NextDouble() < dropoutProb) continue;
                    float el = Mathf.Lerp(-half, half, b / (float)(beams - 1));
                    // Boresight is body -up (nadir); az/el tilt it about body X and Z.
                    Vector3 dir = frame.rotation * (Quaternion.Euler(el, 0f, az) * Vector3.down);
                    if (!col.Raycast(new Ray(origin, dir), out var hit, maxRangeM)) continue;
                    float r = hit.distance + Gauss() * (rangeNoiseBaseM + rangeNoisePerM * hit.distance);
                    pts.Add(origin + dir * r);
                }
            }
            return pts;
        }
    }
}
