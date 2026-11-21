using System;
using System.IO;
using UnityEditor;
using UnityEngine;
using SensorTrust.Experiments.NavigationV3;

namespace SensorTrust.Editor
{
    /// <summary>Exercise the actual demo MonoBehaviour in Play mode, including restarts and rendering.</summary>
    [InitializeOnLoad]
    public static class NavigationDemoVerification
    {
        const string Key="LANTERN.NavigationV3.VisualCheck";
        static NavigationDemoV3 demo;
        static string output;
        static double began,pausedTime,pausedAt;
        static int phase;
        static bool active,failed;
        static TextAsset originalModel;
        [Serializable] sealed class Report { public bool passed; public string[] checks; public string message; }
        static NavigationDemoVerification()
        {
            EditorApplication.playModeStateChanged+=change=>
            {
                if(change==PlayModeStateChange.EnteredPlayMode && SessionState.GetBool(Key,false))
                {
                    SessionState.EraseBool(Key); output=SessionState.GetString(Key+".output","");
                    began=EditorApplication.timeSinceStartup; active=true; phase=0;
                    Application.logMessageReceived+=Log; EditorApplication.update+=Tick;
                }
                if(change==PlayModeStateChange.EnteredEditMode && active)
                { active=false; if(Application.isBatchMode) EditorApplication.delayCall+=()=>EditorApplication.Exit(failed?1:0); }
            };
        }
        public static void Run()
        {
            NavigationExperiment.BuildDemo();
            output=Path.GetFullPath("../out/navigation_v3/"+DateTime.UtcNow.ToString("yyyyMMdd_HHmmss_fff")+"_visual");
            Directory.CreateDirectory(output); SessionState.SetString(Key+".output",output);
            SessionState.SetBool(Key,true); EditorApplication.isPlaying=true;
        }
        static void Log(string message,string stack,LogType type)
        {
            if(type==LogType.Exception || type==LogType.Error) { failed=true; File.AppendAllText(output+"/runtime_errors.txt",message+"\n"+stack+"\n"); }
        }
        static void Assert(bool value,string message) { if(!value) throw new Exception(message); }
        static void Tick()
        {
            try
            {
                Assert(EditorApplication.timeSinceStartup-began<90,"Demo verification timed out");
                if(phase==0)
                {
                    demo=UnityEngine.Object.FindFirstObjectByType<NavigationDemoV3>();
                    if(demo==null || demo.Simulation==null) return;
                    Assert(demo.Error==null && demo.Simulation.Case.arm=="classical_terminal","Default demo is not classical");
                    demo.Paused=true; pausedTime=demo.Simulation.Time; pausedAt=EditorApplication.timeSinceStartup; phase=1;
                }
                else if(phase==1 && EditorApplication.timeSinceStartup-pausedAt>.3)
                {
                    Assert(demo.Simulation.Time==pausedTime,"Pause changed simulation time");
                    originalModel=demo.utilityModel; demo.useMl=true; demo.Restart(); demo.Paused=true;
                    Assert(demo.Error==null && demo.Simulation.Case.arm=="ml_terminal","ML restart failed");
                    for(int i=0;i<200;i++) demo.Simulation.Step();
                    phase=2;
                }
                else if(phase==2)
                {
                    Capture(demo.overview,demo.vehicleCamera,output+"/live_ml.png");
                    demo.utilityModel=null; demo.Restart(); demo.Paused=true;
                    int fallbacks=0;
                    demo.Simulation.SensorObserved+=record=>
                    { if(record.Kind==ObservationKind.Terrain && record.Decision=="Accepted" && record.Prediction==-1 && record.Inflation==1) fallbacks++; };
                    for(int i=0;i<200;i++) demo.Simulation.Step();
                    Assert(fallbacks>0 && demo.Error==null && demo.ModelWarning!=null,"Missing model did not visibly fall back to classical fusion");
                    demo.utilityModel=originalModel; demo.useMl=false; demo.conditionIndex=1; demo.Restart(); demo.Paused=true;
                    Assert(demo.Simulation.Case.condition=="range_spike","Scenario restart did not change condition");
                    for(int i=0;i<300;i++) demo.Simulation.Step(); phase=3;
                }
                else if(phase==3)
                {
                    Capture(demo.overview,demo.vehicleCamera,output+"/live_range_fault.png");
                    Assert(demo.Error==null && !failed,"Runtime errors in live demo");
                    File.WriteAllText(output+"/verification.json",JsonUtility.ToJson(new Report { passed=true,
                        checks=new[]{"serialized scene and terrain assets", "default classical mode", "pause", "ML toggle on restart",
                            "live rendering", "missing-model fallback", "scenario restart", "no runtime errors"}, message="Play-mode demo checks passed" },true));
                    File.WriteAllText("../out/navigation_v3/latest_visual.txt",output); Finish();
                }
            }
            catch(Exception ex)
            {
                failed=true;
                File.WriteAllText(output+"/verification.json",JsonUtility.ToJson(new Report { passed=false,message=ex.ToString() },true));
                Debug.LogException(ex); Finish();
            }
        }
        static void Capture(Camera camera,Camera inset,string path)
        {
            Assert(SystemInfo.graphicsDeviceType!=UnityEngine.Rendering.GraphicsDeviceType.Null,"Visual check needs graphics; omit -nographics");
            var target=new RenderTexture(1024,768,24); var oldTarget=camera.targetTexture; var oldActive=RenderTexture.active;
            Texture2D image=null;
            try
            {
                camera.targetTexture=target; camera.Render(); RenderTexture.active=target;
                image=new Texture2D(1024,768,TextureFormat.RGB24,false); image.ReadPixels(new Rect(0,0,1024,768),0,0); image.Apply();
                Color[] pixels=image.GetPixels(); float low=1,high=0;
                for(int i=0;i<pixels.Length;i+=97) { low=Mathf.Min(low,pixels[i].grayscale); high=Mathf.Max(high,pixels[i].grayscale); }
                Assert(high-low>.05f,"Camera rendered a blank frame");
                if(inset!=null)
                {
                    var insetTarget=new RenderTexture(320,256,24); var previous=inset.targetTexture; var previousRect=inset.rect;
                    Texture2D detail=null;
                    try
                    {
                        inset.rect=new Rect(0,0,1,1); inset.targetTexture=insetTarget; inset.Render(); RenderTexture.active=insetTarget;
                        detail=new Texture2D(320,256,TextureFormat.RGB24,false); detail.ReadPixels(new Rect(0,0,320,256),0,0); detail.Apply();
                        image.SetPixels(688,20,320,256,detail.GetPixels()); image.Apply();
                    }
                    finally
                    {
                        inset.targetTexture=previous; inset.rect=previousRect; RenderTexture.active=target;
                        if(detail!=null) UnityEngine.Object.DestroyImmediate(detail);
                        insetTarget.Release(); UnityEngine.Object.DestroyImmediate(insetTarget);
                    }
                }
                File.WriteAllBytes(path,image.EncodeToPNG());
            }
            finally
            {
                camera.targetTexture=oldTarget; RenderTexture.active=oldActive;
                if(image!=null) UnityEngine.Object.DestroyImmediate(image);
                target.Release(); UnityEngine.Object.DestroyImmediate(target);
            }
        }
        static void Finish()
        {
            EditorApplication.update-=Tick; Application.logMessageReceived-=Log;
            if(demo!=null) demo.Paused=true;
            EditorApplication.delayCall+=()=>EditorApplication.isPlaying=false;
        }
    }
}
