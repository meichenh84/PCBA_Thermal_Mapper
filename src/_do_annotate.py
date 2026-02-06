# -*- coding: utf-8 -*-
import os

SRC = os.path.dirname(os.path.abspath(__file__))

def w(name, content):
    path = os.path.join(SRC, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Written {name}: {os.path.getsize(path)} bytes")

