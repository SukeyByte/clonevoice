# 视频生成服务文档

## 目录
- [API 服务](#api-服务)
- [消息状态](#消息状态)
- [SSE 实时推送](#sse-实时推送)
- [消息队列(MQ)](#消息队列)

## API 服务

### 视频生成任务

#### 任务状态更新
- **类型**: POST
- **路由**: `/api/video/task/update`
- **请求体**:
```json
{
    "task_id": "string",
    "status": "string",
    "output_path": "string",
    "type": "video_task_update"
}
```

## 消息状态

### 任务状态定义
- `processing`: 任务处理中
- `completed`: 任务完成
- `failed`: 任务失败

### 任务进度信息
```json
{
    "task_id": "string",
    "status": "string",
    "progress": "number",
    "message": "string",
    "output_path": "string",
    "error": "string"
}
```

### 进度状态说明
- 10%: 任务开始处理
- 20%: 加载视频帧
- 40%: 提取音频特征
- 60%: 生成唇形同步视频
- 80%: 保存视频
- 100%: 任务完成

## SSE 实时推送

### 视频任务完成通知
```json
{
    "type": "video_task_completed",
    "task_id": "string",
    "status": "completed",
    "output_path": "string"
}
```

## 消息队列

### 交换机和队列
- **交换机**: 默认交换机
- **队列**: `api_queue`

### 消息格式
```json
{
    "task_id": "string",
    "status": "string",
    "output_path": "string",
    "type": "video_task_update"
}
```

### Redis 任务存储
- **键格式**: `task:{task_id}`
- **值格式**: JSON字符串，包含任务完整信息

## 目录结构
```
├── output/           # 输出目录
│   └── temp/         # 临时文件目录
├── videos/           # 视频文件目录
└── video_service/    # 视频服务代码
```

## 依赖服务
- Redis: 用于存储任务状态和信息
- RabbitMQ: 用于任务队列和服务间通信
- CUDA/CPU: 用于模型推理