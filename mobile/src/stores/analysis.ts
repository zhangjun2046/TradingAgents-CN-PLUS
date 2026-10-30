import { defineStore } from "pinia";
import {
  getTaskResult,
  getTaskStatus,
  submitSingleAnalysis,
  type SingleAnalysisPayload,
  type TaskStatusData,
  type TaskStep,
} from "@/api/analysis";
import { createOrReuseShare } from "@/api/reports";
import {
  CURRENT_TASK_KEY,
  CURRENT_TASK_META_KEY,
  POLL_INTERVAL_MS,
  POLL_MAX_CONSECUTIVE_FAILURES,
  POLL_MAX_DURATION_MS,
  POLL_NOT_FOUND_RETRY_MS,
} from "@/constants/analysis";
import { buildShareUrl } from "@/utils/env";

/** 进度状态机（tech_solution 4.1.4） */
export type AnalysisPhase =
  | "idle"
  | "submitting"
  | "running"
  | "completed"
  | "failed"
  | "timeout";

/** timeout 的原因：连续网络失败 / 超过轮询时长上限 */
export type TimeoutReason = "network" | "too_long";

/** 展示用任务快照，随 task_id 一起存入 sessionStorage，刷新后可恢复 */
export interface TaskMeta {
  symbol: string;
  /** 股票名称，可能为空 */
  stockName: string;
  market: string;
  analysisDate: string;
  depthName: string;
  depthLevel: number;
  /** 分析师中文名，用于「分析师团队」展示 */
  analystNames: string[];
  /** 提交时间戳（毫秒），用于 30 分钟上限 */
  submittedAt: number;
  /** 原始提交载荷，「重新分析」时原样重提 */
  payload: SingleAnalysisPayload;
}

interface AnalysisState {
  phase: AnalysisPhase;
  taskId: string;
  meta: TaskMeta | null;
  /** 0-100，单调不减 */
  progress: number;
  currentStepName: string;
  message: string;
  elapsedSeconds: number;
  remainingSeconds: number;
  steps: TaskStep[];
  errorMessage: string;
  timeoutReason: TimeoutReason;
  shareUrl: string;
  shareExpiresAt: string;
  shareLoading: boolean;
  shareError: string;
}

// ---------- 非响应式的调度状态（不参与渲染） ----------
let pollTimer: ReturnType<typeof setTimeout> | null = null;
let inflight = false;
let paused = false;
let consecutiveFailures = 0;
let notFoundRetried = false;
/** 任务切换后丢弃旧任务的异步结果 */
let generation = 0;

function clearTimer(): void {
  if (pollTimer) {
    clearTimeout(pollTimer);
    pollTimer = null;
  }
}

function storageAvailable(): boolean {
  return typeof sessionStorage !== "undefined";
}

function persistTask(taskId: string, meta: TaskMeta): void {
  if (!storageAvailable()) return;
  sessionStorage.setItem(CURRENT_TASK_KEY, taskId);
  sessionStorage.setItem(CURRENT_TASK_META_KEY, JSON.stringify(meta));
}

function clearPersistedTask(): void {
  if (!storageAvailable()) return;
  sessionStorage.removeItem(CURRENT_TASK_KEY);
  sessionStorage.removeItem(CURRENT_TASK_META_KEY);
}

function readPersistedMeta(): TaskMeta | null {
  if (!storageAvailable()) return null;
  const raw = sessionStorage.getItem(CURRENT_TASK_META_KEY);
  if (!raw) return null;
  try {
    const meta = JSON.parse(raw) as TaskMeta;
    return meta && meta.payload ? meta : null;
  } catch {
    return null;
  }
}

function clamp(n: unknown, min: number, max: number): number {
  const v = Number(n);
  if (!Number.isFinite(v)) return min;
  return Math.min(max, Math.max(min, v));
}

function emptyState(): AnalysisState {
  return {
    phase: "idle",
    taskId: "",
    meta: null,
    progress: 0,
    currentStepName: "",
    message: "",
    elapsedSeconds: 0,
    remainingSeconds: 0,
    steps: [],
    errorMessage: "",
    timeoutReason: "network",
    shareUrl: "",
    shareExpiresAt: "",
    shareLoading: false,
    shareError: "",
  };
}

