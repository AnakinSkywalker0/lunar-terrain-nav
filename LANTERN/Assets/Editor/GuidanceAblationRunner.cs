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
    public static class GuidanceAblationExperiment
    {
        const float Dt=.05f, Span=2400, SourceMin=0f;
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
        const float KfInitialVar=100f*100f, KfFixVar=2f*2f, KfProcessPerSecond=.05f, Chi2Gate=9.21f;
        static float navVar;
        static Vector3 biasVec;
        static PortableScanTrust trust;
        static ScanUtilityPolicy utility;
        static string stage,selectedPolicy;
        static Plan plan;
        static Vector2 expectedCorrection;
        static bool hasPrevious;
        static int scanIndex;
        [Serializable] public class Error { public float x,z; }
        [Serializable] public class Draw { public string site_id,condition,error_id; public int variant,altitude,seed; public float error_x,error_z,true_x,true_z; }
        [Serializable] public class Plan { public LandingSite[] training_sites,validation_sites,evaluation_sites,smoke_sites,wide_sites; public Draw[] collection; public Error[] development_errors,evaluation_errors; }
        [Serializable] class SourceMetadata { public int resolution; public float side_m,min_m,max_m; }
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
            public string kind, condition, errorId, arm, guidance;
            public float bias;
            public int variant;
            public Vector3 trueOffset;
            public int altitude, seed;
            public bool enabled;
            public LandingSite site;
            public Vector3 initialError;
            public string Id => kind+"_"+(site!=null?site.id+"_"+errorId+"_":"")+condition+"_v"+variant+"_"+altitude+"_"+seed+"_g"+guidance+(bias>0?"_b"+bias.ToString("0.####",CultureInfo.InvariantCulture):"")+"_"+arm;
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

        public static void Request(string requested)
        {
            if(Array.IndexOf(new[]{"eval_smoke","eval_g1","eval_wide","eval_g3","eval_sweep","eval_imu"},requested)<0)
                throw new ArgumentException("Unknown guidance-ablation stage");
            if(Running || EditorApplication.isPlaying || EditorApplication.isCompiling)throw new InvalidOperationException("Editor busy");
            if(SceneManager.GetActiveScene().isDirty)throw new InvalidOperationException("Save active scene first");
            SessionState.SetString("LANTERN.GA.Pending",requested);EditorApplication.isPlaying=true;
        }
        public static void Start(string requested)
        {
            if(Running || !EditorApplication.isPlaying || EditorApplication.isCompiling) throw new InvalidOperationException("Start isolated physics in ready Play mode.");
            var metadata=JsonUtility.FromJson<SourceMetadata>(File.ReadAllText("Assets/Experiments/ScanUtilityTransfer/site01_height.json"));
            source=new TerrainData { heightmapResolution=metadata.resolution, size=new Vector3(metadata.side_m,metadata.max_m-metadata.min_m,metadata.side_m) };
            var heights=new float[metadata.resolution,metadata.resolution];
            using(var reader=new BinaryReader(File.OpenRead("Assets/Experiments/ScanUtilityTransfer/site01_height.raw")))
            {
                if(reader.BaseStream.Length!=2L*metadata.resolution*metadata.resolution)throw new Exception("Source terrain length mismatch");
                for(int j=0;j<metadata.resolution;j++)for(int i=0;i<metadata.resolution;i++)heights[j,i]=reader.ReadUInt16()/65535f;
            }
            source.SetHeights(0,0,heights);
            stage=requested;
            bool smoke=stage.EndsWith("_smoke",StringComparison.Ordinal);
            const bool expanded=true;
            plan=JsonUtility.FromJson<Plan>(File.ReadAllText("Assets/Experiments/GuidanceAblation/plan.json"));
            SelfChecks();
            trust=ScanTrustVerification.Load();
            if(!stage.StartsWith("collect",StringComparison.Ordinal)){ScanUtilityVerification.Validate();utility=ScanUtilityVerification.Load();}
            selectedPolicy=stage.StartsWith("eval",StringComparison.Ordinal)?JsonUtility.FromJson<ScanUtilityPolicy.Choice>(File.ReadAllText("Assets/Experiments/ScanUtility/policy.json")).policy:"";
            expandedRun=true;
            startedUtc=DateTime.UtcNow;
            MapCache.Clear();
            string requestedOut=SessionState.GetString("LANTERN.GA.Out","");
            output=Path.GetFullPath("../out/guidance_ablation/"+(requestedOut!=""?requestedOut:DateTime.UtcNow.ToString("yyyyMMdd_HHmmss")+"_"+stage));
            bool resume=File.Exists(output+"/summary.csv");
            Directory.CreateDirectory(output);
            File.Copy("../docs/GUIDANCE_ABLATION_PROTOCOL.md",output+"/protocol.md",true);
            File.WriteAllText(output+"/environment.txt","UTC="+DateTime.UtcNow.ToString("O")+"\nUnity="+Application.unityVersion+"\nCPU="+SystemInfo.processorType+"\nPlatform="+Application.platform+"\nDT="+Dt+"\n3-DOF PhysX; ideal attitude; frozen scan-trust model inference; training performed separately in Python\n");
            var sourceFiles=new List<string>{"Assets/Editor/GuidanceAblationRunner.cs","Assets/Scripts/Experiments/TerrainNavigationCore.cs","Assets/Scripts/Experiments/PortableScanTrust.cs","Assets/Scripts/Experiments/ScanUtilityPolicy.cs","Assets/Editor/ScanUtilityVerification.cs"};
            if(expanded) sourceFiles.AddRange(new[]{"Assets/Scripts/Experiments/TerrainTouchdownRecorder.cs","Assets/Experiments/ScanTrust/FreshSites.json","Assets/Experiments/ScanTrust/model.json","Assets/Experiments/ScanTrust/rule.json"});
            sourceFiles.Add("Assets/Experiments/GuidanceAblation/plan.json");
            if(!stage.StartsWith("collect",StringComparison.Ordinal))sourceFiles.Add("Assets/Experiments/ScanUtility/model.json");
            if(stage.StartsWith("eval",StringComparison.Ordinal))sourceFiles.Add("Assets/Experiments/ScanUtility/policy.json");
            sourceFiles.Add("Assets/Experiments/ScanUtilityTransfer/site01_height.raw");
            sourceFiles.Add("Assets/Experiments/ScanUtilityTransfer/site01_height.json");
            foreach(var path in sourceFiles)
            {
                File.Copy(path,output+"/"+(path=="Assets/Experiments/ScanUtility/model.json"?"utility_model.json":Path.GetFileName(path)),true);
                using(var sha=System.Security.Cryptography.SHA256.Create())
                    File.AppendAllText(output+"/source_sha256.txt",BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(path))).Replace("-","")+"  "+path+"\n");
            }
            if(!stage.StartsWith("collect",StringComparison.Ordinal))File.Copy("Library/ScanUtility.validation.json",output+"/parity_report.json",true);
            summary=new StreamWriter(output+"/summary.csv",resume){AutoFlush=true};
            if(!resume) summary.WriteLine("id,kind,condition,altitude,seed,matching,touchdown,success,time_s,horizontal_error_m,vertical_error_m,target_miss_m,impact_vz,impact_vh,fuel_kg,accepted_matches,wrong_matches,attempted_matches,horizontal_rmse_m,site_id,site_x,site_z,error_id,initial_error_x,initial_error_z,contact_definition,arm,variant,stage,true_start_x,true_start_z");
            scans=new StreamWriter(output+"/scans.csv",resume){AutoFlush=true};
            if(!resume) scans.WriteLine("id,time_s,points,valid,accepted,applied,dx,dz,rms_m,confidence,before_error_m,proposed_error_m,wrong,match_ms,arm,rule_accept,ml_accept,bad_score,trust_ms,applied_bad,scan_index,normalized_rms,confidence_feature,correction_norm_m,agl_feature_m,consistency_m,has_previous,optimal_gain,utility_prediction,applied_gain,applied_error_m,beneficial_applied");
            queue=new Queue<Case>();
            if(stage.StartsWith("collect",StringComparison.Ordinal))
            {
                var sites=new List<LandingSite>(plan.training_sites);sites.AddRange(plan.validation_sites);
                int count=0;
                foreach(var draw in plan.collection)
                {
                    var site=sites.Find(s=>s.id==draw.site_id);
                    queue.Enqueue(new Case{kind="stationary",site=site,condition=draw.condition,altitude=draw.altitude,
                        variant=draw.variant,errorId=draw.error_id,initialError=new Vector3(draw.error_x,0,draw.error_z),
                        trueOffset=new Vector3(draw.true_x,0,draw.true_z),seed=draw.seed,arm="collect",enabled=false});
                    if(smoke && ++count==4)break;
                }
            }
            else
            {
                bool evaluation=stage.StartsWith("eval",StringComparison.Ordinal);
                var allSites=new List<LandingSite>(plan.evaluation_sites); allSites.AddRange(plan.wide_sites);
                var sites=smoke?plan.smoke_sites:stage=="eval_wide"?plan.wide_sites:(stage=="eval_g3"||stage=="eval_sweep"||stage=="eval_imu")?allSites.ToArray():plan.evaluation_sites;
                var errors=plan.evaluation_errors;
                bool sweep=stage=="eval_sweep", imu=stage=="eval_imu";
                foreach(var site in sites)
                {
                    foreach(string condition in (smoke?new[]{"aligned","relief_positive","map_shift"}:imu?new[]{"aligned","tie8","relief_positive"}:sweep?new[]{"aligned","relief_a0.5","relief_a1","relief_a2","relief_a4","relief_a8","relief_a16"}:new[]{"aligned","relief_positive","map_shift","tie3","tie8"}))
                    foreach(int vid in (sweep&&condition.StartsWith("relief_a",StringComparison.Ordinal)?new[]{0,1,2,3}:new[]{3}))
                    foreach(int altitude in (smoke?new[]{500}:new[]{500,1500}))
                    for(int e=0;e<(smoke?1:errors.Length);e++)
                    foreach(int seed in (smoke?new[]{404}:new[]{717}))
                    foreach(float bias in (imu?new[]{.0002f,.001f,.005f}:new[]{0f}))
                    foreach(string guide in ((stage=="eval_g3"||sweep||imu)?new[]{"baseline"}:new[]{"baseline","terminal","braking"}))
                    foreach(string arm in (imu?new[]{"off","geometric","authority","kf_chi2","kf_q1","kf_q10"}:stage=="eval_g3"?new[]{"off","geometric","bounded","authority","kf_chi2"}:sweep?new[]{"off","geometric","bounded","utility","authority","kf_chi2"}:new[]{"off","geometric","bounded","utility","authority"}))
                        queue.Enqueue(new Case{kind="descent",site=site,condition=condition,altitude=altitude,
                            variant=vid,errorId="u"+e,initialError=new Vector3(errors[e].x,0,errors[e].z),
                            trueOffset=new Vector3(-12,0,16),seed=seed,arm=arm,guidance=guide,bias=bias,enabled=arm!="off"});
                }
                if(resume)
                {
                    var done=new HashSet<string>();
                    foreach(var line in File.ReadAllLines(output+"/summary.csv")) { int c=line.IndexOf(','); if(c>0) done.Add(line.Substring(0,c)); }
                    var rest=new Queue<Case>(); foreach(var c in queue) if(!done.Contains(c.Id)) rest.Enqueue(c);
                    queue=rest; completed=done.Count-1;
                }
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
            Debug.Log("[GuidanceAblationExperiment] known-offset/sign, flat ambiguity, empty scan and map-bound checks passed.");
        }

        static void MakeMaps(string condition)
        {
            string cacheKey=(current.site!=null?current.site.id:"original")+"_"+condition+"_v"+current.variant;
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
                float bx=current.variant==0?90:current.variant==1?-140:current.variant==2?-90:-75;
                float bz=current.variant==0?-40:current.variant==1?75:current.variant==2?110:-80;
                float sigma=current.variant==0?50:current.variant==1?100:current.variant==2?75:65;
                float amplitude=condition.StartsWith("relief_a",StringComparison.Ordinal)?float.Parse(condition.Substring(8),CultureInfo.InvariantCulture):(current.variant==0?8:current.variant==1?20:current.variant==2?12:16);
                if(condition=="relief_positive" || condition=="relief_negative" || condition.StartsWith("relief_a",StringComparison.Ordinal))
                    real[j,i]+=(condition=="relief_negative"?-1:1)*amplitude*Mathf.Exp(-((x-bx)*(x-bx)+(z-bz)*(z-bz))/(2*sigma*sigma));
                float sx=condition=="map_shift"?(current.variant==0?30:current.variant==1?-25:current.variant==2?-28:22):condition=="tie3"?2.12f:condition=="tie8"?5.66f:0;
                float sz=condition=="map_shift"?(current.variant==0?-20:current.variant==1?35:current.variant==2?36:-31):condition=="tie3"?2.12f:condition=="tie8"?5.66f:0;
                prior[j,i]=source.GetInterpolatedHeight((cx+x+sx)/source.size.x,(cz+z+sz)/source.size.z)+SourceMin-center;
            }
            truth=new ElevationMap(real,new Vector2(-Span/2,-Span/2),spacing);
            map=new ElevationMap(prior,new Vector2(-Span/2,-Span/2),spacing);
            string mapFile=output+"/map_"+(current.site!=null?current.site.id+"_":"")+condition+"_v"+current.variant+".bin";
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
            body.position=current.trueOffset+Vector3.up*(GroundHeight(current.trueOffset)+current.altitude);
            body.linearVelocity=current.kind=="stationary"?Vector3.zero:new Vector3(0,-10,0);
            nav=new NavigationEstimate(body.position+current.initialError,body.linearVelocity);
            hasPrevious=false;expectedCorrection=Vector2.zero;scanIndex=0;navVar=KfInitialVar; { float phi=current.seed*.7f; biasVec=new Vector3(Mathf.Cos(phi),0,Mathf.Sin(phi))*current.bias; }
            rng=new System.Random(current.seed); fuel=800; elapsed=nextScan=nextTrace=0;
            previousVelocity=body.linearVelocity; accepted=wrong=attempted=0; squaredError=0; errorSamples=0;
            trace=new StreamWriter(output+"/"+current.Id+".csv"){AutoFlush=true};
            trace.WriteLine("t,x,y,z,ex,ey,ez,vx,vy,vz,evx,evy,evz,altimeter_m,fuel_kg");
            cloudTrace=new StreamWriter(Stream.Null);
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
            // Truth above is label/evaluation only. Feature construction is scene-free.
            var timer=System.Diagnostics.Stopwatch.StartNew();
            var features=ScanUtilityPolicy.Features(m,measuredAgl,expectedCorrection,hasPrevious);
            double prediction=utility!=null?utility.Predict(features):0;
            double oldScore=trust.Score(PortableScanTrust.Features(m));
            string policy=current.arm=="utility"?selectedPolicy:current.arm;
            float gain=policy=="old_ml"?(trust.Accept(m,oldScore)?1:0):ScanUtilityPolicy.Gain(policy,m,prediction,measuredAgl);
            if(current.arm.StartsWith("kf_",StringComparison.Ordinal))
            {
                navVar+=(current.arm=="kf_q1"?1f:current.arm=="kf_q10"?10f:KfProcessPerSecond)*3f; gain=0;
                if(m.valid&&m.accepted)
                {
                    float s=navVar+KfFixVar;
                    if(m.correction.sqrMagnitude<=Chi2Gate*s){ gain=navVar/s; navVar=(1-gain)*navVar; }
                }
            }
            if(current.arm=="authority") gain=(m.valid&&m.accepted)?Mathf.Min(1,AuthorityLimit(measuredAgl)/Mathf.Max(.001f,m.correction.magnitude)):0;
            double trustMs=timer.Elapsed.TotalMilliseconds;
            Vector2 delta=m.correction*gain;
            var gated=m;gated.accepted=gain>0;gated.correction=delta;nav.Correct(gated);
            float appliedError=Horizontal(estimateBefore+new Vector3(delta.x,0,delta.y)-body.position);
            float norm2=m.correction.sqrMagnitude;
            Vector3 error=estimateBefore-body.position;
            float optimal=norm2<.25f?1:Mathf.Clamp01(-(error.x*m.correction.x+error.z*m.correction.y)/norm2);
            bool apply=gain>0;
            scans.WriteLine(Row(current.Id,elapsed,m.points,m.valid,m.accepted,apply,m.correction.x,m.correction.y,m.rms,m.confidence,
                before,proposed,bad,m.milliseconds,current.arm,false,trust.Accept(m,oldScore),oldScore,trustMs,apply&&appliedError>10,
                scanIndex++,features[0],features[1],features[2],features[3],features[4],features[5],optimal,prediction,gain,appliedError,apply&&appliedError<before-.1f));
            expectedCorrection=m.correction-delta;hasPrevious=m.valid;
        }
        // Largest horizontal correction (m) the lander can still absorb: half of the rest-to-rest distance
        // reachable at the tilt-limited acceleration within the remaining descent time.
        const float TiltLimitAccel=(1.62f+.45f)*.17632698f;
        static float AuthorityLimit(float agl)
        { float tgo=Mathf.Sqrt(2*Mathf.Max(agl,1f)/.45f); return .5f*TiltLimitAccel*tgo*tgo/4f; }
        // baseline = frozen EstimateGuidance. terminal/braking are ablations (docs/GUIDANCE_ABLATION_PROTOCOL.md).
        static Vector3 GuidanceThrust(NavigationEstimate n,float agl,float mass,string mode)
        {
            if(mode=="baseline") return EstimateGuidance.Thrust(n,agl,mass);
            float vy=-Mathf.Min(30,.5f+Mathf.Sqrt(2*.45f*Mathf.Max(0,agl-.5f)));
            float ay=Mathf.Max(0,1.62f+.8f*(vy-n.velocity.y));
            float lim=ay*Mathf.Tan(10*Mathf.Deg2Rad);
            var pos=new Vector2(n.position.x,n.position.z); var vel=new Vector2(n.velocity.x,n.velocity.z);
            Vector2 h;
            if(mode=="terminal") h=agl<30f?-.5f*vel:-.04f*pos-.5f*vel;
            else
            {
                float d=pos.magnitude;
                float vmax=Mathf.Min(Mathf.Sqrt(2*.5f*lim*Mathf.Max(0,d-1f)),.2f*d);
                Vector2 desired=d>1e-3f?-pos/d*vmax:Vector2.zero;
                h=agl<5f?-.5f*vel:(desired-vel);
            }
            h=Vector2.ClampMagnitude(h,lim);
            return Vector3.ClampMagnitude(new Vector3(h.x,ay,h.y)*mass,6000);
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
            {
                for(int k=0;k<2;k++)
                {
                    float sampleAltNoise=Gaussian(rng)*.1f;
                    if(physics.Raycast(body.position+Vector3.up*.05f,Vector3.down,out var altitudeHit,4000,1,QueryTriggerInteraction.Ignore))
                        measuredAgl=Mathf.Max(0,altitudeHit.distance-.05f+sampleAltNoise);
                    Trace();MatchScan();elapsed+=3;Trace();
                }
                Complete(false,0,0);return;
            }
            // Sensor adapter: acceleration from physical velocity changes, with noise.
            Vector3 actualAcceleration=(body.linearVelocity-previousVelocity)/Dt;
            Vector3 measuredAcceleration=actualAcceleration+new Vector3(Gaussian(rng),Gaussian(rng),Gaussian(rng))*.002f+biasVec;
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
            Vector3 thrust=fuel>0?GuidanceThrust(nav,measuredAgl,1200+fuel,current.guidance):Vector3.zero;
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
            summary.WriteLine(Row(current.Id,current.kind,current.condition,current.altitude,current.seed,current.enabled,touchdown,success,elapsed,err,nav.position.y-body.position.y,miss,vz,vh,fuel,accepted,wrong,attempted,errorSamples>0?Math.Sqrt(squaredError/errorSamples):err,current.site!=null?current.site.id:"original",current.site!=null?current.site.x:6198,current.site!=null?current.site.z:8512,current.errorId??"e0",current.initialError.x,current.initialError.z,expandedRun?"PhysX_contact":"proximity_0.08m",current.arm,current.variant,stage,current.trueOffset.x,current.trueOffset.z));
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
            File.WriteAllText(Path.GetFullPath("../out/guidance_ablation/latest_"+stage+".txt"),output);
            if(physicsScene.IsValid()) SceneManager.UnloadSceneAsync(physicsScene);
            if(expandedRun) { foreach(var bundle in MapCache.Values) if(bundle.data!=null) UnityEngine.Object.Destroy(bundle.data); MapCache.Clear(); }
            else if(truthData!=null) UnityEngine.Object.Destroy(truthData);
            if(source!=null)UnityEngine.Object.Destroy(source);
            Debug.Log("[GuidanceAblationExperiment] "+Status);
            EditorApplication.delayCall+=()=>EditorApplication.isPlaying=false;
            if(SessionState.GetBool("LANTERN.GA.Headless",false) && (message=="Complete" || message.StartsWith("ERROR",StringComparison.Ordinal)))
            {
                bool ok=message=="Complete"; string where=output, status=Status;
                EditorApplication.delayCall+=()=>{ File.WriteAllText(where+(ok?"/DONE.txt":"/FAILED.txt"),status); EditorApplication.Exit(ok?0:2); };
            }
        }
    }
}
