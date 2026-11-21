"""Generate GuidanceAblationRunner.cs from the frozen transfer runner.

The transfer runner (ScanUtilityTransferRunner.cs) is left untouched so its published results stay
reproducible. This script applies a fixed list of exact-match edits and fails if any pattern is
missing or ambiguous.
"""
from pathlib import Path

EDITOR = Path(__file__).resolve().parents[1] / "LANTERN/Assets/Editor"
src = (EDITOR / "ScanUtilityTransferRunner.cs").read_text(encoding="utf-8")


def rep(old, new, count=1):
    global src
    assert src.count(old) == count, (old[:80], src.count(old))
    src = src.replace(old, new)


rep("public static class ScanUtilityTransferExperiment", "public static class GuidanceAblationExperiment")
rep("[ScanUtilityTransferExperiment]", "[GuidanceAblationExperiment]", 2)
rep("public LandingSite[] training_sites,validation_sites,evaluation_sites,smoke_sites;",
    "public LandingSite[] training_sites,validation_sites,evaluation_sites,smoke_sites,wide_sites;")
rep("public string kind, condition, errorId, arm;", "public string kind, condition, errorId, arm, guidance;\n            public float bias;")
rep('"_"+seed+"_"+arm;', '"_"+seed+"_g"+guidance+(bias>0?"_b"+bias.ToString("0.####",CultureInfo.InvariantCulture):"")+"_"+arm;')

i = src.index("public static void Request(string requested)")
j = src.index("public static void Start(string requested)")
src = src[:i] + """public static void Request(string requested)
        {
            if(Array.IndexOf(new[]{"eval_smoke","eval_g1","eval_wide","eval_g3","eval_sweep","eval_imu"},requested)<0)
                throw new ArgumentException("Unknown guidance-ablation stage");
            if(Running || EditorApplication.isPlaying || EditorApplication.isCompiling)throw new InvalidOperationException("Editor busy");
            if(SceneManager.GetActiveScene().isDirty)throw new InvalidOperationException("Save active scene first");
            SessionState.SetString("LANTERN.GA.Pending",requested);EditorApplication.isPlaying=true;
        }
        """ + src[j:]

rep('"Assets/Experiments/ScanUtilityTransfer/plan.json"', '"Assets/Experiments/GuidanceAblation/plan.json"', 2)
rep('output=Path.GetFullPath("../out/scan_utility_transfer/"+DateTime.UtcNow.ToString("yyyyMMdd_HHmmss")+"_"+stage);',
    'string requestedOut=SessionState.GetString("LANTERN.GA.Out","");\n'
    '            output=Path.GetFullPath("../out/guidance_ablation/"+(requestedOut!=""?requestedOut:DateTime.UtcNow.ToString("yyyyMMdd_HHmmss")+"_"+stage));\n'
    '            bool resume=File.Exists(output+"/summary.csv");')
rep('File.Copy("../docs/SCAN_UTILITY_TRANSFER_PROTOCOL.md",output+"/protocol.md");',
    'File.Copy("../docs/GUIDANCE_ABLATION_PROTOCOL.md",output+"/protocol.md",true);')
rep('"Assets/Editor/ScanUtilityTransferRunner.cs"', '"Assets/Editor/GuidanceAblationRunner.cs"')
rep('File.Copy(path,output+"/"+(path=="Assets/Experiments/ScanUtility/model.json"?"utility_model.json":Path.GetFileName(path)));',
    'File.Copy(path,output+"/"+(path=="Assets/Experiments/ScanUtility/model.json"?"utility_model.json":Path.GetFileName(path)),true);')
rep('File.Copy("Library/ScanUtility.validation.json",output+"/parity_report.json");',
    'File.Copy("Library/ScanUtility.validation.json",output+"/parity_report.json",true);')
rep('summary=new StreamWriter(output+"/summary.csv"){AutoFlush=true};',
    'summary=new StreamWriter(output+"/summary.csv",resume){AutoFlush=true};')
rep('scans=new StreamWriter(output+"/scans.csv"){AutoFlush=true};',
    'scans=new StreamWriter(output+"/scans.csv",resume){AutoFlush=true};')
rep('            summary.WriteLine("id,kind', '            if(!resume) summary.WriteLine("id,kind')
rep('            scans.WriteLine("id,time_s', '            if(!resume) scans.WriteLine("id,time_s')

a = src.index("                var sites=smoke?plan.smoke_sites:plan.evaluation_sites;")
b = src.index("            physicsScene=SceneManager.CreateScene")
src = src[:a] + """                var allSites=new List<LandingSite>(plan.evaluation_sites); allSites.AddRange(plan.wide_sites);
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
""" + src[b:]

rep('cloudTrace=new StreamWriter(output+"/"+current.Id+"_cloud.csv"){AutoFlush=true};',
    'cloudTrace=new StreamWriter(Stream.Null);')
rep('float sx=condition=="map_shift"?(current.variant==0?30:current.variant==1?-25:current.variant==2?-28:22):0;',
    'float sx=condition=="map_shift"?(current.variant==0?30:current.variant==1?-25:current.variant==2?-28:22):condition=="tie3"?2.12f:condition=="tie8"?5.66f:0;')
