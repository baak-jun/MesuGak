from pathlib import Path
from PIL import Image, ImageDraw
import re
folder=Path(r'C:\Users\baak_jun\Documents\GitHub\MesuGak\tmp\pdfs\mesugak_fsc_legal_interpretation_request_draft_preview')
files=sorted((p for p in folder.glob('page-*.jpg') if re.fullmatch(r'page-\d+\.jpg', p.name)), key=lambda p:int(re.search(r'\d+',p.stem).group()))
assert len(files)==6, [p.name for p in files]
thumbs=[]
for i,path in enumerate(files,1):
    im=Image.open(path).convert('RGB')
    im.thumbnail((150,215))
    card=Image.new('RGB',(160,235),'white')
    card.paste(im,((160-im.width)//2,18))
    ImageDraw.Draw(card).text((6,3),str(i),fill='#102A43')
    thumbs.append(card)
sheet=Image.new('RGB',(320,705),'#E9EEF3')
for i,card in enumerate(thumbs):
    sheet.paste(card,((i%2)*160,(i//2)*235))
out=folder/'contact-small-exact.jpg'
sheet.save(out,quality=28,optimize=True)