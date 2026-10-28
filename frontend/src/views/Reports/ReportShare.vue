<template>
  <div class="report-share">
    <div v-if="loading" class="share-status">
      <div class="spinner" />
      <p>正在加载报告…</p>
    </div>

    <div v-else-if="error" class="share-status share-status--error">
      <a class="back-list" :href="reportListUrl" @click="logBackToList">返回报告列表</a>
      <h1>链接已失效</h1>
      <p>{{ error }}</p>
      <p class="hint">请向分享者重新索取链接，或返回报告列表重新打开。</p>
    </div>

    <article v-else-if="report" class="share-article">
      <ShareHeader :report="report" />

      <DeptTabs
        :departments="departments"
        :roles="activeDept?.roles || []"
        :active-dept-key="location.tab"
        :active-role-key="location.role"
        :show-sub-tabs="showSubTabs"
        @select="onSelectDept"
        @select-role="selectRole"
      />

      <OverviewPanel
        v-if="location.tab === OVERVIEW_DEPT_KEY"
        :report="report"
        :departments="departments"
        @navigate="onOverviewNavigate"
      />

      <RolePanel v-else-if="activeRole" :role="activeRole" />

      <footer class="disclaimer">
        <h2>风险提示与免责声明</h2>
        <ul>
          <li>本系统为股票分析辅助工具，不具备证券投资咨询资质。</li>
          <li>所有分析结果仅为技术分析参考，不构成买卖建议。</li>
          <li>分析基于历史与公开信息，无法预测未来走势，投资有风险。</li>
          <li>投资决策及其后果由投资者自行承担。</li>
        </ul>
      </footer>
    </article>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import DeptTabs from './share/DeptTabs.vue'
import OverviewPanel from './share/OverviewPanel.vue'
import RolePanel from './share/RolePanel.vue'
import ShareHeader from './share/ShareHeader.vue'
import { OVERVIEW_DEPT_KEY, logBackToList, resolveReportListUrl } from './share/shareConfig'
import { useShareReport } from './share/useShareReport'

const reportListUrl = resolveReportListUrl()

const {
  loading,
  error,
  report,
  departments,
  activeDept,
  activeRole,
  showSubTabs,
  location,
  selectTarget,
  selectRole,
  fetchSharedReport,
} = useShareReport()

function onSelectDept(deptKey: string): void {
  selectTarget(deptKey)
}

/** 决策链点击跳转到对应岗位：回顶 + 更新 URL 定位 */
function onOverviewNavigate(tab: string, role: string): void {
  selectTarget(tab, role)
}

onMounted(() => {
  fetchSharedReport()
})
</script>

<style lang="scss" scoped>
.report-share {
  min-height: 100vh;
  background: #f5f7fa;
  color: #303133;
}

.share-status {
  max-width: 720px;
  margin: 0 auto;
  padding: 80px 20px;
  text-align: center;

  h1 {
    font-size: 22px;
    margin: 0 0 12px;
  }

  p {
    font-size: 16px;
    line-height: 1.7;
    color: #909399;
    margin: 0;
  }

  .hint {
    margin-top: 8px;
    font-size: 14px;
  }
}

.share-status .back-list {
  display: inline-flex;
  margin-bottom: 20px;
  color: #3b82f6;
  font-size: 14px;
  text-decoration: none;
}

.spinner {
  width: 32px;
  height: 32px;
  margin: 0 auto 16px;
  border: 3px solid #d9dce3;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.share-article {
  max-width: 720px;
  margin: 0 auto;
  padding: 20px 16px 48px;
}

.disclaimer {
  background: #fdf1e0;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 14px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);

  h2 {
    margin: 0 0 12px;
    font-size: 16px;
    line-height: 1.4;
    color: #303133;
  }

  ul {
    margin: 0;
    padding-left: 18px;
  }

  li {
    font-size: 14px;
    line-height: 1.7;
    color: #606266;
    margin-bottom: 6px;
  }
}

@media (max-width: 480px) {
  .share-article {
    padding: 16px 12px 40px;
  }
}
</style>

<style lang="scss">
/* 压过 html.dark h1–h6 { color: #fff !important }，分享页固定浅色底 */
html.dark .report-share h1,
html.dark .report-share h2,
html.dark .report-share h3,
html.dark .report-share h4,
html.dark .report-share h5,
html.dark .report-share h6 {
  color: #303133 !important;
}

html.dark .report-share .section-head {
  color: #909399 !important;
  font-size: 13px !important;
  font-weight: 400 !important;
}
</style>