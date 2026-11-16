import { BookOpen, ShieldCheck } from 'lucide-react';
import './learning.css';

/**
 * Public, authored learning content that remains visible after the live
 * analysis application hydrates. It intentionally uses a synthetic example
 * and does not repeat raw market values from the public feed.
 */
export function AnalysisEducationGuide() {
  return (
    <article className="analysis-landing-article analysis-live-guide" aria-label="공개 분석 읽기 안내">
      <div className="analysis-guide-heading">
        <BookOpen size={18} aria-hidden="true" />
        <div>
          <p className="analysis-guide-kicker">분석 결과를 읽는 연습</p>
          <h3>좋아 보이는 신호가 하나라면?</h3>
        </div>
      </div>
      <section>
        <h4>이 화면에서 볼 수 있는 것</h4>
        <p>
          공개 목록에는 최근 확정 일봉으로 계산한 지표 상태가 담겨 있어요.
          종목을 열어 기준일과 조건을 읽어 보세요. 원시 가격과 차트는 이 화면에 표시하지 않습니다.
        </p>
      </section>
      <section>
        <h4>신호가 엇갈리는 예</h4>
        <p>
          구름대 위에 있고 RSI도 침체권에서 올라왔다면 좋아 보일 수 있어요.
          그런데 거래량이 약하거나 60일선이 계속 내려간다면 어떨까요?
          위치는 나아졌어도 흐름이 이어질지는 더 봐야 합니다.
          이렇게 신호가 맞는 부분과 엇갈리는 부분을 차례로 읽어 보세요.
        </p>
      </section>
      <section>
        <h4>점수를 읽기 전에</h4>
        <ul>
          <li>종합점수는 확률이나 예상 수익률이 아니라, 다섯 기술지표 구성요소의 가중 평균을 0~100으로 정리한 값입니다. 산식과 결측 처리 방식은 분석 방법론에서 확인할 수 있습니다.</li>
          <li>기준일이 오래되었거나 데이터가 부족하면 같은 상태 문장도 현재 상황을 설명하지 못할 수 있습니다.</li>
          <li>공개 화면에는 원시값이 없어 종목별 계산을 그대로 따라 할 수는 없어요. 계산 기준은 용어집과 방법론에서 확인할 수 있습니다.</li>
        </ul>
      </section>
      <section className="analysis-guide-links">
        <h4>더 궁금하다면</h4>
        <p>
          <a href="/learn/glossary">용어집</a>에서 낯선 표현을 먼저 확인하고,
          <a href="/methodology">분석 방법론</a>에서 조건과 데이터 출처를 읽은 뒤,
          <a href="/learn/cases">사례 수업</a>에서 반대 신호까지 비교해 보세요.
        </p>
      </section>
      <section className="guide-article-note">
        <ShieldCheck size={19} aria-hidden="true" />
        <p>이 자료는 기술지표를 공부하기 위한 참고 콘텐츠이며 개인별 투자상담, 주문 전송, 목표가격, 수익률 보장 서비스가 아닙니다.</p>
      </section>
    </article>
  );
}
