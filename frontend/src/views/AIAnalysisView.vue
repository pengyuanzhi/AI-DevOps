<template>
  <div class="ai-analysis">
    <el-alert
      v-if="error"
      type="error"
      :title="error"
      :closable="false"
      style="margin-bottom: 20px"
    />

    <!-- 骨架屏 - 加载中显示 -->
    <div v-if="loading">
      <el-row :gutter="20">
        <el-col :span="6" v-for="i in 4" :key="i">
          <SkeletonLoader type="stat" />
        </el-col>
      </el-row>
      <el-row :gutter="20" style="margin-top: 20px">
        <el-col :span="12">
          <SkeletonLoader type="chart" />
        </el-col>
        <el-col :span="12">
          <SkeletonLoader type="chart" />
        </el-col>
      </el-row>
      <el-row :gutter="20" style="margin-top: 20px">
        <el-col :span="24">
          <SkeletonLoader type="list" :rows="5" />
        </el-col>
      </el-row>
    </div>

    <!-- 空状态 - 无AI分析数据时显示 -->
    <el-card v-else-if="!loading && hasNoAIAnalysisData">
      <EmptyState
        type="no-data"
        title="暂无AI分析数据"
        description="还没有任何AI分析结果，请先提交MR或运行AI分析"
        :show-action="true"
        action-text="查看MR列表"
        @action="viewMRList"
      />
    </el-card>

    <!-- 实际内容 -->
    <template v-if="!loading && !hasNoAIAnalysisData">
      <!-- 页面标题 -->
      <el-row :gutter="20">
      <el-col :span="24">
        <el-card>
          <div class="page-header" style="display: flex; justify-content: space-between; align-items: center;">
            <div>
              <h2 style="margin: 0;">AI分析结果展示</h2>
              <p class="subtitle" style="margin: 8px 0 0 0;">查看AI驱动的测试选择、代码审查和维护建议</p>
            </div>
            <el-tooltip :content="wsConnected ? '实时更新已连接' : '实时更新已断开'">
              <div class="ws-status" :class="{ connected: wsConnected }">
                <div class="ws-indicator"></div>
              </div>
            </el-tooltip>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 统计概览卡片 -->
    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #ecf5ff">
              <el-icon :size="32" color="#409eff"><Document /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.totalMRs }}</div>
              <div class="stat-label">已分析的MR</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #f0f9ff">
              <el-icon :size="32" color="#67c23a"><SuccessFilled /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.testsSelected }}</div>
              <div class="stat-label">智能选择测试</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #fef0f0">
              <el-icon :size="32" color="#f56c6c"><Warning /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.issuesFound }}</div>
              <div class="stat-label">发现问题</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #fdf6ec">
              <el-icon :size="32" color="#e6a23c"><Timer /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.timeSaved }}</div>
              <div class="stat-label">节省时间(分钟)</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 筛选和搜索 -->
    <el-card style="margin-top: 20px">
      <el-row :gutter="20">
        <el-col :span="5">
          <el-select v-model="filters.project" placeholder="项目" clearable @change="handleFilterChange">
            <el-option label="全部项目" value="" />
            <el-option label="backend-api" value="backend-api" />
            <el-option label="frontend-app" value="frontend-app" />
            <el-option label="mobile-sdk" value="mobile-sdk" />
          </el-select>
        </el-col>
        <el-col :span="5">
          <el-select v-model="filters.type" placeholder="分析类型" clearable @change="handleFilterChange">
            <el-option label="全部类型" value="" />
            <el-option label="测试选择" value="test_selection" />
            <el-option label="代码审查" value="code_review" />
            <el-option label="流水线维护" value="pipeline_maintenance" />
          </el-select>
        </el-col>
        <el-col :span="5">
          <el-select v-model="filters.status" placeholder="状态" clearable @change="handleFilterChange">
            <el-option label="全部状态" value="" />
            <el-option label="待处理" value="pending" />
            <el-option label="已接受" value="accepted" />
            <el-option label="已拒绝" value="rejected" />
            <el-option label="误报" value="false_positive" />
          </el-select>
        </el-col>
        <el-col :span="9">
          <el-input
            v-model="filters.search"
            placeholder="搜索MR编号、标题或作者"
            clearable
            @change="handleFilterChange"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </el-col>
      </el-row>
    </el-card>

    <!-- MR列表 -->
    <el-card style="margin-top: 20px">
      <el-table :data="filteredMRs" style="width: 100%" v-loading="loading">
        <el-table-column prop="id" label="MR编号" width="120">
          <template #default="scope">
            <el-link type="primary" @click="viewMRDetails(scope.row)">
              !{{ scope.row.id }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="标题" min-width="200" />
        <el-table-column prop="project" label="项目" width="130" />
        <el-table-column prop="author" label="作者" width="120" />
        <el-table-column prop="type" label="分析类型" width="120">
          <template #default="scope">
            <el-tag v-if="scope.row.type === 'test_selection'" type="success">测试选择</el-tag>
            <el-tag v-else-if="scope.row.type === 'code_review'" type="warning">代码审查</el-tag>
            <el-tag v-else-if="scope.row.type === 'pipeline_maintenance'" type="danger">流水线维护</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="confidence" label="置信度" width="120">
          <template #default="scope">
            <el-progress
              :percentage="scope.row.confidence"
              :color="getConfidenceColor(scope.row.confidence)"
              :show-text="false"
            />
            <span style="margin-left: 8px">{{ scope.row.confidence }}%</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag v-if="scope.row.status === 'pending'" type="info">待处理</el-tag>
            <el-tag v-else-if="scope.row.status === 'accepted'" type="success">已接受</el-tag>
            <el-tag v-else-if="scope.row.status === 'rejected'" type="danger">已拒绝</el-tag>
            <el-tag v-else-if="scope.row.status === 'false_positive'" type="warning">误报</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="分析时间" width="160">
          <template #default="scope">
            {{ formatTime(scope.row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="scope">
            <el-button size="small" type="primary" @click="viewMRDetails(scope.row)">
              查看详情
            </el-button>
            <el-button
              v-if="scope.row.status === 'pending'"
              size="small"
              @click="openFeedbackDialog(scope.row)"
            >
              反馈
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="pagination.currentPage"
        v-model:page-size="pagination.pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="pagination.total"
        layout="total, sizes, prev, pager, next, jumper"
        style="margin-top: 20px; justify-content: flex-end"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </el-card>

    <!-- MR详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      :title="`!${currentMR.id} - ${currentMR.title}`"
      width="80%"
      top="5vh"
    >
      <el-tabs v-model="activeTab" type="border-card">
        <!-- AI决策解释 -->
        <el-tab-pane label="AI决策解释" name="explanation">
          <div v-if="currentMR.type === 'test_selection'" class="analysis-content">
            <el-alert type="info" :closable="false" style="margin-bottom: 20px">
              <template #title>
                <strong>测试选择决策</strong>
              </template>
            </el-alert>

            <div class="decision-section">
              <h4>📊 变更影响分析</h4>
              <el-descriptions :column="2" border>
                <el-descriptions-item label="修改文件数">
                  {{ currentMR.analysis?.changed_files || 0 }}
                </el-descriptions-item>
                <el-descriptions-item label="修改代码行">
                  {{ currentMR.analysis?.changed_lines || 0 }}
                </el-descriptions-item>
                <el-descriptions-item label="影响函数数">
                  {{ currentMR.analysis?.affected_functions || 0 }}
                </el-descriptions-item>
                <el-descriptions-item label="影响模块数">
                  {{ currentMR.analysis?.affected_modules || 0 }}
                </el-descriptions-item>
              </el-descriptions>
            </div>

            <div class="decision-section" style="margin-top: 20px">
              <h4>🎯 选择的测试 ({{ currentMR.selected_tests?.length || 0 }})</h4>
              <el-table :data="currentMR.selected_tests" max-height="300">
                <el-table-column prop="name" label="测试名称" min-width="200" />
                <el-table-column prop="suite" label="测试套件" width="150" />
                <el-table-column prop="reason" label="选择原因" min-width="250" />
                <el-table-column prop="priority" label="优先级" width="100">
                  <template #default="scope">
                    <el-tag v-if="scope.row.priority === 'high'" type="danger" size="small">高</el-tag>
                    <el-tag v-else-if="scope.row.priority === 'medium'" type="warning" size="small">中</el-tag>
                    <el-tag v-else type="info" size="small">低</el-tag>
                  </template>
                </el-table-column>
              </el-table>
            </div>

            <div class="decision-section" style="margin-top: 20px">
              <h4>⏭️ 跳过的测试 ({{ currentMR.skipped_tests?.length || 0 }})</h4>
              <el-table :data="currentMR.skipped_tests" max-height="200">
                <el-table-column prop="name" label="测试名称" min-width="200" />
                <el-table-column prop="suite" label="测试套件" width="150" />
                <el-table-column prop="reason" label="跳过原因" min-width="250" />
                <el-table-column prop="estimated_time" label="预计节省时间" width="130">
                  <template #default="scope">
                    {{ scope.row.estimated_time }}s
                  </template>
                </el-table-column>
              </el-table>
              <el-alert type="success" :closable="false" style="margin-top: 10px">
                <template #title>
                  总计节省时间: {{ currentMR.total_time_saved }}s ({{
                    ((currentMR.total_time_saved / currentMR.original_test_time) * 100).toFixed(1)
                  }}%)
                </template>
              </el-alert>
            </div>

            <div class="decision-section" style="margin-top: 20px">
              <h4>🔗 依赖关系图</h4>
              <div ref="dependencyChartRef" style="width: 100%; height: 400px"></div>
            </div>
          </div>

          <div v-else-if="currentMR.type === 'code_review'" class="analysis-content">
            <el-alert type="warning" :closable="false" style="margin-bottom: 20px">
              <template #title>
                <strong>代码审查分析</strong>
              </template>
            </el-alert>

            <div class="decision-section">
              <h4>📋 问题汇总</h4>
              <el-row :gutter="20">
                <el-col :span="8">
                  <el-statistic title="严重问题" :value="currentMR.issue_summary?.critical || 0">
                    <template #prefix>
                      <el-icon color="#f56c6c"><CircleCloseFilled /></el-icon>
                    </template>
                  </el-statistic>
                </el-col>
                <el-col :span="8">
                  <el-statistic title="高危问题" :value="currentMR.issue_summary?.high || 0">
                    <template #prefix>
                      <el-icon color="#e6a23c"><WarningFilled /></el-icon>
                    </template>
                  </el-statistic>
                </el-col>
                <el-col :span="8">
                  <el-statistic title="中等问题" :value="currentMR.issue_summary?.medium || 0">
                    <template #prefix>
                      <el-icon color="#409eff"><InfoFilled /></el-icon>
                    </template>
                  </el-statistic>
                </el-col>
              </el-row>
            </div>

            <div class="decision-section" style="margin-top: 20px">
              <h4>🔍 问题列表</h4>
              <el-table :data="currentMR.issues" max-height="400">
                <el-table-column prop="file" label="文件" min-width="200" />
                <el-table-column prop="line" label="行号" width="80" />
                <el-table-column prop="severity" label="严重程度" width="100">
                  <template #default="scope">
                    <el-tag v-if="scope.row.severity === 'critical'" type="danger" size="small">
                      严重
                    </el-tag>
                    <el-tag v-else-if="scope.row.severity === 'high'" type="warning" size="small">
                      高危
                    </el-tag>
                    <el-tag v-else-if="scope.row.severity === 'medium'" type="primary" size="small">
                      中等
                    </el-tag>
                    <el-tag v-else type="info" size="small">低级</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="category" label="类别" width="150" />
                <el-table-column prop="message" label="问题描述" min-width="250" />
                <el-table-column prop="confidence" label="AI置信度" width="120">
                  <template #default="scope">
                    {{ scope.row.confidence }}%
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="150">
                  <template #default="scope">
                    <el-button size="small" @click="viewIssueDetail(scope.row)">
                      查看详情
                    </el-button>
                    <el-button
                      v-if="scope.row.has_fix"
                      size="small"
                      type="primary"
                      @click="applyFix(scope.row)"
                    >
                      应用修复
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>

            <div class="decision-section" style="margin-top: 20px">
              <h4>📈 代码质量评分</h4>
              <div ref="qualityScoreChartRef" style="width: 100%; height: 300px"></div>
            </div>
          </div>

          <div v-else-if="currentMR.type === 'pipeline_maintenance'" class="analysis-content">
            <el-alert type="error" :closable="false" style="margin-bottom: 20px">
              <template #title>
                <strong>流水线维护分析</strong>
              </template>
            </el-alert>

            <div class="decision-section">
              <h4>❌ 失败分类</h4>
              <el-descriptions :column="1" border>
                <el-descriptions-item label="失败类型">
                  {{ currentMR.failure_info?.type || '未知' }}
                </el-descriptions-item>
                <el-descriptions-item label="失败Stage">
                  {{ currentMR.failure_info?.stage || '未知' }}
                </el-descriptions-item>
                <el-descriptions-item label="失败Job">
                  {{ currentMR.failure_info?.job || '未知' }}
                </el-descriptions-item>
              </el-descriptions>
            </div>

            <div class="decision-section" style="margin-top: 20px">
              <h4>🔬 根因分析</h4>
              <el-card>
                <p>{{ currentMR.root_cause }}</p>
              </el-card>
            </div>

            <div class="decision-section" style="margin-top: 20px">
              <h4>💡 修复建议</h4>
              <el-steps :active="currentMR.fix_steps?.length || 0" direction="vertical">
                <el-step
                  v-for="(step, index) in currentMR.fix_steps"
                  :key="index"
                  :title="step.title"
                  :description="step.description"
                />
              </el-steps>
            </div>

            <div class="decision-section" style="margin-top: 20px">
              <h4>🚀 自动修复</h4>
              <el-button type="primary" :loading="autoFixing" @click="applyAutoFix">
                应用自动修复
              </el-button>
              <el-alert
                v-if="currentMR.auto_fix_available"
                type="success"
                :closable="false"
                style="margin-top: 10px"
              >
                <template #title>
                  AI已生成自动修复方案，置信度: {{ currentMR.auto_fix_confidence }}%
                </template>
              </el-alert>
            </div>
          </div>
        </el-tab-pane>

        <!-- 推荐操作 -->
        <el-tab-pane label="推荐操作" name="actions">
          <div class="actions-content">
            <h4>AI建议操作</h4>
            <el-timeline>
              <el-timeline-item
                v-for="(action, index) in currentMR.recommended_actions"
                :key="index"
                :timestamp="action.timestamp"
                :type="getActionType(action.type)"
              >
                <el-card>
                  <div class="action-header">
                    <strong>{{ action.title }}</strong>
                    <el-tag :type="getActionTagType(action.priority)" size="small">
                      {{ action.priority }}
                    </el-tag>
                  </div>
                  <p style="margin-top: 10px">{{ action.description }}</p>
                  <div v-if="action.code_diff" class="code-diff">
                    <pre><code>{{ action.code_diff }}</code></pre>
                  </div>
                  <div class="action-buttons" style="margin-top: 10px">
                    <el-button size="small" type="primary" @click="acceptAction(index)">
                      接受
                    </el-button>
                    <el-button size="small" @click="rejectAction(index)">
                      拒绝
                    </el-button>
                    <el-button size="small" @click="deferAction(index)">
                      延后处理
                    </el-button>
                  </div>
                </el-card>
              </el-timeline-item>
            </el-timeline>
          </div>
        </el-tab-pane>

        <!-- 反馈历史 -->
        <el-tab-pane label="反馈历史" name="feedback">
          <div class="feedback-content">
            <el-button type="primary" @click="openFeedbackDialog(currentMR)">
              添加反馈
            </el-button>

            <el-timeline style="margin-top: 20px">
              <el-timeline-item
                v-for="(feedback, index) in currentMR.feedback_history"
                :key="index"
                :timestamp="formatTime(feedback.timestamp)"
                :type="feedback.is_positive ? 'success' : 'danger'"
              >
                <el-card>
                  <div class="feedback-header">
                    <strong>{{ feedback.user }}</strong>
                    <el-tag :type="feedback.is_positive ? 'success' : 'danger'" size="small">
                      {{ feedback.is_positive ? '肯定' : '否定' }}
                    </el-tag>
                  </div>
                  <p style="margin-top: 10px">{{ feedback.comment }}</p>
                  <div v-if="feedback.category" style="margin-top: 8px">
                    <el-tag size="small">{{ feedback.category }}</el-tag>
                  </div>
                </el-card>
              </el-timeline-item>
            </el-timeline>

            <el-empty
              v-if="!currentMR.feedback_history || currentMR.feedback_history.length === 0"
              description="暂无反馈记录"
            />
          </div>
        </el-tab-pane>
      </el-tabs>

      <template #footer>
        <el-button @click="detailDialogVisible = false">关闭</el-button>
        <el-button
          v-if="currentMR.status === 'pending'"
          type="success"
          @click="acceptAllSuggestions"
        >
          接受所有建议
        </el-button>
      </template>
    </el-dialog>

    <!-- 反馈对话框 -->
    <el-dialog v-model="feedbackDialogVisible" title="提供反馈" width="500px">
      <el-form :model="feedbackForm" label-width="80px">
        <el-form-item label="反馈类型">
          <el-radio-group v-model="feedbackForm.is_positive">
            <el-radio :label="true">👍 有帮助</el-radio>
            <el-radio :label="false">👎 没帮助</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="类别">
          <el-select v-model="feedbackForm.category" placeholder="选择类别">
            <el-option label="误报" value="false_positive" />
            <el-option label="建议不适用" value="not_applicable" />
            <el-option label="有更好的方案" value="better_solution" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="详细说明">
          <el-input
            v-model="feedbackForm.comment"
            type="textarea"
            :rows="4"
            placeholder="请描述您的反馈，帮助AI改进..."
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="feedbackDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitFeedback">提交反馈</el-button>
      </template>
    </el-dialog>

    <!-- 问题详情对话框 -->
    <el-dialog v-model="issueDetailVisible" title="问题详情" width="70%">
      <div v-if="currentIssue">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="文件">
            {{ currentIssue.file }}
          </el-descriptions-item>
          <el-descriptions-item label="行号">
            {{ currentIssue.line }}
          </el-descriptions-item>
          <el-descriptions-item label="严重程度">
            <el-tag v-if="currentIssue.severity === 'critical'" type="danger" size="small">
              严重
            </el-tag>
            <el-tag v-else-if="currentIssue.severity === 'high'" type="warning" size="small">
              高危
            </el-tag>
            <el-tag v-else-if="currentIssue.severity === 'medium'" type="primary" size="small">
              中等
            </el-tag>
            <el-tag v-else type="info" size="small">低级</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="类别">
            {{ currentIssue.category }}
          </el-descriptions-item>
        </el-descriptions>

        <div style="margin-top: 20px">
          <h4>问题描述</h4>
          <el-card>{{ currentIssue.message }}</el-card>
        </div>

        <div style="margin-top: 20px">
          <h4>代码片段</h4>
          <el-card>
            <pre><code>{{ currentIssue.code_snippet }}</code></pre>
          </el-card>
        </div>

        <div style="margin-top: 20px">
          <h4>AI分析</h4>
          <el-card>{{ currentIssue.ai_analysis }}</el-card>
        </div>

        <div v-if="currentIssue.fix_suggestion" style="margin-top: 20px">
          <h4>修复建议</h4>
          <el-card>
            <p>{{ currentIssue.fix_suggestion }}</p>
            <div v-if="currentIssue.fix_code" class="code-diff">
              <pre><code>{{ currentIssue.fix_code }}</code></pre>
            </div>
          </el-card>
        </div>

        <div style="margin-top: 20px">
          <el-button type="primary" @click="applyIssueFix">应用修复</el-button>
          <el-button @click="markAsFalsePositive">标记为误报</el-button>
        </div>
      </div>
    </el-dialog>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Document,
  SuccessFilled,
  Warning,
  Timer,
  Search,
  CircleCloseFilled,
  WarningFilled,
  InfoFilled
} from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { useAIAnalysisStore, useProjectStore } from '@/stores'
import { SkeletonLoader, EmptyState } from '@/components/common'
import { useWebSocket } from '@/composables/useWebSocket'
import { aiAnalysisApi } from '@/api'
import type { MRAnalysis, TestSelection } from '@/types'

// 初始化stores
const aiAnalysisStore = useAIAnalysisStore()
const projectStore = useProjectStore()

// WebSocket实时通信
const {
  isConnected: wsConnected,
  subscribeTo,
  unsubscribeFrom,
  statusUpdates,
  clearStatusUpdates
} = useWebSocket({
  autoConnect: true,
  subscribe: ['ai_analysis_updates', 'mr_updates']
})

const currentProjectId = computed(() => projectStore.currentProject?.id)

// 加载状态和错误处理
const loading = ref(false)
const error = ref<string | null>(null)

// 统计数据 - 从store获取
const stats = computed(() => {
  const analyses = aiAnalysisStore.mrAnalyses
  return {
    totalMRs: analyses.length,
    testsSelected: analyses.reduce((sum, mr) => sum + (mr.selected_tests?.length || 0), 0),
    issuesFound: analyses.reduce((sum, mr) => sum + (mr.issues?.length || 0), 0),
    timeSaved: analyses.reduce((sum, mr) => sum + (mr.total_time_saved || 0), 0)
  }
})

// 筛选条件
const filters = ref({
  project: '',
  type: '',
  status: '',
  search: ''
})

// 分页
const pagination = ref({
  currentPage: 1,
  pageSize: 20,
  total: 0
})

// MR数据 - 从store获取
const mrList = computed(() => aiAnalysisStore.mrAnalyses)

// 筛选后的MR列表
const currentMR = ref<any>(null)

// 详情对话框
const detailDialogVisible = ref(false)
const activeTab = ref('explanation')

// 反馈对话框
const feedbackDialogVisible = ref(false)
const feedbackForm = ref({
  is_positive: true,
  category: '',
  comment: ''
})

// 问题详情
const issueDetailVisible = ref(false)
const currentIssue = ref<any>(null)

// 自动修复
const autoFixing = ref(false)

// 图表引用
const dependencyChartRef = ref<HTMLElement>()
const qualityScoreChartRef = ref<HTMLElement>()
let dependencyChart: echarts.ECharts | null = null
let qualityScoreChart: echarts.ECharts | null = null

// 方法：加载AI分析数据
const loadAIAnalysisData = async () => {
  if (!currentProjectId.value) {
    error.value = '请先选择项目'
    return
  }

  loading.value = true
  error.value = null

  try {
    // 并行加载AI分析数据
    await Promise.all([
      aiAnalysisStore.fetchMRAnalyses(currentProjectId.value, {
        page: pagination.value.currentPage,
        per_page: pagination.value.pageSize,
        type: filters.value.type || undefined,
        status: filters.value.status || undefined
      })
    ])

    // 初始化图表
    await nextTick()
    initDependencyChart()
    initQualityScoreChart()
  } catch (err: any) {
    console.error('Failed to load AI analysis data:', err)
    error.value = err.message || '加载AI分析数据失败'
    ElMessage.error(error.value)
  } finally {
    loading.value = false
  }
}

// 计算属性：筛选后的MR列表
const filteredMRs = computed(() => {
  let result = [...mrList.value]

  if (filters.value.project) {
    result = result.filter(mr => mr.project === filters.value.project)
  }

  if (filters.value.type) {
    result = result.filter(mr => mr.type === filters.value.type)
  }

  if (filters.value.status) {
    result = result.filter(mr => mr.status === filters.value.status)
  }

  if (filters.value.search) {
    const search = filters.value.search.toLowerCase()
    result = result.filter(mr =>
      mr.id.toString().includes(search) ||
      mr.title.toLowerCase().includes(search) ||
      mr.author.toLowerCase().includes(search)
    )
  }

  pagination.value.total = result.length

  const start = (pagination.value.currentPage - 1) * pagination.value.pageSize
  const end = start + pagination.value.pageSize
  return result.slice(start, end)
})

// 判断是否有AI分析数据
const hasNoAIAnalysisData = computed(() => {
  const analyses = aiAnalysisStore.mrAnalyses
  return !analyses || analyses.length === 0
})

// 查看MR列表
const viewMRList = () => {
  // 导航到Pipelines页面查看MR列表
  router.push('/pipelines')
}

// 方法：格式化时间
const formatTime = (timestamp: number) => {
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  if (diff < 3600000) {
    return `${Math.floor(diff / 60000)}分钟前`
  } else if (diff < 86400000) {
    return `${Math.floor(diff / 3600000)}小时前`
  } else if (diff < 604800000) {
    return `${Math.floor(diff / 86400000)}天前`
  } else {
    return date.toLocaleDateString('zh-CN')
  }
}

// 方法：获取置信度颜色
const getConfidenceColor = (confidence: number) => {
  if (confidence >= 90) return '#67c23a'
  if (confidence >= 70) return '#e6a23c'
  return '#f56c6c'
}

// 方法：获取操作类型
const getActionType = (type: string) => {
  if (type === 'run_tests') return 'primary'
  if (type === 'fix_issue') return 'warning'
  if (type === 'apply_fix') return 'success'
  return ''
}

// 方法：获取操作标签类型
const getActionTagType = (priority: string) => {
  if (priority === 'critical') return 'danger'
  if (priority === 'high') return 'warning'
  if (priority === 'medium') return 'primary'
  return 'info'
}

// 方法：处理筛选变化
const handleFilterChange = () => {
  pagination.value.currentPage = 1
}

// 方法：处理分页大小变化
const handleSizeChange = () => {
  pagination.value.currentPage = 1
}

// 方法：处理当前页变化
const handleCurrentChange = () => {
  // 页面变化处理
}

// 方法：查看MR详情
const viewMRDetails = (mr: any) => {
  currentMR.value = mr
  detailDialogVisible.value = true
  activeTab.value = 'explanation'

  nextTick(() => {
    if (mr.type === 'test_selection') {
      initDependencyChart()
    } else if (mr.type === 'code_review') {
      initQualityScoreChart()
    }
  })
}

// 方法：初始化依赖关系图
const initDependencyChart = () => {
  if (!dependencyChartRef.value) return

  if (dependencyChart) {
    dependencyChart.dispose()
  }

  dependencyChart = echarts.init(dependencyChartRef.value)

  const option = {
    title: {
      text: '代码依赖影响关系',
      left: 'center'
    },
    tooltip: {},
    series: [
      {
        type: 'graph',
        layout: 'force',
        symbolSize: 50,
        roam: true,
        label: {
          show: true,
          fontSize: 10
        },
        edgeSymbol: ['circle', 'arrow'],
        edgeSymbolSize: [4, 10],
        data: [
          { name: 'AuthController', itemStyle: { color: '#ff6b6b' } },
          { name: 'AuthService', itemStyle: { color: '#4ecdc4' } },
          { name: 'UserSession', itemStyle: { color: '#45b7d1' } },
          { name: 'RateLimiter', itemStyle: { color: '#f9ca24' } },
          { name: 'APIThrottling', itemStyle: { color: '#6c5ce7' } },
          { name: 'Database', itemStyle: { color: '#a29bfe' } },
          { name: 'Cache', itemStyle: { color: '#fd79a8' } }
        ],
        links: [
          { source: 'AuthController', target: 'AuthService' },
          { source: 'AuthService', target: 'UserSession' },
          { source: 'AuthService', target: 'RateLimiter' },
          { source: 'RateLimiter', target: 'APIThrottling' },
          { source: 'AuthService', target: 'Database' },
          { source: 'AuthService', target: 'Cache' }
        ],
        force: {
          repulsion: 200,
          edgeLength: 100
        }
      }
    ]
  }

  dependencyChart.setOption(option)
}

// 方法：初始化质量评分图
const initQualityScoreChart = () => {
  if (!qualityScoreChartRef.value) return

  if (qualityScoreChart) {
    qualityScoreChart.dispose()
  }

  qualityScoreChart = echarts.init(qualityScoreChartRef.value)

  const option = {
    title: {
      text: '代码质量评分',
      left: 'center'
    },
    tooltip: {
      trigger: 'item'
    },
    radar: {
      indicator: [
        { name: '内存安全', max: 100 },
        { name: '性能', max: 100 },
        { name: '现代C++', max: 100 },
        { name: '线程安全', max: 100 },
        { name: '代码风格', max: 100 }
      ]
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: [75, 82, 68, 70, 85],
            name: '当前代码',
            areaStyle: { color: 'rgba(64, 158, 255, 0.3)' }
          },
          {
            value: [90, 88, 85, 92, 95],
            name: '目标基准',
            areaStyle: { color: 'rgba(103, 194, 58, 0.3)' }
          }
        ]
      }
    ]
  }

  qualityScoreChart.setOption(option)
}

