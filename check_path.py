import sys
print("Python paths:")
for i, path in enumerate(sys.path, 1):
    print(f"{i}. {path}")
