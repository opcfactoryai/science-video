"""从 script.json 读取分镜提示词，逐镜调用 gpt-image-2 生成图片
支持 SSE 流式输出，直接保存为 PNG。

用法:
  python gen_scenes.py --project-dir projects/xxx
  python gen_scenes.py --project-dir projects/xxx --limit 3

环境变量:
  IMAGE_API_KEY          (必填) API 密钥
  IMAGE_API_URL          (可选) API 端点，默认 https://api.apikey.fun/v1/images/generations
  IMAGE_MODEL            (可选) 模型名，默认 gpt-image-2
  IMAGE_SIZE             (可选) 强制指定尺寸，如 "1024x1024"；不设则从 script.json 自动推算
"""
import argparse
import base64
import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── 环境变量 ────────────────────────────────────────────────────────
API_KEY = os.environ.get("IMAGE_API_KEY")
if not API_KEY:
    print("❌ 环境变量 IMAGE_API_KEY 未设置。请 source .env 或 export IMAGE_API_KEY=xxx")
    sys.exit(1)

API_URL = os.environ.get(
    "IMAGE_API_URL",
    "https://api.apikey.fun/v1/images/generations",
)
MODEL = os.environ.get("IMAGE_MODEL", "gpt-image-2")
# IMAGE_SIZE 环境变量可强制覆盖，否则从 script.json 的 aspect_ratio + quality 自动推算
SIZE_OVERRIDE = os.environ.get("IMAGE_SIZE")

# 分辨率查找表: [比例][质量] → (宽, 高)
RESOLUTION_MAP = {
    "1:1":   {"1K": (1280, 1280),   "2K": (2048, 2048),   "4K": (2880, 2880)},
    "2:3":   {"1K": (848, 1280),    "2K": (1360, 2048),   "4K": (2336, 3520)},
    "3:2":   {"1K": (1280, 848),    "2K": (2048, 1360),   "4K": (3520, 2336)},
    "3:4":   {"1K": (960, 1280),    "2K": (1536, 2048),   "4K": (2480, 3312)},
    "4:3":   {"1K": (1280, 960),    "2K": (2048, 1536),   "4K": (3312, 2480)},
    "4:5":   {"1K": (1024, 1280),   "2K": (1632, 2048),   "4K": (2560, 3216)},
    "5:4":   {"1K": (1280, 1024),   "2K": (2048, 1632),   "4K": (3216, 2560)},
    "9:16":  {"1K": (720, 1280),    "2K": (1152, 2048),   "4K": (2160, 3840)},
    "16:9":  {"1K": (1280, 720),    "2K": (2048, 1152),   "4K": (3840, 2160)},
    "21:9":  {"1K": (1280, 544),    "2K": (2048, 864),    "4K": (3840, 1632)},
}
DEFAULT_ASPECT = "16:9"
DEFAULT_QUALITY = "1K"


def resolve_image_size(script_data: dict) -> str:
    """从 script_data.production_notes 解析 aspect_ratio + quality，返回 '宽x高'。

    取值仅来源于 production_notes（顶层已不再有这两个字段）。
    环境变量 IMAGE_SIZE 可强制覆盖。
    """
    if SIZE_OVERRIDE:
        return SIZE_OVERRIDE

    pn = script_data.get("production_notes", {})
    raw_aspect = pn.get("aspect_ratio") or DEFAULT_ASPECT
    raw_quality = pn.get("quality") or DEFAULT_QUALITY

    # 标准化 quality
    q = raw_quality.upper().replace("K", "K")
    if q in ("HD",):
        q = "1K"
    elif q in ("2K",):
        q = "2K"
    elif q in ("4K", "UHD"):
        q = "4K"

    # 标准化 aspect_ratio: "16:9"、"16/9"、"16x9" 都接受
    a = raw_aspect.replace("/", ":").replace("x", ":").replace("×", ":")

    if a in RESOLUTION_MAP and q in RESOLUTION_MAP[a]:
        w, h = RESOLUTION_MAP[a][q]
    else:
        print(f"⚠️  未识别的比例/质量 {raw_aspect}/{raw_quality}，回退到 {DEFAULT_ASPECT} {DEFAULT_QUALITY}")
        w, h = RESOLUTION_MAP[DEFAULT_ASPECT][DEFAULT_QUALITY]

    size_str = f"{w}x{h}"
    print(f"📐  分辨率: {raw_aspect} {raw_quality} → {size_str}")
    return size_str


