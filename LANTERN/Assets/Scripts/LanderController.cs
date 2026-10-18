using UnityEngine;

namespace SensorTrust
{
    /// <summary>Rigid-body lander: throttleable main engine, attitude torque, finite fuel.</summary>
    [RequireComponent(typeof(Rigidbody))]
    public class LanderController : MonoBehaviour
    {
        public float dryMassKg = 1200f;
        public float fuelKg = 800f;
        public float maxThrustN = 6000f;      // about 2x lunar weight at full tank
        public float ispSeconds = 300f;
        public float attitudeTorqueNm = 4000f;
        public float throttleRate = 0.5f;     // throttle change per second

        [Range(0f, 1f)] public float throttle;
        public bool manualControl = true;

        public float Fuel => fuelKg;
        public Rigidbody Body { get; private set; }

        const float G0 = 9.80665f;

        void Awake()
        {
            Body = GetComponent<Rigidbody>();
            Body.mass = dryMassKg + fuelKg;
            Body.angularDamping = 0.5f;
        }

        void Update()
        {
            if (!manualControl) return;
            if (Input.GetKey(KeyCode.LeftShift)) throttle += throttleRate * Time.deltaTime;
            if (Input.GetKey(KeyCode.LeftControl)) throttle -= throttleRate * Time.deltaTime;
            if (Input.GetKeyDown(KeyCode.X)) throttle = 0f;
            if (Input.GetKeyDown(KeyCode.Z)) throttle = 1f;
            throttle = Mathf.Clamp01(throttle);
        }

        void FixedUpdate()
        {
            if (fuelKg <= 0f) throttle = 0f;
            float thrust = throttle * maxThrustN;
            if (thrust > 0f)
            {
                Body.AddRelativeForce(Vector3.up * thrust);
                float burn = thrust / (ispSeconds * G0) * Time.fixedDeltaTime;
                fuelKg = Mathf.Max(0f, fuelKg - burn);
                Body.mass = dryMassKg + fuelKg;
            }

            if (manualControl)
            {
                float pitch = Input.GetAxisRaw("Vertical");
                float roll = -Input.GetAxisRaw("Horizontal");
                float yaw = (Input.GetKey(KeyCode.E) ? 1f : 0f) - (Input.GetKey(KeyCode.Q) ? 1f : 0f);
                Body.AddRelativeTorque(new Vector3(pitch, yaw, roll) * attitudeTorqueNm);
            }
        }

        /// <summary>For guidance code: command throttle and body-frame torque directly.</summary>
        public void Command(float throttle01, Vector3 torqueBody)
        {
            throttle = Mathf.Clamp01(throttle01);
            if (!manualControl) Body.AddRelativeTorque(torqueBody);
        }
    }
}
