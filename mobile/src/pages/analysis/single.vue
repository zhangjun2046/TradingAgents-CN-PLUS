<template>
  <view class="ha-page single-page">
    <!-- 表单视图：无进行中任务时显示 -->
    <template v-if="showForm">
    <!-- 标题卡 -->
    <view class="intro-card">
      <view class="intro-title">单股分析</view>
      <view class="intro-sub">AI驱动的智能股票分析，多维度评估投资价值与风险</view>
    </view>

    <!-- 分析配置 -->
    <view class="section-card">
      <view class="section-head">
        <text class="section-head-title">分析配置</text>
        <text class="section-head-badge">必填信息</text>
      </view>
      <view class="section-body">
        <!-- 1. 股票代码 -->
        <view class="field">
          <view class="field-label">
            <text class="field-label-text"><text class="required">*</text>股票代码</text>
          </view>
          <StockCodeInput
            v-model="form.symbol"
            :placeholder="currentMarket.placeholder"
            :valid="codeCheck.valid"
            :message="codeTip"
            :show-error="showCodeError"
            :stock-name="stockName"
          />
        </view>

        <!-- 2. 市场类型 -->
        <view class="field">
          <view class="field-label"><text class="field-label-text">市场类型</text></view>
          <picker
            mode="selector"
            :range="marketLabels"
            :value="marketIndex"
            @change="onMarketChange"
          >
            <view class="select-box">
              <text class="select-badge">{{ currentMarket.badge }}</text>
              <text class="select-main">{{ form.market }}市场</text>
              <text class="select-hint">（{{ currentMarket.hint }}）</text>
              <text class="select-arrow">▾</text>
            </view>
          </picker>
        </view>

        <!-- 3. 分析日期 -->
        <view class="field">
          <view class="field-label"><text class="field-label-text">分析日期</text></view>
          <uni-datetime-picker
            v-model="form.analysisDate"
            type="date"
            :end="todayStr"
            :clear-icon="false"
            @change="onDateChange"
          />
        </view>

        <!-- 4. 分析深度 -->
        <view class="field">
          <view class="field-label field-label-row">
            <text class="field-label-text">分析深度</text>
            <text class="field-label-extra">默认：3级标准分析</text>
          </view>
          <DepthSelector v-model="form.depthLevel" />
        </view>

        <!-- 5. 分析师团队 -->
        <view class="field">
          <view class="field-label field-label-row">
            <text class="field-label-text">分析师团队</text>
            <text class="field-label-extra">已选中 {{ form.analystIds.length }} 位</text>
          </view>
          <AnalystCards v-model="form.analystIds" :social-disabled="isAShare" />
        </view>
      </view>
    </view>

    <!-- 高级配置 -->
    <view class="section-card">
      <view class="section-head">
        <text class="section-head-title">高级配置</text>
        <text class="section-head-badge is-optional">可选设置</text>
      </view>
      <view class="section-body">
        <view class="field">
          <view class="field-label field-label-row">
            <text class="field-label-text">快速分析模型（市场 / 新闻 / 基本面）</text>
          </view>
          <ModelSelect
            v-model="form.quickModel"
            :options="quickOptions"
            variant="quick"
          />
        </view>
        <view class="field">
          <view class="field-label field-label-row">
            <text class="field-label-text">深度决策模型（研究经理 / 风险经理）</text>
          </view>
          <ModelSelect
            v-model="form.deepModel"
            :options="deepOptions"
            variant="deep"
          />
        </view>
      </view>
    </view>

    <!-- 为底部固定按钮预留空间 -->
    <view class="bottom-spacer"></view>
    <view class="submit-bar">
      <button
        class="submit-btn"
        :loading="submitting"
        :disabled="submitting"
        @click="onSubmit"
      >
        {{ submitting ? "提交中..." : "↗ 开始智能分析" }}
      </button>
    </view>
    </template>

    <!-- 进度视图：有进行中 / 已完成 / 失败的任务时显示（tech_solution 4.1.4） -->
    <template v-else-if="analysis.meta">
      <!-- 任务摘要 -->
      <view class="task-card">
        <view class="task-main">
          <view class="task-top">
            <text class="task-market">{{ analysis.meta.market }}</text>
            <text class="task-title">{{ taskTitle }}</text>
          </view>
          <view class="task-sub">
            基准日：{{ analysis.meta.analysisDate }} · {{ analysis.meta.depthLevel }}级{{ analysis.meta.depthName }}分析
          </view>
        </view>
        <view class="task-side">
          <text class="task-status" :class="`is-${analysis.phase}`">{{ phaseText }}</text>
          <text class="task-reset" @click="onReconfigure">重新配置</text>
        </view>
      </view>

      <!-- 进度（进行中 / 已完成 / 中断） -->
      <AnalysisProgress
        v-if="analysis.phase !== 'failed'"
        :progress="analysis.progress"
        :completed="analysis.phase === 'completed'"
        :step-name="analysis.currentStepName"
        :message="analysis.message"
        :elapsed-seconds="analysis.elapsedSeconds"
        :remaining-seconds="analysis.remainingSeconds"
        :analyst-names="analysis.meta.analystNames"
        :steps="analysis.steps"
      />

      <!-- 完成 -->
      <view v-if="analysis.phase === 'completed'" class="result-card is-success">
        <view class="result-icon is-success">✓</view>
        <view class="result-title">可以查看分析报告</view>
        <view class="result-desc">
          {{ taskTitle }}多智能体综合研判报告已生成完毕，点击下方按钮立即跳转至报告分享页查阅完整内容。
        </view>

        <view class="share-box">
          <view class="share-main">
            <view class="share-label">
              专属报告分享链接（免登录直接查阅）<template v-if="analysis.shareExpiresAt">· 有效期至 {{ analysis.shareExpiresAt.slice(0, 10) }}</template>
            </view>
            <view v-if="analysis.shareUrl" class="share-url">{{ analysis.shareUrl }}</view>
            <view v-else-if="analysis.shareLoading" class="share-url is-muted">链接生成中...</view>
            <view v-else class="share-url is-error">{{ analysis.shareError || "链接尚未生成" }}</view>
          </view>
          <view v-if="analysis.shareUrl" class="share-copy" @click="onCopyLink">复制</view>
          <view v-else-if="!analysis.shareLoading" class="share-copy" @click="analysis.prepareShare()">重试</view>
        </view>

        <button class="result-btn is-success" :loading="analysis.shareLoading" @click="analysis.openReport()">
          立即查看分析报告 ↗
        </button>
        <button class="result-btn is-plain" @click="onNewAnalysis">继续分析其他股票</button>
      </view>

      <!-- 失败 -->
      <view v-else-if="analysis.phase === 'failed'" class="result-card is-danger">
        <view class="result-icon is-danger">!</view>
        <view class="result-title">分析未能完成</view>
        <view class="result-desc is-error">{{ analysis.errorMessage }}</view>
        <button class="result-btn is-danger" :loading="submitting" :disabled="submitting" @click="onRetry">
          重新分析
        </button>
        <button class="result-btn is-plain" @click="onNewAnalysis">返回修改参数</button>
      </view>

      <!-- 查询中断 -->
      <view v-else-if="analysis.phase === 'timeout'" class="result-card is-warning">
        <view class="result-icon is-warning">?</view>
        <template v-if="analysis.timeoutReason === 'network'">
          <view class="result-title">网络异常</view>
          <view class="result-desc">连续多次查询进度失败，分析任务仍在后台运行，请检查网络后继续查询。</view>
          <button class="result-btn is-primary" @click="analysis.continuePolling()">继续查询</button>
        </template>
        <template v-else>
          <view class="result-title">分析时间较长</view>
          <view class="result-desc">本次分析已超过 30 分钟，页面不再自动查询。分析完成后可前往「分析报告」查看。</view>
          <button class="result-btn is-primary" @click="goReports">前往分析报告</button>
        </template>
        <button class="result-btn is-plain" @click="onNewAnalysis">继续分析其他股票</button>
      </view>

      <view class="bottom-spacer"></view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import { onHide, onShow } from "@dcloudio/uni-app";