# ── SSE 流式解析 ────────────────────────────────────────────────────
def iter_sse(response):
    """解析 SSE 事件流，逐个 yield data 字段内容。"""
    buffer = ""
    while True:
        chunk = response.read(4096)
        if not chunk:
            break
        buffer += chunk.decode("utf-8", errors="replace")
        frames = buffer.split("\n\n")
        buffer = frames.pop()
        for frame in frames:
            # 兼容 data:... 和 data: ...
            data = "\n".join(
                line[5:].strip()
                for line in frame.splitlines()
                if line.startswith("data:")
            ).strip()
            if data and data != "[DONE]":
                yield data


# ── 单张生成 ────────────────────────────────────────────────────────
def generate_one(prompt: str, size: str, timeout: int = 900) -> bytes:
    """调用 API 生成单张图片，返回 PNG bytes。

    请求格式为 OpenAI images/generations 兼容接口 + stream=True,
    响应中监听 image_generation.completed 事件并提取 b64_json。
    """
    body = json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "n": 1,
        "size": size,
        "stream": True,
        "response_format": "b64_json",
    }).encode("utf-8")

    req = urllib.request.Request(
        API_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        },
    )

    with urllib.request.urlopen(req, timeout=timeout) as resp:
        for data in iter_sse(resp):
            event = json.loads(data)
            ev_type = event.get("type", "")

            if ev_type == "image_generation.partial_image":
                # 进度指示
                print(".", end="", flush=True)
                continue

            if ev_type == "image_generation.completed":
                # 兼容两种返回格式
                b64 = (
                    event.get("b64_json")
                    or (event.get("data") or [{}])[0].get("b64_json")
                )
                if b64:
                    return base64.b64decode(b64)
                raise RuntimeError("completed 事件缺少 b64_json")

    raise RuntimeError("流结束但未收到 completed 事件")


# ── 提取提示词 ──────────────────────────────────────────────────────
def collect_prompts(script_data: dict) -> list[tuple[str, str]]:
    """从 scenes[] 提取所有 (场景名, image_prompt) 对。

    注意：scenes 数组已包含 cover 类型（首镜）和 outro 类型（末镜），
    所以不再重复读取顶层 cover/outro 字段。
    """
    items: list[tuple[str, str]] = []

    for s in script_data.get("scenes", []):
        sid = s.get("id", "")
        prompt = s.get("image_prompt", "")
        if prompt:
            items.append((sid, prompt))

    return items


# ── main ────────────────────────────────────────────────────────────
def _fmt_duration(seconds: float) -> str:
    """格式化时长，如 '3秒'、'1分15秒'、'3分02秒'。"""
    if seconds < 60:
        return f"{seconds:.0f}秒"
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m}分{s:02d}秒"


def _print_summary(scene_times: list[dict], total_sec: float, limit: int, ok: int, fail: int, skip: int):
    """打印耗时汇总表格。"""
    print(f"\n{'═' * 56}")
    print(f"  📊 生成汇总（全部 {limit} 镜）")
    print(f"{'═' * 56}")
    print(f"  {'镜头':<20} {'结果':<8} {'耗时':<10} {'大小':<10}")
    print(f"  {'─' * 48}")
    for s in scene_times:
        status_icon = "✅" if s["status"] == "ok" else "❌"
        size = f"{s['size_kb']:.0f} KB" if s["size_kb"] else "—"
        print(f"  {s['name']:<20} {status_icon:<8} {_fmt_duration(s['elapsed']):<10} {size:<10}")
    print(f"  {'─' * 48}")
    print(f"  {'合计':>20}    {'':<8} {_fmt_duration(total_sec):<10} {ok}/{limit} 成功")
    if skip:
        print(f"  ⏭️  跳过 {skip} 个（已存在）")
    print(f"{'═' * 56}\n")


