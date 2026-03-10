<template>
  <div class="empty-state">
    <div class="empty-state-content">
      <!-- 图标 -->
      <div class="empty-state-icon">
        <el-icon v-if="type === 'no-data'" :size="80" color="#dcdfe6">
          <Box />
        </el-icon>
        <el-icon v-else-if="type === 'no-search'" :size="80" color="#dcdfe6">
          <Search />
        </el-icon>
        <el-icon v-else-if="type === 'no-network'" :size="80" color="#dcdfe6">
          <Connection />
        </el-icon>
        <el-icon v-else-if="type === 'error'" :size="80" color="#f56c6c">
          <CircleCloseFilled />
        </el-icon>
        <el-icon v-else :size="80" color="#dcdfe6">
          <Box />
        </el-icon>
      </div>

      <!-- 标题 -->
      <div class="empty-state-title">
        {{ title }}
      </div>

      <!-- 描述 -->
      <div v-if="description" class="empty-state-description">
        {{ description }}
      </div>

      <!-- 操作按钮 -->
      <div v-if="showAction" class="empty-state-action">
        <el-button type="primary" @click="handleAction">
          {{ actionText }}
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  Box,
  Search,
  Connection,
  CircleCloseFilled
} from '@element-plus/icons-vue'

interface Props {
  type?: 'no-data' | 'no-search' | 'no-network' | 'error' | 'default'
  title?: string
  description?: string
  showAction?: boolean
  actionText?: string
}

interface Emits {
  (e: 'action'): void
}

const props = withDefaults(defineProps<Props>(), {
  type: 'no-data',
  title: '暂无数据',
  description: '',
  showAction: false,
  actionText: '重新加载'
})

const emit = defineEmits<Emits>()

const handleAction = () => {
  emit('action')
}
</script>

<style scoped>
.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
  padding: 40px 20px;
}

.empty-state-content {
  text-align: center;
}

.empty-state-icon {
  margin-bottom: 20px;
}

.empty-state-title {
  font-size: 18px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 12px;
}

.empty-state-description {
  font-size: 14px;
  color: #909399;
  margin-bottom: 24px;
  line-height: 1.6;
}

.empty-state-action {
  margin-top: 8px;
}
</style>
