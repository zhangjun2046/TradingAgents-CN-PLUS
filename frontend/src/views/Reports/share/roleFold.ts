/**
 * 岗位正文长文折叠阈值（可单测，不依赖 Vue 运行时）。
 *
 * 从 RolePanel.vue 抽离，与 CSS 的 max-height: 60vh 保持一致。
 */

/** 正文高度超过该比例视口高度时默认折叠；对应 .is-collapsed 的 60vh */
export const FOLD_HEIGHT_RATIO = 0.6

/** 正文渲染高度是否达到需要折叠的阈值 */
export function isFoldable(contentHeight: number, viewportHeight: number): boolean {
  return contentHeight > viewportHeight * FOLD_HEIGHT_RATIO
}