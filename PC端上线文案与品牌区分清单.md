# PC 端上线文案与品牌区分清单

> 用途：按步骤改用户能看见的品牌与文案，并写明域名怎么配。  
> 状态：2026-11-05 已定 Logo、域名和备案号。**本文只定步骤，先不改代码。**  
> 对外品牌：**HunterAgents**（带 s，与域名 hunteragents.cn 一致）。联系邮箱：`ocm@onecloudmall.com`。  
> Logo 图形文件名仍是 `icons/hunteragent-v4-3-ai-pill.svg`，不因产品名加 s 而改文件名。  
> 正式入口：**https://hunteragents.cn/**。备案号：**京ICP备2021035986号-4**。  
> 分析引擎来自开源 TradingAgents / 上游 TradingAgents-CN。致谢保留，不要把本产品写成原项目。

范围：PC（`frontend/`）用户能看见的内容，加上发出去的报告落款、H5「我的」页、同域部署。不改仓库名、包名、Mongo 库名、代码注释、菜单 icon、智能体名字、分析流程，也不改服务器上的项目目录名。

---

## 已定、实现时按这个写

| 项 | 写法 |
|----|------|
| 产品名 | HunterAgents（带 s）。界面、协议、导出落款、分享文件名都用这个写法，不要写成 HunterAgent |
| Logo | `icons/hunteragent-v4-3-ai-pill.svg`（圆角 H + 右上 ai 胶囊）。实现时覆盖 `frontend/public/logo.svg`，并据此生成 favicon / PWA / apple-touch。H5 Tab 图标已定稿，不换 |
| 登录副标题 | 保持「多智能体股票分析学习平台」 |
| 版权年 | 2026 |
| 用户可见版本 | 1.0，去掉 `v1.0.0-preview` /「预览版」 |
| 站点 | `https://hunteragents.cn/` 为 PC 和分享页；`https://hunteragents.cn/m/` 为 H5；`https://hunteragents.cn/api/` 为接口。不要拆成 `h5.` / `admin.` 两个网站 |
| Open Graph | `https://hunteragents.cn/`。不要再指向 `tradingagents.cn` |
| 备案号 | 页脚写 `京ICP备2021035986号-4`，链接 `https://beian.miit.gov.cn/` |
| 联系方式 | 只留邮箱 `ocm@onecloudmall.com`。没有的 QQ、公众号、微信文档不要留空卡片 |
| 短信签名 | 本仓库 `.env` 已是 `SMS_SIGN_NAME=北京万商云猫智汇`，且 `SMS_PROVIDER=tencent`。这是腾讯云审核签名，不要改成 HunterAgents |
| 免责 | 产品名换成 HunterAgents。保留「学习、研究、不构成投资建议」。不把「投资建议」模块改名 |
| 上游 | 只出现在关于页致谢，并写明上游不等于本产品 |
| 协议主体 | 继续写「本公司」。不改成公司全称 |
| 公安备案 | 没有京公网安备号。页脚只放 ICP，不要编造 |
| 服务器 | 公网 IP `118.144.76.8`。代码目录 `D:\TradingAgents-CN-PLUS`。正式入口只使用不带端口的 `https://hunteragents.cn/` 和 `https://hunteragents.cn/m/`。不上线 IP 加端口。配好后停掉 `npm run dev`（3000）和 `npm run dev:h5`（3100），安全组关掉 3000、3100、8000。域名由 Nginx + `python -m app` 提供。不做开机自启 |

---

## 复核后要改的判断

1. **有些项已经改完。** 分享页眉、分享页浏览器标题、分享导出文件名已经是 HunterAgents。H5 应用名、导航标题也已是 HunterAgents；底部 Tab 的 6 张 PNG 已在 `mobile/src/static/`。
2. **导出里真正还漏品牌的是正文落款**，不是文件名。`app/utils/report_exporter.py` 末尾仍是「本报告由 TradingAgents-CN 自动生成」。登录后下载的文件名是 `{代码}_{日期}_report.ext`，没有旧品牌，不必改成带 HunterAgents。
3. **「投资建议」改名不要和换品牌绑在同一步。** 提示词一改，分析输出会变。
4. 关于页「查看文档」按钮和联系卡片都打开上游微信文章。删联系卡片时必须一起删这个按钮。
5. **返回报告列表不会因这次域名方案坏掉。** 坏掉的前提是 PC 和 H5 用两个主机名。同域配置下，H5 点「查看报告」打开 `https://hunteragents.cn/s/{token}?from=app`，返回去的是同一个域名下的 `https://hunteragents.cn/m/#/pages/reports/list`。代码不用改。详见下面「域名」一节。

---

## 已经对齐，本轮不改

- 《用户协议》《隐私政策》里的产品名已经是 HunterAgents。其中「开源上游（如 TradingAgents…）」是许可说明，保留。协议主体继续写「本公司」，本轮不改。
- 注册页、忘记密码页标题（没有旧品牌）。
- 分享页眉、分享页 `document.title` 覆盖、分享导出文件名。
- H5 应用名、导航标题、Tab PNG。`icons/h5-tabs/` 里的 SVG 是源稿，不必再导出。
- 仓库目录名、Windows 上的项目文件夹名。用户看不到。

