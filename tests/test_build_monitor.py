import importlib.util, pathlib, random, unittest
P = pathlib.Path(__file__).parents[1] / "scripts" / "build_monitor.py"
S = importlib.util.spec_from_file_location("build_monitor", P); M = importlib.util.module_from_spec(S); S.loader.exec_module(M)
class MonitorTests(unittest.TestCase):
    def rows(self, rising=True):
        out=[]
        for i in range(80):
            p=10+i*.1 if rising else 20-i*.1
            out.append([f"2026-08-{(i%28)+1:02d}",p-.03,p,p+.08,p-.08,100000+i*1000,1000000,2.0])
        return out
    def test_rising_stock_scores_higher(self):
        up=M.analyse("000001","上涨",self.rows(True)); down=M.analyse("000002","下跌",self.rows(False))
        self.assertGreater(up["score"],down["score"]); self.assertGreater(up["ma5"],up["ma20"])
    def test_payload_declares_periodic_mode(self):
        p=M.build_payload({"names":{"000001":"测试"},"bars":{"000001":self.rows()},"provisional":{"applied":False}})
        self.assertEqual(p["dataMode"],"最近收盘数据"); self.assertEqual(len(p["stocks"]),1)
    def test_wave_plan_has_ordered_risk_levels(self):
        item=M.analyse("000001","测试",self.rows(True)); plan=item["wavePlan"]
        self.assertLess(plan["invalidation"],item["price"])
        self.assertGreaterEqual(plan["secondTarget"],plan["firstTarget"])
        self.assertEqual(plan["horizon"],"1—2周")
    def test_indicator_sets_are_explicit_daily_windows(self):
        item=M.analyse("000001","测试",self.rows(True))
        self.assertEqual(set(item["macdSet"]), {"day1","day2","day30","day60","day120"})
        self.assertEqual(set(item["maSet"]), {"ma5","ma10","ma20","ma30","ma60","ma120"})
        self.assertGreater(item["volumeSet"]["ratio5"], 0)
        self.assertIsNotNone(item["macdSet"]["day1"])
        self.assertIsNotNone(item["macdSet"]["day2"])
        self.assertAlmostEqual(item["macd"],item["macdSet"]["day1"],places=3)
        self.assertAlmostEqual(item["volumeRatio5"],item["volumeSet"]["ratio5"],places=2)
        self.assertEqual(item["ma5"],item["maSet"]["ma5"])
    def test_falling_stock_has_no_pullback_above_price(self):
        item=M.analyse("000002","下跌",self.rows(False)); M.repair_levels(item); plan=item["wavePlan"]
        self.assertFalse(plan["aboveMa20"])
        self.assertGreater(plan["bounceLow"],item["price"])
        self.assertGreaterEqual(plan["bounceHigh"],plan["bounceLow"])
        self.assertLess(plan["invalidation"],item["price"])
        self.assertGreater(plan["firstTarget"],item["price"])
        self.assertEqual(M.level_violations(item),[])
    def test_random_series_never_violate_level_ordering(self):
        rnd=random.Random(7)
        for _ in range(300):
            p=rnd.uniform(3,90); rows=[]
            for i in range(140):
                p*=1+rnd.uniform(-.05,.05)
                rows.append([f"2026-{(i%12)+1:02d}-{(i%28)+1:02d}",p*.99,p,p*1.02,p*.97,rnd.uniform(1e5,1e6),1e7,2.0])
            item=M.analyse("000000","随机",rows)
            if item is None: continue
            M.repair_levels(item)
            self.assertEqual(M.level_violations(item),[],msg=str(item["wavePlan"]))
if __name__ == "__main__": unittest.main()
