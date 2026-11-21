using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Security.Cryptography;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using SensorTrust.Experiments;
using SensorTrust.Experiments.NavigationV3;

namespace SensorTrust.Editor
{
    [InitializeOnLoad]
    public static class NavigationExperiment
    {
        public const string AssetsFolder="Assets/Experiments/NavigationV3/";
        const string PendingKey="LANTERN.NavigationV3.Pending", ExitKey="LANTERN.NavigationV3.Exit";
        static readonly string[] Sources={
            "Assets/Scripts/Experiments/NavigationFilterV3.cs","Assets/Scripts/Experiments/LandingGuidanceV3.cs",
            "Assets/Scripts/Experiments/NavigationSimulationV3.cs","Assets/Scripts/Experiments/NavigationDemoV3.cs",
            "Assets/Editor/NavigationV3Verification.cs","Assets/Editor/NavigationExperimentV3.cs","Assets/Editor/NavigationDemoVerification.cs",
            "Assets/Scripts/Experiments/TerrainNavigationCore.cs","Assets/Scripts/Experiments/TerrainTouchdownRecorder.cs",
            "Assets/Scripts/Experiments/ScanUtilityPolicy.cs","Assets/Experiments/ScanUtility/model.json",
            AssetsFolder+"manifest.json","../docs/NAVIGATION_V3_PROTOCOL.md","../tools/prepare_navigation_v3.py",
            "../tools/run_navigation_v3.py","../tools/summarize_navigation_v3.py","../tests/test_navigation_v3_reporting.py"};
        [Serializable] sealed class CaseList { public LandingCase[] cases; }
        [Serializable] sealed class RunStatus { public string state,message,output; public int completed,expected; }
        [Serializable] sealed class EnvironmentRecord { public string utc,unity,cpu,stage; public SimulationSettings settings; }
        static Queue<LandingCase> cases;
        static NavigationSimulation simulation;
        static ScanUtilityPolicy model;
        static SimulationSettings settings;
        static Dictionary<string,TerrainTile> tiles;
        static StreamWriter summary,sensors,trace;
        static string output,stage;
        static bool running,oldBackground;
        static int completed,expected,traceStep;
        static double pollTime;

