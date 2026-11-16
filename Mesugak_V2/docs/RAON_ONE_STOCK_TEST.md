# Raon 종목 1개 의견 테스트

2026-10-22: 기존 분석을 바탕으로 별도 의견을 요청하는 운영자용 로컬 도구.
공개 UI·자동매매·배포·스케줄과 연결하지 않는다.

## 키

`functions/.env.raon`에 `RAON_API_KEY=발급받은키`를 저장한다.
기존 `.gitignore`의 `.env.*` 규칙으로 제외된다. 프론트엔드/VITE 변수에 넣지 않는다.
키 값은 요청의 Authorization 헤더에만 사용하고 결과 파일에 저장하지 않는다.

## 실행 (저장소 루트)

```powershell
# 준비만: 종목 상세 1건 조회, 전송할 자료 저장
python Mesugak_V2/functions/jobs/ask_raon.py --code 005930
# 저장된 상세 자료로 정확히 한 번 요청
python Mesugak_V2/functions/jobs/ask_raon.py --input Mesugak_V2/runtime/raon/<실행폴더>/analysis.json --send
```

Firestore에 해당 종목이 없으면 서버의 상세 분석 JSON을 `--input`으로 지정한다.
공개 요약에는 전체 지표가 없어 입력으로 사용하지 않는다.
매 실행 결과는 `runtime/raon/<UTC시각>/`에 별도로 보존한다.
`request.json`은 실제 요청, `analysis.json`은 선택된 분석 자료,
`result.json`은 답변·토큰 사용량·기준일, `opinion.md`는 읽기용 답변이다.
모델의 내부 추론은 보관하지 않는다. 계좌·보유종목·주문은 조회하지 않는다.

## 자료와 해석

최근 최대 130개 일봉의 모든 저장 지표(일목, MA5/20/60/120, 볼린저,
RSI, 거래량), 점수 구성·조건·위험 신호·있는 경우 재무 참고값을 전달한다.
입력 상한은 128 KiB, 출력 한도는 추론 포함 8192 토큰이다.
기준일을 명시하고 5~20거래일의 조건부 상승/횡보/하락 시나리오를 요청한다.
종합 점수는 확률이 아니며 최신 뉴스·장중 시세를 추가 조회하지 않는다.
모델 답변은 검증된 예측이 아니므로 수치와 근거를 원자료와 대조한다.

## 비용·실패 경계

- `--input`: Firebase 호출 0. `--code`: 상세 문서 get 1회, 쓰기 0.
- 클라우드 저장·Functions·스케줄 추가 0. 응답 전송량은 상세 문서 1건 크기.
- `--send`에서 Raon 요청 1회, 자동 재시도 0. 준비 모드는 Raon 호출 0.
- 공식 문서상 현재 프리뷰 모델 요금 0원. 조직별 RPM/토큰 한도 적용.
- 429/402/타임아웃/빈 답변/출력 잘림은 실패 처리하며 반복 요청하지 않는다.
- 모델·요금 정책은 변경될 수 있으므로 대량/정기 실행 전에 다시 확인한다.

문서: [시작하기](https://raon-mini.krafton.ai/ko/docs),
[Chat Completions](https://raon-mini.krafton.ai/ko/docs/chat-completions),
[추론](https://raon-mini.krafton.ai/ko/docs/reasoning),
[한도](https://raon-mini.krafton.ai/ko/docs/rate-limits).

로컬 검증: `python -m unittest discover -s Mesugak_V2/functions/tests -p test_raon.py`.
