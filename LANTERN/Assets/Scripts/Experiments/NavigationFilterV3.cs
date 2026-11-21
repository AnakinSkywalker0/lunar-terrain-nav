using System;
using System.Collections.Generic;
using UnityEngine;

namespace SensorTrust.Experiments.NavigationV3
{
    [Serializable]
    public sealed class FusionSettings
    {
        public double positionSigma = 80, velocitySigma = .7, biasSigma = .01;
        public double accelerationSigma = .015, biasWalkSigma = .0001;
        public double mapHeightSigma = .5, mapCorrelationLength = 50;
        public double rangeGate = 6.634896601, terrainGate = 9.210340372;
        public double historySeconds = 1.5;
    }

    public enum ObservationKind { Range, Terrain }
    public enum UpdateDecision { Accepted, InnovationRejected, Invalid, OutsideMap, Stale, Duplicate, Future }

    public sealed class Observation
    {
        public ObservationKind Kind;
        public int Sequence;
        public double Time, Range, VarianceX, CovarianceXZ, VarianceZ, Inflation = 1;
        public Vector2 Position;
        public UpdateDecision Decision;
        public double Nis = -1;

        internal Observation Copy() => new Observation { Kind=Kind,Sequence=Sequence,Time=Time,Range=Range,
            VarianceX=VarianceX,CovarianceXZ=CovarianceXZ,VarianceZ=VarianceZ,Inflation=Inflation,Position=Position };
    }

    /// <summary>Position, velocity, acceleration bias and local map-height bias. No truth references.</summary>
    public sealed class NavigationFilter
    {
        public const int Size = 10;
        readonly FusionSettings settings;
        readonly double[] state = new double[Size];
        double[,] covariance = new double[Size, Size];
        public double LastRangeTime { get; private set; } = -1;
        public double LastTerrainTime { get; private set; } = -1;
        public Vector3 Position => new Vector3((float)state[0], (float)state[1], (float)state[2]);
        public Vector3 Velocity => new Vector3((float)state[3], (float)state[4], (float)state[5]);
        public Vector3 Bias => new Vector3((float)state[6], (float)state[7], (float)state[8]);
        public double MapHeightBias => state[9];
        public double HorizontalSigma => Math.Sqrt(covariance[0, 0] + covariance[2, 2]);
        public double Variance(int i, int j) => covariance[i, j];
        public static bool Finite(double x) => !double.IsNaN(x) && !double.IsInfinity(x);
        public static bool Finite(Vector3 x) => Finite(x.x) && Finite(x.y) && Finite(x.z);

        public NavigationFilter(Vector3 position, Vector3 velocity, FusionSettings settings, double? initialMapSigma = null)
        {
            if (!Finite(position) || !Finite(velocity) || settings == null ||
                !Positive(settings.positionSigma) || !Positive(settings.velocitySigma) || !Positive(settings.biasSigma) ||
                !Positive(settings.accelerationSigma) || !Positive(settings.biasWalkSigma) ||
                !Positive(settings.mapHeightSigma) || !Positive(settings.mapCorrelationLength) ||
                !Positive(settings.rangeGate) || !Positive(settings.terrainGate) || !Positive(settings.historySeconds))
                throw new ArgumentException("Invalid navigation initialization/settings");
            this.settings = settings;
            for (int a = 0; a < 3; a++)
            {
                state[a] = position[a]; state[a+3] = velocity[a];
                covariance[a,a] = settings.positionSigma * settings.positionSigma;
                covariance[a+3,a+3] = settings.velocitySigma * settings.velocitySigma;
                covariance[a+6,a+6] = settings.biasSigma * settings.biasSigma;
            }
            double mapSigma=initialMapSigma ?? settings.mapHeightSigma;
            if(!Finite(mapSigma) || mapSigma<0) throw new ArgumentException("Invalid map-height uncertainty");
            covariance[9,9]=Math.Max(1e-6,mapSigma*mapSigma);
        }
        static bool Positive(double x) => Finite(x) && x > 0;

