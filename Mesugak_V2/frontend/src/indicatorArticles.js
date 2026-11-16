import ichimoku from './content/articles/ichimoku.md?raw';
import bollinger from './content/articles/bollinger.md?raw';
import movingAverage from './content/articles/moving-average.md?raw';
import rsi from './content/articles/rsi.md?raw';
import volume from './content/articles/volume.md?raw';
import valuation from './content/articles/valuation.md?raw';

// The Markdown files are the editable source. This parser only adapts them to the page component.
function parseArticle(raw) {
  const normalized = raw.replace(/^\uFEFF/, '').replace(/\r\n/g, '\n');
  const match = normalized.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
  if (!match) throw new Error('지표 글의 맨 위 --- 정보 블록을 확인해 주세요.');

  const meta = Object.fromEntries(match[1].split('\n').map((line) => {
    const separator = line.indexOf(': ');
    if (separator < 1) throw new Error(`지표 글 정보 형식 오류: ${line}`);
    return [line.slice(0, separator), line.slice(separator + 2)];
  }));
  const blocks = match[2].split(/^## /m).map((block) => block.trim()).filter(Boolean);
  const article = { ...meta, minutes: Number(meta.minutes), sections: [], sources: [] };

  for (const block of blocks) {
    const newline = block.indexOf('\n');
    const title = newline < 0 ? block : block.slice(0, newline).trim();
    let text = newline < 0 ? '' : block.slice(newline + 1).trim();
    if (title === '시작하며') {
      article.lead = text;
      continue;
    }
    if (title === '참고 자료') {
      article.sources = text.split('\n').filter(Boolean).map((line) => {
        const source = line.match(/^- \[(.+)\]\((https?:\/\/[^)]+)\)$/);
        if (!source) throw new Error(`${meta.slug}: 참고 자료 형식 오류: ${line}`);
        return { label: source[1], href: source[2] };
      });
      continue;
    }

    const section = { title };
    const formula = text.match(/:::formula\n([\s\S]*?)\n:::/);
    if (formula) {
      section.formula = formula[1].trim();
      text = text.replace(formula[0], '').trim();
    }
    const example = text.match(/:::example\n([\s\S]*?)\n:::/);
    if (example) {
      const fields = Object.fromEntries(example[1].split('\n').map((line) => {
        const separator = line.indexOf(': ');
        if (separator < 1) throw new Error(`${meta.slug}: 숫자 예시 형식 오류: ${line}`);
        return [line.slice(0, separator), line.slice(separator + 2)];
      }));
      section.example = { input: fields.조건, calculation: fields.계산, reading: fields.해석 };
      text = text.replace(example[0], '').trim();
    }
    section.blocks = text ? text.split(/\n\s*\n/).filter(Boolean).map((block) => {
      if (!block.trim().startsWith('|')) return { type: 'paragraph', text: block.replace(/\n/g, ' ').trim() };
      const rows = block.trim().split('\n').map((line) => line.trim().replace(/^\||\|$/g, '').split('|').map((cell) => cell.trim()));
      if (rows.length < 3 || rows[0].length < 2 || !rows[1].every((cell) => /^:?-{3,}:?$/.test(cell)) || rows.some((row) => row.length !== rows[0].length)) {
        throw new Error(`${meta.slug}: '${title}'의 표 열 수와 구분선을 확인해 주세요.`);
      }
      return { type: 'table', headers: rows[0], rows: rows.slice(2) };
    }) : [];
    article.sections.push(section);
  }

  if (!article.slug || !article.title || !article.deck || !article.lead || !/^\d{4}-\d{2}-\d{2}$/.test(article.updatedOn || '') || !Number.isFinite(article.minutes) || article.sections.length < 5 || !article.sources.length) {
    throw new Error(`${meta.slug || '알 수 없는 글'}: 제목·요약·본문·참고 자료를 확인해 주세요.`);
  }
  return article;
}

export const indicatorArticles = [ichimoku, bollinger, movingAverage, rsi, volume, valuation].map(parseArticle);
export const articleBySlug = Object.fromEntries(indicatorArticles.map((article) => [article.slug, article]));
