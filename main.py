"""
FastAPI Backend — Colorisation CGAN
====================================
Lance avec : uvicorn main:app --reload --port 8000
"""

import io
import os
import time
import base64
import sqlite3
from datetime import datetime
from contextlib import contextmanager
from huggingface_hub import hf_hub_download
import torch
import torch.nn as nn
import torchvision.transforms as T
import numpy as np
from PIL import Image

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

# ─── Config ───────────────────────────────────────────────────────────────────
DEVICE     = "cuda" if torch.cuda.is_available() else "cpu"
IMG_SIZE   = 256
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))  # ← abspath = toujours correct
MODEL_PATH = hf_hub_download(
    repo_id="amelakh/best_cgan_V1",
    filename="best_cgan_V1.pth"
)
DB_PATH = "/tmp/history.db"
app = FastAPI(title="Colorisation CGAN API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Architecture CGAN (copie exacte du notebook) ────────────────────────────
class ConvNormAct2d(nn.Module):
    def __init__(self, in_chan, out_chan):
        super().__init__()
        self.model = nn.Sequential(
            nn.Conv2d(in_chan, out_chan, 4, 2, 1),
            nn.BatchNorm2d(out_chan),
            nn.LeakyReLU(0.2),
        )
    def forward(self, x): return self.model(x)

class ConvTransNormAct2d(nn.Module):
    def __init__(self, in_chan, out_chan):
        super().__init__()
        self.model = nn.Sequential(
            nn.ConvTranspose2d(in_chan, out_chan, 4, 2, 1),
            nn.BatchNorm2d(out_chan),
            nn.GELU(),
        )
    def forward(self, x): return self.model(x)

class Encoder(nn.Module):
    def __init__(self, img_chan, n_chans):
        super().__init__()
        stem = nn.Sequential(
            nn.Conv2d(img_chan, n_chans[0], 5, 1, 2),
            nn.LeakyReLU(0.2),
        )
        layers = [stem]
        for i in range(len(n_chans) - 1):
            layers.append(ConvNormAct2d(n_chans[i], n_chans[i + 1]))
        self.model = nn.ModuleList(layers)

    def forward(self, x):
        state, h = [], x
        for layer in self.model:
            h = layer(h)
            state.append(h)
        return h, list(reversed(state[:-1]))

class Decoder(nn.Module):
    def __init__(self, n_chans):
        super().__init__()
        layers = []
        for i in range(len(n_chans) - 1):
            in_c = n_chans[i] if i == 0 else n_chans[i] * 2
            layers.append(ConvTransNormAct2d(in_c, n_chans[i + 1]))
        self.model = nn.ModuleList(layers)
        self.out_conv = nn.Sequential(nn.Conv2d(n_chans[-1], 3, 1), nn.Tanh())

    def forward(self, x, state):
        h = x
        for i, layer in enumerate(self.model):
            if i > 0 and (i - 1) < len(state):
                h = torch.cat([state[i - 1], h], dim=1)
            h = layer(h)
        return self.out_conv(h)

class UNet(nn.Module):
    def __init__(self, enc_chans, dec_chans):
        super().__init__()
        self.encoder = Encoder(1, enc_chans)
        self.decoder = Decoder(dec_chans)
    def forward(self, x):
        h, state = self.encoder(x)
        return self.decoder(h, state)

# ─── Chargement du modèle ─────────────────────────────────────────────────────
def load_model():
    enc_chans = [64, 128, 256, 512, 512]
    dec_chans = list(reversed(enc_chans))
    gen = UNet(enc_chans, dec_chans)

    if not os.path.exists(MODEL_PATH):
        raise RuntimeError(f"Modèle introuvable : {MODEL_PATH}")

    ckpt = torch.load(MODEL_PATH, map_location=DEVICE, weights_only=False)

    # Les clés sont de la forme "generator.module.encoder..."
    # → on garde uniquement celles du générateur et on enlève "generator.module."
    state_dict = {
        k[len("generator.module."):]: v
        for k, v in ckpt.items()
        if k.startswith("generator.module.")
    }

    if not state_dict:
        raise RuntimeError("Aucune clé 'generator.module.' trouvée dans le checkpoint !")

    gen.load_state_dict(state_dict, strict=True)
    gen.eval()
    return gen.to(DEVICE)
GENERATOR = None
MODEL_OK  = False

try:
    GENERATOR = load_model()
    MODEL_OK  = True
    print(f"✅ Modèle chargé sur {DEVICE}")
except Exception as e:
    print(f"⚠️  Erreur chargement modèle : {e}")
    import traceback
    traceback.print_exc()

# ─── Base de données SQLite ───────────────────────────────────────────────────
def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                filename    TEXT    NOT NULL,
                created_at  TEXT    NOT NULL,
                duration_ms REAL    NOT NULL,
                width       INTEGER NOT NULL,
                height      INTEGER NOT NULL,
                input_b64   TEXT    NOT NULL,
                output_b64  TEXT    NOT NULL
            )
        """)
        con.commit()

init_db()

@contextmanager
def get_db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
    finally:
        con.close()

# ─── Helpers image ────────────────────────────────────────────────────────────
gray_transform = T.Compose([
    T.Resize((IMG_SIZE, IMG_SIZE)),
    T.Grayscale(num_output_channels=1),
    T.ToTensor(),
    T.Normalize([0.5], [0.5]),
])

def pil_to_b64(img: Image.Image, fmt="PNG") -> str:
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return base64.b64encode(buf.getvalue()).decode()

def pil_to_bytes(img: Image.Image, fmt="PNG") -> bytes:
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()

def run_colorize(pil_img: Image.Image) -> tuple[Image.Image, float]:
    """Retourne (image colorisée, durée en ms)"""
    t0 = time.time()
    tensor = gray_transform(pil_img).unsqueeze(0).to(DEVICE)
    with torch.no_grad():
        out = GENERATOR(tensor).squeeze(0)
    out = (out * 0.5 + 0.5).clamp(0, 1)
    result = Image.fromarray((out.permute(1, 2, 0).cpu().numpy() * 255).astype(np.uint8))
    result = result.resize(pil_img.size, Image.LANCZOS)
    duration_ms = (time.time() - t0) * 1000
    return result, duration_ms

# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "device": DEVICE, "model_loaded": MODEL_OK}


@app.post("/colorize")
async def colorize(file: UploadFile = File(...)):
    """Colorise une image et sauvegarde dans l'historique."""
    if not MODEL_OK:
        raise HTTPException(503, "Modèle non chargé")

    # Lire l'image
    data = await file.read()
    try:
        pil_img = Image.open(io.BytesIO(data)).convert("RGB")
    except Exception:
        raise HTTPException(400, "Fichier image invalide")

    # Inférence
    result, duration_ms = run_colorize(pil_img)
    w, h = pil_img.size

    # Sauvegarder dans SQLite
    with get_db() as con:
        con.execute(
            """INSERT INTO history (filename, created_at, duration_ms, width, height, input_b64, output_b64)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                file.filename or "image.jpg",
                datetime.now().isoformat(timespec="seconds"),
                round(duration_ms, 1),
                w, h,
                pil_to_b64(pil_img),
                pil_to_b64(result),
            )
        )
        con.commit()

    return {
        "output_b64": pil_to_b64(result),
        "duration_ms": round(duration_ms, 1),
        "width": w,
        "height": h,
    }


@app.get("/history")
def get_history(limit: int = 20):
    """Retourne les N dernières colorisations."""
    with get_db() as con:
        rows = con.execute(
            "SELECT id, filename, created_at, duration_ms, width, height, input_b64, output_b64 "
            "FROM history ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


@app.delete("/history/{item_id}")
def delete_history_item(item_id: int):
    """Supprime un élément de l'historique."""
    with get_db() as con:
        con.execute("DELETE FROM history WHERE id = ?", (item_id,))
        con.commit()
    return {"deleted": item_id}


@app.delete("/history")
def clear_history():
    """Vide tout l'historique."""
    with get_db() as con:
        con.execute("DELETE FROM history")
        con.commit()
    return {"cleared": True}


@app.get("/stats")
def get_stats():
    """Statistiques globales."""
    with get_db() as con:
        row = con.execute("""
            SELECT
                COUNT(*)                         AS total,
                ROUND(AVG(duration_ms), 1)        AS avg_ms,
                ROUND(MIN(duration_ms), 1)        AS min_ms,
                ROUND(MAX(duration_ms), 1)        AS max_ms,
                COUNT(DISTINCT DATE(created_at))  AS active_days
            FROM history
        """).fetchone()
    return dict(row)


@app.get("/history/{item_id}/download")
def download_output(item_id: int):
    """Télécharge l'image colorisée d'un item."""
    with get_db() as con:
        row = con.execute(
            "SELECT output_b64, filename FROM history WHERE id = ?", (item_id,)
        ).fetchone()
    if not row:
        raise HTTPException(404, "Item introuvable")
    img_bytes = base64.b64decode(row["output_b64"])
    name = os.path.splitext(row["filename"])[0] + "_colorized.png"
    return StreamingResponse(
        io.BytesIO(img_bytes),
        media_type="image/png",
        headers={"Content-Disposition": f'attachment; filename="{name}"'}
    )