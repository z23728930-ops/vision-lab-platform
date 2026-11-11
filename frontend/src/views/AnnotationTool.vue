<template>
  <el-container class="annotation-container">
    <!-- 侧边栏：数据集/图片选择与标签管理 -->
    <el-aside width="280px" class="annotation-aside">
      <el-card shadow="never" class="aside-card">
        <template #header>
          <div class="card-header">
            <span>数据集与图片</span>
          </div>
        </template>
        <el-select v-model="selectedDatasetId" placeholder="选择数据集" @change="loadDatasetImages" style="width: 100%; margin-bottom: 5px;">
          <el-option v-for="ds in datasets" :key="ds.id" :label="ds.name" :value="ds.id" />
        </el-select>

        <el-divider v-if="images.length">图片列表 ({{ images.length }})</el-divider>
        <el-scrollbar v-if="images.length" height="calc(100vh - 350px - 20px)"> <!-- 调整高度以适应新间距 -->
          <div class="image-list">
            <div
                v-for="img in images"
                :key="img.id"
                :class="['image-list-item', { 'is-active': currentImage && currentImage.id === img.id }]"
                @click="selectImage(img)"
            >
              <el-image :src="getImageThumbnailUrl(img)" fit="cover" class="image-thumbnail" />
              <span class="image-filename" :title="img.filename">{{ img.filename }}</span>
            </div>
          </div>
        </el-scrollbar>
        <el-empty v-else description="请选择数据集或数据集中无图片"></el-empty>
      </el-card>

      <el-card shadow="never" class="aside-card" style="margin-top: 5px;">
        <template #header>
          <div class="card-header">
            <span>标签管理</span>
            <el-button type="primary" link :icon="Plus" @click="addLabelDialogVisible = true">添加</el-button>
          </div>
        </template>
        <el-empty v-if="labels.length === 0" description="暂无标签"></el-empty>
        <el-scrollbar v-else height="200px">
          <div class="label-list">
            <div v-for="(label, index) in labels" :key="label.name" class="label-item">
              <el-tag :color="label.color" effect="dark" class="label-tag">{{ label.name }}</el-tag>
              <el-button type="danger" link :icon="Delete" @click="removeLabel(index)">删除</el-button>
            </div>
          </div>
        </el-scrollbar>
      </el-card>
    </el-aside>

    <!-- 主内容区：标注画布与工具栏 -->
    <el-main class="annotation-main">
      <el-card shadow="never" class="main-card">
        <template #header>
          <div class="card-header header-with-toolbar">
            <span class="current-image-filename" :title="currentImage?.filename || '未选择'">当前图片: {{ currentImage?.filename || '未选择' }}</span>
            <div class="toolbar">
              <el-radio-group v-model="annotationMode" size="small" :disabled="!currentImage || !canEditDataset">
                <el-radio-button value="view" :icon="View">查看</el-radio-button>
                <el-radio-button value="bbox" :icon="Crop">矩形框</el-radio-button>
                <el-radio-button value="polygon" :icon="Scissor">多边形</el-radio-button>
                <el-radio-button value="point" :icon="Aim">点</el-radio-button>
              </el-radio-group>
              <el-select v-model="currentLabel" placeholder="选择标签" size="small" style="width: 120px;" :disabled="!currentImage || !canEditDataset || labels.length === 0">
                <el-option v-for="label in labels" :key="label.name" :label="label.name" :value="label.name" />
              </el-select>
              <el-button-group>
                <el-button :icon="ZoomIn" size="small" @click="changeZoom(0.1)" :disabled="!currentImage" />
                <el-button size="small" @click="resetZoom" :disabled="!currentImage">{{ (currentZoomLevel * 100).toFixed(0) }}%</el-button>
                <el-button :icon="ZoomOut" size="small" @click="changeZoom(-0.1)" :disabled="!currentImage" />
              </el-button-group>
              <el-button type="primary" :icon="Check" @click="saveAnnotations" :loading="isSaving" :disabled="!currentImage || !canEditDataset || (!newAnnotations.length && !modifiedAnnotations.length && !deletedAnnotationIds.length)">保存标注</el-button>
              <el-button type="success" plain :icon="Check" @click="confirmNoDefect" :disabled="!currentImage || !canEditDataset">标记已检查</el-button>
              <el-button type="danger" :icon="Delete" @click="clearSelectedAnnotations" :disabled="!currentImage || !canEditDataset || (!fabricCanvasRef || fabricCanvasRef.getActiveObjects().length === 0)">删除选中</el-button>
              <el-button type="warning" :icon="Refresh" @click="resetAnnotations" :disabled="!currentImage || !canEditDataset || (!newAnnotations.length && !modifiedAnnotations.length && !deletedAnnotationIds.length)">重置修改</el-button>
            </div>
          </div>
        </template>

        <el-alert
            v-if="currentDataset && !canEditDataset"
            title="当前是公共数据集，只能查看，不能直接保存标注"
            description="请先复制为本小组的独立数据集，避免不同小组互相覆盖标注。"
            type="warning"
            :closable="false"
            show-icon
            class="readonly-alert"
        >
          <template #default>
            <el-button type="primary" size="small" :loading="isCloning" @click="cloneCurrentDataset">复制到我的数据集并开始标注</el-button>
          </template>
        </el-alert>

        <div class="canvas-wrapper" v-loading="isImageLoading">
          <canvas ref="annotationCanvas"></canvas>
          <el-empty v-if="!currentImage" description="请选择图片开始标注" class="canvas-empty"></el-empty>
        </div>
      </el-card>
    </el-main>
  </el-container>

  <!-- 添加标签对话框 -->
  <el-dialog v-model="addLabelDialogVisible" title="添加新标签" width="300px">
    <el-form :model="newLabelForm" :rules="labelRules" ref="labelFormRef">
      <el-form-item label="标签名称" prop="name">
        <el-input v-model="newLabelForm.name"></el-input>
      </el-form-item>
      <el-form-item label="标签颜色" prop="color">
        <el-color-picker v-model="newLabelForm.color"></el-color-picker>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="addLabelDialogVisible = false">取消</el-button>
      <el-button type="primary" @click="confirmAddLabel">添加</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, onMounted, watch, computed, onBeforeUnmount, nextTick } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Plus, Delete, View, Crop, Scissor, Aim, Check, Refresh, ZoomIn, ZoomOut } from '@element-plus/icons-vue';
import { fetchDatasets, fetchImagesByDataset, markImageReviewed, cloneDataset } from '../api/datasets';
import { useUserStore } from '../store/user';
import { fetchAnnotationsByImage, createBatchAnnotations, updateAnnotation, deleteBatchAnnotations } from '../api/annotations';

import apiClient from '../api';

import * as fabric from 'fabric';

const fabricLib = ref(null);


const route = useRoute();
const router = useRouter();
const userStore = useUserStore();

const datasets = ref([]);
const selectedDatasetId = ref(null);
const images = ref([]);
const currentImage = ref(null);
const isImageLoading = ref(false);
const isCloning = ref(false);
const currentDataset = computed(() => datasets.value.find(dataset => dataset.id === selectedDatasetId.value) || null);
const canEditDataset = computed(() => currentDataset.value?.owner_id === userStore.userInfo?.id || userStore.isAdmin);

