using System;
using System.IO;
using System.Collections.Generic;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using SensorTrust.Experiments;

namespace SensorTrust.Editor
{
    public static class TerrainExperimentView
    {
        [MenuItem("SensorTrust/Experiments/Open latest experiment replay")]
        public static void Latest()
        {
            string folder=File.ReadAllText("../out/terrain_matching/latest.txt").Trim();
            Build(folder,"descent_aligned_500_11_on");
        }
        public static void Build(string folder,string runId)
        {
            if(EditorApplication.isPlaying || ShortDescentExperiment.Running) throw new Exception("Stop running before building view.");
            if(UnityEngine.SceneManagement.SceneManager.GetActiveScene().isDirty) throw new Exception("Save the current scene first.");
            var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
            Directory.CreateDirectory("Assets/Experiments"); Directory.CreateDirectory("../deliverables/terrain_matching");
            string condition=runId.Contains("relief_change")?"relief_change":runId.Contains("map_shift")?"map_shift":"aligned";
            float[,] truth,prior; int n; float span;
            using(var file=new BinaryReader(File.OpenRead(folder+"/map_"+condition+".bin")))
            {
                n=file.ReadInt32(); span=file.ReadSingle(); truth=new float[n,n]; prior=new float[n,n];
                for(int j=0;j<n;j++) for(int i=0;i<n;i++) { truth[j,i]=file.ReadSingle(); prior[j,i]=file.ReadSingle(); }
            }
            var material=new Material(Shader.Find("Standard")){color=new Color(.32f,.34f,.36f)};
            material=Asset(material,"Ground.mat");
            var vertices=new List<Vector3>(); var triangles=new List<int>();
            int side=(n-1)/3+1;
            for(int j=0;j<n;j+=3) for(int i=0;i<n;i+=3) vertices.Add(new Vector3(-span/2+i*span/(n-1),truth[j,i],-span/2+j*span/(n-1)));
            for(int j=0;j<side-1;j++) for(int i=0;i<side-1;i++)
            { int k=j*side+i; triangles.AddRange(new[]{k,k+side,k+1,k+1,k+side,k+side+1}); }
            var mesh=new Mesh(); mesh.SetVertices(vertices); mesh.SetTriangles(triangles,0); mesh.RecalculateNormals(); mesh=Asset(mesh,"TruthSurface.asset");
            var surface=new GameObject("Simulated ground surface"); surface.AddComponent<MeshFilter>().sharedMesh=mesh; surface.AddComponent<MeshRenderer>().sharedMaterial=material;
            var grid=new List<LineRenderer>();
            var amber=new Material(Shader.Find("Unlit/Color")){color=new Color(1,.65f,.16f)}; amber=Asset(amber,"StoredMap.mat");
            for(int j=90;j<=210;j+=6)
            {
                var a=new Vector3[121]; var b=new Vector3[121];
                for(int k=0;k<=120;k++) { int i=90+k; a[k]=new Vector3(-span/2+i*span/(n-1),prior[j,i]+1,-span/2+j*span/(n-1)); b[k]=new Vector3(-span/2+j*span/(n-1),prior[i,j]+1,-span/2+i*span/(n-1)); }
                grid.Add(Line("Onboard map row",a,amber,.5f)); grid.Add(Line("Onboard map column",b,amber,.5f));
            }
            var green=new Material(Shader.Find("Unlit/Color")){color=new Color(.2f,1,.4f)}; green=Asset(green,"TrueMarker.mat");
            var orange=new Material(Shader.Find("Unlit/Color")){color=new Color(1,.35f,.1f)}; orange=Asset(orange,"EstimateMarker.mat");
            var real=GameObject.CreatePrimitive(PrimitiveType.Sphere); real.name="TRUE position - enlarged marker"; real.transform.localScale=Vector3.one*14; real.GetComponent<Renderer>().sharedMaterial=green;
            var estimated=GameObject.CreatePrimitive(PrimitiveType.Sphere); estimated.name="ESTIMATED position - enlarged marker"; estimated.transform.localScale=Vector3.one*11; estimated.GetComponent<Renderer>().sharedMaterial=orange;
            real.layer=9; estimated.layer=9;
            var model=AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Art/Lander/LANTERN_Lander_Visual.prefab");
            if(model!=null) { var craft=(GameObject)PrefabUtility.InstantiatePrefab(model); craft.transform.SetParent(real.transform,false); craft.transform.localScale=Vector3.one/14; }
            var camera=new GameObject("Experiment Overview").AddComponent<Camera>(); camera.tag="MainCamera";
            camera.transform.position=new Vector3(800,700,-900); camera.transform.LookAt(new Vector3(0,220,0)); camera.orthographic=true; camera.orthographicSize=460; camera.farClipPlane=5000;
            camera.clearFlags=CameraClearFlags.SolidColor; camera.backgroundColor=new Color(.025f,.04f,.07f);
            var vehicleCamera=new GameObject("Lander inspection inset").AddComponent<Camera>();
            vehicleCamera.rect=new Rect(.72f,.03f,.27f,.30f); vehicleCamera.depth=1;
            vehicleCamera.cullingMask=~(1<<9); vehicleCamera.nearClipPlane=.1f; vehicleCamera.farClipPlane=4000;
            vehicleCamera.clearFlags=CameraClearFlags.SolidColor; vehicleCamera.backgroundColor=new Color(.025f,.04f,.07f);
            var light=new GameObject("Demonstration light").AddComponent<Light>(); light.type=LightType.Directional; light.intensity=1.4f; light.transform.rotation=Quaternion.Euler(55,-30,0);
            RenderSettings.ambientLight=new Color(.35f,.38f,.42f); RenderSettings.ambientMode=UnityEngine.Rendering.AmbientMode.Flat;
            var replay=new GameObject("Measured experiment replay").AddComponent<TerrainExperimentReplay>();
            replay.runFolder=Path.GetRelativePath(Application.dataPath,folder).Replace('\\','/'); replay.runId=runId; replay.trueMarker=real.transform; replay.estimatedMarker=estimated.transform; replay.overview=camera;
            replay.vehicleCamera=vehicleCamera; replay.groundSurface=surface.GetComponent<MeshFilter>(); replay.storedGrid=grid.ToArray();
            // Load maps only in Play mode; the persisted editor scene uses asset meshes.
            // Initial markers are placed at the logged starting pose below.
            var initial=File.ReadAllLines(folder+"/"+runId+".csv")[1].Split(',');
            float P(int i)=>float.Parse(initial[i],System.Globalization.CultureInfo.InvariantCulture);
            real.transform.position=new Vector3(P(1),P(2),P(3)); estimated.transform.position=new Vector3(P(4),P(5),P(6));
            vehicleCamera.transform.position=real.transform.position+new Vector3(8,6,11); vehicleCamera.transform.LookAt(real.transform.position+Vector3.up*1.8f);
            EditorSceneManager.SaveScene(scene,"Assets/Scenes/TerrainMatchingExperiment.unity"); AssetDatabase.SaveAssets();
            if(SceneView.lastActiveSceneView!=null) SceneView.lastActiveSceneView.LookAt(new Vector3(0,200,0),camera.transform.rotation,700);
            Debug.Log("[TerrainExperiment] View saved: "+runId);
        }
        static T Asset<T>(T asset,string name) where T:UnityEngine.Object
        {
            string path="Assets/Experiments/"+name;
            var old=AssetDatabase.LoadMainAssetAtPath(path);
            if(old!=null) { EditorUtility.CopySerialized(asset,old); UnityEngine.Object.DestroyImmediate(asset); return (T)old; }
            else AssetDatabase.CreateAsset(asset,path);
            return asset;
        }
        static LineRenderer Line(string name,Vector3[] points,Material material,float width)
        {
            var line=new GameObject(name).AddComponent<LineRenderer>(); line.sharedMaterial=material; line.positionCount=points.Length; line.SetPositions(points); line.widthMultiplier=width;
            return line;
        }
    }
}
