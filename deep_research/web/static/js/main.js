// 深度研究 Agent 网页应用 JavaScript

// 当DOM加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 模型选择变化时更新描述
    const modelSelect = document.getElementById('model');
    if (modelSelect) {
        const modelDescriptions = {
            'deepseek-chat': '通用对话模型，适合大多数研究任务',
            'deepseek-reasoner': '推理能力更强，适合复杂分析'
        };
        
        const modelDescription = document.getElementById('modelDescription');
        
        modelSelect.addEventListener('change', function() {
            const selectedModel = modelSelect.value;
            if (modelDescription && modelDescriptions[selectedModel]) {
                modelDescription.textContent = modelDescriptions[selectedModel];
            }
        });
    }
    
    // 状态页面自动更新
    const statusContainer = document.querySelector('.status-container');
    if (statusContainer && statusContainer.getAttribute('data-auto-update') === 'true') {
        const taskId = statusContainer.getAttribute('data-task-id');
        
        // 定期更新状态
        function updateStatus() {
            fetch(`/api/task_status/${taskId}`)
                .then(response => response.json())
                .then(data => {
                    // 更新进度条
                    const progressBar = document.querySelector('.progress-bar');
                    if (progressBar) {
                        progressBar.style.width = `${data.progress || 0}%`;
                        const progressText = progressBar.querySelector('.progress-text');
                        if (progressText) {
                            progressText.textContent = `${data.progress || 0}%`;
                        }
                    }
                    
                    // 更新状态消息
                    const statusMessage = document.querySelector('.status-message');
                    if (statusMessage) {
                        statusMessage.textContent = data.message || '正在研究...';
                    }
                    
                    // 更新状态文本
                    const statusText = document.querySelector('.status-text');
                    if (statusText) {
                        statusText.textContent = data.status || '运行中';
                    }
                    
                    // 如果状态变为完成或失败，刷新页面
                    if (data.status === 'completed') {
                        window.location.href = `/result/${taskId}`;
                    } else if (data.status === 'failed') {
                        window.location.reload();
                    }
                })
                .catch(error => {
                    console.error('更新状态时出错:', error);
                });
        }
        
        // 每5秒更新一次状态
        setInterval(updateStatus, 5000);
    }
    
    // 研究结果页面 TOC 滚动处理
    const tocLinks = document.querySelectorAll('.toc a');
    if (tocLinks.length > 0) {
        tocLinks.forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                
                const targetId = this.getAttribute('href').substring(1);
                const targetElement = document.getElementById(targetId);
                
                if (targetElement) {
                    // 平滑滚动到目标位置
                    window.scrollTo({
                        top: targetElement.offsetTop - 20,
                        behavior: 'smooth'
                    });
                }
            });
        });
    }
    
    // 表单验证
    const researchForm = document.querySelector('.research-form form');
    if (researchForm) {
        researchForm.addEventListener('submit', function(e) {
            const queryInput = document.getElementById('query');
            if (queryInput && queryInput.value.trim() === '') {
                e.preventDefault();
                
                // 显示错误消息
                let errorMessage = document.querySelector('.error-message');
                if (!errorMessage) {
                    errorMessage = document.createElement('div');
                    errorMessage.className = 'error-message';
                    researchForm.insertBefore(errorMessage, researchForm.firstChild);
                }
                
                errorMessage.textContent = '请输入研究查询';
                queryInput.focus();
            }
        });
    }
}); 