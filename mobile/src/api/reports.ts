import { request } from "./request";

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
