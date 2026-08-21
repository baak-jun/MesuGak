from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
    KeepTogether, HRFlowable
)

ROOT = Path(r'C:\Users\baak_jun\Documents\GitHub\MesuGak')
OUT = ROOT / 'output' / 'pdf' / 'manggae_indicator_class_fsc_legal_interpretation_request_draft.pdf'
OUT.parent.mkdir(parents=True, exist_ok=True)

pdfmetrics.registerFont(TTFont('Malgun', r'C:\Windows\Fonts\malgun.ttf'))
pdfmetrics.registerFont(TTFont('MalgunBold', r'C:\Windows\Fonts\malgunbd.ttf'))

NAVY = colors.HexColor('#102A43')
TEAL = colors.HexColor('#007C78')
LIGHT_TEAL = colors.HexColor('#EAF7F5')
INK = colors.HexColor('#1F2933')
MUTED = colors.HexColor('#52606D')
BORDER = colors.HexColor('#D9E2EC')
PALE = colors.HexColor('#F7FAFC')
AMBER = colors.HexColor('#FFF7E6')

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(
    name='CoverKicker', fontName='MalgunBold', fontSize=11, leading=16,
    textColor=TEAL, spaceAfter=12,
))
styles.add(ParagraphStyle(
    name='CoverTitle', fontName='MalgunBold', fontSize=23, leading=34,
    textColor=NAVY, spaceAfter=14,
))
styles.add(ParagraphStyle(
    name='CoverSub', fontName='Malgun', fontSize=11, leading=18,
    textColor=MUTED, spaceAfter=16,
))
styles.add(ParagraphStyle(
    name='H1K', fontName='MalgunBold', fontSize=16, leading=23,
    textColor=NAVY, spaceBefore=2, spaceAfter=8,
))
styles.add(ParagraphStyle(
    name='H2K', fontName='MalgunBold', fontSize=12.5, leading=19,
    textColor=NAVY, spaceBefore=10, spaceAfter=6,
))
styles.add(ParagraphStyle(
    name='BodyK', fontName='Malgun', fontSize=9.3, leading=15,
    textColor=INK, spaceAfter=5, wordWrap='CJK',
))
styles.add(ParagraphStyle(
    name='SmallK', fontName='Malgun', fontSize=8.1, leading=12.5,
    textColor=MUTED, wordWrap='CJK',
))
styles.add(ParagraphStyle(
    name='LabelK', fontName='MalgunBold', fontSize=8.2, leading=12,
    textColor=TEAL, wordWrap='CJK',
))
styles.add(ParagraphStyle(
    name='QuestionK', fontName='MalgunBold', fontSize=10.2, leading=16,
    textColor=INK, wordWrap='CJK',
))
styles.add(ParagraphStyle(
    name='NoteK', fontName='Malgun', fontSize=8.6, leading=14,
    textColor=INK, wordWrap='CJK',
))


def p(text, style='BodyK'):
    return Paragraph(text, styles[style])


def line(color=BORDER, width=0.6, space_before=2, space_after=8):
    return HRFlowable(width='100%', thickness=width, color=color,
                      spaceBefore=space_before, spaceAfter=space_after)


def field(label, value):
    table = Table([[p(label, 'LabelK'), p(value, 'BodyK')]], colWidths=[38*mm, 132*mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), LIGHT_TEAL),
        ('BACKGROUND', (1, 0), (1, 0), colors.white),
        ('BOX', (0, 0), (-1, -1), 0.55, BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.45, BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 7),
        ('RIGHTPADDING', (0, 0), (-1, -1), 7),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    return table


def card(label, value, fill=PALE):
    table = Table([[p(label, 'LabelK')], [p(value, 'NoteK')]], colWidths=[170*mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), fill),
        ('BOX', (0, 0), (-1, -1), 0.55, BORDER),
        ('LEFTPADDING', (0, 0), (-1, -1), 9),
        ('RIGHTPADDING', (0, 0), (-1, -1), 9),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
    ]))
    return table


