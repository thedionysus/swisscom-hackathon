#!/usr/bin/env python3
"""Minimal XLSX reader (zipfile + XML, no openpyxl).

Usage: xlsx_peek.py FILE [N_ROWS] [REGEX]
Prints sheet names, row counts, the first N rows, and how many rows match REGEX.
"""
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}


def col_idx(ref):
    letters = re.match(r"([A-Z]+)", ref).group(1)
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def main():
    path = sys.argv[1]
    nrows = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    rx = sys.argv[3] if len(sys.argv) > 3 else None
    z = zipfile.ZipFile(path)
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in root.findall("m:si", NS):
            shared.append("".join(t.text or "" for t in si.iter("{%s}t" % NS["m"])))
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    relmap = {r.get("Id"): r.get("Target") for r in rels}
    for sh in wb.find("m:sheets", NS):
        name = sh.get("name")
        rid = sh.get("{%s}id" % NS["r"])
        target = relmap[rid].lstrip("/")
        if not target.startswith("xl/"):
            target = "xl/" + target
        root = ET.fromstring(z.read(target))
        rows = []
        for row in root.iter("{%s}row" % NS["m"]):
            vals = {}
            for c in row.findall("m:c", NS):
                v = c.find("m:v", NS)
                t = c.get("t")
                if t == "inlineStr":
                    txt = "".join(x.text or "" for x in c.iter("{%s}t" % NS["m"]))
                elif v is None:
                    continue
                elif t == "s":
                    txt = shared[int(v.text)]
                else:
                    txt = v.text
                vals[col_idx(c.get("r"))] = txt
            if vals:
                rows.append([vals.get(i, "") for i in range(max(vals) + 1)])
        print(f"sheet {name!r}: {len(rows)} rows")
        for r in rows[:nrows]:
            print("   ", r[:14])
        if rx:
            hits = [r for r in rows if any(re.search(rx, str(c), re.I) for c in r)]
            print(f"   rows matching {rx!r}: {len(hits)}")
            for r in hits[:3]:
                print("     ", r[:14])


if __name__ == "__main__":
    main()
