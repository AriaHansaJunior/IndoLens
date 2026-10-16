import os
from pathlib import Path

emb_dir = Path("python/embeddings")
print("EMBEDDING DIRECTORY CONTENTS:")
for item in sorted(emb_dir.iterdir()):
    if item.is_dir():
        files = list(item.glob("*.npy"))
        print(f"Actor dir: {item.name} ({len(files)} .npy files)")
        for f in files[:5]:
            print(f"   -> {f.name}")
        if len(files) > 5:
            print(f"   ... and {len(files) - 5} more")
    else:
        print(f"File: {item.name}")
