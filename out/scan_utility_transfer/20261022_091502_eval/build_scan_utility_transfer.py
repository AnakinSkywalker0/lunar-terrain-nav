"""Make a separate terrain adapter from the archived runner; preserve algorithms."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
text = (ROOT/'out/scan_utility/20261021_204054_eval/ScanUtilityRunner.cs').read_text()
text = text.replace('ScanUtilityExperiment', 'ScanUtilityTransferExperiment')
text = text.replace('SourceMin=-2847.877197265625f', 'SourceMin=0f')
text = text.replace('"utility_"+requested', '"transfer_"+requested')
text = text.replace('new[]{"collect_smoke","collect","dev_smoke","dev","eval_smoke","eval"}', 'new[]{"eval_smoke","eval"}')
text = text.replace('"../out/scan_utility/', '"../out/scan_utility_transfer/')
text = text.replace('"../docs/SCAN_TRUST_PROTOCOL_V2.md"', '"../docs/SCAN_UTILITY_TRANSFER_PROTOCOL.md"')
text = text.replace('"Assets/Experiments/ScanUtility/plan.json"', '"Assets/Experiments/ScanUtilityTransfer/plan.json"')
text = text.replace('"Assets/Editor/ScanUtilityRunner.cs"', '"Assets/Editor/ScanUtilityTransferRunner.cs"')
text = text.replace('public LandingSite[] training_sites,validation_sites,evaluation_sites;', 'public LandingSite[] training_sites,validation_sites,evaluation_sites,smoke_sites;')
text = text.replace('var sites=evaluation?plan.evaluation_sites:plan.validation_sites;', 'var sites=smoke?plan.smoke_sites:plan.evaluation_sites;')
old = '''            source=AssetDatabase.LoadAssetAtPath<TerrainData>("Assets/Terrain/Site04TerrainData.asset");
            if(source==null) throw new Exception("Site04 terrain missing");'''
assert old in text
text = text.replace(old, '''            var metadata=JsonUtility.FromJson<SourceMetadata>(File.ReadAllText("Assets/Experiments/ScanUtilityTransfer/site01_height.json"));
            source=new TerrainData { heightmapResolution=metadata.resolution, size=new Vector3(metadata.side_m,metadata.max_m-metadata.min_m,metadata.side_m) };
            var heights=new float[metadata.resolution,metadata.resolution];
            using(var reader=new BinaryReader(File.OpenRead("Assets/Experiments/ScanUtilityTransfer/site01_height.raw")))
            {
                if(reader.BaseStream.Length!=2L*metadata.resolution*metadata.resolution)throw new Exception("Source terrain length mismatch");
                for(int j=0;j<metadata.resolution;j++)for(int i=0;i<metadata.resolution;i++)heights[j,i]=reader.ReadUInt16()/65535f;
            }
            source.SetHeights(0,0,heights);''')
text = text.replace('        static System.Random rng;', '''        [Serializable] class SourceMetadata { public int resolution; public float side_m,min_m,max_m; }
        static System.Random rng;''')
text = text.replace('            foreach(var path in sourceFiles)', '''            sourceFiles.Add("Assets/Experiments/ScanUtilityTransfer/site01_height.raw");
            sourceFiles.Add("Assets/Experiments/ScanUtilityTransfer/site01_height.json");
            foreach(var path in sourceFiles)''')
text = text.replace('            Debug.Log("[ScanUtilityTransferExperiment] "+Status);', '''            if(source!=null)UnityEngine.Object.Destroy(source);
            Debug.Log("[ScanUtilityTransferExperiment] "+Status);''')
(ROOT/'LANTERN/Assets/Editor/ScanUtilityTransferRunner.cs').write_bytes(text.encode())
print('Created independent Site01 terrain adapter from archived v2 runner')
