using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using UnityEngine;

namespace SensorTrust.Experiments
{
    public class TerrainExperimentReplay : MonoBehaviour
    {
        public string runFolder, runId;
        public Transform trueMarker, estimatedMarker;
        public Camera overview;
        public Camera vehicleCamera;
        public MeshFilter groundSurface;
        public LineRenderer[] storedGrid;
        public float playbackSpeed=8;
        public string description="Recorded Unity PhysX experiment";
        struct Row { public float t; public Vector3 p,e; public float agl; }
        struct Cloud { public float t; public Vector3 p; }
        List<Row> rows=new List<Row>(); List<Cloud> points=new List<Cloud>();
        ParticleSystem cloud;
        Material cloudMaterial;
        Mesh displayMesh;
        float clock; int index; bool paused;
        GUIStyle title, label;
        string condition="aligned";
        int altitude=500,seed=11;
        bool matching=true;
        public void Load()
        {
            rows.Clear(); points.Clear(); index=0; clock=0;
            string folder=Path.GetFullPath(Path.Combine(Application.dataPath,runFolder));
            condition=runId.Contains("relief_change")?"relief_change":runId.Contains("map_shift")?"map_shift":"aligned";
            altitude=runId.Contains("_2000_")?2000:runId.Contains("_1000_")?1000:500;
            seed=runId.Contains("_22_")?22:runId.Contains("_33_")?33:11;
            matching=runId.EndsWith("_on",StringComparison.Ordinal);
            var lines=File.ReadAllLines(Path.Combine(folder,runId+".csv"));
            foreach(string line in lines)
            {
                var v=line.Split(','); if(v[0]=="t") continue;
                float P(int n)=>float.Parse(v[n],CultureInfo.InvariantCulture);
                rows.Add(new Row{t=P(0),p=new Vector3(P(1),P(2),P(3)),e=new Vector3(P(4),P(5),P(6)),agl=P(13)});
            }
            foreach(string line in File.ReadAllLines(Path.Combine(folder,runId+"_cloud.csv")))
            {
                var v=line.Split(','); if(v[0]=="t") continue;
                float P(int n)=>float.Parse(v[n],CultureInfo.InvariantCulture);
                points.Add(new Cloud{t=P(0),p=new Vector3(P(4),P(5),P(6))});
            }
            cloud=GetComponent<ParticleSystem>(); if(cloud==null) cloud=gameObject.AddComponent<ParticleSystem>();
            var main=cloud.main; main.playOnAwake=false; main.simulationSpace=ParticleSystemSimulationSpace.World; main.maxParticles=1000;
            var emission=cloud.emission; emission.enabled=false;
            cloud.Stop(true,ParticleSystemStopBehavior.StopEmittingAndClear);
            if(cloudMaterial==null) { cloudMaterial=new Material(Shader.Find("Particles/Standard Unlit")); cloudMaterial.color=Color.cyan; }
            cloud.GetComponent<ParticleSystemRenderer>().sharedMaterial=cloudMaterial;
            LoadMap(folder);
            if(overview!=null)
            {
                overview.transform.position=new Vector3(800,700+altitude,-900);
                overview.transform.LookAt(new Vector3(0,altitude*.5f,0));
                overview.orthographicSize=altitude*.55f+160;
            }
            float markerSize=14*Mathf.Sqrt(altitude/500f);
            trueMarker.localScale=Vector3.one*markerSize;
            estimatedMarker.localScale=Vector3.one*(markerSize*11/14);
            // The marker grows for visibility; the actual model retains metre scale.
            foreach(Transform child in trueMarker) child.localScale=Vector3.one/markerSize;
            Draw();
        }
        void LoadMap(string folder)
        {
            if(groundSurface==null || storedGrid==null) return;
            using(var file=new BinaryReader(File.OpenRead(Path.Combine(folder,"map_"+condition+".bin"))))
            {
                int n=file.ReadInt32(); float span=file.ReadSingle();
                var real=new float[n,n]; var prior=new float[n,n];
                for(int j=0;j<n;j++) for(int i=0;i<n;i++) { real[j,i]=file.ReadSingle(); prior[j,i]=file.ReadSingle(); }
                var vertices=new List<Vector3>(); var triangles=new List<int>(); int side=(n-1)/3+1;
                for(int j=0;j<n;j+=3) for(int i=0;i<n;i+=3) vertices.Add(new Vector3(-span/2+i*span/(n-1),real[j,i],-span/2+j*span/(n-1)));
                for(int j=0;j<side-1;j++) for(int i=0;i<side-1;i++) { int k=j*side+i; triangles.AddRange(new[]{k,k+side,k+1,k+1,k+side,k+side+1}); }
                if(displayMesh!=null) Destroy(displayMesh);
                displayMesh=new Mesh(); displayMesh.SetVertices(vertices); displayMesh.SetTriangles(triangles,0); displayMesh.RecalculateNormals();
                groundSurface.sharedMesh=displayMesh;
                int line=0;
                for(int j=90;j<=210;j+=6)
                {
                    var a=new Vector3[121]; var b=new Vector3[121];
                    for(int k=0;k<=120;k++) { int i=90+k; a[k]=new Vector3(-span/2+i*span/(n-1),prior[j,i]+1,-span/2+j*span/(n-1)); b[k]=new Vector3(-span/2+j*span/(n-1),prior[i,j]+1,-span/2+i*span/(n-1)); }
                    storedGrid[line++].SetPositions(a); storedGrid[line++].SetPositions(b);
                }
            }
        }
        void Select(string c,int a,int s,bool enabled)
        { runId=$"descent_{c}_{a}_{s}_{(enabled?"on":"off")}"; Load(); }
        void Start() { Load(); StartCoroutine(Capture()); }
        IEnumerator Capture()
        {
            yield return new WaitForSecondsRealtime(1);
            yield return new WaitForEndOfFrame();
            ScreenCapture.CaptureScreenshot(Path.GetFullPath(Path.Combine(Application.dataPath,"../../deliverables/terrain_matching/experiment_gameview.png")));
        }
        void Update()
        {
            if(rows.Count==0 || paused) return;
            clock+=Time.unscaledDeltaTime*playbackSpeed;
            if(clock>rows[rows.Count-1].t+8) { clock=0; index=0; }
            while(index<rows.Count-1 && rows[index+1].t<=clock) index++;
            Draw();
        }
        public void Draw()
        {
            if(rows.Count==0) return;
            var row=rows[index]; trueMarker.position=row.p; estimatedMarker.position=row.e;
            if(vehicleCamera!=null)
            {
                vehicleCamera.transform.position=row.p+new Vector3(8,6,11);
                vehicleCamera.transform.LookAt(row.p+Vector3.up*1.8f);
            }
            var particles=new List<ParticleSystem.Particle>();
            float scanTime=-1;
            foreach(var p in points) if(p.t<=row.t) scanTime=Mathf.Max(scanTime,p.t);
            foreach(var p in points) if(Mathf.Abs(p.t-scanTime)<.01f)
                particles.Add(new ParticleSystem.Particle{position=p.p,startColor=Color.cyan,startSize=4,remainingLifetime=1000,startLifetime=1000});
            cloud.SetParticles(particles.ToArray(),particles.Count);
        }
        void OnGUI()
        {
            if(rows.Count==0) return;
            float scale=Mathf.Max(.75f,Screen.height/900f);
            title=new GUIStyle(GUI.skin.label){fontSize=Mathf.RoundToInt(28*scale),fontStyle=FontStyle.Bold,normal={textColor=Color.white}};
            label=new GUIStyle(GUI.skin.label){fontSize=Mathf.RoundToInt(21*scale),normal={textColor=Color.white}};
            var row=rows[index];
            GUI.Box(new Rect(12,12,Screen.width-24,185*scale),GUIContent.none);
            GUI.Label(new Rect(26,20,Screen.width-52,42*scale),"LANTERN  |  Terrain-matching experiment",title);
            GUI.Label(new Rect(26,62*scale,Screen.width-52,35*scale),"REPLAY of measured Unity PhysX run  •  "+runId,label);
            GUI.Label(new Rect(26,96*scale,Screen.width-52,35*scale),"GREEN: true position   ORANGE: estimate   CYAN: scan placed using estimate   AMBER: stored-map grid",label);
            GUI.Label(new Rect(26,130*scale,Screen.width-52,35*scale),$"t = {row.t:F0} s     altitude = {row.agl:F0} m     horizontal error = {new Vector2(row.e.x-row.p.x,row.e.z-row.p.z).magnitude:F1} m",label);
            float y=Screen.height-132;
            GUI.Box(new Rect(12,y-8,Mathf.Min(Screen.width-24,700),132),GUIContent.none);
            GUI.Label(new Rect(25,y,90,28),"Map:",label);
            var cases=new[]{"aligned","relief_change","map_shift"}; var names=new[]{"Aligned","Changed terrain","Shifted map"};
            for(int i=0;i<3;i++)
            {
                GUI.backgroundColor=condition==cases[i]?new Color(.25f,.75f,.8f):Color.white;
                if(GUI.Button(new Rect(110+i*145,y,140,30),names[i])) Select(cases[i],altitude,seed,matching);
            }
            GUI.backgroundColor=Color.white;
            GUI.Label(new Rect(25,y+36,90,28),"Start:",label);
            for(int i=0;i<3;i++) { int a=new[]{500,1000,2000}[i]; GUI.backgroundColor=altitude==a?new Color(.25f,.75f,.8f):Color.white; if(GUI.Button(new Rect(110+i*95,y+36,90,30),a+" m")) Select(condition,a,seed,matching); }
            GUI.backgroundColor=Color.white;
            if(GUI.Button(new Rect(405,y+36,170,30),"Matching: "+(matching?"ON":"OFF"))) Select(condition,altitude,seed,!matching);
            if(GUI.Button(new Rect(25,y+74,90,30),paused?"Resume":"Pause")) paused=!paused;
            if(GUI.Button(new Rect(125,y+74,90,30),"Restart")) { clock=0; index=0; Draw(); }
            if(GUI.Button(new Rect(225,y+74,120,30),"Seed: "+seed)) Select(condition,altitude,seed==11?22:seed==22?33:11,matching);
            GUI.Label(new Rect(365,y+74,315,34),"Markers enlarged. No ML training.",label);
        }
        void OnDestroy()
        {
            if(cloudMaterial!=null) Destroy(cloudMaterial);
            if(displayMesh!=null) Destroy(displayMesh);
        }
    }
}
