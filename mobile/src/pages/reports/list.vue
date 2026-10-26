<template>
  <view class="ha-page report-page">
    <view class="toolbar">
      <view class="search-box">
        <text class="search-icon">⌕</text>
        <input
          class="search-input"
          v-model="keyword"
          placeholder="搜索股票代码或名称"
          confirm-type="search"
          @input="scheduleSearch"
          @confirm="applyFilter"
        />
      </view>
      <view class="segments">
        <view
          v-for="chip in marketChips"
          :key="chip.value || 'all'"
          class="segment"
          :class="{ 'segment-on': market === chip.value }"
          @click="selectMarket(chip.value)"
        >
          {{ chip.label }}
        </view>
      </view>
      <text v-if="loggedIn && !showInitialLoading" class="total-line">共 {{ total }} 份报告</text>
    </view>

    <view v-if="showInitialLoading" class="state-box">加载中...</view>

    <view v-else-if="loadError && items.length === 0" class="state-box">
      <text class="state-text">{{ loadError }}</text>
      <view class="ha-btn-primary state-btn" @click="applyFilter">重试</view>
    </view>

    <view v-else-if="showEmpty" class="state-box">
      <text class="state-text">暂无报告，去发起一次 AI 分析</text>
      <view class="ha-btn-primary state-btn" @click="goAnalysis">去发起一次 AI 分析</view>
    </view>

    <view v-else class="card-list">
      <view
        v-for="item in items"
        :key="itemKey(item)"
        class="card"
        :class="{ 'card-disabled': !canOpen(item) }"
        @click="openReport(item)"
      >
        <view class="card-head">
          <view class="card-title">
            <text class="stock-name">{{ stockTitle(item) }}</text>
            <text class="market-badge" :class="marketClass(item.market_type)">
              {{ item.market_type || "未知" }}
            </text>
          </view>
          <text class="status-tag" :class="statusClass(item.status)">
            {{ statusText(item.status) }}
          </text>
        </view>
        <text class="meta">{{ metaLine(item) }}</text>
        <view class="card-foot">
          <view
            class="open-btn"
            :class="{ 'open-btn-off': !canOpen(item), 'open-btn-busy': openingId === reportShareId(item) }"
          >
            {{ openLabel(item) }}
          </view>
        </view>
      </view>
      <uni-load-more
        v-if="items.length > 0"
        :status="loadMoreStatus"
        :content-text="loadMoreText"
        @clickLoadMore="loadMore"
      />
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { onPullDownRefresh, onReachBottom, onShow } from "@dcloudio/uni-app";
import dayjs from "dayjs";
import type { MarketType } from "@/constants/analysis";
import {
  createOrReuseShare,
  getReportList,
  reportShareId,
  type ReportListItem,
} from "@/api/reports";
import { useAuthStore } from "@/stores/auth";
import { buildShareUrl } from "@/utils/env";

const PAGE_SIZE = 20;

const auth = useAuthStore();
const keyword = ref("");
const market = ref<"" | MarketType>("");
const items = ref<ReportListItem[]>([]);
const total = ref(0);
const page = ref(1);
const loading = ref(false);
const loadingMore = ref(false);
const loadError = ref("");
const openingId = ref("");
const loggedIn = ref(false);

const marketChips: { value: "" | MarketType; label: string }[] = [
  { value: "", label: "全部" },
  { value: "A股", label: "A股" },
  { value: "港股", label: "港股" },
  { value: "美股", label: "美股" },
];

const loadMoreText = {
  contentdown: "上拉加载更多",
  contentrefresh: "加载中...",
  contentnomore: "没有更多了",
};

const hasMore = computed(() => items.value.length < total.value);
const showInitialLoading = computed(() => loading.value && items.value.length === 0);
const showEmpty = computed(
  () => loggedIn.value && !loading.value && !loadError.value && items.value.length === 0
);
const loadMoreStatus = computed(() => {
  if (loadingMore.value || (loading.value && items.value.length > 0)) return "loading";
  if (!hasMore.value) return "noMore";
  return "more";
});

let requestSeq = 0;
let searchTimer: ReturnType<typeof setTimeout> | null = null;
let lastRedirectAt = 0;

