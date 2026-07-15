import type {
  PatternScanResponse,
  ResearchResponse,
  ScanFilters,
  UniverseResponse,
} from "./types";

export class ResearchApiError extends Error {}

function scanParams(filters: ScanFilters): URLSearchParams {
  return new URLSearchParams({
    min_price: String(filters.min_price),
    max_price: String(filters.max_price),
    include_chinext: String(filters.include_chinext),
    include_star_market: String(filters.include_star_market),
  });
}

export async function runPatternScan(filters: ScanFilters): Promise<PatternScanResponse> {
  const response = await fetch(`/api/v1/pattern-scan/sina_free?${scanParams(filters).toString()}`);
  const body = (await response.json().catch(() => null)) as
    | PatternScanResponse
    | { detail?: string }
    | null;
  if (!response.ok) {
    const detail = body && "detail" in body ? body.detail : "形态筛选服务暂时不可用";
    throw new ResearchApiError(detail || "形态筛选服务暂时不可用");
  }
  return body as PatternScanResponse;
}

export async function runPreviousCloseResearch(filters: ScanFilters): Promise<ResearchResponse> {
  const response = await fetch(`/api/v1/research/sina_free?${scanParams(filters).toString()}`, {
    method: "POST",
  });
  const body = (await response.json().catch(() => null)) as
    | ResearchResponse
    | { detail?: string }
    | null;
  if (!response.ok) {
    const detail = body && "detail" in body ? body.detail : "研究服务暂时不可用";
    throw new ResearchApiError(detail || "研究服务暂时不可用");
  }
  return body as ResearchResponse;
}

export async function getUniverse(
  page: number,
  query: string,
  scope: "all" | "base_candidates",
  filters: ScanFilters,
): Promise<UniverseResponse> {
  const params = scanParams(filters);
  params.set("page", String(page));
  params.set("page_size", "50");
  params.set("scope", scope);
  if (query.trim()) params.set("query", query.trim());
  const response = await fetch(`/api/v1/universe/sina_free?${params.toString()}`);
  const body = (await response.json().catch(() => null)) as
    | UniverseResponse
    | { detail?: string }
    | null;
  if (!response.ok) {
    const detail = body && "detail" in body ? body.detail : "全市场数据暂时不可用";
    throw new ResearchApiError(detail || "全市场数据暂时不可用");
  }
  return body as UniverseResponse;
}
