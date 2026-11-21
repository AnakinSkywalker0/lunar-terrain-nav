"""Derive a separate four-arm harness; never mutate old frozen navigation core."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
text=(ROOT/'LANTERN/Assets/Editor/ShortDescentExperiment.cs').read_text()
text=text.replace('ShortDescentExperiment','ScanTrustExperiment')

def replace(old,new):
    global text
    assert text.count(old)==1,(old[:100],text.count(old))
    text=text.replace(old,new)

replace('static NavigationEstimate nav;','static NavigationEstimate nav;\n        static PortableScanTrust trust;')
replace('public string kind, condition, errorId;','public string kind, condition, errorId, arm;')
replace('+(enabled?"on":"off");','+arm;')
start=text.index('        [MenuItem(')
end=text.index('        public static void Start(',start)
text=text[:start]+'''        [MenuItem("SensorTrust/Experiments/Run scan-trust smoke")]
        public static void Smoke() { Request(true); }
        [MenuItem("SensorTrust/Experiments/Run scan-trust protocol v1")]
        public static void Full() { Request(false); }
        static void Request(bool smoke)
        {
            if(Running || EditorApplication.isPlaying || EditorApplication.isCompiling) throw new InvalidOperationException("Editor is busy.");
            if(SceneManager.GetActiveScene().isDirty) throw new InvalidOperationException("Save the current scene before starting.");
            SessionState.SetString("LANTERN.PendingExperiment",smoke?"trust_smoke":"trust_full");
            EditorApplication.isPlaying=true;
        }

'''+text[end:]
replace('public static void Start(bool smoke,bool expanded=false)','public static void Start(bool smoke)')
replace('            SelfChecks();\n            expandedRun=expanded;','            const bool expanded=true;\n            SelfChecks();\n            ScanTrustVerification.Validate();\n            trust=ScanTrustVerification.Load();\n            expandedRun=true;')
replace('"../out/terrain_matching/"+DateTime.UtcNow.ToString("yyyyMMdd_HHmmss")+(expanded?(smoke?"_expanded_smoke":"_expanded_v2"):(smoke?"_smoke":"_v1"))','"../out/scan_trust/"+DateTime.UtcNow.ToString("yyyyMMdd_HHmmss")+(smoke?"_smoke":"_closed_loop_v1")')
replace('expanded?"../docs/TERRAIN_MATCHING_PROTOCOL_V2.md":"../docs/TERRAIN_MATCHING_PROTOCOL.md"','"../docs/SCAN_TRUST_PROTOCOL_V1.md"')
replace('3-DOF PhysX; ideal attitude; no ML training','3-DOF PhysX; ideal attitude; frozen scan-trust model inference; training performed separately in Python')
replace('"Assets/Editor/ScanTrustExperiment.cs","Assets/Scripts/Experiments/TerrainNavigationCore.cs"','"Assets/Editor/ScanTrustExperiment.cs","Assets/Scripts/Experiments/TerrainNavigationCore.cs","Assets/Scripts/Experiments/PortableScanTrust.cs","Assets/Editor/ScanTrustVerification.cs"')
replace('"Assets/Scripts/Experiments/TerrainTouchdownRecorder.cs","Assets/Experiments/ExpandedSites.json"','"Assets/Scripts/Experiments/TerrainTouchdownRecorder.cs","Assets/Experiments/ScanTrust/FreshSites.json","Assets/Experiments/ScanTrust/model.json","Assets/Experiments/ScanTrust/rule.json"')
replace('"/environment.txt",','"/environment.txt",') # Ensure the expected old harness is used.
replace('            summary=new StreamWriter(output+"/summary.csv"){AutoFlush=true};','            File.Copy("Library/ScanTrust.validation.json",output+"/parity_report.json");\n            summary=new StreamWriter(output+"/summary.csv"){AutoFlush=true};')
replace('initial_error_z,contact_definition");','initial_error_z,contact_definition,arm");')
replace('wrong,match_ms");','wrong,match_ms,arm,rule_accept,ml_accept,bad_score,trust_ms,applied_bad");')
start=text.index('            queue=new Queue<Case>();')
end=text.index('            physicsScene=SceneManager.CreateScene(',start)
text=text[:start]+'''            queue=new Queue<Case>();
            var sites=JsonUtility.FromJson<SiteManifest>(File.ReadAllText("Assets/Experiments/ScanTrust/FreshSites.json")).sites;
            if(sites==null || sites.Length!=3) throw new Exception("Expected three frozen fresh sites");
            var errors=new[]{new Vector3(45,0,70),new Vector3(-95,0,-35),new Vector3(75,0,-90)};
            foreach(var site in sites)
            {
                if(smoke && site.id!="fresh01") continue;
                foreach(string condition in Conditions)
                foreach(int altitude in (smoke?new[]{500}:new[]{500,2000}))
                for(int e=0;e<(smoke?1:errors.Length);e++)
                foreach(int seed in (smoke?new[]{101}:new[]{101,202,303}))
                foreach(string arm in new[]{"off","geometric","rule","ml"})
                    queue.Enqueue(new Case{kind="descent",site=site,condition=condition,altitude=altitude,
                        errorId="new_e"+e,initialError=errors[e],seed=seed,arm=arm,enabled=arm!="off"});
            }
'''+text[end:]
replace('12*Mathf.Exp(-((x-120)*(x-120)+(z-60)*(z-60))/(2*60*60))','12*Mathf.Exp(-((x+90)*(x+90)+(z-110)*(z-110))/(2*75*75))')
replace('float sx=condition=="map_shift"?40:0, sz=condition=="map_shift"?-24:0;','float sx=condition=="map_shift"?-28:0, sz=condition=="map_shift"?36:0;')
replace('''            // Both arms compute the same matcher. Only this line differs by arm.
            if(current.enabled) nav.Correct(m);
            scans.WriteLine(Row(current.Id,elapsed,m.points,m.valid,m.accepted,current.enabled&&m.accepted,m.correction.x,m.correction.y,m.rms,m.confidence,before,proposed,bad,m.milliseconds));''','''            // All arms compute both vetoes using identical observable features.
            // Truth above is evaluation only and is never passed to the gate.
            var timer=System.Diagnostics.Stopwatch.StartNew();
            double score=trust.Score(PortableScanTrust.Features(m));
            bool mlAccept=trust.Accept(m,score), ruleAccept=trust.RuleAccept(m);
            double trustMs=timer.Elapsed.TotalMilliseconds;
            bool apply=current.arm=="geometric"?m.accepted:current.arm=="rule"?ruleAccept:current.arm=="ml"?mlAccept:false;
            var gated=m; gated.accepted=apply; nav.Correct(gated);
            scans.WriteLine(Row(current.Id,elapsed,m.points,m.valid,m.accepted,apply,m.correction.x,m.correction.y,m.rms,m.confidence,before,proposed,bad,m.milliseconds,current.arm,ruleAccept,mlAccept,score,trustMs,apply&&proposed>10));''')
replace('expandedRun?"PhysX_contact":"proximity_0.08m"));','expandedRun?"PhysX_contact":"proximity_0.08m",current.arm));')
replace('Path.GetFullPath(expandedRun?"../out/terrain_matching/latest_expanded.txt":"../out/terrain_matching/latest.txt")','Path.GetFullPath("../out/scan_trust/latest_closed_loop.txt")')
text=text.replace('[TerrainExperiment]','[ScanTrustExperiment]')
(ROOT/'LANTERN/Assets/Editor/ScanTrustExperiment.cs').write_text(text)
print('Created separate scan-trust harness')
