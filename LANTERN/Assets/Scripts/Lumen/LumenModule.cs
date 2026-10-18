using UnityEngine;

namespace SensorTrust.Lumen
{
    /// <summary>
    /// LUMEN core loop: scan -> build height patch around the ESTIMATED position -> match against the
    /// stored map -> publish a position correction and confidence. Active below activeBelowM above ground.
    /// </summary>
    [RequireComponent(typeof(LidarScanner))]
    public class LumenModule : MonoBehaviour
    {
        public Terrain map;
        public float scanHz = 2f;
        public float activeBelowM = 2500f;
        public int patchCells = 48;
        public float cellM = 8f;                 // finest patch cell (about the DEM resolution)

        [Tooltip("Grow the cell with altitude so each cell still collects >= 2 lidar points (coarse fix high, fine fix low).")]
        public bool adaptiveCell = true;
        public float cellPerBeamSpacing = 1.6f;
        public float LastCellM { get; private set; }

        [Header("Simulated navigation error (what the filter believes minus truth)")]
        public Vector3 positionErrorM = new Vector3(60f, 0f, -40f);

        public MatchResult Last { get; private set; }
        public HeightPatch LastPatch { get; private set; }
        public float LastScanTime { get; private set; }
        public int LastPointCount { get; private set; }

        LidarScanner scanner;
        float nextScan;

        void Awake() { scanner = GetComponent<LidarScanner>(); }

        public Vector3 EstimatedPosition => transform.position + positionErrorM;

        void FixedUpdate()
        {
            if (map == null || Time.time < nextScan) return;
            float agl = transform.position.y - map.SampleHeight(transform.position) - map.transform.position.y;
            if (agl > activeBelowM) return;
            nextScan = Time.time + 1f / scanHz;
            RunScan();
        }

        public void RunScan()
        {
            if (scanner == null) scanner = GetComponent<LidarScanner>();
            var pts = scanner.Scan();
            float cell = cellM;
            if (adaptiveCell && map != null)
            {
                float agl = transform.position.y - map.SampleHeight(transform.position) - map.transform.position.y;
                float spacing = 2f * agl * Mathf.Tan(scanner.fovDeg * 0.5f * Mathf.Deg2Rad) / Mathf.Max(1, scanner.beams - 1);
                cell = Mathf.Max(cellM, cellPerBeamSpacing * spacing);
            }
            LastCellM = cell;
            var patch = new HeightPatch(patchCells, cell, new Vector2(EstimatedPosition.x, EstimatedPosition.z));
            // The lander places lidar points using its estimated pose, so they inherit the position error.
            foreach (var p in pts) patch.Add(p + positionErrorM);
            LastPatch = patch;
            LastPointCount = pts.Count;
            Last = PatchMatcher.Match(patch, map);
            LastScanTime = Time.time;
        }
    }
}
