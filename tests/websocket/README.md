# WebSocket测试指南

本目录包含WebSocket功能的测试脚本和验证工具。

---

## 📋 测试文件

### `test_websocket_client.py`

WebSocket客户端测试脚本，验证以下功能：
- ✅ WebSocket连接和断开
- ✅ 主题订阅和取消订阅
- ✅ 消息发送和接收
- ✅ 心跳检测 (ping/pong)
- ✅ 广播消息
- ✅ 日志流推送
- ✅ ConnectionManager功能

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install websockets
```

### 2. 启动后端服务器

在终端1中运行：

```bash
./scripts/start-backend.sh
```

服务器将在 http://localhost:8000 启动。

### 3. 运行WebSocket测试

在终端2中运行：

```bash
python tests/websocket/test_websocket_client.py
```

---

## 🧪 测试内容

### 测试1: ConnectionManager功能测试

测试WebSocket连接管理器的核心功能：

- ✅ 连接创建和管理
- ✅ 主题订阅
- ✅ 个人消息发送
- ✅ 连接断开和清理
- ✅ 统计信息查询

**预期结果**: 所有功能正常运行

---

### 测试2: 广播消息功能测试

测试广播和主题订阅功能：

- ✅ 日志消息广播 (`build:test_job_123`)
- ✅ 状态更新广播 (`test:test_job_456`)
- ✅ 进度更新广播 (`pipeline:pipeline_789`)

**预期结果**: 消息正确发送到订阅者

---

### 测试3: 日志流功能测试

模拟构建日志流：

```
ℹ️  [INFO] Starting build configuration...
ℹ️  [INFO] CMake configuration complete
ℹ️  [INFO] Compiling source files...
⚠️  [WARNING] Unused variable 'x' in line 42
ℹ️  [INFO] Linking binaries...
ℹ️  [INFO] Build complete successfully
```

**预期结果**: 所有日志级别正确处理

---

### 测试4: WebSocket连接测试（可选）

需要后端服务器运行。

测试完整的WebSocket连接：

1. **连接建立**
   - 连接到 `ws://localhost:8000/api/v1/ws/connect`
   - 订阅主题: `build:test_job_123`, `test:test_job_456`

2. **消息交换**
   - 接收欢迎消息
   - 订阅额外主题
   - 发送心跳ping
   - 接收pong响应
   - 测试回显功能
   - 取消订阅

3. **连接关闭**
   - 正常断开连接

**预期结果**: 所有消息正确收发

---

## 🔧 故障排除

### 问题1: 连接被拒绝

**错误**: `websockets.exceptions.ConnectionRefused`

**原因**: 后端服务器未运行

**解决**:
```bash
./scripts/start-backend.sh
```

---

### 问题2: 超时无响应

**错误**: `asyncio.TimeoutError`

**原因**: 服务器端没有活动消息

**解决**: 这是正常的，如果没有活跃的构建/测试任务，服务器不会主动推送消息。

---

### 问题3: 导入错误

**错误**: `ModuleNotFoundError: No module named 'src'`

**原因**: Python路径设置问题

**解决**: 测试脚本已添加路径设置，如果仍有问题，确保在项目根目录运行：

```bash
cd /home/kerfs/AI-CICD-new
python tests/websocket/test_websocket_client.py
```

---

## 📊 预期输出

### 成功运行的输出示例

```
============================================================
WebSocket连接测试
============================================================
连接到: ws://localhost:8000/api/v1/ws/connect?subscribe=...

✅ WebSocket连接成功
✅ 收到欢迎消息: connected
✅ 发送订阅请求: pipeline:pipeline_789
✅ 订阅确认: subscribed - pipeline:pipeline_789
发送心跳ping...
✅ 收到心跳响应: pong
发送回显测试...
✅ 回显响应: {'type': 'echo', 'data': {'test': 'Hello WebSocket!'}}
等待服务器消息（5秒）...
⏱️  超时：没有收到服务器消息（正常，如果没有活动）
取消订阅: build:test_job_123
✅ 取消订阅确认: unsubscribed - build:test_job_123

============================================================
✅ 所有测试通过
============================================================
```

---

## 🎯 验证清单

运行测试后，确认以下功能正常：

- [ ] ConnectionManager能创建和管理连接
- [ ] 主题订阅功能正常
- [ ] 广播消息能发送到订阅者
- [ ] 日志流能正确推送
- [ ] WebSocket连接能建立和断开
- [ ] 心跳检测正常
- [ ] 消息收发正确

---

## 📝 下一步

测试通过后，可以：

1. **集成测试**: 在实际的构建/测试流程中验证日志流
2. **前端集成**: 验证前端能正确接收和显示日志
3. **性能测试**: 测试大量并发连接的性能
4. **压力测试**: 测试高频消息推送的稳定性

---

**创建时间**: 2026-03-10
**维护者**: AI-CICD Team
