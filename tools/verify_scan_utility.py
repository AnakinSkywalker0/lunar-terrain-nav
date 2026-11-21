"""Independent archived-distance checks and policy-routing verification."""
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from sim.scan_utility import FEATURES,optimal_gain,policy_gain
KEYS=['site_id','condition','variant','altitude','error_id','seed']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def verify(folder):
    assert (folder/'status.txt').read_text().startswith('Complete;'),'Incomplete run'
    r=pd.read_csv(folder/'summary.csv');s=pd.read_csv(folder/'scans.csv')
    stage=r.stage.iloc[0];plan=json.loads((folder/'plan.json').read_text())
    smoke=stage.endswith('_smoke');collect=stage.startswith('collect')
    transfer=plan.get('dataset')=='Site01'
    expected=4 if stage=='collect_smoke' else plan['expected_collect_cases'] if collect else 21 if stage=='dev_smoke' else 15 if stage=='eval_smoke' else plan['expected_development_cases'] if stage=='dev' else plan['expected_evaluation_cases']
    assert len(r)==expected and r.id.is_unique,(len(r),expected)
    assert not s[['id','scan_index']].duplicated().any()
    assert np.isfinite(s[list(FEATURES)]).all().all()
    assert s.confidence_feature.between(0,1).all() and s.has_previous.isin([0,1]).all()
    assert np.allclose(s.confidence,s.confidence_feature,atol=1e-6)
    assert np.allclose(s.correction_norm_m,np.hypot(s.dx,s.dz),atol=2e-4)
    # Recompute gain targets from three independently archived distances.
    recomputed=np.array([optimal_gain(b,p,n) for b,p,n in zip(s.before_error_m,s.proposed_error_m,s.correction_norm_m)])
    assert np.allclose(recomputed,s.optimal_gain,atol=.01),np.max(np.abs(recomputed-s.optimal_gain))
    assert np.allclose(s.applied_gain.gt(0),s.applied)
    # Convex-combination identity independently checks partial-correction effects.
    a=s.applied_gain.to_numpy(); b=s.before_error_m.to_numpy(); p=s.proposed_error_m.to_numpy(); n=s.correction_norm_m.to_numpy()
    after=np.sqrt(np.maximum(0,(1-a)*b*b+a*p*p-a*(1-a)*n*n))
    assert np.allclose(after,s.applied_error_m,atol=.025),np.max(np.abs(after-s.applied_error_m))
    assert np.array_equal(s.applied & s.applied_error_m.gt(10),s.applied_bad)
    record=(folder/'source_sha256.txt').read_text().upper()
    for name in [('ScanUtilityTransferRunner.cs' if transfer else 'ScanUtilityRunner.cs'),'TerrainNavigationCore.cs','ScanUtilityPolicy.cs','plan.json']:
        assert sha(folder/name).upper() in record,name
    original=ROOT/'out/terrain_matching/20261021_183805_expanded_v2/TerrainNavigationCore.cs'
    assert sha(folder/'TerrainNavigationCore.cs')==sha(original)
    old_model=json.loads((folder/'model.json').read_text())
    assert np.array_equal(s.valid & s.accepted & s.bad_score.lt(old_model['bad_score_threshold']),s.ml_accept)
    assert sha(folder/'model.json')==sha(ROOT/'out/scan_trust/20261022_model_v1/model.json')
    assert sha(folder/'protocol.md')==plan['protocol_sha256']
    for row in r.itertuples():
        assert (folder/(row.id+'.csv')).exists() and (folder/(row.id+'_cloud.csv')).exists()
        if not collect:
            assert row.success==bool(row.touchdown and row.impact_vz<2 and row.impact_vh<1 and row.target_miss_m<10)
    if collect:
        assert len(s)==2*len(r) and not s.applied.any()
        for _,g in s.groupby('id'):
            assert g.has_previous.tolist()==[0,int(g.valid.iloc[0])]
    else:
        expected_arms={'off','geometric','bounded','old_ml','utility'} if stage.startswith('eval') else {'off','geometric','bounded','old_ml','utility_hard','utility_soft','utility_hybrid'}
        assert r.groupby(KEYS).arm.apply(lambda x:set(x)==expected_arms).all()
        first=s[s.scan_index.eq(0)].set_index('id')
        for _,g in r.groupby(KEYS):
            cols=['points','dx','dz','rms_m','confidence','before_error_m','proposed_error_m',*FEATURES,'utility_prediction']
            f=first.loc[g.id,cols].to_numpy(float)
            assert np.allclose(f,f[0],atol=1e-6,rtol=0)
        choice=json.loads((folder/'policy.json').read_text())['policy'] if stage.startswith('eval') else None
        expected=[]
        for row in s.itertuples():
            policy=choice if row.arm=='utility' else row.arm
            value=float(row.ml_accept) if policy=='old_ml' else policy_gain(policy,row.utility_prediction,row.correction_norm_m,row.agl_feature_m,row.valid,row.accepted)
            expected.append(value)
        assert np.allclose(expected,s.applied_gain,atol=2e-5),'Gain routing mismatch'
        assert json.loads((folder/'parity_report.json').read_text())['passed']
        assert sha(folder/'utility_model.json')==sha(ROOT/'out/scan_utility/model_v2/model.json')
        if transfer:
            from sim.scan_utility import predict_portable
            predictions=predict_portable(json.loads((folder/'utility_model.json').read_text()),s[list(FEATURES)].to_numpy())
            assert np.allclose(predictions,s.utility_prediction,atol=1e-9,rtol=0),'Transfer input inference parity failed'
            assets=ROOT/'LANTERN/Assets/Experiments/ScanUtilityTransfer'
            assert sha(folder/'plan.json')==sha(assets/'plan.json')
            assert sha(folder/'site01_height.raw')==plan['raw_sha256']
            metadata=json.loads((folder/'site01_height.json').read_text())
            assert sha(ROOT/metadata['source'])==plan['source_sha256']==metadata['source_sha256']
            freeze=json.loads((assets/'RUNTIME_FREEZE.json').read_text())
            for path,digest in freeze.items():
                assert sha(ROOT/path)==digest,('Runtime freeze changed',path)
            assert sha(folder/'ScanUtilityTransferRunner.cs')==freeze['LANTERN/Assets/Editor/ScanUtilityTransferRunner.cs']
            for path,digest in plan['frozen_sha256'].items():
                assert sha(ROOT/path)==digest,('Frozen component changed',path)
                name='utility_model.json' if path.endswith('ScanUtility/model.json') else Path(path).name
                assert sha(folder/name)==digest,('Archived component mismatch',name)
            baseline=ROOT/plan['baseline_evaluation']
            for name in ['utility_model.json','model.json','policy.json','TerrainNavigationCore.cs','ScanUtilityPolicy.cs','PortableScanTrust.cs','TerrainTouchdownRecorder.cs']:
                assert sha(folder/name)==sha(baseline/name),('Baseline changed',name)
            sites=plan['smoke_sites'] if smoke else plan['evaluation_sites']
            assert set(r.site_id)=={site['id'] for site in sites}
            from itertools import product
            expected_keys=set(product([site['id'] for site in sites],['aligned','relief_positive','map_shift'],[3],
                                      [500] if smoke else [500,1500],['u0'] if smoke else ['u0','u1','u2'],
                                      [404] if smoke else [717,818,919]))
            assert set(r[KEYS].itertuples(index=False,name=None))==expected_keys
            assert np.allclose(r.true_start_x,-12) and np.allclose(r.true_start_z,16)
            for i,error in enumerate(plan['evaluation_errors']):
                g=r[r.error_id.eq('u'+str(i))]
                assert np.allclose(g.initial_error_x,error['x']) and np.allclose(g.initial_error_z,error['z'])
            for site in sites:
                g=r[r.site_id.eq(site['id'])]
                assert np.allclose(g.site_x,site['x']) and np.allclose(g.site_z,site['z'])
            assert r.groupby(KEYS).size().eq(5).all()
            terrain=np.fromfile(folder/'site01_height.raw',dtype='<u2').reshape(metadata['resolution'],metadata['resolution']).astype(float)
            terrain=terrain/65535*(metadata['max_m']-metadata['min_m'])
            spacing=metadata['side_m']/(metadata['resolution']-1)
            def sample(x,z):
                x,z=np.broadcast_arrays(x,z)
                # Unity GetInterpolatedHeight follows its terrain triangles,
                # split along the bottom-left/top-right diagonal, not bilinear interpolation.
                gx,gz=x/spacing,z/spacing
                ix,iz=gx.astype(int),gz.astype(int)
                fx,fz=gx-ix,gz-iz
                a,b,c,d=terrain[iz,ix],terrain[iz,ix+1],terrain[iz+1,ix],terrain[iz+1,ix+1]
                return np.where(fx>fz,a+fx*(b-a)+fz*(d-b),a+fz*(c-a)+fx*(d-c))
            # Allow at most two internal 15-bit height quanta (sample and centre)
            # plus float interpolation error when comparing a relative height.
            height_tolerance=2*(metadata['max_m']-metadata['min_m'])/32766+.005
            for mapfile in folder.glob('map_*.bin'):
                import struct
                with mapfile.open('rb') as stream:
                    size,span=struct.unpack('<if',stream.read(8))
                    heights=np.frombuffer(stream.read(),dtype='<f4')
                assert size==301 and span==2400 and len(heights)==size*size*2
                assert np.isfinite(heights).all() and np.abs(heights).max()<1999,'Terrain clipped by collider range'
                site=next(site for site in sites if mapfile.name.startswith('map_'+site['id']+'_'))
                condition=mapfile.stem[len('map_'+site['id']+'_'):-3]
                x,z=np.meshgrid(np.linspace(-1200,1200,301),np.linspace(-1200,1200,301))
                center=sample(site['x'],site['z'])
                actual=heights.reshape(301,301,2)
                truth=sample(site['x']+x,site['z']+z)-center
                if condition=='relief_positive':truth+=16*np.exp(-((x+75)**2+(z+80)**2)/(2*65**2))
                prior=sample(site['x']+x+(22 if condition=='map_shift' else 0),site['z']+z+(-31 if condition=='map_shift' else 0))-center
                assert np.allclose(actual[:,:,0],truth,atol=height_tolerance,rtol=0),('Truth terrain mismatch',mapfile.name,float(np.abs(actual[:,:,0]-truth).max()))
                assert np.allclose(actual[:,:,1],prior,atol=height_tolerance,rtol=0),('Onboard map mismatch',mapfile.name,float(np.abs(actual[:,:,1]-prior).max()))
            (folder/'RUNTIME_FREEZE.json').write_bytes((assets/'RUNTIME_FREEZE.json').read_bytes())
        else:
            assert sha(folder/'plan.json')==sha(ROOT/'out/scan_utility/model_v2/plan.json')
            assert sha(folder/'protocol.md')==sha(ROOT/'out/scan_utility/model_v2/protocol.md')
    (folder/'VERIFICATION.md').write_text(f'{len(r)} unique cases; {len(s)} unique scan records. Labels recomputed from archived distances; partial-correction geometry checked; feature schema finite; frozen core/source hashes checked; all trajectory/cloud pairs present. '+('Two uncorrected scans per pose, with history reset.' if collect else 'Complete arms, identical initial observable inputs, success labels and correction-routing checks passed; Python/Unity parity confirmed.')+'\n')
    return r,s

if __name__=='__main__':
    r,s=verify(Path(sys.argv[1]));print('PASS:',len(r),'cases,',len(s),'scans')