---

## 开发步骤

按顺序做。一步验收通过再做下一步。步骤 1–5 改代码。步骤 6–7 本轮不做。步骤 8 与「域名」是服务器操作。

看结果的地址：

| 阶段 | PC | H5 |
|------|----|----|
| 步骤 1–5（域名还没切） | `http://118.144.76.8:3000`。改完刷新；文案没变就重启 `frontend` 里的 `npm run dev` | `http://118.144.76.8:3100`。改完刷新；没变就重启 `mobile` 里的 `npm run dev:h5` |
| 域名配完（步骤 8 / 域名一节） | `https://hunteragents.cn/`。要先重新 build 并拷到 Nginx | `https://hunteragents.cn/m/`。同样先 build:h5 再拷贝 |

域名配完后停掉 3000、3100。下面每一步的检查项不变，只换地址。H5 没有单独页面的项，写明「本步 H5 无变化」即可，仍要打开 H5 确认没有被改坏。

### 步骤 1：PC 外壳上的产品名和备案号

只替换产品名、版权年、去掉 preview，并加上备案号。Logo 文件在步骤 5 换。

| 位置 | 现状 | 改成 |
|------|------|------|
| 登录页标题 / Logo `alt` | TradingAgents-CN | HunterAgents |
| 登录页版权 | © 2025 TradingAgents-CN | © 2026 HunterAgents |
| 登录页免责里的自称 | TradingAgents-CN | HunterAgents（其余句子保留） |
| 侧栏 Logo 文字和 `alt` | TradingAgents-CN | HunterAgents |
| 路由标题后缀 | `xxx - TradingAgents-CN` | `xxx - HunterAgents` |
| `index.html` 的 `<title>`、`application-name`、`apple-mobile-web-app-title`、`mobile-web-app-title`、`author` | TradingAgents / TradingAgents-CN | HunterAgents |
| `index.html` 关键词 | 含 TradingAgents | 去掉这个词 |
| `og:url`、`twitter:url` | `https://tradingagents.cn/` | `https://hunteragents.cn/` |
| `og:title`、`twitter:title` | TradingAgents-CN | HunterAgents。描述句保持学习平台 |
| 首页欢迎语 | 「欢迎使用 TradingAgents-CN」+ `v1.0.0-preview` | 「欢迎使用 HunterAgents」，版本改为 1.0 |
| 页脚 | TradingAgents-CN / preview | HunterAgents，© 2026，去掉 preview。免责正文保留。另起一行备案号 |
| PWA 名称 | `manifest.json`、`vite.config.ts` | name：HunterAgents；short_name：HunterAgents |
| 配置向导欢迎语、配置完成提示、`stores/app.ts` 默认标题 | TradingAgents-CN | HunterAgents |

备案号这一行（各处相同）：

`京ICP备2021035986号-4`，链接到 `https://beian.miit.gov.cn/`，新窗口打开。

要放的位置：主布局页脚盖不到的公开页必须单独加，否则分享链接和登录页没有备案号。

- `frontend/src/components/Layout/AppFooter.vue`（登录后的主布局）
- `frontend/src/views/Auth/Login.vue`
- `frontend/src/views/About/index.vue`（关于页不走主布局）
- `frontend/src/views/Reports/ReportShare.vue`（分享页不走主布局，放在免责声明下面）
- 注册、忘记密码、用户协议、隐私政策这些同样不走主布局的页面，底部加同一行：
  - `frontend/src/views/Auth/Register.vue`
  - `frontend/src/views/Auth/ForgotPassword.vue`
  - `frontend/src/views/Legal/Agreement.vue`
  - `frontend/src/views/Legal/Privacy.vue`

对应文件（产品名）：

- `frontend/src/views/Auth/Login.vue`
- `frontend/src/layouts/BasicLayout.vue`
- `frontend/src/router/index.ts`
- `frontend/index.html`
- `frontend/src/views/Dashboard/index.vue`（只改欢迎标题和版本角标；首页学习中心卡片留到步骤 7）
- `frontend/src/components/Layout/AppFooter.vue`
- `frontend/public/manifest.json`
- `frontend/vite.config.ts`
- `frontend/src/components/ConfigWizard.vue`
- `frontend/src/App.vue`
- `frontend/src/stores/app.ts`

顺手可改、不作为验收：`frontend/src/main.ts` 里的启动 `console.log`。

**本步做完后怎么验证**

PC：

- 未登录打开登录页：标题是 HunterAgents，副标题仍是「多智能体股票分析学习平台」，版权是 © 2026 HunterAgents，免责里的产品名是 HunterAgents，底部有 `京ICP备2021035986号-4`，点开进到 beian.miit.gov.cn。Logo 图形本步可以仍是旧图。
- 浏览器标签是 `登录 - HunterAgents`（或对应页名加 HunterAgents），不是 TradingAgents-CN。
- 注册、忘记密码、用户协议、隐私政策底部都有同一备案号。协议正文仍写「本公司」，产品名仍是 HunterAgents。
- 登录后：侧栏文字是 HunterAgents；首页是「欢迎使用 HunterAgents」，版本是 1.0，没有 preview；页脚是 HunterAgents、© 2026，有备案号，免责仍写不构成投资建议。
- 打开一条分享链接：页眉仍是「HunterAgents 分析报告」，免责声明下面有备案号。浏览器标题后缀是 HunterAgents。