import StockCodeInput from "@/components/StockCodeInput.vue";
import DepthSelector from "@/components/DepthSelector.vue";
import AnalystCards from "@/components/AnalystCards.vue";
import ModelSelect from "@/components/ModelSelect.vue";
import AnalysisProgress from "@/components/AnalysisProgress.vue";
import { useAuthStore } from "@/stores/auth";
import { useAnalysisStore } from "@/stores/analysis";
import { getPublicModels } from "@/api/config";
import {
  buildSingleAnalysisPayload,
  depthLevelToName,
  getStockName,
} from "@/api/analysis";
import {
  DEFAULT_DEPTH_LEVEL,
  DEFAULT_MARKET,
  MARKETS,
  type MarketType,
} from "@/constants/analysis";
import {
  ANALYSTS,
  DEFAULT_ANALYST_IDS,
  SOCIAL_ANALYST_ID,
} from "@/constants/analysts";
import type { PublicModel, PublicModelsData } from "@/constants/models";
import { isFutureDate, today, validateStockCode } from "@/utils/validators";

const auth = useAuthStore();
const analysis = useAnalysisStore();

const todayStr = today();

const form = reactive({
  symbol: "",
  market: DEFAULT_MARKET as MarketType,
  analysisDate: todayStr,
  depthLevel: DEFAULT_DEPTH_LEVEL,
  analystIds: [...DEFAULT_ANALYST_IDS] as string[],
  quickModel: "",
  deepModel: "",
});

