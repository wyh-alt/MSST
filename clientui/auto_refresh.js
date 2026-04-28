// 任务状态自动刷新脚本
let autoRefreshInterval = null;

// 开始自动刷新任务状态
function startAutoRefresh() {
  if (autoRefreshInterval) {
    clearInterval(autoRefreshInterval);
  }
  
  // 每30秒刷新一次任务状态
  autoRefreshInterval = setInterval(() => {
    const refreshButton = document.querySelector('button:contains("刷新任务状态")');
    if (refreshButton) {
      refreshButton.click();
    }
  }, 30000);
}

// 停止自动刷新
function stopAutoRefresh() {
  if (autoRefreshInterval) {
    clearInterval(autoRefreshInterval);
    autoRefreshInterval = null;
  }
}

// 在任务管理标签页激活时启动自动刷新
document.addEventListener("DOMContentLoaded", function() {
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (mutation.type === 'attributes' && mutation.attributeName === 'aria-selected') {
        const missionTab = document.querySelector('button[role="tab"]:contains("任务管理")');
        if (missionTab && missionTab.getAttribute('aria-selected') === 'true') {
          startAutoRefresh();
        } else {
          stopAutoRefresh();
        }
      }
    });
  });
  
  // 监听标签页切换
  setTimeout(() => {
    const tabs = document.querySelectorAll('button[role="tab"]');
    tabs.forEach(tab => {
      observer.observe(tab, { attributes: true });
    });
  }, 2000); // 给页面加载一些时间
});

// 在页面卸载时清理
window.addEventListener('beforeunload', () => {
  stopAutoRefresh();
});
