using UnityEngine;

namespace SensorTrust.Lumen
{
    /// <summary>
    /// LUMEN height patch: lidar points averaged into a square grid in the same layout as the DEM,
    /// with a per-cell confidence (many agreeing points = high, few or scattered = low).
    /// </summary>
    public class HeightPatch
    {
        public readonly int size;
        public readonly float cellM;
        public Vector2 originXZ;   // world XZ of cell (0,0) corner

        readonly float[] sum, sumSq;
        readonly int[] count;

        public HeightPatch(int size, float cellM, Vector2 centerXZ)
        {
            this.size = size;
            this.cellM = cellM;
            originXZ = centerXZ - Vector2.one * (size * cellM * 0.5f);
            sum = new float[size * size];
            sumSq = new float[size * size];
            count = new int[size * size];
        }

        public bool Add(Vector3 p)
        {
            int i = Mathf.FloorToInt((p.x - originXZ.x) / cellM);
            int j = Mathf.FloorToInt((p.z - originXZ.y) / cellM);
            if (i < 0 || j < 0 || i >= size || j >= size) return false;
            int k = j * size + i;
            sum[k] += p.y; sumSq[k] += p.y * p.y; count[k]++;
            return true;
        }

        public int Count(int i, int j) => count[j * size + i];

        public bool TryHeight(int i, int j, out float h, int minPoints = 2)
        {
            int k = j * size + i;
            h = count[k] > 0 ? sum[k] / count[k] : 0f;
            return count[k] >= minPoints;
        }

        /// <summary>Std dev of heights inside a cell (m); 0 with fewer than 2 points.</summary>
        public float Spread(int i, int j)
        {
            int k = j * size + i;
            if (count[k] < 2) return 0f;
            float m = sum[k] / count[k];
            return Mathf.Sqrt(Mathf.Max(0f, sumSq[k] / count[k] - m * m));
        }

        /// <summary>0..1 confidence: saturates with point count, falls with spread.</summary>
        public float Confidence(int i, int j)
        {
            int k = j * size + i;
            if (count[k] == 0) return 0f;
            float n = 1f - Mathf.Exp(-count[k] / 3f);
            return n / (1f + Spread(i, j));
        }

        public int FilledCells(int minPoints = 2)
        {
            int n = 0;
            for (int k = 0; k < count.Length; k++) if (count[k] >= minPoints) n++;
            return n;
        }
    }
}
