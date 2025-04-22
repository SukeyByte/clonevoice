import subprocess
import sys
import os
import signal
import time
from typing import Dict, List
from dotenv import load_dotenv

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

# Load environment variables
load_dotenv()

# Service configurations
SERVICES = {
    'api': {
        'name': 'API Service',
        'module': 'api_service.main',
        'port': int(os.getenv('API_SERVICE_PORT', 8000))
    },
    'video': {
        'name': 'Video Service',
        'module': 'video_service.main',
        'port': int(os.getenv('VIDEO_SERVICE_PORT', 8001))
    },
    'audio': {
        'name': 'Audio Service',
        'module': 'audio_service.main',
        'port': int(os.getenv('AUDIO_SERVICE_PORT', 8002))
    }
}

class ServiceManager:
    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}
        self.is_running = True
        self.startup_timeout = 30  # Seconds to wait for service startup

    def start_service(self, service_id: str, service_config: dict):
        """Start a single service"""
        try:
            # Set PYTHONPATH and working directory
            env = os.environ.copy()
            env["PYTHONPATH"] = project_root
            
            # Use project root as working directory instead of individual service dirs
            process = subprocess.Popen(
                [sys.executable, "-m", service_config['module']],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
                cwd=project_root,  # Changed to use project root
                env=env
            )
            
            # Wait for service to initialize
            start_time = time.time()
            while time.time() - start_time < self.startup_timeout:
                if process.poll() is not None:
                    raise Exception(f"Service exited with code {process.poll()}")
                
                # Check stdout/stderr for startup messages
                line = process.stdout.readline() if process.stdout else ""
                error = process.stderr.readline() if process.stderr else ""
                
                if "服务启动" in line or "service started" in line.lower():
                    self.processes[service_id] = process
                    print(f"✅ {service_config['name']} started on port {service_config['port']}")
                    return True
                    
                if error:
                    print(f"[{service_config['name']} ERROR] {error.strip()}")
                    
                time.sleep(0.1)
                
            raise TimeoutError(f"Service startup timeout after {self.startup_timeout}s")
            
        except Exception as e:
            print(f"❌ {service_config['name']} failed to start: {str(e)}")
            if service_id in self.processes:
                self.processes[service_id].terminate()
                del self.processes[service_id]
            return False

    def start_all_services(self):
        """Start all services in correct order"""
        print("🚀 Starting all services...")
        
        # Start services in dependency order
        service_order = ['api', 'video', 'audio']
        for service_id in service_order:
            if not self.start_service(service_id, SERVICES[service_id]):
                print(f"❌ Failed to start {SERVICES[service_id]['name']}, stopping all services...")
                self.stop_all_services()
                sys.exit(1)
            time.sleep(2)  # Wait between service starts

    def monitor_output(self):
        """监控所有服务的输出"""
        while self.is_running:
            for service_id, process in self.processes.items():
                service_name = SERVICES[service_id]['name']
                
                # 检查stdout
                if process.stdout and process.stdout.readable():
                    while True:
                        output = process.stdout.readline()
                        if not output:
                            break
                        print(f"[{service_name}] {output.strip()}")
                
                # 检查stderr
                if process.stderr and process.stderr.readable():
                    while True:
                        error = process.stderr.readline()
                        if not error:
                            break
                        print(f"[{service_name} ERROR] {error.strip()}")

                # 检查进程状态
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