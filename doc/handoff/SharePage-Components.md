# SharePage-Components：分享页组件交接

| 项 | 内容 |
|----|------|
| 生成单元 | P4.4 分享页导出 + 微信内引导 |
| 生成日期 | 2026-10-28 |
| 对应 Git 提交 | `fc859f4`（功能分支 `feat/report/P4.4-export-wechat`；合入 `line/report` 后以 Squash 提交为准） |
| 主要读者 | B（P5.1）、A（P5.2 联调） |
| 设计依据 | `doc/tech_solution.md` 第 5 节（5.6 为 0.5：导出弹层）；报告字段见 `doc/handoff/Backend-API-Report.md`；手机端如何跳到本页见 `doc/handoff/H5-Architecture.md` |

分享页不在 `mobile/` 里。H5 和 PC 都打开 PC 前端的公开路由 `/s/{token}`。开发期地址是 `http://localhost:3000/s/{token}`。

本文件描述的是 B 线 `line/report` 上已经合入的分享页（含 P4.1～P4.3，以及已合入本线的结论一致性修复），加上本单元的导出弹层。

---

## 1. 组件结构

容器是 `frontend/src/views/Reports/ReportShare.vue`：拉公开报告、按 URL 定位、组装页签。成功加载后，标题行右侧有「导出」，点开 `ExportBar`。

```text
frontend/src/views/Reports/
├── ReportShare.vue                 # 容器
└── share/
    ├── shareConfig.ts              # 部门 - 岗位映射、显隐、URL 定位、返回列表地址
    ├── useShareReport.ts           # 拉公开接口、派生可见部门、同步地址栏
    ├── types.ts                    # 公开字段类型
    ├── exportShare.ts              # 微信 UA、复制链接、免登录下载（纯函数）
    ├── ShareHeader.vue             # 返回列表、导出插槽、股票名、有效期
    ├── DeptTabs.vue                # 一级页签（吸顶）+ 二级页签
    ├── OverviewPanel.vue           # 概览：投资建议、置信度、风险、决策链、要点、分析参考
    ├── ConfidenceGauge.vue         # 置信度仪表盘（ECharts 按需加载）
    ├── RiskBadge.vue               # 风险色块
    ├── DecisionChain.vue           # 决策链，点击跳岗位
    ├── RolePanel.vue               # 岗位页：结论卡 + 长文折叠
    ├── RoleConclusionCard.vue      # 结论卡
    ├── MarkdownBody.vue            # Markdown，经 DOMPurify，表格可横滑
    ├── ExportBar.vue               # 导出弹层
    ├── WechatGuide.vue             # 微信内右上角引导气泡
    ├── chartData.ts                # 置信度换算、投资建议文案、决策链节点
    ├── overviewSummary.ts          # 概览「分析参考」取 recommendation
    ├── conclusionCard.ts           # 结论卡展示用的小函数
    ├── roleFold.ts                 # 正文超过 60vh 则折叠
    └── stripDisclaimer.ts          # 去掉正文里重复的免责声明
frontend/src/utils/reportConclusion.ts   # 结论提取（纯函数）
```

`share/BullBearCompare.vue` 仍在目录里，概览没有使用它。多空辩论只在研究部对应岗位的正文里阅读。

页面底部固定有「风险提示与免责声明」。失效页标题是「链接已失效」，并显示「请返回报告列表重新打开」。加载中和失效时不出现导出按钮。

## 2. 部门与岗位

映射表在 `share/shareConfig.ts` 的 `DEPARTMENTS`。多个 `fields` 时用第一个非空字段。

| 部门 key | 名称 | 岗位 |
|----------|------|------|
| `overview` | 概览 | 无二级岗位，始终保留 |
| `analysts` | 分析部 | 市场 / 基本面 / 新闻 / 社媒情绪分析师 |
| `research` | 研究部 | 多头研究员、空头研究员、研究经理 |
| `trading` | 交易部 | 交易员 |
| `risk` | 风控部 | 激进 / 保守 / 中性分析师、风险管理委员会主席 |
| `other` | 其他 | 映射表没用到、但正文非空的模块，避免内容丢失 |

显隐（`buildVisibleDepartments`）：

- 岗位正文为空则不显示该岗位。
- 部门下一个岗位都没有则不显示该部门。概览除外。
- 部门里至少两个岗位才显示二级页签。只有一个岗位时直接展示该岗位，不出现二级页签。

观点徽章（`showsStance`）：分析师、研究经理、风险管理委员会主席显示。多头、空头、交易员、激进 / 保守 / 中性分析师不显示。决策链只收录「允许显示徽章且能识别出观点」的岗位。

## 3. 结论提取

规则在 `frontend/src/utils/reportConclusion.ts` 的 `extractRoleView`。岗位页通过它得到观点和一句话。

