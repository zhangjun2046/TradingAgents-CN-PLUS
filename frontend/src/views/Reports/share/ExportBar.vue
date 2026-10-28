<template>
  <div v-if="open" class="export-layer">
    <WechatGuide v-if="inWechat" />
    <button type="button" class="export-mask" aria-label="关闭导出" @click="close" />
    <section class="export-sheet" role="dialog" aria-modal="true" aria-labelledby="export-title">
      <header class="export-head">
        <div>
          <h2 id="export-title">导出分析报告（免登录公开导出）</h2>
          <p v-if="subtitle" class="export-sub">{{ subtitle }}</p>
        </div>
        <button type="button" class="export-x" aria-label="关闭" @click="close">×</button>
      </header>

      <div class="copy-row" :class="{ 'is-wechat': inWechat }">
        <p v-if="inWechat">检测到当前为微信内置浏览器：推荐复制链接至系统浏览器（Safari / Chrome）下载，或直接尝试导出。</p>
        <p v-else>复制当前报告链接，可在浏览器中打开或发给他人。</p>
        <button type="button" class="copy-btn" @click="onCopy">一键复制报告链接</button>
      </div>

      <ul class="format-list">
        <li v-for="item in SHARE_EXPORT_FORMATS" :key="item.format">
          <div class="format-main">
            <span class="format-badge" aria-hidden="true">
              <svg v-if="item.format === 'pdf'" viewBox="0 0 40 40">
                <rect width="40" height="40" rx="9" fill="#E5252A" />
                <path fill="#fff" d="M14 9h8.2L28 14.8V30a1.6 1.6 0 0 1-1.6 1.6H14A1.6 1.6 0 0 1 12.4 30V10.6A1.6 1.6 0 0 1 14 9z" />
                <path fill="#F6C1C3" d="M22.2 9v5.8H28" />
                <text x="20.2" y="26" text-anchor="middle" fill="#E5252A" font-size="7" font-family="Arial, sans-serif" font-weight="700">PDF</text>
              </svg>
              <svg v-else-if="item.format === 'docx'" viewBox="0 0 40 40">
                <rect width="40" height="40" rx="9" fill="#2B579A" />
                <text x="20" y="27" text-anchor="middle" fill="#fff" font-size="18" font-family="Georgia, serif" font-weight="700">W</text>
              </svg>
              <svg v-else viewBox="0 0 40 40">
                <rect width="40" height="40" rx="9" fill="#1E2A3A" />
                <text x="20" y="25" text-anchor="middle" fill="#fff" font-size="11" font-family="Arial, sans-serif" font-weight="700">MD</text>
              </svg>
            </span>
            <div class="format-copy">
              <strong>{{ item.title }}</strong>
              <span>{{ item.hint }}</span>
            </div>
          </div>
          <button
            type="button"
            class="export-now"
            :disabled="busy"
            @click="onExport(item.format)"
          >
            {{ loadingFormat === item.format ? '导出中' : '立即导出' }}
          </button>
        </li>
      </ul>

      <button type="button" class="cancel-btn" @click="close">取消（返回阅读报告）</button>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import WechatGuide from './WechatGuide.vue'
import {
  SHARE_EXPORT_FORMATS,
  copyText,
  fetchShareDownload,
  isWechatUserAgent,
  triggerBlobDownload,
  type ShareExportFormat,
} from './exportShare'

const props = defineProps<{
  open: boolean
  token: string
  stockSymbol?: string
  stockName?: string
  analysisDate?: string
}>()

const emit = defineEmits<{
  'update:open': [value: boolean]
}>()

const loadingFormat = ref<ShareExportFormat | ''>('')
const busy = computed(() => loadingFormat.value !== '')
const inWechat = isWechatUserAgent(typeof navigator === 'undefined' ? '' : navigator.userAgent)

const subtitle = computed(() => {
  const name = [props.stockSymbol, props.stockName].filter(Boolean).join(' ')
  const date = props.analysisDate ? `基准日 ${props.analysisDate}` : ''
  return [name, date].filter(Boolean).join(' · ')
})

function close(): void {
  emit('update:open', false)
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') close()
}

