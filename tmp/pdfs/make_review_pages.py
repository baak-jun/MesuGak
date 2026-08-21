from PIL import Image
from pathlib import Path
folder=Path(r'C:\Users\baak_jun\Documents\GitHub\MesuGak\tmp\pdfs\mesugak_fsc_legal_interpretation_request_draft_preview')
for num in (2,3,4,5,6):
    im=Image.open(folder/f'page-{num}.jpg')
    im.thumbnail((430,610))
    im.save(folder/f'page-{num}-review.jpg',quality=48,optimize=True)