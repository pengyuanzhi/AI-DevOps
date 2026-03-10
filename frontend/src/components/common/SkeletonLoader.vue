<template>
  <div class="skeleton-loader">
    <!-- 卡片骨架屏 -->
    <div v-if="type === 'card'" class="skeleton-card">
      <el-skeleton animated>
        <template #template>
          <div class="skeleton-card-content">
            <el-skeleton-item variant="circle" style="width: 50px; height: 50px;" />
            <div class="skeleton-text">
              <el-skeleton-item variant="h3" style="width: 50%;" />
              <el-skeleton-item variant="text" style="margin-top: 10px; width: 80%;" />
            </div>
          </div>
        </template>
      </el-skeleton>
    </div>

    <!-- 表格骨架屏 -->
    <div v-else-if="type === 'table'" class="skeleton-table">
      <el-skeleton :rows="rows" animated />
    </div>

    <!-- 列表骨架屏 -->
    <div v-else-if="type === 'list'" class="skeleton-list">
      <el-skeleton :rows="rows" animated>
        <template #template>
          <div v-for="i in rows" :key="i" class="skeleton-list-item">
            <el-skeleton-item variant="circle" style="width: 40px; height: 40px;" />
            <div class="skeleton-list-content">
              <el-skeleton-item variant="h3" style="width: 60%; margin-bottom: 10px;" />
              <el-skeleton-item variant="text" style="width: 40%;" />
            </div>
          </div>
        </template>
      </el-skeleton>
    </div>

    <!-- 统计卡片骨架屏 -->
    <div v-else-if="type === 'stat'" class="skeleton-stat">
      <el-skeleton animated>
        <template #template>
          <div class="skeleton-stat-content">
            <el-skeleton-item variant="circle" style="width: 60px; height: 60px;" />
            <div class="skeleton-stat-text">
              <el-skeleton-item variant="h1" style="width: 40%;" />
              <el-skeleton-item variant="text" style="margin-top: 10px; width: 60%;" />
            </div>
          </div>
        </template>
      </el-skeleton>
    </div>

    <!-- 图表骨架屏 -->
    <div v-else-if="type === 'chart'" class="skeleton-chart">
      <el-skeleton animated>
        <template #template>
          <el-skeleton-item variant="rect" style="width: 100%; height: 350px;" />
        </template>
      </el-skeleton>
    </div>

    <!-- 通用骨架屏 -->
    <div v-else class="skeleton-default">
      <el-skeleton :rows="rows" animated />
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  type?: 'card' | 'table' | 'list' | 'stat' | 'chart' | 'default'
  rows?: number
}

withDefaults(defineProps<Props>(), {
  type: 'default',
  rows: 5
})
</script>

<style scoped>
.skeleton-loader {
  width: 100%;
}

/* 卡片骨架屏 */
.skeleton-card {
  padding: 20px;
  background: #fff;
  border-radius: 4px;
}

.skeleton-card-content {
  display: flex;
  align-items: center;
  gap: 20px;
}

.skeleton-text {
  flex: 1;
}

/* 列表骨架屏 */
.skeleton-list-item {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 15px 0;
  border-bottom: 1px solid #f0f0f0;
}

.skeleton-list-item:last-child {
  border-bottom: none;
}

.skeleton-list-content {
  flex: 1;
}

/* 统计卡片骨架屏 */
.skeleton-stat {
  padding: 20px;
  background: #fff;
  border-radius: 4px;
}

.skeleton-stat-content {
  display: flex;
  align-items: center;
  gap: 20px;
}

.skeleton-stat-text {
  flex: 1;
}

/* 图表骨架屏 */
.skeleton-chart {
  padding: 20px;
  background: #fff;
  border-radius: 4px;
}

/* 默认骨架屏 */
.skeleton-default {
  padding: 20px;
  background: #fff;
  border-radius: 4px;
}
</style>
