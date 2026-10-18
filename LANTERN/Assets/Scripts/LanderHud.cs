using UnityEngine;

namespace SensorTrust
{
    /// <summary>HUD: true altitude above terrain, speeds, fuel, throttle, LUMEN. Text scales with screen height.</summary>
    public class LanderHud : MonoBehaviour
    {
        public LanderController lander;
        public Terrain terrain;
        public Lumen.LumenModule lumen;
        [Tooltip("Font size as a fraction of screen height.")]
        public float fontFraction = 0.03f;

        GUIStyle style;

        void OnGUI()
        {
            if (lander == null) return;
            if (style == null) style = new GUIStyle(GUI.skin.label) { richText = false, wordWrap = false };
            style.fontSize = Mathf.Max(14, Mathf.RoundToInt(Screen.height * fontFraction));
            style.normal.textColor = Color.white;

            var p = lander.transform.position;
            float agl = terrain != null ? p.y - terrain.SampleHeight(p) - terrain.transform.position.y : p.y;
            var v = lander.Body.linearVelocity;
            float tilt = Vector3.Angle(lander.transform.up, Vector3.up);
            string lum = lumen != null && lumen.Last.valid
                ? $"LUMEN  shift ({lumen.Last.shiftXZ.x:F0},{lumen.Last.shiftXZ.y:F0}) m  conf {lumen.Last.confidence:F2}  rms {lumen.Last.rmsM:F1} m  cell {lumen.LastCellM:F0} m"
                : "LUMEN  no fix";
            string text =
                $"Alt (MSL)  {p.y:F1} m\nAlt (AGL)  {agl:F1} m\n" +
                $"V vert  {v.y:F2} m/s   V horiz  {new Vector2(v.x, v.z).magnitude:F2} m/s\n" +
                $"Tilt  {tilt:F1} deg\nThrottle  {lander.throttle * 100f:F0} %   Fuel  {lander.Fuel:F0} kg\n" +
                lum + "\n" +
                "Shift/Ctrl throttle  Z full  X cut  WASD pitch/roll  Q/E yaw";

            var content = new GUIContent(text);
            Vector2 size = style.CalcSize(content);
            float pad = style.fontSize * 0.5f;
            var box = new Rect(8, 8, size.x + 2 * pad, size.y + 2 * pad);
            var prev = GUI.color;
            GUI.color = new Color(0f, 0f, 0f, 0.7f);
            GUI.DrawTexture(box, Texture2D.whiteTexture);
            GUI.color = prev;
            GUI.Label(new Rect(box.x + pad, box.y + pad, size.x + 4, size.y + 4), content, style);
        }
    }
}