def main():
    parser = argparse.ArgumentParser(
        description="从 script.json 逐镜生成图片（gpt-image-2，流式 SSE），自动跳过已有，缺图补图",
    )
    parser.add_argument(
        "--project-dir", "-d",
        default=".",
        help="项目目录（含 script.json），图片输出到此目录",
    )
    parser.add_argument(
        "--limit", "-n",
        type=int,
        default=0,
        help="只生成前 N 个镜头的图片；0=全部（默认 0）",
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=2,
        help="每镜间隔秒数（默认 2）",
    )
    args = parser.parse_args()

    proj = Path(args.project_dir)
    script_path = proj / "script.json"

    if not script_path.exists():
        print(f"❌ 未找到 {script_path}")
        sys.exit(1)

    with open(script_path, "r", encoding="utf-8") as f:
        script_data = json.load(f)

    items = collect_prompts(script_data)
    if not items:
        print(f"❌ {script_path} 中未找到任何 image_prompt")
        sys.exit(1)

    total = len(items)
    limit = min(args.limit, total) if args.limit > 0 else total

    title = (
        script_data.get("meta", {}).get("title")
        or script_data.get("title")
        or "未命名"
    )
    image_size = resolve_image_size(script_data)
    print(f"🎬 {title}")
    print(f"📁 {proj.resolve()}")
    print(f"🎯 共 {total} 个图片提示词，目标生成 {limit} 个\n")

    t_start_all = time.time()
    scene_times: list[dict] = []
    total_ok = total_fail = total_skip = 0

    # ── 第 1 轮：生成所有缺失的镜头 ──
    for attempt in range(2):  # 最多两轮：首轮 + 一轮补偿
        missing = []
        for name, prompt in items[:limit]:
            safe = re.sub(r"[^\w\-]", "_", name) or "scene"
            fpath = proj / f"{safe}.png"
            if not fpath.exists():
                missing.append((name, prompt, safe))

        if not missing:
            print(f"\n{'=' * 50}")
            print(f"  ✅ 全部 {limit} 个镜头图片已就绪！")
            print(f"{'=' * 50}")
            break

        if attempt == 0:
            existing_count = limit - len(missing)
            if existing_count > 0:
                print(f"  ⏭️  跳过 {existing_count} 个已存在的图片\n")
                total_skip += existing_count
            print(f"{'─' * 50}")
            print(f"  首轮：生成 {len(missing)} 个缺失镜头")
            print(f"{'─' * 50}")
        else:
            print(f"\n{'─' * 50}")
            print(f"  补偿轮：重新生成 {len(missing)} 个仍缺失的镜头")
            print(f"{'─' * 50}")

        round_ok = round_fail = 0
        round_results = []

        for idx, (name, prompt, safe) in enumerate(missing):
            fpath = proj / f"{safe}.png"

            # 补偿轮中可能已被生成
            if fpath.exists():
                print(f"  [{idx + 1}/{len(missing)}] ⏭️  {name} → {safe}.png  (已存在)")
                round_ok += 1
                continue

            t0 = time.time()
            ts0 = datetime.now().strftime("%H:%M:%S")
            print(f"  [{idx + 1}/{len(missing)}] 🖼️  {name} → {safe}.png  ", end="", flush=True)
            print(f"\n        ⏱️  开始 {ts0}", end="", flush=True)

            try:
                img_data = generate_one(prompt, image_size)
                elapsed = time.time() - t0
                with open(fpath, "wb") as f:
                    f.write(img_data)
                size_kb = len(img_data) / 1024
                print(f" ✅ ({size_kb:.0f} KB, {_fmt_duration(elapsed)})")
                round_ok += 1
                round_results.append({"name": name, "file": safe, "status": "ok", "elapsed": elapsed, "size_kb": size_kb})
            except Exception as e:
                elapsed = time.time() - t0
                print(f" ❌ ({_fmt_duration(elapsed)}) {e}")
                round_fail += 1
                round_results.append({"name": name, "file": safe, "status": "fail", "elapsed": elapsed, "size_kb": 0})

            if idx < len(missing) - 1:
                time.sleep(args.delay)

        total_ok += round_ok
        total_fail += round_fail
        scene_times.extend(round_results)

        done_now = total_ok + total_skip
        print(f"\n  📊 本轮: ✅ {round_ok} 成功, ❌ {round_fail} 失败  | 累计: {done_now}/{limit}")

        # 第二轮结束仍缺失 → 报错
        if attempt == 1:
            still_missing = [(n, p, s) for n, p, s in missing
                           if not (proj / f"{s}.png").exists()]
            if still_missing:
                print(f"\n{'=' * 50}")
                print(f"  ❌ 补偿后仍有 {len(still_missing)} 个镜头缺失:")
                for name, _, safe in still_missing:
                    print(f"     - {safe}.png")
                print(f"  请检查后重新运行")
                print(f"{'=' * 50}")
                t_total = time.time() - t_start_all
                _print_summary(scene_times, t_total, limit, total_ok, total_fail, total_skip)
                return 1

    t_total = time.time() - t_start_all
    _print_summary(scene_times, t_total, limit, total_ok, total_fail, total_skip)
    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
