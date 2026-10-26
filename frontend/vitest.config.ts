import { defineConfig } from 'vitest/config'
import { resolve } from 'path'

/**
 * 单元测试配置（仅跑纯 TS 逻辑，不测组件，不引 @vue/test-utils）。
 * 通过 `npm test` 调用；测试文件位于各目录的 __tests__/ 下。
 */
export default defineConfig({
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  test: {
    environment: 'node',
    include: ['src/**/__tests__/**/*.test.ts'],
  },
})