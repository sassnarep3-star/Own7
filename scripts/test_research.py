import unittest
from research_math import fair_decimal, expected_net, no_vig, pearson
class ResearchMath(unittest.TestCase):
    def test_fair_price(self): self.assertEqual(fair_decimal(.5),2)
    def test_push(self): self.assertAlmostEqual(expected_net(.4,2,.2),0)
    def test_no_vig(self): self.assertEqual(no_vig([2,2]),[.5,.5])
    def test_correlation(self): self.assertAlmostEqual(pearson([1,2,3],[3,2,1]),-1)
    def test_invalid(self):
        for fn,args in [(fair_decimal,(0,)),(fair_decimal,(float('nan'),)),(expected_net,(.8,2,.4)),(no_vig,([1,2],)),(pearson,([1,1,1],[1,2,3]))]:
            with self.assertRaises(ValueError):fn(*args)
if __name__=='__main__': unittest.main()