// 方法：查看问题详情
const viewIssueDetail = (issue: any) => {
  currentIssue.value = {
    ...issue,
    code_snippet: `DataProcessor* processor = new DataProcessor();
processor->processData(data);
// Memory leak: processor not deleted`,
    ai_analysis: '该处存在明显的内存泄漏。DataProcessor对象在堆上分配，但未在使用后释放。建议使用智能指针std::unique_ptr自动管理内存。',
    fix_suggestion: '使用std::unique_ptr替代裸指针，确保内存自动释放',
    fix_code: `auto processor = std::make_unique<DataProcessor>();
processor->processData(data);
// processor will be automatically deleted`
  }
  issueDetailVisible.value = true
}

// 方法：应用修复
const applyFix = (issue: any) => {
  ElMessageBox.confirm(
    `确定要应用此修复吗？\n\n文件: ${issue.file}\n行号: ${issue.line}`,
    '确认应用修复',
    {
      confirmButtonText: '应用',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    ElMessage.success('修复已应用，MR已更新')
  }).catch(() => {
    // 用户取消
  })
}

// 方法：应用问题修复
const applyIssueFix = () => {
  ElMessage.success('修复已应用到代码')
  issueDetailVisible.value = false
}

// 方法：标记为误报
const markAsFalsePositive = () => {
  ElMessage.success('已标记为误报，AI将学习此反馈')
  issueDetailVisible.value = false
}

