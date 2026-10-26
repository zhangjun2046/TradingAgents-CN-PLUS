import { request } from "./request";

/** 报告列表单项（GET /api/reports/list 的 data.reports） */
export interface ReportListItem {
  id: string;
  analysis_id?: string;
  title?: string;
  stock_code?: string;
  stock_name?: string;
  market_type?: string;
  status?: string;
  created_at?: string;
  analysis_date?: string;
  task_id?: string;
}

/** 报告列表分页结果 */
export interface ReportListData {
  reports: ReportListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface ReportListQuery {
  page?: number;
  page_size?: number;
  search_keyword?: string;
  market_filter?: string;
}

/**
 * 我的报告列表（需登录）。后端按 user_id 过滤，管理员返回全部。
 */
export function getReportList(query: ReportListQuery = {}): Promise<ReportListData> {
  const page = query.page ?? 1;
  const pageSize = query.page_size ?? 20;
  const parts = [`page=${page}`, `page_size=${pageSize}`];
  const keyword = query.search_keyword?.trim();
  if (keyword) {
    parts.push(`search_keyword=${encodeURIComponent(keyword)}`);
  }
  if (query.market_filter) {
    parts.push(`market_filter=${encodeURIComponent(query.market_filter)}`);
  }
  return request<ReportListData>({
    url: `/api/reports/list?${parts.join("&")}`,
    method: "GET",
  });
}

/**
 * 分享接口使用的报告标识：优先 analysis_id，其次 Mongo id，再次 task_id。
 */
export function reportShareId(item: Pick<ReportListItem, "analysis_id" | "id" | "task_id">): string {
  return item.analysis_id || item.id || item.task_id || "";
}

/** 分享记录（POST /api/reports/{id}/share 的 data） */
export interface ShareInfo {
  token: string;
  /** 形如 /s/{token} */
  path?: string;
  expires_at?: string;
  created_at?: string;
  view_count?: number;
}

/**
 * 创建或复用分享链接（需登录）。
 * 后端自动复用未撤销且未过期的分享，过期则新建，默认有效期 30 天（tech_solution 7.6）。
 * @param reportId 报告标识：analysis_id，缺失时可直接使用 task_id
 */
export async function createOrReuseShare(reportId: string): Promise<ShareInfo> {
  const data = await request<ShareInfo>({
    url: `/api/reports/${encodeURIComponent(reportId)}/share`,
    method: "POST",
    data: {},
    silent: true,
  });
  if (!data?.token) {
    throw new Error("分享链接生成失败，请重试");
  }
  return data;
}
