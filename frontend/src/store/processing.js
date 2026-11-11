import { defineStore } from 'pinia';
import { createProcessingJob, fetchProcessingJobStatus } from '../api/processing';
import { ElNotification } from 'element-plus';
import emitter from "../utils/eventBus.js";

export const useProcessingStore = defineStore('processing', {
    state: () => ({
        activeJobs: new Map(), // 使用Map来存储正在轮询的任务，key为jobId
    }),
    actions: {
        async startJob(jobConfig) {
            try {
                const response = await createProcessingJob(jobConfig);
                const newJob = response.data;

                ElNotification({
                    title: '任务已提交',
                    message: `预处理任务 #${newJob.id} 已开始，请稍后在数据管理页面查看结果。`,
                    type: 'info',
                    duration: 5000,
                });

                // 将新任务加入轮询队列
                this.activeJobs.set(newJob.id, { status: newJob.status, progress: newJob.progress });
                this.pollJobStatus(newJob.id);

                return newJob.id;
            } catch (error) {
                ElNotification({
                    title: '任务提交失败',
                    message: error.response?.data?.detail || '无法创建预处理任务',
                    type: 'error',
                });
                return null;
            }
        },

        pollJobStatus(jobId) {
            const intervalId = setInterval(async () => {
                try {
                    const response = await fetchProcessingJobStatus(jobId);
                    const job = response.data;

                    this.activeJobs.set(jobId, { status: job.status, progress: job.progress });

                    if (job.status === 'completed' || job.status === 'failed') {
                        clearInterval(intervalId); // 停止轮询
                        this.activeJobs.delete(jobId); // 从队列中移除


                        ElNotification({
                            title: `任务 #${jobId} 已完成`,
                            message: `状态: ${job.status}`,
                            type: job.status === 'completed' ? 'success' : 'error',
                            duration: 0, // 永久显示，直到用户关闭
                        });
                        // 可以在这里触发一个事件，让数据集列表刷新
                        // eventBus.emit('refresh-datasets');
                        if (job.status === 'completed') {
                            emitter.emit('refresh-datasets'); // 发出事件
                        }
                    }
                } catch (error) {
                    console.error(`Polling for job ${jobId} failed:`, error);
                    clearInterval(intervalId);
                    this.activeJobs.delete(jobId);
                }
            }, 5000); // 每5秒查询一次状态
        },
    },
});