const taskForm = document.getElementById('task-form');
const topicInput = document.getElementById('topic');
const statusOutput = document.getElementById('status-output');
const resultsOutput = document.getElementById('results-output');
const sortMethodSelect = document.getElementById('sort-method');
const applySortButton = document.getElementById('apply-sort');
const API_BASE_URL = "/api/v1"; // Adjust if needed

let currentTaskId = null;
let pollIntervalId = null;
let currentResults = null; // 存储当前结果数据

taskForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    clearPreviousResults();

    const topic = topicInput.value;
    const selectedConferences = Array.from(document.querySelectorAll('input[name="conference"]:checked'))
                                     .map(cb => cb.value);

    statusOutput.textContent = "提交任务中...";

    try {
        const response = await fetch(`${API_BASE_URL}/tasks`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                 topic: topic,
                 selected_conferences: selectedConferences.length > 0 ? selectedConferences : null
            }),
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(`HTTP error! status: ${response.status}, message: ${errorData.detail || '未知错误'}`);
        }

        const data = await response.json();
        currentTaskId = data.task_id;
        statusOutput.textContent = `任务提交成功! 任务ID: ${currentTaskId}. 正在轮询状态...`;
        startPollingStatus(currentTaskId);

    } catch (error) {
        console.error('提交任务错误:', error);
        statusOutput.textContent = `提交任务错误: ${error.message}`;
    }
});

// 添加排序按钮事件监听
applySortButton.addEventListener('click', () => {
    if (currentResults) {
        const sortMethod = sortMethodSelect.value;
        renderResults(currentResults, sortMethod);
    }
});

function startPollingStatus(taskId) {
    if (pollIntervalId) {
        clearInterval(pollIntervalId); // 清除之前的轮询
    }

    pollIntervalId = setInterval(async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/tasks/${taskId}/status`);
            if (!response.ok) {
                 if (response.status === 404) {
                     statusOutput.textContent = `任务 ${taskId} 未找到. 停止轮询.`;
                     clearInterval(pollIntervalId);
                     return;
                 }
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();

            statusOutput.textContent = `任务ID: ${taskId}\n状态: ${data.status}\n消息: ${data.message || ''}\n创建时间: ${data.created_at}`;

            if (data.status === 'completed' || data.status === 'failed') {
                clearInterval(pollIntervalId);
                pollIntervalId = null;
                if (data.status === 'completed') {
                    fetchResults(taskId);
                }
            }
        } catch (error) {
            console.error('轮询状态错误:', error);
            statusOutput.textContent = `轮询任务 ${taskId} 状态时出错: ${error.message}. 停止轮询.`;
            clearInterval(pollIntervalId);
            pollIntervalId = null;
        }
    }, 3000); // 每3秒轮询一次
}

async function fetchResults(taskId) {
    resultsOutput.innerHTML = '<p>加载结果中...</p>';
    try {
        const response = await fetch(`${API_BASE_URL}/tasks/${taskId}/results?include_papers=true`);
         if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();

        if (data.results) {
             currentResults = data.results; // 存储获取到的结果
             const sortMethod = sortMethodSelect.value; // 获取当前选择的排序方式
             renderResults(data.results, sortMethod);
        } else {
             resultsOutput.innerHTML = '<p>未找到论文结果或结果为空.</p>';
        }

    } catch (error) {
        console.error('获取结果错误:', error);
        resultsOutput.innerHTML = `<p>获取结果错误: ${error.message}</p>`;
    }
}

// 对论文列表进行排序
function sortPapers(papers, sortMethod) {
    // 创建原始数据的拷贝以避免修改原始数据
    const sortedPapers = [...papers];
    
    switch (sortMethod) {
        case 'conference':
            // 顶会优先排序
            sortedPapers.sort((a, b) => {
                // 首先按顶会状态排序
                if (a.is_top_conference && !b.is_top_conference) return -1;
                if (!a.is_top_conference && b.is_top_conference) return 1;
                
                // 如果顶会状态相同，再按年份降序排序（新→旧）
                if (a.year && b.year) return b.year - a.year;
                if (a.year && !b.year) return -1;
                if (!a.year && b.year) return 1;
                
                return 0;
            });
            break;
            
        case 'year-desc':
            // 时间降序（新→旧）
            sortedPapers.sort((a, b) => {
                if (a.year && b.year) return b.year - a.year;
                if (a.year && !b.year) return -1;
                if (!a.year && b.year) return 1;
                return 0;
            });
            break;
            
        case 'year-asc':
            // 时间升序（旧→新）
            sortedPapers.sort((a, b) => {
                if (a.year && b.year) return a.year - b.year;
                if (a.year && !b.year) return 1;
                if (!a.year && b.year) return -1;
                return 0;
            });
            break;
            
        case 'default':
        default:
            // 默认排序，保持原有顺序
            break;
    }
    
    return sortedPapers;
}

function renderResults(results, sortMethod = 'default') {
    resultsOutput.innerHTML = ''; // 清除之前的结果

    for (const [query, papers] of Object.entries(results)) {
        const querySection = document.createElement('div');
        querySection.classList.add('query-section');

        const queryTitle = document.createElement('h3');
        queryTitle.textContent = `查询: "${query}" (${papers.length} 篇论文)`;
        querySection.appendChild(queryTitle);

        if (papers.length === 0) {
            const noResultsP = document.createElement('p');
            noResultsP.textContent = '此查询未找到论文.';
            querySection.appendChild(noResultsP);
        } else {
            // 对论文进行排序
            const sortedPapers = sortPapers(papers, sortMethod);
            
            const ul = document.createElement('ul');
            sortedPapers.forEach(paper => {
                const li = document.createElement('li');
                li.classList.add('paper-item');
                if (paper.is_top_conference) {
                    li.classList.add('top-conference');
                }

                let authorsStr = paper.authors.join(', ');
                if (authorsStr.length > 100) authorsStr = authorsStr.substring(0, 100) + '...'; // 截断过长的作者列表

                li.innerHTML = `
                    <strong>${paper.title || '无标题'}</strong> (${paper.year || 'N/A'}) ${paper.is_top_conference ? '<span class="top-conf-badge">顶会</span>' : ''}<br>
                    <em>作者:</em> ${authorsStr || 'N/A'}<br>
                    <em>来源:</em> ${paper.source || 'N/A'} ${paper.doi ? `| DOI: ${paper.doi}` : ''} ${paper.arxiv_id ? `| arXiv: ${paper.arxiv_id}` : ''}<br>
                    ${paper.url ? `<a href="${paper.url}" target="_blank">链接</a><br>` : ''}
                    <details>
                        <summary>摘要</summary>
                        <p>${paper.abstract || '无摘要.'}</p>
                    </details>
                `;
                ul.appendChild(li);
            });
            querySection.appendChild(ul);
        }
        resultsOutput.appendChild(querySection);
    }

    if (Object.keys(results).length === 0) {
        resultsOutput.innerHTML = '<p>此任务的所有查询都未找到结果.</p>';
    }
}

function clearPreviousResults() {
    if (pollIntervalId) {
        clearInterval(pollIntervalId);
        pollIntervalId = null;
    }
    currentTaskId = null;
    currentResults = null; // 清除结果数据
    statusOutput.textContent = '提交任务查看状态...';
    resultsOutput.innerHTML = '';
} 