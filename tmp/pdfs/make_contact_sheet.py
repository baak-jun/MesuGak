from pathlib import Path
from PIL import Image, ImageDraw
folder = Path(r'C:\Users\baak_jun\Documents\GitHub\MesuGak\tmp\pdfs\mesugak_fsc_legal_interpretation_request_draft_v2')
files = sorted(folder.glob('page-*.png'))
thumbs=[]
for i, path in enumerate(files, 1):
    image=Image.open(path).convert('RGB')
    image.thumbnail((400, 566))
    page=Image.new('RGB', (420, 610), 'white')
    page.paste(image, ((420-image.width)//2, 28))
    ImageDraw.Draw(page).text((12, 5), f'Page {i}', fill='#102A43')
    thumbs.append(page)
sheet=Image.new('RGB', (840, 1830), '#E9EEF3')
for i, image in enumerate(thumbs):
    sheet.paste(image, ((i%2)*420, (i//2)*610))
out=folder/'contact-sheet.png'
sheet.save(out)
print(out)