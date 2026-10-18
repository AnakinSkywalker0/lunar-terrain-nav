using UnityEngine;

namespace SensorTrust.Lumen
{
    public struct MatchResult
    {
        public bool valid;
        public Vector2 shiftXZ;     // correction to add to the estimated position (m)
        public float rmsM;          // residual at the best fit
        public float confidence;    // 0..1: one clear best fit = high, many similar fits = low
        public int cellsUsed;
    }

    /// <summary>
    /// LUMEN match step: slide the live height patch over the stored map near the estimated
    /// position; the best-fitting shift corrects the position.
    /// </summary>
    public static class PatchMatcher
    {
        /// <param name="searchCells">Search +/- this many cells in X and Z.</param>
        public static MatchResult Match(HeightPatch patch, Terrain map, int searchCells = 16, int minCells = 40)
        {
            int n = patch.size, s = searchCells, w = n + 2 * s;
            var td = map.terrainData;
            var origin = map.transform.position;

            // Pre-sample the stored map once over patch + search margin (same cell size as the patch).
            var stored = new float[w * w];
            for (int j = 0; j < w; j++)
                for (int i = 0; i < w; i++)
                {
                    float x = patch.originXZ.x + (i - s + 0.5f) * patch.cellM;
                    float z = patch.originXZ.y + (j - s + 0.5f) * patch.cellM;
                    stored[j * w + i] = map.SampleHeight(new Vector3(x, 0f, z)) + origin.y;
                }

            // Patch cells with enough points.
            var pi = new System.Collections.Generic.List<int>();
            var pj = new System.Collections.Generic.List<int>();
            var ph = new System.Collections.Generic.List<float>();
            for (int j = 0; j < n; j++)
                for (int i = 0; i < n; i++)
                    if (patch.TryHeight(i, j, out float h)) { pi.Add(i); pj.Add(j); ph.Add(h); }

            var res = new MatchResult { cellsUsed = ph.Count };
            if (ph.Count < minCells) return res;

            int side = 2 * s + 1;
            var cost = new float[side * side];
            float best = float.MaxValue; int bi = 0, bj = 0;
            double costSum = 0;
            for (int dj = -s; dj <= s; dj++)
                for (int di = -s; di <= s; di++)
                {
                    // Remove the mean offset: lidar uses its own height datum, only the shape must match.
                    double diffSum = 0, diffSq = 0;
                    for (int k = 0; k < ph.Count; k++)
                    {
                        float d = ph[k] - stored[(pj[k] + s + dj) * w + (pi[k] + s + di)];
                        diffSum += d; diffSq += d * d;
                    }
                    double m = diffSum / ph.Count;
                    float c = (float)(diffSq / ph.Count - m * m);
                    cost[(dj + s) * side + (di + s)] = c;
                    costSum += c;
                    if (c < best) { best = c; bi = di; bj = dj; }
                }

            // Confidence: best fit vs the mean of fits outside its neighbourhood (flat ground = no contrast).
            double farSum = 0; int farN = 0;
            for (int dj = -s; dj <= s; dj++)
                for (int di = -s; di <= s; di++)
                    if (Mathf.Abs(di - bi) > 2 || Mathf.Abs(dj - bj) > 2)
                    { farSum += cost[(dj + s) * side + (di + s)]; farN++; }
            float far = farN > 0 ? (float)(farSum / farN) : best;

            res.valid = true;
            res.rmsM = Mathf.Sqrt(Mathf.Max(0f, best));
            res.confidence = Mathf.Clamp01(1f - (best + 0.01f) / (far + 0.01f));
            // Patch content sits at +shift in the stored map, so the true position is estimate + shift.
            res.shiftXZ = new Vector2(bi, bj) * patch.cellM;
            return res;
        }
    }
}
