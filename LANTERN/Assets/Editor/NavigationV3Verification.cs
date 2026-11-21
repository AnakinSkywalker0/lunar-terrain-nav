using System;
using System.Collections.Generic;
using UnityEngine;
using SensorTrust.Experiments;
using SensorTrust.Experiments.NavigationV3;

namespace SensorTrust.Editor
{
    public static class NavigationV3Verification
    {
        [Serializable] public sealed class Report { public bool passed; public string[] checks; }
        static void Require(bool condition,string message) { if(!condition) throw new Exception("Navigation v3 contract: "+message); }
        static void Close(double actual,double expected,double tolerance,string message)
            => Require(Math.Abs(actual-expected)<=tolerance,message+" actual="+actual+" expected="+expected);
        static ElevationMap Flat(float value=0)
        {
            var h=new float[101,101];
            for(int j=0;j<101;j++) for(int i=0;i<101;i++) h[j,i]=value;
            return new ElevationMap(h,new Vector2(-500,-500),10);
        }
        static Observation Fix(int sequence,double time,float x,float z,double variance=1,double inflation=1)
            => new Observation { Kind=ObservationKind.Terrain,Sequence=sequence,Time=time,Position=new Vector2(x,z),
                VarianceX=variance,VarianceZ=variance,Inflation=inflation };
        static void PositiveDefinite(NavigationFilter nav)
        {
            var l=new double[NavigationFilter.Size,NavigationFilter.Size];
            for(int i=0;i<NavigationFilter.Size;i++) for(int j=0;j<=i;j++)
            {
                Close(nav.Variance(i,j),nav.Variance(j,i),1e-8,"symmetric covariance");
                double value=nav.Variance(i,j);
                for(int k=0;k<j;k++) value-=l[i,k]*l[j,k];
                if(i==j) { Require(value>0 && NavigationFilter.Finite(value),"positive definite covariance"); l[i,j]=Math.Sqrt(value); }
                else l[i,j]=value/l[j,j];
            }
        }
        public static Report Run()
        {
            var checks=new List<string>(); var map=Flat(); var sigma=Flat(.4f);
            var settings=new FusionSettings { positionSigma=2,terrainGate=1000 };
            var filter=new NavigationFilter(new Vector3(0,100,0),Vector3.zero,settings);
            var accepted=Fix(0,0,10,0);
            Require(filter.Observe(accepted,map,sigma)==UpdateDecision.Accepted,"known position update accepted");
            Close(filter.Position.x,8,1e-6,"Kalman mean"); Close(filter.Variance(0,0),.8,1e-10,"Kalman variance");
            checks.Add("Analytical Kalman mean and covariance");
            var before=filter.Save(); var invalid=Fix(1,0,float.NaN,0);
            Require(filter.Observe(invalid,map,sigma)==UpdateDecision.Invalid,"NaN rejected");
            Close(filter.Position.x,before.Component(0),1e-9,"NaN cannot mutate state");
            invalid=Fix(1,0,0,0,-1); Require(filter.Observe(invalid,map,sigma)==UpdateDecision.Invalid,"negative R rejected");
            invalid=Fix(1,0,0,0); invalid.CovarianceXZ=2;
            Require(filter.Observe(invalid,map,sigma)==UpdateDecision.Invalid,"indefinite R rejected");
            invalid=Fix(1,0,0,0,1,.5); Require(filter.Observe(invalid,map,sigma)==UpdateDecision.Invalid,"ML cannot deflate covariance");
            checks.Add("Nonfinite/negative/indefinite observation guards");
            settings=new FusionSettings { positionSigma=1 };
            var plain=new NavigationFilter(new Vector3(0,100,0),Vector3.zero,settings);
            var ml=new NavigationFilter(new Vector3(0,100,0),Vector3.zero,settings);
            Require(plain.Observe(Fix(0,0,100,0),map,sigma)==UpdateDecision.InnovationRejected,"classical outlier rejected");
            Require(ml.Observe(Fix(0,0,100,0,1,4),map,sigma)==UpdateDecision.InnovationRejected,"ML cannot rescue outlier");
            Close(plain.Position.x,0,0,"outlier mean unchanged"); Close(plain.Variance(0,0),1,0,"outlier covariance unchanged");
            plain.Observe(Fix(1,0,1,0),map,sigma); ml.Observe(Fix(1,0,1,0,1,4),map,sigma);
            Require(ml.Position.x<plain.Position.x && ml.Variance(0,0)>plain.Variance(0,0),"ML only reduces influence");
            Close(TerrainFixQuality.MlInflation(double.NaN),1,0,"missing ML falls back to classical");
            checks.Add("Innovation gate precedes bounded optional ML; rejection is nonmutating");

            var timely=new DelayedNavigation(new Vector3(0,100,0),new Vector3(1,0,0),new FusionSettings(),map,sigma);
            var delayed=new DelayedNavigation(new Vector3(0,100,0),new Vector3(1,0,0),new FusionSettings(),map,sigma);
            for(int i=1;i<=12;i++)
            {
                var acceleration=new Vector3(.1f,0,-.05f); timely.Advance(acceleration,.05); delayed.Advance(acceleration,.05);
                if(i==2) timely.Deliver(Fix(0,.1,1,2));
                if(i==4)
                {
                    timely.Deliver(new Observation { Kind=ObservationKind.Range,Sequence=0,Time=.2,Range=100.2,VarianceX=.01 });
                    delayed.Deliver(new Observation { Kind=ObservationKind.Range,Sequence=0,Time=.2,Range=100.2,VarianceX=.01 });
                }
                if(i==8) Require(delayed.Deliver(Fix(0,.1,1,2))==UpdateDecision.Accepted,"late fix accepted");
            }
            var a=timely.Filter.Save(); var b=delayed.Filter.Save();
            for(int i=0;i<NavigationFilter.Size;i++)
            { Close(a.Component(i),b.Component(i),1e-9,"delayed mean equivalence"); for(int j=0;j<NavigationFilter.Size;j++) Close(a.Variance(i,j),b.Variance(i,j),1e-9,"delayed covariance equivalence"); }
            checks.Add("Out-of-order range/terrain delivery equals chronological replay");
            Require(delayed.Deliver(Fix(0,.1,1,2))==UpdateDecision.Duplicate,"duplicate rejected");
            Require(delayed.Deliver(Fix(9,2,1,2))==UpdateDecision.Future,"future rejected");
            Require(delayed.Deliver(Fix(9,-1,1,2))==UpdateDecision.Stale,"stale rejected");
            Require(delayed.Deliver(Fix(9,double.NaN,1,2))==UpdateDecision.Invalid,"invalid time rejected");
            for(int i=0;i<NavigationFilter.Size;i++) Close(delayed.Filter.Save().Component(i),b.Component(i),1e-9,"delivery guard cannot mutate");
            checks.Add("Duplicate/stale/future/invalid timestamps do not mutate state");
            for(int i=0;i<50;i++) delayed.Advance(Vector3.zero,.05);
            Require(delayed.Deliver(Fix(1,.1,1,2))==UpdateDecision.Stale,"history expires");
            checks.Add("Fixed-lag history has bounded lifetime");
            var owned=new DelayedNavigation(new Vector3(0,100,0),Vector3.zero,new FusionSettings(),map,sigma);
            var control=new DelayedNavigation(new Vector3(0,100,0),Vector3.zero,new FusionSettings(),map,sigma);
            var packet=Fix(0,0,1,2); owned.Deliver(packet); control.Deliver(Fix(0,0,1,2));
            packet.Position=new Vector2(1000,1000); packet.VarianceX=1e-6;
            var range=new Observation { Kind=ObservationKind.Range,Sequence=0,Time=0,Range=100,VarianceX=.01 };
            owned.Deliver(range);
            control.Deliver(new Observation { Kind=ObservationKind.Range,Sequence=0,Time=0,Range=100,VarianceX=.01 });
            for(int i=0;i<NavigationFilter.Size;i++) Close(owned.Filter.Save().Component(i),control.Filter.Save().Component(i),1e-9,"caller mutation cannot change replay history");
            checks.Add("Delayed replay owns immutable copies of caller measurements");

            var slope=new float[101,101];
            for(int j=0;j<101;j++) for(int i=0;i<101;i++) slope[j,i]=.1f*(-500+i*10);
            var slopeMap=new ElevationMap(slope,new Vector2(-500,-500),10);
            filter=new NavigationFilter(new Vector3(10,101,0),Vector3.zero,new FusionSettings());
            filter.Altitude(slopeMap,out double altitude,out _); Close(altitude,100,1e-6,"terrain-relative altitude");
            Require(filter.Observe(new Observation { Kind=ObservationKind.Range,Time=0,Range=100,VarianceX=.01 },slopeMap,sigma)==UpdateDecision.Accepted,"range geometry");
            Require(filter.Variance(0,1)>0,"range update retains terrain-gradient cross covariance");
            Require(filter.Observe(new Observation { Kind=ObservationKind.Range,Time=0,Range=-1,VarianceX=.01 },map,sigma)==UpdateDecision.Invalid,"negative range rejected");
            checks.Add("Terrain-gradient altitude fusion and cross-axis covariance");
            var outside=new NavigationFilter(new Vector3(1000,100,0),Vector3.zero,new FusionSettings());
            Require(!outside.Altitude(map,out _,out _),"unknown altitude outside map");
            Require(outside.Observe(new Observation { Kind=ObservationKind.Range,Time=0,Range=100,VarianceX=.01 },map,sigma)==UpdateDecision.OutsideMap,"outside-map update rejected");
            var unknownGuidance=new LandingGuidance(); var unknownThrust=unknownGuidance.Command(outside,map,0,2000,true);
            Require(unknownGuidance.Mode==GuidanceMode.DegradedBrake && NavigationFilter.Finite(unknownThrust),"unknown altitude has finite degraded control");
            checks.Add("Unknown/out-of-map altitude remains explicit with finite fallback control");
            filter=new NavigationFilter(new Vector3(0,100,0),Vector3.zero,new FusionSettings { positionSigma=2 });
            for(int i=0;i<100;i++) filter.Observe(new Observation { Kind=ObservationKind.Range,Time=i*.1,Range=100,VarianceX=.01 },map,sigma);
            Require(filter.Variance(1,1)>.2,"repeated readings cannot average away shared map-height error");
            checks.Add("Persistent map-height error is not counted as independent range noise");
            filter=new NavigationFilter(new Vector3(0,100,0),Vector3.zero,new FusionSettings { biasSigma=.1 });
            for(int i=1;i<=1000;i++)
            {
                filter.Predict(new Vector3(.02f,0,0),.05);
                if(i%10==0) filter.Observe(Fix(i,i*.05,0,0,.01),map,sigma);
                if(i%100==0) PositiveDefinite(filter);
            }
            Close(filter.Bias.x,.02,.003,"constant accelerometer bias estimation");
            checks.Add("Bias observability under repeated fixes; covariance remains positive definite");

            var points=new List<Vector3>();
            for(int j=-5;j<=5;j++) for(int i=-5;i<=5;i++) points.Add(new Vector3(i*10,-200,j*10));
            var match=LocalScanMatcher.Match(points,new Vector3(0,200,0),map);
            Require(!match.accepted,"flat terrain cannot localize");
            Require(!TerrainFixQuality.Covariance(points,new Vector3(0,200,0),match,map,sigma,200,out _,out _,out _),"flat geometry rejected");
            checks.Add("Flat terrain provides no confident horizontal fix");
            filter=new NavigationFilter(new Vector3(0,10,0),new Vector3(2,-3,0),new FusionSettings { positionSigma=.1 });
            filter.Observe(new Observation { Kind=ObservationKind.Range,Time=0,Range=10,VarianceX=.01 },map,sigma);
            var guidance=new LandingGuidance(); var force=guidance.Command(filter,map,0,2000,true);
            Require(guidance.TerminalLatched && force.x<0,"terminal phase brakes lateral velocity");
            Require(force.magnitude<=6000.001 && new Vector2(force.x,force.z).magnitude<=force.y*Mathf.Tan(10*Mathf.Deg2Rad)+.001f,"force/tilt bounds");
            filter=new NavigationFilter(new Vector3(0,100,0),Vector3.zero,new FusionSettings { positionSigma=.1 });
            filter.Observe(new Observation { Kind=ObservationKind.Range,Time=0,Range=100,VarianceX=.01 },map,sigma);
            guidance.Command(filter,map,0,2000,true); Require(guidance.TerminalLatched,"terminal phase cannot chatter back to approach");
            var staleGuidance=new LandingGuidance(); staleGuidance.Command(filter,map,3,2000,true);
            Require(staleGuidance.Mode==GuidanceMode.DegradedBrake,"stale altitude visibly degrades mode");
            checks.Add("Latched terminal braking, thrust/tilt limits, explicit stale-sensor mode");
            Close(LandingMetrics.Miss(new Vector3(22,0,-31),new Vector2(22,-31)),0,0,"map-frame sign");
            Require(!LandingMetrics.Success(true,1,1,1,10),"horizontal speed equality fails");
            Require(!LandingMetrics.Success(true,10,1,0,10),"miss equality fails");
            Require(!LandingMetrics.Success(false,0,0,0,10),"contact required");
            Require(!LandingMetrics.Success(true,float.NaN,0,0,10),"nonfinite cannot pass");
            checks.Add("Physical contact, strict speed/distance boundaries and frame transform");
            return new Report { passed=true,checks=checks.ToArray() };
        }
    }
}
