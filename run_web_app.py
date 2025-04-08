"""
深度研究 Agent 网页应用启动脚本
"""

import os
import sys
import logging
import traceback
from datetime import datetime

# 配置日志
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"webapp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("deep_research")

if __name__ == "__main__":
    try:
        # 创建必要的目录
        logger.info("创建必要的目录")
        #os.makedirs("deep_research/uploads", exist_ok=True)
        #os.makedirs("deep_research/results", exist_ok=True)
        
        # 从命令行参数获取主机和端口(如果有)
        host = '127.0.0.1'  # 默认只监听本地接口
        port = 5000  # 默认端口
        
        # 检查命令行参数
        if len(sys.argv) > 1:
            try:
                port = int(sys.argv[1])
            except ValueError:
                logger.warning(f"警告: 无效的端口号 '{sys.argv[1]}'，使用默认端口 5000")
        
        logger.info(f"启动深度研究 Agent 网页应用...")
        logger.info(f"服务器将在 http://localhost:{port} 上运行")
        logger.info("按 Ctrl+C 停止服务器")
        
        # 导入Flask应用
        from web_app import run_app
        
        # 运行Flask应用
        run_app(host=host, port=port, debug=True)
    except Exception as e:
        error_msg = f"启动服务器时出错: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        print(error_msg)
        sys.exit(1) 