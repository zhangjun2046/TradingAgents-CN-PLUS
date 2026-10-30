<template>
  <p class="wx-guide" role="note">若直接下载受限，请点击右上角「…」选择「在浏览器中打开」后再导出</p>
</template>

<style lang="scss" scoped>
.wx-guide {
  position: fixed;
  top: 12px;
  right: 12px;
  z-index: 60;
  max-width: 240px;
  margin: 0;
  padding: 12px 14px;
  border-radius: 12px;
  background: #fff;
  color: #303133;
  font-size: 13px;
  line-height: 1.6;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.16);
}

.wx-guide::after {
  content: '';
  position: absolute;
  top: -6px;
  right: 28px;
  width: 12px;
  height: 12px;
  background: #fff;
  transform: rotate(45deg);
}
</style>
