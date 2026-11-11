# 缺陷检测后端

基于 FastAPI、SQLAlchemy 和 PyTorch 的缺陷检测后端服务，提供用户认证、数据集管理、图像处理、模型管理、推理和硬件采集接口。

## 目录结构

```text
app/
  main.py                 # FastAPI 应用入口
  api/routers/            # API 路由
  core/                   # 配置和安全认证
  crud/                   # 数据库 CRUD
  db/                     # SQLAlchemy Engine、Session 和模型
  schemas/                # Pydantic 请求/响应模型
  services/               # 业务服务和模型推理
uploads/                  # 上传文件和相机配置
processed_images/         # 处理后的图片
requirements.txt          # Python 依赖
```

## 环境要求

- Windows、Python 3.10 或更高版本
- MySQL 5.7/8.0（当前配置使用 MySQL）
- 建议使用项目自带的 `.venv`

## 安装依赖

在项目根目录执行：

```powershell
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

如果尚未创建虚拟环境：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## 数据库配置

当前项目通过 `app/db/base.py` 创建 SQLAlchemy Engine，连接地址由 `.env` 中的 `DATABASE_URL` 提供。项目目前没有 Alembic 迁移目录，也不会在服务启动时自动创建数据表，因此请先准备数据库和对应表结构。

### 1. 创建 MySQL 数据库

```sql
CREATE DATABASE defect_detection
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

### 2. 配置 `.env`

`.env` 位于项目根目录，不要提交到 Git。可按下面的格式配置：

```dotenv
DATABASE_URL=mysql+pymysql://用户名:密码@127.0.0.1:3306/defect_detection?charset=utf8mb4
SECRET_KEY=请替换为长度足够的随机字符串
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
UPLOADS_DIR=uploads

SMTP_HOST=smtp.qq.com
SMTP_PORT=587
SMTP_USERNAME=你的邮箱账号
SMTP_PASSWORD=邮箱授权码
SMTP_SENDER_EMAIL=你的发件邮箱
```

注意：密码中包含 `@`、`:`、`/` 等特殊字符时，需要按 URL 规则编码。`SMTP_*` 主要用于邮件通知功能；不使用邮件功能时仍建议保留这些配置项，因为当前配置模型会读取它们。

### 3. 初始化数据表

当前仓库没有迁移脚本。请使用已有数据库结构，或根据 `app/db/models.py` 创建表后再调用 API。建议后续引入 Alembic 管理表结构变更，避免直接修改生产数据库。

## 启动后端

```powershell
.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

开发时启用热重载：

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

启动成功后：

- 服务首页：http://127.0.0.1:8000/
- Swagger 文档：http://127.0.0.1:8000/docs
- ReDoc：http://127.0.0.1:8000/redoc
- 上传文件：http://127.0.0.1:8000/static_uploads/文件相对路径

## 前端连接

### 开发环境地址

前端开发服务器可以使用以下后端地址：

```text
http://127.0.0.1:8000
```

当前后端已允许以下前端来源跨域访问：

- `http://localhost`
- `http://localhost:5173`（常见 Vite/Vue 地址）
- `http://127.0.0.1`
- `http://127.0.0.1:8080`

如果前端使用其他端口，需要在 `app/main.py` 的 `FRONTEND_ORIGINS` 中加入完整来源，例如 `http://localhost:3000`，然后重启后端。

### Axios 示例

```javascript
import axios from "axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:8000/api/v1",
  timeout: 60000,
});

export async function getDatasets(token) {
  const response = await api.get("/datasets/", {
    headers: { Authorization: `Bearer ${token}` },
  });
  return response.data;
}
```

### 登录并保存 Token

登录接口使用 OAuth2 表单数据，不是 JSON：

```javascript
const body = new URLSearchParams();
body.append("username", username);
body.append("password", password);

const response = await fetch(
  "http://127.0.0.1:8000/api/v1/auth/token",
  {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  },
);

const { access_token } = await response.json();
localStorage.setItem("access_token", access_token);
```

后续需要认证的请求携带：

```http
Authorization: Bearer <access_token>
```

### 主要接口前缀

| 功能 | 前缀 |
| --- | --- |
| 认证、注册 | `/api/v1/auth` |
| 用户 | `/api/v1/users` |
| 数据集 | `/api/v1/datasets` |
| 处理任务 | `/api/v1/processing` |
| 硬件和相机 | `/api/v1/hardware` |
| 模型 | `/api/v1/models` |
| 推理 | `/api/v1/inference` |
| 标注 | `/api/v1/annotations` |

完整请求参数和响应结构以 `/docs` 中的 OpenAPI 文档为准。

## 常见问题

### 启动时提示配置字段缺失

确认当前目录是项目根目录，并检查 `.env` 是否存在且包含 `DATABASE_URL`、`SECRET_KEY` 和 `SMTP_*` 字段。

### 请求返回数据库连接错误

检查 MySQL 服务是否启动、数据库名和账号密码是否正确，并确认 `DATABASE_URL` 使用了 `mysql+pymysql://` 格式。

### 浏览器提示 CORS 错误

确认前端实际访问来源（协议、域名和端口）已加入 `FRONTEND_ORIGINS`。修改后需要重启 Uvicorn。

### 接口返回 401

先调用 `/api/v1/auth/token` 获取 Token，并在请求头中使用 `Authorization: Bearer <token>`。登录接口的请求体必须是 `application/x-www-form-urlencoded`。
