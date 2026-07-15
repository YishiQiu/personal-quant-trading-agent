import { useState } from "react";

import { getUniverse, runPatternScan, runPreviousCloseResearch } from "./api";
import type {
  PatternCandidate,
  PatternScanResponse,
  Recommendation,
  ResearchResponse,
  UniverseItem,
  UniverseResponse,
} from "./types";

type ViewState = "idle" | "running" | "completed" | "failed";
type ResultView = "patterns" | "research" | "recommendations" | "universe";
type UniverseScope = "all" | "base_candidates";

const patternPageSize = 50;

function scoreTone(score: number): string {
  if (score >= 70) return "strong";
  if (score >= 60) return "watch";
  return "neutral";
}

function verdictLabel(verdict: string): string {
  return verdict === "watch_for_tail_buy" ? "重点关注" : verdict === "rejected" ? "风险否决" : "继续观察";
}

function patternLabel(pattern: string): string {
  if (pattern === "bullish_perfect_doji") return "阳线完美十字";
  if (pattern === "bullish_hammer") return "阳线锤子";
  return pattern === "doji" ? "十字星" : pattern === "hammer" ? "锤头线" : pattern;
}

function percentage(value: number): string {
  return `${(value * 100).toFixed(2)}%`;
}

function turnover(amount: number): string {
  return `${(amount / 100_000_000).toFixed(2)} 亿`;
}

function statusLabel(item: UniverseItem): string {
  if (item.status !== "excluded") return "基础通过";
  return item.rejection_reasons.join(" · ") || "未通过基础规则";
}

function closeDateLabel(closeDate: string | undefined): string {
  return closeDate ? closeDate.replaceAll("-", ".") : "等待扫描";
}

function CandidateCard({ item, rank, featured = false }: { item: Recommendation; rank: number; featured?: boolean }) {
  const news = item.news ?? [];
  return (
    <article className={`candidate-card ${featured ? "featured" : ""}`}>
      <div className="candidate-topline">
        <span className="rank">第 {String(rank).padStart(2, "0")} 名</span>
        <span className={`score ${scoreTone(item.total_score)}`}>{item.total_score.toFixed(2)}</span>
      </div>
      <div className="candidate-title">
        <div>
          <h3>{item.name}</h3>
          <span>{item.code}</span>
        </div>
        <span className={`verdict ${item.verdict}`}>{verdictLabel(item.verdict)}</span>
      </div>
      <div className="evidence">
        {item.reasons.slice(0, 5).map((reason) => <p key={reason}>{reason}</p>)}
      </div>
      {news.length > 0 && (
        <section className="news-evidence" aria-label="新闻与公告证据">
          <p>新闻 / 公告证据</p>
          {news.slice(0, 3).map((newsItem) => (
            <div className="news-item" key={`${newsItem.source}-${newsItem.published_at}-${newsItem.headline}`}>
              <span>{newsItem.source} · {new Date(newsItem.published_at).toLocaleString("zh-CN")}</span>
              {newsItem.url ? (
                <a href={newsItem.url} target="_blank" rel="noreferrer">{newsItem.headline}</a>
              ) : <strong>{newsItem.headline}</strong>}
            </div>
          ))}
        </section>
      )}
      {item.risks.length > 0 && (
        <div className="risk-list">
          {item.risks.map((risk) => <span key={risk}>{risk}</span>)}
        </div>
      )}
    </article>
  );
}

function Metric({ label, value, detail }: { label: string; value: string | number; detail: string }) {
  return (
    <div className="metric-card">
      <span>{label}</span>
      <strong>{typeof value === "number" ? value.toLocaleString() : value}</strong>
      <small>{detail}</small>
    </div>
  );
}

