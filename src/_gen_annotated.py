# -*- coding: utf-8 -*-
import os
import sys

BASE = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))

def write_file(filename, content):
    path = os.path.join(BASE, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Written {filename}: {len(content)} chars")
