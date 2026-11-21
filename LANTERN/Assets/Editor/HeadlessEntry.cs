using UnityEditor;

namespace SensorTrust.Editor
{
    // Command-line entry points so experiments can start without the editor UI:
    //   Unity.exe -batchmode -projectPath LANTERN -executeMethod SensorTrust.Editor.HeadlessEntry.TransferSmoke
    // The runner itself enters Play mode and writes to ../out/<experiment>/<timestamp>_<stage>/.
    public static class HeadlessEntry
    {
        public static void TransferSmoke() => ScanUtilityTransferExperiment.Request("eval_smoke");
    }
}