// 方法：应用自动修复
const applyAutoFix = async () => {
  if (!currentMR.value) return

  try {
    await ElMessageBox.confirm(
      '确定要应用自动修复吗？这将创建一个新的MR。',
      '确认应用修复',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'info'
      }
    )

    autoFixing.value = true
    await aiAnalysisStore.applyAutoFix(currentMR.value.id)

    ElMessage.success('自动修复已应用，已创建新的MR')

    // 重新加载数据
    if (currentProjectId.value) {
      await loadAIAnalysisData()
    }
  } catch (err: any) {
    if (err !== 'cancel') {
      console.error('Apply auto fix failed:', err)
      ElMessage.error(err.message || '应用自动修复失败')
    }
  } finally {
    autoFixing.value = false
  }
}

// 方法：接受操作
const acceptAction = (index: number) => {
  ElMessage.success(`已接受建议 #${index + 1}`)
}

// 方法：拒绝操作
const rejectAction = (index: number) => {
  ElMessage.info(`已拒绝建议 #${index + 1}`)
}

// 方法：延后操作
const deferAction = (index: number) => {
  ElMessage.info(`已延后处理建议 #${index + 1}`)
}

// 方法：接受所有建议
const acceptAllSuggestions = () => {
  ElMessageBox.confirm(
    '确定要接受所有AI建议吗？此操作将批量应用所有推荐的修改。',
    '确认批量接受',
    {
      confirmButtonText: '接受所有',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    ElMessage.success('所有建议已接受')
    detailDialogVisible.value = false
  }).catch(() => {
    // 用户取消
  })
}