H5：

- 本步不改 H5。打开三个 Tab，页面仍能进。导航标题仍是 HunterAgents。
- 「我的」里若仍是 `1.0.0-preview` 和「基于 TradingAgents-CN 改造」，留到步骤 4，不算本步失败。

### 步骤 2：关于页整页改完

`frontend/src/views/About/index.vue` 一次改完。

1. 主标题改为 HunterAgents，去掉 `v1.0.0-preview`。
2. 「助您做出更明智的投资决策」「全方位投资决策支持」改为学习 / 研究 / 辅助分析，并写明不构成投资建议。
3. 删掉「查看文档」按钮和 `viewDocumentation`（现在打开上游微信文章）。
4. 「项目来源」保留 Tauric Research / TradingAgents 的 GitHub 致谢。第一句改成：HunterAgents 的分析引擎基于该开源项目，本产品不是 TradingAgents-CN。
5. 改进列表改成 HunterAgents 1.0 实际有的：手机号注册 / 登录 / 短信 / 忘记密码；H5 与 PC 共用账号；报告按用户隔离；分享页；HunterAgents 用户协议与隐私政策。
6. 版本卡：对外 1.0，去掉「预览版」和上游发布日期 2025-10-16。
7. 联系我们只留 `ocm@onecloudmall.com`。删掉 QQ 群 `187537480`、公众号「TradingAgents-CN」、微信文档链接。
8. 页脚版权改为 © 2026 HunterAgents，并加备案号。现有「前端与后端采用专有许可证…」不要原样留着。改成：开源组件遵循各自许可证；产品与协议以 HunterAgents 用户协议、隐私政策为准。
9. 「12 个智能体 / 12+ 数据源 / 24/7 实时监控」未核对，不要保留这些数字。

**本步做完后怎么验证**

PC：

- 打开关于页。主标题是 HunterAgents，没有 preview，没有「12 / 12+ / 24/7」这类数字。
- 没有「查看文档」按钮，没有 QQ、公众号、微信文章、`hsliup@163.com`。
- 联系方式只有 `ocm@onecloudmall.com`。
- 「项目来源」可以出现 TradingAgents 和 GitHub 链接，并且写明本产品不是 TradingAgents-CN。改进列表是手机号登录、H5 与 PC 账号、报告隔离、分享页、协议，不是上游的中文版卖点。
- 版本是 1.0，没有 2025-10-16。页脚是 © 2026 HunterAgents，有备案号。
- 登录页、首页、侧栏仍与步骤 1 一致，没有被这页改动带回去。

H5：

- 本步不改 H5。再打开「我的」、分析页、报告列表，确认仍能用。关于页只在 PC。

### 步骤 3：导出正文落款

- 文件：`app/utils/report_exporter.py`
- 现状：`*本报告由 TradingAgents-CN 自动生成*`
- 改为：`*本报告由 HunterAgents 自动生成*`

不改分享文件名、登录后下载文件名，也不改报告正文里的「投资建议」。仓库里没有断言这句落款的测试。改完需重启 `python -m app`，否则导出仍是旧进程里的文案。

**本步做完后怎么验证**

PC：

- 登录后打开一份已完成报告，导出 Markdown。文件名仍是 `{代码}_{日期}_report.md`。打开文件，最后一行是「本报告由 HunterAgents 自动生成」，没有 TradingAgents-CN。
- 再导出 PDF 或 Word 一份，落款同样是 HunterAgents。
- 页面上的「投资建议」标题本步保持不变。

H5：

- 在报告列表点「查看报告」进入分享页，点导出，选 Markdown。分享文件名仍是 `{代码}_{日期}_HunterAgents.md`。正文最后一行同样是 HunterAgents。
- 导出后点「返回报告列表」，应回到 H5 报告列表（开发期是 `:3100/m/#/pages/reports/list`）。
- 「我的」页文案本步可以仍是旧的，留到步骤 4。

### 步骤 4：H5「我的」页

| 位置 | 现状 | 改成 |
|------|------|------|
| `mobile/src/pages/mine/index.vue` 版本 | `1.0.0-preview` | `1.0` |
| 同页来源说明 | 「本产品基于 TradingAgents-CN 改造…」 | 本产品是 HunterAgents。分析能力参考开源 TradingAgents，本产品不是该项目或其 CN 版本。用途与免责以用户协议为准 |
| 同页底部 | 无备案号 | 加上 `京ICP备2021035986号-4`，链到 `https://beian.miit.gov.cn/` |
| `mobile/src/manifest.json` 的 `description` | TradingAgents-CN H5 | HunterAgents |

