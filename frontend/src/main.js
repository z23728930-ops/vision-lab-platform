import { createApp } from 'vue'
import App from './App.vue'
import router from './router' // 导入路由
import { createPinia } from 'pinia' // 导入 Pinia
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import './styles/variables.scss'
import './styles/global.scss'
import './style.css'
import 'fabric'
import {useCameraStore} from "@/store/camera.js";

const app = createApp(App)
const pinia = createPinia()// 创建 Pinia 实例


app.use(pinia) // 使用 Pinia
// 在 Pinia 初始化后，立即获取 cameraStore 实例并调用 checkInitialStatus
// 注意：在 setup() 外部使用 useStore 需要传入 pinia 实例
const cameraStore =   useCameraStore(pinia);
cameraStore.checkInitialStatus();


app.use(router) // 使用路由
app.use(ElementPlus) // 使用 Element Plus

app.mount('#app')
