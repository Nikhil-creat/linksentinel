"""Train the spoof CNN. Put screenshots in data/safe/*.png and data/spoof/*.png, then: python scripts/train_cnn.py"""
import torch, torch.nn as nn
from torchvision import datasets, transforms
from app.services.cnn import build

ds = datasets.ImageFolder("data", transforms.Compose([transforms.Resize((128, 128)), transforms.ToTensor()]))
dl = torch.utils.data.DataLoader(ds, batch_size=32, shuffle=True)
m, loss = build(), nn.BCEWithLogitsLoss()
opt = torch.optim.Adam(m.parameters(), 1e-3)
for ep in range(10):
    for x, y in dl:
        opt.zero_grad(); l = loss(m(x).squeeze(1), y.float()); l.backward(); opt.step()
    print("epoch", ep, float(l))
torch.save(m.state_dict(), "models/spoof_cnn.pt")  # class index: safe=0, spoof=1 (alphabetical)