def bullet(text):
    return Table([[p('-', 'LabelK'), p(text, 'BodyK')]], colWidths=[6*mm, 164*mm], hAlign='LEFT',
                 style=TableStyle([
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                    ('LEFTPADDING', (0,0), (-1,-1), 0),
                    ('RIGHTPADDING', (0,0), (-1,-1), 0),
                    ('TOPPADDING', (0,0), (-1,-1), 0),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 2),
                 ]))


def question(number, text):
    return Table([[p(str(number).zfill(2), 'LabelK'), p(text, 'QuestionK')]],
                 colWidths=[12*mm, 158*mm],
                 style=TableStyle([
                     ('BACKGROUND', (0,0), (0,0), LIGHT_TEAL),
                     ('BACKGROUND', (1,0), (1,0), colors.white),
                     ('BOX', (0,0), (-1,-1), 0.55, BORDER),
                     ('VALIGN', (0,0), (-1,-1), 'TOP'),
                     ('ALIGN', (0,0), (0,0), 'CENTER'),
                     ('LEFTPADDING', (0,0), (-1,-1), 8),
                     ('RIGHTPADDING', (0,0), (-1,-1), 8),
                     ('TOPPADDING', (0,0), (-1,-1), 8),
                     ('BOTTOMPADDING', (0,0), (-1,-1), 8),
                 ]))


def page_decor(canvas, doc):
    canvas.saveState()
    w, h = A4
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.45)
    canvas.line(20*mm, 13*mm, w-20*mm, 13*mm)
    canvas.setFont('Malgun', 7.3)
    canvas.setFillColor(MUTED)
    canvas.drawString(20*mm, 8*mm, '망개의 기지분 교실 - 금융위원회 법령해석 요청서 초안')
    canvas.drawRightString(w-20*mm, 8*mm, f'{doc.page} / 6')
    canvas.restoreState()


doc = SimpleDocTemplate(
    str(OUT), pagesize=A4, leftMargin=20*mm, rightMargin=20*mm,
    topMargin=18*mm, bottomMargin=20*mm,
    title='광고수익 기반 전 종목 기술지표 상태 해설 웹서비스 - 법령해석 요청서 초안',
    author='망치든개발자의 기술지표분석교실', subject='자본시장법상 투자자문업 및 유사투자자문업 해당 여부 질의 초안',
)

story = []

# Page 1: Cover
story += [Spacer(1, 18*mm), p('금융위원회 법령해석 요청서 초안', 'CoverKicker')]
story += [p('광고수익 기반 전 종목 기술지표 상태 해설 웹서비스의<br/>자본시장법상 투자자문업 또는 유사투자자문업 해당 여부', 'CoverTitle')]
story += [p('무료 공개 웹서비스에서 다수 종목의 기술지표 상태와 일반적 해석을 동일하게 제공할 때, 투자조언 및 대가성의 범위가 어디까지인지 확인하기 위한 질의서입니다.', 'CoverSub')]
story += [line(TEAL, 1.4, 4, 13)]
story += [card('서비스 개요', '망치든개발자의 기술지표분석교실(약칭: 망개의 기지분 교실)은 국내 상장 종목 전반을 고정된 기술적 조건으로 분석하여, 종목명과 코드 및 비가격형 기술지표 상태 해설을 무료 공개하려는 웹서비스입니다. 수익원은 화면 광고수익만을 예정하고 있습니다.', LIGHT_TEAL)]
story += [Spacer(1, 10)]
story += [card('질의의 핵심', '특정 종목을 식별할 수 있게 표시하되, 매수·매도·보유 등 투자판단 문구, 가격·차트·점수·순위·목표가·진입/청산 시점 및 개별화 기능을 모두 배제한 경우에도 자본시장법상 투자조언에 해당하는지 확인하고자 합니다.', PALE)]
story += [Spacer(1, 20)]
story += [field('신청인', '[신청인 성명 또는 법인명 입력]')]
story += [Spacer(1, 5)]
story += [field('작성일', '2026. 7. 14.  - 제출 전 실제 작성일로 수정')]
story += [Spacer(1, 5)]
story += [field('공개 여부', '법령해석은 공개 접수 대상이므로 즉시공개를 선택합니다.')]
story += [Spacer(1, 14)]
story += [p('제출 전 유의: 이 문서는 신청 내용 작성을 돕는 초안이며, 금융위원회의 최종 회신 또는 법률자문을 대체하지 않습니다.', 'SmallK')]
story += [PageBreak()]