const labels = ref([
  { name: 'defect_A', color: '#FF0000' },
  { name: 'defect_B', color: '#00FF00' },
  { name: 'defect_C', color: '#0000FF' },
]);
const currentLabel = ref(labels.value.length > 0 ? labels.value[0].name : '');
const addLabelDialogVisible = ref(false);
const newLabelForm = ref({ name: '', color: '#409EFF' });
const labelFormRef = ref(null);
const labelRules = {
  name: [{ required: true, message: '请输入标签名称', trigger: 'blur' }],
  color: [{ required: true, message: '请选择标签颜色', trigger: 'change' }],
};

// 标注画布与工具
const annotationMode = ref('view');
const annotationCanvas = ref(null);
const fabricCanvasRef = ref(null);
let resizeObserver = null;
const isCanvasReady = ref(false);
const canvasInitPromise = ref(null);


let originalAnnotations = [];
const newAnnotations = ref([]);
const modifiedAnnotations = ref([]);
const deletedAnnotationIds = ref([]);

const isSaving = ref(false);


let isDrawing = false;
let origX, origY;
let currentShape = null;
let polygonPoints = [];
let polygonLine = null;


let isPanning = false;
let lastPosX, lastPosY;
const ZOOM_MAX = 5;
const ZOOM_MIN = 0.1;
const ZOOM_STEP = 0.1;


const currentZoomLevel = ref(1.0);
let initialImageScale = 1.0;


const buildImageUrl = (img, cacheBust = false) => {
  if (!img?.file_path) return '';

  const normalizedPath = img.file_path.replace(/\\/g, '/');
  const uploadsMatch = normalizedPath.match(/(?:^|\/)uploads\/(.+)$/i);
  if (!uploadsMatch?.[1]) {
    console.error('图片路径不在 uploads 目录中:', img.file_path);
    return '';
  }

  // 空字符串表示使用当前站点，由 Vite/Nginx 将 /static_uploads 转发给后端。
  const apiBase = apiClient.defaults.baseURL || '/api/v1';
  const backendBase = apiBase.replace(/\/api\/v1\/?$/, '');
  const encodedPath = uploadsMatch[1]
      .split('/')
      .map(segment => encodeURIComponent(segment))
      .join('/');
  const query = cacheBust ? `?t=${Date.now()}` : '';
  return `${backendBase}/static_uploads/${encodedPath}${query}`;
};

const getImageThumbnailUrl = (img) => buildImageUrl(img);
const getImageFullUrl = (img) => buildImageUrl(img, true);

const getLabelColor = (labelName) => {
  return labels.value.find(l => l.name === labelName)?.color || '#909399';
};

const loadDatasets = async () => {
  try {
    const response = await fetchDatasets({include_public: true});
    datasets.value = response.data;
  } catch (error) {
    ElMessage.error('加载数据集失败！');
    console.error(error);
  }
};

const loadDatasetImages = async () => {
  if (!selectedDatasetId.value) {
    images.value = [];
    currentImage.value = null;
    return;
  }
  isImageLoading.value = true;
  try {
    const response = await fetchImagesByDataset(selectedDatasetId.value);
    images.value = response.data;
  } catch (error) {
    ElMessage.error('加载图片列表失败！');
    console.error(error);
  } finally {
    isImageLoading.value = false;
  }
};

const cloneCurrentDataset = async () => {
  if (!currentDataset.value) return;
  isCloning.value = true;
  try {
    const cloneName = `${currentDataset.value.name}_${userStore.userInfo?.username || '小组'}`;
    const response = await cloneDataset(currentDataset.value.id, cloneName);
    await loadDatasets();
    selectedDatasetId.value = response.data.id;
    await loadDatasetImages();
    const firstImage = images.value[0];
    ElMessage.success(`已创建独立数据集“${response.data.name}”，现在可以保存标注。`);
    if (firstImage) {
      router.replace({ name: 'AnnotationTool', params: { datasetId: response.data.id, imageId: firstImage.id } });
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '复制数据集失败');
  } finally {
    isCloning.value = false;
  }
};

const selectImage = async (img) => {
  if (currentImage.value && currentImage.value.id === img.id) return;
  router.push({name: 'AnnotationTool', params: {datasetId: selectedDatasetId.value, imageId: img.id}});
};

