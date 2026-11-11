<template>
  <el-container class="documentation-container">
    <!-- 左侧导航菜单 -->
    <el-aside width="220px" class="documentation-aside">
      <el-menu
          :default-active="activeSection"
          class="el-menu-vertical-demo"
          @select="handleMenuSelect"
      >
        <el-menu-item index="overview">
          <el-icon><Document /></el-icon> <!-- 修正图标用法 -->
          <span>1. 项目总览</span>
        </el-menu-item>
        <el-menu-item index="quick-start">
          <el-icon><Star /></el-icon> <!-- 修正图标用法 -->
          <span>2. 快速启动指南</span>
        </el-menu-item>
        <el-menu-item index="backend-details">
          <el-icon><Setting /></el-icon> <!-- 修正图标用法 -->
          <span>3. 后端服务详解</span>
        </el-menu-item>
        <el-menu-item index="frontend-details">
          <el-icon><Monitor /></el-icon> <!-- 修正图标用法 -->
          <span>4. 前端应用详解</span>
        </el-menu-item>
        <el-menu-item index="extend-maintain" v-if="userStore.isAdmin">
          <el-icon><Plus /></el-icon> <!-- 修正图标用法 -->
          <span>5. 扩展与维护</span>
        </el-menu-item>
        <el-menu-item index="faq">
          <el-icon><QuestionFilled /></el-icon> <!-- 修正图标用法 -->
          <span>6. 常见问题 (FAQ)</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- 右侧内容区域 -->
    <el-main class="documentation-main">
      <el-card class="box-card">
        <template #header>
          <div class="card-header">
            <span>📚 线激光内表面缺陷检测系统 - 开发者文档 📚</span>
          </div>
        </template>

        <!-- 1. 项目总览 -->
        <h2 id="overview">1. 项目总览：系统目的与架构</h2>
        <el-alert
            title="系统概览：本系统旨在实现管道内表面缺陷的自动化检测。"
            type="info"
            show-icon
            :closable="false"
        />
        <p>
          本系统是一个智能检测解决方案，利用线激光技术和人工智能算法，对管道内部表面缺陷进行高精度、自动化识别与分析。它由三个主要部分构成：
        </p>
        <ul>
          <li><strong>硬件层 (数据采集)</strong>：负责连接和控制相机与线激光设备，实时采集管道内部的图像数据。</li>
          <li><strong>后端服务 (数据处理与AI推理)</strong>：作为系统的核心处理单元，负责接收、存储和处理图像数据，运行AI模型进行缺陷识别，并提供API接口供前端调用。</li>
          <li><strong>前端界面 (用户交互)</strong>：提供直观的用户操作界面，用于控制硬件设备、管理数据集、配置AI模型参数、启动检测任务以及可视化检测结果。</li>
        </ul>
        <el-divider />

        <!-- 2. 快速启动指南 -->
        <h2 id="quick-start">2. 快速启动指南</h2>
        <el-alert
            title="本章节提供系统快速部署与运行的步骤，请按序操作以确保系统正常启动。"
            type="success"
            show-icon
            :closable="false"
        />

        <h3>2.1 后端服务启动步骤 (`defect-detection-backend`)</h3>
        <p>后端服务是系统的核心处理单元，负责数据处理和AI模型运行。</p>
        <ol>
          <li>
            <strong>环境准备：：</strong> 确保您的系统已安装 Python 3.8 或更高版本。
            <p>
              <em>验证方法：</em> 打开命令行工具（如 `cmd` 或 `Terminal`），输入 `python --version`。
            </p>
          </li>
          <li>
            <strong>依赖安装：：</strong> 导航至 `defect-detection-backend` 目录，安装所有Python依赖。
            <p>
              在命令行中执行：
            </p>
            <el-card class="code-card">
              <code>pip install -r requirements.txt</code>
            </el-card>
            <p>
              <em>注意：</em> 如果 `requirements.txt` 文件不存在，请先通过 `pip freeze > requirements.txt` 命令生成。
            </p>
          </li>
          <li>
            <strong>环境变量配置：：</strong> 复制 `.env.example` 文件为 `.env`，并编辑 `.env` 文件。
            <p>
              修改 `DATABASE_URL` 为您的MySQL数据库连接字符串，并为 `SECRET_KEY` 生成一个强随机字符串。
            </p>
            <el-card class="code-card">
              <code>DATABASE_URL="mysql+pymysql://[用户名]:[密码]@127.0.0.1:3306/[数据库名]"</code><br>
              <code>SECRET_KEY="[您的随机密钥字符串]"</code>
            </el-card>
          </li>
          <li>
            <strong>数据库准备：：</strong> 确保MySQL服务正在运行，并且 `.env` 中指定的数据库已创建。
            <p>
              您可以使用MySQL管理工具（如Navicat或MySQL Workbench）进行检查和创建。
            </p>
          </li>
          <li>
            <strong>启动服务：：</strong> 在 `defect-detection-backend` 目录下，执行以下命令启动FastAPI应用。
            <p>
              <el-card class="code-card">
                <code>uvicorn app.main:app --reload</code>
              </el-card>
              成功启动后，命令行将显示“Application startup complete.”。
            </p>
          </li>
          <li>
            <strong>API文档访问：：</strong> 服务启动后，您可以通过浏览器访问FastAPI自动生成的API文档。
            <p>
              访问地址： <el-link type="primary" href="http://127.0.0.1:8000/docs" target="_blank">http://127.0.0.1:8000/docs</el-link>
            </p>
          </li>
        </ol>

        <h3>2.2 前端应用启动步骤 (`defect-detection-frontend`)</h3>
        <p>前端应用提供用户界面和交互功能。</p>
        <ol>
          <li>
            <strong>环境准备：：</strong> 确保您的系统已安装 Node.js 16 或更高版本。
            <p>
              <em>验证方法：</em> 打开命令行工具，输入 `node -v`。
            </p>
          </li>
          <li>
            <strong>依赖安装：：</strong> 导航至 `defect-detection-frontend` 目录，安装所有Node.js依赖。
            <p>
              在命令行中执行：
            </p>
            <el-card class="code-card">
              <code>npm install</code>
            </el-card>
          </li>
          <li>
            <strong>后端地址配置：：</strong> 检查 `src/api/index.js` 文件中的 `baseURL` 配置。
            <p>
              确保 `baseURL` 指向正确的后端服务地址（通常是 `http://127.0.0.1:8000/api/v1`）。
            </p>
            <el-card class="code-card">
              <code>baseURL: 'http://127.0.0.1:8000/api/v1',</code>
            </el-card>
          </li>
          <li>
            <strong>启动应用：：</strong> 在 `defect-detection-frontend` 目录下，执行以下命令启动Vue应用。
            <p>
              <el-card class="code-card">
                <code>npm run dev</code>
              </el-card>
              成功启动后，命令行将显示应用访问地址（通常是 `http://localhost:5173`）。
            </p>
          </li>
          <li>
            <strong>访问界面：：</strong> 在浏览器中打开终端提示的地址。
            <p>
              访问地址： <el-link type="primary" href="http://localhost:5173" target="_blank">http://localhost:5173</el-link>
              您将看到系统的登录界面。
            </p>
          </li>
        </ol>
        <el-divider />

        <!-- 3. 后端 (FastAPI) 详细说明 -->
        <h2 id="backend-details">3. 后端服务详解</h2>
        <el-alert
            title="后端服务采用模块化架构，各组件职责分离，协同完成数据处理与业务逻辑。"
            type="warning"
            show-icon
            :closable="false"
        />

        <h3>3.1 目录结构与核心文件解析</h3>
        <p>
          后端代码组织严谨，每个目录和文件都有其特定职责。
        </p>
        <el-card class="code-card">
          <pre><code>
