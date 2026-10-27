import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

/**
 * 单元测试配置：
 * - 纯 TS 逻辑（node 环境）与 Vue 组件（jsdom 环境）分开跑。
 * - `environmentMatchGlobs` 让 .vue 相关的测试使用 jsdom，
 *   其余纯函数测试继续使用 node 环境，避免拖慢速度。
 * - 通过 `npm test` 调用；测试文件位于各目录的 __tests__/ 下。
 */
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  test: {
    environment: 'node',
    environmentMatchGlobs: [
      ['src/**/__tests__/**/*.vue.test.ts', 'jsdom'],
      ['src/**/__tests__/**/*.spec.ts', 'jsdom'],
    ],
    include: ['src/**/__tests__/**/*.test.ts'],
  },
})