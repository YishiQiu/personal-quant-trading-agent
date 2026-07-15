export interface Recommendation {
  code: string;
  name: string;
  total_score: number;
  verdict: string;
  reasons: string[];
  risks: string[];
  vetoed: boolean;
  news: NewsItem[];
}

export interface ScanFilters {
  min_price: number;
  max_price: number;
  include_chinext: boolean;
  include_star_market: boolean;
}

export interface NewsItem {
  headline: string;
  published_at: string;
  source: string;
  url: string | null;
  summary: string | null;
}

export interface ResearchResponse {
  provider: string;
  snapshot: string | null;
  close_date: string;
  filters: ScanFilters;
  scanned_count: number;
  observation_pool_count: number;
  research_pool_count: number;
  recommendations: Recommendation[];
  vetoed: Recommendation[];
  research_results: Recommendation[];
}

export interface PatternCandidate {
  code: string;
  name: string;
  last_price: number;
  pct_change: number;
  turnover_amount: number;
  patterns: string[];
  body_ratio: number;
  upper_shadow_ratio: number;
  lower_shadow_ratio: number;
}

export interface PatternScanResponse {
  provider: string;
  snapshot: string | null;
  close_date: string;
  filters: ScanFilters;
  scanned_count: number;
  observation_pool_count: number;
  pattern_match_count: number;
  pattern_candidates: PatternCandidate[];
}

export interface UniverseItem {
  code: string;
  name: string;
  last_price: number;
  pct_change: number;
  turnover_amount: number;
  status: "excluded" | "eligible" | "observation";
  rejection_reasons: string[];
}

export interface UniverseResponse {
  provider: string;
  snapshot: string | null;
  close_date: string;
  filters: ScanFilters;
  source_count: number;
  eligible_count: number;
  observation_count: number;
  scope: "all" | "base_candidates";
  matched_count: number;
  page: number;
  page_size: number;
  total_pages: number;
  items: UniverseItem[];
}
