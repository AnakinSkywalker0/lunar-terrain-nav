using System;
using System.IO;
using UnityEditor;
using UnityEngine;

namespace SensorTrust.Editor
{
    // Command-line launcher for the guidance ablation (no editor window needed):
    //   Unity.exe -batchmode -nographics -projectPath LANTERN -executeMethod SensorTrust.Editor.GuidanceAblationHeadless.Run
    //             -gaStage eval_g1 [-gaOut <folder name under out/guidance_ablation>]
    // Re-running with the same -gaOut resumes: cases already in summary.csv are skipped.
    [InitializeOnLoad]
    public static class GuidanceAblationHeadless
    {
        static GuidanceAblationHeadless() { EditorApplication.playModeStateChanged+=PlayChanged; }

        static string Arg(string name)
        {
            var args=Environment.GetCommandLineArgs();
            for(int i=0;i<args.Length-1;i++) if(args[i]==name) return args[i+1];
            return "";
        }

        public static void Run()
        {
            string stage=Arg("-gaStage"); if(stage=="") stage="eval_smoke";
            SessionState.SetBool("LANTERN.GA.Headless",true);
            SessionState.SetString("LANTERN.GA.Out",Arg("-gaOut"));
            GuidanceAblationExperiment.Request(stage);
        }

        static void PlayChanged(PlayModeStateChange state)
        {
            if(state!=PlayModeStateChange.EnteredPlayMode) return;
            string pending=SessionState.GetString("LANTERN.GA.Pending","");
            SessionState.EraseString("LANTERN.GA.Pending");
            if(pending=="") return;
            EditorApplication.delayCall+=()=>
            {
                try { GuidanceAblationExperiment.Start(pending); }
                catch(Exception ex)
                {
                    Debug.LogException(ex);
                    File.WriteAllText("Library/GuidanceAblation.error",ex.ToString());
                    if(SessionState.GetBool("LANTERN.GA.Headless",false)) EditorApplication.Exit(3);
                    EditorApplication.isPlaying=false;
                }
            };
        }
    }
}