不改 H5 应用名、导航标题、Tab 图标、协议正文。

**本步做完后怎么验证**

PC：

- 本步不改 PC 页面。再看登录页、首页、关于页，仍是步骤 1–2 的结果。

H5：

- 打开「我的」。版本是 `1.0`，没有 preview。
- 来源说明是 HunterAgents，并写明分析能力参考开源 TradingAgents、本产品不是该项目或 CN 版本。看不到「基于 TradingAgents-CN 改造」「上游专有许可」「不对外收费」。
- 底部有 `京ICP备2021035986号-4`，点开进到 beian.miit.gov.cn。
- 底部三个 Tab 图标与改前相同。导航标题仍是 HunterAgents。
- 《用户协议》《隐私政策》仍是 HunterAgents，主体仍是「本公司」。

### 步骤 5：换上已选定的 Logo

选定文件：`icons/hunteragent-v4-3-ai-pill.svg`。

实现时：

1. 用该文件覆盖 `frontend/public/logo.svg`。登录页和登录后侧栏引用 `/logo.svg?v=v4-3`。开发环境 PWA 对 svg / png / ico 是缓存优先、保留 30 天；地址不带版本时，文件已经换掉，登录后左上角仍会显示旧图。
2. 用同一图形导出 PNG / ICO，覆盖这些已有引用，**文件名不要改**（`index.html`、`manifest.json`、`vite.config.ts` 已指向它们）：
   - `frontend/public/favicon.ico`（可用 32×32 或含多尺寸的 ico）
   - `frontend/public/apple-touch-icon.png`（180×180）
   - `frontend/public/icon-192.png`（192×192）
   - `frontend/public/icon-512.png`（512×512）
3. 导出方式任选其一即可：本机用 Inkscape / ImageMagick / Figma 从 SVG 导出；或用在线 SVG→PNG 工具。不要另起一套文件名。
4. 不改 H5 Tab。不改主题色 `#409EFF`（与这版 Logo 的蓝底一致）。

v1、v4-2、v4-4 留在 `icons/`，不要再接到页面上。预览页 `frontend/public/logo-hunteragent-preview.html` 可以留着，它不是用户入口。

**本步做完后怎么验证**

PC：

- 登录页和登录后侧栏的 Logo 是圆角 H，右上有 ai 胶囊，不是旧的 TradingAgents 图形。侧栏图片地址是 `/logo.svg?v=v4-3`。若仍是旧图，硬刷新一次。
- 浏览器标签页图标换成新图（必要时强刷）。页面文字仍是 HunterAgents，与步骤 1 一致。

H5：

- 底部三个 Tab 图标与改前相同，不要变成 PC 的 Logo。
- 「我的」文案仍是步骤 4 的结果。

### 步骤 6：单独的合规口径（本轮不做）

若要把界面上的「投资建议」改成「分析结论 / 策略讨论」，单独开一轮。只改展示标签，不改模型提示词，也不改已入库的报告正文。免责声明里的「不构成投资建议」保留。

涉及：`SingleAnalysis.vue`、`ReportDetail.vue`、`shareConfig.ts` 的 `MODULE_TITLES`、`chartData.ts`，以及 `shareConfig.test.ts`、`chartData.test.ts`、`conclusionCard.test.ts`。

**本步不验收。** PC 分析页、报告页、H5 分享页里的「投资建议」标题保持原样。

### 步骤 7：信息架构（本轮不做）

学习中心在侧栏对所有登录用户可见，首页还有推荐卡。文章标题大量是上游教程。若要降权，收进关于页或仅管理员可见。不要在换名时重写教程正文。模拟交易、股票筛选的菜单名不动。

**本步不验收。** PC 侧栏仍有「学习中心」，首页仍有学习中心卡片。H5 没有学习中心。

### 步骤 8：运维收尾（配域名时一并核对，不改品牌文案）

- 默认管理员密码若仍是 `admin123`，上线前改掉，不要写进 Git。
- `DEBUG=false` 后 `/docs` 会关掉。这是服务器 `.env`，不要为了改 Swagger 标题去改代码。
- Streamlit `web/` 若还在跑，关掉。那是另一个旧品牌入口（常见端口 8501）。怎么查看见下面「怎么确认 Streamlit 还在不在跑」。
- 短信签名不要改成产品名。本仓库 `.env` 已是 `北京万商云猫智汇`。Windows 服务器上若有另一份 `.env`，核对其 `SMS_SIGN_NAME` 也是这一串。改成 HunterAgents 会导致腾讯云拒发。
- OpenRouter 的 `X-Title`、`HTTP-Referer` 只出现在服务商后台。有余力再改，不挡上线。
- 安全组、防火墙放行 **80、443**。8000、3000、3100 不对公网开放。域名配好后停掉服务器上的 `npm run dev` 和 `npm run dev:h5`。见「服务器上要启动什么」。
- 服务器 `.env` 只改 `DEBUG=false`、`PUBLIC_APP_URL=https://hunteragents.cn`、`ALLOWED_ORIGINS`、`ALLOWED_HOSTS`。改完重启 `python -m app`。`SMS_SIGN_NAME` 保持「北京万商云猫智汇」。

