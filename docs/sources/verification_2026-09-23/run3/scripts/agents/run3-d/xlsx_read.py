#!/usr/bin/env python3
"""Minimal XLSX reader (no openpyxl): python3 xlsx_read.py file.xlsx [maxrows]"""
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
fn = sys.argv[1]
maxrows = int(sys.argv[2]) if len(sys.argv) > 2 else 8
z = zipfile.ZipFile(fn)
shared = []
if "xl/sharedStrings.xml" in z.namelist():
    root = ET.fromstring(z.read("xl/sharedStrings.xml"))
    for si in root.findall("m:si", NS):
        shared.append("".join(t.text or "" for t in si.iter("{%s}t" % NS["m"])))
wb = ET.fromstring(z.read("xl/workbook.xml"))
names = [s.get("name") for s in wb.find("m:sheets", NS)]
sheets = sorted([n for n in z.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml", n)],
                key=lambda s: int(re.findall(r"\d+", s)[0]))
for name, path in zip(names, sheets):
    root = ET.fromstring(z.read(path))
    rows = []
    for row in root.iter("{%s}row" % NS["m"]):
        vals = []
        for c in row.findall("m:c", NS):
            v = c.find("m:v", NS)
            t = c.get("t")
            if v is None:
                isv = c.find("m:is", NS)
                vals.append("".join(x.text or "" for x in isv.iter("{%s}t" % NS["m"])) if isv is not None else None)
            elif t == "s":
                vals.append(shared[int(v.text)])
            else:
                vals.append(v.text)
        rows.append(vals)
    nonempty = [r for r in rows if any(x not in (None, "") for x in r)]
    print(f"sheet {name!r}: rows={len(rows)} non-empty={len(nonempty)}")
    for r in nonempty[:maxrows]:
        print("   ", r[:12])
    if nonempty:
        print("   last:", nonempty[-1][:12])
    links = [x for r in rows for x in r if isinstance(x, str) and ("http" in x or "www." in x)]
    print(f"   cells with web links: {len(links)} {links[:3]}")
