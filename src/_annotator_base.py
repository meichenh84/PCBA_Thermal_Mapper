import os

SRC = os.path.dirname(os.path.abspath(__file__))

def write_file(name, content):
    path = os.path.join(SRC, name)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    sz = os.path.getsize(path)
    print(f'Written {name}: {sz} bytes')

print('Annotator ready')