        static NavigationExperiment()
        {
            EditorApplication.playModeStateChanged+=PlayChanged;
            EditorApplication.update+=Poll;
            AssemblyReloadEvents.beforeAssemblyReload+=()=> { if(running) Finish(false,"Interrupted by script reload"); };
            EditorApplication.quitting+=()=> { if(running) Finish(false,"Editor exiting"); };
        }
        [MenuItem("SensorTrust/Navigation v3/Run development smoke (18 descents)")]
        public static void RunSmoke() => Request("smoke");
        [MenuItem("SensorTrust/Navigation v3/Run reserved evaluation (324 descents)")]
        public static void RunEvaluation() => Request("evaluation");
        [MenuItem("SensorTrust/Navigation v3/Stop experiment")]
        public static void Stop() { if(running) Finish(false,"Stopped by user"); }
        [MenuItem("SensorTrust/Navigation v3/Verify navigation contracts")]
        public static void Verify()
        {
            try
            {
                var report=NavigationV3Verification.Run();
                Directory.CreateDirectory("../out/navigation_v3");
                File.WriteAllText("../out/navigation_v3/contracts.json",JsonUtility.ToJson(report,true));
                Debug.Log("[NavigationV3] "+report.checks.Length+" contract groups passed");
                if(Application.isBatchMode) EditorApplication.Exit(0);
            }
            catch(Exception ex) { Debug.LogException(ex); if(Application.isBatchMode) EditorApplication.Exit(1); else throw; }
        }
        static void Request(string requested)
        {
            try
            {
                if(running || EditorApplication.isPlayingOrWillChangePlaymode || EditorApplication.isCompiling) throw new InvalidOperationException("Editor busy");
                for(int i=0;i<SceneManager.sceneCount;i++) if(SceneManager.GetSceneAt(i).isDirty) throw new InvalidOperationException("Save open scenes first");
                SessionState.SetString("LANTERN.NavigationV3.PreviousScene",SceneManager.GetActiveScene().path);
                EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
                SessionState.SetString(PendingKey,requested); EditorApplication.isPlaying=true;
            }
            catch(Exception ex) { Debug.LogException(ex); if(Application.isBatchMode) EditorApplication.Exit(1); else throw; }
        }
        static void PlayChanged(PlayModeStateChange change)
        {
            if(change==PlayModeStateChange.EnteredPlayMode)
            {
                string requested=SessionState.GetString(PendingKey,""); SessionState.EraseString(PendingKey);
                if(requested!="") EditorApplication.delayCall+=()=> { try { Start(requested); } catch(Exception ex) { Debug.LogException(ex); Finish(false,ex.ToString()); } };
            }
            if(change==PlayModeStateChange.ExitingPlayMode && running) Finish(false,"Play mode interrupted");
            if(change==PlayModeStateChange.EnteredEditMode)
            {
                int exit=SessionState.GetInt(ExitKey,-1); SessionState.EraseInt(ExitKey);
                if(exit>=0 && Application.isBatchMode) EditorApplication.delayCall+=()=>EditorApplication.Exit(exit);
                else if(exit>=0)
                {
                    string previous=SessionState.GetString("LANTERN.NavigationV3.PreviousScene","");
                    if(previous!="" && File.Exists(previous)) EditorApplication.delayCall+=()=>EditorSceneManager.OpenScene(previous);
                }
            }
        }
        static void Poll()
        {
            if(EditorApplication.timeSinceStartup<pollTime || EditorApplication.isCompiling || EditorApplication.isUpdating) return;
            pollTime=EditorApplication.timeSinceStartup+.5;
            const string path="Library/NavigationV3.command";
            if(!File.Exists(path)) return;
            string command=File.ReadAllText(path).Trim(); File.Delete(path);
            try
            {
                if(command=="smoke") RunSmoke(); else if(command=="evaluation") RunEvaluation();
                else if(command=="verify") Verify(); else if(command=="stop") Stop(); else if(command=="demo") BuildDemo();
                else throw new ArgumentException("Unknown navigation v3 command");
                File.WriteAllText(path+"-result",command+" accepted "+DateTime.UtcNow.ToString("O"));
            }
            catch(Exception ex) { File.WriteAllText(path+"-result",ex.ToString()); Debug.LogException(ex); }
        }
        static void Start(string requested)
        {
            if(requested!="smoke" && requested!="evaluation") throw new ArgumentException("Unknown stage");
            stage=requested; settings=new SimulationSettings(); completed=0;
            oldBackground=Application.runInBackground; Application.runInBackground=true;
            output=Path.GetFullPath("../out/navigation_v3/"+DateTime.UtcNow.ToString("yyyyMMdd_HHmmss_fff")+"_"+stage);
            Directory.CreateDirectory(output); Directory.CreateDirectory(output+"/sources");
            File.WriteAllText(output+"/contracts.json",JsonUtility.ToJson(NavigationV3Verification.Run(),true));
            var manifest=JsonUtility.FromJson<TerrainManifest>(File.ReadAllText(AssetsFolder+"manifest.json"));
            if(manifest.version!=3 || manifest.sites.Length!=4) throw new InvalidDataException("Wrong terrain manifest");
            model=new ScanUtilityPolicy(File.ReadAllText("Assets/Experiments/ScanUtility/model.json"));
            tiles=new Dictionary<string,TerrainTile>(); cases=new Queue<LandingCase>();
            foreach(var site in manifest.sites)
            {
                if((stage=="smoke")!=(site.split=="development")) continue;
                string path=AssetsFolder+site.file;
                if(!string.Equals(Hash(path),site.sha256,StringComparison.OrdinalIgnoreCase)) throw new InvalidDataException("Terrain hash mismatch: "+path);
                tiles.Add(site.id,TerrainTile.Load(File.ReadAllBytes(path))); Archive(path);
                foreach(int altitude in stage=="smoke" ? new[]{500} : new[]{500,1500})
                foreach(int seed in stage=="smoke" ? new[]{1201} : new[]{2201,2202,2203})
                foreach(string condition in manifest.conditions) foreach(string arm in manifest.arms)
                    cases.Enqueue(new LandingCase { site=site.id,condition=condition,arm=arm,altitude=altitude,seed=seed });
            }
            expected=cases.Count;
            if(expected!=(stage=="smoke" ? 18 : 324)) throw new InvalidDataException("Unexpected experiment matrix");
            File.WriteAllText(output+"/cases.json",JsonUtility.ToJson(new CaseList { cases=cases.ToArray() },true));
            File.WriteAllText(output+"/environment.json",JsonUtility.ToJson(new EnvironmentRecord { utc=DateTime.UtcNow.ToString("O"),
                unity=Application.unityVersion,cpu=SystemInfo.processorType,stage=stage,settings=settings },true));
            foreach(string path in Sources) Archive(path);
            summary=new StreamWriter(output+"/summary.csv") { AutoFlush=true };
            summary.WriteLine("id,site,condition,arm,altitude,seed,termination,contact,time_s,absolute_miss_m,map_miss_m,impact_vz,impact_vh,fuel_kg,x,z,shift_x,shift_z,abs_10,abs_50,abs_100,map_10,map_50,map_100,range_accepted,range_rejected,scan_accepted,scan_rejected,missing_ranges,missing_scans,ml_fallbacks");
            sensors=new StreamWriter(output+"/sensors.csv") { AutoFlush=true };
            sensors.WriteLine("id,kind,sequence,captured_s,delivered_s,decision,nis,injected_fault,points,dx,dz,rms,confidence,variance_x,covariance_xz,variance_z,ml_prediction,inflation,fix_map_error_m,range_m");
            running=true; EditorApplication.update+=Tick; Next();
        }
        static string Hash(string path)
        { using(var sha=SHA256.Create()) using(var file=File.OpenRead(path)) return BitConverter.ToString(sha.ComputeHash(file)).Replace("-","").ToLowerInvariant(); }
        static void Archive(string path)
        {
            string name=path.Replace("../","root_").Replace('/','_');
            File.Copy(path,output+"/sources/"+name);
            File.AppendAllText(output+"/source_sha256.txt",Hash(path)+"  sources/"+name+"\n");
        }
        static string Row(params object[] values)
        {
            var cells=new string[values.Length];
            for(int i=0;i<values.Length;i++) cells[i]=values[i] is float f ? f.ToString("R",CultureInfo.InvariantCulture) :
                values[i] is double d ? d.ToString("R",CultureInfo.InvariantCulture) : Convert.ToString(values[i],CultureInfo.InvariantCulture);
            return string.Join(",",cells);
        }
        static void Next()
        {
            simulation?.Dispose(); simulation=null; trace?.Dispose(); trace=null;
            if(cases.Count==0) { Finish(true,"Complete"); return; }
            var next=cases.Dequeue(); simulation=new NavigationSimulation(next,settings,tiles[next.site],model);
            simulation.SensorObserved+=r=>sensors.WriteLine(Row(next.Id,r.Kind,r.Sequence,r.Captured,r.Delivered,r.Decision,r.Nis,r.InjectedFault,
                r.Points,r.CorrectionX,r.CorrectionZ,r.Rms,r.Confidence,r.VarianceX,r.CovarianceXZ,r.VarianceZ,r.Prediction,r.Inflation,r.FixMapError,r.Range));
            trace=new StreamWriter(output+"/"+next.Id+".csv");
            trace.WriteLine("t,x,y,z,vx,vy,vz,ex,ey,ez,evx,evy,evz,bx,by,bz,sigma_horizontal_m,estimated_agl_m,sigma_agl_m,last_range_s,last_scan_s,mode,saturated,fuel_kg,map_height_bias_m,sigma_vertical_m,altitude_valid");
            traceStep=0; Trace(); Status("running",next.Id);
        }
        static void Trace()
        {
            var p=simulation.Body.position; var v=simulation.Body.linearVelocity; var f=simulation.Navigation.Filter;
            var e=f.Position; var ev=f.Velocity; var b=f.Bias; bool altitudeValid=f.Altitude(simulation.Map,out double h,out double sigma);
            trace.WriteLine(Row(simulation.Time,p.x,p.y,p.z,v.x,v.y,v.z,e.x,e.y,e.z,ev.x,ev.y,ev.z,b.x,b.y,b.z,
                f.HorizontalSigma,h,NavigationFilter.Finite(sigma)?sigma:-1,f.LastRangeTime,f.LastTerrainTime,simulation.Guidance.Mode,simulation.Guidance.Saturated,simulation.Fuel,f.MapHeightBias,Math.Sqrt(f.Variance(1,1)),altitudeValid));
        }
        static void Tick()
        {
            if(!running) return;
            try
            {
                var clock=System.Diagnostics.Stopwatch.StartNew();
                do
                {
                    simulation.Step(); if(++traceStep%10==0 || simulation.Finished) Trace();
                    if(simulation.Finished)
                    {
                        var r=simulation.Result;
                        summary.WriteLine(Row(r.id,r.site,r.condition,r.arm,r.altitude,r.seed,r.termination,r.contact,r.time,r.absoluteMiss,r.mapMiss,
                            r.impactVertical,r.impactHorizontal,r.fuel,r.finalX,r.finalZ,r.shiftX,r.shiftZ,r.absolute10,r.absolute50,r.absolute100,
                            r.map10,r.map50,r.map100,r.rangeAccepted,r.rangeRejected,r.scanAccepted,r.scanRejected,r.missingRanges,r.missingScans,r.mlFallbacks));
                        File.WriteAllText(output+"/"+r.id+".json",JsonUtility.ToJson(r,true)); completed++; Next();
                    }
                } while(running && clock.ElapsedMilliseconds<30);
            }
            catch(Exception ex) { Debug.LogException(ex); Finish(false,ex.ToString()); }
        }
        static void Status(string state,string message)
        {
            if(output!=null) File.WriteAllText(output+"/status.json",JsonUtility.ToJson(new RunStatus { state=state,message=message,output=output,completed=completed,expected=expected },true));
        }
        static void Finish(bool success,string message)
        {
            running=false; EditorApplication.update-=Tick;
            simulation?.Dispose(); simulation=null; trace?.Dispose(); sensors?.Dispose(); summary?.Dispose(); trace=sensors=summary=null;
            Application.runInBackground=oldBackground;
            Status(success?"complete":"failed",message);
            if(output!=null && success) File.WriteAllText("../out/navigation_v3/latest_"+stage+".txt",output);
            Debug.Log("[NavigationV3] "+message+"; "+completed+"/"+expected+"; "+output);
            SessionState.SetInt(ExitKey,success?0:1);
            if(EditorApplication.isPlaying) EditorApplication.delayCall+=()=>EditorApplication.isPlaying=false;
            else if(Application.isBatchMode) EditorApplication.Exit(success?0:1);
        }

