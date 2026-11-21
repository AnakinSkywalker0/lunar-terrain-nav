using System;
using System.IO;
using System.Globalization;
using UnityEngine;
using SensorTrust.Experiments;

namespace SensorTrust.Editor
{
    public static class ScanTrustVerification
    {
        public const string Folder="Assets/Experiments/ScanTrust/";
        public static PortableScanTrust Load() => new PortableScanTrust(File.ReadAllText(Folder+"model.json"),File.ReadAllText(Folder+"rule.json"));
        public static string Validate()
        {
            var gate=Load(); int rows=0; double maximum=0;
            var timer=System.Diagnostics.Stopwatch.StartNew();
            using(var reader=new StreamReader(Folder+"parity.csv"))
            {
                reader.ReadLine(); string line;
                while((line=reader.ReadLine())!=null)
                {
                    var c=line.Split(','); var x=new float[6];
                    for(int i=0;i<6;i++) x[i]=(float)double.Parse(c[i],CultureInfo.InvariantCulture);
                    double expected=double.Parse(c[7],CultureInfo.InvariantCulture), score=gate.Score(x);
                    if(double.IsNaN(score) || double.IsInfinity(score)) throw new Exception("Nonfinite fixture inference");
                    maximum=Math.Max(maximum,Math.Abs(score-expected));
                    var m=new ScanMatch{valid=true,accepted=c[6]=="1"};
                    bool accept=gate.Accept(m,score);
                    if(maximum>1e-9 || accept!=(c[8]=="1")) throw new Exception("Python/Unity parity failed at row "+rows);
                    rows++;
                }
            }
            if(rows!=10530) throw new Exception("Incomplete parity fixtures: "+rows);
            if(gate.Accept(new ScanMatch{valid=false,accepted=true},0) ||
               gate.Accept(new ScanMatch{valid=true,accepted=true},double.NaN)) throw new Exception("Veto guards failed");
            string report="{\"passed\":true,\"rows\":"+rows+",\"max_score_difference\":"+
                maximum.ToString("R",CultureInfo.InvariantCulture)+",\"wall_ms\":"+
                timer.Elapsed.TotalMilliseconds.ToString("R",CultureInfo.InvariantCulture)+",\"model_id\":\""+gate.model.model_id+"\"}";
            File.WriteAllText("Library/ScanTrust.validation.json",report);
            Debug.Log("[ScanTrust] Python/Unity parity passed: "+report);
            return report;
        }
    }
}
