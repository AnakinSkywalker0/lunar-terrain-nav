using System;
using System.Collections.Generic;
using UnityEngine;

namespace SensorTrust.Experiments
{
    // This module has no access to a Rigidbody, true pose, TerrainCollider or scene.
    public sealed class ElevationMap
    {
        public readonly float[,] heights;
        public readonly Vector2 origin;
        public readonly float spacing;
        public ElevationMap(float[,] h, Vector2 o, float s) { heights=h; origin=o; spacing=s; }
        public bool Sample(float x, float z, out float height)
        {
            float u=(x-origin.x)/spacing, v=(z-origin.y)/spacing;
            int i=Mathf.FloorToInt(u), j=Mathf.FloorToInt(v);
            if(i<0 || j<0 || i>=heights.GetLength(1)-1 || j>=heights.GetLength(0)-1)
            { height=0; return false; }
            height=Mathf.Lerp(Mathf.Lerp(heights[j,i],heights[j,i+1],u-i),
                Mathf.Lerp(heights[j+1,i],heights[j+1,i+1],u-i),v-j);
            return true;
        }
    }

    public struct ScanMatch
    {
        public bool valid, accepted;
        public Vector2 correction;
        public float rms, confidence;
        public int points;
        public double milliseconds;
    }

    public static class LocalScanMatcher
    {
        static float Cost(List<Vector3> points, Vector3 estimate, ElevationMap map, float dx, float dz)
        {
            double sum=0, sq=0; int n=0;
            // Deterministic downsampling; no use of true pose or error in fitting.
            int stride=Mathf.Max(1,points.Count/144);
            for(int k=0;k<points.Count;k+=stride)
            {
                Vector3 p=estimate+points[k];
                if(!map.Sample(p.x+dx,p.z+dz,out float h)) return float.PositiveInfinity;
                double d=p.y-h; sum+=d; sq+=d*d; n++;
            }
            return n>0 ? (float)Math.Max(0,sq/n-(sum/n)*(sum/n)) : float.PositiveInfinity;
        }
        public static ScanMatch Match(List<Vector3> localPoints, Vector3 estimate, ElevationMap map)
        {
            var watch=System.Diagnostics.Stopwatch.StartNew();
            var r=new ScanMatch { points=localPoints.Count };
            if(localPoints.Count<80) { r.milliseconds=watch.Elapsed.TotalMilliseconds; return r; }
            float best=float.PositiveInfinity; Vector2 shift=Vector2.zero;
            var scores=new List<Vector3>();
            for(int z=-128;z<=128;z+=16) for(int x=-128;x<=128;x+=16)
            {
                float c=Cost(localPoints,estimate,map,x,z);
                scores.Add(new Vector3(x,z,c));
                if(c<best) { best=c; shift=new Vector2(x,z); }
            }
            if(float.IsInfinity(best)) { r.milliseconds=watch.Elapsed.TotalMilliseconds; return r; }
            bool boundary=Mathf.Abs(shift.x)>=128 || Mathf.Abs(shift.y)>=128;
            foreach(int step in new[]{4,1})
            {
                Vector2 center=shift;
                for(int j=-3;j<=3;j++) for(int i=-3;i<=3;i++)
                {
                    Vector2 candidate=center+new Vector2(i,j)*step;
                    float c=Cost(localPoints,estimate,map,candidate.x,candidate.y);
                    if(c<best) { best=c; shift=candidate; }
                }
            }
            double far=0; int count=0;
            foreach(var s in scores) if(!float.IsInfinity(s.z) && Vector2.Distance(new Vector2(s.x,s.y),shift)>32)
            { far+=s.z; count++; }
            r.valid=true; r.correction=shift; r.rms=Mathf.Sqrt(best);
            r.confidence=count>0 ? Mathf.Clamp01(1-(best+.01f)/((float)(far/count)+.01f)) : 0;
            r.accepted=!boundary && r.rms<=8 && r.confidence>=.35f;
            r.milliseconds=watch.Elapsed.TotalMilliseconds;
            return r;
        }
    }

    public sealed class NavigationEstimate
    {
        public Vector3 position, velocity;
        public NavigationEstimate(Vector3 p, Vector3 v) { position=p; velocity=v; }
        public void Predict(Vector3 measuredAcceleration, float dt)
        { position+=velocity*dt+.5f*measuredAcceleration*dt*dt; velocity+=measuredAcceleration*dt; }
        public void ObserveAltitude(float range, ElevationMap map)
        { if(map.Sample(position.x,position.z,out float h)) position.y=h+range; }
        public void Correct(ScanMatch match)
        { if(match.accepted) position+=new Vector3(match.correction.x,0,match.correction.y); }
    }

    public static class EstimateGuidance
    {
        // Inputs are estimated state and measured altitude, never ground truth.
        public static Vector3 Thrust(NavigationEstimate nav, float measuredAgl, float mass)
        {
            float vy=-Mathf.Min(30,.5f+Mathf.Sqrt(2*.45f*Mathf.Max(0,measuredAgl-.5f)));
            float ay=Mathf.Max(0,1.62f+.8f*(vy-nav.velocity.y));
            Vector2 horizontal=new Vector2(-.04f*nav.position.x-.5f*nav.velocity.x,
                -.04f*nav.position.z-.5f*nav.velocity.z);
            horizontal=Vector2.ClampMagnitude(horizontal,ay*Mathf.Tan(10*Mathf.Deg2Rad));
            return Vector3.ClampMagnitude(new Vector3(horizontal.x,ay,horizontal.y)*mass,6000);
        }
    }
}