        public sealed class Snapshot
        {
            internal double[] State;
            internal double[,] Covariance;
            internal double RangeTime, TerrainTime;
            public double Component(int index) => State[index];
            public double Variance(int row, int column) => Covariance[row,column];
        }
        public Snapshot Save() => new Snapshot { State = (double[])state.Clone(), Covariance = (double[,])covariance.Clone(),
            RangeTime = LastRangeTime, TerrainTime = LastTerrainTime };
        public void Restore(Snapshot saved)
        {
            Array.Copy(saved.State, state, Size); covariance = (double[,])saved.Covariance.Clone();
            LastRangeTime = saved.RangeTime; LastTerrainTime = saved.TerrainTime;
        }

        public void Predict(Vector3 measuredAcceleration, double dt)
        {
            if (!Finite(measuredAcceleration) || !Positive(dt) || dt > .25) throw new ArgumentException("Invalid IMU step");
            double half = .5 * dt * dt;
            for (int a = 0; a < 3; a++)
            {
                double acceleration = measuredAcceleration[a] - state[a+6];
                state[a] += dt * state[a+3] + half * acceleration;
                state[a+3] += dt * acceleration;
            }
            // Sparse F*P*F': F[p,v]=dt, F[p,b]=-dt²/2, F[v,b]=-dt.
            var left = new double[Size,Size]; var next = new double[Size,Size];
            for (int i = 0; i < Size; i++) for (int j = 0; j < Size; j++)
                left[i,j] = covariance[i,j] + (i < 3 ? dt*covariance[i+3,j]-half*covariance[i+6,j] :
                    i < 6 ? -dt*covariance[i+3,j] : 0);
            for (int i = 0; i < Size; i++) for (int j = 0; j < Size; j++)
                next[i,j] = left[i,j] + (j < 3 ? dt*left[i,j+3]-half*left[i,j+6] : j < 6 ? -dt*left[i,j+3] : 0);
            double q = settings.accelerationSigma * settings.accelerationSigma;
            for (int a = 0; a < 3; a++)
            {
                next[a,a] += q*half*half; next[a,a+3] += q*half*dt; next[a+3,a] += q*half*dt;
                next[a+3,a+3] += q*dt*dt;
                next[a+6,a+6] += settings.biasWalkSigma*settings.biasWalkSigma*dt;
            }
            // Shared map error must not become independent white noise at each altimeter tick.
            // A local bias random walk accounts approximately for moving across correlated errors.
            double distance=Math.Sqrt(state[3]*state[3]+state[5]*state[5])*dt;
            next[9,9]+=2*settings.mapHeightSigma*settings.mapHeightSigma*distance/settings.mapCorrelationLength;
            covariance = next;
        }

        public static bool TerrainGeometry(ElevationMap map, Vector3 p, out float height, out Vector2 gradient)
        {
            gradient = Vector2.zero; height = 0;
            if (map == null || !Finite(p)) return false;
            float step = map.spacing;
            if (!map.Sample(p.x,p.z,out height) || !map.Sample(p.x-step,p.z,out float xm) ||
                !map.Sample(p.x+step,p.z,out float xp) || !map.Sample(p.x,p.z-step,out float zm) ||
                !map.Sample(p.x,p.z+step,out float zp)) return false;
            gradient = new Vector2((xp-xm)/(2*step),(zp-zm)/(2*step));
            return Finite(height) && Finite(gradient.x) && Finite(gradient.y);
        }

        public bool Altitude(ElevationMap map, out double agl, out double sigma)
        {
            agl = 0; sigma = double.PositiveInfinity;
            if (!TerrainGeometry(map,Position,out float height,out var g)) return false;
            agl = state[1]-height-state[9];
            double[] h = {-g.x,1,-g.y,0,0,0,0,0,0,-1}; double variance = 0;
            for (int i=0;i<Size;i++) for (int j=0;j<Size;j++) variance += h[i]*covariance[i,j]*h[j];
            sigma = Math.Sqrt(Math.Max(0,variance)); return Finite(agl) && Finite(sigma);
        }

