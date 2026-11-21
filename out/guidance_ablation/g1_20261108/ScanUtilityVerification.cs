using System;
using System.IO;
using System.Globalization;
using UnityEngine;
using SensorTrust.Experiments;

namespace SensorTrust.Editor
{
    public static class ScanUtilityVerification
    {
        public const string Folder="Assets/Experiments/ScanUtility/";
        public static ScanUtilityPolicy Load() => new ScanUtilityPolicy(File.ReadAllText(Folder+"model.json"));
        public static void Validate()
        {
            var utility=Load();int rows=0;double maximum=0;
            using(var f=new StreamReader(Folder+"parity.csv"))
            {
                f.ReadLine();string line;
                while((line=f.ReadLine())!=null)
                {
                    var c=line.Split(',');var x=new float[6];
                    for(int i=0;i<6;i++)x[i]=(float)double.Parse(c[i],CultureInfo.InvariantCulture);
                    double expected=double.Parse(c[6],CultureInfo.InvariantCulture),score=utility.Predict(x);
                    if(!ScanUtilityPolicy.Finite(score))throw new Exception("Nonfinite utility prediction");
                    maximum=Math.Max(maximum,Math.Abs(score-expected));
                    if(maximum>1e-9)throw new Exception("Utility Python/Unity mismatch row "+rows);
                    rows++;
                }
            }
            if(rows<1000)throw new Exception("Insufficient utility fixtures");
            var m=new ScanMatch{valid=true,accepted=true,correction=new Vector2(30,40),rms=1,confidence=.9f};
            var a=ScanUtilityPolicy.Features(m,500,Vector2.zero,false);m.correction=new Vector2(-40,30);
            var b=ScanUtilityPolicy.Features(m,500,Vector2.zero,false);
            for(int i=0;i<6;i++)if(a[i]!=b[i])throw new Exception("Direction invariance failed");
            if(ScanUtilityPolicy.Gain("utility_soft",m,double.NaN,500)!=0)throw new Exception("Nonfinite gain guard failed");
            if(ScanUtilityPolicy.Gain("bounded",m,1,20)>.20001f)throw new Exception("Correction bound failed");
            m.accepted=false;if(ScanUtilityPolicy.Gain("utility_hard",m,1,500)!=0)throw new Exception("Geometric rejection guard failed");
            string report="{\"passed\":true,\"rows\":"+rows+",\"max_score_difference\":"+maximum.ToString("R",CultureInfo.InvariantCulture)+"}";
            File.WriteAllText("Library/ScanUtility.validation.json",report);Debug.Log("[ScanUtility] Parity/guards passed "+report);
        }
    }
}
