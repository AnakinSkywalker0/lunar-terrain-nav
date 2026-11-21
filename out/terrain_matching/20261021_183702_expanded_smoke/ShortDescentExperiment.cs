using System;
using System.IO;
using System.Collections.Generic;
using System.Globalization;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using SensorTrust.Experiments;

namespace SensorTrust.Editor
{
    public static class ShortDescentExperiment
    {
        const float Dt=.05f, Span=2400, SourceMin=-2847.877197265625f;
        const int Resolution=301;
        static readonly int[] Seeds={11,22,33};
        static readonly int[] Altitudes={500,1000,2000};
        static readonly string[] Conditions={"aligned","relief_change","map_shift"};
        static Scene physicsScene;
        static PhysicsScene physics;
        static TerrainCollider ground;
        static TerrainData source, truthData;
        static ElevationMap truth, map;
        static Rigidbody body;
        static TerrainTouchdownRecorder contact;
        static bool expandedRun;
        sealed class MapBundle { public ElevationMap truth,map; public TerrainData data; }
        static readonly Dictionary<string,MapBundle> MapCache=new Dictionary<string,MapBundle>();
        static DateTime startedUtc;
        [Serializable] public class LandingSite { public string id; public float x,z; }
        [Serializable] class SiteManifest { public LandingSite[] sites; }
        static readonly Vector3[] ExpandedErrors={new Vector3(60,0,-40),new Vector3(-80,0,50),new Vector3(100,0,80)};
        static NavigationEstimate nav;
        static System.Random rng;
        static Queue<Case> queue;
        static Case current;
        static StreamWriter summary, scans, trace, cloudTrace;
        static string output;
        static float elapsed, nextScan, nextTrace, fuel, measuredAgl;
        static Vector3 previousVelocity;
        static int accepted, wrong, attempted, completed;
        static double squaredError;
        static int errorSamples;
        public static string Status { get; private set; }="Idle";
        public static bool Running { get; private set; }
        struct Case
        {
            public string kind, condition, errorId;
            public int altitude, seed;
            public bool enabled;
            public LandingSite site;
            public Vector3 initialError;
            public string Id => kind+"_"+(site!=null?site.id+"_"+errorId+"_":"")+condition+"_"+altitude+"_"+seed+"_"+(enabled?"on":"off");
        }
        static float Gaussian(System.Random random)
        { return (float)(Math.Sqrt(-2*Math.Log(1-random.NextDouble()))*Math.Cos(2*Math.PI*random.NextDouble())); }
        static string F(float value) => value.ToString("R",CultureInfo.InvariantCulture);
        static string Row(params object[] values)
        {
            var parts=new string[values.Length];
            for(int i=0;i<values.Length;i++) parts[i]=Convert.ToString(values[i],CultureInfo.InvariantCulture);
            return string.Join(",",parts);
        }

        [MenuItem("SensorTrust/Experiments/Run short-descent smoke checks")]
        public static void Smoke() { Request(true); }
        [MenuItem("SensorTrust/Experiments/Run short-descent protocol v1")]
        public static void Full() { Request(false); }
        [MenuItem("SensorTrust/Experiments/Run expanded terrain protocol v2")]
        public static void Expanded() { Request(false,true); }
        [MenuItem("SensorTrust/Experiments/Run expanded terrain smoke checks")]
        public static void ExpandedSmoke() { Request(true,true); }
        [MenuItem("SensorTrust/Experiments/Stop short-descent experiment")]
        public static void Stop() { Finish("Stopped by user"); }

        static void Request(bool smoke,bool expanded=false)
        {
            if(Running || EditorApplication.isPlaying || EditorApplication.isCompiling) throw new InvalidOperationException("Editor is busy.");
            if(SceneManager.GetActiveScene().isDirty) throw new InvalidOperationException("Save the current scene before starting.");
            SessionState.SetString("LANTERN.PendingExperiment",expanded?(smoke?"expanded_smoke":"expanded"):(smoke?"smoke":"full"));
            EditorApplication.isPlaying=true;
        }

