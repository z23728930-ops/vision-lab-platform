import { createRouter, createWebHistory } from 'vue-router';
import { useUserStore } from '../store/user';
import { ElMessage } from 'element-plus'; // 导入 ElMessage

// 导入所有视图组件
import Login from '../views/Login.vue';
import Register from '../views/Register.vue';
import MainLayout from '../views/MainLayout.vue';
import Dashboard from '../views/Dashboard.vue';
import Hardware from "../views/Hardware.vue";
import Datasets from "../views/Datasets.vue";
import Models from "../views/Models.vue";
import SingleInference from "../views/SingleInference.vue";
import InferenceJobs from "../views/InferenceJobs.vue";
import UserManagement from '../views/UserManagement.vue';
import ProjectDocumentation from "../views/ProjectDocumentation.vue";
import AnnotationTool from "@/views/AnnotationTool.vue";
import UserSettings from "@/views/UserSettings.vue";
import RealtimeInference from "@/views/RealtimeInference.vue";
import ImageProcessingCenter from "@/views/ImageProcessingCenter.vue";
// 导入新增的推理中心占位组件
import InferenceCenterPlaceholder from "@/views/InferenceCenterPlaceholder.vue";
import AiAssistant from "@/views/AiAssistant.vue";
import TrainingMentor from "@/views/TrainingMentor.vue";
import IndustryCases from "@/views/IndustryCases.vue";
import UserFeedback from "@/views/UserFeedback.vue";

const routes = [
    {
        path: '/login',
        name: 'Login',
        component: Login,
    },
    {
        path: '/register',
        name: 'Register',
        component: Register,
    },
    {
        path: '/',
        component: MainLayout, // MainLayout 作为所有内部路由的父组件
        redirect: '/dashboard', // 默认重定向到仪表盘
        meta: { requiresAuth: true }, // 所有子路由都需要认证
        children: [
            {
                path: 'dashboard',
                name: 'Dashboard',
                component: Dashboard,
                meta: {title: '系统总览'}
            },
            {
                path: 'hardware',
                name: 'Hardware',
                component: Hardware,
                meta: { title: '硬件控制' }
            },
            {
                path: 'datasets',
                name: 'Datasets',
                component: Datasets,
                meta: { title: '数据管理' }
            },
            {
                path: '/datasets/:datasetId/process', // 预处理页面路由
                name: 'ImageProcessingCenter',
                component: ImageProcessingCenter,
                props: true // 允许路由参数作为组件props
            },
            {
                path: 'models',
                name: 'Models',
                component: Models,
                meta: { title: '模型管理' }
            },
            { path: 'assistant', name: 'AiAssistant', component: AiAssistant, meta: { title: 'AI质检助手', requiresAuth: true } },
            { path: 'training-mentor', name: 'TrainingMentor', component: TrainingMentor, meta: { title: 'AI实训导师', requiresAuth: true } },
            { path: 'industry-cases', name: 'IndustryCases', component: IndustryCases, meta: { title: '工业场景案例', requiresAuth: true } },
            { path: 'feedback', name: 'UserFeedback', component: UserFeedback, meta: { title: '用户评价', requiresAuth: true } },
            {
                path: 'inference', // 路由路径，相对于父路由 '/'
                name: 'InferenceCenter', // 路由名称
                component: InferenceCenterPlaceholder, // 使用占位组件
                meta: { title: '推理中心', requiresAuth: true }, // 必须有 title 才能在面包屑中显示
                redirect: '/inference/inference-jobs', // 默认重定向到第一个子路由
                children: [
                    {
                        path: 'inference-jobs', // 相对于父路由 '/inference'
                        name: 'InferenceJobs',
                        component: InferenceJobs,
                        meta: { title: '推理任务' }
                    },
                    {
                        path: 'single-inference', // 相对于父路由 '/inference'
                        name: 'SingleInference',
                        component: SingleInference,
                        meta: { title: '单图推理' }
                    },
                    {
                        path: 'realtime-inference', // 相对于父路由 '/inference'
                        name: 'RealtimeInference',
                        component: RealtimeInference,
                        meta: { title: '在线推理' }
                    },
                ]
            },
            {
                path: 'annotation/:datasetId/:imageId?', // datasetId 必选，imageId 可选
                name: 'AnnotationTool',
                component: AnnotationTool,
                meta: { title: '数据标注', requiresAuth: true }
            },
            {
                path: 'user-management',
                name: 'UserManagement',
                component: UserManagement,
                meta: { title: '用户管理', requiresAuth: true, requiresAdmin: true }
            },
            {
                path: 'user-settings',
                name: 'UserSettings',
                component: UserSettings,
                meta: { title: '个人设置', requiresAuth: true }
            },
            {
                path: 'documentation',
                name: 'ProjectDocumentation',
                component: ProjectDocumentation,
                meta: { requiresAuth: true, title: '项目文档' }
            }
        ],
    },
];