const submitting = ref(false);
/** 用户点过「开始智能分析」后，空代码也展示错误态 */
const submitTried = ref(false);
const stockName = ref("");
const models = ref<PublicModelsData | null>(null);

// ---------- 市场 ----------
const marketLabels = MARKETS.map(
  (m) => `${m.badge} ${m.value}市场（${m.hint}）`
);
const marketIndex = computed(() =>
  MARKETS.findIndex((m) => m.value === form.market)
);
const currentMarket = computed(() => MARKETS[marketIndex.value] || MARKETS[0]);
const isAShare = computed(() => form.market === "A股");

function onMarketChange(e: { detail: { value: number | string } }) {
  const next = MARKETS[Number(e.detail.value)];
  if (next) form.market = next.value;
}

// 切到 A 股时自动剔除社媒分析师
watch(
  () => form.market,
  (market) => {
    if (market === "A股" && form.analystIds.includes(SOCIAL_ANALYST_ID)) {
      form.analystIds = form.analystIds.filter((id) => id !== SOCIAL_ANALYST_ID);
    }
    stockName.value = "";
  },
  { immediate: true }
);

// ---------- 股票代码校验 ----------
const codeCheck = computed(() => validateStockCode(form.symbol, form.market));
const codeTip = computed(() => {
  if (codeCheck.value.empty) return submitTried.value ? codeCheck.value.message : "";
  return codeCheck.value.message;
});
const showCodeError = computed(
  () => !codeCheck.value.valid && (!codeCheck.value.empty || submitTried.value)
);

// ---------- 日期 ----------
function onDateChange(value: string) {
  if (value && isFutureDate(value)) {
    uni.showToast({ title: "不能选择未来日期", icon: "none" });
    form.analysisDate = todayStr;
  }
}

// ---------- 模型 ----------
function filterByRole(list: PublicModel[], role: string): PublicModel[] {
  const matched = list.filter(
    (m) => m.roles.includes(role) || m.roles.includes("both")
  );
  // 角色标注缺失时不让下拉为空
  return matched.length > 0 ? matched : list;
}

const quickOptions = computed(() =>
  models.value ? filterByRole(models.value.models, "quick_analysis") : []
);
const deepOptions = computed(() =>
  models.value ? filterByRole(models.value.models, "deep_analysis") : []
);

/** 保留用户已选且仍有效的模型；否则取默认模型，再否则取列表第一项 */
function pickModel(
  current: string,
  preferred: string | null,
  options: PublicModel[]
): string {
  const names = options.map((o) => o.name);
  if (current && names.includes(current)) return current;
  if (preferred && names.includes(preferred)) return preferred;
  return names[0] || "";
}

async function loadModels() {
  const { data, fromFallback } = await getPublicModels();
  models.value = data;
  form.quickModel = pickModel(
    form.quickModel,
    data.default_quick_model,
    quickOptions.value
  );
  form.deepModel = pickModel(
    form.deepModel,
    data.default_deep_model,
    deepOptions.value
  );
  console.info("[Analysis] models ready", {
    fromFallback,
    quick: form.quickModel,
    deep: form.deepModel,
  });
}