export default function App() {
  const [state, setState] = useState<ViewState>("idle");
  const [patternResult, setPatternResult] = useState<PatternScanResponse | null>(null);
  const [researchResult, setResearchResult] = useState<ResearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [resultView, setResultView] = useState<ResultView>("patterns");
  const [patternPage, setPatternPage] = useState(1);
  const [researchLoading, setResearchLoading] = useState(false);
  const [researchError, setResearchError] = useState<string | null>(null);
  const [activeCode, setActiveCode] = useState<string | null>(null);
  const [universe, setUniverse] = useState<UniverseResponse | null>(null);
  const [universeLoading, setUniverseLoading] = useState(false);
  const [universeError, setUniverseError] = useState<string | null>(null);
  const [universeQuery, setUniverseQuery] = useState("");
  const [universeScope, setUniverseScope] = useState<UniverseScope>("all");

  const startAnalysis = async () => {
    setState("running");
    setError(null);
    setPatternResult(null);
    setResearchResult(null);
    setUniverse(null);
    setResearchError(null);
    setUniverseError(null);
    setActiveCode(null);
    setPatternPage(1);
    setResultView("patterns");
    try {
      setPatternResult(await runPatternScan());
      setState("completed");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "形态筛选服务暂时不可用");
      setState("failed");
    }
  };

  const startDeepResearch = async () => {
    setResearchLoading(true);
    setResearchError(null);
    try {
      const response = await runPreviousCloseResearch();
      setResearchResult(response);
      setActiveCode(response.research_results[0]?.code ?? null);
      setResultView("research");
    } catch (caught) {
      setResearchError(caught instanceof Error ? caught.message : "深度研究服务暂时不可用");
    } finally {
      setResearchLoading(false);
    }
  };

  const loadUniverse = async (page = 1, query = universeQuery, scope = universeScope) => {
    setUniverseLoading(true);
    setUniverseError(null);
    try {
      setUniverse(await getUniverse(page, query, scope));
    } catch (caught) {
      setUniverseError(caught instanceof Error ? caught.message : "全市场数据暂时不可用");
    } finally {
      setUniverseLoading(false);
    }
  };

  const showUniverse = () => {
    setResultView("universe");
    if (universe === null) void loadUniverse();
  };

  const visiblePatterns = patternResult
    ? patternResult.pattern_candidates.slice((patternPage - 1) * patternPageSize, patternPage * patternPageSize)
    : [];
  const patternPageCount = patternResult ? Math.max(1, Math.ceil(patternResult.pattern_candidates.length / patternPageSize)) : 1;
  const researchItems = researchResult?.research_results ?? [];
  const focusedResearch = researchItems.find((item) => item.code === activeCode) ?? researchItems[0] ?? null;
  const closeDate = researchResult?.close_date ?? patternResult?.close_date ?? universe?.close_date;
  const resultHeading = resultView === "patterns" ? "形态命中清单"
    : resultView === "research" ? "全部分析结果"
      : resultView === "recommendations" ? "重点关注"
        : "全市场收盘快照";

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark"><i />Q</span>
          <div><p>A 股短线研究</p><h1>量化收盘研究室</h1></div>
        </div>
        <div className="topbar-status">
          <span className="pulse" />
          <span>研究系统运行中</span>
          <b>最近收盘 {closeDateLabel(closeDate)}</b>
        </div>
      </header>

      <section className="hero-panel">
        <div className="hero-copy-block">
          <p className="eyebrow">每日收盘研究</p>
          <h2>从全市场，找到<em>少数机会</em></h2>
          <p>自动采用最近一个完整交易日的收盘数据。先扫描全市场，再对阳线完美十字与锤子线命中股补充历史行情、新闻公告和风险判断。</p>
          <div className="hero-notes"><span>股价低于 100 元</span><span>完美十字 · 锤子线</span><span>全部命中股深度研究</span></div>
        </div>
        <div className="hero-action">
          <button className="start-button" onClick={startAnalysis} disabled={state === "running"}>
            <span>{state === "running" ? "正在扫描" : "开始扫描"}</span><b>→</b>
          </button>
        </div>
      </section>

      {state === "idle" && <section className="empty-panel"><div className="empty-icon">Q</div><p>今日研究尚未开始</p><span>点击“开始扫描”，读取最近一个完整收盘的全市场快照。</span></section>}
      {state === "running" && <section className="empty-panel loading-panel"><span className="loader" /><p>正在构建今日研究宇宙</p><span>读取收盘快照 · 初筛 · 计算十字星 / 锤头线</span></section>}
      {state === "failed" && <section className="empty-panel error-panel" role="alert"><p>本次扫描未完成</p><span>{error}</span><small>收盘后会优先刷新当天快照；若公开数据源未返回完整数据，会保留上次成功结果而不生成推荐。</small></section>}

      {state === "completed" && patternResult && (
        <>
          <section className="summary-grid" aria-label="本次统计">
            <Metric label="全市场收盘" value={patternResult.scanned_count} detail="完整股票快照" />
            <Metric label="基础规则通过" value={patternResult.observation_pool_count} detail="价格、流动性、风险过滤" />
            <Metric label="形态命中" value={patternResult.pattern_match_count} detail="完美十字 · 锤子线" />
            <Metric label="已完成分析" value={researchResult?.research_pool_count ?? "—"} detail="行情、消息与风险" />
            <Metric label="重点关注" value={researchResult?.recommendations.length ?? "—"} detail="综合评分较高" />
          </section>

          <section className="result-header">
            <div><p className="eyebrow">本次分析 · {closeDateLabel(closeDate)}</p><h2>{resultHeading}</h2></div>
            <p className="snapshot-label">{closeDate ? `收盘日期 ${closeDate}` : "读取最近可用收盘快照"}</p>
          </section>

          <nav className="view-switcher" aria-label="结果视图">
            <button className={resultView === "patterns" ? "selected" : ""} onClick={() => setResultView("patterns")}>形态命中 <span>{patternResult.pattern_match_count}</span></button>
            <button className={resultView === "research" ? "selected" : ""} onClick={() => researchResult && setResultView("research")} disabled={!researchResult}>全部分析 <span>{researchItems.length || "—"}</span></button>
            <button className={resultView === "recommendations" ? "selected" : ""} onClick={() => researchResult && setResultView("recommendations")} disabled={!researchResult}>重点关注 <span>{researchResult?.recommendations.length ?? "—"}</span></button>
            <button className={resultView === "universe" ? "selected" : ""} onClick={showUniverse}>全市场</button>
          </nav>

          {resultView === "patterns" && (
            <section className="data-surface pattern-panel">
              <div className="surface-header">
                <div><p>第一步筛选结果</p><h3>符合形态条件的股票</h3><span>按实体、上下影和振幅比例判断，展示全部结果。</span></div>
                <button className="deep-research-button" onClick={() => void startDeepResearch()} disabled={researchLoading || patternResult.pattern_match_count === 0}>
                  <small>历史行情 · 新闻公告 · AI 辅助</small>{researchLoading ? "正在分析全部股票…" : `分析全部 ${patternResult.pattern_match_count} 只`} <b>↗</b>
                </button>
              </div>
              {researchError && <p className="message error">{researchError}</p>}
              <p className="surface-meta">共命中 {patternResult.pattern_match_count.toLocaleString()} 只，当前展示 {(patternPage - 1) * patternPageSize + 1}–{Math.min(patternPage * patternPageSize, patternResult.pattern_match_count)}。</p>
              <div className="table-scroll"><table><thead><tr><th>代码</th><th>名称</th><th>形态</th><th>最近收盘</th><th>涨跌幅</th><th>实体</th><th>上影</th><th>下影</th><th>成交额</th></tr></thead><tbody>
                {visiblePatterns.map((item: PatternCandidate) => <tr key={item.code}><td>{item.code}</td><td className="company">{item.name}</td><td><span className="pattern-badges">{item.patterns.map((pattern) => <span key={pattern}>{patternLabel(pattern)}</span>)}</span></td><td>{item.last_price.toFixed(2)}</td><td className={item.pct_change >= 0 ? "rise" : "fall"}>{item.pct_change.toFixed(2)}%</td><td>{percentage(item.body_ratio)}</td><td>{percentage(item.upper_shadow_ratio)}</td><td>{percentage(item.lower_shadow_ratio)}</td><td>{turnover(item.turnover_amount)}</td></tr>)}
              </tbody></table></div>
              <div className="pagination"><button disabled={patternPage <= 1} onClick={() => setPatternPage((page) => page - 1)}>← 上一页</button><span>{patternPage} / {patternPageCount}</span><button disabled={patternPage >= patternPageCount} onClick={() => setPatternPage((page) => page + 1)}>下一页 →</button></div>
            </section>
          )}

          {resultView === "research" && researchResult && (
            <section className="research-layout">
              <div className="data-surface research-table"><div className="surface-header compact"><div><p>完整分析结果</p><h3>{researchItems.length} 只股票已完成分析</h3></div><span>点击股票查看理由和风险</span></div>
                <div className="table-scroll"><table><thead><tr><th>排名</th><th>股票</th><th>综合分</th><th>结论</th><th>新闻</th><th>风险</th></tr></thead><tbody>
                  {researchItems.map((item, index) => <tr className={item.code === focusedResearch?.code ? "active-row" : ""} key={item.code} onClick={() => setActiveCode(item.code)}><td>#{String(index + 1).padStart(2, "0")}</td><td><b>{item.name}</b><small>{item.code}</small></td><td><strong className={`table-score ${scoreTone(item.total_score)}`}>{item.total_score.toFixed(2)}</strong></td><td><span className={`table-verdict ${item.verdict}`}>{verdictLabel(item.verdict)}</span></td><td>{item.news.length}</td><td>{item.risks.length}</td></tr>)}
                </tbody></table></div>
              </div>
              <aside className="research-inspector">{focusedResearch ? <CandidateCard item={focusedResearch} rank={researchItems.findIndex((item) => item.code === focusedResearch.code) + 1} featured /> : <div className="inspector-empty">尚无研究结果</div>}</aside>
            </section>
          )}

          {resultView === "recommendations" && researchResult && (researchResult.recommendations.length > 0 ? <section className="candidate-grid">{researchResult.recommendations.map((item, index) => <CandidateCard key={item.code} item={item} rank={index + 1} />)}</section> : <section className="empty-panel"><p>本次没有达到关注阈值的股票</p><span>所有形态命中股仍已完成分析，可在“全部分析”查看每一只的理由与风险。</span></section>)}

          {resultView === "universe" && (
            <section className="data-surface universe-panel"><div className="surface-header compact"><div><p>全部股票</p><h3>最近收盘行情</h3></div><form className="universe-toolbar" onSubmit={(event) => { event.preventDefault(); void loadUniverse(1); }}><input value={universeQuery} onChange={(event) => setUniverseQuery(event.target.value)} placeholder="输入股票代码或名称" /><button type="submit" disabled={universeLoading}>搜索</button></form></div>
              <div className="scope-switcher"><button className={universeScope === "all" ? "selected" : ""} onClick={() => { setUniverseScope("all"); void loadUniverse(1, universeQuery, "all"); }} disabled={universeLoading}>全部股票</button><button className={universeScope === "base_candidates" ? "selected" : ""} onClick={() => { setUniverseScope("base_candidates"); void loadUniverse(1, universeQuery, "base_candidates"); }} disabled={universeLoading}>&lt;100 元且基础通过</button></div>
              {universeLoading && <p className="message">正在读取完整收盘快照…</p>}{universeError && <p className="message error">{universeError}</p>}
              {universe && !universeLoading && <><p className="surface-meta">快照共 {universe.source_count.toLocaleString()} 只；基础规则通过 {universe.observation_count.toLocaleString()} 只；当前范围匹配 {universe.matched_count.toLocaleString()} 只。</p><div className="table-scroll"><table><thead><tr><th>代码</th><th>名称</th><th>最近收盘</th><th>涨跌幅</th><th>成交额</th><th>状态</th></tr></thead><tbody>{universe.items.map((item) => <tr key={item.code}><td>{item.code}</td><td className="company">{item.name}</td><td>{item.last_price.toFixed(2)}</td><td className={item.pct_change >= 0 ? "rise" : "fall"}>{item.pct_change.toFixed(2)}%</td><td>{turnover(item.turnover_amount)}</td><td><span className={`status ${item.status}`}>{statusLabel(item)}</span></td></tr>)}</tbody></table></div><div className="pagination"><button disabled={universe.page <= 1} onClick={() => void loadUniverse(universe.page - 1)}>← 上一页</button><span>{universe.page} / {universe.total_pages}</span><button disabled={universe.page >= universe.total_pages} onClick={() => void loadUniverse(universe.page + 1)}>下一页 →</button></div></>}
            </section>
          )}

          <p className="disclaimer">研究结果仅供人工判断，不会自动下单。新闻与公告均保留来源；缺失的信息会明确提示，系统不会自行猜测。</p>
        </>
      )}
    </main>
  );
}