        public static void Start(bool smoke,bool expanded=false)
        {
            if(Running || !EditorApplication.isPlaying || EditorApplication.isCompiling) throw new InvalidOperationException("Start isolated physics in ready Play mode.");
            source=AssetDatabase.LoadAssetAtPath<TerrainData>("Assets/Terrain/Site04TerrainData.asset");
            if(source==null) throw new Exception("Site04 terrain missing");
            SelfChecks();
            expandedRun=expanded;
            startedUtc=DateTime.UtcNow;
            MapCache.Clear();
            output=Path.GetFullPath("../out/terrain_matching/"+DateTime.UtcNow.ToString("yyyyMMdd_HHmmss")+(expanded?(smoke?"_expanded_smoke":"_expanded_v2"):(smoke?"_smoke":"_v1")));
            Directory.CreateDirectory(output);
            File.Copy(expanded?"../docs/TERRAIN_MATCHING_PROTOCOL_V2.md":"../docs/TERRAIN_MATCHING_PROTOCOL.md",output+"/protocol.md");
            File.WriteAllText(output+"/environment.txt","UTC="+DateTime.UtcNow.ToString("O")+"\nUnity="+Application.unityVersion+"\nCPU="+SystemInfo.processorType+"\nPlatform="+Application.platform+"\nDT="+Dt+"\n3-DOF PhysX; ideal attitude; no ML training\n");
            var sourceFiles=new List<string>{"Assets/Editor/ShortDescentExperiment.cs","Assets/Scripts/Experiments/TerrainNavigationCore.cs"};
            if(expanded) sourceFiles.AddRange(new[]{"Assets/Scripts/Experiments/TerrainTouchdownRecorder.cs","Assets/Experiments/ExpandedSites.json"});
            foreach(var path in sourceFiles)
            {
                File.Copy(path,output+"/"+Path.GetFileName(path));
                using(var sha=System.Security.Cryptography.SHA256.Create())
                    File.AppendAllText(output+"/source_sha256.txt",BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(path))).Replace("-","")+"  "+path+"\n");
            }
            summary=new StreamWriter(output+"/summary.csv"){AutoFlush=true};
            summary.WriteLine("id,kind,condition,altitude,seed,matching,touchdown,success,time_s,horizontal_error_m,vertical_error_m,target_miss_m,impact_vz,impact_vh,fuel_kg,accepted_matches,wrong_matches,attempted_matches,horizontal_rmse_m,site_id,site_x,site_z,error_id,initial_error_x,initial_error_z,contact_definition");
            scans=new StreamWriter(output+"/scans.csv"){AutoFlush=true};
            scans.WriteLine("id,time_s,points,valid,accepted,applied,dx,dz,rms_m,confidence,before_error_m,proposed_error_m,wrong,match_ms");
            queue=new Queue<Case>();
            if(expanded)
            {
                var sites=JsonUtility.FromJson<SiteManifest>(File.ReadAllText("Assets/Experiments/ExpandedSites.json")).sites;
                if(sites==null || sites.Length!=5) throw new Exception("Expanded protocol requires five sites.");
                foreach(var site in sites)
                {
                    if(smoke && site.id!="original" && site.id!="area01") continue;
                    foreach(string condition in (smoke?new[]{"aligned"}:Conditions))
                    foreach(int altitude in (smoke?new[]{500}:new[]{500,2000}))
                    for(int error=0;error<(smoke?1:ExpandedErrors.Length);error++)
                    foreach(int seed in (smoke?new[]{11}:Seeds))
                    {
                        queue.Enqueue(new Case{kind="stationary",condition=condition,altitude=altitude,seed=seed,enabled=true,site=site,errorId="e"+error,initialError=ExpandedErrors[error]});
                        foreach(bool enabled in new[]{false,true}) queue.Enqueue(new Case{kind="descent",condition=condition,altitude=altitude,seed=seed,enabled=enabled,site=site,errorId="e"+error,initialError=ExpandedErrors[error]});
                    }
                }
            }
            else
            foreach(string condition in (smoke?new[]{"aligned"}:Conditions))
            foreach(int altitude in (smoke?new[]{500}:Altitudes))
            foreach(int seed in (smoke?new[]{11}:Seeds))
            {
                queue.Enqueue(new Case{kind="stationary",condition=condition,altitude=altitude,seed=seed,enabled=true,initialError=new Vector3(60,0,-40)});
                foreach(bool enabled in new[]{false,true}) queue.Enqueue(new Case{kind="descent",condition=condition,altitude=altitude,seed=seed,enabled=enabled,initialError=new Vector3(60,0,-40)});
            }
            physicsScene=SceneManager.CreateScene("LANTERN isolated experiment physics",new CreateSceneParameters(LocalPhysicsMode.Physics3D));
            physics=physicsScene.GetPhysicsScene();
            completed=0; Running=true;
            EditorApplication.update+=Tick;
            AssemblyReloadEvents.beforeAssemblyReload+=BeforeReload;
            Next();
        }

        static void SelfChecks()
        {
            var flat=new ElevationMap(new float[201,201],new Vector2(-1000,-1000),10);
            var points=new List<Vector3>();
            for(int j=-5;j<=5;j++) for(int i=-5;i<=5;i++) points.Add(new Vector3(i*10,-500,j*10));
            var m=LocalScanMatcher.Match(points,new Vector3(60,500,-40),flat);
            if(m.accepted || m.confidence>.01f) throw new Exception("Flat-map ambiguity check failed");
            var empty=LocalScanMatcher.Match(new List<Vector3>(),Vector3.zero,flat);
            if(empty.valid || empty.accepted) throw new Exception("Empty scan check failed");
            var outside=LocalScanMatcher.Match(points,new Vector3(5000,500,5000),flat);
            if(outside.valid) throw new Exception("Out-of-map check failed");
            var shape=new float[201,201];
            for(int j=0;j<201;j++) for(int i=0;i<201;i++)
            { float x=-1000+i*10,z=-1000+j*10; shape[j,i]=10*Mathf.Sin(x/100)+7*Mathf.Cos(z/70)+.002f*x*z; }
            var shaped=new ElevationMap(shape,new Vector2(-1000,-1000),10);
            points.Clear();
            for(int j=-5;j<=5;j++) for(int i=-5;i<=5;i++)
            { shaped.Sample(i*20,j*20,out float h); points.Add(new Vector3(i*20,h-500,j*20)); }
            var known=LocalScanMatcher.Match(points,new Vector3(60,500,-40),shaped);
            if(!known.accepted || Vector2.Distance(known.correction,new Vector2(-60,40))>1.5f)
                throw new Exception("Known-offset/sign check failed: "+known.correction);
            Debug.Log("[TerrainExperiment] known-offset/sign, flat ambiguity, empty scan and map-bound checks passed.");
        }

        static void MakeMaps(string condition)
        {
            string cacheKey=(current.site!=null?current.site.id:"original")+"_"+condition;
            if(expandedRun && MapCache.TryGetValue(cacheKey,out var cached))
            { truth=cached.truth; map=cached.map; truthData=cached.data; CreateGround(); return; }
            float cx=current.site!=null?current.site.x:6198, cz=current.site!=null?current.site.z:8512;
            float center=source.GetInterpolatedHeight(cx/source.size.x,cz/source.size.z)+SourceMin;
            float[,] real=new float[Resolution,Resolution], prior=new float[Resolution,Resolution];
            float spacing=Span/(Resolution-1);
            for(int j=0;j<Resolution;j++) for(int i=0;i<Resolution;i++)
            {
                float x=-Span/2+i*spacing, z=-Span/2+j*spacing;
                real[j,i]=source.GetInterpolatedHeight((cx+x)/source.size.x,(cz+z)/source.size.z)+SourceMin-center;
                if(condition=="relief_change") real[j,i]+=12*Mathf.Exp(-((x-120)*(x-120)+(z-60)*(z-60))/(2*60*60));
                float sx=condition=="map_shift"?40:0, sz=condition=="map_shift"?-24:0;
                prior[j,i]=source.GetInterpolatedHeight((cx+x+sx)/source.size.x,(cz+z+sz)/source.size.z)+SourceMin-center;
            }
            truth=new ElevationMap(real,new Vector2(-Span/2,-Span/2),spacing);
            map=new ElevationMap(prior,new Vector2(-Span/2,-Span/2),spacing);
            string mapFile=output+"/map_"+(current.site!=null?current.site.id+"_":"")+condition+".bin";
            if(!File.Exists(mapFile)) using(var file=new BinaryWriter(File.Open(mapFile,FileMode.CreateNew)))
            {
                file.Write(Resolution); file.Write(Span);
                for(int j=0;j<Resolution;j++) for(int i=0;i<Resolution;i++) { file.Write(real[j,i]); file.Write(prior[j,i]); }
            }
            // Unity requires 2^n+1 height samples. Resample the independent truth grid to 513.
            truthData=new TerrainData { heightmapResolution=513, size=new Vector3(Span,4000,Span) };
            var heights=new float[513,513];
            for(int j=0;j<513;j++) for(int i=0;i<513;i++)
            {
                float x=-Span/2+i*Span/512, z=-Span/2+j*Span/512;
                truth.Sample(Mathf.Min(x,Span/2-.01f),Mathf.Min(z,Span/2-.01f),out float h);
                heights[j,i]=(h+2000)/4000;
            }
            truthData.SetHeights(0,0,heights);
            if(expandedRun) MapCache.Add(cacheKey,new MapBundle{truth=truth,map=map,data=truthData});
            CreateGround();
        }
        static void CreateGround()
        {
            var go=Terrain.CreateTerrainGameObject(truthData);
            go.name="Independent simulated ground";
            go.transform.position=new Vector3(-Span/2,-2000,-Span/2);
            SceneManager.MoveGameObjectToScene(go,physicsScene);
            go.GetComponent<Terrain>().enabled=false;
            ground=go.GetComponent<TerrainCollider>();
        }
        static float GroundHeight(Vector3 p) => truthData.GetInterpolatedHeight((p.x+Span/2)/Span,(p.z+Span/2)/Span)-2000;

        static void Next()
        {
            trace?.Dispose(); trace=null; cloudTrace?.Dispose(); cloudTrace=null;
            foreach(var go in physicsScene.GetRootGameObjects()) UnityEngine.Object.DestroyImmediate(go);
            if(!expandedRun && truthData!=null) UnityEngine.Object.DestroyImmediate(truthData);
            if(queue.Count==0) { Finish("Complete"); return; }
            current=queue.Dequeue(); MakeMaps(current.condition);
            var goBody=new GameObject("Physics truth - sensor adapter only"); goBody.layer=8;
            SceneManager.MoveGameObjectToScene(goBody,physicsScene);
            body=goBody.AddComponent<Rigidbody>(); body.useGravity=false;
            contact=expandedRun?goBody.AddComponent<TerrainTouchdownRecorder>():null;
            body.constraints=RigidbodyConstraints.FreezeRotation;
            body.mass=2000; body.linearDamping=0; body.collisionDetectionMode=CollisionDetectionMode.ContinuousDynamic;
            var col=goBody.AddComponent<SphereCollider>(); col.radius=.4f; col.center=new Vector3(0,.4f,0);
            body.position=new Vector3(0,GroundHeight(Vector3.zero)+current.altitude,0);
            body.linearVelocity=current.kind=="stationary"?Vector3.zero:new Vector3(0,-10,0);
            nav=new NavigationEstimate(body.position+current.initialError,body.linearVelocity);
            rng=new System.Random(current.seed); fuel=800; elapsed=nextScan=nextTrace=0;
            previousVelocity=body.linearVelocity; accepted=wrong=attempted=0; squaredError=0; errorSamples=0;
            trace=new StreamWriter(output+"/"+current.Id+".csv"){AutoFlush=true};
            trace.WriteLine("t,x,y,z,ex,ey,ez,vx,vy,vz,evx,evy,evz,altimeter_m,fuel_kg");
            cloudTrace=new StreamWriter(output+"/"+current.Id+"_cloud.csv"){AutoFlush=true};
            cloudTrace.WriteLine("t,true_x,true_y,true_z,estimated_x,estimated_y,estimated_z");
            Status=current.Id+" ("+completed+" complete)";
            File.WriteAllText(output+"/status.txt",Status);
            Physics.SyncTransforms();
            measuredAgl=current.altitude;
        }

        static List<Vector3> Scan()
        {
            var local=new List<Vector3>();
            for(int j=0;j<24;j++) for(int i=0;i<24;i++)
            {
                Vector3 direction=Quaternion.Euler(Mathf.Lerp(-20,20,j/23f),0,Mathf.Lerp(-20,20,i/23f))*Vector3.down;
                bool dropout=rng.NextDouble()<.02; float noise=Gaussian(rng);
                if(physics.Raycast(body.position,direction,out var hit,3000,1,QueryTriggerInteraction.Ignore) && !dropout)
                    local.Add(direction*(hit.distance+noise*(.05f+.001f*hit.distance)));
            }
            return local;
        }
        static void MatchScan()
        {
            var points=Scan(); var estimateBefore=nav.position;
            var m=LocalScanMatcher.Match(points,estimateBefore,map); attempted++;
            for(int k=0;k<points.Count;k+=8)
            {
                var actual=body.position+points[k]; var placed=estimateBefore+points[k];
                cloudTrace.WriteLine(Row(elapsed,actual.x,actual.y,actual.z,placed.x,placed.y,placed.z));
            }
            float before=Horizontal(estimateBefore-body.position);
            float proposed=Horizontal(estimateBefore+new Vector3(m.correction.x,0,m.correction.y)-body.position);
            bool bad=m.accepted && proposed>10;
            if(m.accepted) accepted++; if(bad) wrong++;
            // Both arms compute the same matcher. Only this line differs by arm.
            if(current.enabled) nav.Correct(m);
            scans.WriteLine(Row(current.Id,elapsed,m.points,m.valid,m.accepted,current.enabled&&m.accepted,m.correction.x,m.correction.y,m.rms,m.confidence,before,proposed,bad,m.milliseconds));
            if(current.kind=="stationary")
            {
                using(var cloud=new StreamWriter(output+"/"+current.Id+"_points.csv"))
                {
                    cloud.WriteLine("local_x,local_y,local_z,true_x,true_y,true_z");
                    foreach(var p in points) { var w=body.position+p; cloud.WriteLine(Row(p.x,p.y,p.z,w.x,w.y,w.z)); }
                }
            }
        }
        static float Horizontal(Vector3 v) => new Vector2(v.x,v.z).magnitude;
        static void Trace() { trace.WriteLine(Row(elapsed,body.position.x,body.position.y,body.position.z,nav.position.x,nav.position.y,nav.position.z,body.linearVelocity.x,body.linearVelocity.y,body.linearVelocity.z,nav.velocity.x,nav.velocity.y,nav.velocity.z,measuredAgl,fuel)); }
        static void Tick()
        {
            if(!Running) return;
            try
            {
                var wall=System.Diagnostics.Stopwatch.StartNew();
                do { Step(); } while(Running && wall.ElapsedMilliseconds<35);
            }
            catch(Exception ex) { Debug.LogException(ex); Finish("ERROR: "+ex); }
        }
        static void Step()
        {
            if(current.kind=="stationary")
            { Trace(); MatchScan(); Trace(); Complete(false,0,0); return; }
            // Sensor adapter: acceleration from physical velocity changes, with noise.
            Vector3 actualAcceleration=(body.linearVelocity-previousVelocity)/Dt;
            Vector3 measuredAcceleration=actualAcceleration+new Vector3(Gaussian(rng),Gaussian(rng),Gaussian(rng))*.002f;
            if(elapsed>0) nav.Predict(measuredAcceleration,Dt);
            float altNoise=Gaussian(rng)*.1f;
            if(physics.Raycast(body.position+Vector3.up*.05f,Vector3.down,out var hit,4000,1,QueryTriggerInteraction.Ignore))
                measuredAgl=Mathf.Max(0,hit.distance-.05f+altNoise);
            nav.ObserveAltitude(measuredAgl,map);
            if(elapsed>=nextScan)
            {
                // Fixed clock; consume scan noise in both arms even at low altitude.
                if(measuredAgl>80) MatchScan(); else Scan();
                nextScan+=3;
            }
            float e=Horizontal(nav.position-body.position); squaredError+=e*e; errorSamples++;
            if(elapsed>=nextTrace) { Trace(); nextTrace+=1; }
            Vector3 thrust=fuel>0?EstimateGuidance.Thrust(nav,measuredAgl,1200+fuel):Vector3.zero;
            previousVelocity=body.linearVelocity;
            body.mass=1200+fuel;
            body.AddForce(thrust+Vector3.down*(body.mass*1.62f),ForceMode.Force);
            fuel=Mathf.Max(0,fuel-thrust.magnitude/(300*9.80665f)*Dt);
            physics.Simulate(Dt); elapsed+=Dt;
            float gap=body.position.y-GroundHeight(body.position);
            if(expandedRun && contact.Touched)
            { Trace(); Complete(true,Mathf.Abs(contact.ContactVelocity.y),Horizontal(contact.ContactVelocity)); }
            else if(!expandedRun && gap<.08f && previousVelocity.y<0)
            { Trace(); Complete(true,Mathf.Max(0,-previousVelocity.y),Horizontal(previousVelocity)); }
            else if(elapsed>=360 || Mathf.Abs(body.position.x)>1000 || Mathf.Abs(body.position.z)>1000)
            { Trace(); Complete(false,Mathf.Max(0,-body.linearVelocity.y),Horizontal(body.linearVelocity)); }
        }
        static void Complete(bool touchdown, float vz, float vh)
        {
            float miss=Horizontal(body.position), err=Horizontal(nav.position-body.position);
            bool success=touchdown && vz<2 && vh<1 && miss<10;
            summary.WriteLine(Row(current.Id,current.kind,current.condition,current.altitude,current.seed,current.enabled,touchdown,success,elapsed,err,nav.position.y-body.position.y,miss,vz,vh,fuel,accepted,wrong,attempted,errorSamples>0?Math.Sqrt(squaredError/errorSamples):err,current.site!=null?current.site.id:"original",current.site!=null?current.site.x:6198,current.site!=null?current.site.z:8512,current.errorId??"e0",current.initialError.x,current.initialError.z,expandedRun?"PhysX_contact":"proximity_0.08m"));
            completed++; Next();
        }
        static void BeforeReload() { Finish("Interrupted by script reload"); }
        static void Finish(string message)
        {
            if(!Running) return;
            Running=false; EditorApplication.update-=Tick; AssemblyReloadEvents.beforeAssemblyReload-=BeforeReload;
            trace?.Dispose(); cloudTrace?.Dispose(); summary?.Dispose(); scans?.Dispose(); trace=null; cloudTrace=null; summary=null; scans=null;
            Status=message+"; "+completed+" cases; wall_seconds="+(DateTime.UtcNow-startedUtc).TotalSeconds.ToString("F1",CultureInfo.InvariantCulture)+"; "+output;
            File.WriteAllText(output+"/status.txt",Status);
            File.WriteAllText(Path.GetFullPath(expandedRun?"../out/terrain_matching/latest_expanded.txt":"../out/terrain_matching/latest.txt"),output);
            if(physicsScene.IsValid()) SceneManager.UnloadSceneAsync(physicsScene);
            if(expandedRun) { foreach(var bundle in MapCache.Values) if(bundle.data!=null) UnityEngine.Object.Destroy(bundle.data); MapCache.Clear(); }
            else if(truthData!=null) UnityEngine.Object.Destroy(truthData);
            Debug.Log("[TerrainExperiment] "+Status);
            EditorApplication.delayCall+=()=>EditorApplication.isPlaying=false;
        }
    }
}
