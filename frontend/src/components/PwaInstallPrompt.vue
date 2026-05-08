<template>
  <transition name="slide-up">
    <div v-if="showPrompt" class="pwa-install-prompt">
      <div class="prompt-content">
        <div class="prompt-icon">
          <el-icon><Download /></el-icon>
        </div>
        <div class="prompt-text">
          <div class="prompt-title">安装应用到桌面</div>
          <div class="prompt-desc">获得更好的使用体验，支持离线访问</div>
        </div>
        <div class="prompt-actions">
          <el-button type="primary" size="small" @click="handleInstall">
            安装
          </el-button>
          <el-button size="small" @click="handleDismiss">
            稍后
          </el-button>
          <el-button size="small" text @click="handleNeverShow">
            不再提示
          </el-button>
        </div>
      </div>
      <div class="prompt-close" @click="handleDismiss">
        <el-icon><Close /></el-icon>
      </div>
    </div>
  </transition>

  <!-- iOS Safari 特殊提示 -->
  <el-dialog
    v-model="showIOSPrompt"
    title="安装应用到主屏幕"
    width="90%"
    :close-on-click-modal="false"
    class="ios-install-dialog"
  >
    <div class="ios-install-guide">
      <div class="guide-step">
        <div class="step-number">1</div>
        <div class="step-content">
          <div class="step-text">点击底部的分享按钮</div>
          <div class="step-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
              <path d="M16 5l-1.42 1.42-1.59-1.59V16h-1.98V4.83L9.42 6.42 8 5l4-4 4 4zm4 5v11c0 1.1-.9 2-2 2H6c-1.11 0-2-.9-2-2V10c0-1.11.89-2 2-2h3v2H6v11h12V10h-3V8h3c1.1 0 2 .89 2 2z"/>
            </svg>
          </div>
        </div>
      </div>
      <div class="guide-step">
        <div class="step-number">2</div>
        <div class="step-content">
          <div class="step-text">选择"添加到主屏幕"</div>
          <div class="step-icon">➕</div>
        </div>
      </div>
      <div class="guide-step">
        <div class="step-number">3</div>
        <div class="step-content">
          <div class="step-text">点击"添加"完成安装</div>
          <div class="step-icon">✅</div>
        </div>
      </div>
    </div>
    <template #footer>
      <el-button @click="handleIOSDismiss">我知道了</el-button>
      <el-button type="primary" @click="handleIOSNeverShow">不再提示</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'

const showPrompt = ref(false)
const showIOSPrompt = ref(false)
let deferredPrompt: any = null

// 检查是否已经安装
const isInstalled = () => {
  // 检查是否在独立模式下运行（已安装）
  return window.matchMedia('(display-mode: standalone)').matches ||
         (window.navigator as any).standalone === true ||
         document.referrer.includes('android-app://')
}

// 检查是否为iOS设备
const isIOS = () => {
  return /iPad|iPhone|iPod/.test(navigator.userAgent) && !(window as any).MSStream
}

// 检查是否应该显示提示
const shouldShowPrompt = () => {
  const neverShow = localStorage.getItem('pwa_install_never_show')
  const lastDismissed = localStorage.getItem('pwa_install_last_dismissed')
  
  if (neverShow === 'true') {
    return false
  }
  
  if (lastDismissed) {
    const daysSinceLastDismiss = (Date.now() - parseInt(lastDismissed)) / (1000 * 60 * 60 * 24)
    if (daysSinceLastDismiss < 7) {
      return false
    }
  }
  
  return true
}

// 处理安装
const handleInstall = async () => {
  if (!deferredPrompt) {
    ElMessage.warning('当前浏览器不支持应用安装')
    return
  }

  console.log('🚀 用户点击安装PWA应用')
  
  // 显示安装提示
  deferredPrompt.prompt()
  
  // 等待用户响应
  const { outcome } = await deferredPrompt.userChoice
  console.log(`👉 用户选择: ${outcome}`)
  
  if (outcome === 'accepted') {
    console.log('✅ 用户接受安装')
    ElMessage.success('应用安装成功！')
  } else {
    console.log('❌ 用户拒绝安装')
  }
  
  // 清除 deferredPrompt
  deferredPrompt = null
  showPrompt.value = false
}

// 稍后提醒
const handleDismiss = () => {
  console.log('⏰ 用户选择稍后安装')
  localStorage.setItem('pwa_install_last_dismissed', Date.now().toString())
  showPrompt.value = false
}

// 不再提示
const handleNeverShow = () => {
  console.log('🚫 用户选择不再提示安装')
  localStorage.setItem('pwa_install_never_show', 'true')
  showPrompt.value = false
  ElMessage.info('已设置不再提示')
}

// iOS 提示处理
const handleIOSDismiss = () => {
  localStorage.setItem('pwa_install_last_dismissed', Date.now().toString())
  showIOSPrompt.value = false
}

const handleIOSNeverShow = () => {
  localStorage.setItem('pwa_install_never_show', 'true')
  showIOSPrompt.value = false
  ElMessage.info('已设置不再提示')
}

// 监听 beforeinstallprompt 事件
const handleBeforeInstallPrompt = (e: Event) => {
  console.log('💡 PWA安装提示事件触发')
  
  // 阻止默认的安装提示
  e.preventDefault()
  
  // 保存事件，稍后使用
  deferredPrompt = e
  
  // 检查是否应该显示提示
  if (shouldShowPrompt() && !isInstalled()) {
    // 延迟显示，给用户一些时间浏览页面
    setTimeout(() => {
      showPrompt.value = true
    }, 5000) // 5秒后显示
  }
}

