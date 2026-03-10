<template>
  <div class="build-view">
    <el-row :gutter="20">
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>构建管理</span>
              <el-button type="primary" size="small" @click="showTriggerDialog = true">
                触发构建
              </el-button>
            </div>
          </template>

          <!-- 筛选器 -->
          <el-form :inline="true" class="filter-form">
            <el-form-item label="项目">
              <el-select v-model="filters.projectId" placeholder="选择项目" clearable>
                <el-option label="所有项目" value="" />
                <el-option v-for="project in projects" :key="project.id"
                  :label="project.name" :value="project.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="状态">
              <el-select v-model="filters.status" placeholder="选择状态" clearable>
                <el-option label="全部" value="" />
                <el-option label="运行中" value="running" />
                <el-option label="成功" value="success" />
                <el-option label="失败" value="failed" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="fetchBuilds">查询</el-button>
            </el-form-item>
          </el-form>

          <!-- 构建列表 -->
          <el-table :data="builds" style="width: 100%" v-loading="loading">
            <el-table-column prop="id" label="构建ID" width="100" />
            <el-table-column prop="project" label="项目" width="200" />
            <el-table-column prop="branch" label="分支" width="150" />
            <el-table-column prop="commit" label="提交SHA" width="100" show-overflow-tooltip />
            <el-table-column label="状态" width="120">
              <template #default="scope">
                <el-tag :type="getStatusType(scope.row.status)">
                  {{ scope.row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="duration" label="耗时" width="100" />
            <el-table-column prop="createdAt" label="开始时间" width="180" />
            <el-table-column label="操作" width="250">
              <template #default="scope">
                <el-button type="text" size="small" @click="viewLogs(scope.row)">
                  查看日志
                </el-button>
                <el-button type="text" size="small" @click="viewArtifacts(scope.row)"
                  v-if="scope.row.status === 'success'">
                  产物
                </el-button>
                <el-button type="text" size="small" @click="cancelBuild(scope.row)"
                  v-if="scope.row.status === 'running'">
                  取消
                </el-button>
                <el-button type="text" size="small" @click="retryBuild(scope.row)"
                  v-if="scope.row.status === 'failed'">
                  重试
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <!-- 分页 -->
          <el-pagination
            v-model:current-page="pagination.page"
            v-model:page-size="pagination.perPage"
            :total="pagination.total"
            @current-change="fetchBuilds"
            @size-change="fetchBuilds"
            layout="total, sizes, prev, pager, next, jumper"
            style="margin-top: 20px"
          />
        </el-card>
      </el-col>
    </el-row>

    <!-- 触发构建对话框 -->
    <el-dialog v-model="showTriggerDialog" title="触发构建" width="500px">
      <el-form :model="triggerForm" label-width="100px">
        <el-form-item label="项目">
          <el-select v-model="triggerForm.projectId" placeholder="选择项目">
            <el-option v-for="project in projects" :key="project.id"
              :label="project.name" :value="project.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="分支">
          <el-input v-model="triggerForm.branch" placeholder="例如: main" />
        </el-form-item>
        <el-form-item label="构建类型">
          <el-select v-model="triggerForm.buildType">
            <el-option label="Debug" value="Debug" />
            <el-option label="Release" value="Release" />
            <el-option label="RelWithDebInfo" value="RelWithDebInfo" />
          </el-select>
        </el-form-item>
        <el-form-item label="并行任务">
          <el-input-number v-model="triggerForm.parallelJobs" :min="1" :max="16" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showTriggerDialog = false">取消</el-button>
        <el-button type="primary" @click="triggerBuild">确定</el-button>
      </template>
    </el-dialog>

    <!-- 构建日志对话框 -->
    <el-dialog v-model="showLogsDialog" title="构建日志" width="900px" @close="closeLogsDialog">
      <div class="logs-header">
        <el-tag :type="wsConnected ? 'success' : 'danger'">
          {{ wsConnected ? '实时连接中' : '连接断开' }}
        </el-tag>
        <el-button size="small" @click="clearLogs" style="margin-left: 10px">清空日志</el-button>
        <el-button size="small" @click="toggleAutoScroll" style="margin-left: 10px">
          {{ autoScroll ? '停止滚动' : '自动滚动' }}
        </el-button>
      </div>
      <div class="build-logs" ref="logsContainer">
        <div v-for="(log, index) in realtimeLogs" :key="index" :class="['log-line', `log-${log.level}`]">
          <span class="log-time">{{ formatLogTime(log.timestamp) }}</span>
          <span class="log-level">[{{ log.level.toUpperCase() }}]</span>
          <span class="log-message">{{ log.message }}</span>
        </div>
        <div v-if="realtimeLogs.length === 0" class="log-empty">
          {{ wsConnected ? '等待日志...' : '未连接' }}
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { useBuildLogs } from '@/composables/useWebSocket'

interface Build {
  id: number
  project: string
  branch: string
  commit: string
  status: string
  duration: string
  createdAt: string
}

interface Project {
  id: number
  name: string
}

const loading = ref(false)
const builds = ref<Build[]>([])
const projects = ref<Project[]>([])

const filters = ref({
  projectId: '',
  status: ''
})

const pagination = ref({
  page: 1,
  perPage: 20,
  total: 0
})

const showTriggerDialog = ref(false)
const showLogsDialog = ref(false)
const logsContainer = ref<HTMLElement>()
const autoScroll = ref(true)
const currentBuildId = ref<number | null>(null)

const triggerForm = ref({
  projectId: null as number | null,
  branch: 'main',
  buildType: 'RelWithDebInfo',
  parallelJobs: 4
})

// WebSocket日志连接
const { isConnected: wsConnected, logs: realtimeLogs, startWatching, stopWatching, clearLogs: clearWsLogs } = useBuildLogs(0)

const getStatusType = (status: string) => {
  const typeMap: Record<string, any> = {
    running: 'warning',
    success: 'success',
    failed: 'danger',
    pending: 'info'
  }
  return typeMap[status] || 'info'
}

const fetchBuilds = async () => {
  loading.value = true
  try {
    // TODO: 调用实际的API
    // const response = await request.get('/api/v1/build/list', {
    //   params: { ...filters.value, ...pagination.value }
    // })
    // builds.value = response.data.items
    // pagination.value.total = response.data.total

    builds.value = [
      { id: 1, project: 'backend-api', branch: 'main', commit: 'abc123', status: 'success', duration: '12m', createdAt: '2024-03-08 10:00' },
      { id: 2, project: 'frontend-app', branch: 'dev', commit: 'def456', status: 'running', duration: '-', createdAt: '2024-03-08 11:00' },
      { id: 3, project: 'ml-service', branch: 'feature', commit: 'ghi789', status: 'failed', duration: '8m', createdAt: '2024-03-08 09:00' }
    ]
    pagination.value.total = 3
  } catch (_error) {
    ElMessage.error('获取构建列表失败')
  } finally {
    loading.value = false
  }
}

const fetchProjects = async () => {
  try {
    // TODO: 调用实际的API
    projects.value = [
      { id: 1, name: 'backend-api' },
      { id: 2, name: 'frontend-app' }
    ]
  } catch (_error) {
    ElMessage.error('获取项目列表失败')
  }
}

const triggerBuild = async () => {
  try {
    // TODO: 调用实际的API
    ElMessage.success('构建已触发')
    showTriggerDialog.value = false
    fetchBuilds()
  } catch (_error) {
    ElMessage.error('触发构建失败')
  }
}

const viewLogs = async (build: Build) => {
  currentBuildId.value = build.id
  showLogsDialog.value = true

  // 启动WebSocket实时日志
  if (build.id) {
    await startWatching()
  }
}

const closeLogsDialog = () => {
  stopWatching()
  currentBuildId.value = null
}

const clearLogs = () => {
  clearWsLogs()
}

const toggleAutoScroll = () => {
  autoScroll.value = !autoScroll.value
}

const viewArtifacts = (build: Build) => {
  ElMessage.info(`查看构建产物功能开发中: ${build.project}`)
}

const cancelBuild = async (build: Build) => {
  try {
    // TODO: 调用实际的API
    ElMessage.success('构建已取消')
    fetchBuilds()
  } catch (_error) {
    ElMessage.error('取消构建失败')
  }
}

const retryBuild = async (build: Build) => {
  try {
    // TODO: 调用实际的API
    ElMessage.success('构建已重试')
    fetchBuilds()
  } catch (_error) {
    ElMessage.error('重试构建失败')
  }
}

const formatLogTime = (timestamp: number) => {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', { hour12: false }) + '.' + date.getMilliseconds().toString().padStart(3, '0')
}

// 监听日志变化，自动滚动到底部
import { watch } from 'vue'
watch(realtimeLogs, async () => {
  if (autoScroll.value && logsContainer.value) {
    await nextTick()
    logsContainer.value.scrollTop = logsContainer.value.scrollHeight
  }
})

onMounted(() => {
  fetchBuilds()
  fetchProjects()
})

onUnmounted(() => {
  stopWatching()
})
</script>

<style scoped>
.build-view {
  padding: 20px;
}

.filter-form {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logs-header {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
  padding-bottom: 10px;
  border-bottom: 1px solid #eee;
}

.build-logs {
  max-height: 500px;
  overflow-y: auto;
  background: #1e1e1e;
  padding: 15px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
}

.log-line {
  color: #d4d4d4;
  padding: 2px 0;
  white-space: pre-wrap;
  word-break: break-all;
}

.log-line:hover {
  background: rgba(255, 255, 255, 0.05);
}

.log-time {
  color: #858585;
  margin-right: 8px;
}

.log-level {
  font-weight: bold;
  margin-right: 8px;
}

.log-info .log-level {
  color: #4fc3f7;
}

.log-warning .log-level {
  color: #ffb74d;
}

.log-error .log-level {
  color: #f44336;
}

.log-message {
  color: #d4d4d4;
}

.log-empty {
  color: #858585;
  text-align: center;
  padding: 20px;
}
</style>
