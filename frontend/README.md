# 缺陷检测前端

这是一个基于 Vue 3、Vite 和 Element Plus 的缺陷检测系统前端，提供数据集管理、标注、模型管理、图像预处理、单图推理、实时推理、硬件控制和用户管理等功能。

## 技术栈

- Vue 3 + Vite 7
- Vue Router 4
- Pinia 3
- Element Plus
- Axios
- Fabric.js（图像标注）
- GSAP、vuedraggable、marked

## 快速开始

### 环境要求

- Node.js 18 或更高版本
- npm 9 或更高版本
- 可访问的缺陷检测后端服务

### 安装和启动

```bash
npm install
npm run dev
```

启动后访问 <http://127.0.0.1:5173/>。未登录时会自动进入 `/login`。

其他命令：

```bash
npm run build    # 构建生产文件到 dist/
npm run preview  # 预览生产构建结果
```

## 与后端连接

### 开发环境默认方式

默认假设后端运行在 `http://127.0.0.1:8000`。前端请求使用相对路径 `/api/v1`，由 `vite.config.js` 转发：

| 前端路径 | 后端目标 |
| --- | --- |
| `/api/*` | `http://127.0.0.1:8000/api/*` |
| `/static_uploads/*` | `http://127.0.0.1:8000/static_uploads/*` |
| `/api/v1/hardware/camera/stream`（WebSocket） | 后端同路径 |

因此，开发时浏览器只访问 `5173` 端口，不会直接跨域请求 `8000` 端口，也不需要额外配置 CORS。后端仍需启动并提供对应 API。

### 修改后端地址

复制 `.env.example` 为 `.env.local`，按实际后端地址修改：

```dotenv
VITE_BACKEND_URL=http://127.0.0.1:8000
```

修改环境变量后需要重启 Vite。`VITE_BACKEND_URL` 用于开发代理；如果生产环境不使用同源反向代理，可以设置完整 API 地址：

```dotenv
VITE_API_BASE_URL=https://api.example.com/api/v1
```

生产环境直接使用完整 API 地址时，后端必须允许前端域名的 CORS 请求，并正确处理 `Authorization` 请求头。更推荐在 Nginx 或其他网关中将 `/api`、`/static_uploads` 和 WebSocket 路径转发到后端，使前后端保持同源。

### 认证方式

登录请求为：

```text
POST /api/v1/auth/token
Content-Type: application/x-www-form-urlencoded
```

登录成功后，前端将返回的 `access_token` 保存到浏览器 `localStorage` 的 `token` 字段。后续 Axios 请求会自动添加：

```text
Authorization: Bearer <access_token>
```

刷新页面时，Pinia 用户状态会从 `localStorage` 恢复，并通过 `GET /api/v1/users/me` 获取当前用户信息。

## 目录结构

```text
src/
├── api/          # Axios 客户端和后端接口封装
├── assets/       # 图片、视频等静态资源
├── components/  # 可复用组件
├── router/      # 路由和登录权限守卫
├── store/       # Pinia 状态：用户、摄像头、预处理任务
├── utils/       # 事件总线等工具
├── views/       # 页面级组件
├── App.vue      # 应用根组件
├── main.js      # 应用初始化
└── style.css    # 全局样式
```

主要页面路由：

- `/dashboard`：系统总览
- `/hardware`：硬件和摄像头控制
- `/datasets`：数据集管理、预处理和标注入口
- `/models`：模型管理
- `/inference/inference-jobs`：推理任务
- `/inference/single-inference`：单图推理
- `/inference/realtime-inference`：实时推理
- `/user-management`：管理员用户管理
- `/user-settings`：个人设置
- `/documentation`：项目文档

## API 模块

所有业务请求集中在 `src/api/`，页面和 Store 不直接拼接后端 URL：

- `auth.js`：登录和当前用户
- `users.js`：用户信息和用户管理
- `datasets.js`：数据集、文件浏览和标注导出
- `models.js`：模型上传、查询和删除
- `processing.js`：图像预处理任务
- `inference.js`：推理任务和结果
- `hardware.js`：摄像头连接、参数和实时流

新增接口时，优先在对应 API 模块中封装，再由页面或 Store 调用，以保持请求地址、认证和错误处理的一致性。

## 常见问题

### 页面打不开

确认 `npm run dev` 进程仍在运行，并访问终端输出的地址（通常为 <http://127.0.0.1:5173/>）。如果看到旧的 Conda 报错，它来自 PowerShell 配置文件，不是本项目依赖；可在不加载 PowerShell 配置的终端中运行 npm，或清理配置文件中的失效 Conda 路径。

### 页面能打开，但登录或摄像头状态失败

确认后端正在监听 `8000` 端口，并检查浏览器 Network 面板中的 `/api/v1` 请求。若请求被发送到错误地址，检查 `.env.local` 后重启 Vite；若生产环境直接跨域访问后端，检查后端 CORS 配置。

### 摄像头实时流无法连接

确认后端支持 WebSocket，并允许 `/api/v1/hardware/camera/stream`。开发环境的 Vite `/api` 代理已启用 WebSocket 转发；生产环境需要在网关中启用 WebSocket Upgrade。

## 构建说明

`npm run build` 会生成 `dist/`。部署时需要同时保证：

1. Web 服务器将 Vue history 路由回退到 `index.html`。
2. `/api`、`/static_uploads` 和摄像头 WebSocket 路径能转发到后端。
3. 前端使用完整后端地址时，后端配置了正确的 CORS、认证头和凭据策略。