        public UpdateDecision Observe(Observation observation, ElevationMap map, ElevationMap mapSigma)
        {
            observation.Nis = -1;
            if ((observation.Kind!=ObservationKind.Range && observation.Kind!=ObservationKind.Terrain) ||
                !Finite(observation.Time) || !Positive(observation.VarianceX) || !Finite(observation.Inflation) || observation.Inflation < 1 || observation.Inflation > 4)
                return observation.Decision = UpdateDecision.Invalid;
            int count = observation.Kind == ObservationKind.Range ? 1 : 2;
            var h = new double[count,Size]; var residual = new double[count]; var r = new double[count,count];
            if (observation.Kind == ObservationKind.Range)
            {
                if (!Finite(observation.Range) || observation.Range < 0) return observation.Decision = UpdateDecision.Invalid;
                if (!TerrainGeometry(map,Position,out float height,out var g) || mapSigma == null ||
                    !mapSigma.Sample(Position.x,Position.z,out float sigma) || !Finite(sigma) || sigma < 0)
                    return observation.Decision = UpdateDecision.OutsideMap;
                h[0,0] = -g.x; h[0,1] = 1; h[0,2] = -g.y; h[0,9] = -1;
                residual[0] = observation.Range - (state[1]-height-state[9]);
                r[0,0] = observation.VarianceX;
            }
            else
            {
                if (!Finite(observation.Position.x) || !Finite(observation.Position.y) || !Positive(observation.VarianceZ) ||
                    !Finite(observation.CovarianceXZ) || observation.VarianceX*observation.VarianceZ <= observation.CovarianceXZ*observation.CovarianceXZ)
                    return observation.Decision = UpdateDecision.Invalid;
                h[0,0] = 1; h[1,2] = 1;
                residual[0] = observation.Position.x-state[0]; residual[1] = observation.Position.y-state[2];
                r[0,0] = observation.VarianceX; r[1,1] = observation.VarianceZ;
                r[0,1] = r[1,0] = observation.CovarianceXZ;
            }
            var ph = new double[Size,count];
            for (int i=0;i<Size;i++) for (int j=0;j<count;j++) for (int k=0;k<Size;k++) ph[i,j] += covariance[i,k]*h[j,k];
            var s = new double[count,count];
            for (int i=0;i<count;i++) for (int j=0;j<count;j++)
            { s[i,j] = r[i,j]; for (int k=0;k<Size;k++) s[i,j] += h[i,k]*ph[k,j]; }
            if (!Invert(s,out var inverse)) return observation.Decision = UpdateDecision.Invalid;
            double nis = 0;
            for (int i=0;i<count;i++) for (int j=0;j<count;j++) nis += residual[i]*inverse[i,j]*residual[j];
            observation.Nis = nis;
            // Gate with classical R first. ML may never turn a rejected reading into an accepted reading.
            if (!Finite(nis) || nis > (count==1 ? settings.rangeGate : settings.terrainGate))
                return observation.Decision = UpdateDecision.InnovationRejected;
            if (count==2 && observation.Inflation > 1)
            {
                for (int i=0;i<count;i++) for (int j=0;j<count;j++)
                { s[i,j] += (observation.Inflation-1)*r[i,j]; r[i,j] *= observation.Inflation; }
                if (!Invert(s,out inverse)) return observation.Decision = UpdateDecision.Invalid;
            }
            var gain = new double[Size,count];
            for (int i=0;i<Size;i++) for (int j=0;j<count;j++) for (int k=0;k<count;k++) gain[i,j] += ph[i,k]*inverse[k,j];
            for (int i=0;i<Size;i++) for (int j=0;j<count;j++) state[i] += gain[i,j]*residual[j];
            // Joseph update, retaining cross-axis/velocity/bias covariance.
            var a = new double[Size,Size]; var ap = new double[Size,Size]; var next = new double[Size,Size];
            for (int i=0;i<Size;i++) for (int j=0;j<Size;j++)
            { a[i,j] = i==j ? 1 : 0; for (int k=0;k<count;k++) a[i,j] -= gain[i,k]*h[k,j]; }
            for (int i=0;i<Size;i++) for (int j=0;j<Size;j++) for (int k=0;k<Size;k++) ap[i,j] += a[i,k]*covariance[k,j];
            for (int i=0;i<Size;i++) for (int j=0;j<Size;j++)
            {
                for (int k=0;k<Size;k++) next[i,j] += ap[i,k]*a[j,k];
                for (int k=0;k<count;k++) for (int l=0;l<count;l++) next[i,j] += gain[i,k]*r[k,l]*gain[j,l];
            }
            for (int i=0;i<Size;i++) for (int j=0;j<Size;j++) covariance[i,j] = .5*(next[i,j]+next[j,i]);
            if (count==1) LastRangeTime = observation.Time; else LastTerrainTime = observation.Time;
            return observation.Decision = UpdateDecision.Accepted;
        }