        [MenuItem("SensorTrust/Navigation v3/Build and open live demo")]
        public static void BuildDemo()
        {
            if(EditorApplication.isPlayingOrWillChangePlaymode) throw new InvalidOperationException("Stop Play mode first");
            for(int i=0;i<SceneManager.sceneCount;i++) if(SceneManager.GetSceneAt(i).isDirty) throw new InvalidOperationException("Save open scenes first");
            var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
            var demo=new GameObject("Navigation v3 live experiment").AddComponent<NavigationDemoV3>();
            demo.terrain=AssetDatabase.LoadAssetAtPath<TextAsset>(AssetsFolder+"development.bytes");
            demo.utilityModel=AssetDatabase.LoadAssetAtPath<TextAsset>("Assets/Experiments/ScanUtility/model.json");
            demo.landerVisual=AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Art/Lander/LANTERN_Lander_Visual.prefab");
            var camera=new GameObject("Overview camera").AddComponent<Camera>(); camera.tag="MainCamera";
            camera.transform.position=new Vector3(850,950,-950); camera.transform.LookAt(new Vector3(0,220,0));
            camera.orthographic=true; camera.orthographicSize=550; camera.farClipPlane=5000;
            camera.backgroundColor=new Color(.025f,.035f,.055f); camera.clearFlags=CameraClearFlags.SolidColor; demo.overview=camera;
            var inset=new GameObject("Vehicle inspection inset").AddComponent<Camera>();
            inset.rect=new Rect(.67f,.03f,.32f,.37f); inset.depth=1; inset.cullingMask=~(1<<9);
            inset.nearClipPlane=.05f; inset.farClipPlane=3000; inset.clearFlags=CameraClearFlags.SolidColor;
            inset.backgroundColor=camera.backgroundColor; demo.vehicleCamera=inset;
            var light=new GameObject("Demonstration lighting").AddComponent<Light>(); light.type=LightType.Directional;
            light.intensity=1.3f; light.transform.rotation=Quaternion.Euler(45,-30,0);
            RenderSettings.ambientMode=UnityEngine.Rendering.AmbientMode.Flat; RenderSettings.ambientLight=new Color(.35f,.37f,.4f);
            EditorSceneManager.SaveScene(scene,"Assets/Scenes/NavigationV3.unity"); AssetDatabase.SaveAssets();
            Debug.Log("[NavigationV3] Live scene saved. Press Play; classical terminal guidance is the default.");
        }
    }
}