# Page 2: form data
story += [p('1. 신청내용', 'H1K'), line()]
story += [field('요청 구분', '법령해석')]
story += [Spacer(1, 5)]
story += [field('제목', '광고수익 기반 전 종목 기술지표 상태 해설 웹서비스의 자본시장법상 투자자문업 또는 유사투자자문업 해당 여부')]
story += [Spacer(1, 5)]
story += [field('질의 동기', '기타')]
story += [Spacer(1, 5)]
story += [field('질의 동기 상세', '신청인은 현재 인허가 또는 신고 신청을 진행 중인 당사자가 아닙니다. 웹서비스 공개 전, 예정된 서비스 구조가 자본시장법상 투자자문업 또는 유사투자자문업에 해당하는지와 공개 가능한 정보의 경계를 확인하기 위하여 질의합니다.')]
story += [Spacer(1, 5)]
story += [field('해석 대상 법령', '자본시장과 금융투자업에 관한 법률 제6조 제7항(투자자문업), 제17조(투자자문업 등록), 제18조(유사투자자문업 신고), 제101조 제1항 및 같은 법 시행령 제102조 제1항')]
story += [Spacer(1, 16)]
story += [p('2. 법령해석 요청의 원인이 되는 구체적 사실관계', 'H1K'), line()]
story += [p('가. 서비스의 기본 운영 방식', 'H2K')]
story += [bullet('국내 상장 종목 전반을 대상으로 동일한 고정 규칙을 적용해 하루 1회, 장 마감 이후 기술지표 상태를 갱신하는 웹서비스를 계획하고 있습니다.')]
story += [bullet('이용자는 로그인, 유료 결제, 멤버십 가입 없이 동일한 내용을 볼 수 있습니다. 유료 구독, 프리미엄 화면, 종목별 유료 열람, 후원자 전용 콘텐츠, 제휴 수수료 또는 증권사 주문 유도 수수료는 운영하지 않을 예정입니다.')]
story += [bullet('예정된 수익원은 웹페이지에 표시되는 일반 광고수익뿐이며, 광고를 보지 않은 이용자와 광고를 본 이용자 사이에 분석 내용의 차이를 두지 않습니다.')]
story += [bullet('투자성향, 보유자산, 보유종목, 매수단가, 투자목적 등 개인 정보를 받거나 이용자별 결과를 다르게 제공하지 않습니다.')]
story += [Spacer(1, 5)]
story += [p('나. 이용자와의 상호작용 제한', 'H2K')]
story += [bullet('개별 종목에 대한 1:1 질의응답, 채팅 상담, 댓글 답변, DM 상담, 맞춤형 알림, 개인별 추천, 자동주문, 주문연동 및 계좌연동 기능을 제공하지 않습니다.')]
story += [bullet('표시 내용은 불특정 다수에게 동시에 일방향으로 제공하며, 특정 이용자의 상황을 고려하여 투자판단을 제시하지 않습니다.')]
story += [PageBreak()]