rep('float sz=condition=="map_shift"?(current.variant==0?-20:current.variant==1?35:current.variant==2?36:-31):0;',
    'float sz=condition=="map_shift"?(current.variant==0?-20:current.variant==1?35:current.variant==2?36:-31):condition=="tie3"?2.12f:condition=="tie8"?5.66f:0;')
rep('float gain=policy=="old_ml"?(trust.Accept(m,oldScore)?1:0):ScanUtilityPolicy.Gain(policy,m,prediction,measuredAgl);',
    'float gain=policy=="old_ml"?(trust.Accept(m,oldScore)?1:0):ScanUtilityPolicy.Gain(policy,m,prediction,measuredAgl);\n'
    '            if(current.arm=="authority") gain=(m.valid&&m.accepted)?Mathf.Min(1,AuthorityLimit(measuredAgl)/Mathf.Max(.001f,m.correction.magnitude)):0;')
# Unmodelled-relief amplitude sweep: condition "relief_a<metres>" uses the variant's bump position/width.
rep('float amplitude=current.variant==0?8:current.variant==1?20:current.variant==2?12:16;',
    'float amplitude=condition.StartsWith("relief_a",StringComparison.Ordinal)?float.Parse(condition.Substring(8),CultureInfo.InvariantCulture):(current.variant==0?8:current.variant==1?20:current.variant==2?12:16);')
rep('if(condition=="relief_positive" || condition=="relief_negative")',
    'if(condition=="relief_positive" || condition=="relief_negative" || condition.StartsWith("relief_a",StringComparison.Ordinal))')
rep('Vector3 measuredAcceleration=actualAcceleration+new Vector3(Gaussian(rng),Gaussian(rng),Gaussian(rng))*.002f;',
    'Vector3 measuredAcceleration=actualAcceleration+new Vector3(Gaussian(rng),Gaussian(rng),Gaussian(rng))*.002f+biasVec;')
# Classical baseline (plan gate G3): scalar position-variance Kalman update with a chi-square (99%, 2 dof)
# innovation gate. Constants are design values fixed before any result: they are NOT tuned on outcomes.
rep('hasPrevious=false;expectedCorrection=Vector2.zero;scanIndex=0;',
    'hasPrevious=false;expectedCorrection=Vector2.zero;scanIndex=0;navVar=KfInitialVar;'
    ' { float phi=current.seed*.7f; biasVec=new Vector3(Mathf.Cos(phi),0,Mathf.Sin(phi))*current.bias; }')
rep('        static NavigationEstimate nav;',
    '        static NavigationEstimate nav;\n'
    '        const float KfInitialVar=100f*100f, KfFixVar=2f*2f, KfProcessPerSecond=.05f, Chi2Gate=9.21f;\n'
    '        static float navVar;\n        static Vector3 biasVec;')
rep('            if(current.arm=="authority") gain=',
    '            if(current.arm.StartsWith("kf_",StringComparison.Ordinal))\n'
    '            {\n'
    '                navVar+=(current.arm=="kf_q1"?1f:current.arm=="kf_q10"?10f:KfProcessPerSecond)*3f; gain=0;\n'
    '                if(m.valid&&m.accepted)\n'
    '                {\n'
    '                    float s=navVar+KfFixVar;\n'
    '                    if(m.correction.sqrMagnitude<=Chi2Gate*s){ gain=navVar/s; navVar=(1-gain)*navVar; }\n'
    '                }\n'
    '            }\n'
    '            if(current.arm=="authority") gain=')
rep("EstimateGuidance.Thrust(nav,measuredAgl,1200+fuel)", "GuidanceThrust(nav,measuredAgl,1200+fuel,current.guidance)")
rep("        static float Horizontal(Vector3 v) =>", """        // Largest horizontal correction (m) the lander can still absorb: half of the rest-to-rest distance
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
        static float Horizontal(Vector3 v) =>""")
rep('File.WriteAllText(Path.GetFullPath("../out/scan_utility_transfer/latest_"+stage+".txt"),output);',
    'File.WriteAllText(Path.GetFullPath("../out/guidance_ablation/latest_"+stage+".txt"),output);')
rep("            EditorApplication.delayCall+=()=>EditorApplication.isPlaying=false;\n        }",
    """            EditorApplication.delayCall+=()=>EditorApplication.isPlaying=false;
            if(SessionState.GetBool("LANTERN.GA.Headless",false) && (message=="Complete" || message.StartsWith("ERROR",StringComparison.Ordinal)))
            {
                bool ok=message=="Complete"; string where=output, status=Status;
                EditorApplication.delayCall+=()=>{ File.WriteAllText(where+(ok?"/DONE.txt":"/FAILED.txt"),status); EditorApplication.Exit(ok?0:2); };
            }
        }""")

(EDITOR / "GuidanceAblationRunner.cs").write_text(src, encoding="utf-8")
print("wrote GuidanceAblationRunner.cs,", len(src.splitlines()), "lines")