**本步做完后怎么验证**

具体点击见下面「配完后怎么验收这条链路」。通过标准是：PC、H5 都用域名打开，并把步骤 1–5 的检查在域名上再做一遍。

PC（`https://hunteragents.cn/`）：

- 登录页、侧栏、首页、关于页、页脚与步骤 1、2、5 一致：HunterAgents、备案号、v4-3 Logo。
- 导出一份报告，落款仍是 HunterAgents（步骤 3）。
- `https://hunteragents.cn/docs` 打不开（`DEBUG=false`）。
- `https://hunteragents.cn/api/health` 返回 ok。

H5（`https://hunteragents.cn/m/`）：

- 「我的」与步骤 4 一致：版本 1.0、HunterAgents 来源说明、备案号。
- 报告列表点「查看报告」，地址是 `https://hunteragents.cn/s/...?from=app`。返回报告列表回到 `https://hunteragents.cn/m/#/pages/reports/list`。
- 从分享页导出 Markdown，落款是 HunterAgents。
- 用手机号收一条验证码，短信签名是「北京万商云猫智汇」。

#### 怎么确认 Streamlit `web/` 还在不在跑

在 Windows 服务器上开命令提示符：

```bat
netstat -ano | findstr ":8501"
tasklist | findstr /I "streamlit python"
```

浏览器试 `http://118.144.76.8:8501`。页面能打开、或 8501 有 LISTENING，就是还在跑。关掉对应窗口，或结束该 PID：

```bat
taskkill /PID 进程号 /F
```

没有 8501、浏览器打不开，就不用管。不要为了查这个去改代码。

#### 怎么确认有没有 Nginx，没有怎么装

在服务器上：

```bat
where nginx
dir C:\nginx\nginx.exe
```

`C:\nginx\nginx.exe` 存在，或 `where nginx` 能找到路径，就是已经装过，沿用该目录，不要再解压一套覆盖。再看是否在跑：

```bat
tasklist | findstr /I nginx
```

没有 `nginx.exe` 时：浏览器打开 https://nginx.org/en/download.html ，下 **Stable version** 的 Windows zip（例如 `nginx/Windows-1.28.x`）。不要下 Linux 源码包。解压到 `C:\nginx`，使 `C:\nginx\nginx.exe` 能直接运行。不要装到 Program Files（路径带空格，配置容易出错）。

装好后还没有站点配置。证书、`hunteragent.conf`、构建产物按下面「Windows 服务器」做完，再 `nginx.exe -t` 后启动。

---

## 域名：同域配置，返回列表不会跳错

### 推荐操作顺序

1. 阿里云解析 `@`、`www` 指向 `118.144.76.8`，本机 `ping hunteragents.cn` 已对。
2. 在阿里云申请免费证书（见下节），下载 Nginx 格式，上传到服务器。
3. 确认或安装 Nginx（步骤 8）。
4. 在服务器上 `npm run build`、`npm run build:h5`，拷到 `C:\nginx\html\pc` 和 `C:\nginx\html\m`。
5. 改服务器 `.env` 的 `PUBLIC_APP_URL` 等，重启后端。
6. 写好 `hunteragent.conf`，确认 `nginx.conf` 已 `include conf.d/*.conf;`，再 `nginx -t` 并启动。
7. 停掉服务器上的 3000、3100 开发服务，安全组关掉这两个端口和 8000。按文末验收清单只测域名。

### 服务器上要启动什么

已确认：**不需要 IP 加端口访问，也不做成 Windows 开机服务。**

域名不靠 `npm run dev` / `npm run dev:h5`。那两个是开发进程，分别听 3000 和 3100。正式站只用构建好的静态文件，所以这两个命令在服务器上不要再启动。

域名要起来，手动启动的是：

| 进程 | 作用 | 怎么开 |
|------|------|--------|
| Nginx | 提供 `https://hunteragents.cn/` 和 `/m/` 的页面，并把 `/api/` 转到本机 8000 | `cd /d C:\nginx` 后 `nginx.exe`（已在跑则 `nginx.exe -s reload`） |
| 后端 | 登录、分析、报告 | `cd /d D:\TradingAgents-CN-PLUS` 后 `python -m app` |

MongoDB、Redis 是这台机器上原有的 Windows 服务，重启后一般会自己起来。不用为它们再做开机项，也不要把 Nginx 或 `python -m app` 注册成开机服务。

Windows 重启之后：看一眼 MongoDB、Redis 是否在运行，然后手动启动 Nginx，再执行 `python -m app`。不要启动 3000 和 3100。

改前端之后要重新 `npm run build`、`npm run build:h5` 并拷到 `C:\nginx\html`，Nginx 才会换成新页面。不需要为了看新页面去开开发服务。

### 会不会出现「查看报告后返回列表报错」

按本节配置，**不会**。

现在的跳转是按「同一个网站」写的，不是按两个子域名写的：

