import subprocess
import sys
import os
import signal
import time
from typing import Dict, List
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 服务配置
SERVICES = {
    'api': {
        'name': 'API Service',
        'path': 'api_service/main.py',
        'port': int(os.getenv('API_SERVICE_PORT', 8000))
    },
    'video': {
        'name': 'Video Service',
        'path': 'video_service/main.py',
        'port': int(os.getenv('VIDEO_SERVICE_PORT', 8001))
    },
    'audio': {
        'name': 'Audio Service',
        'path': 'audio_service/main.py',
        'port': int(os.getenv('AUDIO_SERVICE_PORT', 8002))
    }
}

class ServiceManager:
    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}
        self.is_running = True

    def start_service(self, service_id: str, service_config: dict):
        """启动单个服务"""
        try:
            # 使用Python解释器启动服务，并开启reload模式
            process = subprocess.Popen(
                [sys.executable, service_config['path']],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            self.processes[service_id] = process
            print(f"✅ {service_config['name']} 已启动在端口 {service_config['port']}")
            return True
        except Exception as e:
            print(f"❌ {service_config['name']} 启动失败: {str(e)}")
            return False

    def start_all_services(self):
        """启动所有服务"""
        print("🚀 正在启动所有服务...")
        for service_id, config in SERVICES.items():
            self.start_service(service_id, config)

    def monitor_output(self):
        """监控所有服务的输出"""
        while self.is_running:
            for service_id, process in self.processes.items():
                service_name = SERVICES[service_id]['name']
                # 检查stdout
                if process.stdout.readable():
                    output = process.stdout.readline()
                    if output:
                        print(f"[{service_name}] {output}", end='')
                # 检查stderr
                if process.stderr.readable():
                    error = process.stderr.readline()
                    if error:
                        print(f"[{service_name} ERROR] {error}", end='')

                # 检查进程是否还在运行
                if process.poll() is not None:
                    print(f"⚠️ {service_name} 已停止运行，正在尝试重启...")
                    self.start_service(service_id, SERVICES[service_id])

            time.sleep(0.1)

    def stop_all_services(self):
        """停止所有服务"""
        print("\n🛑 正在停止所有服务...")
        self.is_running = False
        for service_id, process in self.processes.items():
            service_name = SERVICES[service_id]['name']
            try:
                process.terminate()
                process.wait(timeout=5)
                print(f"✅ {service_name} 已停止")
            except subprocess.TimeoutExpired:
                process.kill()
                print(f"⚠️ {service_name} 被强制终止")
            except Exception as e:
                print(f"❌ {service_name} 停止失败: {str(e)}")

def signal_handler(signum, frame):
    """信号处理函数"""
    print("\n收到终止信号，正在关闭服务...")
    manager.stop_all_services()
    sys.exit(0)

if __name__ == "__main__":
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        manager = ServiceManager()
        manager.start_all_services()
        print("\n🔍 正在监控服务输出...按 Ctrl+C 停止所有服务\n")
        manager.monitor_output()
    except KeyboardInterrupt:
        manager.stop_all_services()
    except Exception as e:
        print(f"❌ 发生错误: {str(e)}")
        manager.stop_all_services()
        sys.exit(1)