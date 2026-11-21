using UnityEngine;

namespace SensorTrust.Experiments
{
    /// <summary>Evaluation only: records an actual PhysX terrain contact.
    /// Never read by navigation or guidance.</summary>
    public sealed class TerrainTouchdownRecorder : MonoBehaviour
    {
        public bool Touched { get; private set; }
        public Vector3 ContactVelocity { get; private set; }
        void OnCollisionEnter(Collision collision)
        {
            if(Touched || !(collision.collider is TerrainCollider)) return;
            Touched=true;
            ContactVelocity=collision.relativeVelocity;
        }
    }
}