export const useAnalysisStore = defineStore("analysis", {
  state: (): AnalysisState => emptyState(),

  getters: {
    /** 是否存在需要展示进度视图的任务 */
    hasTask: (s) => s.phase !== "idle" && s.phase !== "submitting",
  },

  actions: {
    /**
     * 提交分析并开始轮询。提交失败时回到 idle 并抛出异常，由页面决定提示方式。
     */
    async submit(
      payload: SingleAnalysisPayload,
      info: Omit<TaskMeta, "submittedAt" | "payload">
    ): Promise<string> {
      if (this.phase === "submitting") throw new Error("正在提交，请勿重复操作");
      this.stopPolling();
      this.phase = "submitting";
      try {
        console.info("[Analysis] submit", payload);
        const taskId = await submitSingleAnalysis(payload);
        const meta: TaskMeta = { ...info, submittedAt: Date.now(), payload };
        this.beginTask(taskId, meta);
        console.info("[Analysis] submitted", { taskId });
        return taskId;
      } catch (e) {
        this.$patch(emptyState());
        console.info("[Analysis] submit failed", (e as Error)?.message);
        throw e;
      }
    },

    /** 进入 running 并立即查询一次 */
    beginTask(taskId: string, meta: TaskMeta): void {
      generation += 1;
      this.$patch(emptyState());
      this.taskId = taskId;
      this.meta = meta;
      this.phase = "running";
      consecutiveFailures = 0;
      notFoundRetried = false;
      paused = false;
      persistTask(taskId, meta);
      void this.tick();
    },

    /** 页面重新出现 / 刷新后：恢复进行中的任务；已有任务则立即查询一次 */
    restoreOrResume(): void {
      paused = false;
      if (this.phase === "running") {
        console.info("[Analysis] resume polling", { taskId: this.taskId });
        clearTimer();
        void this.tick();
        return;
      }
      if (this.phase !== "idle") return;
      if (!storageAvailable()) return;
      const taskId = sessionStorage.getItem(CURRENT_TASK_KEY);
      const meta = readPersistedMeta();
      if (!taskId || !meta) {
        // 只有 task_id、缺少快照（如旧版本写入）时无法展示，直接丢弃
        if (taskId) clearPersistedTask();
        return;
      }
      console.info("[Analysis] restore task", { taskId });
      generation += 1;
      this.$patch(emptyState());
      this.taskId = taskId;
      this.meta = meta;
      this.phase = "running";
      consecutiveFailures = 0;
      notFoundRetried = false;
      void this.tick();
    },

    /** 页面隐藏 / 切到后台：暂停轮询 */
    pause(): void {
      if (paused) return;
      paused = true;
      clearTimer();
      if (this.phase === "running") {
        console.info("[Analysis] polling paused", { taskId: this.taskId });
      }
    },

    /** 轮询并停止（不清除持久化的任务） */
    stopPolling(): void {
      clearTimer();
      generation += 1;
      inflight = false;
    },

    /** 回到表单：清除当前任务（后端任务不受影响，可在「分析报告」查看） */
    reset(): void {
      this.stopPolling();
      clearPersistedTask();
      this.$patch(emptyState());
    },

    /** timeout（网络）后「继续查询」 */
    continuePolling(): void {
      if (this.phase !== "timeout" || this.timeoutReason !== "network") return;
      consecutiveFailures = 0;
      notFoundRetried = false;
      paused = false;
      this.phase = "running";
      console.info("[Analysis] continue polling", { taskId: this.taskId });
      void this.tick();
    },

    /** 失败后「重新分析」：用相同载荷重新提交 */
    async retry(): Promise<void> {
      const meta = this.meta;
      if (!meta) return;
      const { payload, submittedAt: _t, ...info } = meta;
      await this.submit(payload, info);
    },

    scheduleNext(delay: number): void {
      clearTimer();
      if (this.phase !== "running" || paused) return;
      pollTimer = setTimeout(() => {
        pollTimer = null;
        void this.tick();
      }, delay);
    },

    /** 单次进度查询 */
    async tick(): Promise<void> {
      if (this.phase !== "running" || paused || inflight) return;
      const meta = this.meta;
      if (meta && Date.now() - meta.submittedAt > POLL_MAX_DURATION_MS) {
        this.enterTimeout("too_long");
        return;
      }

      const gen = generation;
      const taskId = this.taskId;
      inflight = true;
      let nextDelay = POLL_INTERVAL_MS;
      try {
        const data = await getTaskStatus(taskId);
        if (gen !== generation) return;
        consecutiveFailures = 0;
        notFoundRetried = false;
        this.applyStatus(data);
      } catch (e) {
        if (gen !== generation) return;
        const status = (e as { statusCode?: number })?.statusCode ?? 0;
        if (status === 401) {
          // 请求层已清空登录态并跳转登录页；停止轮询，登录回来后 onShow 恢复
          console.info("[Analysis] polling stopped: unauthorized");
          paused = true;
          return;
        }
        if (status === 404) {
          if (!notFoundRetried) {
            // 刚提交时任务可能尚未可查，等 2s 重试一次
            notFoundRetried = true;
            nextDelay = POLL_NOT_FOUND_RETRY_MS;
            console.info("[Analysis] status not found, retry once", { taskId });
          } else {
            this.enterFailed("任务不存在或已过期，请重新发起分析");
            return;
          }
        } else if (status === 0 || status >= 500) {
          consecutiveFailures += 1;
          console.info("[Analysis] poll failed", { status, consecutiveFailures });
          if (consecutiveFailures >= POLL_MAX_CONSECUTIVE_FAILURES) {
            this.enterTimeout("network");
            return;
          }
        } else {
          this.enterFailed((e as Error)?.message || "查询进度失败");
          return;
        }
      } finally {
        if (gen === generation) inflight = false;
      }
      if (gen === generation) this.scheduleNext(nextDelay);
    },

    applyStatus(data: TaskStatusData): void {
      const status = String(data.status || "").toLowerCase();

      if (status === "failed" || status === "cancelled") {
        const fallback =
          status === "cancelled" ? "任务已取消" : "分析失败，请稍后重试";
        this.enterFailed(data.error_message || data.message || fallback);
        return;
      }

      // 后端未给出耗时时（如历史记录恢复），按提交时间本地估算
      const serverElapsed = clamp(data.elapsed_time, 0, Number.MAX_SAFE_INTEGER);
      this.elapsedSeconds =
        serverElapsed > 0 || !this.meta
          ? serverElapsed
          : Math.floor((Date.now() - this.meta.submittedAt) / 1000);
      if (Array.isArray(data.steps)) {
        this.steps = data.steps.map((s) => ({
          name: String(s.name || ""),
          description: s.description,
          status: String(s.status || "pending"),
        }));
        // 后端有时不把进行中的步骤标成 current，按 current_step 索引补上
        const idx = data.current_step;
        if (
          status !== "completed" &&
          typeof idx === "number" &&
          this.steps[idx] &&
          this.steps[idx].status === "pending" &&
          !this.steps.some((s) => s.status === "current")
        ) {
          this.steps[idx].status = "current";
        }
      }

      if (status === "completed") {
        this.progress = 100;
        this.remainingSeconds = 0;
        this.currentStepName = "";
        this.message = data.message || "";
        this.enterCompleted();
        return;
      }

      // pending / processing / running 统一视为进行中
      this.progress = Math.max(this.progress, clamp(data.progress, 0, 99));
      this.remainingSeconds = clamp(
        data.remaining_time,
        0,
        Number.MAX_SAFE_INTEGER
      );
      this.currentStepName = data.current_step_name || "";
      this.message = data.message || "";
    },

    enterCompleted(): void {
      this.stopPolling();
      this.phase = "completed";
      console.info("[Analysis] completed", { taskId: this.taskId });
      void this.prepareShare();
    },

    enterFailed(message: string): void {
      this.stopPolling();
      this.phase = "failed";
      this.errorMessage = message;
      // 失败任务无需再恢复，刷新后回到表单
      clearPersistedTask();
      console.info("[Analysis] failed", { taskId: this.taskId, message });
    },

    enterTimeout(reason: TimeoutReason): void {
      this.stopPolling();
      this.phase = "timeout";
      this.timeoutReason = reason;
      console.info("[Analysis] timeout", { taskId: this.taskId, reason });
    },

    /**
     * 完成后取 analysis_id 并创建 / 复用分享链接（失败可由用户点击按钮重试）。
     * result 取不到 analysis_id 时直接用 task_id（后端 _build_report_query 支持）。
     */
    async prepareShare(): Promise<boolean> {
      if (this.shareUrl) return true;
      if (this.shareLoading) return false;
      const gen = generation;
      const taskId = this.taskId;
      this.shareLoading = true;
      this.shareError = "";
      try {
        let reportId = taskId;
        try {
          const result = await getTaskResult(taskId);
          if (result.analysis_id) reportId = result.analysis_id;
        } catch (e) {
          console.info("[Share] result unavailable, use task id", {
            message: (e as Error)?.message,
          });
        }
        let share;
        try {
          share = await createOrReuseShare(reportId);
        } catch (e) {
          // analysis_id 有时尚未写入 analysis_reports，按 tech_solution 7.5 回退 task_id
          if (reportId === taskId) throw e;
          console.info("[Share] analysis_id not found, fallback to task id", {
            reportId,
            taskId,
            message: (e as Error)?.message,
          });
          share = await createOrReuseShare(taskId);
        }
        if (gen !== generation) return false;
        this.shareUrl = buildShareUrl(share.token);
        this.shareExpiresAt = share.expires_at || "";
        console.info("[Share] ready", { reportId, token: share.token?.slice(0, 6) });
        return true;
      } catch (e) {
        if (gen !== generation) return false;
        this.shareError = (e as Error)?.message || "分享链接生成失败，请重试";
        console.info("[Share] create failed", this.shareError);
        return false;
      } finally {
        if (gen === generation) this.shareLoading = false;
      }
    },

    /** 点击「立即查看分析报告」：确保分享链接已就绪后整页跳转到 /s/{token} */
    async openReport(): Promise<void> {
      const ok = await this.prepareShare();
      if (!ok || !this.shareUrl) {
        uni.showToast({ title: this.shareError || "分享链接生成失败", icon: "none" });
        return;
      }
      console.info("[Share] redirect", { url: this.shareUrl });
      window.location.href = this.shareUrl;
    },
  },
});