1. H5 在 `https://hunteragents.cn/m/#/pages/reports/list` 点「查看报告」。
2. 打开 PC 分享页 `https://hunteragents.cn/s/{token}?from=app`。生产构建不要设置 `VITE_PUBLIC_APP_URL`，链接就用当前网页的域名。
3. 分享页「返回报告列表」在端口不是 3000 时，回到**当前域名**的 `/m/#/pages/reports/list`，也就是 `https://hunteragents.cn/m/#/pages/reports/list`。

登录态放在 `localStorage`，键名 PC 和 H5 相同（`auth-token`）。只有协议、主机、端口都一样时才共用。`hunteragents.cn` 的 `/` 和 `/m/` 是同一个站点，登录可以共用。

会坏的只有拆成两个子域名：PC 用 `admin.hunteragents.cn`、H5 用 `h5.hunteragents.cn`。返回会去 `admin` 下面的 `/m/`，登录也不互通。不要这样配。也不要用 IP 加 3000/3100 当入口：分享页若发现端口是 3000，会返回到 `:3100`，而正式环境这两个端口是关掉的。

用户只打开：

| 地址 | 说明 |
|------|------|
| `https://hunteragents.cn/` | PC，分享页 `/s/{token}` 也在这里 |
| `https://hunteragents.cn/m/` | H5 |

Nginx 配好后，`http://118.144.76.8/`（80、不带端口）跳到 `https://hunteragents.cn/`。不要给 IP 配 HTTPS。

后端 `PUBLIC_APP_URL` 改成 `https://hunteragents.cn`（不要末尾斜杠，不要带 3000）。仓库 `.env` 里若仍是 `http://118.144.76.8:3000`，那是开发机配置，不要原样拷到服务器当正式地址。通知和后端拼出来的分享链接都用 `PUBLIC_APP_URL`。

PC 自己的报告详情返回 `/reports`，本来就留在 PC，不受这次域名影响。

### 地址怎么分

| 地址 | 内容 |
|------|------|
| `https://hunteragents.cn/` | PC。分享页 `/s/{token}` 也在这里 |
| `https://www.hunteragents.cn/` | 只做跳转，跳到不带 www 的主站 |
| `https://hunteragents.cn/m/` | H5，例如 `/m/#/pages/reports/list` |
| `https://hunteragents.cn/api/` | Nginx 反代到本机 `127.0.0.1:8000` |

不要解析、不要做网站：`h5.hunteragents.cn`、`admin.hunteragents.cn`。H5 工程的 `publicPath` 和路由基路径已经是 `/m/`，不要改成子域名根路径。

### 阿里云解析

在阿里云「云解析 DNS」打开 `hunteragents.cn`。公网 IP 已确认是 `118.144.76.8`。

| 主机记录 | 记录类型 | 记录值 | 说明 |
|----------|----------|--------|------|
| `@` | A | `118.144.76.8` | 主站 `hunteragents.cn` |
| `www` | A | `118.144.76.8` | 只为了跳转到主站 |

不要添加主机记录 `h5`、`admin`。TTL 用默认即可。

保存后在自己电脑执行 `ping hunteragents.cn`，看到的 IP 与上面一致再申请证书。解析生效可能要几分钟到几小时。

备案已经完成的话，在备案控制台确认这个域名的接入 IP 就是这台服务器。解析指到别的 IP，备案接入会不一致。

### 证书（在阿里云申请，再上传到服务器）

你在阿里云控制台申请即可，不需要在服务器上用 certbot。

**要申请哪些域名**

| 证书绑定的域名 | 用途 | 是否必须 |
|----------------|------|----------|
| `hunteragents.cn` | 正式主站（PC、H5 `/m/`、API、分享页） | **必须** |
| `www.hunteragents.cn` | 把带 www 的访问跳到主站 | 建议有。若只做 `@`、不做 www 跳转，可以不申请 |

不要申请、也不需要：`h5.hunteragents.cn`、`admin.hunteragents.cn`、`*.hunteragents.cn`（通配）。H5 在主站路径 `/m/` 下，不单独占一个主机名。

阿里云「数字证书管理服务 / 免费证书」常见限制是一张免费 DV 证只绑 **一个** 域名。那就申请 **两张**：

1. 一张绑定 `hunteragents.cn`
2. 一张绑定 `www.hunteragents.cn`

若控制台当时允许一张证填多个域名，也可以只申请一张，同时写上这两个名字。以控制台实际可选为准。

**要什么格式**

下载时选 **Nginx**（或「其他」里带 Nginx 字样的包）。需要这两个文件：

- 证书文件：一般是 `.pem`（有的包里叫 `xxx.pem` 或把证书链拼好的文件）
- 私钥文件：`.key`

不要下：Tomcat 的 `.jks`、IIS 的 `.pfx`（除非你自己会转换）。本机 Nginx 配置写的是 `ssl_certificate` + `ssl_certificate_key`，对应 pem + key。

**验证方式**

优先用控制台给的 **DNS 验证**：按提示在云解析里加一条 TXT 或 CNAME，签发后这条验证记录可以删。机器上还没装 Nginx、80 还不通时，DNS 验证最省事。不要依赖「文件验证」，除非 80 已经能从公网访问。