// ---------- 股票名称标签（防抖，失败静默） ----------
let nameTimer: ReturnType<typeof setTimeout> | null = null;
watch(
  () => [codeCheck.value.valid, codeCheck.value.normalized, form.market] as const,
  ([valid, code]) => {
    if (nameTimer) clearTimeout(nameTimer);
    stockName.value = "";
    // 未登录时接口会 401 并触发全局跳转，故仅登录后查询
    if (!valid || !auth.isLoggedIn) return;
    nameTimer = setTimeout(async () => {
      const name = await getStockName(code);
      if (codeCheck.value.normalized === code) stockName.value = name;
    }, 400);
  }
);

// ---------- 提交 ----------
function goLogin() {
  const redirect = encodeURIComponent("/pages/analysis/single");
  uni.navigateTo({ url: `/pages/auth/login?redirect=${redirect}` });
}

function validateForm(): boolean {
  submitTried.value = true;
  if (!codeCheck.value.valid) {
    uni.showToast({ title: codeCheck.value.message, icon: "none" });
    return false;
  }
  if (form.analystIds.length === 0) {
    uni.showToast({ title: "请至少选择一个分析师", icon: "none" });
    return false;
  }
  if (isFutureDate(form.analysisDate)) {
    uni.showToast({ title: "不能选择未来日期", icon: "none" });
    return false;
  }
  return true;
}

async function onSubmit() {
  if (submitting.value) return;
  if (!validateForm()) return;

  auth.hydrateFromStorage();
  if (!auth.isLoggedIn) {
    console.info("[Analysis] login required, redirect to login");
    goLogin();
    return;
  }

  const payload = buildSingleAnalysisPayload({
    symbol: codeCheck.value.normalized,
    market: form.market,
    analysisDate: form.analysisDate,
    depthLevel: form.depthLevel,
    analystIds: form.analystIds,
    quickModel: form.quickModel,
    deepModel: form.deepModel,
  });

  submitting.value = true;
  try {
    // 提交成功后 store 进入 running 并开始轮询，页面自动切到进度视图
    await analysis.submit(payload, {
      symbol: payload.symbol,
      stockName: stockName.value,
      market: form.market,
      analysisDate: form.analysisDate,
      depthName: depthLevelToName(form.depthLevel),
      depthLevel: form.depthLevel,
      analystNames: ANALYSTS.filter((a) => form.analystIds.includes(a.id)).map(
        (a) => a.name
      ),
    });
    scrollToTop();
  } catch (e) {
    showSubmitError(e);
  } finally {
    submitting.value = false;
  }
}

function scrollToTop() {
  uni.pageScrollTo({ scrollTop: 0, duration: 0 });
}

/** 请求层已弹出错误 toast；非请求层异常（如缺少 task_id）在此提示 */
function showSubmitError(e: unknown) {
  if (!(e as { statusCode?: number })?.statusCode) {
    uni.showToast({ title: (e as Error)?.message || "提交失败", icon: "none" });
  }
}

// ---------- 进度视图（P3.4） ----------
/** 无进行中任务时显示表单；有任务（进行中 / 完成 / 失败 / 中断）时显示进度视图 */
const showForm = computed(() => !analysis.hasTask);

const taskTitle = computed(() => {
  const meta = analysis.meta;
  if (!meta) return "";
  return meta.stockName ? `${meta.symbol} ${meta.stockName}` : meta.symbol;
});

const phaseText = computed(() => {
  switch (analysis.phase) {
    case "completed":
      return "已完成";
    case "failed":
      return "分析失败";
    case "timeout":
      return "查询中断";
    default:
      return "分析中";
  }
});

/** 返回表单；任务仍在运行时先确认，任务不会被取消，可稍后到「分析报告」查看 */
function onReconfigure() {
  if (analysis.phase !== "running") {
    onNewAnalysis();
    return;
  }
  uni.showModal({
    title: "重新配置",
    content: "当前分析仍在进行，返回后将不再显示进度（任务不会取消，完成后可在「分析报告」查看）。确定返回吗？",
    success: (res) => {
      if (res.confirm) onNewAnalysis();
    },
  });
}

function onNewAnalysis() {
  console.info("[Analysis] back to form");
  analysis.reset();
  scrollToTop();
}

async function onRetry() {
  if (submitting.value) return;
  submitting.value = true;
  try {
    await analysis.retry();
    scrollToTop();
  } catch (e) {
    showSubmitError(e);
  } finally {
    submitting.value = false;
  }
}

