# 构建执行引擎实施总结 - Phase 2: 实时日志流

**日期**: 2026-03-09
**阶段**: Phase 2 - 实时日志流
**状态**: ✅ 完成

---

## 完成的工作

### 1. 构建日志流处理器 ✅

**文件**: `src/services/build/log_streamer.py`

**核心类**:

#### `LogMessage`
- 日志消息数据类
- 包含级别、消息、时间戳、来源等信息
- 支持元数据扩展

#### `BuildLogStreamer`
- **主要功能**:
  - 实时捕获和推送构建日志
  - 支持日志级别过滤 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  - 日志来源过滤 (build, cmake, make, qmake, ninja)
  - 单行最大长度限制（防止单行过长）
  - 日志缓冲（支持重放历史日志）

- **核心方法**:
  - `stream_log()` - 流式传输日志
  - `stream_info/warning/error/debug()` - 便捷方法
  - `send_status_update()` - 发送状态更新
  - `send_progress()` - 发送进度更新
  - `stream_from_process()` - 从子进程流式读取输出
  - `replay_buffer()` - 重放缓冲的日志

- **统计功能**:
  - 总日志数统计
  - 按级别分类统计
  - 订阅者数量统计

#### `BuildLogStreamManager`
- 管理多个构建任务的日志流
- 单例模式，全局共享
- 提供日志流的创建、获取、移除功能

**特性**:
- ✅ 日志级别过滤
- ✅ 来源过滤
- ✅ 日志缓冲和重放
- ✅ 统计信息收集
- ✅ 异常处理
- ✅ 线程安全

### 2. Celery任务集成 ✅

**文件**: `src/tasks/build_tasks.py`

**更新内容**:
- 导入日志流管理器
- 在`_execute_build_async()`中创建日志流处理器
- 发送构建开始/结束状态
- 实时推送构建信息
- 错误处理和日志记录

**流程**:
```
Celery任务开始
    ↓
创建BuildLogStreamer
    ↓
发送"running"状态
    ↓
执行构建 (BuildExecutorService)
    ↓
发送结果状态 (success/failed)
    ↓
发送统计信息
```

### 3. BuildExecutorService集成 ✅

**文件**: `src/services/build/executor.py`

**更新内容**:
- 导入日志流处理器
- `execute_build()`方法添加`log_streamer`参数
- 添加`_send_log_dual()`辅助方法
- 同时支持WebSocket和日志流处理器

**特性**:
- 向后兼容（仍支持WebSocket）
- 优先使用日志流处理器
- WebSocket作为fallback

---

## 使用方式

### WebSocket订阅流程

1. **客户端连接WebSocket**
```javascript
// 客户端代码示例
const ws = new WebSocket('ws://localhost:8000/api/ws');

ws.onopen = () => {
    // 订阅构建日志
    ws.send(JSON.stringify({
        action: 'subscribe',
        topic: `build:${job_id}`  // 例如: build:job-456
    }));
};

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);

    switch(message.type) {
        case 'log':
            console.log(`[${message.level}] ${message.message}`);
            break;
        case 'status_update':
            console.log(`Status: ${message.status}`);
            break;
        case 'progress':
            console.log(`Progress: ${message.progress}%`);
            break;
    }
};
```

### API端点使用

```bash
# 提交构建任务
curl -X POST "http://localhost:8000/api/v1/build/celery/submit" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 1,
    "pipeline_id": "pipeline-123",
    "job_id": "job-456",
    "gitlab_job_id": 789,
    "job_name": "build-linux",
    "build_type": "Release"
  }'

# 响应:
{
    "job_id": "job-456",
    "celery_task_id": "abc-123-def",
    "status": "pending",
    "message": "Build task submitted to Celery queue"
}
```

### 日志消息格式

#### Log消息
```json
{
    "type": "log",
    "topic": "build:job-456",
    "level": "info",
    "message": "Starting build for job-456",
    "timestamp": 1678425640.123,
    "datetime": "2026-03-09T12:34:00.123456",
    "source": "build",
    "job_id": "job-456",
    "project_id": 1,
    "pipeline_id": "pipeline-123"
}
```

#### Status Update消息
```json
{
    "type": "status_update",
    "topic": "build:job-456",
    "status": "running",
    "timestamp": 1678425640.123,
    "message": "Build started",
    "job_id": "job-456"
}
```

#### Progress消息
```json
{
    "type": "progress",
    "topic": "build:job-456",
    "progress": 50.0,
    "total": 100,
    "current": 50,
    "timestamp": 1678425640.123,
    "message": "Compiling..."
}
```

---

## 日志级别

| 级别 | 说明 | 使用场景 |
|------|------|----------|
| DEBUG | 调试信息 | 详细的执行信息 |
| INFO | 一般信息 | 正常的构建输出 |
| WARNING | 警告信息 | 非致命错误 |
| ERROR | 错误信息 | 编译错误、链接错误 |
| CRITICAL | 严重错误 | 导致构建失败的问题 |

