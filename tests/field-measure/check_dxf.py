#!/usr/bin/env python3
"""Validate a DXF with ezdxf and print a JSON summary.

Usage: check_dxf.py <file.dxf>
Prints {version, layers, counts, texts}; exits 1 if ezdxf.audit reports errors.
"""
import json
import re
import sys

import ezdxf

_U = re.compile(r"\\U\+([0-9A-Fa-f]{4})")


def decode(s):
    return _U.sub(lambda m: chr(int(m.group(1), 16)), s)


def main(argv):
    if len(argv) != 2:
        print("usage: check_dxf.py <file.dxf>", file=sys.stderr)
        return 2
    try:
        doc = ezdxf.readfile(argv[1])
    except (IOError, ezdxf.DXFError) as exc:
        print(f"cannot read DXF: {exc}", file=sys.stderr)
        return 1
    auditor = doc.audit()
    msp = doc.modelspace()
    result = {
        "version": doc.dxfversion,
        "layers": [layer.dxf.name for layer in doc.layers],
        "counts": {t: len(msp.query(t)) for t in ("LINE", "LWPOLYLINE", "TEXT", "CIRCLE")},
        "texts": [decode(e.dxf.text) for e in msp.query("TEXT")],
    }
    print(json.dumps(result, ensure_ascii=False))
    if auditor.has_errors:
        for err in auditor.errors:
            print(f"audit error {err.code}: {err.message}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