function onCopyLink() {
  if (!analysis.shareUrl) return;
  uni.setClipboardData({
    data: analysis.shareUrl,
    success: () => console.info("[Share] link copied"),
  });
}

function goReports() {
  uni.switchTab({ url: "/pages/reports/list" });
}

/** H5 切后台 / 锁屏时暂停轮询，回到前台立即查询一次 */
function onVisibilityChange() {
  if (document.hidden) {
    analysis.pause();
  } else if (auth.isLoggedIn) {
    analysis.restoreOrResume();
  }
}

onMounted(() => {
  document.addEventListener("visibilitychange", onVisibilityChange);
});

onUnmounted(() => {
  document.removeEventListener("visibilitychange", onVisibilityChange);
  analysis.pause();
});

onHide(() => {
  analysis.pause();
});

onShow(() => {
  auth.hydrateFromStorage();
  console.info("[Analysis] form show", { loggedIn: auth.isLoggedIn });
  loadModels();
  // 已登录时恢复进行中的任务（刷新 / 切回本页）
  if (auth.isLoggedIn) analysis.restoreOrResume();
});
</script>

<style lang="scss" scoped>
.single-page {
  padding-top: 24rpx;
}

.intro-card {
  padding: 28rpx 32rpx;
  margin-bottom: 24rpx;
  border-radius: 24rpx;
  background: #fff;
  box-shadow: 0 4rpx 16rpx rgba(0, 0, 0, 0.04);
}

.intro-title {
  font-size: 40rpx;
  font-weight: 700;
  color: #303133;
}

.intro-sub {
  margin-top: 8rpx;
  font-size: 24rpx;
  color: #909399;
}

