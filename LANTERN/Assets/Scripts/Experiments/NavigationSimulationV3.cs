using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace SensorTrust.Experiments.NavigationV3
{
    [Serializable] public sealed class TerrainSite { public string id, file, sha256, split; public float x,z; }
    [Serializable] public sealed class TerrainManifest { public int version; public TerrainSite[] sites; public string[] conditions,arms; }
    [Serializable] public sealed class LandingCase
    {
        public string site, condition, arm;
        public int altitude, seed;
        public string Id => site+"_"+condition+"_"+altitude+"_"+seed+"_"+arm;
    }
    [Serializable] public sealed class SimulationSettings
    {
        public float dt=.05f, rangePeriod=.1f, scanPeriod=3, rangeLatency=.15f, scanLatency=.3f;
        public float rangeNoise=.1f, accelerationNoise=.01f, attitudeSigmaDegrees=.02f;
        public float initialVelocitySigma=.5f, initialErrorMinimum=25, initialErrorMaximum=70;
        public float maximumSeconds=300, minimumScanAltitude=80;
        public FusionSettings fusion=new FusionSettings();
    }
    public sealed class TerrainTile
    {
        public readonly float[,] Ground, Prior, Sigma;
        public readonly float Span;
        TerrainTile(float[,] ground,float[,] prior,float[,] sigma,float span)
        { Ground=ground; Prior=prior; Sigma=sigma; Span=span; }
        public static TerrainTile Load(byte[] bytes)
        {
            using (var reader=new BinaryReader(new MemoryStream(bytes,false)))
            {
                int ng=reader.ReadInt32(),nm=reader.ReadInt32(); float span=reader.ReadSingle();
                if (ng!=513 || nm!=301 || span!=2400 || bytes.Length!=12+4*(ng*ng+2*nm*nm))
                    throw new InvalidDataException("Wrong navigation terrain format");
                float[,] Read(int n,bool nonnegative)
                {
                    var result=new float[n,n];
                    for(int j=0;j<n;j++) for(int i=0;i<n;i++)
                    { float v=reader.ReadSingle(); if(!NavigationFilter.Finite(v) || (nonnegative && v<0)) throw new InvalidDataException("Invalid terrain sample"); result[j,i]=v; }
                    return result;
                }
                return new TerrainTile(Read(ng,false),Read(nm,false),Read(nm,true),span);
            }
        }
    }

    public sealed class SensorRecord
    {
        public ObservationKind Kind;
        public int Sequence, Points;
        public double Captured,Delivered,Nis=-1,Prediction=-1,Inflation=1,VarianceX,VarianceZ,CovarianceXZ;
        public string Decision;
        public bool InjectedFault;
        public float Range,CorrectionX,CorrectionZ,Rms,Confidence,FixMapError=-1;
    }

    [Serializable] public sealed class LandingResult
    {
        public string id,site,condition,arm,termination;
        public int altitude,seed,rangeAccepted,rangeRejected,scanAccepted,scanRejected,missingRanges,missingScans,mlFallbacks;
        public bool contact,absolute10,absolute50,absolute100,map10,map50,map100;
        public float time,absoluteMiss,mapMiss,impactVertical,impactHorizontal,fuel,finalX,finalZ,shiftX,shiftZ;
    }

    /// <summary>Sensor/physics adapter only. Navigation and guidance receive no ground truth.</summary>
    public sealed class NavigationSimulation : IDisposable
    {
        sealed class Pending
        {
            public ObservationKind Kind;
            public int Sequence;
            public double Time,Ready;
            public float Range,FeatureAltitude;
            public List<Vector3> Points;
            public Vector3 ActualPosition; // Evaluation only, never supplied to matcher/estimator/ML.
            public string Unavailable;
            public bool InjectedFault;
        }
        public readonly LandingCase Case;
        public readonly SimulationSettings Settings;
        public readonly DelayedNavigation Navigation;
        public readonly LandingGuidance Guidance=new LandingGuidance();
        public readonly ElevationMap Map, MapSigma;
        public readonly Vector2 MapShift;
        public readonly Rigidbody Body;
        public LandingResult Result { get; private set; }
        public bool Finished => Result!=null;
        public int MlFallbackCount => mlFallbacks;
        public float Fuel { get; private set; }=800;
        public double Time => Navigation.Time;
        public Vector3 InitialEstimate { get; }
        public Vector3 InitialVelocityEstimate { get; }
        public event Action<SensorRecord> SensorObserved;
        readonly Scene scene;
        readonly PhysicsScene physics;
        readonly TerrainData groundData;
        readonly TerrainLayer displayLayer;
        readonly Texture2D displayTexture;
        readonly TerrainTouchdownRecorder touchdown;
        readonly ScanUtilityPolicy model;
        readonly System.Random imuRng,rangeRng,scanRng;
        readonly Vector3 accelerationBias;
        readonly Quaternion attitudeError;
        readonly List<Pending> pending=new List<Pending>();
        int step,rangeSequence,scanSequence,rangeAccepted,rangeRejected,scanAccepted,scanRejected,missingRanges,missingScans,mlFallbacks;
        bool disposed,hasPreviousFix;
        Vector2 previousFixOffset;

        public NavigationSimulation(LandingCase configuration,SimulationSettings settings,TerrainTile tile,ScanUtilityPolicy model=null,bool visible=false)
        {
            if (configuration==null || settings==null || tile==null || settings.dt!=.05f ||
                Array.IndexOf(new[]{"classical_pd","classical_terminal","ml_terminal"},configuration.arm)<0 ||
                Array.IndexOf(new[]{"nominal","range_spike","range_dropout","scan_dropout","gross_map_shift","gross_relief"},configuration.condition)<0)
                throw new ArgumentException("Invalid navigation experiment configuration");
            if(settings.rangePeriod!=.1f || settings.scanPeriod!=3 || settings.rangeLatency!=.15f || settings.scanLatency!=.3f)
                throw new ArgumentException("Sensor clocks must match the frozen v3 protocol");
            Case=configuration; Settings=settings; this.model=model;
            MapShift=Case.condition=="gross_map_shift" ? new Vector2(22,-31) : Vector2.zero;
            Vector2 origin=new Vector2(-tile.Span/2,-tile.Span/2)-MapShift;
            Map=new ElevationMap(tile.Prior,origin,tile.Span/(tile.Prior.GetLength(0)-1));
            MapSigma=new ElevationMap(tile.Sigma,origin,Map.spacing);
            var initialization=new System.Random(Case.seed);
            imuRng=new System.Random(Case.seed+10000); rangeRng=new System.Random(Case.seed+20000); scanRng=new System.Random(Case.seed+30000);
            accelerationBias=new Vector3(Gaussian(initialization),Gaussian(initialization),Gaussian(initialization))*.003f;
            attitudeError=Quaternion.Euler(Gaussian(initialization)*settings.attitudeSigmaDegrees,0,Gaussian(initialization)*settings.attitudeSigmaDegrees);
            scene=SceneManager.CreateScene("Navigation v3 "+Guid.NewGuid().ToString("N"),new CreateSceneParameters(LocalPhysicsMode.Physics3D));
            physics=scene.GetPhysicsScene();
            try
            {
                var actual=(float[,])tile.Ground.Clone(); int n=actual.GetLength(0);
                float low=float.PositiveInfinity,high=float.NegativeInfinity;
                for(int j=0;j<n;j++) for(int i=0;i<n;i++)
                {
                    float x=-tile.Span/2+i*tile.Span/(n-1),z=-tile.Span/2+j*tile.Span/(n-1);
                    if(Case.condition=="gross_relief") actual[j,i]+=16*Mathf.Exp(-((x+75)*(x+75)+(z+80)*(z+80))/(2*65*65));
                    low=Mathf.Min(low,actual[j,i]); high=Mathf.Max(high,actual[j,i]);
                }
                low=Mathf.Floor(low)-1; high=Mathf.Ceil(high)+1;
                groundData=new TerrainData { heightmapResolution=n,size=new Vector3(tile.Span,high-low,tile.Span) };
                for(int j=0;j<n;j++) for(int i=0;i<n;i++) actual[j,i]=(actual[j,i]-low)/(high-low);
                groundData.SetHeights(0,0,actual);
                var ground=Terrain.CreateTerrainGameObject(groundData); ground.name="Site01 ground (uncertainty-scaled proxy)";
                ground.transform.position=new Vector3(-tile.Span/2,low,-tile.Span/2);
                SceneManager.MoveGameObjectToScene(ground,scene); ground.GetComponent<Terrain>().enabled=visible;
                if(visible)
                {
                    displayTexture=new Texture2D(1,1,TextureFormat.RGB24,false);
                    displayTexture.SetPixel(0,0,new Color(.28f,.29f,.31f)); displayTexture.Apply();
                    displayLayer=new TerrainLayer { diffuseTexture=displayTexture,tileSize=new Vector2(20,20) };
                    groundData.terrainLayers=new[]{displayLayer};
                }
                var craft=new GameObject("Lander physics and sensor adapter"); craft.layer=8;
                SceneManager.MoveGameObjectToScene(craft,scene);
                Body=craft.AddComponent<Rigidbody>(); Body.useGravity=false; Body.mass=2000;
                Body.constraints=RigidbodyConstraints.FreezeRotation; Body.linearDamping=0;
                Body.collisionDetectionMode=CollisionDetectionMode.ContinuousDynamic;
                var collider=craft.AddComponent<SphereCollider>(); collider.radius=.4f; collider.center=Vector3.up*.4f;
                touchdown=craft.AddComponent<TerrainTouchdownRecorder>();
                var start=new Vector3(-12,0,16);
                float surface=groundData.GetInterpolatedHeight((start.x+tile.Span/2)/tile.Span,(start.z+tile.Span/2)/tile.Span)+low;
                Body.position=start+Vector3.up*(surface+Case.altitude); Body.linearVelocity=new Vector3(.5f,-10,-.25f);
                float angle=(float)(initialization.NextDouble()*2*Math.PI);
                float magnitude=settings.initialErrorMinimum+(float)initialization.NextDouble()*(settings.initialErrorMaximum-settings.initialErrorMinimum);
                InitialEstimate=Body.position+new Vector3(Mathf.Cos(angle)*magnitude,Gaussian(initialization)*2,Mathf.Sin(angle)*magnitude);
                InitialVelocityEstimate=Body.linearVelocity+new Vector3(Gaussian(initialization),Gaussian(initialization),Gaussian(initialization))*settings.initialVelocitySigma;
                Navigation=new DelayedNavigation(InitialEstimate,InitialVelocityEstimate,settings.fusion,Map,MapSigma);
                Physics.SyncTransforms();
            }
            catch { Dispose(); throw; }
        }

        public static float Gaussian(System.Random rng)
            => (float)(Math.Sqrt(-2*Math.Log(1-rng.NextDouble()))*Math.Cos(2*Math.PI*rng.NextDouble()));

        void Acquire()
        {
            // Integer clocks: schedules and RNG consumption do not depend on policy decisions.
            if(step%2==0)
            {
                double time=Time; float noise=Gaussian(rangeRng)*Settings.rangeNoise;
                var packet=new Pending { Kind=ObservationKind.Range,Time=time,Ready=time+Settings.rangeLatency,Sequence=rangeSequence++ };
                if(physics.Raycast(Body.position,Vector3.down,out var hit,4000,1,QueryTriggerInteraction.Ignore))
                    packet.Range=Mathf.Max(0,hit.distance+noise);
                else packet.Unavailable="NoReturn";
                if(Case.condition=="range_dropout" && time>=12 && time<22) packet.Unavailable="Unavailable";
                packet.InjectedFault=Case.condition=="range_spike" && time>=12 && time<18;
                if(packet.InjectedFault) packet.Range+=100;
                pending.Add(packet);
            }
            if(step%60==0)
            {
                double time=Time;
                Navigation.Filter.Altitude(Map,out double agl,out _);
                var packet=new Pending { Kind=ObservationKind.Terrain,Time=time,Ready=time+Settings.scanLatency,Sequence=scanSequence++,
                    ActualPosition=Body.position,FeatureAltitude=(float)Math.Max(0,agl),Points=new List<Vector3>() };
                for(int j=0;j<24;j++) for(int i=0;i<24;i++)
                {
                    Vector3 direction=Quaternion.Euler(Mathf.Lerp(-20,20,j/23f),0,Mathf.Lerp(-20,20,i/23f))*Vector3.down;
                    bool drop=scanRng.NextDouble()<.02; float noise=Gaussian(scanRng);
                    if(physics.Raycast(Body.position,direction,out var hit,3000,1,QueryTriggerInteraction.Ignore) && !drop)
                        packet.Points.Add(attitudeError*direction*(hit.distance+noise*(.05f+.001f*hit.distance)));
                }
                if(agl<Settings.minimumScanAltitude) packet.Unavailable="BelowScanEnvelope";
                if(Case.condition=="scan_dropout" && time>=9 && time<24) packet.Unavailable="Unavailable";
                pending.Add(packet);
            }
        }

        void Deliver()
        {
            while(true)
            {
                int index=pending.FindIndex(p=>p.Ready<=Time+1e-5); if(index<0) return;
                var packet=pending[index]; pending.RemoveAt(index);
                var log=new SensorRecord { Kind=packet.Kind,Sequence=packet.Sequence,Captured=packet.Time,Delivered=Time,InjectedFault=packet.InjectedFault,Range=packet.Range };
                if(packet.Unavailable!=null)
                {
                    log.Decision=packet.Unavailable;
                    if(packet.Kind==ObservationKind.Range) missingRanges++; else missingScans++;
                    SensorObserved?.Invoke(log); continue;
                }
                var observation=new Observation { Kind=packet.Kind,Sequence=packet.Sequence,Time=packet.Time,
                    Range=packet.Range,VarianceX=Settings.rangeNoise*Settings.rangeNoise };
                if(packet.Kind==ObservationKind.Terrain)
                {
                    if(!Navigation.At(packet.Time,out var estimate,out _))
                    { log.Decision="Stale"; scanRejected++; SensorObserved?.Invoke(log); continue; }
                    var match=LocalScanMatcher.Match(packet.Points,estimate,Map);
                    log.Points=match.points; log.Rms=match.rms; log.Confidence=match.confidence;
                    log.CorrectionX=match.correction.x; log.CorrectionZ=match.correction.y;
                    if(!TerrainFixQuality.Covariance(packet.Points,estimate,match,Map,MapSigma,packet.FeatureAltitude,out double xx,out double xz,out double zz))
                    { log.Decision="GeometryRejected"; scanRejected++; SensorObserved?.Invoke(log); continue; }
                    observation.Position=new Vector2(estimate.x,estimate.z)+match.correction;
                    observation.VarianceX=xx; observation.CovarianceXZ=xz; observation.VarianceZ=zz;
                    if(Case.arm=="ml_terminal")
                    {
                        double prediction=model!=null ? model.Predict(ScanUtilityPolicy.Features(match,packet.FeatureAltitude,previousFixOffset,hasPreviousFix)) : double.NaN;
                        if(NavigationFilter.Finite(prediction)) log.Prediction=prediction; else mlFallbacks++;
                        observation.Inflation=TerrainFixQuality.MlInflation(prediction);
                    }
                    log.FixMapError=Vector2.Distance(observation.Position,new Vector2(packet.ActualPosition.x,packet.ActualPosition.z)-MapShift);
                    previousFixOffset=match.correction; hasPreviousFix=true;
                }
                Vector3 before=Navigation.Filter.Position;
                var decision=Navigation.Deliver(observation);
                if(packet.Kind==ObservationKind.Range) { if(decision==UpdateDecision.Accepted) rangeAccepted++; else rangeRejected++; }
                else { if(decision==UpdateDecision.Accepted) scanAccepted++; else scanRejected++; }
                // Observable history follows changes to the estimate, including replayed updates.
                Vector3 delta=Navigation.Filter.Position-before;
                if(hasPreviousFix) previousFixOffset-=new Vector2(delta.x,delta.z);
                log.Decision=decision.ToString(); log.Nis=observation.Nis; log.Inflation=observation.Inflation;
                log.VarianceX=observation.VarianceX; log.VarianceZ=observation.VarianceZ; log.CovarianceXZ=observation.CovarianceXZ;
                SensorObserved?.Invoke(log);
            }
        }

        public void Step()
        {
            if(disposed) throw new ObjectDisposedException(nameof(NavigationSimulation));
            if(Finished) return;
            Acquire(); Deliver();
            float mass=1200+Fuel;
            Vector3 thrust=Fuel>0 ? Guidance.Command(Navigation.Filter,Map,Time,mass,Case.arm!="classical_pd") : Vector3.zero;
            Body.mass=mass;
            Body.AddForce(thrust+Vector3.down*(mass*LandingGuidance.Gravity),ForceMode.Force);
            // Ideal 3-DOF force sensor; attitude-error coupling, bias and noise are added here only.
            Vector3 measuredAcceleration=attitudeError*(thrust/mass)+Vector3.down*LandingGuidance.Gravity+accelerationBias+
                new Vector3(Gaussian(imuRng),Gaussian(imuRng),Gaussian(imuRng))*Settings.accelerationNoise;
            Fuel=Mathf.Max(0,Fuel-thrust.magnitude/(300*9.80665f)*Settings.dt);
            physics.Simulate(Settings.dt); Navigation.Advance(measuredAcceleration,Settings.dt); step++;
            if(!NavigationFilter.Finite(Body.position) || !NavigationFilter.Finite(Navigation.Filter.Position) || !NavigationFilter.Finite(Navigation.Filter.HorizontalSigma))
                throw new ArithmeticException("Nonfinite simulation state");
            if(touchdown.Touched) Complete("Contact");
            else if(Time>=Settings.maximumSeconds) Complete("Timeout");
            else if(Mathf.Abs(Body.position.x)>1050 || Mathf.Abs(Body.position.z)>1050) Complete("OutsideTerrain");
        }

        void Complete(string reason)
        {
            bool touched=touchdown.Touched;
            Vector3 velocity=touched ? touchdown.ContactVelocity : Body.linearVelocity;
            float vertical=Mathf.Abs(velocity.y),horizontal=new Vector2(velocity.x,velocity.z).magnitude;
            float absolute=LandingMetrics.Miss(Body.position,Vector2.zero),relative=LandingMetrics.Miss(Body.position,MapShift);
            Result=new LandingResult { id=Case.Id,site=Case.site,condition=Case.condition,arm=Case.arm,altitude=Case.altitude,seed=Case.seed,
                termination=reason,contact=touched,time=(float)Time,absoluteMiss=absolute,mapMiss=relative,impactVertical=vertical,
                impactHorizontal=horizontal,fuel=Fuel,finalX=Body.position.x,finalZ=Body.position.z,shiftX=MapShift.x,shiftZ=MapShift.y,
                rangeAccepted=rangeAccepted,rangeRejected=rangeRejected,scanAccepted=scanAccepted,scanRejected=scanRejected,
                missingRanges=missingRanges,missingScans=missingScans,mlFallbacks=mlFallbacks,
                absolute10=LandingMetrics.Success(touched,absolute,vertical,horizontal,10),absolute50=LandingMetrics.Success(touched,absolute,vertical,horizontal,50),
                absolute100=LandingMetrics.Success(touched,absolute,vertical,horizontal,100),map10=LandingMetrics.Success(touched,relative,vertical,horizontal,10),
                map50=LandingMetrics.Success(touched,relative,vertical,horizontal,50),map100=LandingMetrics.Success(touched,relative,vertical,horizontal,100) };
        }

        public void Dispose()
        {
            if(disposed) return; disposed=true; pending.Clear();
            if(scene.IsValid()) SceneManager.UnloadSceneAsync(scene);
            if(groundData!=null) UnityEngine.Object.Destroy(groundData);
            if(displayLayer!=null) UnityEngine.Object.Destroy(displayLayer);
            if(displayTexture!=null) UnityEngine.Object.Destroy(displayTexture);
        }
    }
}