| 项 | 当前行为 |
|----|----------|
| 观点 | `bullish` 看多、`bearish` 看空、`neutral` 中性、`unknown` 未识别。关键词含买入 / 增持 / 看多 / 看涨、卖出 / 减持 / 看空 / 看跌、持有 / 观望。紧挨着的否定（不建议买入等）不算命中 |
| 取哪一句 | 优先正文里点名的结论（最终裁决、投资评级、我的建议是等），从后往前取最后一句。其次才看标题含「结论 / 建议」的小节。表格里的「买入」不当成观点；只有评级类的汇总表行可以在正文识别不到时兜底 |
| 一句话 | 保留观点所在的原句，不截成 60 字，也不用省略号把关键词截掉。`unknown` 时不显示这句话 |
| 和正文一致 | 这句话必须能在去掉 Markdown 标记后的正文里找到，否则不展示 |

长文折叠不在这个文件里。`roleFold.ts`：正文高度超过视口的 60% 时默认折叠，可展开 / 收起。

## 4. URL 定位

查询参数是 `?tab={部门 key}&role={岗位 key}`，例如 `?tab=research&role=bull`。

- 切换页签用 `router.replace`，不往历史记录里堆。
- 切换时滚回顶部。
- `tab` 缺失或非法时回到概览。
- 部门合法但 `role` 缺失或非法时，打开该部门第一个岗位。概览忽略 `role`。
- 旧链接 `tab=decision` 改到风控部主席；该岗位没有内容时回到概览。

一级页签吸顶。Markdown 表格包在可横向滑动的容器里，渲染结果经过 DOMPurify。

## 5. 数据从哪来

`useShareReport` 使用 `fetch('/api/reports/share/{token}')`，不走带登录拦截器的请求实例。

- 404 和 410 都当成链接失效。
- 成功体要有 `success` 和 `data`。
- 页面标题改为 `{股票名} - HunterAgent`。

公开字段以 `Backend-API-Report.md` 第 2.3 节为准。概览用到 `recommendation`（分析参考，不是执行摘要）、`confidence_score`、`risk_level`、`key_points`。`decision` 可能是空对象。

「返回报告列表」：开发期分享页在 `localhost:3000` 时，链到 `http://localhost:3100/m/#/pages/reports/list`；同域部署时用当前站点的 `/m/#/pages/reports/list`。

## 6. 导出与微信引导（P4.4）

对照原型图 `doc/images/h5-report-share-export-wx-guide.png`，交互以 `tech_solution.md` 5.6（0.5）为准。

| 行为 | 说明 |
|------|------|
| 入口 | 仅报告加载成功时，标题行右侧「导出」 |
| 弹层 | 窄屏贴底，宽屏（≥768px）居中卡片。标题「导出分析报告（免登录公开导出）」，下列出股票与基准日 |
| 格式 | PDF、Word、Markdown，按钮「立即导出」。生成期间该按钮显示「导出中」 |
| 下载 | `GET /api/reports/share/{token}/download?format=markdown\|pdf\|docx`，不带 `Authorization`。成功后用隐藏 `<a download>`，文件名优先读响应头里的 UTF-8 名 |
| 失败提示 | 429：「下载过于频繁，请稍后再试」。404 / 410：「请返回报告列表重新打开」。其他状态尽量显示后端 `detail` |
| 微信 | UA 含 `MicroMessenger` 时，报告一加载就自动打开弹层，可点「取消」继续阅读。黄色提示建议复制到系统浏览器；右上角气泡说明点「…」后「在浏览器中打开」。「立即导出」仍可点，失败时保留引导 |
| 复制 | 弹层里始终有「一键复制报告链接」，复制当前分享页地址（含 `?tab=&role=`）。点击当下先同步复制，再尝试 `navigator.clipboard`；非安全上下文或剪贴板被拒绝时用 `document.execCommand('copy')`。黄色提示和右上角气泡只在微信里出现 |

日志：`[Share] export`、`[Share] export failed`、`[Share] copy link`、`[Share] wechat guide opened`。

同一 token 每分钟导出超过 10 次会 429。Redis 不可用时后端放行。PDF 中文字体问题见 `Backend-API-Report.md`，本页不负责装字体。

## 7. 给下一单元的约定

- P5.1 部署时保证 `/s/{token}` 仍落到这份 PC 分享页，`/api/reports/share/` 能被浏览器直接访问（导出不走登录拦截）。
- 不要把导出改成整页跳转到下载地址，否则限流时读者会看到 JSON 而不是提示。
- 改部门岗位或结论规则时，同时改 `shareConfig.ts` / `reportConclusion.ts` 和本文件对应小节。
- A 的 P5.2 验收分享页：系统浏览器三种格式能下载；微信内能看到弹层、黄色提示、右上角气泡，复制链接可用；宽屏弹层居中，不挡住整页阅读以外的操作（取消可关）。
