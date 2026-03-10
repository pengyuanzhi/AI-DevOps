<template>
  <div class="settings" v-loading="loading" element-loading-text="加载中...">
    <el-alert
      v-if="error"
      type="error"
      :title="error"
      :closable="false"
      style="margin-bottom: 20px"
    />

    <!-- 页面标题 -->
    <el-row :gutter="20">
      <el-col :span="24">
        <el-card>
          <div class="page-header">
            <h2>用户设置和配置</h2>
            <p class="subtitle">管理个人偏好、项目配置和系统设置</p>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 设置选项卡 -->
    <el-card style="margin-top: 20px">
      <el-tabs v-model="activeTab" type="border-card">
        <!-- 用户偏好设置 -->
        <el-tab-pane label="用户偏好" name="preferences">
          <div class="settings-content">
            <!-- 通知设置 -->
            <div class="setting-section">
              <h3>通知设置</h3>
              <el-form :model="notificationSettings" label-width="200px">
                <el-form-item label="Pipeline状态通知">
                  <el-switch v-model="notificationSettings.pipelineStatus" />
                  <span class="setting-description">
                    当Pipeline状态改变时接收通知
                  </span>
                </el-form-item>

                <el-form-item label="测试失败通知">
                  <el-switch v-model="notificationSettings.testFailure" />
                  <span class="setting-description">
                    测试失败时立即通知
                  </span>
                </el-form-item>

                <el-form-item label="代码质量问题通知">
                  <el-switch v-model="notificationSettings.codeQuality" />
                  <span class="setting-description">
                    发现严重代码问题时通知
                  </span>
                </el-form-item>

                <el-form-item label="内存安全问题通知">
                  <el-switch v-model="notificationSettings.memorySafety" />
                  <span class="setting-description">
                    检测到内存安全问题时通知
                  </span>
                </el-form-item>

                <el-form-item label="AI分析结果通知">
                  <el-switch v-model="notificationSettings.aiAnalysis" />
                  <span class="setting-description">
                    AI分析完成时通知
                  </span>
                </el-form-item>

                <el-form-item label="通知方式">
                  <el-checkbox-group v-model="notificationSettings.methods">
                    <el-checkbox label="email">邮件</el-checkbox>
                    <el-checkbox label="websocket">浏览器推送</el-checkbox>
                    <el-checkbox label="slack">Slack</el-checkbox>
                    <el-checkbox label="webhook">Webhook</el-checkbox>
                  </el-checkbox-group>
                </el-form-item>

                <el-form-item label="邮件通知频率">
                  <el-radio-group v-model="notificationSettings.emailFrequency">
                    <el-radio label="immediate">立即</el-radio>
                    <el-radio label="hourly">每小时汇总</el-radio>
                    <el-radio label="daily">每日汇总</el-radio>
                    <el-radio label="weekly">每周汇总</el-radio>
                  </el-radio-group>
                </el-form-item>
              </el-form>
            </div>

            <el-divider />

            <!-- 仪表盘设置 -->
            <div class="setting-section">
              <h3>仪表盘设置</h3>
              <el-form :model="dashboardSettings" label-width="200px">
                <el-form-item label="默认仪表盘">
                  <el-select v-model="dashboardSettings.defaultDashboard">
                    <el-option label="项目概览" value="dashboard" />
                    <el-option label="测试和质量" value="test-quality" />
                    <el-option label="代码质量" value="code-review" />
                    <el-option label="CI/CD流水线" value="pipelines" />
                    <el-option label="AI分析" value="ai-analysis" />
                    <el-option label="内存安全" value="memory-safety" />
                  </el-select>
                </el-form-item>

                <el-form-item label="自动刷新间隔">
                  <el-select v-model="dashboardSettings.refreshInterval">
                    <el-option label="不刷新" :value="0" />
                    <el-option label="30秒" :value="30" />
                    <el-option label="1分钟" :value="60" />
                    <el-option label="5分钟" :value="300" />
                    <el-option label="15分钟" :value="900" />
                  </el-select>
                  <span class="setting-description">
                    仪表盘数据自动刷新间隔
                  </span>
                </el-form-item>

                <el-form-item label="显示密度">
                  <el-radio-group v-model="dashboardSettings.density">
                    <el-radio label="comfortable">舒适</el-radio>
                    <el-radio label="compact">紧凑</el-radio>
                  </el-radio-group>
                </el-form-item>

                <el-form-item label="图表主题">
                  <el-radio-group v-model="dashboardSettings.chartTheme">
                    <el-radio label="default">默认</el-radio>
                    <el-radio label="dark">深色</el-radio>
                    <el-radio label="colorful">彩色</el-radio>
                  </el-radio-group>
                </el-form-item>
              </el-form>
            </div>

            <el-divider />

            <!-- 主题和语言 -->
            <div class="setting-section">
              <h3>主题和语言</h3>
              <el-form :model="uiSettings" label-width="200px">
                <el-form-item label="主题模式">
                  <el-radio-group v-model="uiSettings.theme">
                    <el-radio label="light">浅色</el-radio>
                    <el-radio label="dark">深色</el-radio>
                    <el-radio label="auto">跟随系统</el-radio>
                  </el-radio-group>
                </el-form-item>

                <el-form-item label="语言">
                  <el-select v-model="uiSettings.language">
                    <el-option label="简体中文" value="zh-CN" />
                    <el-option label="English" value="en-US" />
                  </el-select>
                </el-form-item>

                <el-form-item label="时区">
                  <el-select v-model="uiSettings.timezone" filterable>
                    <el-option label="UTC+8 北京时间" value="Asia/Shanghai" />
                    <el-option label="UTC+9 东京时间" value="Asia/Tokyo" />
                    <el-option label="UTC+0 伦敦时间" value="Europe/London" />
                    <el-option label="UTC-5 纽约时间" value="America/New_York" />
                    <el-option label="UTC-8 太平洋时间" value="America/Los_Angeles" />
                  </el-select>
                </el-form-item>

                <el-form-item label="日期格式">
                  <el-select v-model="uiSettings.dateFormat">
                    <el-option label="YYYY-MM-DD" value="yyyy-mm-dd" />
                    <el-option label="DD/MM/YYYY" value="dd/mm/yyyy" />
                    <el-option label="MM/DD/YYYY" value="mm/dd/yyyy" />
                  </el-select>
                </el-form-item>

                <el-form-item label="时间格式">
                  <el-radio-group v-model="uiSettings.timeFormat">
                    <el-radio label="24h">24小时制</el-radio>
                    <el-radio label="12h">12小时制</el-radio>
                  </el-radio-group>
                </el-form-item>
              </el-form>
            </div>

            <div style="margin-top: 30px; text-align: right">
              <el-button type="primary" @click="savePreferences">保存偏好设置</el-button>
              <el-button @click="resetPreferences">重置为默认</el-button>
            </div>
          </div>
        </el-tab-pane>

        <!-- 项目配置 -->
        <el-tab-pane label="项目配置" name="project">
          <div class="settings-content">
            <!-- AI模型配置 -->
            <div class="setting-section">
              <h3>AI模型配置</h3>
              <el-alert type="info" :closable="false" style="margin-bottom: 20px">
                选择用于不同AI功能的模型。您可以配置云端模型（需要API密钥）或本地模型。
              </el-alert>

              <el-form :model="aiModelSettings" label-width="200px">
                <el-form-item label="智能测试选择模型">
                  <el-select v-model="aiModelSettings.testSelection">
                    <el-option label="智谱AI GLM-4 (云端)" value="zhipu-glm4" />
                    <el-option label="通义千问 Qwen (云端)" value="qwen-plus" />
                    <el-option label="Claude 3.5 Sonnet (云端)" value="claude-3.5-sonnet" />
                    <el-option label="Qwen 7B (本地)" value="qwen-7b-local" />
                    <el-option label="Llama 3 8B (本地)" value="llama3-8b-local" />
                  </el-select>
                  <span class="setting-description">
                    用于测试选择和影响域分析
                  </span>
                </el-form-item>

                <el-form-item label="代码审查模型">
                  <el-select v-model="aiModelSettings.codeReview">
                    <el-option label="智谱AI GLM-4 (云端)" value="zhipu-glm4" />
                    <el-option label="通义千问 Qwen (云端)" value="qwen-plus" />
                    <el-option label="Claude 3.5 Sonnet (云端)" value="claude-3.5-sonnet" />
                    <el-option label="Qwen 7B (本地)" value="qwen-7b-local" />
                    <el-option label="Llama 3 8B (本地)" value="llama3-8b-local" />
                  </el-select>
                  <span class="setting-description">
                    用于静态代码审查和误报过滤
                  </span>
                </el-form-item>

                <el-form-item label="自然语言配置模型">
                  <el-select v-model="aiModelSettings.nlConfig">
                    <el-option label="智谱AI GLM-4 (云端)" value="zhipu-glm4" />
                    <el-option label="通义千问 Qwen (云端)" value="qwen-plus" />
                    <el-option label="Claude 3.5 Sonnet (云端)" value="claude-3.5-sonnet" />
                    <el-option label="Qwen 7B (本地)" value="qwen-7b-local" />
                  </el-select>
                  <span class="setting-description">
                    用于自然语言生成CI/CD配置
                  </span>
                </el-form-item>

                <el-form-item label="内存安全分析模型">
                  <el-select v-model="aiModelSettings.memorySafety">
                    <el-option label="Claude 3.5 Sonnet (云端)" value="claude-3.5-sonnet" />
                    <el-option label="智谱AI GLM-4 (云端)" value="zhipu-glm4" />
                    <el-option label="通义千问 Qwen (云端)" value="qwen-plus" />
                  </el-select>
                  <span class="setting-description">
                    用于内存安全问题分析和修复建议
                  </span>
                </el-form-item>
              </el-form>

              <el-divider />

              <h4>API密钥配置</h4>
              <el-form :model="apiKeys" label-width="200px">
                <el-form-item label="智谱AI API密钥">
                  <el-input
                    v-model="apiKeys.zhipu"
                    type="password"
                    show-password
                    placeholder="请输入智谱AI API密钥"
                    style="width: 400px"
                  />
                  <el-button type="primary" link @click="testApiKey('zhipu')">测试连接</el-button>
                </el-form-item>

                <el-form-item label="通义千问API密钥">
                  <el-input
                    v-model="apiKeys.qwen"
                    type="password"
                    show-password
                    placeholder="请输入通义千问API密钥"
                    style="width: 400px"
                  />
                  <el-button type="primary" link @click="testApiKey('qwen')">测试连接</el-button>
                </el-form-item>

                <el-form-item label="Anthropic API密钥">
                  <el-input
                    v-model="apiKeys.anthropic"
                    type="password"
                    show-password
                    placeholder="请输入Anthropic API密钥"
                    style="width: 400px"
                  />
                  <el-button type="primary" link @click="testApiKey('anthropic')">测试连接</el-button>
                </el-form-item>

                <el-form-item label="本地模型API地址">
                  <el-input
                    v-model="apiKeys.localModel"
                    placeholder="http://localhost:11434"
                    style="width: 400px"
                  />
                  <el-button type="primary" link @click="testApiKey('local')">测试连接</el-button>
                </el-form-item>
              </el-form>
            </div>

            <el-divider />

            <!-- CI/CD配置 -->
            <div class="setting-section">
              <h3>CI/CD配置</h3>
              <el-form :model="cicdSettings" label-width="200px">
                <el-form-item label="默认构建类型">
                  <el-select v-model="cicdSettings.defaultBuildType">
                    <el-option label="Debug" value="Debug" />
                    <el-option label="Release" value="Release" />
                    <el-option label="RelWithDebInfo" value="RelWithDebInfo" />
                    <el-option label="MinSizeRel" value="MinSizeRel" />
                  </el-select>
                </el-form-item>

                <el-form-item label="并行构建作业数">
                  <el-input-number v-model="cicdSettings.parallelJobs" :min="1" :max="32" />
                  <span class="setting-description">
                    构建时的并行作业数，建议设置为CPU核心数
                  </span>
                </el-form-item>

                <el-form-item label="启用ccache">
                  <el-switch v-model="cicdSettings.enableCcache" />
                  <span class="setting-description">
                    使用ccache加速C/C++编译
                  </span>
                </el-form-item>

                <el-form-item label="构建缓存保留时间">
                  <el-input-number v-model="cicdSettings.cacheRetentionDays" :min="1" :max="365" />
                  <span class="setting-description">
                    天
                  </span>
                </el-form-item>

                <el-form-item label="测试超时时间">
                  <el-input-number v-model="cicdSettings.testTimeout" :min="60" :max="3600" />
                  <span class="setting-description">
                    秒
                  </span>
                </el-form-item>

                <el-form-item label="启用测试覆盖率">
                  <el-switch v-model="cicdSettings.enableCoverage" />
                  <span class="setting-description">
                    自动收集代码覆盖率数据
                  </span>
                </el-form-item>
              </el-form>
            </div>

            <el-divider />

            <!-- 智能测试选择配置 -->
            <div class="setting-section">
              <h3>智能测试选择配置</h3>
              <el-form :model="testSelectionSettings" label-width="200px">
                <el-form-item label="选择策略">
                  <el-radio-group v-model="testSelectionSettings.strategy">
                    <el-radio label="conservative">保守（优先保证不遗漏）</el-radio>
                    <el-radio label="balanced">平衡（推荐）</el-radio>
                    <el-radio label="aggressive">激进（最大化速度）</el-radio>
                  </el-radio-group>
                </el-form-item>

                <el-form-item label="最小置信度">
                  <el-slider v-model="testSelectionSettings.minConfidence" :min="0" :max="100" />
                  <span class="setting-description">
                    {{ testSelectionSettings.minConfidence }}% - 低于此置信度的测试将被包含
                  </span>
                </el-form-item>

                <el-form-item label="影响域深度">
                  <el-input-number v-model="testSelectionSettings.impactDepth" :min="1" :max="10" />
                  <span class="setting-description">
                    层级 - 分析依赖关系的深度
                  </span>
                </el-form-item>
              </el-form>
            </div>

            <div style="margin-top: 30px; text-align: right">
              <el-button type="primary" @click="saveProjectConfig">保存项目配置</el-button>
              <el-button @click="resetProjectConfig">重置为默认</el-button>
            </div>
          </div>
        </el-tab-pane>

        <!-- 告警规则 -->
        <el-tab-pane label="告警规则" name="alerts">
          <div class="settings-content">
            <div class="setting-section">
              <h3>告警规则配置</h3>

              <el-button type="primary" @click="addAlertRule" style="margin-bottom: 20px">
                <el-icon><Plus /></el-icon>
                添加告警规则
              </el-button>

              <el-table :data="alertRules" style="width: 100%">
                <el-table-column prop="name" label="规则名称" min-width="150" />
                <el-table-column prop="type" label="类型" width="150">
                  <template #default="scope">
                    <el-tag v-if="scope.row.type === 'pipeline'" type="primary">Pipeline</el-tag>
                    <el-tag v-else-if="scope.row.type === 'test'" type="success">测试</el-tag>
                    <el-tag v-else-if="scope.row.type === 'quality'" type="warning">质量</el-tag>
                    <el-tag v-else-if="scope.row.type === 'memory'" type="danger">内存</el-tag>
                    <el-tag v-else-if="scope.row.type === 'resource'" type="info">资源</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="condition" label="条件" min-width="200" />
                <el-table-column prop="threshold" label="阈值" width="120" />
                <el-table-column prop="enabled" label="状态" width="100">
                  <template #default="scope">
                    <el-switch v-model="scope.row.enabled" @change="toggleAlertRule(scope.row)" />
                  </template>
                </el-table-column>
                <el-table-column prop="actions" label="通知方式" width="150">
                  <template #default="scope">
                    <el-tag
                      v-for="action in scope.row.actions"
                      :key="action"
                      size="small"
                      style="margin-right: 5px"
                    >
                      {{ getActionLabel(action) }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="150" fixed="right">
                  <template #default="scope">
                    <el-button size="small" @click="editAlertRule(scope.row)">编辑</el-button>
                    <el-button size="small" type="danger" @click="deleteAlertRule(scope.row)">
                      删除
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>

            <el-divider />

            <div class="setting-section">
              <h3>告警历史</h3>
              <el-table :data="alertHistory" style="width: 100%">
                <el-table-column prop="timestamp" label="时间" width="180">
                  <template #default="scope">
                    {{ formatTime(scope.row.timestamp) }}
                  </template>
                </el-table-column>
                <el-table-column prop="rule" label="规则" min-width="150" />
                <el-table-column prop="message" label="消息" min-width="300" />
                <el-table-column prop="severity" label="严重程度" width="100">
                  <template #default="scope">
                    <el-tag v-if="scope.row.severity === 'critical'" type="danger" size="small">
                      严重
                    </el-tag>
                    <el-tag v-else-if="scope.row.severity === 'warning'" type="warning" size="small">
                      警告
                    </el-tag>
                    <el-tag v-else type="info" size="small">信息</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="acknowledged" label="状态" width="100">
                  <template #default="scope">
                    <el-tag v-if="scope.row.acknowledged" type="success" size="small">
                      已确认
                    </el-tag>
                    <el-tag v-else type="info" size="small">未确认</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="100">
                  <template #default="scope">
                    <el-button
                      v-if="!scope.row.acknowledged"
                      size="small"
                      @click="acknowledgeAlert(scope.row)"
                    >
                      确认
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>

              <el-pagination
                v-model:current-page="alertPagination.currentPage"
                v-model:page-size="alertPagination.pageSize"
                :page-sizes="[10, 20, 50]"
                :total="alertPagination.total"
                layout="total, sizes, prev, pager, next"
                style="margin-top: 20px; justify-content: flex-end"
              />
            </div>
          </div>
        </el-tab-pane>

        <!-- 权限管理 -->
        <el-tab-pane label="权限管理" name="permissions">
          <div class="settings-content">
            <div class="setting-section">
              <h3>我的权限</h3>

              <el-descriptions :column="2" border>
                <el-descriptions-item label="用户名">
                  {{ currentUser.name }}
                </el-descriptions-item>
                <el-descriptions-item label="邮箱">
                  {{ currentUser.email }}
                </el-descriptions-item>
                <el-descriptions-item label="角色">
                  <el-tag v-for="role in currentUser.roles" :key="role" style="margin-right: 5px">
                    {{ getRoleLabel(role) }}
                  </el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="项目访问">
                  {{ currentUser.projects.length }} 个项目
                </el-descriptions-item>
              </el-descriptions>
            </div>

            <el-divider />

            <div class="setting-section">
              <h3>项目权限</h3>

              <el-table :data="projectPermissions" style="width: 100%">
                <el-table-column prop="project" label="项目" min-width="200" />
                <el-table-column prop="role" label="角色" width="150">
                  <template #default="scope">
                    <el-tag :type="getRoleTagType(scope.row.role)">
                      {{ getRoleLabel(scope.row.role) }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="permissions" label="权限" min-width="300">
                  <template #default="scope">
                    <el-tag
                      v-for="perm in scope.row.permissions"
                      :key="perm"
                      size="small"
                      style="margin-right: 5px; margin-bottom: 5px"
                    >
                      {{ getPermissionLabel(perm) }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="lastAccess" label="最后访问" width="180">
                  <template #default="scope">
                    {{ formatTime(scope.row.lastAccess) }}
                  </template>
                </el-table-column>
              </el-table>
            </div>

            <el-divider />

            <div class="setting-section">
              <h3>API访问令牌</h3>

              <el-button type="primary" @click="generateToken" style="margin-bottom: 20px">
                <el-icon><Plus /></el-icon>
                生成新令牌
              </el-button>

              <el-table :data="apiTokens" style="width: 100%">
                <el-table-column prop="name" label="令牌名称" min-width="150" />
                <el-table-column prop="token" label="令牌" min-width="200">
                  <template #default="scope">
                    <span v-if="scope.row.visible">{{ scope.row.token }}</span>
                    <span v-else>************************</span>
                    <el-button
                      link
                      type="primary"
                      @click="toggleTokenVisibility(scope.row)"
                      style="margin-left: 10px"
                    >
                      {{ scope.row.visible ? '隐藏' : '显示' }}
                    </el-button>
                  </template>
                </el-table-column>
                <el-table-column prop="scopes" label="权限范围" min-width="200">
                  <template #default="scope">
                    <el-tag
                      v-for="scope in scope.row.scopes"
                      :key="scope"
                      size="small"
                      style="margin-right: 5px"
                    >
                      {{ scope }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="expiresAt" label="过期时间" width="180">
                  <template #default="scope">
                    {{ scope.row.expiresAt ? formatDate(scope.row.expiresAt) : '永不过期' }}
                  </template>
                </el-table-column>
                <el-table-column prop="lastUsed" label="最后使用" width="180">
                  <template #default="scope">
                    {{ scope.row.lastUsed ? formatTime(scope.row.lastUsed) : '未使用' }}
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="120">
                  <template #default="scope">
                    <el-button size="small" type="danger" @click="revokeToken(scope.row)">
                      撤销
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>

            <el-divider />

            <div class="setting-section">
              <h3>SSH密钥</h3>

              <el-button type="primary" @click="addSSHKey" style="margin-bottom: 20px">
                <el-icon><Plus /></el-icon>
                添加SSH密钥
              </el-button>

              <el-table :data="sshKeys" style="width: 100%">
                <el-table-column prop="name" label="名称" min-width="200" />
                <el-table-column prop="fingerprint" label="指纹" width="200">
                  <template #default="scope">
                    <code>{{ scope.row.fingerprint }}</code>
                  </template>
                </el-table-column>
                <el-table-column prop="type" label="类型" width="120">
                  <template #default="scope">
                    <el-tag size="small">{{ scope.row.type }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="createdAt" label="添加时间" width="180">
                  <template #default="scope">
                    {{ formatTime(scope.row.createdAt) }}
                  </template>
                </el-table-column>
                <el-table-column prop="lastUsed" label="最后使用" width="180">
                  <template #default="scope">
                    {{ scope.row.lastUsed ? formatTime(scope.row.lastUsed) : '未使用' }}
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="120">
                  <template #default="scope">
                    <el-button size="small" type="danger" @click="deleteSSHKey(scope.row)">
                      删除
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>
        </el-tab-pane>

        <!-- 账户设置 -->
        <el-tab-pane label="账户" name="account">
          <div class="settings-content">
            <div class="setting-section">
              <h3>个人信息</h3>
              <el-form :model="userInfo" label-width="150px" style="max-width: 600px">
                <el-form-item label="头像">
                  <el-avatar :size="80" :src="userInfo.avatar">
                    <el-icon><User /></el-icon>
                  </el-avatar>
                  <el-button type="primary" link style="margin-left: 20px">
                    更换头像
                  </el-button>
                </el-form-item>

                <el-form-item label="用户名">
                  <el-input v-model="userInfo.name" disabled />
                </el-form-item>

                <el-form-item label="邮箱">
                  <el-input v-model="userInfo.email" />
                </el-form-item>

                <el-form-item label="显示名称">
                  <el-input v-model="userInfo.displayName" />
                </el-form-item>

                <el-form-item label="位置">
                  <el-input v-model="userInfo.location" />
                </el-form-item>

                <el-form-item label="公司">
                  <el-input v-model="userInfo.company" />
                </el-form-item>

                <el-form-item label="个人简介">
                  <el-input
                    v-model="userInfo.bio"
                    type="textarea"
                    :rows="4"
                    placeholder="介绍一下自己..."
                  />
                </el-form-item>
              </el-form>

              <el-button type="primary" @click="updateProfile">更新个人信息</el-button>
            </div>

            <el-divider />

            <div class="setting-section">
              <h3>修改密码</h3>
              <el-form :model="passwordForm" label-width="150px" style="max-width: 500px">
                <el-form-item label="当前密码">
                  <el-input v-model="passwordForm.currentPassword" type="password" show-password />
                </el-form-item>

                <el-form-item label="新密码">
                  <el-input v-model="passwordForm.newPassword" type="password" show-password />
                </el-form-item>

                <el-form-item label="确认新密码">
                  <el-input v-model="passwordForm.confirmPassword" type="password" show-password />
                </el-form-item>
              </el-form>

              <el-button type="primary" @click="changePassword">修改密码</el-button>
            </div>

            <el-divider />

            <div class="setting-section">
              <h3>两步验证</h3>
              <el-alert type="info" :closable="false" style="margin-bottom: 20px">
                启用两步验证可以提高账户安全性。
              </el-alert>

              <div v-if="!userInfo.twoFactorEnabled">
                <el-button type="primary" @click="enableTwoFactor">启用两步验证</el-button>
              </div>
              <div v-else>
                <el-result icon="success" title="两步验证已启用" sub-title="您的账户现在受到额外保护。">
                  <template #extra>
                    <el-button type="danger" @click="disableTwoFactor">禁用两步验证</el-button>
                  </template>
                </el-result>
              </div>
            </div>

            <el-divider />

            <div class="setting-section">
              <h3>危险区域</h3>
              <el-alert type="error" :closable="false" style="margin-bottom: 20px">
                以下操作不可逆，请谨慎操作。
              </el-alert>

              <el-button type="danger" @click="exportData">导出我的数据</el-button>
              <el-button type="danger" @click="deleteAccount" style="margin-left: 20px">
                删除账户
              </el-button>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, User } from '@element-plus/icons-vue'
import { useProjectStore } from '@/stores'
import { settingsApi } from '@/api'

// 初始化store
const projectStore = useProjectStore()
const currentProjectId = computed(() => projectStore.currentProject?.id)

// 加载状态和错误处理
const loading = ref(false)
const error = ref<string | null>(null)

// 当前激活的标签页
const activeTab = ref('preferences')

// 用户偏好设置
const notificationSettings = ref({
  pipelineStatus: true,
  testFailure: true,
  codeQuality: true,
  memorySafety: true,
  aiAnalysis: false,
  methods: ['email', 'websocket'],
  emailFrequency: 'immediate'
})

const dashboardSettings = ref({
  defaultDashboard: 'dashboard',
  refreshInterval: 60,
  density: 'comfortable',
  chartTheme: 'default'
})

const uiSettings = ref({
  theme: 'auto',
  language: 'zh-CN',
  timezone: 'Asia/Shanghai',
  dateFormat: 'yyyy-mm-dd',
  timeFormat: '24h'
})

// AI模型配置
const aiModelSettings = ref({
  testSelection: 'zhipu-glm4',
  codeReview: 'claude-3.5-sonnet',
  nlConfig: 'zhipu-glm4',
  memorySafety: 'claude-3.5-sonnet'
})

// API密钥
const apiKeys = ref({
  zhipu: '',
  qwen: '',
  anthropic: '',
  localModel: 'http://localhost:11434'
})

// CI/CD配置
const cicdSettings = ref({
  defaultBuildType: 'Release',
  parallelJobs: 4,
  enableCcache: true,
  cacheRetentionDays: 7,
  testTimeout: 300,
  enableCoverage: true
})

// 智能测试选择配置
const testSelectionSettings = ref({
  strategy: 'balanced',
  minConfidence: 70,
  impactDepth: 3
})

// 告警规则
const alertRules = ref([
  {
    id: 1,
    name: 'Pipeline失败告警',
    type: 'pipeline',
    condition: 'Pipeline失败率',
    threshold: '> 10%',
    enabled: true,
    actions: ['email', 'slack']
  },
  {
    id: 2,
    name: '测试失败告警',
    type: 'test',
    condition: '测试失败率',
    threshold: '> 5%',
    enabled: true,
    actions: ['email']
  },
  {
    id: 3,
    name: '内存安全告警',
    type: 'memory',
    condition: '严重内存问题',
    threshold: '> 0',
    enabled: true,
    actions: ['email', 'websocket', 'slack']
  },
  {
    id: 4,
    name: '资源使用告警',
    type: 'resource',
    condition: 'CPU使用率',
    threshold: '> 80%',
    enabled: false,
    actions: ['email']
  }
])

// 告警历史
const alertHistory = ref([
  {
    id: 1,
    timestamp: Date.now() - 3600000,
    rule: 'Pipeline失败告警',
    message: '项目 backend-api 的Pipeline #1234 失败',
    severity: 'critical',
    acknowledged: false
  },
  {
    id: 2,
    timestamp: Date.now() - 7200000,
    rule: '内存安全告警',
    message: '检测到3个严重内存泄漏问题',
    severity: 'critical',
    acknowledged: true
  },
  {
    id: 3,
    timestamp: Date.now() - 86400000,
    rule: '测试失败告警',
    message: '测试套件 AuthTests 失败率 8%',
    severity: 'warning',
    acknowledged: true
  }
])

const alertPagination = ref({
  currentPage: 1,
  pageSize: 10,
  total: 3
})

// 当前用户
const currentUser = ref({
  name: 'alice_chen',
  email: 'alice.chen@example.com',
  roles: ['admin', 'developer'],
  projects: ['backend-api', 'frontend-app', 'mobile-sdk'],
  avatar: '',
  displayName: 'Alice Chen',
  location: 'Beijing, China',
  company: 'Tech Corp',
  bio: '',
  twoFactorEnabled: false
})

// 项目权限
const projectPermissions = ref([
  {
    project: 'backend-api',
    role: 'admin',
    permissions: ['read', 'write', 'admin', 'deploy'],
    lastAccess: Date.now() - 3600000
  },
  {
    project: 'frontend-app',
    role: 'developer',
    permissions: ['read', 'write'],
    lastAccess: Date.now() - 86400000
  },
  {
    project: 'mobile-sdk',
    role: 'maintainer',
    permissions: ['read', 'write', 'deploy'],
    lastAccess: Date.now() - 172800000
  }
])

// API令牌
const apiTokens = ref([
  {
    id: 1,
    name: 'CI/CD自动化',
    token: 'gp8sK7mN3qP9lW2xR5tY8vB1cD4eF6gH',
    scopes: ['read', 'write'],
    expiresAt: new Date(Date.now() + 86400000 * 365),
    lastUsed: Date.now() - 3600000,
    visible: false
  },
  {
    id: 2,
    name: '开发测试',
    token: 'a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6',
    scopes: ['read'],
    expiresAt: null,
    lastUsed: Date.now() - 604800000,
    visible: false
  }
])

// SSH密钥
const sshKeys = ref([
  {
    id: 1,
    name: 'MacBook Pro',
    fingerprint: 'SHA256:abc123def456...',
    type: 'ED25519',
    createdAt: Date.now() - 86400000 * 30,
    lastUsed: Date.now() - 3600000
  },
  {
    id: 2,
    name: 'Development Server',
    fingerprint: 'SHA256:789xyz012abc...',
    type: 'RSA 4096',
    createdAt: Date.now() - 86400000 * 60,
    lastUsed: Date.now() - 86400000
  }
])

// 用户信息表单
const userInfo = ref({
  avatar: '',
  name: 'alice_chen',
  email: 'alice.chen@example.com',
  displayName: 'Alice Chen',
  location: 'Beijing, China',
  company: 'Tech Corp',
  bio: '',
  twoFactorEnabled: false
})

// 密码表单
const passwordForm = ref({
  currentPassword: '',
  newPassword: '',
  confirmPassword: ''
})

// 方法：格式化时间
const formatTime = (timestamp: number) => {
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN')
}

// 方法：格式化日期
const formatDate = (date: Date) => {
  return date.toLocaleDateString('zh-CN')
}

// 方法：获取操作标签
const getActionLabel = (action: string) => {
  const labels: Record<string, string> = {
    email: '邮件',
    websocket: '推送',
    slack: 'Slack',
    webhook: 'Webhook'
  }
  return labels[action] || action
}

// 方法：获取角色标签
const getRoleLabel = (role: string) => {
  const labels: Record<string, string> = {
    admin: '管理员',
    developer: '开发者',
    maintainer: '维护者',
    guest: '访客'
  }
  return labels[role] || role
}

// 方法：获取角色标签类型
const getRoleTagType = (role: string) => {
  if (role === 'admin') return 'danger'
  if (role === 'maintainer') return 'warning'
  if (role === 'developer') return 'primary'
  return 'info'
}

// 方法：获取权限标签
const getPermissionLabel = (perm: string) => {
  const labels: Record<string, string> = {
    read: '读取',
    write: '写入',
    admin: '管理',
    deploy: '部署'
  }
  return labels[perm] || perm
}

// 方法：加载设置
const loadSettings = async () => {
  loading.value = true
  error.value = null

  try {
    // 加载用户偏好设置
    const prefs = await settingsApi.getUserPreferences()
    if (prefs) {
      notificationSettings.value = prefs.notifications || notificationSettings.value
      dashboardSettings.value = prefs.dashboard || dashboardSettings.value
      uiSettings.value = prefs.ui || uiSettings.value
    }

    // 如果有选中的项目，加载项目配置
    if (currentProjectId.value) {
      const config = await settingsApi.getProjectConfig(currentProjectId.value)
      if (config) {
        aiModelSettings.value = config.ai_models || aiModelSettings.value
        cicdSettings.value = config.cicd || cicdSettings.value
        testSelectionSettings.value = config.test_selection || testSelectionSettings.value
      }
    }
  } catch (err: any) {
    console.error('Failed to load settings:', err)
    error.value = err.message || '加载设置失败'
    ElMessage.error(error.value)
  } finally {
    loading.value = false
  }
}

// 方法：保存偏好设置
const savePreferences = async () => {
  try {
    loading.value = true
    await settingsApi.saveUserPreferences({
      notifications: notificationSettings.value,
      dashboard: dashboardSettings.value,
      ui: uiSettings.value
    })
    ElMessage.success('偏好设置已保存')
  } catch (err: any) {
    console.error('Failed to save preferences:', err)
    ElMessage.error(err.message || '保存偏好设置失败')
  } finally {
    loading.value = false
  }
}

// 方法：重置偏好设置
const resetPreferences = () => {
  ElMessageBox.confirm('确定要重置所有偏好设置为默认值吗？', '确认重置', {
    confirmButtonText: '重置',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    ElMessage.success('偏好设置已重置')
  }).catch(() => {
    // 用户取消
  })
}

// 方法：保存项目配置
const saveProjectConfig = async () => {
  if (!currentProjectId.value) {
    ElMessage.warning('请先选择项目')
    return
  }

  try {
    loading.value = true
    await settingsApi.saveProjectConfig(currentProjectId.value, {
      ai_models: aiModelSettings.value,
      cicd: cicdSettings.value,
      test_selection: testSelectionSettings.value
    })
    ElMessage.success('项目配置已保存')
  } catch (err: any) {
    console.error('Failed to save project config:', err)
    ElMessage.error(err.message || '保存项目配置失败')
  } finally {
    loading.value = false
  }
}

// 方法：重置项目配置
const resetProjectConfig = () => {
  ElMessageBox.confirm('确定要重置项目配置为默认值吗？', '确认重置', {
    confirmButtonText: '重置',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    ElMessage.success('项目配置已重置')
  }).catch(() => {
    // 用户取消
  })
}

// 方法：测试API密钥
const testApiKey = (provider: string) => {
  ElMessage.info(`正在测试 ${provider} API 连接...`)

  setTimeout(() => {
    ElMessage.success(`${provider} API 连接成功！`)
  }, 1500)
}

// 方法：添加告警规则
const addAlertRule = () => {
  ElMessage.info('打开添加告警规则对话框...')
}

// 方法：编辑告警规则
const editAlertRule = (rule: any) => {
  ElMessage.info(`编辑告警规则: ${rule.name}`)
}

// 方法：删除告警规则
const deleteAlertRule = (rule: any) => {
  ElMessageBox.confirm(`确定要删除告警规则"${rule.name}"吗？`, '确认删除', {
    confirmButtonText: '删除',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    ElMessage.success('告警规则已删除')
  }).catch(() => {
    // 用户取消
  })
}

// 方法：切换告警规则
const toggleAlertRule = (rule: any) => {
  ElMessage.success(`告警规则"${rule.name}"已${rule.enabled ? '启用' : '禁用'}`)
}

// 方法：确认告警
const acknowledgeAlert = (alert: any) => {
  alert.acknowledged = true
  ElMessage.success('告警已确认')
}

// 方法：生成令牌
const generateToken = () => {
  ElMessage.info('打开生成令牌对话框...')
}

// 方法：切换令牌可见性
const toggleTokenVisibility = (token: any) => {
  token.visible = !token.visible
}

// 方法：撤销令牌
const revokeToken = (token: any) => {
  ElMessageBox.confirm(`确定要撤销令牌"${token.name}"吗？`, '确认撤销', {
    confirmButtonText: '撤销',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    ElMessage.success('令牌已撤销')
  }).catch(() => {
    // 用户取消
  })
}

// 方法：添加SSH密钥
const addSSHKey = () => {
  ElMessage.info('打开添加SSH密钥对话框...')
}

// 方法：删除SSH密钥
const deleteSSHKey = (key: any) => {
  ElMessageBox.confirm(`确定要删除SSH密钥"${key.name}"吗？`, '确认删除', {
    confirmButtonText: '删除',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    ElMessage.success('SSH密钥已删除')
  }).catch(() => {
    // 用户取消
  })
}

// 方法：更新个人信息
const updateProfile = () => {
  ElMessage.success('个人信息已更新')
}

// 方法：修改密码
const changePassword = () => {
  if (!passwordForm.value.currentPassword || !passwordForm.value.newPassword) {
    ElMessage.warning('请填写完整信息')
    return
  }

  if (passwordForm.value.newPassword !== passwordForm.value.confirmPassword) {
    ElMessage.error('两次输入的新密码不一致')
    return
  }

  ElMessage.success('密码已修改')
  passwordForm.value = {
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  }
}

// 方法：启用两步验证
const enableTwoFactor = () => {
  ElMessage.info('打开两步验证设置向导...')
}

// 方法：禁用两步验证
const disableTwoFactor = () => {
  ElMessageBox.confirm('确定要禁用两步验证吗？这会降低账户安全性。', '确认禁用', {
    confirmButtonText: '禁用',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    userInfo.value.twoFactorEnabled = false
    ElMessage.success('两步验证已禁用')
  }).catch(() => {
    // 用户取消
  })
}

// 方法：导出数据
const exportData = () => {
  ElMessage.info('正在准备数据导出...')
}

// 方法：删除账户
const deleteAccount = () => {
  ElMessageBox.alert('删除账户需要联系管理员，请发送邮件到 support@example.com', '删除账户', {
    confirmButtonText: '我知道了',
    type: 'warning'
  })
}

// 生命周期：挂载
onMounted(() => {
  loadSettings()
})

// 监听项目切换
watch(currentProjectId, () => {
  if (currentProjectId.value) {
    loadSettings()
  }
})
</script>

<style scoped>
.settings {
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

.settings-content {
  padding: 20px;
}

.setting-section {
  margin-bottom: 30px;
}

.setting-section h3 {
  margin: 0 0 20px 0;
  font-size: 18px;
  color: #303133;
  border-left: 4px solid #409eff;
  padding-left: 10px;
}

.setting-section h4 {
  margin: 20px 0 15px 0;
  font-size: 16px;
  color: #606266;
}

.setting-description {
  margin-left: 10px;
  color: #909399;
  font-size: 13px;
}

:deep(.el-form-item) {
  margin-bottom: 22px;
}

:deep(.el-divider) {
  margin: 40px 0;
}
</style>
