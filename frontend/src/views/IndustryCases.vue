<template>
  <div class="page">
    <!-- Headline -->
    <div class="page-head">
      <div>
        <h2>工业场景案例</h2>
        <p class="intro">通过真实案例学习工件、缺陷类型与模型的匹配关系。</p>
      </div>
    </div>

    <!-- Case wall -->
    <div class="case-wall">
      <div v-for="c in cases" :key="c.title" class="case-card">
        <div class="case-img-wrap">
          <img :src="c.image" :alt="c.title" class="case-img" />
          <div class="case-img-overlay">
            <div class="case-tags">
              <el-tag size="small" :type="tagType(c.type)" effect="plain">{{ c.level }}</el-tag>
            </div>
          </div>
        </div>
        <div class="case-body">
          <h3 class="case-title">{{ c.title }}</h3>
          <div class="case-specs">
            <div class="spec-row">
              <span class="spec-label">工件</span>
              <span class="spec-value">{{ c.workpiece }}</span>
            </div>
            <div class="spec-row">
              <span class="spec-label">缺陷</span>
              <span class="spec-value">{{ c.defect }}</span>
            </div>
            <div class="spec-row">
              <span class="spec-label">模型</span>
              <span class="spec-value model">{{ c.model }}</span>
            </div>
          </div>
          <el-button type="primary" size="small" plain class="case-cta" @click="openCase(c)">查看详情</el-button>
        </div>
      </div>
    </div>
    <el-dialog v-model="detailVisible" :title="selectedCase?.title || '案例详情'" width="680px">
      <template v-if="selectedCase">
        <div class="detail-hero"><img :src="selectedCase.image" :alt="selectedCase.title" /><div><el-tag :type="tagType(selectedCase.type)" effect="plain">{{ selectedCase.level }}</el-tag><p>{{ selectedCase.description || '工业视觉缺陷检测方案案例。' }}</p></div></div>
        <el-descriptions :column="2" border><el-descriptions-item label="检测工件">{{ selectedCase.workpiece }}</el-descriptions-item><el-descriptions-item label="缺陷类型">{{ selectedCase.defect }}</el-descriptions-item><el-descriptions-item label="推荐模型">{{ selectedCase.model }}</el-descriptions-item><el-descriptions-item label="应用阶段">方案验证/演示</el-descriptions-item></el-descriptions>
        <div class="report-section"><div class="report-heading">结构化报告 <el-tag size="small" type="info">案例方案报告</el-tag></div><div class="report-grid"><div><span>检测流程</span><strong>采集 → 预处理 → 推理 → 结果复核</strong></div><div><span>输出内容</span><strong>缺陷类别、位置、置信度、结果图片</strong></div><div><span>数据要求</span><strong>正常与缺陷样本及标注信息</strong></div><div><span>平台能力</span><strong>任务追踪、报告导出、异常回流</strong></div></div><el-alert title="说明" type="info" :closable="false" show-icon>这里展示案例方案的结构化信息；执行真实推理后，请到“推理中心”任务详情查看 JSON/CSV 报告。</el-alert></div>
      </template>
      <template #footer><el-button type="primary" @click="detailVisible = false">关闭</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue';
const tagType = (t) => t === 'success' ? 'success' : t === 'primary' ? 'primary' : 'info';
const detailVisible = ref(false);
const selectedCase = ref(null);
const openCase = (item) => { selectedCase.value = item; detailVisible.value = true; };