const loadImageOnCanvas = async () => {
  console.log('loadImageOnCanvas: Called.');
  if (!currentImage.value) {
    console.log('loadImageOnCanvas: No current image. Clearing canvas.');
    if (fabricCanvasRef.value) {
      fabricCanvasRef.value.clear();
      fabricCanvasRef.value.renderAll();
      const canvasWrapper = annotationCanvas.value?.parentElement;
      if (canvasWrapper) {
        canvasWrapper.style.display = 'flex';
        canvasWrapper.style.justifyContent = 'center';
        canvasWrapper.style.alignItems = 'center';
      }
    }
    isImageLoading.value = false;
    return;
  }

  if (!fabricLib.value || !(fabricCanvasRef.value instanceof fabricLib.value.Canvas)) {
    console.error('loadImageOnCanvas: fabricLib or fabricCanvasRef is not a valid Fabric.Canvas instance. Cannot load image.');
    isImageLoading.value = false;
    return;
  }

  isImageLoading.value = true;
  console.log('loadImageOnCanvas: Proceeding with image load for:', currentImage.value.filename);


  const canvasWrapper = annotationCanvas.value?.parentElement;
  if (!canvasWrapper) {
    console.error("Canvas wrapper not found in loadImageOnCanvas.");
    isImageLoading.value = false;
    return;
  }

  let currentWrapperWidth = canvasWrapper.clientWidth;
  let currentWrapperHeight = canvasWrapper.clientHeight;

  if (currentWrapperWidth === 0 || currentWrapperHeight === 0) {
    console.warn('loadImageOnCanvas: Canvas wrapper dimensions are still 0. This might indicate a CSS layout issue or timing problem. Attempting nextTick retry.');
    await nextTick();
    currentWrapperWidth = canvasWrapper.clientWidth;
    currentWrapperHeight = canvasWrapper.clientHeight;
    if (currentWrapperWidth === 0 || currentWrapperHeight === 0) {
      console.error('Canvas wrapper dimensions remain 0 even after nextTick. Cannot load image.');
      isImageLoading.value = false;
      return;
    }
  }


  if (fabricCanvasRef.value.width !== currentWrapperWidth || fabricCanvasRef.value.height !== currentWrapperHeight) {
    fabricCanvasRef.value.setDimensions({width: currentWrapperWidth, height: currentWrapperHeight});
    console.log(`loadImageOnCanvas: Fabric.js canvas dimensions explicitly set to ${currentWrapperWidth}x${currentWrapperHeight}.`);
  } else {
    console.log(`loadImageOnCanvas: Fabric.js canvas dimensions already ${currentWrapperWidth}x${currentWrapperHeight}.`);
  }


  fabricCanvasRef.value.remove(...fabricCanvasRef.value.getObjects());
  fabricCanvasRef.value.setBackgroundImage(null, fabricCanvasRef.value.renderAll.bind(fabricCanvasRef.value));

  try {
    const imageUrlToLoad = getImageFullUrl(currentImage.value);
    if (!imageUrlToLoad) {
      throw new Error("Image URL could not be generated.");
    }

    await new Promise((resolve, reject) => {
      fabricLib.value.Image.fromURL(imageUrlToLoad, (fabricImage) => {
        if (!fabricImage || fabricImage.width === 0) {
          reject(new Error('图片加载失败，请检查URL或CORS策略。'));
          return;
        }


        const finalCanvasWidth = fabricCanvasRef.value.width;
        const finalCanvasHeight = fabricCanvasRef.value.height;

        const scaleX = finalCanvasWidth / fabricImage.width;
        const scaleY = finalCanvasHeight / fabricImage.height;
        const scale = Math.min(scaleX, scaleY);

        fabricCanvasRef.value.setBackgroundImage(fabricImage, fabricCanvasRef.value.renderAll.bind(fabricCanvasRef.value), {
          scaleX: scale,
          scaleY: scale,
          originX: 'center',
          originY: 'center',
          top: finalCanvasHeight / 2,
          left: finalCanvasWidth / 2,
          selectable: false,
          evented: false,
        });


        initialImageScale = scale;
        fabricCanvasRef.value.setViewportTransform([1, 0, 0, 1, 0, 0]);
        fabricCanvasRef.value.setZoom(initialImageScale);
        fabricCanvasRef.value.centerObject(fabricImage);
        currentZoomLevel.value = initialImageScale;

        console.log(`Image loaded: original ${fabricImage.width}x${fabricImage.height}, scaled to ${fabricImage.width * scale}x${fabricImage.height * scale} on canvas ${finalCanvasWidth}x${finalCanvasHeight}. Initial zoom: ${initialImageScale}`);
        resolve();
      }, {
        crossOrigin: 'anonymous',
        onload: () => { console.log('Fabric.js Image loaded successfully.'); },
        onError: (err) => {
          console.error('Fabric.js Image loading error:', err);
          reject(new Error('图片加载失败，请检查URL或CORS策略。'));
        }
      });
    });

    isImageLoading.value = false;
    console.log('Image loaded and set as background successfully.');
  } catch (error) {
    isImageLoading.value = false;
    ElMessage.error('加载图片到画布时发生错误: ' + (error.message || '未知错误'));
    console.error('loadImageOnCanvas: 错误详情:', error);
    if (fabricCanvasRef.value) fabricCanvasRef.value.clear();
  }
};

const loadAnnotationsForCurrentImage = async () => {
  console.log('loadAnnotationsForCurrentImage: Called.');
  if (!currentImage.value || !fabricLib.value || !(fabricCanvasRef.value instanceof fabricLib.value.Canvas)) {
    originalAnnotations = [];
    newAnnotations.value = [];
    modifiedAnnotations.value = [];
    deletedAnnotationIds.value = [];
    if (fabricCanvasRef.value) {
      fabricCanvasRef.value.remove(...fabricCanvasRef.value.getObjects());
    }
    return;
  }

  try {
    const response = await fetchAnnotationsByImage(currentImage.value.id);
    originalAnnotations = response.data;
    newAnnotations.value = [];
    modifiedAnnotations.value = [];
    deletedAnnotationIds.value = [];

    fabricCanvasRef.value.remove(...fabricCanvasRef.value.getObjects());

    originalAnnotations.forEach(ann => {
      addAnnotationToCanvas(ann);
    });
    fabricCanvasRef.value.renderAll();
    console.log(`Loaded ${originalAnnotations.length} annotations.`);
  } catch (error) {
    ElMessage.error('加载标注失败！');
    console.error(error);
  }
};

const getAbsolutePolygonPoints = (polygonObj) => {
  const points = polygonObj.get('points');
  const matrix = polygonObj.calcTransformMatrix();

  return points.map(p => {
    const newPoint = fabricLib.value.util.transformPoint(
        {x: p.x - (polygonObj.pathOffset?.x || 0), y: p.y - (polygonObj.pathOffset?.y || 0)},
        matrix
    );
    return [newPoint.x, newPoint.y];
  });
};

const addAnnotationToCanvas = (annotationData, isNew = false) => {
  if (!fabricLib.value || !(fabricCanvasRef.value instanceof fabricLib.value.Canvas)) {
    console.error('addAnnotationToCanvas: fabricLib or canvas not ready.');
    return;
  }

  const {id, annotation_type, label, coordinates, extra_data} = annotationData;
  const color = getLabelColor(label);
  let fabricObject = null;

  const commonProps = {
    fill: 'rgba(255, 255, 255, 0.2)',
    stroke: color,
    strokeWidth: 2,
    cornerColor: color,
    cornerSize: 8,
    transparentCorners: false,
    hasControls: true,
    hasBorders: true,
    data: {
      id: id,
      image_id: annotationData.image_id,
      dataset_id: annotationData.dataset_id,
      annotation_type: annotation_type,
      label: label,
      coordinates: coordinates,
      extra_data: extra_data,
      isNew: isNew,
      isModified: false,
    }
  };

  if (annotation_type === 'bbox') {
    fabricObject = new fabricLib.value.Rect({
      left: coordinates.x,
      top: coordinates.y,
      width: coordinates.width,
      height: coordinates.height,
      ...commonProps
    });
  } else if (annotation_type === 'polygon') {
    const fabricPoints = coordinates.points.map(p => ({x: p[0], y: p[1]}));
    fabricObject = new fabricLib.value.Polygon(fabricPoints, {
      ...commonProps
    });
    fabricObject.perPixelTargetFind = true;
    fabricObject.objectCaching = false;
  } else if (annotation_type === 'point') {
    fabricObject = new fabricLib.value.Circle({
      left: coordinates.x - 5,
      top: coordinates.y - 5,
      radius: 5,
      ...commonProps,
      fill: color,
      stroke: 'white',
      strokeWidth: 1,
      hasControls: false,
      hasBorders: false,
    });
  }

  if (fabricObject) {
    fabricCanvasRef.value.add(fabricObject);
    if (isNew) {
      newAnnotations.value.push(fabricObject);
    }
    const textLabel = new fabricLib.value.Text(label, {
      left: fabricObject.left,
      top: fabricObject.top - 20,
      fontSize: 14,
      fill: getLabelColor(label),
      selectable: false,
      evented: false,
      data: {parent: fabricObject}
    });
    fabricCanvasRef.value.add(textLabel);
    fabricObject.data.textLabel = textLabel;
  }
};


