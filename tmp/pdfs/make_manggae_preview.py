from PIL import Image
from pathlib import Path
folder=Path(r"C:\Users\baak_jun\Documents\GitHub\MesuGak\tmp\pdfs\manggae_indicator_class_preview")
im=Image.open(folder/'page-1.jpg')
im.thumbnail((430,610))
im.save(folder/'page-1-review.jpg',quality=48,optimize=True)