"""
MSST WebUI - PyTorch 自动安装工具

自动检测系统 GPU 和 CUDA 版本，安装兼容的 PyTorch。
支持场景：
  - NVIDIA GPU（自动匹配 CUDA 版本）
  - 无 NVIDIA GPU（安装 CPU 版本）
"""

import subprocess
import sys
import re
import os


def run_cmd(cmd, timeout=30):
    """执行命令并返回输出"""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, shell=True
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except FileNotFoundError:
        return -1, "", "command not found"
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"


def detect_nvidia_gpu():
    """检测 NVIDIA GPU 信息"""
    code, stdout, _ = run_cmd("nvidia-smi --query-gpu=name,driver_version --format=csv,noheader,nounits")
    if code != 0 or not stdout:
        return None, None

    lines = stdout.strip().split("\n")
    gpu_name = lines[0].split(",")[0].strip()
    driver_version = lines[0].split(",")[1].strip() if "," in lines[0] else "unknown"
    return gpu_name, driver_version


def detect_cuda_version():
    """通过 nvidia-smi 检测系统支持的最高 CUDA 版本"""
    code, stdout, _ = run_cmd("nvidia-smi")
    if code != 0 or not stdout:
        return None

    match = re.search(r"CUDA Version:\s*(\d+\.\d+)", stdout)
    if match:
        return match.group(1)
    return None


def get_compute_capability():
    """尝试获取 GPU 的计算能力"""
    code, stdout, _ = run_cmd(
        "nvidia-smi --query-gpu=compute_cap --format=csv,noheader,nounits"
    )
    if code != 0 or not stdout:
        return None
    try:
        return float(stdout.strip().split("\n")[0])
    except (ValueError, IndexError):
        return None


def select_cuda_torch_version(cuda_version_str):
    """
    根据系统 CUDA 版本选择合适的 PyTorch CUDA 索引。
    PyTorch 官方提供的 CUDA 版本：cu118, cu121, cu124, cu126
    """
    if not cuda_version_str:
        return "cpu"

    try:
        cuda_ver = float(cuda_version_str)
    except ValueError:
        return "cpu"

    # PyTorch 官方可用的 CUDA 版本（从高到低）
    available = [
        (12.6, "cu126"),
        (12.4, "cu124"),
        (12.1, "cu121"),
        (11.8, "cu118"),
    ]

    for min_ver, tag in available:
        if cuda_ver >= min_ver:
            return tag

    if cuda_ver >= 11.0:
        return "cu118"

    return "cpu"


def check_current_torch():
    """检查当前安装的 PyTorch 版本和 CUDA 支持"""
    try:
        import torch
        ver = torch.__version__
        cuda_available = torch.cuda.is_available()
        cuda_ver = torch.version.cuda if hasattr(torch.version, 'cuda') else None
        return ver, cuda_available, cuda_ver
    except ImportError:
        return None, False, None


def install_pytorch(cuda_tag):
    """安装对应版本的 PyTorch"""
    python = sys.executable

    if cuda_tag == "cpu":
        index_url = "https://download.pytorch.org/whl/cpu"
        print(f"\n将安装 CPU 版本的 PyTorch")
    else:
        index_url = f"https://download.pytorch.org/whl/{cuda_tag}"
        print(f"\n将安装 CUDA {cuda_tag} 版本的 PyTorch")

    print(f"下载源: {index_url}")
    print("正在安装，请稍候（首次安装可能需要较长时间）...\n")

    cmd = [
        python, "-m", "pip", "install",
        "torch", "torchvision", "torchaudio",
        "--index-url", index_url,
        "--force-reinstall"
    ]

    result = subprocess.run(cmd)
    return result.returncode == 0


def verify_installation():
    """验证 PyTorch 安装"""
    python = sys.executable
    code, stdout, stderr = run_cmd(
        f'"{python}" -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.version.cuda if torch.cuda.is_available() else \'N/A\')"'
    )
    if code == 0:
        lines = stdout.strip().split("\n")
        if len(lines) >= 3:
            return lines[0], lines[1] == "True", lines[2]
    return None, False, None


def main():
    print("=" * 50)
    print("  PyTorch 自动安装工具")
    print("=" * 50)

    # 1. 检测 GPU
    print("\n[1/5] 检测 GPU...")
    gpu_name, driver_ver = detect_nvidia_gpu()
    if gpu_name:
        print(f"  检测到 NVIDIA GPU: {gpu_name}")
        print(f"  驱动版本: {driver_ver}")
    else:
        print("  未检测到 NVIDIA GPU")

    # 2. 检测 CUDA
    print("\n[2/5] 检测 CUDA 版本...")
    cuda_version = detect_cuda_version()
    if cuda_version:
        print(f"  系统支持的 CUDA 版本: {cuda_version}")
    else:
        print("  未检测到 CUDA 支持")

    # 3. 检测计算能力
    cc = get_compute_capability()
    if cc:
        print(f"  GPU 计算能力: {cc}")
        if cc < 3.5:
            print("  [警告] GPU 计算能力较低，可能不支持较新版本的 PyTorch")

    # 4. 选择合适的版本
    print("\n[3/5] 选择合适的 PyTorch 版本...")
    cuda_tag = select_cuda_torch_version(cuda_version)
    print(f"  选择的版本标签: {cuda_tag}")

    # 5. 检查当前安装
    print("\n[4/5] 检查当前 PyTorch 安装...")
    current_ver, current_cuda, current_cuda_ver = check_current_torch()
    if current_ver:
        print(f"  当前版本: {current_ver}")
        print(f"  CUDA 可用: {current_cuda}")
        print(f"  CUDA 版本: {current_cuda_ver}")

        if current_cuda and cuda_tag != "cpu":
            expected_major = cuda_tag.replace("cu", "")[:2]
            if current_cuda_ver and current_cuda_ver.replace(".", "").startswith(expected_major):
                print("\n  当前 PyTorch 版本已兼容，无需重新安装。")
                print("  如需强制重新安装，请添加 --force 参数运行。")
                if "--force" not in sys.argv:
                    return 0
        elif not current_cuda and cuda_tag != "cpu":
            print("  当前安装不支持 CUDA，需要重新安装。")
    else:
        print("  未检测到 PyTorch 安装")

    # 6. 安装
    print("\n[5/5] 安装 PyTorch...")
    success = install_pytorch(cuda_tag)

    if success:
        print("\n" + "=" * 50)
        print("  安装完成！正在验证...")
        print("=" * 50)

        ver, cuda_ok, cuda_v = verify_installation()
        if ver:
            print(f"\n  PyTorch 版本: {ver}")
            print(f"  CUDA 可用: {cuda_ok}")
            if cuda_ok:
                print(f"  CUDA 版本: {cuda_v}")
            print("\n  PyTorch 安装成功！")
        else:
            print("\n  [警告] 安装后验证失败，请手动检查")
        return 0
    else:
        print("\n  [错误] 安装失败，请检查网络连接或手动安装")
        print(f"  手动安装命令:")
        if cuda_tag == "cpu":
            print(f"  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu")
        else:
            print(f"  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/{cuda_tag}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