# Page 3 public scope
story += [p('3. 공개 화면에서 표시하려는 정보와 명시적으로 배제하는 정보', 'H1K'), line()]
story += [p('가. 표시하려는 정보', 'H2K')]
story += [bullet('종목명과 종목코드를 식별 정보로 표시합니다. 이는 특정 종목을 예로 들어 기술지표의 읽는 방법을 설명하기 위한 것입니다.')]
story += [bullet('볼린저밴드의 수축·확장, 이동평균선의 중립·정렬 상태, RSI의 중립·과열·침체 구간, 거래량 확인 여부, 일목균형표의 구름대 상대 위치 등 정성적 상태 설명을 제공합니다.')]
story += [bullet('예: "밴드 수축 뒤 확장 조건", "거래량 확인", "추세가 중립인 구간", "과열 또는 침체 여부를 추가 확인할 구간"처럼 기술지표의 일반적 의미와 상반 신호 또는 무효화 가능성을 함께 설명합니다.')]
story += [bullet('모든 종목에 동일한 형식의 해설을 제공하며, 화면에서 특정 종목을 더 유망하거나 우선적인 종목으로 보이게 하는 순위, 추천 배지 또는 강조 표시를 두지 않습니다.')]
story += [Spacer(1, 7)]
story += [p('나. 공개 화면에서 배제하는 정보', 'H2K')]
exclude_rows = [
    ['투자판단 문구', '매수, 매도, 보유, 추천, 비추천, 진입, 청산, 손절, 목표가, 적정가, 수익 기대 등'],
    ['가격 및 시세 정보', '현재가, 종가, 시가, 고가, 저가, 등락률, 거래량 원수치, 호가, 체결 정보 등'],
    ['차트 및 원자료', '캔들 차트, 가격 그래프, 원시 기술지표 수치, 계산식 결과값, 시계열 데이터 등'],
    ['비교 및 순위', '종합 점수, 랭킹, 매수 후보 목록, 시장 대비 수익률, 목표 수익률, 우선순위 등'],
    ['시점 및 실행 정보', '언제 사거나 팔아야 하는지, 주문 수량·방법·가격·시기, 자동주문 또는 알림 등'],
]
t = Table([[p('구분', 'LabelK'), p('배제 범위', 'LabelK')]] + [[p(a, 'NoteK'), p(b, 'NoteK')] for a,b in exclude_rows], colWidths=[42*mm, 128*mm])
t.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), LIGHT_TEAL),
    ('BACKGROUND', (0,1), (-1,-1), colors.white),
    ('BOX', (0,0), (-1,-1), 0.55, BORDER),
    ('INNERGRID', (0,0), (-1,-1), 0.4, BORDER),
    ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ('LEFTPADDING', (0,0), (-1,-1), 7),
    ('RIGHTPADDING', (0,0), (-1,-1), 7),
    ('TOPPADDING', (0,0), (-1,-1), 6),
    ('BOTTOMPADDING', (0,0), (-1,-1), 6),
]))
story += [t]
story += [Spacer(1, 12)]
story += [card('설명 목적', '해당 화면은 특정 종목의 취득 또는 처분을 유도하기 위한 것이 아니라, 기술지표 조건들이 동시에 나타날 때 일반적으로 어떤 점을 점검하는지를 학습적으로 설명하기 위한 것입니다. 상승 가능성뿐 아니라 상반 신호, 실패 가능성, 해석의 한계를 함께 고지합니다.', AMBER)]
story += [PageBreak()]

