/** 与 frontend/public/legal 同步的占位文案，P5.4 替换。 */
export const AGREEMENT_MD = `# 用户协议（占位）

本文件为 HunterAgent / TradingAgents-CN 1.0 开发占位文案，上线前由业务方替换。

使用本平台即表示你理解：分析结论由 AI 自动生成，仅供学习研究，不构成投资建议。投资有风险，决策与后果由用户自行承担。
`;

export const PRIVACY_MD = `# 隐私政策（占位）

本文件为 HunterAgent / TradingAgents-CN 1.0 开发占位文案，上线前由业务方替换。

我们可能收集你的手机号用于注册、登录与找回密码。短信验证码由短信服务商发送。详细条款上线前替换。
`;

export function mdToText(md: string): string {
  return md
    .replace(/^#+\s?/gm, "")
    .trim();
}