const initFabricCanvas = () => {
  return new Promise(resolve => {
    if (!fabricLib.value) {
      if (fabric && fabric.default && typeof fabric.default.Canvas !== 'undefined') {
        fabricLib.value = fabric.default;
      } else if (fabric && typeof fabric.Canvas !== 'undefined') {
        fabricLib.value = fabric;
      } else if (fabric && fabric.fabric && typeof fabric.fabric.Canvas !== 'undefined') {
        fabricLib.value = fabric.fabric;
      } else {
        console.error('CRITICAL: Could not determine fabricLib.value. Fabric.Canvas might not be available.');
        ElMessage.error('Fabric.js 库加载失败，请检查依赖或网络。');
        isCanvasReady.value = false;
        resolve(null);
        return;
      }
      console.log('initFabricCanvas: fabricLib.value determined as:', fabricLib.value);
    }

    if (!fabricLib.value || typeof fabricLib.value.Canvas === 'undefined') {
      console.error('initFabricCanvas: fabricLib or fabricLib.Canvas is still not defined after determination. Cannot initialize canvas.');
      isCanvasReady.value = false;
      resolve(null);
      return;
    }

    if (fabricCanvasRef.value instanceof fabricLib.value.Canvas) {
      console.warn('initFabricCanvas: fabricCanvasRef.value already holds a valid Fabric.Canvas instance. Skipping re-initialization.');
      resolve(fabricCanvasRef.value);
      return;
    }

    if (annotationCanvas.value) {
      console.log('initFabricCanvas: Creating new fabric.Canvas instance...');
      // 初始尺寸可以先给一个默认值，或者直接从容器获取（如果此时容器已经有尺寸）
      const initialWidth = annotationCanvas.value.parentElement?.clientWidth || 800; // 提高默认值
      const initialHeight = annotationCanvas.value.parentElement?.clientHeight || 600; // 提高默认值

      fabricCanvasRef.value = new fabricLib.value.Canvas(annotationCanvas.value, {
        selection: true,
        preserveObjectStacking: true,
        backgroundColor: '#f0f0f0',
        renderOnAddRemove: false,
        width: initialWidth,
        height: initialHeight,
      });

      console.log(`initFabricCanvas: fabricCanvasRef.value created with initial dimensions: ${initialWidth}x${initialHeight}.`);

      fabricCanvasRef.value.on('object:modified', (e) => {
        const obj = e.target;
        if (obj && obj.data) {
          if (!obj.data.isNew) {
            obj.data.isModified = true;
            if (!modifiedAnnotations.value.includes(obj)) {
              modifiedAnnotations.value.push(obj);
            }
          }
          if (obj.data.textLabel) {
            obj.data.textLabel.set({
              left: obj.left,
              top: obj.top - 20
            });
            fabricCanvasRef.value.bringToFront(obj.data.textLabel);
          }
          fabricCanvasRef.value.renderAll();
        }
      });

      fabricCanvasRef.value.on('object:removed', (e) => {
        const obj = e.target;
        if (obj && obj.data) {
          if (obj.data.textLabel && fabricCanvasRef.value.contains(obj.data.textLabel)) {
            fabricCanvasRef.value.remove(obj.data.textLabel);
          }
          const newIndex = newAnnotations.value.indexOf(obj);
          if (newIndex !== -1) {
            newAnnotations.value.splice(newIndex, 1);
          }
          const modifiedIndex = modifiedAnnotations.value.indexOf(obj);
          if (modifiedIndex !== -1) {
            modifiedAnnotations.value.splice(modifiedIndex, 1);
          }
        }
      });

      fabricCanvasRef.value.on('selection:created', (e) => {
        if (e.selected && e.selected.length === 1 && e.selected[0].data && e.selected[0].data.label) {
          currentLabel.value = e.selected[0].data.label;
        }
      });

      fabricCanvasRef.value.on('selection:updated', (e) => {
        if (e.selected && e.selected.length === 1 && e.selected[0].data && e.selected[0].data.label) {
          currentLabel.value = e.selected[0].data.label;
        }
      });

      fabricCanvasRef.value.on('mouse:wheel', (opt) => {
        // ✨ 优化缩放逻辑：以鼠标位置为中心进行缩放
        const pointer = fabricCanvasRef.value.getPointer(opt.e);
        let zoom = fabricCanvasRef.value.getZoom();
        zoom *= 0.999 ** opt.e.deltaY; // 缩放因子
        if (zoom > ZOOM_MAX) zoom = ZOOM_MAX;
        if (zoom < ZOOM_MIN) zoom = ZOOM_MIN;

        // 使用 zoomToPoint 以鼠标位置为中心进行缩放
        fabricCanvasRef.value.zoomToPoint(new fabricLib.value.Point(pointer.x, pointer.y), zoom);
        currentZoomLevel.value = zoom;
        opt.e.preventDefault();
        opt.e.stopPropagation();
      });

      fabricCanvasRef.value.on('mouse:down', (o) => {
        if (!currentImage.value || !currentLabel.value) return;

        if (o.e.altKey || o.e.spaceKey) {
          isPanning = true;
          fabricCanvasRef.value.selection = false;
          lastPosX = o.e.clientX;
          lastPosY = o.e.clientY;
          return;
        }

        if (annotationMode.value === 'view' || o.target) return;

        isDrawing = true;
        const pointer = fabricCanvasRef.value.getPointer(o.e);
        origX = pointer.x;
        origY = pointer.y;

        if (annotationMode.value === 'bbox') {
          currentShape = new fabricLib.value.Rect({
            left: origX,
            top: origY,
            width: 0,
            height: 0,
            fill: 'rgba(255, 255, 255, 0.2)',
            stroke: getLabelColor(currentLabel.value),
            strokeWidth: 2,
            selectable: true,
            evented: true,
            hasControls: true,
            hasBorders: true,
            cornerColor: getLabelColor(currentLabel.value),
            transparentCorners: false,
          });
          fabricCanvasRef.value.add(currentShape);
        } else if (annotationMode.value === 'polygon') {
          if (!polygonPoints.length) {
            polygonPoints.push({x: origX, y: origY});
          } else {
            polygonPoints.push({x: origX, y: origY});
            if (polygonLine) {
              fabricCanvasRef.value.remove(polygonLine);
            }
            polygonLine = new fabricLib.value.Line([polygonPoints[polygonPoints.length - 2].x, polygonPoints[polygonPoints.length - 2].y, origX, origY], {
              stroke: getLabelColor(currentLabel.value),
              strokeWidth: 2,
              selectable: false,
              evented: false,
              strokeDashArray: [5, 5]
            });
            fabricCanvasRef.value.add(polygonLine);
          }
        } else if (annotationMode.value === 'point') {
          const pointObj = new fabricLib.value.Circle({
            left: origX - 5,
            top: origY - 5,
            radius: 5,
            fill: getLabelColor(currentLabel.value),
            stroke: 'white',
            strokeWidth: 1,
            selectable: true,
            evented: true,
            hasControls: false,
            hasBorders: false,
            data: {
              image_id: currentImage.value.id,
              dataset_id: currentImage.value.dataset_id,
              annotation_type: 'point',
              label: currentLabel.value,
              coordinates: {x: origX, y: origY},
              extra_data: {},
              isNew: true,
              isModified: false,
            }
          });
          fabricCanvasRef.value.add(pointObj);
          newAnnotations.value.push(pointObj);

          const textLabel = new fabricLib.value.Text(currentLabel.value, {
            left: pointObj.left + 10,
            top: pointObj.top + 5,
            fontSize: 14,
            fill: getLabelColor(currentLabel.value),
            selectable: false,
            evented: false,
            data: {parent: pointObj}
          });
          fabricCanvasRef.value.add(textLabel);
          pointObj.data.textLabel = textLabel;
          fabricCanvasRef.value.renderAll();
          isDrawing = false;
        }
        fabricCanvasRef.value.renderAll();
      });

      fabricCanvasRef.value.on('mouse:move', (o) => {
        if (isPanning) {
          const e = o.e;
          const deltaX = e.clientX - lastPosX;
          const deltaY = e.clientY - lastPosY;
          fabricCanvasRef.value.viewportTransform[4] += deltaX;
          fabricCanvasRef.value.viewportTransform[5] += deltaY;
          fabricCanvasRef.value.requestRenderAll();
          lastPosX = e.clientX;
          lastPosY = e.clientY;
          return;
        }

        if (!isDrawing || annotationMode.value !== 'bbox') return;
        const pointer = fabricCanvasRef.value.getPointer(o.e);
        if (currentShape) {
          currentShape.set({
            width: Math.abs(pointer.x - origX),
            height: Math.abs(pointer.y - origY),
            left: Math.min(pointer.x, origX),
            top: Math.min(pointer.y, origY)
          });
          fabricCanvasRef.value.renderAll();
        }
      });

      fabricCanvasRef.value.on('mouse:up', () => {
        if (isPanning) {
          isPanning = false;
          fabricCanvasRef.value.selection = true;
          return;
        }

        if (!isDrawing) return;

        if (annotationMode.value === 'bbox' && currentShape) {
          if (currentShape.width > 5 && currentShape.height > 5) {
            currentShape.data = {
              image_id: currentImage.value.id,
              dataset_id: currentImage.value.dataset_id,
              annotation_type: 'bbox',
              label: currentLabel.value,
              coordinates: {
                x: currentShape.left,
                y: currentShape.top,
                width: currentShape.width,
                height: currentShape.height
              },
              extra_data: {},
              isNew: true,
              isModified: false,
            };
            newAnnotations.value.push(currentShape);
            const textLabel = new fabricLib.value.Text(currentLabel.value, {
              left: currentShape.left,
              top: currentShape.top - 20,
              fontSize: 14,
              fill: getLabelColor(currentLabel.value),
              selectable: false,
              evented: false,
              data: {parent: currentShape}
            });
            fabricCanvasRef.value.add(textLabel);
            currentShape.data.textLabel = textLabel;
          } else {
            fabricCanvasRef.value.remove(currentShape);
            ElMessage.warning('绘制的矩形过小，已取消。');
          }
          currentShape = null;
        }
        isDrawing = false;
        fabricCanvasRef.value.renderAll();
      });

      fabricCanvasRef.value.on('mouse:dblclick', (o) => {
        if (annotationMode.value === 'polygon' && polygonPoints.length >= 3) {
          if (polygonLine) {
            fabricCanvasRef.value.remove(polygonLine);
            polygonLine = null;
          }
          const polygonObj = new fabricLib.value.Polygon(polygonPoints, {
            fill: 'rgba(255, 255, 255, 0.2)',
            stroke: getLabelColor(currentLabel.value),
            strokeWidth: 2,
            selectable: true,
            evented: true,
            hasControls: true,
            hasBorders: true,
            cornerColor: getLabelColor(currentLabel.value),
            transparentCorners: false,
            data: {
              image_id: currentImage.value.id,
              dataset_id: currentImage.value.dataset_id,
              annotation_type: 'polygon',
              label: currentLabel.value,
              coordinates: {points: polygonPoints.map(p => [p.x, p.y])},
              extra_data: {},
              isNew: true,
              isModified: false,
            }
          });
          polygonObj.perPixelTargetFind = true;
          polygonObj.objectCaching = false;

          fabricCanvasRef.value.add(polygonObj);
          newAnnotations.value.push(polygonObj);
          const textLabel = new fabricLib.value.Text(currentLabel.value, {
            left: polygonObj.left,
            top: polygonObj.top - 20,
            fontSize: 14,
            fill: getLabelColor(currentLabel.value),
            selectable: false,
            evented: false,
            data: {parent: polygonObj}
          });
          fabricCanvasRef.value.add(textLabel);
          polygonObj.data.textLabel = textLabel;

          polygonPoints = [];
          isDrawing = false;
          fabricCanvasRef.value.renderAll();
        }
      });

      window.addEventListener('keydown', handleKeyDown);

      resolve(fabricCanvasRef.value);
    } else {
      console.log('initFabricCanvas: annotationCanvas.value is null, cannot initialize. Resolving canvasInitPromise with null.');
      isCanvasReady.value = false;
      resolve(null);
    }
  });
};

