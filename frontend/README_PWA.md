# PWA 应用快速启动指南

## 🚀 快速开始

### 方法一：使用自动化脚本（推荐）

**Windows (PowerShell):**
```powershell
.\scripts\setup-pwa.ps1
```

**Linux/Mac:**
```bash
chmod +x scripts/setup-pwa.sh
./scripts/setup-pwa.sh
```

脚本会自动：
1. ✅ 检查 Node.js 环境
2. ✅ 安装项目依赖
3. ✅ 生成 PWA 图标
4. ✅ 验证资源完整性
5. ✅ 启动开发服务器

### 方法二：手动设置

#### 步骤 1: 安装依赖
```bash
cd frontend
npm install
```

#### 步骤 2: 生成 PWA 图标
```bash
# 使用 Node.js 脚本
node scripts/generate-pwa-icons.js

# 或者启动开发服务器后访问浏览器工具
# http://localhost:3000/generate-icons.html
```

#### 步骤 3: 启动开发服务器
```bash
npm run dev
```

## 📱 测试 PWA 功能

### 1. 验证基础配置

访问 http://localhost:3000 后：

1. 打开浏览器开发者工具 (F12)
2. 切换到 **Application** 标签
3. 检查以下项目：
   - **Manifest**: 查看应用名称、图标、主题色
   - **Service Workers**: 确认 SW 已注册且状态为 "activated"
   - **Storage**: 查看缓存的资源

### 2. 测试安装功能

**桌面端 (Chrome/Edge):**
- 地址栏右侧会出现安装图标 ⊕
- 点击安装图标
- 或等待 5 秒后自动弹出安装提示

**移动端 (Chrome/Safari):**
- Chrome: 菜单 → "安装应用"
- Safari: 分享按钮 → "添加到主屏幕"

### 3. 测试离线功能

1. 在开发者工具中切换到 **Network** 标签
2. 勾选 **Offline** 复选框
3. 刷新页面
4. 应用应该仍然可以访问（显示缓存的内容）

### 4. 测试移动端适配

在开发者工具中：

1. 点击设备工具栏图标 (Ctrl+Shift+M)
2. 测试不同设备：
   - **iPhone SE** (375x667) - 小屏手机
   - **iPhone 12 Pro** (390x844) - 标准手机
   - **iPad** (768x1024) - 平板
   - **iPad Pro** (1024x1366) - 大平板

重点检查：
- ✅ 页面布局是否正常
- ✅ 文字是否清晰可读
- ✅ 按钮是否足够大（≥44px）
- ✅ 表单是否易于填写
- ✅ 滚动是否流畅

## 🔧 常见问题排查

### 问题 1: Service Worker 未注册

**症状**: Application 标签中看不到 Service Worker

**解决方案**:
1. 确保使用 `localhost` 或 HTTPS
2. 检查浏览器控制台是否有错误
3. 清除浏览器缓存后重试
4. 确认 vite-plugin-pwa 已安装：
   ```bash
   npm list vite-plugin-pwa
   ```

### 问题 2: 图标未显示

**症状**: Manifest 中图标显示 404

**解决方案**:
1. 运行图标生成脚本：
   ```bash
   node scripts/generate-pwa-icons.js
   ```
2. 检查 `frontend/public/` 目录是否包含：
   - icon-192.png
   - icon-512.png
   - apple-touch-icon.png
3. 刷新页面并清除缓存

### 问题 3: 移动端布局错乱

**症状**: 在手机上页面显示不正常

**解决方案**:
1. 清除浏览器缓存
2. 检查 viewport meta 标签
3. 使用开发者工具的设备模拟器调试
4. 检查 CSS 媒体查询是否生效

### 问题 4: 无法安装应用

**症状**: 没有看到安装提示

**可能原因**:
1. 之前点击了"不再提示"
   - **解决**: 清除 localStorage: `localStorage.removeItem('pwa_install_never_show')`
2. 应用已经安装
   - **解决**: 检查是否已在独立窗口运行
3. 浏览器不支持 PWA
   - **解决**: 使用 Chrome、Edge 或 Safari

### 问题 5: 更新不生效

**症状**: 修改代码后看不到变化