**上传到服务器放哪里**

在服务器建目录（若还没有）：

```text
C:\nginx\conf\cert\
```

上传后建议改成下面这些名字，和后文 Nginx 配置一致（你也可以保留阿里云下载的原名，但要把配置里的路径改成一致）：

```text
C:\nginx\conf\cert\hunteragents.cn.pem
C:\nginx\conf\cert\hunteragents.cn.key
C:\nginx\conf\cert\www.hunteragents.cn.pem
C:\nginx\conf\cert\www.hunteragents.cn.key
```

若两张证其实是同一套文件（一张证绑了两个域名），两处 `ssl_certificate` 都指向同一对 pem/key 即可。

`.key` 是私钥：只放服务器，不要进 Git、不要发到聊天或邮件。免费证一般一年，到期前在同一控制台续期或重申请，换文件后执行 `nginx -s reload`。

### Windows 服务器

与 `Windows非Docker升级部署.md` 的 F 节同一做法，下面把域名写成 `hunteragents.cn`。代码目录已确认是 `D:\TradingAgents-CN-PLUS`。不要为了上域名去改文件夹名。

1. 云服务器安全组和 Windows 防火墙放行 **80、443**。关掉 3000、3100、8000 的公网放行。服务器上若还开着 `npm run dev`、`npm run dev:h5`，停掉对应窗口。
2. 按步骤 8 确认有没有 Nginx。没有则从 https://nginx.org/en/download.html 下 Windows Stable zip，解压到 `C:\nginx`。已经有 `C:\nginx\nginx.exe` 就不要再解压覆盖。不要把 Nginx 注册成 Windows 服务。
3. 域名用构建产物。H5 必须用生产配置构建，这样不会把 `mobile/.env.development` 里的 `http://118.144.76.8:3000` 打进包。`mobile/.env.production` 保持 `VITE_API_BASE` 为空，且不要新增 `VITE_PUBLIC_APP_URL`。构建完即可关掉 Node 开发进程；Nginx 读的是拷过去的静态文件。

```bat
cd /d D:\TradingAgents-CN-PLUS\frontend
npm run build
cd /d D:\TradingAgents-CN-PLUS\mobile
npm run build:h5
```

4. 拷贝产物：

- `frontend\dist` 的内容 → `C:\nginx\html\pc`
- `mobile\dist\build\h5` 的内容 → `C:\nginx\html\m`（`index.html` 在 `C:\nginx\html\m\index.html`）

5. 后端继续只监听 `127.0.0.1:8000`。在服务器那份 `.env`（不要提交 Git）改为：

```ini
DEBUG=false
PUBLIC_APP_URL=https://hunteragents.cn
ALLOWED_ORIGINS=["https://hunteragents.cn"]
ALLOWED_HOSTS=["hunteragents.cn"]
```

`PUBLIC_APP_URL` 不要末尾斜杠。`SMS_SIGN_NAME` 保持 `北京万商云猫智汇`。改完重启 `python -m app`。

6. Nginx。打开 `C:\nginx\conf\nginx.conf`，在 `http { }` 里确认有这一行（默认 Windows 包常常没有，需要自己加）：

```nginx
include conf.d/*.conf;
```

没有就加在 `http { }` 内靠前的位置，保存。再建目录 `C:\nginx\conf\conf.d\`（若没有），新建 `C:\nginx\conf\conf.d\hunteragent.conf`：

```nginx
server {
    listen 80 default_server;
    server_name _;
    return 301 https://hunteragents.cn$request_uri;
}

server {
    listen 80;
    server_name hunteragents.cn www.hunteragents.cn;
    return 301 https://hunteragents.cn$request_uri;
}

server {
    listen 443 ssl;
    server_name www.hunteragents.cn;
    ssl_certificate     C:/nginx/conf/cert/www.hunteragents.cn.pem;
    ssl_certificate_key C:/nginx/conf/cert/www.hunteragents.cn.key;
    ssl_protocols       TLSv1.2 TLSv1.3;
    return 301 https://hunteragents.cn$request_uri;
}

server {
    listen 443 ssl;
    server_name hunteragents.cn;
    client_max_body_size 100m;

    ssl_certificate     C:/nginx/conf/cert/hunteragents.cn.pem;
    ssl_certificate_key C:/nginx/conf/cert/hunteragents.cn.key;
    ssl_protocols       TLSv1.2 TLSv1.3;

    root C:/nginx/html/pc;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /m/ {
        alias C:/nginx/html/m/;
        index index.html;
        try_files $uri $uri/ /m/index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }
}
```

www 和主站若合在同一张证书里，两处 `ssl_certificate` 都指向那一对 pem/key。`/s/` 由 PC 前端路由处理，走 `location /`，不要单独反代。`X-Real-IP` 和 `X-Forwarded-For` 要保留，短信按 IP 限流靠它们。

`listen 80 default_server` 用来接住 `http://118.144.76.8/`（不带端口），跳到 `https://hunteragents.cn/`。不要给 IP 配 HTTPS。不要再启动 3000、3100。

