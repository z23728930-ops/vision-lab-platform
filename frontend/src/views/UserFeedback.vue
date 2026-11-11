<template>
  <div class="page">
    <h2>用户评价与建议</h2>
    <p class="intro">帮助我们持续改进工业视觉实训与智能质检流程。</p>
    <el-card class="form">
      <el-form label-width="90px">
        <el-form-item label="评分"><el-rate v-model="form.score"/></el-form-item>
        <el-form-item label="使用场景">
          <el-select v-model="form.scene" placeholder="请选择">
            <el-option label="课程实训" value="课程实训"/>
            <el-option label="工业质检演示" value="工业质检演示"/>
            <el-option label="模型测试" value="模型测试"/>
          </el-select>
        </el-form-item>
        <el-form-item label="评价内容">
          <el-input v-model="form.text" type="textarea" :rows="4" placeholder="请填写使用体验或改进建议"/>
        </el-form-item>
        <el-button type="primary" @click="submit">提交评价</el-button>
      </el-form>
    </el-card>
    <el-card v-if="submitted" class="thanks">感谢你的评价！我们会根据反馈持续改进实训流程。</el-card>
  </div>
</template>
<script setup>
import { reactive, ref } from 'vue';
import { ElMessage } from 'element-plus';
const form = reactive({ score: 0, scene: '', text: '' });
const submitted = ref(false);
const submit = () => {
  if (!form.score || !form.text) {
    ElMessage.warning('请填写评分和评价内容');
    return;
  }
  submitted.value = true;
  ElMessage.success('评价已提交');
};
</script>
<style scoped>
.form { max-width: 760px; }
.thanks { margin-top: 16px; color: #1e6fff; }
</style>
