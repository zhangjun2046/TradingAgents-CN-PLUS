<template>
  <div class="user-management">
    <el-card shadow="never">
      <template #header>
        <h3>用户管理</h3>
      </template>
      <el-table :data="users" v-loading="loading" stripe>
        <el-table-column prop="username" label="用户名" min-width="140" />
        <el-table-column label="手机号" min-width="140">
          <template #default="{ row }">
            <el-tooltip v-if="row.phone" :content="row.phone" placement="top">
              <span>{{ maskPhone(row.phone) }}</span>
            </el-tooltip>
            <span v-else>—</span>
          </template>
        </el-table-column>
        <el-table-column prop="email" label="邮箱" min-width="180">
          <template #default="{ row }">{{ row.email || '—' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.is_active === false ? 'warning' : 'success'" size="small">
              {{ row.is_active === false ? '停用' : '正常' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { authApi, extractAuthError } from '@/api/auth'
import type { User } from '@/types/auth'

const users = ref<User[]>([])
const loading = ref(false)

function maskPhone(phone: string) {
  if (!phone || phone.length < 7) return phone
  return `${phone.slice(0, 3)}****${phone.slice(-4)}`
}

onMounted(async () => {
  loading.value = true
  try {
    const res = await authApi.listUsers()
    const data = (res as any).data || res
    users.value = data.users || []
  } catch (error) {
    ElMessage.error(extractAuthError(error) || '加载用户列表失败')
  } finally {
    loading.value = false
  }
})
</script>
