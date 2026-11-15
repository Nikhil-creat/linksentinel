"""Tiny CNN for landing-page spoof detection. Lazy torch import; returns 0.0 if torch, Pillow or weights are absent."""
import io, os

WEIGHTS = os.getenv("CNN_WEIGHTS", "models/spoof_cnn.pt")
_model = None

def build():
    import torch.nn as nn
    return nn.Sequential(nn.Conv2d(3, 16, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2), nn.Conv2d(16, 32, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
                         nn.Conv2d(32, 64, 3, padding=1), nn.ReLU(), nn.AdaptiveAvgPool2d(1), nn.Flatten(), nn.Linear(64, 1))

def spoof_score(png: bytes) -> float:
    """P(visually spoofed login page) for a screenshot; 0.0 when unavailable."""
    global _model
    try:
        import torch
        from PIL import Image
        if _model is None:
            if not os.path.exists(WEIGHTS):
                return 0.0
            _model = build(); _model.load_state_dict(torch.load(WEIGHTS, map_location="cpu")); _model.eval()
        img = Image.open(io.BytesIO(png)).convert("RGB").resize((128, 128))
        x = torch.tensor(list(img.getdata()), dtype=torch.float32).view(128, 128, 3).permute(2, 0, 1)[None] / 255
        with torch.no_grad():
            return float(torch.sigmoid(_model(x))[0, 0])
    except Exception:
        return 0.0