watch(
  () => props.open,
  (value) => {
    if (typeof window === 'undefined') return
    if (value) window.addEventListener('keydown', onKeydown)
    else window.removeEventListener('keydown', onKeydown)
  }
)

onBeforeUnmount(() => {
  if (typeof window !== 'undefined') window.removeEventListener('keydown', onKeydown)
})

async function onCopy(): Promise<void> {
  const url = window.location.href
  const result = await copyText(url)
  if (result === 'failed') {
    ElMessage.error('复制失败，请长按地址栏复制')
    console.info('[Share] copy link failed')
    return
  }
  ElMessage.success('链接已复制')
  console.info('[Share] copy link', { via: result })
}

async function onExport(format: ShareExportFormat): Promise<void> {
  if (busy.value || !props.token) return
  loadingFormat.value = format
  try {
    const { blob, filename } = await fetchShareDownload(props.token, format, props.stockSymbol)
    triggerBlobDownload(blob, filename)
    ElMessage.success('已开始下载')
  } catch (error) {
    const message = error instanceof Error ? error.message : '导出失败，请稍后重试'
    ElMessage.error(message)
    console.info('[Share] export failed', { format, message })
  } finally {
    loadingFormat.value = ''
  }
}
</script>

<style lang="scss" scoped>
.export-layer {
  position: fixed;
  inset: 0;
  z-index: 40;
}

.export-mask {
  position: absolute;
  inset: 0;
  border: 0;
  padding: 0;
  background: rgba(0, 0, 0, 0.45);
  cursor: pointer;
}

.export-sheet {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  max-height: 86vh;
  overflow: auto;
  padding: 16px 16px calc(16px + env(safe-area-inset-bottom));
  border-radius: 16px 16px 0 0;
  background: #fff;
  color: #303133;
  box-shadow: 0 -8px 32px rgba(0, 0, 0, 0.12);
}

.export-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;

  h2 {
    margin: 0;
    font-size: 18px;
    line-height: 1.4;
    font-weight: 700;
    color: #303133;
  }
}

.export-sub {
  margin: 6px 0 0;
  font-size: 13px;
  line-height: 1.5;
  color: #909399;
}

.export-x {
  flex: none;
  width: 32px;
  height: 32px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: #909399;
  font-size: 22px;
  line-height: 1;
  cursor: pointer;
}

.copy-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
  padding: 12px;
  border-radius: 10px;
  background: #f5f7fa;
  color: #606266;

  p {
    flex: 1 1 180px;
    margin: 0;
    font-size: 13px;
    line-height: 1.6;
  }

  &.is-wechat {
    background: #fff7e8;
    color: #8a5a00;
  }
}

.copy-btn,
.export-now,
.cancel-btn {
  border: 0;
  cursor: pointer;
}

.copy-btn {
  flex: none;
  padding: 8px 12px;
  border-radius: 8px;
  background: #3b82f6;
  color: #fff;
  font-size: 13px;
}

.format-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;

  li {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 12px;
    border: 1px solid #ebeef5;
    border-radius: 12px;
  }
}

.format-main {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.format-badge {
  flex: none;
  width: 40px;
  height: 40px;

  svg {
    display: block;
    width: 40px;
    height: 40px;
  }
}

.format-copy {
  min-width: 0;

  strong {
    display: block;
    font-size: 15px;
    line-height: 1.4;
    color: #303133;
  }

  span {
    display: block;
    margin-top: 4px;
    font-size: 12px;
    line-height: 1.5;
    color: #909399;
  }
}

.export-now {
  flex: none;
  padding: 8px 12px;
  border-radius: 8px;
  background: #ecf5ff;
  color: #3b82f6;
  font-size: 13px;

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
}

.cancel-btn {
  width: 100%;
  margin-top: 12px;
  padding: 12px;
  border-radius: 10px;
  background: #f5f7fa;
  color: #606266;
  font-size: 14px;
}

@media (min-width: 768px) {
  .export-sheet {
    left: 50%;
    right: auto;
    bottom: auto;
    top: 50%;
    width: min(480px, calc(100vw - 48px));
    transform: translate(-50%, -50%);
    border-radius: 16px;
    padding-bottom: 16px;
  }
}
</style>
