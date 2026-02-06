import os
path = os.path.join(os.path.dirname(__file__), "toast.py")
with open(path, "r", encoding="utf-8") as fin:
    original = fin.read()
print("Read", len(original), "chars from toast.py")
