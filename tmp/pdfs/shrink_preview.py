from PIL import Image
src=r'C:\Users\baak_jun\Documents\GitHub\MesuGak\tmp\pdfs\mesugak_fsc_legal_interpretation_request_draft_preview\page-1.jpg'
out=r'C:\Users\baak_jun\Documents\GitHub\MesuGak\tmp\pdfs\mesugak_fsc_legal_interpretation_request_draft_preview\page-1-small.jpg'
im=Image.open(src)
im.thumbnail((360, 510))
im.save(out, quality=45, optimize=True)