/defect-detection-backend
|-- /app                  # 核心应用代码目录
|   |-- /api              # API层：定义路由和依赖
|   |   |-- /routers      # 按功能模块划分的路由文件 (e.g., auth.py, users.py, datasets.py)
|   |   `-- deps.py       # 依赖注入函数 (如 get_current_user)，用于认证和获取数据库会话
|   |
|   |-- /core             # 核心配置和安全模块
|   |   |-- config.py     # 从.env加载配置，提供全局配置参数
|   |   `-- security.py   # 密码哈希、JWT Token生成与验证逻辑
|   |
|   |-- /crud             # 数据库操作层 (CRUD: Create, Read, Update, Delete)
|   |   |-- __init__.py   # 导出所有crud函数
|   |   `-- crud_user.py, crud_dataset.py, ... # 各模型对应的数据库操作实现
|   |
|   |-- /db               # 数据库连接与ORM模型定义
|   |   |-- base.py       # SQLAlchemy引擎和会话(Session)创建，负责数据库连接管理
|   |   `-- models.py     # 所有数据库表的ORM模型定义 (User, Dataset, etc.)
|   |
|   |-- /ml_models        # 存放纯粹的AI模型Python定义 (如U-Net架构)
|   |   `-- unet_with_cbam.py
|   |
|   |-- /schemas          # Pydantic数据模型层 (用于API数据验证和序列化)
|   |   |-- __init__.py   # 导出所有schema
|   |   `-- user.py, dataset.py, ... # 每个ORM模型对应一组Pydantic Schema
|   |
|   |-- /services         # 业务逻辑服务层 (处理复杂业务逻辑和后台任务)
|   |   |-- /model_runners # 具体的模型推理器实现，负责加载和运行AI模型
|   |   |   `-- unet_cbam_runner.py
|   |   |-- camera_service.py # (单例) 管理相机连接、状态和参数
|   |   |-- acquisition_service.py # (单例) 管理标定和数据采集流程
|   |   |-- image_processor.py # 图像批量预处理后台任务服务
|   |   |-- inference_runner.py # 模型批量推理后台任务服务
|   |   `-- model_runner.py # AI模型推理器的抽象基类和工厂函数
|   |
|   `-- main.py           # FastAPI应用入口，挂载所有路由和中间件(CORS)
|
|-- /uploads              # 所有用户上传文件的根目录 (通常在.gitignore中排除)
|-- .env                  # 环境变量文件 (敏感信息，应在.gitignore中排除)
`-- requirements.txt      # Python依赖列表
          </code></pre>
        </el-card>

        <h4>文件关系与数据流：</h4>
        <p>
          一个典型的请求处理流程如下：
        </p>
        <ol>
          <li>**请求入口：** 客户端请求首先到达 <code>app/api/routers</code> 中定义的API端点。</li>
          <li>**依赖注入与认证：** 路由函数通过 <code>app/api/deps.py</code> 进行依赖注入（如获取数据库会话）和用户认证（通过 <code>app/core/security.py</code> 验证JWT Token）。</li>
          <li>**数据验证与序列化：** 传入的请求数据会通过 <code>app/schemas</code> 中定义的Pydantic模型进行验证；返回响应时，数据也会根据Schema进行序列化。</li>
          <li><strong>数据库操作：：</strong> 对于涉及数据库的请求，路由会调用 <code>app/crud</code> 中对应的函数执行数据库的增、删、改、查操作。<code>crud</code> 层依赖 <code>app/db/models.py</code> 定义的ORM模型和 <code>app/db/base.py</code> 提供的数据库会话。</li>
          <li><strong>业务逻辑处理：：</strong> 对于复杂的业务流程（如图像预处理、模型推理、相机控制），路由会调用 <code>app/services</code> 中相应的服务函数。这些服务可能进一步调用 <code>crud</code> 进行数据持久化，或调用 <code>app/ml_models</code> 中定义的AI模型（通过 <code>app/services/model_runners</code> 封装）。</li>
          <li><strong>应用启动：：</strong> <code>app/main.py</code> 是FastAPI应用的启动文件，它负责注册所有 <code>app/api/routers</code> 中定义的路由，并配置CORS等中间件，是整个后端服务的入口。</li>
        </ol>

        <h3>3.2 API 接口说明 (`/api/v1/...`)</h3>
        <p>
          以下是后端服务提供的主要API接口列表，详细描述了每个端点的功能、请求方法和访问权限。
        </p>
        <el-alert
            title="API接口使用提示："
            description="通过这些接口，前端应用可以与后端服务进行数据交互，例如用户登录、上传数据集、启动AI推理任务等。"
            type="success"
            show-icon
            :closable="false"
        />

        <el-table :data="apiEndpoints" style="width: 100%; margin-top: 20px;" border>
          <el-table-column prop="endpoint" label="端点 (Endpoint)" width="200"></el-table-column>
          <el-table-column prop="method" label="方法 (Method)" width="120"></el-table-column>
          <el-table-column prop="description" label="描述 (Description)"></el-table-column>
          <el-table-column prop="permission" label="权限 (Permission)" width="120"></el-table-column>
        </el-table>
        <el-divider />

        <!-- 4. 前端 (Vue.js) 详细说明 -->
        <h2 id="frontend-details">4. 前端应用详解</h2>
        <el-alert
            title="前端应用基于Vue.js构建，采用组件化开发，提供直观的用户交互界面。"
            type="info"
            show-icon
            :closable="false"
        />

        <h3>4.1 目录结构与核心文件解析</h3>
        <p>
          前端代码结构清晰，便于开发和维护。
        </p>
        <el-card class="code-card">
          <pre><code>
