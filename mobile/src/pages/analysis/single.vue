<template>
  <view class="ha-page single-page">
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
  </view>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { onShow } from "@dcloudio/uni-app";
import StockCodeInput from "@/components/StockCodeInput.vue";
import DepthSelector from "@/components/DepthSelector.vue";
import AnalystCards from "@/components/AnalystCards.vue";
import ModelSelect from "@/components/ModelSelect.vue";
import { useAuthStore } from "@/stores/auth";
import { getPublicModels } from "@/api/config";
import {
  buildSingleAnalysisPayload,
  getStockName,
  submitSingleAnalysis,
} from "@/api/analysis";
import {
  CURRENT_TASK_KEY,
  DEFAULT_DEPTH_LEVEL,
  DEFAULT_MARKET,
  MARKETS,
  type MarketType,
} from "@/constants/analysis";
import { DEFAULT_ANALYST_IDS, SOCIAL_ANALYST_ID } from "@/constants/analysts";
import type { PublicModel, PublicModelsData } from "@/constants/models";
import { isFutureDate, today, validateStockCode } from "@/utils/validators";

const auth = useAuthStore();

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
    console.info("[Analysis] submit", payload);
    const taskId = await submitSingleAnalysis(payload);
    // P3.4 使用该键恢复进度；此处只保存，不做进度展示
    if (typeof sessionStorage !== "undefined") {
      sessionStorage.setItem(CURRENT_TASK_KEY, taskId);
    }
    console.info("[Analysis] submitted", { taskId });
    uni.showToast({ title: "分析任务已提交", icon: "success" });
  } catch (e) {
    console.info("[Analysis] submit failed", (e as Error)?.message);
    // 请求层已弹出错误 toast；非请求层异常（如缺少 task_id）在此提示
    if (!(e as { statusCode?: number })?.statusCode) {
      uni.showToast({ title: (e as Error)?.message || "提交失败", icon: "none" });
    }
  } finally {
    submitting.value = false;
  }
}

onShow(() => {
  auth.hydrateFromStorage();
  console.info("[Analysis] form show", { loggedIn: auth.isLoggedIn });
  loadModels();
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
</style>
