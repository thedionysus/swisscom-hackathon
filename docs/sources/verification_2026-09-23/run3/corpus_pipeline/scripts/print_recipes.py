import os, re
D = "<scratchpad>/wt-run3/docs/sources/verification_2026-09-23/run3/agent_reports"
for f in ["run3-a.md", "run3-b.md", "run3-c.md", "run3-d.md", "run3-e.md"]:
    lines = open(os.path.join(D, f), encoding="utf-8").read().splitlines()
    for i, line in enumerate(lines):
        if re.search(r"site recipe", line, re.I):
            block = [line]
            for nxt in lines[i + 1:i + 14]:
                if nxt.startswith("#") or nxt.startswith("|"):
                    break
                block.append(nxt)
            print(f"--- {f}:{i+1}")
            for b in block:
                if b.strip():
                    print("   ", b[:700])