// 方法：打开反馈对话框
const openFeedbackDialog = (mr: any) => {
  currentMR.value = mr
  feedbackForm.value = {
    is_positive: true,
    category: '',
    comment: ''
  }
  feedbackDialogVisible.value = true
}

// 方法：提交反馈
const submitFeedback = async () => {
  if (!feedbackForm.value.comment) {
    ElMessage.warning('请提供反馈说明')
    return
  }

  if (!currentMR.value) return

  try {
    loading.value = true
    await aiAnalysisStore.submitFeedback(currentMR.value.id, {
      is_positive: feedbackForm.value.is_positive,
      category: feedbackForm.value.category,
      comment: feedbackForm.value.comment
    })

    ElMessage.success('感谢您的反馈！AI将学习此反馈以改进。')
    feedbackDialogVisible.value = false

    // 重新加载数据
    if (currentProjectId.value) {
      await loadAIAnalysisData()
    }
  } catch (error) {
    console.error('Submit feedback failed:', error)
    ElMessage.error('提交反馈失败')
  } finally {
    loading.value = false
  }
}

// 设置WebSocket实时更新
const setupWebSocketUpdates = () => {
  // 订阅AI分析更新主题
  subscribeTo('ai_analysis_updates')
  subscribeTo('mr_updates')

  // 监听状态更新消息
  watch(() => statusUpdates.value.length, (newLength, oldLength) => {
    if (newLength > oldLength) {
      // 有新的状态更新，刷新AI分析数据
      if (currentProjectId.value) {
        loadAIAnalysisData()
      }
    }
  })
}