### 级别过滤

可以通过`set_min_level()`设置最小日志级别：

```python
# 只记录WARNING及以上级别
log_streamer.set_min_level(LogLevel.WARNING)
```

---

## 性能优化

### 日志缓冲

- 默认缓冲1000条日志
- 新客户端连接时可以重放历史日志
- 自动清理旧日志

### 单行长度限制

- 默认最大10000字符
- 防止单行日志过长
- 自动截断并标记

### 异步发送

- 所有日志推送都是异步的
- 不阻塞构建执行
- 异常隔离

---

## 监控和统计

### 获取统计信息

```python
from src.services.build.log_streamer import build_log_stream_manager

# 获取特定构建的统计
streamer = build_log_stream_manager.get_streamer("job-456")
stats = streamer.get_statistics()

print(stats)
# {
#     "job_id": "job-456",
#     "total_logs": 1523,
#     "logs_by_level": {
#         "debug": 234,
#         "info": 1123,
#         "warning": 145,
#         "error": 21,
#         "critical": 0
#     },
#     "buffer_size": 1000,
#     "topic": "build:job-456",
#     "subscribers": 2
# }
```

### 获取所有统计

```python
all_stats = build_log_stream_manager.get_all_statistics()
```

---

## 测试验证

### 手动测试步骤

1. **启动服务**:
```bash
# 启动API服务
uvicorn src.main:app --reload

# 启动Celery worker
celery -A src.tasks.celery_app worker --loglevel=info --queues=build
```

2. **提交构建任务**:
```bash
curl -X POST "http://localhost:8000/api/v1/build/celery/submit" \
  -H "Content-Type: application/json" \
  -d @- << EOF
{
    "project_id": 1,
    "pipeline_id": "test-pipeline",
    "job_id": "test-job",
    "gitlab_job_id": 1,
    "job_name": "test-build",
    "build_type": "Release",
    "parallel_jobs": 4,
    "project_path": "/path/to/project"
}
EOF
```

3. **使用WebSocket客户端订阅**:
```python
import asyncio
import websockets
import json

async def subscribe_build_logs(job_id):
    uri = "ws://localhost:8000/api/ws"
    async with websockets.connect(uri) as websocket:
        # 订阅
        await websocket.send(json.dumps({
            "action": "subscribe",
            "topic": f"build:{job_id}"
        }))

        # 接收消息
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            print(f"[{data.get('level', 'INFO')}] {data.get('message', '')}")

# 运行
asyncio.run(subscribe_build_logs("test-job"))
```

### 预期结果

- ✅ 客户端连接成功
- ✅ 构建日志实时推送
- ✅ 状态更新正确发送
- ✅ 缓冲日志可以重放
- ✅ 统计信息准确

---

## 故障排查

### 问题1: 没有收到日志消息

**可能原因**:
- 未正确订阅WebSocket主题
- 构建任务未启动
- 日志级别过滤

**解决方案**:
```python
# 检查订阅者数量
from src.services.build.websocket.manager import manager
count = manager.get_subscriber_count(f"build:{job_id}")
print(f"Subscribers: {count}")

# 降低日志级别
log_streamer.set_min_level(LogLevel.DEBUG)
```

### 问题2: 日志延迟

**可能原因**:
- WebSocket连接慢
- 网络延迟
- 日志生成速度过快

**解决方案**:
- 使用日志缓冲
- 批量发送日志
- 增加worker数量

### 问题3: 日志丢失

**可能原因**:
- 缓冲区溢出
- 客户端断开连接
- 异常未捕获

**解决方案**:
- 增加缓冲区大小
- 实现日志持久化
- 完善异常处理

---

## 后续优化

### 短期优化
- [ ] 添加日志持久化（存储到文件/数据库）
- [ ] 实现日志搜索功能
- [ ] 支持日志下载
- [ ] 添加日志高亮功能

### 长期优化
- [ ] 分布式日志收集（ELK/Loki）
- [ ] 实时日志分析
- [ ] 异常检测和告警
- [ ] 日志可视化Dashboard

---

## 与Phase 1的集成

Phase 2在Phase 1的基础上添加了实时日志流功能：

```
Phase 1架构:
API → 调度器 → Celery任务 → 执行器 → 构建工具

Phase 2扩展:
                              ↓
                         日志流处理器
                              ↓
                         WebSocket推送
                              ↓
                         客户端实时显示
```

**兼容性**:
- ✅ 完全向后兼容Phase 1
- ✅ 可选功能（不使用日志流也能正常运行）
- ✅ 不影响现有API

---

**实施人员**: Claude Code
**审核状态**: 待审核
**下一步**: Phase 4 - 状态跟踪和性能监控