**解决方案**:
1. 硬刷新: Ctrl+Shift+R (Windows) / Cmd+Shift+R (Mac)
2. 在 Application > Service Workers 中点击 "Unregister"
3. 清除所有缓存
4. 重启开发服务器

## 📊 PWA 评分检查

使用 Lighthouse 检查 PWA 质量：

1. 打开 Chrome 开发者工具
2. 切换到 **Lighthouse** 标签
3. 选择 **Progressive Web App** 类别
4. 点击 **Generate report**

目标分数：
- ✅ Performance: ≥90
- ✅ Accessibility: ≥90
- ✅ Best Practices: ≥90
- ✅ SEO: ≥90
- ✅ PWA: 满分

## 🎯 移动端测试清单

### 单股分析页面测试

在移动设备或模拟器上测试以下功能：

#### 基础交互
- [ ] 页面加载速度 < 3秒
- [ ] 标题和描述清晰可见
- [ ] 卡片布局正常显示

#### 表单输入
- [ ] 股票代码输入框正常
- [ ] 市场选择下拉框易于操作
- [ ] 日期选择器适配移动端
- [ ] 表单标签不遮挡输入框

#### 分析深度选择
- [ ] 深度选项卡片单列显示
- [ ] 点击区域足够大
- [ ] 选中状态明显
- [ ] 文字大小适中

#### 分析师选择
- [ ] 分析师卡片单列显示
- [ ] 头像和文字清晰
- [ ] 选中状态明显
- [ ] 滚动流畅

#### 操作按钮
- [ ] 按钮全宽显示
- [ ] 按钮高度 ≥44px
- [ ] 按钮文字清晰
- [ ] 点击反馈明显

#### 进度显示
- [ ] 进度条正常显示
- [ ] 统计信息布局合理
- [ ] 当前任务信息清晰
- [ ] 不会横向滚动

#### 结果展示
- [ ] 结果卡片正常显示
- [ ] 文字大小适中
- [ ] 标题和内容层次分明
- [ ] 可以正常滚动

## 📝 部署到生产环境

### 构建应用
```bash
cd frontend
npm run build
```

### 检查构建产物
```bash
ls dist/
# 应该包含：
# - index.html
# - manifest.json
# - icon-192.png
# - icon-512.png
# - apple-touch-icon.png
# - sw.js (Service Worker)
# - assets/ (CSS, JS, 图片等)
```

### 部署要求

1. **HTTPS 必需**
   - PWA 必须在 HTTPS 环境下运行
   - localhost 除外（开发环境）

2. **正确的 MIME 类型**
   ```nginx
   # Nginx 配置示例
   location /manifest.json {
       types { application/manifest+json json; }
   }
   
   location /sw.js {
       types { application/javascript js; }
       add_header Cache-Control "no-cache";
   }
   ```

3. **缓存策略**
   ```nginx
   # 静态资源长期缓存
   location ~* \.(png|jpg|jpeg|gif|ico|svg)$ {
       expires 1y;
       add_header Cache-Control "public, immutable";
   }
   
   # Service Worker 不缓存
   location /sw.js {
       add_header Cache-Control "no-cache";
   }
   ```

### 验证部署

1. 访问生产环境 URL
2. 检查 HTTPS 证书
3. 打开开发者工具验证 PWA 功能
4. 测试安装和离线功能
5. 使用 Lighthouse 评分

## 🎓 学习资源

- [PWA 官方文档](https://web.dev/progressive-web-apps/)
- [Vite PWA 插件文档](https://vite-pwa-org.netlify.app/)
- [Workbox 缓存策略](https://developer.chrome.com/docs/workbox/caching-strategies-overview/)
- [Web App Manifest](https://developer.mozilla.org/en-US/docs/Web/Manifest)

## 💬 获取帮助

如果遇到问题：

1. 查看 `frontend/PWA_IMPLEMENTATION_SUMMARY.md` 了解实现细节
2. 查看 `frontend/public/ICON_GENERATION_GUIDE.md` 了解图标生成方法
3. 检查浏览器控制台的错误信息
4. 在项目 Issues 中搜索类似问题
5. 提交新的 Issue 并附上详细信息

---

**祝您使用愉快！** 🎉