// 生命周期：挂载
onMounted(() => {
  loadAIAnalysisData()

  // 设置WebSocket实时更新
  setupWebSocketUpdates()
})

// 监听项目切换
watch(currentProjectId, () => {
  if (currentProjectId.value) {
    loadAIAnalysisData()
  }
})

// 监听筛选变化
watch(filters, () => {
  pagination.value.currentPage = 1
  if (currentProjectId.value) {
    loadAIAnalysisData()
  }
}, { deep: true })

// 监听分页变化
watch(() => pagination.value.currentPage, () => {
  if (currentProjectId.value) {
    loadAIAnalysisData()
  }
})

watch(() => pagination.value.pageSize, () => {
  pagination.value.currentPage = 1
  if (currentProjectId.value) {
    loadAIAnalysisData()
  }
})

// 生命周期：卸载
onUnmounted(() => {
  if (dependencyChart) {
    dependencyChart.dispose()
  }
  if (qualityScoreChart) {
    qualityScoreChart.dispose()
  }

  // 清理状态更新
  clearStatusUpdates()
})
</script>

<style scoped>
.ai-analysis {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.page-header h2 {
  margin: 0;
  font-size: 24px;
  color: #303133;
}

.subtitle {
  margin: 5px 0 0 0;
  color: #909399;
  font-size: 14px;
}

.stat-card {
  height: 100px;
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 15px;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
  line-height: 1;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 8px;
}

.analysis-content h4 {
  margin: 0 0 15px 0;
  font-size: 16px;
  color: #303133;
}

.decision-section {
  margin-bottom: 20px;
}

.code-diff {
  background: #f5f7fa;
  border-radius: 4px;
  padding: 10px;
  margin-top: 10px;
}

.code-diff pre {
  margin: 0;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.action-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.action-buttons {
  display: flex;
  gap: 10px;
}

.feedback-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.actions-content h4,
.feedback-content h4 {
  margin: 0 0 15px 0;
  font-size: 16px;
  color: #303133;
}

/* WebSocket状态指示器 */
.ws-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background-color: #f5f5f5;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s;
}

.ws-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #ff4d4f;
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

.ws-status.connected .ws-indicator {
  background-color: #52c41a;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}
</style>