```bat
cd /d C:\nginx
nginx.exe -t
nginx.exe
```

已经在跑时用 `nginx.exe -s reload`。不要注册成开机服务。

Windows 重启后手动再开（MongoDB、Redis 若已是系统服务，先确认它们在跑即可）：

```bat
cd /d C:\nginx
nginx.exe
cd /d D:\TradingAgents-CN-PLUS
python -m app
```

### 配完后怎么验收这条链路

先确认构建产物已拷进 Nginx，再按步骤 8 的 PC / H5 清单在域名上重看步骤 1–5。另外：

- `https://hunteragents.cn/` 和 `https://hunteragents.cn/m/` 地址栏没有端口号，是锁，证书域名是 hunteragents.cn。
- `https://www.hunteragents.cn/` 跳到不带 www 的主站。
- `http://118.144.76.8:3000` 和 `:3100` 打不开。
- 把分享链接发到微信，预览地址是 `https://hunteragents.cn/`，不是 `tradingagents.cn`。

---

## 本轮不要改

- 菜单 icon、智能体名字、数据源、分析流程、模型提示词
- Git 仓库名、依赖包名、Mongo 库名 `tradingagents`、服务器项目目录名
- `package.json` 描述、锁文件、代码注释
- 配置管理里「TradingAgents（可选）」分区名
- 邮箱占位 `admin@example.com`
- 引擎日志和 User-Agent
- 侧栏是否只保留管理员 / 普通用户两档
- 分享链接是否继续免登录
- 短信签名（已是审核名，不要改成产品名）
- H5 的 `/m/` 基路径

---

## 建议怎么提交

步骤 1–5 可以同一分支、按步骤分成几次提交。域名和证书只改服务器，不进 Git。

每步改完后搜 `TradingAgents-CN`：

- 步骤 1 之后，`frontend/src` 的 `.vue` / `.html` 里，旧产品名应只剩关于页、学习中心、配置分区名。
- 步骤 2 之后，关于页只在致谢里出现 TradingAgents，且写明是上游。
- 步骤 3 之后，全仓库「本报告由 TradingAgents-CN」应为 0。
- 步骤 4 之后，`mobile/src` 里 TradingAgents-CN 不再作为产品名出现。协议里的上游许可说明可以留。

---

## 上线验收（步骤 1–5 加上域名配完）

- 未登录：登录页、浏览器标题、PWA 安装名是 HunterAgents。登录页 Logo 是 v4-3（H + ai 胶囊）。
- 已登录：侧栏、首页、页脚是 HunterAgents，版本不是 preview。
- 页脚、登录页、关于页、分享页、H5「我的」页能看到 `京ICP备2021035986号-4`。
- 分享链接页眉是 HunterAgents；导出文件名是 `{代码}_{日期}_HunterAgents`；正文落款是 HunterAgents。
- 关于页联系方式只有 `ocm@onecloudmall.com`。致谢可以出现 TradingAgents。
- H5 查看报告再返回，回到 `https://hunteragents.cn/m/#/pages/reports/list`。
- 链接预览是 `https://hunteragents.cn/`。
- 「投资建议」区块标题、菜单 icon，本轮不作为验收项。

---

## Logo

| 版本 | 文件 | 状态 |
|------|------|------|
| v4-3 | `icons/hunteragent-v4-3-ai-pill.svg` | **选用**。实现时覆盖 `frontend/public/logo.svg` 并导出 favicon / PWA 图标 |
| v1 | `icons/hunteragent-v1.svg` | 不选用，保留文件 |
| v4-2 | `icons/hunteragent-v4-2-ai-star.svg` | 不选用，保留文件 |
| v4-4 | `icons/hunteragent-v4-4-ai-gradient.svg` | 不选用，保留文件 |

预览：用浏览器打开 `frontend/public/logo-hunteragent-preview.html`，或在 PC 开发服务下打开 `http://localhost:3000/logo-hunteragent-preview.html`。

H5 Tab PNG 已在 `mobile/src/static/`。步骤 4、步骤 5 都不重新导出。

---

## 已确认、本轮不再改口

- 用户协议、隐私政策继续写「本公司」，不改成公司全称。页脚也不写公司全称。
- 没有京公网安备号。页脚只放 `京ICP备2021035986号-4`。
- 公网 IP 是 `118.144.76.8`。代码目录是 `D:\TradingAgents-CN-PLUS`。正式只走域名，不提供 IP 加端口访问。
- 服务器不启动 `npm run dev`（3000）和 `npm run dev:h5`（3100）。域名由 Nginx 加 `python -m app` 提供。
- Windows 重启后不做开机服务。手动启动 Nginx 和 `python -m app`。MongoDB、Redis 沿用现有系统服务。
- 短信签名保持「北京万商云猫智汇」。
- 证书：在阿里云申请免费 DV，绑定 `hunteragents.cn`（必须）和 `www.hunteragents.cn`（建议）；下载 **Nginx** 格式（`.pem` + `.key`），上传到 `C:\nginx\conf\cert\`。
