using UnityEngine;

namespace SensorTrust
{
    /// <summary>
    /// Vertical-speed-profile descent: brake along v_des = -(vTouch + sqrt(2 a h)) with a derated deceleration,
    /// hold the body upright and null horizontal drift by tilting. Disable this component to fly manually.
    /// </summary>
    [RequireComponent(typeof(LanderController))]
    public class DescentAutopilot : MonoBehaviour
    {
        public Terrain terrain;
        public float gravity = 1.62f;            // lunar surface gravity, m/s^2
        public float touchdownSpeed = 0.5f;      // target vertical speed at contact, m/s
        public float decelMargin = 0.5f;         // fraction of available net deceleration used by the profile
        public float velGain = 4f;               // 1/s, throttle response to velocity error
        public float maxTiltDeg = 10f;
        public float attitudeWn = 2f;            // rad/s, attitude loop bandwidth

        [Header("Time warp (high-altitude coast only; physics step is unchanged)")]
        public float warpMax = 8f;
        public float warpAboveM = 8000f;         // full warp above this AGL
        public float realtimeBelowM = 4000f;     // 1x below this AGL, linear blend between

        public bool TouchedDown { get; private set; }
        public float ImpactVertical { get; private set; }   // m/s, downward positive
        public float ImpactHorizontal { get; private set; }
        public float TouchdownTime { get; private set; }
        public float Agl { get; private set; }

        LanderController lander;
        Rigidbody rb;
        float footOffset;
        Vector3 lastVel;
        float nextLogAgl = float.MaxValue;

        void Start()
        {
            lander = GetComponent<LanderController>();
            rb = lander.Body != null ? lander.Body : GetComponent<Rigidbody>();
            lander.manualControl = false;
            Application.runInBackground = true;   // keep ticking when the editor window isn't focused
            if (terrain == null) terrain = Terrain.activeTerrain;

            float minY = float.MaxValue;
            foreach (var c in GetComponentsInChildren<Collider>()) minY = Mathf.Min(minY, c.bounds.min.y);
            footOffset = minY == float.MaxValue ? 0f : transform.position.y - minY;
        }

        void FixedUpdate()
        {
            if (rb == null) return;
            var v = rb.linearVelocity;
            if (!TouchedDown) lastVel = v;

            var p = transform.position;
            Agl = p.y - footOffset - (terrain.SampleHeight(p) + terrain.transform.position.y);

            if (Agl < nextLogAgl)
            {
                Debug.Log($"[Autopilot] t={Time.time:F0}s agl={Agl:F0} m vy={v.y:F1} m/s throttle={lander.throttle:F2} fuel={lander.Fuel:F0} kg");
                nextLogAgl = Agl > 12000f ? Mathf.Floor(Agl / 10000f) * 10000f : Agl > 3000f ? Mathf.Floor(Agl / 2000f) * 2000f : Mathf.Floor(Agl / 500f) * 500f;
            }

            Time.timeScale = TouchedDown ? 1f
                : Mathf.Lerp(1f, warpMax, Mathf.InverseLerp(realtimeBelowM, warpAboveM, Agl));

            if (TouchedDown) { lander.Command(0f, Vector3.zero); return; }

            float mass = rb.mass;
            float aMax = lander.maxThrustN / mass;
            float aNet = Mathf.Max(0.1f, aMax - gravity) * decelMargin;
            float h = Mathf.Max(0f, Agl - 1f);
            float vDes = -(touchdownSpeed + Mathf.Sqrt(2f * aNet * h));
            float aCmd = gravity + velGain * (vDes - v.y);

            // Tilt toward cancelling horizontal velocity.
            Vector3 vh = new Vector3(v.x, 0f, v.z);
            Vector3 tiltDir = -vh * 0.05f;
            tiltDir = Vector3.ClampMagnitude(tiltDir, Mathf.Tan(maxTiltDeg * Mathf.Deg2Rad));
            Vector3 upDes = (Vector3.up + tiltDir).normalized;

            float cos = Mathf.Max(0.5f, Vector3.Dot(transform.up, Vector3.up));
            float throttle = aCmd * mass / (lander.maxThrustN * cos);
            // Free-fall until the profile says brake (avoids burning fuel early).
            if (v.y > vDes) throttle = 0f;

            Vector3 errWorld = Vector3.Cross(transform.up, upDes);
            Vector3 errBody = transform.InverseTransformDirection(errWorld);
            Vector3 wBody = transform.InverseTransformDirection(rb.angularVelocity);
            float inertia = rb.inertiaTensor.magnitude / 1.7320508f;
            Vector3 torque = inertia * (attitudeWn * attitudeWn * errBody - 2f * attitudeWn * wBody);
            // Kill yaw rate only.
            torque.y = -inertia * 2f * attitudeWn * wBody.y;
            torque = Vector3.ClampMagnitude(torque, lander.attitudeTorqueNm);

            lander.Command(throttle, torque);
        }

        void OnDisable() { Time.timeScale = 1f; }

        void OnCollisionEnter(Collision c)
        {
            if (TouchedDown) return;
            TouchedDown = true;
            TouchdownTime = Time.time;
            ImpactVertical = -lastVel.y;
            ImpactHorizontal = new Vector2(lastVel.x, lastVel.z).magnitude;
            Debug.Log($"[Autopilot] TOUCHDOWN t={Time.time:F1}s vertical={ImpactVertical:F2} m/s horizontal={ImpactHorizontal:F2} m/s tilt={Vector3.Angle(transform.up, Vector3.up):F1} deg fuel={lander.Fuel:F0} kg");
        }
    }
}
