import os
import re
import time
import uuid
import shutil
import threading
import subprocess
from pathlib import Path
from typing import Dict, Any
import asyncio
import mimetypes

import gradio as gr
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse

# -----------------------------
# 路径：按你项目结构来（根目录）
# -----------------------------
ROOT = Path(__file__).resolve().parent
PYTHON = (ROOT / "workenv" / "python.exe").resolve()
SCRIPT = (ROOT / "clientui" / "preset_infer_cli.py").resolve()
PRESET = (ROOT / "presets"/"提取干声（不含和声、混响）.json").resolve()

WORKDIR = ROOT / "_api_jobs"
WORKDIR.mkdir(parents=True, exist_ok=True)

# -----------------------------
# FastAPI 主 app（单端口）
# -----------------------------
app = FastAPI(title="MSST WebUI + API (single port 7861)")


@app.get("/")
def root():
    return RedirectResponse(url="/ui")


# -----------------------------
# 简单任务表（内存版）
# -----------------------------
JOBS: Dict[str, Dict[str, Any]] = {}
JOBS_LOCK = threading.Lock()

# 建议先限制并发为 1（避免抢 GPU / 显存爆）
GPU_SEM = threading.Semaphore(1)


def _set_job(job_id: str, **kwargs):
    with JOBS_LOCK:
        JOBS.setdefault(job_id, {})
        JOBS[job_id].update(kwargs)


def _get_job(job_id: str) -> Dict[str, Any]:
    with JOBS_LOCK:
        if job_id not in JOBS:
            raise KeyError(job_id)
        return dict(JOBS[job_id])


def _safe_rmtree(p: Path):
    shutil.rmtree(p, ignore_errors=True)


def _safe_filename(name: str) -> str:
    """
    防止用户传入奇怪文件名/字符：只保留 a-zA-Z0-9._-
    同时去掉路径（避免 ../ 穿越）
    """
    name = Path(name).name
    name = re.sub(r"[^a-zA-Z0-9._-]+", "_", name)
    return name or "input.wav"


def _pick_output_wav(output_dir: Path) -> Path:
    """
    从输出目录里找一个 wav（取最后修改时间最新的）
    """
    wavs = list(output_dir.rglob("*.wav"))
    if not wavs:
        raise FileNotFoundError("no .wav output generated")
    wavs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return wavs[0]


def _run_infer(job_id: str, input_dir: Path, output_dir: Path):
    """
    后台执行推理（阻塞）：input_dir -> preset_infer_cli.py -> output_dir
    固定输出 wav（-f wav）
    """
    with GPU_SEM:
        start = time.time()
        job_dir = WORKDIR / job_id
        log_path = job_dir / "run.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            str(PYTHON),
            str(SCRIPT),
            "-p", str(PRESET),
            "-i", str(input_dir),
            "-o", str(output_dir),
            "-f", "wav",
        ]

        _set_job(job_id, status="running", started_at=time.time(), cmd=cmd, log=str(log_path))

        try:
            with open(log_path, "w", encoding="utf-8") as f:
                p = subprocess.Popen(
                    cmd,
                    cwd=str(ROOT),  # 保持在工程根目录跑
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    text=True
                )
                ret = p.wait()

            if ret != 0:
                _set_job(job_id, status="failed", finished_at=time.time(), return_code=ret)
                return

            _set_job(
                job_id,
                status="completed",
                finished_at=time.time(),
                seconds=round(time.time() - start, 2),
            )
        except Exception as e:
            _set_job(job_id, status="failed", finished_at=time.time(), error=str(e))