/defect-detection-frontend
|-- /src
|   |-- /api                 # API请求封装层
|   |   |-- index.js         # Axios实例初始化、拦截器配置 (如添加认证Token)
|   |   `-- auth.js, datasets.js, ... # 按功能模块封装API请求函数
|   |
|   |-- /assets              # 静态资源 (图片, logo等)
|   |
|   |-- /router              # Vue Router配置
|   |   `-- index.js         # 定义所有页面路由、导航守卫 (如认证检查)
|   |
|   |-- /store               # Pinia状态管理
|   |   |-- user.js          # 管理用户认证Token、用户信息、角色等全局状态
|   |   `-- processing.js    # 管理异步处理任务的轮询状态和进度
|   |
|   |-- /utils               # 工具函数集合
|   |   `-- eventBus.js      # 用于跨组件通信的事件总线 (基于mitt库)
|   |
|   |-- /views               # 页面级组件 (每个文件代表一个独立的功能页面)
|   |   |-- Login.vue        # 登录页面
|   |   |-- MainLayout.vue   # 登录后的主布局 (包含侧边栏和顶栏)
|   |   |-- Dashboard.vue    # 系统总览/欢迎页
|   |   |-- Hardware.vue     # 硬件控制与数据采集页
|   |   |-- Datasets.vue     # 数据集管理页
|   |   |-- Models.vue       # 模型管理与发起推理页
|   |   |-- InferenceJobs.vue# 推理任务结果展示页
|   |   |-- SingleInference.vue# 单图推理页
|   |   `-- UserManagement.vue # (管理员)用户管理页
|   |
|   |-- App.vue              # 根组件，挂载 router-view
|   `-- main.js              # 应用入口，初始化Vue、Pinia、Router、ElementPlus等
|
`-- package.json             # 项目依赖和脚本配置
          </code></pre>
        </el-card>

        <h4>核心流程与文件关系：</h4>
        <p>
          前端应用的运行流程和各模块间的协作关系：
        </p>
        <ol>
          <li><strong>应用初始化：：</strong> <code>main.js</code> 是应用的入口文件，负责初始化Vue实例、Pinia状态管理、Vue Router以及Element Plus UI库，并挂载根组件 <code>App.vue</code>。</li>
          <li><strong>路由管理：：</strong> <code>router/index.js</code> 定义了所有页面的路由规则，并通过导航守卫 (<code>beforeEach</code>) 检查用户登录状态，如果未登录则重定向到 <code>Login.vue</code> 页面。导航守卫会与 <code>store/user.js</code> 交互以获取用户认证信息。</li>
          <li><strong>用户认证：：</strong> <code>Login.vue</code> 页面处理用户登录逻辑，成功后调用 <code>userStore.login</code> action 将JWT Token和用户信息存储到 <code>store/user.js</code>。</li>
          <li><strong>主布局：：</strong> 登录成功后，系统会渲染 <code>views/MainLayout.vue</code> 作为主框架。它包含一个根据路由动态高亮的侧边栏菜单、一个显示用户信息的顶栏，以及一个用于显示子页面的 <code>&lt;router-view&gt;</code>。菜单项的可见性受 <code>userStore</code> 中的用户角色（`isAdmin`）控制。</li>
          <li><strong>功能页面交互：：</strong> 各功能页面（如 <code>Hardware.vue</code>, <code>Datasets.vue</code>）通过 <code>import { ... } from '@/api/...'</code> 调用 <code>src/api</code> 中封装的API函数与后端服务通信，并通过 <code>import { use...Store } from '@/store/...'</code> 与全局状态交互。</li>
          <li><strong>组件通信：：</strong> <code>src/utils/eventBus.js</code> 提供了跨组件通信的机制，允许不直接相关的组件之间发送和接收事件。</li>
        </ol>

        <h3>4.2 页面组件功能详解</h3>
        <p>
          以下是主要页面组件的功能描述：
        </p>
        <ul>
          <li><strong>`Login.vue`</strong>: 提供用户登录表单，负责用户认证。成功登录后，将用户认证信息存储到全局状态。</li>
          <li><strong>`MainLayout.vue`</strong>: 系统的整体布局骨架。包含侧边导航菜单、顶部信息栏和内容显示区域。菜单项的显示会根据用户角色进行动态调整。</li>
          <li><strong>`Hardware.vue`</strong>: 硬件交互控制中心。
            <ul>
              <li>通过WebSocket实时显示视频流。</li>
              <li>提供API接口调用，实现相机参数（如亮度、曝光）的获取与设置（使用Element Plus的 `El-Slider`）。</li>
              <li>支持相机参数配置文件的保存与加载（利用 `ElMessageBox.prompt` 和 `El-Select`）。</li>
              <li>实现单帧图像采集功能（通过独立的 `El-Dialog`）。</li>
              <li>提供连续数据采集的启动与停止功能（通过 `ElMessageBox.prompt`）。</li>
              <li>包含一个侧拉抽屉组件（`El-Drawer`），以分步向导（`El-Steps`）的形式引导用户完成相机标定流程。</li>
            </ul>
          </li>
          <li><strong>`Datasets.vue`</strong>: 数据集管理中心。
            <ul>
              <li>使用 `El-Table` 展示数据集列表。</li>
              <li>通过 `El-Dialog` 和 `El-Upload` 实现数据集文件的上传。</li>
              <li>使用 `El-Switch` 在表格内直接切换数据集的公开状态。</li>
              <li>通过另一个 `El-Dialog` 构建并启动图像预处理任务流程。</li>
              <li>提供数据集内容的图片浏览功能（通过 `El-Dialog` 和 `El-Image`）。</li>
            </ul>
          </li>
          <li><strong>`Models.vue`</strong>: AI模型管理与推理任务发起中心。功能类似于 `Datasets.vue`，用于模型的增删查，并集成了发起推理任务的表单对话框。</li>
          <li><strong>`InferenceJobs.vue`</strong>: 展示所有推理任务的状态与进度。核心功能是使用 `setInterval` 定期轮询后端API，并利用 `El-Progress` 实时更新任务进度条。</li>
          <li><strong>`SingleInference.vue`</strong>: 提供即时AI推理能力的演示。用户可上传单张图片并选择AI模型，页面将并排展示原图和后端API返回的推理结果图。</li>
          <li><strong>`UserManagement.vue`</strong>: 专为管理员设计的页面，提供用户账户的基础管理功能（增、删、查）。</li>
        </ul>
        <el-divider />

        <!-- 5. 扩展与维护 (管理员可见) -->
        <h2 id="extend-maintain" v-if="userStore.isAdmin">5. 扩展与维护</h2>
        <el-alert
            v-if="userStore.isAdmin"
            title="本章节指导如何对系统进行功能扩展和日常维护，确保系统持续演进和稳定运行。"
            type="success"
            show-icon
            :closable="false"
        />

        <h3 v-if="userStore.isAdmin">5.1 添加新的功能模块 (示例：数据统计图表)</h3>
        <p v-if="userStore.isAdmin">当需要为系统添加全新功能时，通常需要同时修改后端和前端代码。</p>
        <ol v-if="userStore.isAdmin">
          <li>
            <strong>后端服务部分：：</strong>
            <ul>
              <li><strong>定义API接口：：</strong> 在 `app/api/routers` 目录下创建新的路由文件（例如 `statistics.py`），定义新功能的API端点和请求处理逻辑。</li>
              <li><strong>实现业务逻辑：：</strong> 如果涉及复杂的数据处理或计算，在 `app/services` 目录下创建新的服务文件（例如 `statistics_service.py`），封装具体的业务逻辑。</li>
              <li><strong>定义数据模型：：</strong> 在 `app/schemas` 目录下为新功能的数据结构定义Pydantic Schema，用于请求体验证和响应数据序列化。</li>
              <li><strong>更新主应用：：</strong> 在 `app/main.py` 中导入并注册新的路由文件，使其生效。</li>
            </ul>
          </li>
          <li>
            <strong>前端应用部分：：</strong>
            <ul>
              <li><strong>创建页面组件：：</strong> 在 `src/views` 目录下创建新的Vue组件文件（例如 `Statistics.vue`），用于构建新功能的UI界面。</li>
              <li><strong>封装API请求：：</strong> 在 `src/api` 目录下创建新的API服务模块（例如 `statistics.js`），封装调用后端新API的函数。</li>
              <li><strong>配置路由：：</strong> 在 `src/router/index.js` 中为新的页面组件添加路由规则，定义其访问路径。</li>
              <li><strong>更新导航菜单：：</strong> 在 `src/views/MainLayout.vue` 中修改侧边栏菜单，添加新的菜单项，使用户可以访问新功能页面。</li>
              <li><strong>实现页面逻辑：：：</strong> 在新的Vue组件中，调用 `src/api` 中封装的函数获取数据，并使用Element Plus或其他图表库（如ECharts）进行数据可视化。</li>
            </ul>
          </li>
        </ol>

        <h3 v-if="userStore.isAdmin">5.2 集成新的AI模型 (示例：新的缺陷识别模型)</h3>
        <p v-if="userStore.isAdmin">集成新的AI模型通常涉及后端模型文件的管理和推理逻辑的适配。</p>
        <ol v-if="userStore.isAdmin">
          <li>
            <strong>准备AI模型文件：：</strong> 确保您拥有训练好的AI模型文件（例如 `.pt`, `.onnx` 等格式）以及任何相关的模型定义代码。
          </li>
          <li>
            <strong>后端服务部分：：</strong>
            <ul>
              <li><strong>放置模型定义代码：：</strong> 如果模型有特定的Python定义，将其放置在 `app/ml_models` 目录下。</li>
              <li><strong>创建模型推理器：：</strong> 在 `app/services/model_runners` 目录下创建新的模型推理器实现文件（例如 `new_model_runner.py`）。该文件应负责加载您的新AI模型，并实现其推理逻辑。建议继承自 `model_runner.py` 中定义的抽象基类，以保持接口一致性。</li>
              <li><strong>更新模型管理API：：</strong> 检查 `app/api/routers/models.py`，确保系统能够识别和管理新的模型类型。</li>
              <li><strong>更新推理服务：：</strong> 在 `app/services/inference_runner.py` 中，确保批量推理服务能够正确识别并调用您的新模型推理器。</li>
              <li><strong>（管理员操作）上传模型文件：：</strong> 后端服务启动后，管理员可以通过 `/models/upload` API接口将实际的模型文件上传到系统中，系统会将其存储到指定目录并记录到数据库。</li>
            </ul>
          </li>
          <li>
            <strong>前端应用部分：：</strong>
            <ul>
              <li><strong>更新模型选择列表：：</strong> 在 `Models.vue` 和 `SingleInference.vue` 页面中，获取模型列表时，新的模型应自动显示在下拉选择框中。如果需要特殊展示或处理，可能需要修改相关页面逻辑。</li>
              <li><strong>测试推理功能：：</strong> 验证新的AI模型在单张图像推理和批量推理任务中都能被正确选择和使用，并返回预期结果。</li>
            </ul>
          </li>
        </ol>
        <el-divider v-if="userStore.isAdmin" />

        <!-- 6. 常见问题 -->
        <h2 id="faq">6. 常见问题 (FAQ)</h2>
        <el-collapse v-model="activeFaq" accordion>
          <el-collapse-item title="Q1: 后端服务启动后，为何无法访问 `/docs` 页面？" name="1">
            <div>
              <strong>A:</strong>
              <ol>
                <li><strong>检查URL：：</strong> 确保访问地址为 `http://127.0.0.1:8000/docs`。</li>
                <li><strong>检查后端日志：：</strong> 查看后端服务运行的命令行终端，确认是否有报错信息，以及是否显示“Application startup complete.”。</li>
                <li><strong>端口占用：：</strong> 8000端口可能被其他程序占用。尝试使用 `uvicorn app.main:app --reload --port 8001` 启动服务，并访问 `http://127.0.0.1:8001/docs`。</li>
                <li><strong>防火墙：：</strong> 检查系统防火墙设置，确保未阻止对8000端口的访问。</li>
              </ol>
            </div>
          </el-collapse-item>
          <el-collapse-item title="Q2: 前端页面显示空白或控制台报错，如何排查？" name="2">
            <div>
              <strong>A:</strong>
              <ol>
                <li><strong>检查前端终端：：</strong> 查看运行前端命令的终端，确认是否有编译错误或运行时错误信息。</li>
                <li><strong>浏览器开发者工具：：</strong> 按 `F12` 打开浏览器开发者工具，切换到“Console”（控制台）标签页，检查是否有红色错误信息。</li>
                <li><strong>后端服务状态：：</strong> 确保后端服务已成功启动且无报错，前端需要与后端进行API通信。</li>
                <li><strong>`baseURL` 配置：：</strong> 确认 `src/api/index.js` 中的 `baseURL` 是否正确指向后端服务地址。</li>
                <li><strong>依赖完整性：：</strong> 重新运行 `npm install` 确保所有前端依赖库已完整安装。</li>
              </ol>
            </div>
          </el-collapse-item>
          <el-collapse-item title="Q3: 登录时提示用户名或密码错误，即使确认输入正确？" name="3">
            <div>
              <strong>A:</strong>
              <ol>
                <li><strong>数据库连接：：</strong> 检查数据库连接是否正常，以及数据库中是否存在您尝试登录的用户记录。</li>
                <li><strong>密码加密：：</strong> 密码在数据库中是加密存储的。如果您直接在数据库中修改了密码，请注意密码需要通过后端提供的注册或修改密码接口进行设置，以确保正确加密。</li>
                <li><strong>后端日志：：</strong> 检查后端服务的日志，查找有关登录失败的详细错误信息，这有助于定位问题。</li>
              </ol>
            </div>
          </el-collapse-item>
        </el-collapse>
        <el-divider />

        <el-alert
            title="总结"
            description="本开发者文档提供了系统从部署到扩展的全面指南。希望这份文档能帮助您快速理解项目架构，高效进行开发和维护工作。"
            type="success"
            show-icon
            :closable="false"
            style="margin-top: 30px;"
        />
      </el-card>
    </el-main>
  </el-container>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import {useUserStore} from "../store/user.js";

