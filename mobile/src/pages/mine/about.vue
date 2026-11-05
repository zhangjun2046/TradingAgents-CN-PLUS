<template>
  <view class="ha-page about">
    <view class="card">
      <text class="title">HunterAgents</text>
      <text class="subtitle">多智能体股票分析学习平台</text>
      <text class="body">
        基于 AI 多智能体协作，从不同角度辅助分析股票。分析结果仅供学习与研究，不构成投资建议。
      </text>
    </view>

    <view class="card">
      <text class="section">产品说明</text>
      <text class="body">
        本产品是 HunterAgents。分析能力参考开源 TradingAgents，本产品不是该项目或其 CN 版本。
      </text>
      <text class="body">HunterAgents 1.0 提供：</text>
      <text class="item">手机号注册、登录、短信验证码和忘记密码</text>
      <text class="item">H5 与 PC 使用同一套账号</text>
      <text class="item">分析报告按用户分开存放</text>
      <text class="item">可打开的分析报告分享页</text>
      <text class="item">用户协议和隐私政策</text>
    </view>

    <view class="card">
      <view class="row">
        <text class="label">版本</text>
        <text class="value">1.0</text>
      </view>
      <view class="row">
        <text class="label">联系邮箱</text>
        <text class="value">ocm@onecloudmall.com</text>
      </view>
      <text class="body foot">
        开源组件遵循各自许可证；产品与协议以 HunterAgents 用户协议、隐私政策为准。
      </text>
      <text class="copy">© 2026 HunterAgents</text>
      <text class="beian" @click="openBeian">京ICP备2021035986号-4</text>
    </view>
  </view>
</template>

<script setup lang="ts">
function openBeian() {
  if (typeof window !== "undefined") {
    window.open("https://beian.miit.gov.cn/", "_blank", "noopener");
  }
}
</script>

<style lang="scss" scoped>
.about {
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}

.card {
  background: #fff;
  border-radius: 12px;
  padding: 32rpx;
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.title {
  font-size: 22px;
  font-weight: 600;
  color: var(--ha-text-primary);
}

.subtitle {
  font-size: 14px;
  color: #606266;
}

.section {
  font-size: 16px;
  font-weight: 600;
  color: var(--ha-text-primary);
}

.body,
.item {
  font-size: 14px;
  line-height: 1.7;
  color: #606266;
}

.item {
  padding-left: 8rpx;
}

.row {
  display: flex;
  justify-content: space-between;
  gap: 24rpx;
  font-size: 14px;
}

.label {
  color: #909399;
}

.value {
  color: var(--ha-text-primary);
  text-align: right;
}

.foot {
  margin-top: 8rpx;
}

.copy,
.beian {
  font-size: 12px;
  color: #909399;
}

.beian {
  color: #409eff;
}
</style>
