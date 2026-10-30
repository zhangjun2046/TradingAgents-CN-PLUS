/**
 * 分享页数据获取 + 派生 + URL 定位。
 *
 * - 数据沿用公开接口 `GET /api/reports/share/{token}`（不走带鉴权拦截器的实例，
 *   避免 401 刷新逻辑干扰），见 doc/handoff/Backend-API-Report.md 2.3；
 * - 可见部门 / 岗位派生规则见 shareConfig.ts；
 * - URL 定位 `?tab=&role=`，切换用 router.replace 不堆历史记录。
 */
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  OVERVIEW_DEPT_KEY,
  buildVisibleDepartments,
  resolveLocation,
  type ShareLocation,
  type VisibleDept,
  type VisibleRole,
} from './shareConfig'
import type { ShareApiResponse, SharedReport } from './types'

const INVALID_LINK_MESSAGE = '该分享链接不存在、已过期或已被撤销。'
const LOAD_FAILED_MESSAGE = '报告加载失败，请稍后重试。'

function scrollToTop(): void {
  if (typeof window !== 'undefined') window.scrollTo({ top: 0 })
}

/** 路由守卫会在每次 query 变化时把标题改回 TradingAgents-CN，这里改回分享页品牌 */
function applyDocumentTitle(reportData: SharedReport | null): void {
  if (typeof document === 'undefined' || !reportData) return
  const titleName = reportData.stock_name || reportData.stock_symbol || '分析报告'
  document.title = `${titleName} - HunterAgent`
}

export function useShareReport() {
  const route = useRoute()
  const router = useRouter()

  const loading = ref(true)
  const error = ref('')
  const report = ref<SharedReport | null>(null)
  const location = ref<ShareLocation>({ tab: OVERVIEW_DEPT_KEY, role: '' })

  const departments = computed<VisibleDept[]>(() =>
    buildVisibleDepartments(report.value?.reports)
  )

  const activeDept = computed<VisibleDept | undefined>(() =>
    departments.value.find((dept) => dept.key === location.value.tab)
  )

  const activeRole = computed<VisibleRole | undefined>(() =>
    activeDept.value?.roles.find((role) => role.key === location.value.role)
  )

  /** 至少两个岗位时才显示二级页签 */
  const showSubTabs = computed(() => Boolean(activeDept.value?.showSubTabs))

  /** 按当前 URL 参数定位；非法参数回落到概览，并同步回地址栏 */
  function applyRouteLocation(replace: boolean): void {
    if (departments.value.length === 0) return
    const next = resolveLocation(
      departments.value,
      typeof route.query.tab === 'string' ? route.query.tab : null,
      typeof route.query.role === 'string' ? route.query.role : null
    )
    location.value = next
    if (!replace) return
    const normalizedTab = next.tab
    const normalizedRole = next.role
    if (route.query.tab === normalizedTab && (route.query.role || '') === normalizedRole) {
      return
    }
    router.replace({ query: toQuery(normalizedTab, normalizedRole) }).finally(() => {
      applyDocumentTitle(report.value)
    })
  }

  function toQuery(tab: string, role: string): Record<string, string> {
    return role ? { tab, role } : { tab }
  }

  /** 切换到指定部门 / 岗位；回顶并同步地址栏 */
  function selectTarget(tab: string, role = ''): void {
    const next = resolveLocation(departments.value, tab, role)
    const changed = next.tab !== location.value.tab || next.role !== location.value.role
    location.value = next
    if (changed) scrollToTop()
    router.replace({ query: toQuery(next.tab, next.role) }).finally(() => {
      applyDocumentTitle(report.value)
    })
    console.info('[Share] switch tab', next)
  }

  function selectRole(role: VisibleRole): void {
    selectTarget(location.value.tab, role.key)
  }

  async function fetchSharedReport(): Promise<void> {
    loading.value = true
    error.value = ''
    try {
      const token = String(route.params.token || '')
      const response = await fetch(`/api/reports/share/${encodeURIComponent(token)}`)
      if (response.status === 404 || response.status === 410) {
        error.value = INVALID_LINK_MESSAGE
        report.value = null
        return
      }
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      const result = (await response.json()) as ShareApiResponse
      if (!result?.success || !result.data) {
        error.value = INVALID_LINK_MESSAGE
        report.value = null
        return
      }
      report.value = result.data
      applyDocumentTitle(result.data)
      applyRouteLocation(true)
    } catch (err) {
      console.info('[Share] failed to load shared report', err)
      error.value = LOAD_FAILED_MESSAGE
      report.value = null
    } finally {
      loading.value = false
    }
  }

  // 地址栏参数被外部改变（转发定位 / 前进后退）时重新定位
  watch(
    () => [route.query.tab, route.query.role, route.params.token],
    () => {
      applyRouteLocation(false)
      applyDocumentTitle(report.value)
    }
  )

  return {
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
  }
}