// 修正：直接导入Element Plus图标组件名称
import {
  Document, // 对应 el-icon-document
  Star,     // 对应 el-icon-star
  Setting,  // 对应 el-icon-setting
  Monitor,  // 对应 el-icon-monitor
  Plus,     // 对应 el-icon-plus
  QuestionFilled // 对应 el-icon-question-filled
} from '@element-plus/icons-vue';

const activeSection = ref('overview'); // 默认激活的菜单项
const userStore = useUserStore(); // 获取用户store实例

// API接口数据
const apiEndpoints = ref([
  { endpoint: '/token', method: 'POST', description: '用户登录。接收`username`和`password`，返回JWT Token。', permission: '公开' },
  { endpoint: '/users/', method: 'POST', description: '(管理员)创建用户。', permission: '管理员' },
  { endpoint: '/users/', method: 'GET', description: '(管理员)获取所有用户列表。', permission: '管理员' },
  { endpoint: '/users/{user_id}', method: 'DELETE', description: '(管理员)删除指定用户。', permission: '管理员' },
  { endpoint: '/users/me', method: 'GET', description: '获取当前登录用户的个人信息。', permission: '已登录用户' },
  { endpoint: '/datasets/upload', method: 'POST', description: '上传数据集。接收`name`, `description`, `is_public`和`.zip`文件。', permission: '已登录用户' },
  { endpoint: '/datasets/', method: 'GET', description: '获取当前用户的所有数据集列表。', permission: '已登录用户' },
  { endpoint: '/datasets/{id}', method: 'DELETE', description: '删除数据集及其所有文件。', permission: '数据集所有者' },
  { endpoint: '/datasets/{id}/download', method: 'GET', description: '下载数据集的`.zip`压缩包。', permission: '数据集所有者' },
  { endpoint: '/datasets/{id}/browse', method: 'GET', description: '获取数据集中所有图片的URL列表以供前端浏览。', permission: '数据集所有者' },
  { endpoint: '/datasets/{id}/public', method: 'PATCH', description: '更新数据集的公开状态。', permission: '数据集所有者' },
  { endpoint: '/processing/jobs', method: 'POST', description: '创建并启动图像预处理任务。接收源数据集ID和处理步骤。', permission: '已登录用户' },
  { endpoint: '/processing/jobs/{id}', method: 'GET', description: '查询指定预处理任务的状态和进度。', permission: '任务提交者' },
  { endpoint: '/hardware/cameras', method: 'GET', description: '(模拟)列出可用的相机。', permission: '已登录用户' },
  { endpoint: '/hardware/camera/connect/{id}', method: 'POST', description: '连接相机。', permission: '已登录用户' },
  { endpoint: '/hardware/camera/disconnect', method: 'POST', description: '断开相机。', permission: '已登录用户' },
  { endpoint: '/hardware/camera/parameters', method: 'GET/PUT', description: '获取/设置当前相机的所有参数。', permission: '已登录用户' },
  { endpoint: '/hardware/camera/profiles', method: 'GET', description: '获取所有已保存的相机参数配置文件列表。', permission: '已登录用户' },
  { endpoint: '/hardware/camera/profiles/{name}/save', method: 'POST', description: '保存当前相机参数为配置文件。', permission: '已登录用户' },
  { endpoint: '/hardware/camera/profiles/{name}/load', method: 'POST', description: '从配置文件加载并应用参数。', permission: '已登录用户' },
  { endpoint: '/hardware/calibration/start', method: 'POST', description: '开始相机标定流程，准备捕捉帧。', permission: '已登录用户' },
  { endpoint: '/hardware/calibration/capture', method: 'POST', description: '捕捉一张用于标定的图像。', permission: '已登录用户' },
  { endpoint: '/hardware/calibration/run', method: 'POST', description: '运行标定算法并返回结果。', permission: '已登录用户' },
  { endpoint: '/hardware/calibration/cancel', method: 'POST', description: '取消当前的标定流程。', permission: '已登录用户' },
  { endpoint: '/hardware/acquisition/start', method: 'POST', description: '开始连续数据采集，创建新数据集。', permission: '已登录用户' },
  { endpoint: '/hardware/acquisition/stop', method: 'POST', description: '停止连续数据采集。', permission: '已登录用户' },
  { endpoint: '/hardware/acquisition/capture-single/{id}', method: 'POST', description: '采集单帧图像到指定的数据集。', permission: '已登录用户' },
  { endpoint: '/models/upload', method: 'POST', description: '(管理员)上传AI模型文件。', permission: '管理员' },
  { endpoint: '/models/', method: 'GET', description: '获取所有可用的AI模型列表。', permission: '已登录用户' },
  { endpoint: '/models/{id}', method: 'DELETE', description: '(管理员)删除AI模型。', permission: '管理员' },
  { endpoint: '/inference/single', method: 'POST', description: '单张图像推理。接收图片和模型ID，立即返回结果URL。', permission: '已登录用户' },
  { endpoint: '/inference/jobs', method: 'POST', description: '创建并启动批量推理任务。', permission: '已登录用户' },
  { endpoint: '/inference/jobs', method: 'GET', description: '获取当前用户的所有推理任务列表。', permission: '已登录用户' },
  { endpoint: '/inference/jobs/{id}', method: 'GET', description: '查询指定推理任务的状态和进度。', permission: '任务提交者' },
  { endpoint: '/inference/jobs/{id}', method: 'DELETE', description: '删除推理任务及其结果文件。', permission: '任务提交者' },
  { endpoint: '/inference/jobs/{id}/browse', method: 'GET', description: '获取推理结果中所有图片的URL列表以供前端浏览。', permission: '任务提交者' },
]);