const cases = [
  { title: '金属板表面检测', workpiece: '金属片、铝板', defect: '划痕、裂纹、锈蚀', model: 'UNet 裂纹分割模型', level: '推荐演示', type: 'success', image: '/images/carousel-robot.jpg' },
  { title: '包装外观检测', workpiece: '纸箱、硬纸板', defect: '破损、污渍、孔洞', model: 'YOLO 缺陷检测模型', level: '可扩展', type: 'primary', image: '/images/carousel-factory.jpg' },
  { title: '零件装配检查', workpiece: '机械零件', defect: '缺件、错装、位置偏移', model: '目标检测模型', level: '需专用数据', type: 'info', image: '/images/carousel-ai.jpg' },
  { title: '电子元件检测', workpiece: 'PCB、芯片封装', defect: '焊点不良、缺件、短路', model: '高精度检测模型', level: '推荐演示', type: 'success', image: '/images/carousel-pcb.jpg' },
  { title: '智能工厂产线巡检', workpiece: '输送线与工位', defect: '漏检、姿态异常', model: '视觉巡检模型', level: '实训场景', type: 'info', image: '/images/carousel-training.jpg' },
  { title: 'AI 模型训练示范', workpiece: '工业视觉数据集', defect: '样本偏差与过拟合', model: '分割 / 检测联合训练', level: '教学示范', type: 'primary', image: '/images/carousel-ai.jpg' }
];
</script>

<style scoped>
.page { padding: 20px 24px; }

.page-head { margin-bottom: 24px; }
.page-head h2 {
  margin: 0 0 6px;
  font-size: 1.375rem;
  font-weight: 700;
  color: #0f2a44;
  letter-spacing: -0.01em;
}
.intro { margin: 0; font-size: 0.9rem; color: #6b7c93; }

/* Case wall - 3-col grid */
.case-wall {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 18px;
}

.case-card {
  background: #fff;
  border: 1px solid rgba(30, 111, 255, 0.1);
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(15, 42, 68, 0.07);
  transition:
    transform 0.22s cubic-bezier(0.16, 1, 0.3, 1),
    box-shadow 0.22s cubic-bezier(0.16, 1, 0.3, 1);
}
.case-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 16px 40px rgba(30, 111, 255, 0.14);
}

.case-img-wrap { position: relative; height: 200px; overflow: hidden; }
.case-img { width: 100%; height: 100%; object-fit: cover; display: block; transition: transform 0.4s ease; }
.case-card:hover .case-img { transform: scale(1.04); }

.case-img-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, transparent 50%, rgba(11, 31, 53, 0.5));
  display: flex;
  align-items: flex-end;
  padding: 12px 14px;
}
.case-tags { display: flex; gap: 6px; flex-wrap: wrap; }

.case-body { padding: 18px 18px 16px; }

.case-title {
  margin: 0 0 12px;
  font-size: 1rem;
  font-weight: 700;
  color: #0f2a44;
  letter-spacing: -0.01em;
}

.case-specs { display: flex; flex-direction: column; gap: 6px; margin-bottom: 16px; }
.spec-row { display: flex; align-items: baseline; gap: 8px; }
.spec-label {
  font-size: 0.72rem;
  font-weight: 700;
  color: #6b7c93;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  flex-shrink: 0;
  width: 36px;
}
.spec-value { font-size: 0.82rem; color: #4a607a; line-height: 1.5; }
.spec-value.model { color: #1e6fff; font-weight: 600; }

.case-cta {
  width: 100%;
  border-radius: 10px !important;
  font-weight: 600;
}
.detail-hero { display: flex; gap: 18px; align-items: center; margin-bottom: 18px; }
.detail-hero img { width: 220px; height: 130px; object-fit: cover; border-radius: 12px; }
.detail-hero p { margin: 12px 0 0; color: #5f7187; line-height: 1.7; }
.report-section { margin-top: 20px; padding-top: 16px; border-top: 1px solid #e6eef8; }
.report-heading { display: flex; justify-content: space-between; align-items: center; color: #0f2a44; font-weight: 700; margin-bottom: 12px; }
.report-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-bottom: 14px; }
.report-grid div { padding: 12px; background: #f5f9ff; border-radius: 10px; }
.report-grid span, .report-grid strong { display: block; }
.report-grid span { color: #71839a; font-size: 12px; margin-bottom: 5px; }
.report-grid strong { color: #244664; font-size: 13px; line-height: 1.5; }

@media (max-width: 1024px) { .case-wall { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 640px)  { .case-wall { grid-template-columns: 1fr; } }
</style>
