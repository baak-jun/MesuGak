import { BookOpen } from 'lucide-react';
import { AdSenseSlot } from './AdSenseSlot.jsx';
import './learning.css';

/**
 * Public, authored learning content that remains visible after the live
 * analysis application hydrates. It intentionally uses a synthetic example
 * and does not repeat raw market values from the public feed.
 */
export function AnalysisEducationGuide() {
  return (
    <article className="analysis-live-guide" aria-label="공개 분석 읽기 안내">
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
          공개 목록에는 최근 확정 일봉으로 계산한 종목별 종합점수와 5개 지표의 상태가 담겨 있습니다.
          종목을 선택해 분석 기준일과 뒷받침 조건, 함께 확인할 주의 조건을 비교해 보세요.
        </p>
      </section>
      <section>
        <h4>신호가 엇갈리는 예</h4>
        <p>
          주가가 구름대 위에 있고 RSI도 침체권에서 올라왔다면 단기 흐름은 긍정적으로 볼 수 있습니다.
          하지만 거래량이 최근 평균보다 약하거나 60일선이 하락 중이라면 추세 전환으로 이어질지는 더 지켜봐야 합니다.
          이처럼 신호가 일치하는 부분과 엇갈리는 부분을 나누어 읽어 보세요.
        </p>
      </section>
      <section>
        <h4>점수를 읽을 때 확인할 3가지</h4>
        <ul>
          <li>종합점수는 볼린저 밴드(25)·이동평균 지지(20)·일목균형표(20)·RSI(10)·거래량(10) 구성요소의 가중 평균을 0~100으로 정리한 값입니다.</li>
          <li>점수가 높아도 구름대와 이동평균처럼 비슷한 추세 조건만 겹친 결과일 수 있으니, 거래량과 RSI 등 성격이 다른 근거가 함께 있는지 확인하세요.</li>
          <li>확정 일봉 기준 분석이므로 목록 상단에 표시된 기준일이 최근 거래일인지, 기간 부족으로 계산에서 제외된 지표가 없는지 함께 점검하세요.</li>
        </ul>
      </section>
      <section className="analysis-guide-links">
        <h4>더 알아보기</h4>
        <p>
          <a href="/learn/glossary">용어집</a>에서 낯선 지표 용어를 확인하고,
          <a href="/methodology">분석 방법론</a>에서 점수 산식과 결측 처리 기준을 읽은 뒤,
          <a href="/learn/cases">사례 수업</a>에서 지표 간 충돌 사례를 비교해 보세요.
        </p>
      </section>
      <AdSenseSlot placement="learning" title="광고" className="learning-inline-ad" />
    </article>
  );
}
