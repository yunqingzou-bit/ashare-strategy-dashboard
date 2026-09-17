# -*- coding: utf-8 -*-
'''Daily pipeline entry: fetch -> replay -> report -> build site.'''
import argparse, os, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STEPS = ['fetch.py', 'replay.py', 'report.py', 'build_site.py', 'build_tables.py']
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', type=int, default=45)
    ap.add_argument('--skip-fetch', action='store_true')
    a = ap.parse_args()
    env = dict(os.environ)
    env['WINDOW_DAYS'] = str(a.days)
    t0 = time.time()
    for i, s in enumerate(STEPS):
        if a.skip_fetch and s == 'fetch.py': continue
        if s == 'fetch.py':
            cmd = [sys.executable, os.path.join(HERE, s), '--days', str(a.days)]
        else:
            cmd = [sys.executable, os.path.join(HERE, s)]
        print('=== ' + s + ' ===', flush=True)
        r = subprocess.run(cmd, cwd=ROOT, env=env)
        if r.returncode != 0:
            if s == 'snapshot.py':
                print('  snapshot failed; continuing without intraday snapshot', flush=True)
                continue
            print('STEP FAILED: ' + s, flush=True)
            return 1
        print('  done %.0fs' % (time.time() - t0), flush=True)
    out = os.path.join(ROOT, 'docs', 'index.html')
    print('DONE ' + out + ' ' + str(os.path.getsize(out)) + ' bytes', flush=True)
    return 0
sys.exit(main())