const handleKeyDown = (e) => {
  if (!fabricCanvasRef.value) return;

  if (e.key === 'Escape') {
    if (isDrawing) {
      isDrawing = false;
      if (currentShape) {
        fabricCanvasRef.value.remove(currentShape);
        currentShape = null;
      }
      if (polygonPoints.length > 0) {
        polygonPoints = [];
        if (polygonLine) {
          fabricCanvasRef.value.remove(polygonLine);
          polygonLine = null;
        }
      }
      fabricCanvasRef.value.renderAll();
      ElMessage.info('当前绘制已取消。');
    }
  } else if (e.key === 'Delete' || e.key === 'Backspace') {
    const activeObjects = fabricCanvasRef.value.getActiveObjects();
    if (activeObjects.length > 0) {
      clearSelectedAnnotations();
      e.preventDefault();
    }
  }
};

const changeZoom = (delta) => {
  if (!fabricCanvasRef.value) return;
  let zoom = fabricCanvasRef.value.getZoom();
  zoom += delta;
  if (zoom > ZOOM_MAX) zoom = ZOOM_MAX;
  if (zoom < ZOOM_MIN) zoom = ZOOM_MIN;

  // ✨ 优化：以画布中心为缩放点
  const center = new fabricLib.value.Point(fabricCanvasRef.value.width / 2, fabricCanvasRef.value.height / 2);
  fabricCanvasRef.value.zoomToPoint(center, zoom);
  currentZoomLevel.value = zoom;
  fabricCanvasRef.value.renderAll();
};

const resetZoom = () => {
  if (!fabricCanvasRef.value || !fabricCanvasRef.value.backgroundImage) return;

  // ✨ 确保重置时使用最新的 initialImageScale
  fabricCanvasRef.value.setViewportTransform([1, 0, 0, 1, 0, 0]); // 重置平移
  fabricCanvasRef.value.setZoom(initialImageScale); // 应用初始适应缩放
  const fabricImage = fabricCanvasRef.value.backgroundImage;
  fabricCanvasRef.value.centerObject(fabricImage); // 居中背景图
  fabricCanvasRef.value.renderAll();
  currentZoomLevel.value = initialImageScale;
};


