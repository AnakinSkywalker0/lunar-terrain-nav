using System;
using UnityEngine;

namespace SensorTrust.Experiments.NavigationV3
{
    /// <summary>Live view and controls; runs the same simulation class used by batch validation.</summary>
    public sealed class NavigationDemoV3 : MonoBehaviour
    {
        public TextAsset terrain,utilityModel;
        public GameObject landerVisual;
        public Camera overview,vehicleCamera;
        public bool useMl;
        public int conditionIndex;
        public NavigationSimulation Simulation { get; private set; }
        public bool Paused { get; set; }
        public string Error { get; private set; }
        public string ModelWarning { get; private set; }
        readonly string[] conditions={"nominal","range_spike","range_dropout","scan_dropout","gross_map_shift","gross_relief"};
        Transform estimateMarker,trueMarker;
        GameObject markers;
        Material estimateMaterial,targetMaterial,trueMaterial;
        float accumulator;
        int speed=1;
        void Start() { Restart(); }
        public void Restart()
        {
            Cleanup(); Error=null; ModelWarning=null; Paused=false; accumulator=0;
            try
            {
                if(terrain==null) throw new InvalidOperationException("Terrain asset missing; prepare navigation v3 inputs first");
                ScanUtilityPolicy model=null;
                if(useMl)
                {
                    if(utilityModel==null) ModelWarning="ML unavailable; using classical measurement weighting";
                    else
                    {
                        try { model=new ScanUtilityPolicy(utilityModel.text); }
                        catch(Exception ex) { ModelWarning="Invalid ML model; classical weighting: "+ex.Message; Debug.LogWarning(ModelWarning); }
                    }
                }
                Simulation=new NavigationSimulation(new LandingCase { site="development",condition=conditions[conditionIndex],
                    arm=useMl?"ml_terminal":"classical_terminal",altitude=500,seed=1201 },new SimulationSettings(),TerrainTile.Load(terrain.bytes),model,true);
                if(landerVisual!=null)
                {
                    var visual=Instantiate(landerVisual,Simulation.Body.transform,false);
                    foreach(var collider in visual.GetComponentsInChildren<Collider>()) collider.enabled=false;
                    foreach(var body in visual.GetComponentsInChildren<Rigidbody>()) { body.isKinematic=true; body.detectCollisions=false; }
                }
                else
                {
                    var visual=GameObject.CreatePrimitive(PrimitiveType.Cylinder); visual.name="Lander visual";
                    visual.transform.SetParent(Simulation.Body.transform,false); visual.transform.localScale=new Vector3(3,2,3);
                    visual.GetComponent<Collider>().enabled=false;
                }
                markers=new GameObject("Evaluation overlays (not navigation inputs)");
                var estimate=GameObject.CreatePrimitive(PrimitiveType.Sphere); estimate.transform.SetParent(markers.transform,false);
                estimate.layer=9;
                estimate.name="Estimated position (enlarged)"; estimate.GetComponent<Collider>().enabled=false; estimate.transform.localScale=Vector3.one*8;
                estimateMaterial=new Material(Shader.Find("Unlit/Color")) { color=new Color(1,.55f,.1f) };
                estimate.GetComponent<Renderer>().sharedMaterial=estimateMaterial; estimateMarker=estimate.transform;
                var actual=GameObject.CreatePrimitive(PrimitiveType.Sphere); actual.transform.SetParent(markers.transform,false);
                actual.name="Actual position (enlarged evaluation marker)"; actual.layer=9;
                actual.GetComponent<Collider>().enabled=false; actual.transform.localScale=Vector3.one*12;
                trueMaterial=new Material(Shader.Find("Unlit/Color")) { color=new Color(.15f,.7f,1) };
                actual.GetComponent<Renderer>().sharedMaterial=trueMaterial; trueMarker=actual.transform;
                var target=GameObject.CreatePrimitive(PrimitiveType.Cylinder); target.transform.SetParent(markers.transform,false);
                target.name="Map target footprint"; target.GetComponent<Collider>().enabled=false;
                Simulation.Map.Sample(0,0,out float height);
                target.transform.position=new Vector3(Simulation.MapShift.x,height+1,Simulation.MapShift.y); target.transform.localScale=new Vector3(20,.3f,20);
                targetMaterial=new Material(Shader.Find("Unlit/Color")) { color=new Color(.15f,.9f,.45f) };
                target.GetComponent<Renderer>().sharedMaterial=targetMaterial;
            }
            catch(Exception ex) { Error=ex.Message; Cleanup(); Debug.LogException(ex); }
        }
        void Update()
        {
            if(Simulation==null) return;
            try
            {
                if(!Paused && !Simulation.Finished)
                {
                    accumulator+=Mathf.Min(Time.deltaTime,.2f)*speed;
                    while(accumulator>=Simulation.Settings.dt && !Simulation.Finished)
                    { Simulation.Step(); accumulator-=Simulation.Settings.dt; }
                }
                if(estimateMarker!=null) estimateMarker.position=Simulation.Navigation.Filter.Position;
                if(trueMarker!=null) trueMarker.position=Simulation.Body.position;
                if(vehicleCamera!=null)
                {
                    vehicleCamera.transform.position=Simulation.Body.position+new Vector3(9,6,11);
                    vehicleCamera.transform.LookAt(Simulation.Body.position+Vector3.up*1.5f);
                }
            }
            catch(Exception ex) { Error=ex.Message; Paused=true; Debug.LogException(ex); }
        }
        void OnGUI()
        {
            GUILayout.BeginArea(new Rect(16,16,480,460),GUI.skin.box);
            GUILayout.Label("LANTERN — live uncertainty-aware landing");
            GUILayout.Label("Site01 / 3-DOF / synthetic sensors and correlated map-error proxy");
            bool requestedMl=GUILayout.Toggle(useMl,"Enable experimental frozen ML advice (applies on restart)");
            useMl=requestedMl;
            GUILayout.Label("Scenario (applies on restart)");
            conditionIndex=GUILayout.SelectionGrid(conditionIndex,conditions,2);
            GUILayout.BeginHorizontal();
            if(GUILayout.Button("Restart")) Restart();
            if(GUILayout.Button(Paused?"Resume":"Pause")) Paused=!Paused;
            if(GUILayout.Button(speed==1?"4x speed":"1x speed")) speed=speed==1?4:1;
            GUILayout.EndHorizontal();
            if(Error!=null) GUILayout.Label("ERROR: "+Error);
            if(ModelWarning!=null) GUILayout.Label(ModelWarning);
            if(Simulation!=null)
            {
                var nav=Simulation.Navigation.Filter; bool validAltitude=nav.Altitude(Simulation.Map,out double agl,out double sigma);
                GUILayout.Label("Running: "+Simulation.Case.arm+" / "+Simulation.Case.condition);
                if(Simulation.MlFallbackCount>0) GUILayout.Label("Classical fallback used for "+Simulation.MlFallbackCount+" unavailable/invalid ML predictions");
                GUILayout.Label($"Time {Simulation.Time:F1}s   Mode: {Simulation.Guidance.Mode}");
                GUILayout.Label(validAltitude ? $"Estimated altitude {agl:F1} m   sigma {sigma:F2} m" : "Altitude unknown — degraded guidance");
                GUILayout.Label($"Estimated lateral speed {new Vector2(nav.Velocity.x,nav.Velocity.z).magnitude:F2} m/s");
                GUILayout.Label($"Horizontal sigma {nav.HorizontalSigma:F2} m   Fuel {Simulation.Fuel:F1} kg");
                GUILayout.Label(nav.LastRangeTime<0?"Altitude: waiting for first valid reading":$"Altitude age {Simulation.Time-nav.LastRangeTime:F2}s");
                GUILayout.Label(nav.LastTerrainTime<0?"Terrain: no accepted fix":$"Terrain fix age {Simulation.Time-nav.LastTerrainTime:F2}s");
                if(Simulation.Finished)
                {
                    var r=Simulation.Result;
                    GUILayout.Label($"{r.termination}: absolute miss {r.absoluteMiss:F2} m / map-target miss {r.mapMiss:F2} m");
                    GUILayout.Label($"Impact vertical {r.impactVertical:F2}, lateral {r.impactHorizontal:F2} m/s");
                    GUILayout.Label("10 m map-target landing: "+(r.map10?"PASS":"FAIL"));
                }
            }
            GUILayout.Label("Cyan: vehicle. Orange: estimate. Markers enlarged; inset shows the lander. Green: map target.");
            GUILayout.EndArea();
        }
        void Cleanup()
        {
            Simulation?.Dispose(); Simulation=null;
            if(markers!=null) Destroy(markers); if(estimateMaterial!=null) Destroy(estimateMaterial); if(targetMaterial!=null) Destroy(targetMaterial);
            if(trueMaterial!=null) Destroy(trueMaterial);
            markers=null; estimateMarker=trueMarker=null;
        }
        void OnDestroy() { Cleanup(); }
    }
}
