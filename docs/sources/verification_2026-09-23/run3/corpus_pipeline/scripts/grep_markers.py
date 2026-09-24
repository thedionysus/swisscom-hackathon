import re, sys, os
D = "<scratchpad>/wt-run3/docs/sources/verification_2026-09-23/run3/agent_reports"
pat = re.compile(sys.argv[1], re.I)
for f in ["run3-a.md", "run3-b.md", "run3-c.md", "run3-d.md", "run3-e.md"]:
    for n, line in enumerate(open(os.path.join(D, f), encoding="utf-8"), 1):
        for m in pat.finditer(line):
            s = max(0, m.start() - int(sys.argv[2] if len(sys.argv) > 2 else 150)); e = m.end() + int(sys.argv[2] if len(sys.argv) > 2 else 150)
            print(f"{f}:{n}: ...{line[s:e].strip()}...")
