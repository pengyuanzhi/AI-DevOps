<template>
  <div class="test-view">
    <el-row :gutter="20">
      <!-- 统计卡片 -->
      <el-col :span="6" v-for="stat in stats" :key="stat.title">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-title">{{ stat.title }}</div>
            <div class="stat-value" :style="{ color: stat.color }">{{ stat.value }}</div>
            <div class="stat-subtitle">{{ stat.subtitle }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>测试执行</span>
              <div>
                <el-button type="primary" size="small" @click="showRunDialog = true">
                  运行测试
                </el-button>
                <el-button size="small" @click="showSmartSelection = true">
                  智能测试选择
                </el-button>
              </div>
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
                <el-option label="通过" value="passed" />
                <el-option label="失败" value="failed" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="fetchTestRuns">查询</el-button>
            </el-form-item>
          </el-form>

          <!-- 测试列表 -->
          <el-table :data="testRuns" style="width: 100%" v-loading="loading">
            <el-table-column prop="id" label="运行ID" width="100" />
            <el-table-column prop="project" label="项目" width="200" />
            <el-table-column prop="suite" label="测试套件" width="200" />
            <el-table-column label="结果" width="100">
              <template #default="scope">
                <el-tag :type="getResultType(scope.row.status)">
                  {{ scope.row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="totalTests" label="总用例" width="100" align="center" />
            <el-table-column prop="passedTests" label="通过" width="80" align="center">
              <template #default="scope">
                <span style="color: #67c23a">{{ scope.row.passedTests }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="failedTests" label="失败" width="80" align="center">
              <template #default="scope">
                <span style="color: #f56c6c">{{ scope.row.failedTests }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="duration" label="耗时" width="100" />
            <el-table-column prop="coverage" label="覆盖率" width="100" />
            <el-table-column prop="createdAt" label="运行时间" width="180" />
            <el-table-column label="操作" width="150">
              <template #default="scope">
                <el-button type="text" size="small" @click="viewReport()">
                  报告
                </el-button>
                <el-button type="text" size="small" @click="viewFailedTests()"
                  v-if="scope.row.failedTests > 0">
                  失败用例
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <!-- 分页 -->
          <el-pagination
            v-model:current-page="pagination.page"
            v-model:page-size="pagination.perPage"
            :total="pagination.total"
            @current-change="fetchTestRuns"
            @size-change="fetchTestRuns"
            layout="total, sizes, prev, pager, next, jumper"
            style="margin-top: 20px"
          />
        </el-card>
      </el-col>
    </el-row>

    <!-- 运行测试对话框 -->
    <el-dialog v-model="showRunDialog" title="运行测试" width="500px">
      <el-form :model="runForm" label-width="120px">
        <el-form-item label="项目">
          <el-select v-model="runForm.projectId" placeholder="选择项目">
            <el-option v-for="project in projects" :key="project.id"
              :label="project.name" :value="project.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="构建目录">
          <el-input v-model="runForm.buildDir" placeholder="/path/to/build" />
        </el-form-item>
        <el-form-item label="测试类型">
          <el-select v-model="runForm.testType">
            <el-option label="Qt Test" value="qttest" />
            <el-option label="Google Test" value="googletest" />
          </el-select>
        </el-form-item>
        <el-form-item label="启用覆盖率">
          <el-switch v-model="runForm.enableCoverage" />
        </el-form-item>
        <el-form-item label="启用智能选择">
          <el-switch v-model="runForm.enableSmartSelection" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showRunDialog = false">取消</el-button>
        <el-button type="primary" @click="runTests">确定</el-button>
      </template>
    </el-dialog>

    <!-- 智能测试选择对话框 -->
    <el-dialog v-model="showSmartSelection" title="智能测试选择" width="800px">
      <el-form :model="selectionForm" label-width="120px">
        <el-form-item label="源分支">
          <el-input v-model="selectionForm.sourceBranch" placeholder="feature-branch" />
        </el-form-item>
        <el-form-item label="目标分支">
          <el-input v-model="selectionForm.targetBranch" placeholder="main" />
        </el-form-item>
        <el-form-item label="保守模式">
          <el-switch v-model="selectionForm.conservative" />
          <span style="margin-left: 10px; color: #999; font-size: 12px">
            启用后会选择更多测试，降低遗漏风险
          </span>
        </el-form-item>
      </el-form>

      <el-divider />

      <div v-if="selectionResult">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-statistic title="选择的测试" :value="selectionResult.selected_count" />
          </el-col>
          <el-col :span="8">
            <el-statistic title="跳过的测试" :value="selectionResult.skip_count" />
          </el-col>
          <el-col :span="8">
            <el-statistic 
              title="节省时间" 
              :value="selectionResult.time_saved_percent" 
              suffix="%" 
            />
          </el-col>
        </el-row>

        <el-divider />

        <h4>受影响的文件</h4>
        <el-tag v-for="file in selectionResult.affected_files.slice(0, 10)" 
          :key="file" style="margin: 5px">
          {{ file }}
        </el-tag>
        <el-tag v-if="selectionResult.affected_files.length > 10">
          等{{ selectionResult.affected_files.length }}个文件
        </el-tag>
      </div>

      <template #footer>
        <el-button @click="showSmartSelection = false">取消</el-button>
        <el-button type="primary" @click="applySelection" :disabled="!selectionResult">
          应用选择并运行
        </el-button>
      </template>
    </el-dialog>

    <!-- 失败用例对话框 -->
    <el-dialog v-model="showFailedTestsDialog" title="失败用例详情" width="900px">
      <el-table :data="failedTestCases" style="width: 100%">
        <el-table-column prop="name" label="用例名称" width="200" />
        <el-table-column prop="suite" label="测试套件" width="150" />
        <el-table-column prop="error" label="错误信息" show-overflow-tooltip />
        <el-table-column label="操作" width="100">
          <template #default>
            <el-button type="text" size="small">
              查看日志
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'

interface TestRun {
  id: number
  project: string
  suite: string
  status: string
  totalTests: number
  passedTests: number
  failedTests: number
  duration: string
  coverage: string
  createdAt: string
}

interface Project {
  id: number
  name: string
}

interface TestCase {
  name: string
  suite: string
  error: string
}

const loading = ref(false)
const testRuns = ref<TestRun[]>([])
const projects = ref<Project[]>([])

const stats = ref([
  { title: '总测试数', value: '1,234', subtitle: '活跃测试用例', color: '#409eff' },
  { title: '通过率', value: '95.2%', subtitle: '最近7天平均', color: '#67c23a' },
  { title: '平均耗时', value: '5.8m', subtitle: '单次测试运行', color: '#e6a23c' },
  { title: '覆盖率', value: '78.5%', subtitle: '代码覆盖率', color: '#909399' }
])

const filters = ref({
  projectId: '',
  status: ''
})

const pagination = ref({
  page: 1,
  perPage: 20,
  total: 0
})

const showRunDialog = ref(false)
const showSmartSelection = ref(false)
const showFailedTestsDialog = ref(false)

const runForm = ref({
  projectId: null as number | null,
  buildDir: '',
  testType: 'qttest',
  enableCoverage: true,
  enableSmartSelection: false
})

const selectionForm = ref({
  sourceBranch: '',
  targetBranch: 'main',
  conservative: false
})

const selectionResult = ref<any>(null)
const failedTestCases = ref<TestCase[]>([])

const getResultType = (status: string) => {
  const typeMap: Record<string, any> = {
    running: 'warning',
    passed: 'success',
    failed: 'danger',
    skipped: 'info'
  }
  return typeMap[status] || 'info'
}

const fetchTestRuns = async () => {
  loading.value = true
  try {
    // TODO: 调用实际的API
    testRuns.value = [
      { id: 1, project: 'backend-api', suite: 'ApiTest', status: 'passed', totalTests: 100, passedTests: 98, failedTests: 2, duration: '5m', coverage: '75%', createdAt: '2024-03-08 10:00' },
      { id: 2, project: 'frontend-app', suite: 'UiTest', status: 'failed', totalTests: 50, passedTests: 45, failedTests: 5, duration: '8m', coverage: '68%', createdAt: '2024-03-08 11:00' },
      { id: 3, project: 'ml-service', suite: 'ModelTest', status: 'running', totalTests: 30, passedTests: 0, failedTests: 0, duration: '-', coverage: '-', createdAt: '2024-03-08 12:00' }
    ]
    pagination.value.total = 3
  } catch (_error) {
    ElMessage.error('获取测试列表失败')
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

const runTests = async () => {
  try {
    // TODO: 调用实际的API
    ElMessage.success('测试已启动')
    showRunDialog.value = false
    fetchTestRuns()
  } catch (_error) {
    ElMessage.error('启动测试失败')
  }
}

const analyzeSelection = async () => {
  try {
    // TODO: 调用实际的API
    selectionResult.value = {
      selected_count: 45,
      skip_count: 155,
      time_saved_percent: 77.5,
      affected_files: ['src/api/user.cpp', 'src/service/auth.cpp', 'include/user.h'],
      confidence: 0.85
    }
  } catch (_error) {
    ElMessage.error('测试选择分析失败')
  }
}

const applySelection = () => {
  showSmartSelection.value = false
  ElMessage.success(`已选择 ${selectionResult.value.selected_count} 个测试`)
}

const viewReport = () => {
  ElMessage.info('测试报告功能开发中')
}

const viewFailedTests = () => {
  showFailedTestsDialog.value = true
  // TODO: 调用API获取失败的测试用例
  failedTestCases.value = [
    { name: 'testUserLogin', suite: 'ApiTest', error: 'Assertion failed: expected 200 but got 500' },
    { name: 'testCreateUser', suite: 'ApiTest', error: 'Timeout: request exceeded 5000ms' }
  ]
}

// 监听选择表单变化
const { sourceBranch, targetBranch } = selectionForm.value
if (sourceBranch && targetBranch) {
  analyzeSelection()
}

onMounted(() => {
  fetchTestRuns()
  fetchProjects()
})
</script>

<style scoped>
.test-view {
  padding: 20px;
}

.stat-card {
  text-align: center;
}

.stat-content {
  padding: 10px;
}

.stat-title {
  font-size: 14px;
  color: #999;
  margin-bottom: 10px;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  margin-bottom: 5px;
}

.stat-subtitle {
  font-size: 12px;
  color: #999;
}

.filter-form {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
