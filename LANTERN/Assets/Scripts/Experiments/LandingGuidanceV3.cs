using System;
using System.Collections.Generic;
using UnityEngine;

namespace SensorTrust.Experiments.NavigationV3
{
    public static class TerrainFixQuality
    {
        // Local least-squares curvature proxy, NOT a calibrated full matching posterior.
        // Mean-removing gradients matches the legacy matcher's unknown vertical offset.
        public static bool Covariance(List<Vector3> points, Vector3 estimate, ScanMatch match,
            ElevationMap map, ElevationMap sigmaMap, float agl, out double xx, out double xz, out double zz)
        {
            xx=xz=zz=0;
            if (!match.valid || !match.accepted || points.Count<80 || !NavigationFilter.Finite(match.rms)) return false;
            double sx=0,sz=0,sxx=0,sxz=0,szz=0,sigma2=0; int n=0;
            Vector3 corrected=estimate+new Vector3(match.correction.x,0,match.correction.y);
            for (int i=0;i<points.Count;i+=Math.Max(1,points.Count/144))
            {
                Vector3 p=corrected+points[i];
                if (!NavigationFilter.TerrainGeometry(map,p,out _,out var g) || !sigmaMap.Sample(p.x,p.z,out float sigma)) return false;
                sx+=g.x; sz+=g.y; sxx+=g.x*g.x; sxz+=g.x*g.y; szz+=g.y*g.y; sigma2+=sigma*sigma; n++;
            }
            double a=sxx/n-(sx/n)*(sx/n), b=sxz/n-sx*sz/(n*n), c=szz/n-(sz/n)*(sz/n);
            double determinant=a*c-b*b, trace=a+c;
            if (determinant<=1e-10 || trace*trace/determinant>1e4) return false;
            double noise=Math.Max(match.rms*match.rms,Math.Pow(.05+.001*Math.Max(0,agl),2)+sigma2/n);
            // Cap effective independent support because both DEM and scan samples are correlated.
            double scale=noise/Math.Min(n,16);
            double floor=1+Math.Pow(Math.Max(0,agl)*Math.Tan(.02*Math.PI/180),2);
            xx=scale*c/determinant+floor; xz=-scale*b/determinant; zz=scale*a/determinant+floor;
            return NavigationFilter.Finite(xx) && NavigationFilter.Finite(zz);
        }
        public static double MlInflation(double prediction) => NavigationFilter.Finite(prediction)
            ? 1+3*(1-Math.Max(0,Math.Min(1,prediction))) : 1;
    }

    public enum GuidanceMode { Approach, TerminalBrake, DegradedBrake }

    public sealed class LandingGuidance
    {
        public const float Gravity=1.62f, MaximumThrust=6000, TiltDegrees=10;
        public bool TerminalLatched { get; private set; }
        public GuidanceMode Mode { get; private set; }
        public bool Saturated { get; private set; }
        public Vector3 Command(NavigationFilter nav, ElevationMap map, double time, float mass, bool terminalController)
        {
            if (!NavigationFilter.Finite(mass) || mass<=0) throw new ArgumentException("Invalid vehicle mass");
            bool geometry=nav.Altitude(map,out double agl,out double sigma);
            bool stale=nav.LastRangeTime<0 || time-nav.LastRangeTime>2;
            bool degraded=!geometry || stale || sigma>15;
            float height=geometry ? (float)Math.Max(0,agl) : 0;
            float conservativeHeight=geometry ? (float)Math.Max(0,agl-3*sigma) : 0;
            float timeToGo=2*conservativeHeight/Mathf.Max(.6f,-nav.Velocity.y+.6f);
            if (terminalController && (conservativeHeight<25 || timeToGo<8)) TerminalLatched=true;
            Mode=degraded ? GuidanceMode.DegradedBrake : TerminalLatched ? GuidanceMode.TerminalBrake : GuidanceMode.Approach;
            // Enter the final 3 m at the terminal speed rather than chasing a curve
            // that reaches its terminal value only at contact (finite control response).
            float verticalTarget=-Mathf.Min(20,Mathf.Max(.6f,Mathf.Sqrt(2*.35f*Mathf.Max(0,height-3))));
            if (degraded) verticalTarget=geometry ? -Mathf.Min(2,Mathf.Max(.3f,conservativeHeight*.1f)) : 0;
            float ay=Mathf.Clamp(Gravity+.8f*(verticalTarget-nav.Velocity.y),0,MaximumThrust/mass);
            Vector2 position=new Vector2(nav.Position.x,nav.Position.z), velocity=new Vector2(nav.Velocity.x,nav.Velocity.z);
            Vector2 horizontal;
            if (!terminalController && !degraded) horizontal=-.04f*position-.5f*velocity;
            else
            {
                Vector2 targetVelocity=Vector2.zero;
                bool localized=nav.LastTerrainTime>=0 && time-nav.LastTerrainTime<20 && nav.HorizontalSigma<40;
                if (!TerminalLatched && !degraded && localized)
                {
                    const float brakingAcceleration=.18f;
                    float speed=Mathf.Min(8,.18f*position.magnitude,Mathf.Sqrt(2*brakingAcceleration*position.magnitude),
                        .6f*brakingAcceleration*Mathf.Max(0,timeToGo-4));
                    targetVelocity=-position.normalized*speed;
                }
                horizontal=(targetVelocity-velocity)/2;
            }
            float authority=ay*Mathf.Tan(TiltDegrees*Mathf.Deg2Rad);
            Saturated=horizontal.magnitude>authority+1e-6f;
            horizontal=Vector2.ClampMagnitude(horizontal,authority);
            return Vector3.ClampMagnitude(new Vector3(horizontal.x,ay,horizontal.y)*mass,MaximumThrust);
        }
    }

    public static class LandingMetrics
    {
        public static bool Success(bool contact, float miss, float verticalSpeed, float horizontalSpeed, float threshold)
            => contact && NavigationFilter.Finite(miss) && NavigationFilter.Finite(verticalSpeed) && NavigationFilter.Finite(horizontalSpeed)
                && miss>=0 && Math.Abs(verticalSpeed)<2 && horizontalSpeed>=0 && horizontalSpeed<1 && miss<threshold;
        public static float Miss(Vector3 actualPosition, Vector2 mapShift)
            => Vector2.Distance(new Vector2(actualPosition.x,actualPosition.z),mapShift);
    }
}