// 监听应用安装成功事件
const handleAppInstalled = () => {
  console.log('🎉 PWA应用已成功安装')
  deferredPrompt = null
  showPrompt.value = false
  ElMessage.success({
    message: '应用已成功安装到桌面！',
    duration: 5000
  })
}

onMounted(() => {
  console.log('🔍 PWA安装提示组件已挂载')
  
  // 检查是否已安装
  if (isInstalled()) {
    console.log('✅ 应用已安装，不显示提示')
    return
  }
  
  // iOS 设备特殊处理
  if (isIOS()) {
    console.log('📱 检测到iOS设备')
    if (shouldShowPrompt()) {
      // iOS 延迟显示提示
      setTimeout(() => {
        showIOSPrompt.value = true
      }, 10000) // 10秒后显示
    }
    return
  }
  
  // 监听安装提示事件
  window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt)
  window.addEventListener('appinstalled', handleAppInstalled)
  
  console.log('👂 已注册PWA安装事件监听器')
})

onBeforeUnmount(() => {
  window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt)
  window.removeEventListener('appinstalled', handleAppInstalled)
  console.log('🧹 已清理PWA安装事件监听器')
})
</script>

<style lang="scss" scoped>
.pwa-install-prompt {
  position: fixed;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 9999;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  padding: 20px 24px;
  max-width: 90%;
  width: 600px;
  display: flex;
  align-items: center;
  gap: 16px;
  animation: slideUpBounce 0.5s ease-out;

  .prompt-content {
    display: flex;
    align-items: center;
    gap: 16px;
    flex: 1;
  }

  .prompt-icon {
    font-size: 32px;
    flex-shrink: 0;
  }

  .prompt-text {
    flex: 1;
    min-width: 0;

    .prompt-title {
      font-size: 16px;
      font-weight: 600;
      margin-bottom: 4px;
    }

    .prompt-desc {
      font-size: 13px;
      opacity: 0.9;
    }
  }

  .prompt-actions {
    display: flex;
    gap: 8px;
    flex-shrink: 0;

    .el-button {
      border-color: rgba(255, 255, 255, 0.3);
      
      &.el-button--primary {
        background: white;
        color: #667eea;
        border-color: white;

        &:hover {
          background: rgba(255, 255, 255, 0.9);
        }
      }

      &:not(.el-button--primary) {
        color: white;
        background: rgba(255, 255, 255, 0.1);

        &:hover {
          background: rgba(255, 255, 255, 0.2);
        }
      }
    }
  }

  .prompt-close {
    cursor: pointer;
    font-size: 20px;
    opacity: 0.8;
    transition: opacity 0.3s;
    flex-shrink: 0;

    &:hover {
      opacity: 1;
    }
  }
}

// 移动端样式
@media (max-width: 768px) {
  .pwa-install-prompt {
    bottom: 10px;
    left: 10px;
    right: 10px;
    transform: none;
    width: auto;
    max-width: none;
    padding: 16px;
    flex-direction: column;
    align-items: stretch;

    .prompt-content {
      flex-direction: column;
      align-items: flex-start;
      gap: 12px;
    }

    .prompt-icon {
      font-size: 28px;
    }

    .prompt-text {
      .prompt-title {
        font-size: 15px;
      }

      .prompt-desc {
        font-size: 12px;
      }
    }

    .prompt-actions {
      width: 100%;
      flex-direction: column;

      .el-button {
        width: 100%;
      }
    }

    .prompt-close {
      position: absolute;
      top: 12px;
      right: 12px;
    }
  }
}

// iOS 安装指南样式
.ios-install-dialog {
  .ios-install-guide {
    padding: 20px 0;

    .guide-step {
      display: flex;
      align-items: flex-start;
      gap: 16px;
      margin-bottom: 24px;
      padding: 16px;
      background: var(--el-fill-color-light);
      border-radius: 12px;

      &:last-child {
        margin-bottom: 0;
      }

      .step-number {
        width: 32px;
        height: 32px;
        background: #409EFF;
        color: white;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 600;
        flex-shrink: 0;
      }

      .step-content {
        flex: 1;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;

        .step-text {
          font-size: 15px;
          color: var(--el-text-color-primary);
        }

        .step-icon {
          font-size: 24px;
          color: #409EFF;
          flex-shrink: 0;
        }
      }
    }
  }
}

// 动画
.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.3s ease;
}

.slide-up-enter-from {
  transform: translateX(-50%) translateY(100px);
  opacity: 0;
}

.slide-up-leave-to {
  transform: translateX(-50%) translateY(100px);
  opacity: 0;
}

@keyframes slideUpBounce {
  0% {
    transform: translateX(-50%) translateY(100px);
    opacity: 0;
  }
  60% {
    transform: translateX(-50%) translateY(-10px);
    opacity: 1;
  }
  80% {
    transform: translateX(-50%) translateY(5px);
  }
  100% {
    transform: translateX(-50%) translateY(0);
  }
}

@media (max-width: 768px) {
  @keyframes slideUpBounce {
    0% {
      transform: translateY(100px);
      opacity: 0;
    }
    60% {
      transform: translateY(-10px);
      opacity: 1;
    }
    80% {
      transform: translateY(5px);
    }
    100% {
      transform: translateY(0);
    }
  }
}
</style>

