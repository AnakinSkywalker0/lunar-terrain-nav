using System;
using UnityEngine;

namespace SensorTrust.Experiments
{
    // Inference receives matcher diagnostics only. No scene, Rigidbody or truth.
    public sealed class PortableScanTrust
    {
        [Serializable] public sealed class Tree
        {
            public int[] feature,left,right;
            public double[] threshold,bad;
        }
        [Serializable] public sealed class Model
        {
            public int version;
            public string task,kind,model_id;
            public string[] features;
            public double bad_score_threshold,intercept;
            public double[] center,scale,weights;
            public Tree[] trees;
        }
        [Serializable] public sealed class Rule { public double max_rms_m,min_confidence; }
        public readonly Model model;
        public readonly Rule rule;
        static readonly string[] Names={"points","rms_m","confidence","dx","dz","correction_norm_m"};
        public PortableScanTrust(string modelJson,string ruleJson)
        {
            model=JsonUtility.FromJson<Model>(modelJson); rule=JsonUtility.FromJson<Rule>(ruleJson);
            if(model==null || model.version!=1 || model.task!="scan_absolute_error_over_10m_v1" ||
               string.IsNullOrEmpty(model.model_id) || model.features==null || model.features.Length!=6)
                throw new ArgumentException("Wrong scan-trust task/schema");
            for(int i=0;i<6;i++) if(model.features[i]!=Names[i]) throw new ArgumentException("Feature order differs");
            if(!Finite(model.bad_score_threshold) || model.bad_score_threshold<=0 || model.bad_score_threshold>=1)
                throw new ArgumentException("Invalid learned threshold");
            if(rule==null || !Finite(rule.max_rms_m) || rule.max_rms_m<0 || !Finite(rule.min_confidence) ||
                rule.min_confidence<0 || rule.min_confidence>1) throw new ArgumentException("Invalid classical rule");
            if(model.kind=="forest")
            {
                if(model.trees==null || model.trees.Length==0) throw new ArgumentException("No trees");
                foreach(var t in model.trees)
                {
                    int n=t.feature.Length;
                    if(n==0 || t.left.Length!=n || t.right.Length!=n || t.threshold.Length!=n || t.bad.Length!=n)
                        throw new ArgumentException("Invalid tree arrays");
                    for(int i=0;i<n;i++)
                    {
                        if(!Finite(t.bad[i]) || t.bad[i]<0 || t.bad[i]>1) throw new ArgumentException("Invalid leaf score");
                        if(t.left[i]>=0 && (t.feature[i]<0 || t.feature[i]>=6 || t.left[i]>=n || t.right[i]<0 ||
                            t.right[i]>=n || !Finite(t.threshold[i]))) throw new ArgumentException("Invalid branch");
                    }
                }
            }
            else if(model.kind=="logistic")
            {
                if(model.center.Length!=6 || model.scale.Length!=6 || model.weights.Length!=6 || !Finite(model.intercept))
                    throw new ArgumentException("Invalid logistic arrays");
                for(int i=0;i<6;i++) if(!Finite(model.center[i]) || !Finite(model.scale[i]) || model.scale[i]<=0 ||
                    !Finite(model.weights[i])) throw new ArgumentException("Invalid logistic parameters");
            }
            else throw new ArgumentException("Unsupported scan model");
        }
        static bool Finite(double v) => !double.IsNaN(v) && !double.IsInfinity(v);
        public static float[] Features(ScanMatch m) => new[]{(float)m.points,m.rms,m.confidence,
            m.correction.x,m.correction.y,(float)Math.Sqrt((double)m.correction.x*m.correction.x+(double)m.correction.y*m.correction.y)};
        public double Score(float[] x)
        {
            if(x.Length!=6) return double.NaN;
            foreach(float v in x) if(!Finite(v)) return double.NaN;
            if(model.kind=="logistic")
            {
                double z=model.intercept;
                for(int i=0;i<6;i++) z+=((double)x[i]-model.center[i])/model.scale[i]*model.weights[i];
                return 1/(1+Math.Exp(-z));
            }
            double sum=0;
            foreach(var t in model.trees)
            {
                int node=0,steps=0;
                while(t.left[node]>=0)
                {
                    if(++steps>t.feature.Length) return double.NaN;
                    node=(double)x[t.feature[node]]<=t.threshold[node]?t.left[node]:t.right[node];
                }
                sum+=t.bad[node];
            }
            return sum/model.trees.Length;
        }
        public bool Accept(ScanMatch m,double score) => m.valid && m.accepted && Finite(score) &&
            score>=0 && score<=1 && score<model.bad_score_threshold;
        public bool RuleAccept(ScanMatch m) => m.valid && m.accepted && m.rms<=rule.max_rms_m &&
            m.confidence>=rule.min_confidence;
    }
}