.section-card {
  margin-bottom: 24rpx;
  border-radius: 24rpx;
  background: #fff;
  overflow: hidden;
  box-shadow: 0 4rpx 16rpx rgba(0, 0, 0, 0.04);
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24rpx 32rpx;
  background: linear-gradient(90deg, #4f7cf2, #7b57c9);
  color: #fff;
}

.section-head-title {
  font-size: 30rpx;
  font-weight: 600;
}

.section-head-badge {
  padding: 4rpx 16rpx;
  border-radius: 8rpx;
  background: rgba(255, 255, 255, 0.25);
  font-size: 22rpx;

  &.is-optional {
    background: #fdf1e0;
    color: #e6a23c;
  }
}

.section-body {
  padding: 24rpx 32rpx 8rpx;
}

.field {
  margin-bottom: 28rpx;
}

.field-label {
  margin-bottom: 12rpx;
}

.field-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.field-label-text {
  font-size: 26rpx;
  font-weight: 600;
  color: #303133;
}

.field-label-extra {
  font-size: 22rpx;
  color: #909399;
}

.required {
  margin-right: 6rpx;
  color: #f56c6c;
}

.select-box {
  display: flex;
  align-items: center;
  height: 88rpx;
  padding: 0 24rpx;
  border: 2rpx solid #dcdfe6;
  border-radius: 16rpx;
  background: #fff;
  box-sizing: border-box;
}

.select-badge {
  margin-right: 16rpx;
  font-size: 20rpx;
  font-weight: 700;
  color: #606266;
}

.select-main {
  font-size: 28rpx;
  color: #303133;
}

.select-hint {
  margin-left: 8rpx;
  font-size: 22rpx;
  color: #909399;
}

.select-arrow {
  margin-left: auto;
  color: #909399;
}

.bottom-spacer {
  height: 140rpx;
}

.submit-bar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: var(--window-bottom, 0);
  padding: 16rpx 32rpx;
  background: linear-gradient(180deg, rgba(245, 247, 250, 0), #f5f7fa 40%);
  box-sizing: border-box;
  z-index: 10;
}

.submit-btn {
  height: 96rpx;
  line-height: 96rpx;
  border-radius: 24rpx;
  background: linear-gradient(90deg, #3b82f6, #1d4ed8);
  color: #fff;
  font-size: 32rpx;
  font-weight: 600;
  box-shadow: 0 8rpx 20rpx rgba(37, 99, 235, 0.35);

  &[disabled] {
    opacity: 0.7;
  }
}

// ---------- 进度视图（P3.4） ----------
.task-card {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 24rpx;
  padding: 24rpx 28rpx;
  border-radius: 24rpx;
  background: #fff;
  box-shadow: 0 4rpx 16rpx rgba(0, 0, 0, 0.04);
}

.task-main {
  flex: 1;
  min-width: 0;
}

.task-top {
  display: flex;
  align-items: center;
}

.task-market {
  margin-right: 16rpx;
  padding: 2rpx 14rpx;
  border-radius: 8rpx;
  background: #ecf5ff;
  color: #409eff;
  font-size: 22rpx;
  font-weight: 700;
}

.task-title {
  font-size: 32rpx;
  font-weight: 700;
  color: #303133;
}

.task-sub {
  margin-top: 8rpx;
  font-size: 22rpx;
  color: #909399;
}

.task-side {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  flex-shrink: 0;
  margin-left: 16rpx;
}

.task-status {
  padding: 4rpx 16rpx;
  border-radius: 8rpx;
  font-size: 22rpx;
  font-weight: 600;
  background: #ecf5ff;
  color: #409eff;

  &.is-completed {
    background: #e8f8ef;
    color: #10b981;
  }

  &.is-failed {
    background: #fef0f0;
    color: #f56c6c;
  }

  &.is-timeout {
    background: #fdf6ec;
    color: #e6a23c;
  }
}

.task-reset {
  margin-top: 12rpx;
  font-size: 24rpx;
  font-weight: 600;
  color: #409eff;
}

.result-card {
  padding: 36rpx 32rpx 28rpx;
  margin-bottom: 24rpx;
  border-radius: 24rpx;
  background: #fff;
  border: 4rpx solid #dcdfe6;
  text-align: center;
  box-shadow: 0 4rpx 16rpx rgba(0, 0, 0, 0.04);

  &.is-success {
    border-color: #10b981;
  }

  &.is-danger {
    border-color: #f56c6c;
  }

  &.is-warning {
    border-color: #e6a23c;
  }
}

.result-icon {
  width: 96rpx;
  height: 96rpx;
  margin: 0 auto 16rpx;
  border-radius: 50%;
  line-height: 96rpx;
  font-size: 48rpx;
  font-weight: 700;

  &.is-success {
    background: #e8f8ef;
    color: #10b981;
  }

  &.is-danger {
    background: #fef0f0;
    color: #f56c6c;
  }

  &.is-warning {
    background: #fdf6ec;
    color: #e6a23c;
  }
}

.result-title {
  font-size: 36rpx;
  font-weight: 700;
  color: #303133;
}

.result-desc {
  margin-top: 12rpx;
  font-size: 24rpx;
  line-height: 1.6;
  color: #606266;

  &.is-error {
    color: #f56c6c;
    word-break: break-all;
  }
}

.share-box {
  display: flex;
  align-items: center;
  margin: 24rpx 0;
  padding: 16rpx 20rpx;
  border: 2rpx dashed #c0c4cc;
  border-radius: 16rpx;
  background: #fafbfc;
  text-align: left;
}

.share-main {
  flex: 1;
  min-width: 0;
}

.share-label {
  font-size: 20rpx;
  color: #909399;
}

.share-url {
  margin-top: 4rpx;
  font-size: 24rpx;
  font-weight: 600;
  color: #303133;
  word-break: break-all;

  &.is-muted {
    color: #909399;
    font-weight: 400;
  }

  &.is-error {
    color: #f56c6c;
    font-weight: 400;
  }
}

.share-copy {
  flex-shrink: 0;
  margin-left: 16rpx;
  padding: 8rpx 24rpx;
  border-radius: 8rpx;
  background: #ecf5ff;
  color: #409eff;
  font-size: 24rpx;
  font-weight: 600;
}

.result-btn {
  height: 88rpx;
  margin-top: 16rpx;
  border-radius: 20rpx;
  line-height: 88rpx;
  font-size: 30rpx;
  font-weight: 600;

  &.is-success {
    background: linear-gradient(90deg, #10b981, #059669);
    color: #fff;
  }

  &.is-primary {
    background: linear-gradient(90deg, #3b82f6, #1d4ed8);
    color: #fff;
  }

  &.is-danger {
    background: linear-gradient(90deg, #f56c6c, #e04b4b);
    color: #fff;
  }

  &.is-plain {
    background: #fff;
    border: 2rpx solid #dcdfe6;
    color: #606266;
  }
}
</style>
