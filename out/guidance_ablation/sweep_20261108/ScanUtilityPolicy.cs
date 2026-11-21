using System;
using UnityEngine;

namespace SensorTrust.Experiments
{
    // Only observable diagnostics/history enter inference or correction scaling.
    public sealed class ScanUtilityPolicy
    {
        public static readonly string[] Names={"normalized_rms","confidence_feature","correction_norm_m","agl_feature_m","consistency_m","has_previous"};
        [Serializable] public sealed class Tree { public int[] feature,left,right; public double[] threshold,value; }
        [Serializable] public sealed class Model { public string task,model_id; public int version; public string[] features; public Tree[] trees; }
        [Serializable] public sealed class Choice { public string policy; }
        public readonly Model model;
        public ScanUtilityPolicy(string json)
        {
            model=JsonUtility.FromJson<Model>(json);
            if(model==null || model.version!=2 || model.task!="scan_optimal_gain_v2" || model.features==null || model.features.Length!=6 ||
               model.trees==null || model.trees.Length==0) throw new ArgumentException("Wrong utility model schema");
            for(int i=0;i<6;i++) if(model.features[i]!=Names[i]) throw new ArgumentException("Wrong utility feature order");
            foreach(var t in model.trees)
            {
                int n=t.feature.Length;
                if(n==0 || t.left.Length!=n || t.right.Length!=n || t.threshold.Length!=n || t.value.Length!=n)
                    throw new ArgumentException("Invalid utility tree arrays");
                for(int i=0;i<n;i++)
                {
                    if(!Finite(t.value[i]) || t.value[i]<0 || t.value[i]>1+1e-9) throw new ArgumentException("Invalid gain leaf");
                    if(t.left[i]>=0 && (t.feature[i]<0 || t.feature[i]>=6 || t.left[i]>=n || t.right[i]<0 || t.right[i]>=n || !Finite(t.threshold[i])))
                        throw new ArgumentException("Invalid utility branch");
                }
            }
        }
        public static bool Finite(double v) => !double.IsNaN(v) && !double.IsInfinity(v);
        public static float[] Features(ScanMatch m,float agl,Vector2 expected,bool previous)
        {
            float norm=(float)Math.Sqrt((double)m.correction.x*m.correction.x+(double)m.correction.y*m.correction.y);
            return new[]{m.rms/(.05f+.001f*Mathf.Max(0,agl)),m.confidence,norm,Mathf.Max(0,agl),
                previous?Vector2.Distance(m.correction,expected):0,previous?1f:0f};
        }
        public double Predict(float[] x)
        {
            if(x.Length!=6) return double.NaN;
            foreach(float v in x) if(!Finite(v)) return double.NaN;
            double total=0;
            foreach(var t in model.trees)
            {
                int node=0,steps=0;
                while(t.left[node]>=0)
                {
                    if(++steps>t.feature.Length) return double.NaN;
                    node=(double)x[t.feature[node]]<=t.threshold[node]?t.left[node]:t.right[node];
                }
                total+=t.value[node];
            }
            return Math.Max(0,Math.Min(1,total/model.trees.Length));
        }
        public static float Gain(string policy,ScanMatch m,double prediction,float agl)
        {
            if(!m.valid || !m.accepted) return 0;
            if(policy=="off" || policy=="collect") return 0;
            if(policy=="geometric") return 1;
            if(policy!="bounded" && !Finite(prediction)) return 0;
            float p=(float)Math.Max(0,Math.Min(1,prediction));
            float gain=policy=="utility_hard"?(p>=.5f?1:0):policy=="utility_soft"?p:
                policy=="utility_hybrid"?(p>=.75f?1:p):policy=="bounded"?1:0;
            if(policy=="bounded" || policy=="utility_hybrid")
                gain=Mathf.Min(gain,Mathf.Max(5,.5f*agl)/Mathf.Max(.001f,m.correction.magnitude));
            return gain;
        }
    }
}