# Page 4 questions
story += [p('4. 질의 요지', 'H1K'), line()]
story += [p('아래 사실관계를 전제로 자본시장법상 해석을 요청합니다.', 'BodyK'), Spacer(1, 4)]
story += [question(1, '종목명 및 종목코드를 표시하면서 전 종목에 대한 정성적 기술지표 상태와 일반적 해설을 동일하게 공개하는 행위가, 가격·차트·점수·순위·매수·매도·보유·목표가·진입 또는 청산 시점 등을 전혀 제시하지 않는 경우에도 금융투자상품의 가치 또는 투자판단에 관한 조언으로서 투자자문업 또는 유사투자자문업의 "투자조언"에 해당하는지요?')]
story += [Spacer(1, 8)]
story += [question(2, '질의 1의 서비스가 투자조언에 해당한다고 보더라도, 모든 이용자에게 무상으로 동일한 내용을 제공하고 운영자가 광고수익만 얻는 경우, 광고수익이 자본시장법 시행령 제102조 제1항의 "일정한 대가"에 해당하여 유사투자자문업 신고가 필요한지요?')]
story += [Spacer(1, 8)]
story += [question(3, '특정 종목의 식별 정보와 함께 "볼린저밴드 수축 뒤 확장", "거래량 확인", "이동평균선 중립", "RSI 과열 여부 확인" 등 기술지표 상태를 설명하는 행위가, 매수·매도·보유 의견이나 취득·처분의 방법·수량·가격·시기 제시와 구별되는지요? 구별 판단에 중요한 요소가 있다면 제시해 주시기 바랍니다.')]
story += [Spacer(1, 8)]
story += [question(4, '질의의 서비스 구조가 투자자문업 또는 유사투자자문업에 해당하지 않기 위해 추가로 제외하거나 제한해야 할 표현, 기능, 수익 구조 또는 이용자 상호작용이 있다면 구체적으로 알려주시기 바랍니다.')]
story += [Spacer(1, 15)]
story += [p('질의 범위에 관한 보충', 'H2K')]
story += [p('본 질의는 자본시장법상 영업 분류와 신고 필요 여부에 관한 것입니다. 시세·차트 등 원천정보의 이용허락, 재배포 또는 계약상 제한은 별도의 데이터 권리 및 계약 문제로서, 해당 정보 제공처와 별도로 확인할 예정입니다.', 'BodyK')]
story += [PageBreak()]

# Page 5 interpretation
story += [p('5. 대립되는 의견 및 이유', 'H1K'), line()]
story += [card('갑설 - 투자조언에 해당할 수 있다는 견해', '특정 종목을 식별한 상태에서 기술지표를 해석하면, 명시적 매수·매도 문구가 없어도 일반 투자자가 특정 종목의 매수·매도 판단에 활용할 가능성이 있으므로 금융투자상품의 가치 또는 투자판단에 대한 조언으로 볼 여지가 있다는 견해입니다.', PALE)]
story += [Spacer(1, 8)]
story += [card('을설 - 투자조언과 구별될 수 있다는 견해', '표현과 기능이 기술지표의 일반적 교육·설명에 한정되고, 투자판단을 결론으로 제시하지 않으며, 가격·차트·점수·순위·행동 유도와 개인화가 모두 배제되어 있고 모든 이용자에게 동일하게 무상 제공된다면, 투자조언 또는 이를 업으로 하는 행위와 구별될 수 있다는 견해입니다.', LIGHT_TEAL)]
story += [Spacer(1, 16)]
story += [p('6. 신청인의 의견', 'H1K'), line()]
story += [bullet('신청인은 서비스가 특정 종목의 취득·처분을 권유하거나 그 방법·수량·가격·시기를 제시하는 구조가 아니므로, 투자판단에 관한 조언으로 보기 어렵다고 생각합니다.')]
story += [bullet('특히 종합 점수, 등급, 순위, 추천 표시, 목표가, 매수 후보 목록, 현재 가격 및 차트를 모두 배제하고, 해석 문구에 위험 신호와 한계를 함께 포함할 예정입니다.')]
story += [bullet('다만 종목 식별 정보와 기술지표 상태의 결합만으로도 투자조언으로 평가될 가능성이 있는지 불명확하므로, 구체적 판단 기준을 공식적으로 확인하고자 합니다.')]
story += [bullet('질의 1에서 투자조언에 해당한다고 판단되더라도, 서비스는 유료회원제나 개별 대가를 전혀 받지 않고 광고수익만을 예정하므로, 광고수익만으로 유사투자자문업 신고 대상이 되는지 명확한 해석을 요청합니다.')]
story += [Spacer(1, 12)]
story += [card('운영상 확약', '법령해석 회신 전에는 실제 종목을 식별 가능한 상태로 공개하지 않고, 일반적인 기술지표 교육 콘텐츠만을 공개합니다. 회신 내용에 따라 문구·기능·수익 구조를 수정하고 필요한 신고 또는 등록 절차를 이행하겠습니다.', AMBER)]
story += [PageBreak()]

