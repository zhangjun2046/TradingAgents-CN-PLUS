/**
 * 公开模型接口的内置兜底列表。
 * 结构严格等于 tech_solution 7.3 契约（GET /api/config/public/models 的 data）：
 * { default_quick_model, default_deep_model, models: [{ name, display_name, provider, capability_level, roles }] }
 * 接口 404 / 失败 / 未登录时使用；集成后接口可用则自动走真实数据。
 */

export type ModelRole = "quick_analysis" | "deep_analysis" | "both" | string;

export interface PublicModel {
  name: string;
  display_name: string;
  provider: string;
  capability_level: number;
  roles: ModelRole[];
}

export interface PublicModelsData {
  default_quick_model: string | null;
  default_deep_model: string | null;
  models: PublicModel[];
}

export const FALLBACK_PUBLIC_MODELS: PublicModelsData = {
  default_quick_model: "qwen-plus",
  default_deep_model: "deepseek-chat",
  models: [
    {
      name: "qwen-turbo",
      display_name: "通义千问 Turbo (qwen-turbo)",
      provider: "dashscope",
      capability_level: 1,
      roles: ["quick_analysis"],
    },
    {
      name: "qwen-plus",
      display_name: "通义千问 Plus (qwen-plus)",
      provider: "dashscope",
      capability_level: 2,
      roles: ["both"],
    },
    {
      name: "qwen-max",
      display_name: "通义千问 Max (qwen-max)",
      provider: "dashscope",
      capability_level: 4,
      roles: ["deep_analysis"],
    },
    {
      name: "deepseek-chat",
      display_name: "DeepSeek V3 (deepseek-chat)",
      provider: "deepseek",
      capability_level: 4,
      roles: ["both"],
    },
  ],
};