const confirmAddLabel = async () => {
  if (!labelFormRef.value) return;
  await labelFormRef.value.validate((valid) => {
    if (valid) {
      if (labels.value.some(l => l.name === newLabelForm.value.name)) {
        ElMessage.warning('标签名称已存在！');
        return;
      }
      labels.value.push({...newLabelForm.value});
      currentLabel.value = newLabelForm.value.name;
      addLabelDialogVisible.value = false;
      newLabelForm.value = {name: '', color: '#409EFF'};
      ElMessage.success('标签添加成功！(本次会话有效)');
    }
  });
};

const removeLabel = (index) => {
  ElMessageBox.confirm('确定要删除此标签吗？已使用此标签的标注将失去标签关联，但标注本身不会被删除。此操作仅在当前会话有效。', '警告', {
    type: 'warning'
  }).then(() => {
    const deletedLabelName = labels.value[index].name;
    labels.value.splice(index, 1);
    if (currentLabel.value === deletedLabelName) {
      currentLabel.value = labels.value.length > 0 ? labels.value[0].name : '';
    }
    ElMessage.success('标签删除成功！(本次会话有效)');
  }).catch(() => {
  });
};

const mapFabricObjectToAnnotationCreate = (obj) => {
  const data = obj.data;
  let coordinates;
  if (data.annotation_type === 'bbox') {
    coordinates = {
      x: obj.left,
      y: obj.top,
      width: obj.width * obj.scaleX,
      height: obj.height * obj.scaleY,
    };
  } else if (data.annotation_type === 'polygon') {
    coordinates = {points: getAbsolutePolygonPoints(obj)};
  } else if (data.annotation_type === 'point') {
    coordinates = {
      x: obj.left + obj.radius,
      y: obj.top + obj.radius,
    };
  } else {
    throw new Error(`Unsupported annotation type: ${data.annotation_type}`);
  }

  return {
    image_id: data.image_id,
    dataset_id: data.dataset_id,
    annotation_type: data.annotation_type,
    label: data.label,
    coordinates: coordinates,
    extra_data: data.extra_data || {},
  };
};

const mapFabricObjectToAnnotationUpdate = (obj) => {
  const data = obj.data;
  const annotation = mapFabricObjectToAnnotationCreate(obj);
  return {
    id: data.id,
    label: annotation.label,
    coordinates: annotation.coordinates,
    extra_data: annotation.extra_data
  };
};


const saveAnnotations = async () => {
  if (!currentImage.value) {
    ElMessage.warning('请先选择图片！');
    return;
  }
  if (!canEditDataset.value) {
    ElMessage.warning('公共数据集为只读，请先复制到自己的账号再进行标注。');
    return;
  }

  isSaving.value = true;
  try {
    if (newAnnotations.value.length > 0) {
      const annotationsToCreate = newAnnotations.value.map(mapFabricObjectToAnnotationCreate);
      await createBatchAnnotations(annotationsToCreate);
      ElMessage.success(`成功添加 ${newAnnotations.value.length} 条新标注。`);
    }

    const validModifiedAnnotations = modifiedAnnotations.value.filter(obj => obj.data && obj.data.id);
    for (const obj of validModifiedAnnotations) {
      const annotationData = mapFabricObjectToAnnotationUpdate(obj);
      await updateAnnotation(annotationData.id, annotationData);
    }
    if (validModifiedAnnotations.length > 0) {
      ElMessage.success(`成功更新 ${validModifiedAnnotations.length} 条标注。`);
    }

    if (deletedAnnotationIds.value.length > 0) {
      await deleteBatchAnnotations(deletedAnnotationIds.value);
      ElMessage.success(`成功删除 ${deletedAnnotationIds.value.length} 条标注。`);
    }

    newAnnotations.value = [];
    modifiedAnnotations.value = [];
    deletedAnnotationIds.value = [];

    await loadAnnotationsForCurrentImage();
    await markImageReviewed(selectedDatasetId.value, currentImage.value.id, true);
    ElMessage.success('所有标注已保存！');
  } catch (error) {
    ElMessage.error('保存标注失败！' + (error.response?.data?.detail || error.message));
    console.error(error);
  } finally {
    isSaving.value = false;
  }
};

const confirmNoDefect = async () => {
  if (!currentImage.value) return;
  if (newAnnotations.value.length || modifiedAnnotations.value.length || deletedAnnotationIds.value.length) {
    ElMessage.warning('当前图片有未保存的修改，请先保存标注。');
    return;
  }
  try {
    await markImageReviewed(selectedDatasetId.value, currentImage.value.id, true);
    ElMessage.success('当前图片已标记为检查完成。');
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '更新检查状态失败');
  }
};

const clearSelectedAnnotations = () => {
  if (!fabricCanvasRef.value || !(fabricCanvasRef.value instanceof fabricLib.value.Canvas)) {
    ElMessage.info('画布未初始化，无法执行删除操作。');
    return;
  }
  const activeObjects = fabricCanvasRef.value.getActiveObjects();
  if (activeObjects.length === 0) {
    ElMessage.info('请先选择要删除的标注。');
    return;
  }

  ElMessageBox.confirm(`确定要删除选中的 ${activeObjects.length} 条标注吗？`, '警告', {
    type: 'warning'
  }).then(() => {
    activeObjects.forEach(obj => {
      if (obj.data && obj.data.id && !obj.data.isNew) {
        deletedAnnotationIds.value.push(obj.data.id);
      }
      const newIndex = newAnnotations.value.indexOf(obj);
      if (newIndex !== -1) {
        newAnnotations.value.splice(newIndex, 1);
      }
      const modifiedIndex = modifiedAnnotations.value.indexOf(obj);
      if (modifiedIndex !== -1) {
        modifiedAnnotations.value.splice(modifiedIndex, 1);
      }
      fabricCanvasRef.value.remove(obj);
    });
    fabricCanvasRef.value.discardActiveObject().renderAll();
    ElMessage.success('选中标注已删除。');
  }).catch(() => {
  });
};

const resetAnnotations = async () => {
  if (!currentImage.value) return;

  try {
    await ElMessageBox.confirm('确定要放弃所有未保存的更改并重置标注吗？', '警告', {
      type: 'warning'
    });
    newAnnotations.value = [];
    modifiedAnnotations.value = [];
    deletedAnnotationIds.value = [];
    await loadAnnotationsForCurrentImage();
    ElMessage.info('标注已重置。');
  } catch (error) {
    // User cancelled reset
  }
};