# Page 6 sources/checklist
story += [p('7. 참고자료 및 별도 확인 사항', 'H1K'), line()]
story += [p('가. 참고자료', 'H2K')]
refs = [
    '금융위원회 법령해석 회신문 210147 - 온라인 방송을 통한 투자정보 제공과 유사투자자문업 신고 필요 여부',
    '금융위원회 2024. 8. 20. 보도자료 - 유사투자자문업의 양방향 채널 운영 제한 관련 규정 정비 안내',
    '한국투자증권 Open API 제휴 안내 - 제3자 서비스에서 시세 API 활용 시 KRX 등 정보이용계약 필요 여부 확인 안내',
]
for item in refs:
    story += [bullet(item)]
story += [Spacer(1, 6)]
story += [p('참고 링크', 'H2K')]
links = [
    'https://better.fsc.go.kr/fsc_new/replyCase/LawreqDetail.do?lawreqIdx=3509&muGpNo=75&muNo=171&stNo=11',
    'https://www.fsc.go.kr/no010101/82887?curPage=4&srchBeginDt=2024-08-01&srchCtgry=&srchEndDt=2024-08-31&srchKey=sj&srchText=',
    'https://apiportal.koreainvestment.com/provider-info',
]
for url in links:
    story += [p(url, 'SmallK')]
story += [Spacer(1, 10)]
story += [p('나. 데이터 권리 별도 확인 문안', 'H2K')]
story += [card('정보 제공처에 별도 문의할 문안', '당사는 귀사 또는 제휴 경로로 취득한 시장정보를 바탕으로 가격·차트·원시 지표·시계열 수치를 공개하지 않고, 특정 종목별 기술지표 상태에 관한 정성적 해설만을 무료 웹페이지에 제공하려 합니다. 광고수익이 발생하는 공개 웹서비스에서 이러한 파생 해설의 공개가 정보이용계약 또는 재배포 제한에 해당하는지, 필요한 계약 또는 승인 절차가 무엇인지 안내를 요청드립니다.', PALE)]
story += [Spacer(1, 12)]
story += [p('다. 제출 전 확인 목록', 'H2K')]
checks = [
    '신청인, 연락처, 실제 서비스명 및 작성일을 입력했는지',
    '유료회원제, 맞춤형 조언, 1:1 질의응답, 주문 연동이 없다는 사실관계가 실제 운영안과 같은지',
    '공개 화면에서 배제할 표현과 기능이 실제 제품 사양서 및 광고 문구에도 반영되었는지',
    '시장정보 제공처 또는 거래소에 데이터 이용허락 및 재배포 가능 여부를 별도로 문의했는지',
    '법령해석 회신 전에는 실제 종목 식별형 공개 화면을 열지 않는지',
]
for item in checks:
    story += [bullet('[ ] ' + item)]
story += [Spacer(1, 10)]
story += [p('제출 팁: 첨부파일에는 공개 예정 화면의 비식별 와이어프레임, 금지 문구 목록, 서비스 이용 흐름도를 넣으면 사실관계가 더 명확해집니다. 실제 시세·차트·종목별 추천 화면은 첨부하지 않는 편이 안전합니다.', 'SmallK')]

doc.build(story, onFirstPage=page_decor, onLaterPages=page_decor)
print(OUT)