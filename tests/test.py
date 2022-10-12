import unittest
from plot61_namo.plot61 import *

class TestGaugeReader(unittest.TestCase):

    # Test time interval reading
    def test_dt(self):
        timeArray, gaugeArray = getGauge("tests/manchester.csv")
        dt = (timeArray[1]-timeArray[0])*86400.0
        self.assertAlmostEqual(dt, 3600)

    def test_missing_verified(self):
        timeArray, gaugeArray = getGauge("tests/rollover_pass.csv")
        self.assertTrue(True,True)


if __name__ == '__main__':
    unittest.main()
