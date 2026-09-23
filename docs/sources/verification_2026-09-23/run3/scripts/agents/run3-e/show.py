"""python3 show.py SPEC [SPEC ...]
SPEC = file::text::N  | file::links::regex | file::grep::kw1|kw2 (each kw separated by ';;')
Runs h.py helpers over several saved files without shell loops."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h, re
for spec in sys.argv[1:]:
    parts = spec.split('::')
    fn, mode = parts[0], parts[1]
    arg = parts[2] if len(parts) > 2 else ''
    print(f'##### {fn} [{mode}] {arg}')
    if mode == 'text':
        print(h.main_text(fn)[:int(arg or 1500)])
    elif mode == 'links':
        seen = set()
        for x, t in h.links(fn, arg or None):
            if (x, t) in seen:
                continue
            seen.add((x, t))
            print('  ', x, '|', t)
    elif mode == 'grep':
        txt = h.main_text(fn)
        for kw in arg.split(';;'):
            for m in list(re.finditer(kw, txt, re.I))[:2]:
                print(f'  [{kw}]', txt[max(0, m.start() - 180):m.end() + 180])
    print()
