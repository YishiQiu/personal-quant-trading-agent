import type { PatternScanResponse, ResearchResponse, UniverseResponse } from "./types";

export class ResearchApiError extends Error {}

export async function runPatternScan(): Promise<PatternScanResponse> {
  const response = await fetch("/api/v1/pattern-scan/sina_free");
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

export async function runPreviousCloseResearch(): Promise<ResearchResponse> {
  const response = await fetch("/api/v1/research/sina_free", { method: "POST" });
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
): Promise<UniverseResponse> {
  const params = new URLSearchParams({ page: String(page), page_size: "50", scope });
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
