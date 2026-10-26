<template>
  <nav class="dept-tabs">
    <div ref="deptRowRef" class="dept-row" role="tablist" aria-label="部门">
      <button
        v-for="dept in departments"
        :key="dept.key"
        type="button"
        role="tab"
        class="dept-tab"
        :class="{ 'is-active': dept.key === activeDeptKey }"
        :aria-selected="dept.key === activeDeptKey"
        @click="emit('select', dept.key)"
      >
        {{ dept.name }}
      </button>
    </div>

    <div v-if="showSubTabs" ref="roleRowRef" class="role-row" role="tablist" aria-label="岗位">
      <button
        v-for="role in roles"
        :key="role.key"
        type="button"
        role="tab"
        class="role-tab"
        :class="{ 'is-active': role.key === activeRoleKey }"
        :aria-selected="role.key === activeRoleKey"
        @click="emit('select-role', role)"
      >
        {{ role.name }}
      </button>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import type { VisibleDept, VisibleRole } from './shareConfig'

const props = defineProps<{
  departments: VisibleDept[]
  roles: VisibleRole[]
  activeDeptKey: string
  activeRoleKey: string
  showSubTabs: boolean
}>()

const deptRowRef = ref<HTMLElement | null>(null)
const roleRowRef = ref<HTMLElement | null>(null)

/** 只滚动页签行，避免 scrollIntoView 把整页拉开。选中项必须完整落在可视区内。 */
function revealActive(row: HTMLElement | null): void {
  if (!row) return
  const active = row.querySelector<HTMLElement>('.is-active')
  if (!active) return
  const rowBox = row.getBoundingClientRect()
  const tabBox = active.getBoundingClientRect()
  const pad = 8
  if (tabBox.left < rowBox.left + pad) {
    row.scrollLeft -= rowBox.left + pad - tabBox.left
  } else if (tabBox.right > rowBox.right - pad) {
    row.scrollLeft += tabBox.right - (rowBox.right - pad)
  }
}

watch(
  () => [props.activeDeptKey, props.activeRoleKey, props.showSubTabs, props.roles.length],
  async () => {
    await nextTick()
    revealActive(deptRowRef.value)
    revealActive(roleRowRef.value)
  },
  { immediate: true }
)

const emit = defineEmits<{
  (e: 'select', deptKey: string): void
  (e: 'select-role', role: VisibleRole): void
}>()
</script>

<style lang="scss" scoped>
.dept-tabs {
  position: sticky;
  top: 0;
  z-index: 10;
  margin: 0 -16px 14px;
  padding: 8px 16px;
  background: #f5f7fa;
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box;
}

.dept-row,
.role-row {
  display: flex;
  gap: 8px;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  overflow-x: auto;
  scrollbar-width: none;

  &::-webkit-scrollbar {
    display: none;
  }
}

.role-row {
  margin-top: 8px;
}

.dept-tab,
.role-tab {
  flex: 0 0 auto;
  border: 0;
  cursor: pointer;
  white-space: nowrap;
  font-family: inherit;
}

.dept-tab {
  padding: 8px 16px;
  border-radius: 999px;
  background: #fff;
  color: #606266;
  font-size: 14px;
  font-weight: 600;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
  transition: background 0.2s, color 0.2s, box-shadow 0.2s;

  &.is-active {
    background: linear-gradient(90deg, #3b82f6, #1d4ed8);
    color: #fff;
    box-shadow: 0 8px 20px rgba(37, 99, 235, 0.35);
  }
}

.role-tab {
  padding: 6px 12px;
  border-radius: 8px;
  border: 1px solid #dcdfe6;
  background: #fff;
  color: #606266;
  font-size: 13px;

  &.is-active {
    border-color: #3b82f6;
    background: #fff;
    color: #3b82f6;
    font-weight: 600;
  }
}

@media (max-width: 480px) {
  .dept-tabs {
    margin: 0 -12px 12px;
    padding: 8px 12px;
  }
}
</style>