const activeFaq = ref('1'); // 默认展开第一个FAQ

// 处理菜单选择，并滚动到对应ID
const handleMenuSelect = (index) => {
  activeSection.value = index;
  const element = document.getElementById(index);
  if (element) {
    element.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
};

// 页面加载时，如果URL中有hash，则滚动到对应位置
onMounted(() => {
  if (window.location.hash) {
    const sectionId = window.location.hash.substring(1);
    activeSection.value = sectionId;
    const element = document.getElementById(sectionId);
    if (element) {
      // 使用 setTimeout 确保页面渲染完成后再滚动
      setTimeout(() => {
        element.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 100);
    }
  }
});
</script>

<style scoped>
.documentation-container {
  height: calc(100dvh - 60px);
  display: flex;
  background-color: var(--color-bg);
}

.documentation-aside {
  background-color: #ffffff;
  padding-top: 20px;
  box-shadow: 2px 0 6px rgba(0, 21, 41, 0.08);
  overflow-y: auto; /* 允许侧边栏滚动 */
}

.el-menu-vertical-demo {
  border-right: none; /* 移除Element Plus菜单默认右边框 */
}

.el-menu-item {
  font-size: 16px;
  height: 50px;
  line-height: 50px;
}

.el-menu-item.is-active {
  background-color: #ecf5ff;
  color: #1e6fff;
}

.documentation-main {
  padding: 20px;
  overflow-y: auto; /* 允许主内容区滚动 */
}

.box-card {
  margin-bottom: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.card-header {
  font-size: 24px;
  font-weight: bold;
  color: #333;
  text-align: center;
  padding: 10px 0;
  background-image: linear-gradient(to right, #a1c4fd, #c2e9fb);
  -webkit-background-clip: text;
  color: transparent;
}

h2 {
  font-size: 28px;
  color: #303133;
  margin-top: 40px;
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 2px solid #1e6fff;
  display: flex;
  align-items: center;
}

h2::before {
  content: "💡"; /* 可以替换为其他有趣的图标 */
  margin-right: 10px;
  font-size: 24px;
}

h3 {
  font-size: 22px;
  color: #606266;
  margin-top: 30px;
  margin-bottom: 15px;
  border-left: 5px solid #1e6fff;
  padding-left: 10px;
}

h4 {
  font-size: 18px;
  color: #909399;
  margin-top: 20px;
  margin-bottom: 10px;
}

p, ul, ol {
  line-height: 1.8;
  color: #606266;
  font-size: 16px;
  margin-bottom: 10px;
}

ul, ol {
  padding-left: 25px;
}

li {
  margin-bottom: 5px;
}

.el-alert {
  margin-bottom: 20px;
  font-size: 16px;
}

.code-card {
  background-color: #f5f7fa;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  padding: 15px;
  margin: 15px 0;
  overflow-x: auto; /* 防止代码过长溢出 */
}

.code-card code {
  font-family: 'Cascadia Code', 'Fira Code', monospace;
  font-size: 14px;
  color: #303133;
  display: block; /* 确保代码块内的换行 */
  white-space: pre-wrap; /* 允许自动换行 */
}

.el-table {
  margin-top: 20px;
  font-size: 15px;
}

.el-link {
  font-size: 16px;
}

.el-collapse-item__header {
  font-size: 18px;
  font-weight: bold;
  color: #303133;
}

.el-collapse-item__content {
  font-size: 16px;
  line-height: 1.8;
  color: #606266;
}
</style>