const router = createRouter({
    history: createWebHistory(),
    routes,
});

// 全局前置路由守卫
router.beforeEach(async (to, from, next) => {
    const userStore = useUserStore();
    let isLoggedIn = userStore.isLoggedIn;
    let isAdmin = userStore.isAdmin;

    // 调试日志：帮助您在控制台追踪守卫的执行流程
    console.log(`%c[Router Guard] Navigating from ${from.path} to ${to.path}`, 'color: #1a73e8; font-weight: bold;');
    console.log(`%c[Router Guard] Initial isLoggedIn: ${isLoggedIn}, userInfo:`, 'color: #1a73e8;', userStore.userInfo);

    // 首次进入或刷新页面时，如果已登录但没有用户信息，则获取
    // 增加对 userInfo 是否为空对象或关键属性缺失的检查
    if (isLoggedIn && (!userStore.userInfo || Object.keys(userStore.userInfo).length === 0 || !userStore.userInfo.username)) {
        console.log("%c[Router Guard] Attempting to fetch user info...", 'color: #f7931e;');
        try {
            await userStore.getUserInfo();
            // 获取用户信息成功后，重新评估 isLoggedIn 和 isAdmin
            isLoggedIn = userStore.isLoggedIn;
            isAdmin = userStore.isAdmin;
            console.log("%c[Router Guard] User info fetched successfully. New isLoggedIn:", 'color: #34a853;', isLoggedIn, "isAdmin:", isAdmin);
        } catch (error) {
            console.error("%c[Router Guard] Failed to fetch user info:", 'color: #ea4335;', error);
            ElMessage.error("获取用户信息失败，请重新登录。");
            // 如果获取用户信息失败，认为用户未登录，并重定向到登录页
            userStore.logout(); // 清除本地登录状态
            next({ name: 'Login' });
            return; // 阻止继续执行后续的 next()
        }
    }

    // 调试日志：在所有状态更新后再次打印
    console.log(`%c[Router Guard] Final isLoggedIn: ${isLoggedIn}, isAdmin: ${isAdmin}`, 'color: #1a73e8;');

    if (to.meta.requiresAuth && !isLoggedIn) {
        // 如果需要认证且用户未登录，跳转到登录页
        console.log("%c[Router Guard] Redirecting to Login: requiresAuth but not logged in.", 'color: #ea4335;');
        next({ name: 'Login' });
        return; // 确保在重定向后停止执行
    } else if (to.meta.requiresAdmin && !isAdmin) {
        // 如果需要管理员权限但当前用户不是，则跳转到无权限页面或首页
        console.log("%c[Router Guard] Redirecting to Dashboard: requiresAdmin but not admin.", 'color: #ea4335;');
        ElMessage.error("您没有权限访问此页面！"); // 提示用户无权限
        next({ name: 'Dashboard' }); // 或者创建一个专门的403页面
        return; // 确保在重定向后停止执行
    } else if (isLoggedIn && ['Login', 'Register'].includes(to.name)) {
        // 如果用户已登录，但又要去登录页，则直接把他导向主页
        console.log("%c[Router Guard] Redirecting to Dashboard: already logged in, trying to access Login.", 'color: #4285f4;');
        next({ name: 'Dashboard' });
        return; // 确保在重定向后停止执行
    } else {
        // 其他所有情况，直接放行
        console.log("%c[Router Guard] Proceeding with navigation.", 'color: #34a853;');
        next();
        return; // 确保在放行后停止执行
    }
});

export default router;
