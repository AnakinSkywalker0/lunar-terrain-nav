using System;
using System.IO;
using UnityEditor;
using UnityEngine;

namespace SensorTrust.Editor
{
    // Explicit local job requests survive MCP reconnects. Only fixed experiment
    // operations are accepted; no arbitrary code is executed from the request.
    [InitializeOnLoad]
    public static class TerrainExperimentCommand
    {
        static double next;
        static TerrainExperimentCommand() { EditorApplication.update+=Poll; EditorApplication.playModeStateChanged+=PlayChanged; }
        static void PlayChanged(PlayModeStateChange state)
        {
            if(state!=PlayModeStateChange.EnteredPlayMode) return;
            string pending=SessionState.GetString("LANTERN.PendingExperiment","");
            SessionState.EraseString("LANTERN.PendingExperiment");
            if(pending=="") return;
            EditorApplication.delayCall+=()=>
            {
                try {
                    if(pending.StartsWith("transfer_",StringComparison.Ordinal)) ScanUtilityTransferExperiment.Start(pending.Substring(9));
                    else if(pending.StartsWith("utility_",StringComparison.Ordinal)) ScanUtilityExperiment.Start(pending.Substring(8));
                    else if(pending.StartsWith("trust_",StringComparison.Ordinal)) ScanTrustExperiment.Start(pending=="trust_smoke");
                    else ShortDescentExperiment.Start(pending=="smoke" || pending=="expanded_smoke",pending.StartsWith("expanded",StringComparison.Ordinal));
                }
                catch(Exception ex) { File.WriteAllText("Library/TerrainExperiment.command-result",ex.ToString()); Debug.LogException(ex); EditorApplication.isPlaying=false; }
            };
        }
        static void Poll()
        {
            if(EditorApplication.timeSinceStartup<next || EditorApplication.isCompiling || EditorApplication.isUpdating) return;
            next=EditorApplication.timeSinceStartup+.5;
            const string path="Library/TerrainExperiment.command";
            if(!File.Exists(path)) return;
            string command=File.ReadAllText(path).Trim(); File.Delete(path);
            try
            {
                if(command=="smoke") ShortDescentExperiment.Smoke();
                else if(command=="full") ShortDescentExperiment.Full();
                else if(command=="expanded") ShortDescentExperiment.Expanded();
                else if(command=="expanded_smoke") ShortDescentExperiment.ExpandedSmoke();
                else if(command=="trust_validate") ScanTrustVerification.Validate();
                else if(command=="trust_smoke") ScanTrustExperiment.Smoke();
                else if(command=="trust_full") ScanTrustExperiment.Full();
                else if(command=="utility_validate") ScanUtilityVerification.Validate();
                else if(command.StartsWith("transfer_",StringComparison.Ordinal)) ScanUtilityTransferExperiment.Request(command.Substring(9));
                else if(command.StartsWith("utility_",StringComparison.Ordinal)) ScanUtilityExperiment.Request(command.Substring(8));
                else if(command=="view") TerrainExperimentView.Latest();
                else if(command=="play") EditorApplication.isPlaying=true;
                else if(command=="stop_play") EditorApplication.isPlaying=false;
                else throw new ArgumentException("Unknown experiment operation");
                File.WriteAllText("Library/TerrainExperiment.command-result",command+": accepted "+DateTime.UtcNow.ToString("O"));
            }
            catch(Exception ex) { File.WriteAllText("Library/TerrainExperiment.command-result",ex.ToString()); Debug.LogException(ex); }
        }
    }
}
