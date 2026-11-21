"""Create a separate staged runner, retaining prior experiments unchanged."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
text=(ROOT/'LANTERN/Assets/Editor/ScanTrustExperiment.cs').read_text()
text=text.replace('ScanTrustExperiment','ScanUtilityExperiment')
def replace(old,new):
    global text
    assert text.count(old)==1,(old[:80],text.count(old))
    text=text.replace(old,new)

replace('static PortableScanTrust trust;','''static PortableScanTrust trust;
        static ScanUtilityPolicy utility;
        static string stage,selectedPolicy;
        static Plan plan;
        static Vector2 expectedCorrection;
        static bool hasPrevious;
        static int scanIndex;
        [Serializable] public class Error { public float x,z; }
        [Serializable] public class Draw { public string site_id,condition,error_id; public int variant,altitude,seed; public float error_x,error_z,true_x,true_z; }
        [Serializable] public class Plan { public LandingSite[] training_sites,validation_sites,evaluation_sites; public Draw[] collection; public Error[] development_errors,evaluation_errors; }''')
replace('public string kind, condition, errorId, arm;','public string kind, condition, errorId, arm;\n            public int variant;\n            public Vector3 trueOffset;')
replace('condition+"_"+altitude','condition+"_v"+variant+"_"+altitude')
start=text.index('        [MenuItem(');end=text.index('        public static void Start(',start)
text=text[:start]+'''        public static void Request(string requested)
        {
            if(Array.IndexOf(new[]{"collect_smoke","collect","dev_smoke","dev","eval_smoke","eval"},requested)<0)
                throw new ArgumentException("Unknown utility stage");
            if(Running || EditorApplication.isPlaying || EditorApplication.isCompiling)throw new InvalidOperationException("Editor busy");
            if(SceneManager.GetActiveScene().isDirty)throw new InvalidOperationException("Save active scene first");
            SessionState.SetString("LANTERN.PendingExperiment","utility_"+requested);EditorApplication.isPlaying=true;
        }
'''+text[end:]
replace('public static void Start(bool smoke)','public static void Start(string requested)')
replace('            const bool expanded=true;','''            stage=requested;
            bool smoke=stage.EndsWith("_smoke",StringComparison.Ordinal);
            const bool expanded=true;
            plan=JsonUtility.FromJson<Plan>(File.ReadAllText("Assets/Experiments/ScanUtility/plan.json"));''')
replace('            ScanTrustVerification.Validate();\n            trust=ScanTrustVerification.Load();','''            trust=ScanTrustVerification.Load();
            if(!stage.StartsWith("collect",StringComparison.Ordinal)){ScanUtilityVerification.Validate();utility=ScanUtilityVerification.Load();}
            selectedPolicy=stage.StartsWith("eval",StringComparison.Ordinal)?JsonUtility.FromJson<ScanUtilityPolicy.Choice>(File.ReadAllText("Assets/Experiments/ScanUtility/policy.json")).policy:"";''')
replace('"../out/scan_trust/"+DateTime.UtcNow.ToString("yyyyMMdd_HHmmss")+(smoke?"_smoke":"_closed_loop_v1")','"../out/scan_utility/"+DateTime.UtcNow.ToString("yyyyMMdd_HHmmss")+"_"+stage')
replace('"../docs/SCAN_TRUST_PROTOCOL_V1.md"','"../docs/SCAN_TRUST_PROTOCOL_V2.md"')
replace('"Assets/Editor/ScanUtilityExperiment.cs","Assets/Scripts/Experiments/TerrainNavigationCore.cs","Assets/Scripts/Experiments/PortableScanTrust.cs","Assets/Editor/ScanTrustVerification.cs"','"Assets/Editor/ScanUtilityExperiment.cs","Assets/Scripts/Experiments/TerrainNavigationCore.cs","Assets/Scripts/Experiments/PortableScanTrust.cs","Assets/Scripts/Experiments/ScanUtilityPolicy.cs","Assets/Editor/ScanUtilityVerification.cs"')
replace('            foreach(var path in sourceFiles)','''            sourceFiles.Add("Assets/Experiments/ScanUtility/plan.json");
            if(!stage.StartsWith("collect",StringComparison.Ordinal))sourceFiles.Add("Assets/Experiments/ScanUtility/model.json");
            if(stage.StartsWith("eval",StringComparison.Ordinal))sourceFiles.Add("Assets/Experiments/ScanUtility/policy.json");
            foreach(var path in sourceFiles)''')
replace('File.Copy(path,output+"/"+Path.GetFileName(path));','File.Copy(path,output+"/"+(path=="Assets/Experiments/ScanUtility/model.json"?"utility_model.json":Path.GetFileName(path)));')
replace('            File.Copy("Library/ScanTrust.validation.json",output+"/parity_report.json");','            if(!stage.StartsWith("collect",StringComparison.Ordinal))File.Copy("Library/ScanUtility.validation.json",output+"/parity_report.json");')
replace('contact_definition,arm");','contact_definition,arm,variant,stage,true_start_x,true_start_z");')
replace('applied_bad");','applied_bad,scan_index,normalized_rms,confidence_feature,correction_norm_m,agl_feature_m,consistency_m,has_previous,optimal_gain,utility_prediction,applied_gain,applied_error_m,beneficial_applied");')
start=text.index('            queue=new Queue<Case>();');end=text.index('            physicsScene=SceneManager.CreateScene(',start)
text=text[:start]+'''            queue=new Queue<Case>();
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
                var sites=evaluation?plan.evaluation_sites:plan.validation_sites;
                var errors=evaluation?plan.evaluation_errors:plan.development_errors;
                foreach(var site in sites)
                {
                    if(smoke && site.id!=sites[0].id)continue;
                    foreach(string condition in new[]{"aligned","relief_positive","map_shift"})
                    foreach(int altitude in (smoke?new[]{500}:evaluation?new[]{500,1500}:new[]{500,2000}))
                    for(int e=0;e<(smoke?1:errors.Length);e++)
                    foreach(int seed in (smoke?new[]{404}:evaluation?new[]{717,818,919}:new[]{404,505}))
                    foreach(string arm in (evaluation?new[]{"off","geometric","bounded","old_ml","utility"}:
                        new[]{"off","geometric","bounded","old_ml","utility_hard","utility_soft","utility_hybrid"}))
                        queue.Enqueue(new Case{kind="descent",site=site,condition=condition,altitude=altitude,
                            variant=evaluation?3:2,errorId="u"+e,initialError=new Vector3(errors[e].x,0,errors[e].z),
                            trueOffset=evaluation?new Vector3(-12,0,16):new Vector3(15,0,-10),seed=seed,arm=arm,enabled=arm!="off"});
                }
            }
'''+text[end:]
replace('+"_"+condition;','+"_"+condition+"_v"+current.variant;')
replace('                if(condition=="relief_change") real[j,i]+=12*Mathf.Exp(-((x+90)*(x+90)+(z-110)*(z-110))/(2*75*75));\n                float sx=condition=="map_shift"?-28:0, sz=condition=="map_shift"?36:0;','''                float bx=current.variant==0?90:current.variant==1?-140:current.variant==2?-90:-75;
                float bz=current.variant==0?-40:current.variant==1?75:current.variant==2?110:-80;
                float sigma=current.variant==0?50:current.variant==1?100:current.variant==2?75:65;
                float amplitude=current.variant==0?8:current.variant==1?20:current.variant==2?12:16;
                if(condition=="relief_positive" || condition=="relief_negative")
                    real[j,i]+=(condition=="relief_negative"?-1:1)*amplitude*Mathf.Exp(-((x-bx)*(x-bx)+(z-bz)*(z-bz))/(2*sigma*sigma));
                float sx=condition=="map_shift"?(current.variant==0?30:current.variant==1?-25:current.variant==2?-28:22):0;
                float sz=condition=="map_shift"?(current.variant==0?-20:current.variant==1?35:current.variant==2?36:-31):0;''')
replace('+condition+".bin"','+condition+"_v"+current.variant+".bin"')
replace('body.position=new Vector3(0,GroundHeight(Vector3.zero)+current.altitude,0);','body.position=current.trueOffset+Vector3.up*(GroundHeight(current.trueOffset)+current.altitude);')
replace('            rng=new System.Random(current.seed);','            hasPrevious=false;expectedCorrection=Vector2.zero;scanIndex=0;\n            rng=new System.Random(current.seed);')
start=text.index('            // All arms compute both vetoes');end=text.index('\n        static void Trace()',start)
text=text[:start]+'''            // Truth above is label/evaluation only. Feature construction is scene-free.
            var timer=System.Diagnostics.Stopwatch.StartNew();
            var features=ScanUtilityPolicy.Features(m,measuredAgl,expectedCorrection,hasPrevious);
            double prediction=utility!=null?utility.Predict(features):0;
            double oldScore=trust.Score(PortableScanTrust.Features(m));
            string policy=current.arm=="utility"?selectedPolicy:current.arm;
            float gain=policy=="old_ml"?(trust.Accept(m,oldScore)?1:0):ScanUtilityPolicy.Gain(policy,m,prediction,measuredAgl);
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
        static float Horizontal(Vector3 v) => new Vector2(v.x,v.z).magnitude;
'''+text[end:]
replace('''            { Trace(); MatchScan(); Trace(); Complete(false,0,0); return; }''','''            {
                for(int k=0;k<2;k++)
                {
                    float sampleAltNoise=Gaussian(rng)*.1f;
                    if(physics.Raycast(body.position+Vector3.up*.05f,Vector3.down,out var altitudeHit,4000,1,QueryTriggerInteraction.Ignore))
                        measuredAgl=Mathf.Max(0,altitudeHit.distance-.05f+sampleAltNoise);
                    Trace();MatchScan();elapsed+=3;Trace();
                }
                Complete(false,0,0);return;
            }''')
replace('expandedRun?"PhysX_contact":"proximity_0.08m",current.arm));','expandedRun?"PhysX_contact":"proximity_0.08m",current.arm,current.variant,stage,current.trueOffset.x,current.trueOffset.z));')
replace('"../out/scan_trust/latest_closed_loop.txt"','"../out/scan_utility/latest_"+stage+".txt"')
text=text.replace('[ScanTrustExperiment]','[ScanUtilityExperiment]')
text=text.replace('"Assets/Editor/ScanUtilityExperiment.cs"','"Assets/Editor/ScanUtilityRunner.cs"')
(ROOT/'LANTERN/Assets/Editor/ScanUtilityRunner.cs').write_bytes(text.encode('utf-8'))
print('Created staged utility runner')
