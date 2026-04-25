import os
import torch

MODEL_PATH = r"C:\Users\hp\Documents\Semester 2\DL\colorization_app\backend\model\best_cgan.pth"

print(f"Fichier existe : {os.path.exists(MODEL_PATH)}")

ckpt = torch.load(MODEL_PATH, map_location="cpu", weights_only=False)

if isinstance(ckpt, dict):
    print(f"Clés : {list(ckpt.keys())}")
    for k, v in ckpt.items():
        if isinstance(v, dict):
            sub_keys = list(v.keys())
            print(f"  [{k}] → {len(sub_keys)} clés, ex: {sub_keys[:3]}")
        else:
            print(f"  [{k}] → {type(v)}")
else:
    print(f"Type direct : {type(ckpt)}")