# -----------------------------
# API：单文件推理（返回 wav）
# -----------------------------
@app.post("/infer")
async def infer(
    audio_file: UploadFile = File(..., description="上传一个音频文件（一次只处理一个）"),
    background_tasks: BackgroundTasks = None,
):
    # 基础校验
    if not PYTHON.exists():
        raise HTTPException(500, f"python.exe not found: {PYTHON}")
    if not SCRIPT.exists():
        raise HTTPException(500, f"script not found: {SCRIPT}")
    if not PRESET.exists():
        raise HTTPException(500, f"preset not found: {PRESET}")

    # 允许的后缀（你可以按需增减）
    raw_name = audio_file.filename or "input.wav"
    filename = _safe_filename(raw_name)
    ext = Path(filename).suffix.lower()
    if ext not in {".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg"}:
        raise HTTPException(400, f"unsupported file type: {filename}")

    job_id = uuid.uuid4().hex
    job_dir = WORKDIR / job_id
    in_dir = job_dir / "input"
    out_dir = job_dir / "output"

    _safe_rmtree(job_dir)
    in_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 由于脚本只吃“输入文件夹”，把单个文件保存到 input 目录
    in_path = in_dir / filename
    try:
        with open(in_path, "wb") as f:
            f.write(await audio_file.read())
    except Exception as e:
        _safe_rmtree(job_dir)
        raise HTTPException(500, f"failed to save upload file: {e}")

    _set_job(job_id, status="queued", created_at=time.time())

    # 运行推理：subprocess 阻塞，丢到线程里执行（避免堵塞 FastAPI）
    await asyncio.to_thread(_run_infer, job_id, in_dir, out_dir)

    # 读取任务结果
    try:
        job = _get_job(job_id)
    except KeyError:
        _safe_rmtree(job_dir)
        raise HTTPException(500, "job status missing")

    if job.get("status") != "completed":
        # 不立刻删目录，方便你排查；也可以选择仍清理
        # 这里返回 job_id 和 log 路径，用户可调用 /tasks/{job_id}/log 拉日志
        raise HTTPException(500, f"infer failed. job_id={job_id}. status={job.get('status')}. log={job.get('log')}")

    # 找到输出 wav
    try:
        out_file = _pick_output_wav(out_dir)
    except Exception as e:
        raise HTTPException(500, f"no output generated: {e}")

    # 返回文件名：原名去后缀 + .wav
    out_name = f"{Path(filename).stem}.wav"

    # 响应完成后清理临时目录（必须用 BackgroundTasks，不能在 return 前删）
    # 注意：如果你想保留失败任务目录用于排查，上面失败分支没加清理。
    if background_tasks is not None:
        background_tasks.add_task(_safe_rmtree, job_dir)

    mime, _ = mimetypes.guess_type(str(out_file))
    if not mime:
        mime = "audio/wav"

    return FileResponse(
        str(out_file),
        filename=out_name,
        media_type=mime,
        headers={"X-Job-Id": job_id},
    )


# -----------------------------
# 调试接口：查任务状态 / 看日志
# -----------------------------
@app.get("/tasks/{job_id}")
def task_status(job_id: str):
    try:
        job = _get_job(job_id)
    except KeyError:
        raise HTTPException(404, "job_id not found")
    return JSONResponse(job)


@app.get("/tasks/{job_id}/log")
def task_log(job_id: str):
    try:
        job = _get_job(job_id)
    except KeyError:
        raise HTTPException(404, "job_id not found")

    log_path = Path(job.get("log", ""))
    if not log_path.exists():
        raise HTTPException(404, "log not found")

    return FileResponse(str(log_path), filename="run.log", media_type="text/plain; charset=utf-8")


# -----------------------------
# 挂载 Gradio UI 到 /ui （同端口）
# -----------------------------
def build_gradio_ui() -> gr.Blocks:
    from utils.constant import WEBUI_CONFIG, THEME_FOLDER
    from webui.utils import load_configs
    from clientui.ui import create_ui
    from client import client_login

    webui_config = load_configs(WEBUI_CONFIG)
    theme_path = os.path.join(THEME_FOLDER, webui_config["settings"].get("theme", "theme_blue.json"))

    # 临时目录（可选）
    os.environ["GRADIO_TEMP_DIR"] = os.path.abspath("MSST_ypd/cache/")

    interface = gr.Blocks(theme=gr.Theme.load(theme_path), title="MSST 客户端")
    with interface:
        create_ui()
    interface._msst_auth = client_login
    return interface


demo = build_gradio_ui()

try:
    app = gr.mount_gradio_app(app, demo, path="/ui", auth=getattr(demo, "_msst_auth", None))
except TypeError:
    app = gr.mount_gradio_app(app, demo, path="/ui", gradio_kwargs={"auth": getattr(demo, "_msst_auth", None)})

if __name__ == "__main__":
    import argparse
    import sys
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=7862)
    parser.add_argument("--daemon", action="store_true")
    args, _unknown = parser.parse_known_args()
    if args.daemon:
        creationflags = 0
        if os.name == "nt":
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | 0x00000008
        cmd = [
            str(PYTHON),
            "-m",
            "uvicorn",
            "msst_api:app",
            "--host",
            str(args.host),
            "--port",
            str(args.port),
        ]
        subprocess.Popen(cmd, cwd=str(ROOT), creationflags=creationflags)
        sys.exit(0)
    else:
        import uvicorn
        uvicorn.run(app, host=args.host, port=args.port)