onMounted(() => {
  console.log('onMounted: Component mounted.');

  canvasInitPromise.value = initFabricCanvas();
  loadDatasets();

  const canvasWrapper = annotationCanvas.value?.parentElement;
  if (canvasWrapper) {
    resizeObserver = new ResizeObserver(entries => {
      const entry = entries[0];
      const {width, height} = entry.contentRect;

      console.log(`ResizeObserver: Canvas wrapper dimensions detected: ${width}px x ${height}px`);

      if (width > 0 && height > 0) {
        if (fabricCanvasRef.value && fabricCanvasRef.value instanceof (fabricLib.value?.Canvas || Function)) {
          if (fabricCanvasRef.value.width !== width || fabricCanvasRef.value.height !== height) {
            console.log(`Setting Fabric.js canvas dimensions to: ${width}x${height} from ResizeObserver.`);
            fabricCanvasRef.value.setDimensions({width, height});

            // 如果有背景图片，需要重新调整其缩放和位置以适应新尺寸
            if (fabricCanvasRef.value.backgroundImage) {
              const fabricImage = fabricCanvasRef.value.backgroundImage;
              const scaleX = width / fabricImage.width;
              const scaleY = height / fabricImage.height;
              const newInitialScale = Math.min(scaleX, scaleY);

              fabricImage.set({
                scaleX: newInitialScale,
                scaleY: newInitialScale,
                originX: 'center',
                originY: 'center',
                top: height / 2,
                left: width / 2,
              });

              // ✨ 仅当当前缩放是初始缩放时才自动调整，否则保持用户缩放
              if (Math.abs(currentZoomLevel.value - initialImageScale) < 0.001) { // 浮点数比较用容差
                fabricCanvasRef.value.setZoom(newInitialScale);
                currentZoomLevel.value = newInitialScale;
              }
              initialImageScale = newInitialScale; // 更新初始缩放比例，供后续重置使用
            }
            fabricCanvasRef.value.renderAll();
          }
          if (!isCanvasReady.value) {
            isCanvasReady.value = true;
            console.log('ResizeObserver: isCanvasReady set to true.');
          }
        } else {
          console.warn('ResizeObserver: fabricCanvasRef.value not yet initialized or invalid. Cannot set canvas dimensions.');
        }
      } else {
        if (isCanvasReady.value) {
          isCanvasReady.value = false;
          console.log('ResizeObserver: Canvas container dimensions became 0. isCanvasReady set to false.');
        }
      }
    });
    resizeObserver.observe(canvasWrapper);
  }
});

// 优化后的当前图片监视器
watch([currentImage, isCanvasReady], async ([newImg, canvasReady]) => {
  console.log('Watch currentImage/isCanvasReady triggered.');
  console.log('  newImg:', newImg ? newImg.filename : null);
  console.log('  canvasReady:', canvasReady);

  if (canvasReady) {
    if (newImg) {
      if (canvasInitPromise.value) {
        console.log('Watch: Awaiting canvas initialization promise...');
        const resolvedCanvas = await canvasInitPromise.value;
        if (resolvedCanvas && resolvedCanvas instanceof (fabricLib.value?.Canvas || Function)) {
          console.log('Watch: Canvas is ready and valid. Calling loadImageOnCanvas and loadAnnotationsForCurrentImage.');
          // 在加载图片前，再次确保画布尺寸是正确的
          const canvasWrapper = annotationCanvas.value?.parentElement;
          if (canvasWrapper) {
            const currentWrapperWidth = canvasWrapper.clientWidth;
            const currentWrapperHeight = canvasWrapper.clientHeight;
            if (fabricCanvasRef.value.width !== currentWrapperWidth || fabricCanvasRef.value.height !== currentWrapperHeight) {
              console.log(`Watch: Re-setting canvas dimensions to ${currentWrapperWidth}x${currentWrapperHeight} before loading image.`);
              fabricCanvasRef.value.setDimensions({width: currentWrapperWidth, height: currentWrapperHeight});
            }
          }
          loadImageOnCanvas();
          loadAnnotationsForCurrentImage();
        } else {
          console.warn('Watch: Canvas not resolved to a valid Fabric.Canvas instance after promise. Skipping image load.');
        }
      } else {
        console.warn('Watch: canvasInitPromise is null, canvas not initialized yet. Skipping image load.');
      }
    } else {
      console.log('Watch: currentImage is null, clearing canvas.');
      if (fabricCanvasRef.value && fabricCanvasRef.value instanceof (fabricLib.value?.Canvas || Function)) {
        fabricCanvasRef.value.clear();
        fabricCanvasRef.value.renderAll();
        const canvasWrapper = annotationCanvas.value?.parentElement;
        if (canvasWrapper) {
          canvasWrapper.style.display = 'flex';
          canvasWrapper.style.justifyContent = 'center';
          canvasWrapper.style.alignItems = 'center';
        }
        originalAnnotations = [];
        newAnnotations.value = [];
        modifiedAnnotations.value = [];
        deletedAnnotationIds.value = [];
      }
    }
  } else {
    console.log('Watch: Canvas not ready yet. Skipping image load/clear.');
  }
}, {immediate: true});

// 路由监视器保持不变
watch(() => route.params, async (newParams, oldParams) => {
  const newDatasetId = parseInt(newParams.datasetId);
  const newImageId = parseInt(newParams.imageId);
  const oldDatasetId = oldParams ? parseInt(oldParams.datasetId) : undefined;
  const oldImageId = oldParams ? parseInt(oldParams.imageId) : undefined;

  let targetDatasetId = newDatasetId;
  let targetImageId = newImageId;

  if (newDatasetId && newDatasetId !== selectedDatasetId.value) {
    selectedDatasetId.value = newDatasetId;
    await loadDatasetImages();
  } else if (!newDatasetId) {
    selectedDatasetId.value = null;
    images.value = [];
    currentImage.value = null;
    return;
  }

  let imageToLoad = null;
  if (targetImageId) {
    imageToLoad = images.value.find(i => i.id === targetImageId);
  }

  if (!imageToLoad && images.value.length > 0) {
    imageToLoad = images.value[0];
    if (targetImageId !== imageToLoad.id) {
      router.replace({name: 'AnnotationTool', params: {datasetId: selectedDatasetId.value, imageId: imageToLoad.id}});
      return;
    }
  }

  if (currentImage.value && imageToLoad && currentImage.value.id !== imageToLoad.id) {
    if (newAnnotations.value.length > 0 || modifiedAnnotations.value.length > 0 || deletedAnnotationIds.value.length > 0) {
      try {
        await ElMessageBox.confirm('当前图片有未保存的标注更改，是否保存？', '提示', {
          confirmButtonText: '保存并切换',
          cancelButtonText: '放弃并切换',
          type: 'warning',
        });
        await saveAnnotations();
      } catch (action) {
        if (action === 'cancel') {
          resetAnnotations();
          ElMessage.info('已放弃当前图片标注更改。');
        } else {
          if (oldDatasetId !== undefined && oldImageId !== undefined) {
            router.replace({name: 'AnnotationTool', params: {datasetId: oldDatasetId, imageId: oldImageId}});
          } else {
            router.replace({name: 'AnnotationTool', params: {datasetId: selectedDatasetId.value}});
          }
          return;
        }
      }
    }
  }

  if (imageToLoad && currentImage.value?.id !== imageToLoad.id) {
    currentImage.value = imageToLoad;
  } else if (!imageToLoad && currentImage.value) {
    currentImage.value = null;
  }
}, {immediate: true});


