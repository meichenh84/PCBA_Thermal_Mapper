# -*- coding: utf-8 -*-
import os

SRC = os.path.dirname(os.path.abspath(__file__))

def w(name, content):
    path = os.path.join(SRC, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Written {name}: {os.path.getsize(path)} bytes")

def r(name):
    with open(os.path.join(SRC, name), "r", encoding="utf-8") as f:
        return f.read()

def rep(content, old, new):
    if old in content:
        return content.replace(old, new, 1)
    else:
        print(f"WARNING: pattern not found")
        return content

print("Annotator starting...")