function ensureLogin(): boolean {
  auth.hydrateFromStorage();
  loggedIn.value = auth.isLoggedIn;
  if (auth.isLoggedIn) return true;
  items.value = [];
  total.value = 0;
  const now = Date.now();
  if (now - lastRedirectAt < 800) return false;
  lastRedirectAt = now;
  const redirect = encodeURIComponent("/pages/reports/list");
  uni.navigateTo({
    url: `/pages/auth/login?redirect=${redirect}`,
    fail: () => {
      uni.reLaunch({ url: `/pages/auth/login?redirect=${redirect}` });
    },
  });
  return false;
}

function itemKey(item: ReportListItem): string {
  return reportShareId(item) || `${item.stock_code}-${item.created_at}`;
}

function displayName(item: ReportListItem): string {
  const name = (item.stock_name || "").trim();
  const code = (item.stock_code || "").trim();
  if (!name || name === code) return "";
  return name;
}

/** 标题「名称 (代码)」；无名称时只显示代码。 */
function stockTitle(item: ReportListItem): string {
  const name = displayName(item);
  const code = (item.stock_code || "").trim();
  if (name) return code ? `${name} (${code})` : name;
  return code || "—";
}

function canOpen(item: ReportListItem): boolean {
  return (item.status || "completed") === "completed";
}

function statusText(status?: string): string {
  if (!status || status === "completed") return "已完成";
  if (status === "failed") return "失败";
  return "分析中";
}

function statusClass(status?: string): string {
  if (!status || status === "completed") return "status-ok";
  if (status === "failed") return "status-fail";
  return "status-run";
}

function marketClass(marketType?: string): string {
  if (marketType === "A股") return "market-a";
  if (marketType === "港股") return "market-hk";
  if (marketType === "美股") return "market-us";
  return "market-unknown";
}

function formatDate(value?: string, withTime = false): string {
  if (!value) return "";
  const parsed = dayjs(value);
  if (!parsed.isValid()) return withTime ? value : value.slice(0, 10);
  return parsed.format(withTime ? "YYYY-MM-DD HH:mm" : "YYYY-MM-DD");
}

function metaLine(item: ReportListItem): string {
  const parts: string[] = [];
  const analysisDate = formatDate(item.analysis_date);
  const createdAt = formatDate(item.created_at, true);
  if (analysisDate) parts.push(`基准日：${analysisDate}`);
  if (createdAt) parts.push(`创建于 ${createdAt}`);
  return parts.join(" · ") || "—";
}

function openLabel(item: ReportListItem): string {
  if (openingId.value && openingId.value === reportShareId(item)) return "打开中...";
  if (canOpen(item)) return "查看报告 >";
  return statusText(item.status);
}

async function fetchPage(nextPage: number, mode: "replace" | "append"): Promise<void> {
  if (!auth.isLoggedIn) return;
  if (mode === "append") {
    if (loading.value || loadingMore.value || !hasMore.value) return;
    loadingMore.value = true;
  } else {
    loading.value = true;
  }
  const seq = ++requestSeq;
  if (mode === "replace") loadError.value = "";
  try {
    const data = await getReportList({
      page: nextPage,
      page_size: PAGE_SIZE,
      search_keyword: keyword.value,
      market_filter: market.value || undefined,
    });
    if (seq !== requestSeq) return;
    const rows = data?.reports || [];
    total.value = data?.total ?? rows.length;
    page.value = nextPage;
    if (mode === "replace") {
      items.value = rows;
    } else {
      const seen = new Set(items.value.map((row) => itemKey(row)));
      items.value = items.value.concat(rows.filter((row) => !seen.has(itemKey(row))));
    }
    console.info("[Reports] loaded", {
      page: nextPage,
      count: rows.length,
      total: total.value,
      market: market.value || "all",
    });
  } catch (error) {
    if (seq !== requestSeq) return;
    const message = (error as Error)?.message || "加载失败";
    loadError.value = message;
    console.info("[Reports] load failed", { page: nextPage, message });
  } finally {
    if (seq === requestSeq) {
      loading.value = false;
      loadingMore.value = false;
    }
  }
}

function applyFilter(): void {
  if (searchTimer) {
    clearTimeout(searchTimer);
    searchTimer = null;
  }
  if (!ensureLogin()) return;
  void fetchPage(1, "replace");
}

function scheduleSearch(): void {
  if (searchTimer) clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    applyFilter();
  }, 400);
}

function selectMarket(value: "" | MarketType): void {
  if (market.value === value) return;
  market.value = value;
  applyFilter();
}

function loadMore(): void {
  if (!auth.isLoggedIn) return;
  void fetchPage(page.value + 1, "append");
}

function goAnalysis(): void {
  uni.switchTab({ url: "/pages/analysis/single" });
}