        static bool Invert(double[,] matrix, out double[,] inverse)
        {
            int n = matrix.GetLength(0); inverse = new double[n,n];
            if (n==1) { if (!Positive(matrix[0,0])) return false; inverse[0,0]=1/matrix[0,0]; return true; }
            double determinant = matrix[0,0]*matrix[1,1]-matrix[0,1]*matrix[1,0];
            if (!Positive(determinant)) return false;
            inverse[0,0]=matrix[1,1]/determinant; inverse[1,1]=matrix[0,0]/determinant;
            inverse[0,1]=-matrix[0,1]/determinant; inverse[1,0]=-matrix[1,0]/determinant; return true;
        }
    }

    /// <summary>Replay IMU and accepted/rejected observations in measurement-time order.</summary>
    public sealed class DelayedNavigation
    {
        sealed class Frame
        {
            public double Time, Dt;
            public Vector3 Acceleration;
            public NavigationFilter.Snapshot Before, After;
            public readonly List<Observation> Observations = new List<Observation>();
        }
        readonly List<Frame> frames = new List<Frame>();
        readonly ElevationMap map, sigma;
        readonly double history;
        public NavigationFilter Filter { get; }
        public double Time => frames[frames.Count-1].Time;

        public DelayedNavigation(Vector3 p, Vector3 v, FusionSettings settings, ElevationMap map, ElevationMap sigma)
        {
            double? initialSigma=sigma!=null && sigma.Sample(p.x,p.z,out float error) ? (double?)error : null;
            Filter = new NavigationFilter(p,v,settings,initialSigma); this.map=map; this.sigma=sigma; history=settings.historySeconds;
            frames.Add(new Frame { Time=0, Before=Filter.Save(), After=Filter.Save() });
        }
        public void Advance(Vector3 acceleration, double dt)
        {
            double time = Time+dt; Filter.Predict(acceleration,dt);
            frames.Add(new Frame { Time=time,Dt=dt,Acceleration=acceleration,Before=Filter.Save(),After=Filter.Save() });
            while (frames.Count>1 && time-frames[0].Time>history) frames.RemoveAt(0);
        }
        public bool At(double time, out Vector3 position, out Vector3 velocity)
        {
            var frame = frames.Find(f=>Math.Abs(f.Time-time)<1e-5);
            position=velocity=Vector3.zero;
            if (frame==null) return false;
            var x=frame.After.State;
            position=new Vector3((float)x[0],(float)x[1],(float)x[2]);
            velocity=new Vector3((float)x[3],(float)x[4],(float)x[5]); return true;
        }
        public UpdateDecision Deliver(Observation observation)
        {
            if (observation==null) throw new ArgumentNullException(nameof(observation));
            if (!NavigationFilter.Finite(observation.Time) || observation.Sequence<0) return observation.Decision=UpdateDecision.Invalid;
            if (observation.Time>Time+1e-5) return observation.Decision=UpdateDecision.Future;
            int index=frames.FindIndex(f=>Math.Abs(f.Time-observation.Time)<1e-5);
            if (index<0) return observation.Decision=UpdateDecision.Stale;
            foreach (var frame in frames) foreach (var existing in frame.Observations)
                if (existing.Kind==observation.Kind && existing.Sequence==observation.Sequence) return observation.Decision=UpdateDecision.Duplicate;
            // Own the replay input. A caller may reuse/mutate its packet after delivery;
            // that must never rewrite a historical measurement in the filter.
            var stored=observation.Copy();
            frames[index].Observations.Add(stored);
            frames[index].Observations.Sort((a,b)=>a.Kind!=b.Kind ? a.Kind.CompareTo(b.Kind) : a.Sequence.CompareTo(b.Sequence));
            Filter.Restore(frames[index].Before);
            for (int i=index;i<frames.Count;i++)
            {
                var frame=frames[i];
                if (i>index) { Filter.Predict(frame.Acceleration,frame.Dt); frame.Before=Filter.Save(); }
                foreach (var update in frame.Observations) Filter.Observe(update,map,sigma);
                frame.After=Filter.Save();
            }
            observation.Nis=stored.Nis;
            return observation.Decision=stored.Decision;
        }
    }
}