onBeforeUnmount(() => {
  console.log('onBeforeUnmount: Component is unmounting. Disposing fabricCanvas.');
  if (fabricCanvasRef.value) {
    fabricCanvasRef.value.dispose();
    fabricCanvasRef.value = null;
    isCanvasReady.value = false;
    canvasInitPromise.value = null;
  }
  if (resizeObserver) {
    resizeObserver.disconnect();
  }
  window.removeEventListener('keydown', handleKeyDown);
});
</script>

<style scoped>

/* 整个标注容器：占据视口减去顶部导航栏后的所有高度，并移除自身内边距 */
.annotation-main {
  padding: 5px; /* 主内容区内部内容与边缘的距离 */
  background-color: #f5f9ff;
  display: flex;
  flex-direction: column; /* 垂直排列子元素 */
  flex-grow: 1; /* 占据所有可用宽度 */
  min-width: 0; /* 防止内容溢出 */
  box-sizing: border-box;
  height: 100%; /* 确保在父容器 (annotation-container) 中占据所有可用高度 */

  /* ✨ 新增：覆盖 Element Plus el-main 的默认 padding 变量 */
  --el-main-padding: 5px; /* 将其设置为你想要的更小的值，例如 5px 或 0px */
}

.annotation-container {
  height: calc(100vh - 60px); /* 假设顶部导航栏高度为 60px。这里不再减去额外的 10px */
  padding: 0px; /* 移除容器自身的内边距，让内容紧贴边缘 */
  display: flex; /* 启用 Flexbox 布局 */
  box-sizing: border-box; /* 确保 padding 不会增加总高度 */
  width: 100%; /* 确保占据父容器全部宽度 */
}

/* 侧边栏：占据固定宽度，内部有 padding */
.annotation-aside {
  background-color: #f5f7fa;
  padding: 5px; /* 侧边栏内部内容与边缘的距离 */
  border-right: 1px solid #e4e7ed; /* 右侧边框作为分隔线 */
  display: flex;
  flex-direction: column; /* 垂直排列子元素 */
  box-sizing: border-box;
  flex-shrink: 0; /* 防止侧边栏被压缩 */
}

/* 侧边栏的卡片样式 */
.aside-card {
  margin-bottom: 5px; /* 卡片之间的间距 */
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  min-height: 0; /* 防止内容溢出导致卡片高度问题 */
  box-sizing: border-box;
}

/* 侧边栏第一个卡片（数据集和图片）：使其伸展以填充可用空间 */
.aside-card:first-of-type {
  flex-grow: 1; /* 占据更多垂直空间 */
}

/* 侧边栏第二个卡片（标签管理）：保持其内容所需的高度 */
.aside-card:last-of-type {
  flex-grow: 0;
}

/* 侧边栏卡片头部样式 */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
  font-size: 16px;
  padding-bottom: 10px; /* 头部与内容之间的间距 */
  flex-shrink: 0; /* 防止头部被压缩 */
}

/* 图片列表滚动区域 */
.image-list {
  display: flex;
  flex-direction: column;
  gap: 8px; /* 列表项之间的间距 */
}

.image-list-item {
  display: flex;
  align-items: center;
  padding: 8px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
  background-color: #fff;
}

.image-list-item:hover {
  background-color: #ecf5ff;
  border-color: #1e6fff;
}

.image-list-item.is-active {
  background-color: #d9ecff;
  border-color: #1e6fff;
  box-shadow: 0 0 0 1px #1e6fff inset;
}

.image-thumbnail {
  width: 40px;
  height: 40px;
  border-radius: 4px;
  margin-right: 10px;
  flex-shrink: 0;
}

.image-filename {
  flex-grow: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 14px;
  color: #303133;
}

/* 标签列表 */
.label-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.label-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 5px 0;
}

.label-tag {
  font-size: 14px;
  height: 32px;
  line-height: 30px;
  padding: 0 10px;
}

/* 主内容区：占据剩余宽度，内部有 padding */
.annotation-main {
  padding: 5px; /* 主内容区内部内容与边缘的距离 */
  background-color: #f5f9ff;
  display: flex;
  flex-direction: column; /* 垂直排列子元素 */
  flex-grow: 1; /* 占据所有可用宽度 */
  min-width: 0; /* 防止内容溢出导致宽度问题 */
  box-sizing: border-box;
  height: 100%; /* 确保在父容器 (annotation-container) 中占据所有可用高度 */
}

/* 主内容区的卡片：占据所有可用空间 */
.main-card {
  height: 100%; /* 确保在父容器 (annotation-main) 中占据所有可用高度 */
  display: flex;
  flex-direction: column; /* 垂直排列内部 header 和 body */
  border-radius: 8px;
  flex-grow: 1; /* 确保能正确伸展 */
  min-height: 0; /* 防止内容溢出 */
  box-sizing: border-box;
}

/* Element Plus Card Header 样式覆盖 */
.main-card :deep(.el-card__header) {
  padding: 18px 20px 10px 20px !important; /* 调整 header padding，确保底部有间距 */
  flex-shrink: 0; /* 防止 header 被压缩 */
}

/* Element Plus Card Body 样式覆盖：占据所有剩余空间，移除默认 padding */
.main-card :deep(.el-card__body) {
  flex-grow: 1; /* 占据 main-card 中除去 header 后的所有剩余垂直空间 */
  padding: 0 !important; /* 强制移除 Element Plus 默认的内边距，让画布完全贴合 */
  display: flex; /* 启用 Flexbox 布局，使其子元素 (canvas-wrapper) 可以伸展 */
  overflow: hidden; /* 隐藏溢出内容 */
  position: relative; /* 为 canvas-empty 的绝对定位提供上下文 */
  min-height: 0; /* 防止内容溢出 */
  height: 100%; /* 确保在父容器 (main-card) 中占据所有可用高度 */
}

/* 头部工具栏样式 */
.header-with-toolbar {
  display: flex;
  flex-wrap: wrap; /* 允许工具栏项目换行 */
  gap: 10px; /* 标题和工具栏之间的间距 */
  align-items: center;
}

.current-image-filename {
  flex-grow: 0;
  flex-shrink: 1;
  flex-basis: auto;
  max-width: 50%;
  min-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 16px;
  font-weight: bold;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  flex-grow: 1;
  min-width: min-content;
  justify-content: flex-end;
}

.toolbar > * {
  flex-shrink: 0;
}

/* 画布容器：占据所有可用空间 */
.canvas-wrapper {
  position: relative;
  width: 100%; /* 填满父容器宽度 */
  height: 100%; /* 填满父容器高度 */
  flex-grow: 1; /* 确保在父容器 (el-card__body) 中占据所有可用空间 */
  display: flex; /* 使内部 canvas 居中 */
  justify-content: center;
  align-items: center;
  background-color: #eee;
  overflow: hidden; /* 隐藏超出画布的内容 */
  min-height: 0; /* 防止内容溢出 */
}

/* Fabric.js 会自动设置 canvas 元素的宽度和高度 */
.annotation-canvas {
  display: block;
}

/* 空状态提示 */
.canvas-empty {
  position: absolute;
  width: 100%;
  height: 100%;
  background-color: #fff;
  z-index: 10;
  display: flex; /* 确保 empty 内部内容居中 */
  justify-content: center;
  align-items: center;
}
</style>