async function openReport(item: ReportListItem): Promise<void> {
  if (!canOpen(item) || openingId.value) return;
  const id = reportShareId(item);
  if (!id) {
    uni.showToast({ title: "报告标识缺失", icon: "none" });
    return;
  }
  openingId.value = id;
  console.info("[Reports] open", { id });
  try {
    const share = await createOrReuseShare(id);
    const url = buildShareUrl(share.token);
    console.info("[Reports] redirect", { url });
    if (typeof window !== "undefined") {
      window.location.href = url;
    }
  } catch (error) {
    uni.showToast({
      title: (error as Error)?.message || "分享链接生成失败，请重试",
      icon: "none",
    });
  } finally {
    openingId.value = "";
  }
}

onShow(() => {
  if (!ensureLogin()) return;
  void fetchPage(1, "replace");
});

onPullDownRefresh(() => {
  const done = () => uni.stopPullDownRefresh();
  if (!ensureLogin()) {
    done();
    return;
  }
  void fetchPage(1, "replace").finally(done);
});

onReachBottom(() => {
  loadMore();
});
</script>

<style lang="scss" scoped>
.report-page {
  display: flex;
  flex-direction: column;
  gap: 24rpx;
  padding-bottom: 48rpx;
}

.toolbar {
  display: flex;
  flex-direction: column;
  gap: 20rpx;
}

.search-box {
  display: flex;
  align-items: center;
  height: 76rpx;
  padding: 0 20rpx;
  background: #fff;
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  box-sizing: border-box;
}

.search-icon {
  margin-right: 8rpx;
  color: var(--ha-text-secondary);
  font-size: 16px;
  line-height: 1;
}

.search-input {
  flex: 1;
  height: 100%;
  font-size: 14px;
  color: var(--ha-text-primary);
}

// 分段控件（对齐 PC el-select 的视觉）
.segments {
  display: flex;
  padding: 6rpx;
  border-radius: 8px;
  background: #f2f3f5;
}

.segment {
  flex: 1;
  padding: 10rpx 0;
  border-radius: 6px;
  color: var(--ha-text-regular);
  font-size: 14px;
  text-align: center;
}

.segment-on {
  background: #fff;
  color: var(--ha-color-primary);
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.total-line {
  font-size: 12px;
  color: var(--ha-text-secondary);
}

.state-box {
  padding: 80rpx 32rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24rpx;
  color: var(--ha-text-secondary);
  font-size: 14px;
  text-align: center;
}

.state-text {
  line-height: 1.6;
}

.state-btn {
  padding: 16rpx 32rpx;
  line-height: 1.4;
}

.card-list {
  display: flex;
  flex-direction: column;
  gap: 20rpx;
}

.card {
  background: #fff;
  border-radius: 8px;
  padding: 28rpx;
  display: flex;
  flex-direction: column;
  gap: 16rpx;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.06);
}

.card-disabled {
  opacity: 0.85;
}

.card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16rpx;
}

.card-title {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12rpx;
  min-width: 0;
}

.stock-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--ha-text-primary);
}

// 市场徽标：浅底彩字（对齐 el-tag plain）
.market-badge {
  padding: 2px 10px;
  border-radius: 4px;
  font-size: 12px;
  line-height: 1.6;
}

.market-a {
  background: #ecf5ff;
  color: #409eff;
}

.market-hk {
  background: #ede9ff;
  color: #7b61ff;
}

.market-us {
  background: #fdf6ec;
  color: #e6a23c;
}

.market-unknown {
  background: #f4f4f5;
  color: #909399;
}

.status-tag {
  flex-shrink: 0;
  padding: 2px 10px;
  border-radius: 4px;
  font-size: 12px;
  line-height: 1.6;
}

.status-ok {
  color: #67c23a;
  background: #f0f9eb;
}

.status-run {
  color: #e6a23c;
  background: #fdf6ec;
}

.status-fail {
  color: #f56c6c;
  background: #fef0f0;
}

.meta {
  font-size: 12px;
  color: var(--ha-text-secondary);
  line-height: 1.5;
}

.card-foot {
  display: flex;
  justify-content: flex-end;
  padding-top: 4rpx;
  border-top: 1px solid #f0f2f5;
}

// 「查看报告」文字链接（对齐 PC el-link type=primary）
.open-btn {
  font-size: 14px;
  color: var(--ha-color-primary);
}

.open-btn-off {
  color: var(--ha-text-secondary);
}

.open-btn-busy {
  opacity: 0.7;
}
</style>
