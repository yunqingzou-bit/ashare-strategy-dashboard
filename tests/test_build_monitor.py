import importlib.util, pathlib, unittest
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
if __name__ == "__main__": unittest.main()
