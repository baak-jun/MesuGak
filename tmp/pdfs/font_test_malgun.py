from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
pdfmetrics.registerFont(TTFont('Malgun', r'C:\Windows\Fonts\malgun.ttf'))
pdfmetrics.registerFont(TTFont('MalgunBold', r'C:\Windows\Fonts\malgunbd.ttf'))
out = r'C:\Users\baak_jun\Documents\GitHub\MesuGak\tmp\pdfs\font-test-malgun.pdf'
c = canvas.Canvas(out)
c.setFont('MalgunBold', 20)
c.drawString(72, 760, '한글 PDF 글꼴 확인')
c.setFont('Malgun', 12)
c.drawString(72, 720, '볼린저밴드 수축과 확장, 투자판단 교육용 문서입니다.')
c.save()
print(out)