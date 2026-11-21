import unittest
from sim.scan_utility import optimal_gain,policy_gain,predict_portable

class UtilityTests(unittest.TestCase):
    def test_useful_but_not_absolute_accurate_update_retained(self):
        self.assertEqual(optimal_gain(100,45,55),1)
    def test_harmful_update_zero_gain(self):
        self.assertEqual(optimal_gain(0,50,50),0)
    def test_overshoot_has_partial_optimum(self):
        self.assertEqual(optimal_gain(20,20,40),.5)
    def test_tiny_update_not_punished(self):
        self.assertEqual(optimal_gain(.1,.2,.3),1)
    def test_late_correction_is_bounded(self):
        self.assertAlmostEqual(policy_gain('bounded',1,100,20),.1)
        self.assertAlmostEqual(policy_gain('utility_hybrid',1,100,20),.1)
    def test_geometric_rejection_and_nonfinite_fail_closed(self):
        self.assertEqual(policy_gain('utility_hard',1,10,500,accepted=False),0)
        self.assertEqual(policy_gain('utility_soft',float('nan'),10,500),0)
    def test_wrong_task_rejected(self):
        with self.assertRaises(ValueError):predict_portable({'task':'altimeter'},[[0]*6])
    def test_threshold_comparison_preserves_double_precision(self):
        import numpy as np
        from sim.scan_utility import FEATURES,TASK
        lower=np.nextafter(np.float32(1),np.float32(2));upper=np.nextafter(lower,np.float32(2))
        threshold=(float(lower)+float(upper))/2
        bundle=dict(version=2,task=TASK,features=list(FEATURES),trees=[dict(feature=[0,-2,-2],left=[1,-1,-1],right=[2,-1,-1],threshold=[threshold,-2,-2],value=[.5,0,1])])
        self.assertEqual(predict_portable(bundle,[[upper,0,0,0,0,0]])[0],1)

if __name__=='__main__':unittest.main()
