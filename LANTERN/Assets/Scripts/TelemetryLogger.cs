using System;
using System.Globalization;
using System.IO;
using UnityEngine;

namespace SensorTrust
{
    /// <summary>
    /// Writes one CSV per Play session to &lt;project&gt;/../out/runs and a one-line summary to runs_summary.csv.
    /// Lines are flushed as they are written, so data survives stopping Play mid-run.
    /// </summary>
    public class TelemetryLogger : MonoBehaviour
    {
        public LanderController lander;
        public DescentAutopilot autopilot;
        public Lumen.LumenModule lumen;
        public Terrain terrain;
        public float intervalS = 0.5f;           // sim seconds between rows
        public string scenario = "site04_descent";

        public string CsvPath { get; private set; }

        StreamWriter w;
        float next;
        string runId, dir;
        float startAgl, startTime;
        bool summarized;
        float minAgl = float.MaxValue, maxSpeed, lumenValidRows, rows;
        float firstFixAgl = float.NaN;
        double maxShiftErr;
        static readonly CultureInfo C = CultureInfo.InvariantCulture;

        void Start()
        {
            dir = Path.GetFullPath(Path.Combine(Application.dataPath, "../../out/runs"));
            Directory.CreateDirectory(dir);
            runId = DateTime.Now.ToString("yyyyMMdd_HHmmss");
            CsvPath = Path.Combine(dir, $"run_{runId}.csv");
            w = new StreamWriter(CsvPath, false) { AutoFlush = true };
            w.WriteLine("t,agl_m,msl_m,x_m,z_m,vx,vy,vz,speed,throttle,fuel_kg,tilt_deg,time_scale," +
                        "lumen_valid,lumen_shift_x,lumen_shift_z,lumen_conf,lumen_rms,lumen_cell_m,inj_err_x,inj_err_z,shift_err_m,touched_down");
            startTime = Time.time;
        }

        void FixedUpdate()
        {
            if (w == null || lander == null || Time.time < next) return;
            next = Time.time + intervalS;
            var p = lander.transform.position;
            var v = lander.Body.linearVelocity;
            float agl = p.y - terrain.SampleHeight(p) - terrain.transform.position.y;
            if (rows == 0) startAgl = agl;
            var L = lumen != null ? lumen.Last : default;
            bool valid = lumen != null && L.valid;
            float shiftErr = float.NaN;
            if (valid)
            {
                // Correct shift = -injected error; residual is what LUMEN got wrong.
                float ex = L.shiftXZ.x + lumen.positionErrorM.x, ez = L.shiftXZ.y + lumen.positionErrorM.z;
                shiftErr = Mathf.Sqrt(ex * ex + ez * ez);
                maxShiftErr = Math.Max(maxShiftErr, shiftErr);
                lumenValidRows++;
                if (float.IsNaN(firstFixAgl)) firstFixAgl = agl;
            }
            rows++;
            minAgl = Mathf.Min(minAgl, agl);
            maxSpeed = Mathf.Max(maxSpeed, v.magnitude);
            w.WriteLine(string.Join(",",
                F(Time.time), F(agl), F(p.y), F(p.x), F(p.z), F(v.x), F(v.y), F(v.z), F(v.magnitude),
                F(lander.throttle), F(lander.Fuel), F(Vector3.Angle(lander.transform.up, Vector3.up)), F(Time.timeScale),
                valid ? 1 : 0, F(valid ? L.shiftXZ.x : float.NaN), F(valid ? L.shiftXZ.y : float.NaN),
                F(valid ? L.confidence : float.NaN), F(valid ? L.rmsM : float.NaN), F(lumen != null ? lumen.LastCellM : float.NaN),
                F(lumen != null ? lumen.positionErrorM.x : 0f), F(lumen != null ? lumen.positionErrorM.z : 0f),
                F(shiftErr), autopilot != null && autopilot.TouchedDown ? 1 : 0));

            if (!summarized && autopilot != null && autopilot.TouchedDown) WriteSummary("touchdown");
        }

        void WriteSummary(string reason)
        {
            if (summarized || rows == 0) return;
            summarized = true;
            string path = Path.Combine(dir, "runs_summary.csv");
            bool header = !File.Exists(path);
            using (var s = new StreamWriter(path, true))
            {
                if (header)
                    s.WriteLine("run_id,scenario,end_reason,start_agl_m,duration_s,impact_vertical_mps,impact_horizontal_mps,fuel_left_kg,max_speed_mps,lumen_valid_fraction,lumen_first_fix_agl_m,lumen_max_shift_err_m,csv");
                s.WriteLine(string.Join(",", runId, scenario, reason, F(startAgl), F(Time.time - startTime),
                    F(autopilot != null ? autopilot.ImpactVertical : float.NaN), F(autopilot != null ? autopilot.ImpactHorizontal : float.NaN),
                    F(lander.Fuel), F(maxSpeed), F(rows > 0 ? lumenValidRows / rows : 0f), F(firstFixAgl), F((float)maxShiftErr),
                    Path.GetFileName(CsvPath)));
            }
            Debug.Log($"[Telemetry] {reason}: {CsvPath}");
        }

        void OnDestroy()
        {
            if (w == null) return;
            try { WriteSummary(autopilot != null && autopilot.TouchedDown ? "touchdown" : "stopped"); }
            catch (Exception e) { Debug.LogWarning("[Telemetry] summary failed: " + e.Message); }
            w.Dispose();
        }

        static string F(float x) => float.IsNaN(x) ? "" : x.ToString("0.###", C);
    }
}
