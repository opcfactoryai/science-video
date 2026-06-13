#!/usr/bin/env python3
"""
compose_video.py — Step 5: ffmpeg 合成最终视频

将 script.json 中的每个分镜（scene-XX.png）按 scene_boundaries.json 时间对齐，
用 ffmpeg 合并图片 + TTS 配音（dissolve 转场），输出 MP4。

用法:
    python compose_video.py --project-dir projects/starship-0612
    python compose_video.py --project-dir projects/starship-0612 --tlimit 3
    python compose_video.py --project-dir projects/starship-0612 --dry-run

前置校验:
    - script.json（必选）
    - 每个 scene 的 scene-XX.png 必须存在（无此文件则报错退出）
    - scene_boundaries.json（可选，有则精确对齐配音；无则用 script duration_seconds）
    - TTS *.mp3（可选，有则合成配音；无则纯视频）
"""
import argparse
import io
import json
import re
import subprocess
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ── 分辨率查找表（与 gen_scenes.py 一致） ──────────────────────────────
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
DEFAULT_FADE = 0.5  # dissolve 转场秒数
DEFAULT_FPS = 30


# ── 工具函数 ──────────────────────────────────────────────────────────

def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def resolve_output_size(script_data: dict) -> tuple[int, int, int]:
    """从 production_notes 解析输出分辨率 + fps"""
    pn = script_data.get("production_notes", {})
    raw_aspect = pn.get("aspect_ratio", DEFAULT_ASPECT)
    raw_quality = pn.get("quality", DEFAULT_QUALITY)
    raw_fps = pn.get("fps", DEFAULT_FPS)

    q = raw_quality.upper().replace("K", "K")
    if q not in ("1K", "2K", "4K"):
        q = DEFAULT_QUALITY

    a = raw_aspect.replace("/", ":").replace("x", ":").replace("×", ":")

    if a in RESOLUTION_MAP and q in RESOLUTION_MAP[a]:
        w, h = RESOLUTION_MAP[a][q]
    else:
        print(f"  ⚠️  未识别 {raw_aspect}/{raw_quality}，回退 {DEFAULT_ASPECT} {DEFAULT_QUALITY}")
        w, h = RESOLUTION_MAP[DEFAULT_ASPECT][DEFAULT_QUALITY]

    return w, h, int(raw_fps)


def find_tts_audio(project_dir: Path) -> Path | None:
    """查找项目目录下的 TTS MP3（取第一个 *.mp3）"""
    files = sorted(project_dir.glob("*.mp3"))
    return files[0] if files else None


def load_scene_boundaries(project_dir: Path) -> dict[str, dict]:
    """加载 scene_boundaries.json → {scene_id: {start_ms, end_ms}}"""
    path = project_dir / "scene_boundaries.json"
    if not path.exists():
        return {}
    data = load_json(path)
    return {s["id"]: s for s in data.get("scenes", [])}


def detect_audio_sample_rate(audio_path: Path) -> int:
    """用 ffprobe 探测音频采样率"""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error",
             "-show_entries", "stream=sample_rate",
             "-of", "default=noprint_wrappers=1",
             str(audio_path)],
            capture_output=True, text=True, timeout=30,
        )
        for line in result.stdout.strip().splitlines():
            if "=" in line:
                return int(line.split("=")[1])
    except Exception:
        pass
    return 24000  # 默认 TTS 采样率


def detect_audio_channels(audio_path: Path) -> int:
    """用 ffprobe 探测音频声道数"""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error",
             "-show_entries", "stream=channels",
             "-of", "default=noprint_wrappers=1",
             str(audio_path)],
            capture_output=True, text=True, timeout=30,
        )
        for line in result.stdout.strip().splitlines():
            if "=" in line:
                return int(line.split("=")[1])
    except Exception:
        pass
    return 1  # 默认单声道


# ── ffmpeg 命令构建 ──────────────────────────────────────────────────

def build_ffmpeg_command(
    project_dir: Path,
    scenes: list[dict],
    segment_durations: list[float],
    audio_segments: list,
    audio_path: Path | None,
    out_w: int,
    out_h: int,
    fps: int,
    fade_d: float,
    sample_rate: int,
    channels: int,
    output_path: Path,
):
    """构建完整的 ffmpeg 命令列表"""
    n = len(segment_durations)
    cmd = ["ffmpeg", "-y"]

    # ── 输入文件 ──
    # 音频（如果有）放在第一个输入，索引为 0
    if audio_path:
        cmd += ["-i", str(audio_path)]

    for i, s in enumerate(scenes):
        img = project_dir / f"{s['id']}.png"
        cmd += ["-loop", "1", "-t", f"{segment_durations[i]:.3f}", "-i", str(img)]

    # ── 构建 filter_complex ──
    parts = []

    # 图片基址：音频存在时从索引 1 开始，否则从 0 开始
    img_base = 1 if audio_path else 0

    # 视频 scale + pad
    scale_str = (
        f"scale={out_w}:{out_h}:force_original_aspect_ratio=decrease,"
        f"pad={out_w}:{out_h}:(ow-iw)/2:(oh-ih)/2,setsar=1"
    )
    for i in range(n):
        parts.append(f"[{img_base + i}:v]{scale_str}[v{i}]")

    # xfade 链式转场
    cum_dur = segment_durations[0]
    prev = "v0"
    for i in range(1, n):
        offset = cum_dur - fade_d
        cur = f"v{i}"
        out = f"m{i}"
        parts.append(
            f"[{prev}][{cur}]xfade=transition=fade:duration={fade_d}:"
            f"offset={offset:.3f},format=yuv420p[{out}]"
        )
        cum_dur = cum_dur + segment_durations[i] - fade_d
        prev = out

    total_video_dur = cum_dur  # 最后一个累计值就是总视频时长
    final_video = prev

    # 首尾 fade
    fade_out_start = total_video_dur - fade_d
    parts.append(
        f"[{final_video}]fade=t=in:st=0:d={fade_d},"
        f"fade=t=out:st={fade_out_start:.3f}:d={fade_d},"
        f"format=yuv420p[video]"
    )

    # ── 音频部分 ──
    has_audio = audio_path and any(seg is not None for seg in audio_segments)
    if has_audio:
        audio_labels = []
        for i, seg in enumerate(audio_segments):
            if seg is None:
                # 静音段（cover / b-roll）
                label = f"s{i}"
                parts.append(
                    f"anullsrc=r={sample_rate}:cl={'mono' if channels == 1 else 'stereo'}:"
                    f"duration={segment_durations[i]:.3f}[{label}]"
                )
                audio_labels.append(label)
            else:
                # 从 TTS 音频中截取
                label = f"a{i}"
                start_s = seg[0] / 1000.0
                end_s = seg[1] / 1000.0
                parts.append(
                    f"[0:a]atrim={start_s:.3f}:{end_s:.3f},asetpts=N/SR/TB[{label}]"
                )
                audio_labels.append(label)

        # concat 所有音频段
        concat_refs = "".join(f"[{l}]" for l in audio_labels)
        parts.append(
            f"{concat_refs}concat=n={len(audio_labels)}:v=0:a=1,"
            f"atrim=duration={total_video_dur:.3f}[audio]"
        )

    filter_complex = "; ".join(parts)
    cmd += ["-filter_complex", filter_complex]
    cmd += ["-map", "[video]"]
    if has_audio:
        cmd += ["-map", "[audio]"]

    # ── 编码参数 ──
    cmd += [
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-pix_fmt", "yuv420p", "-r", str(fps),
    ]
    if has_audio:
        cmd += [
            "-c:a", "aac", "-b:a", "64k",
            "-ar", str(sample_rate), "-ac", str(channels),
        ]
    cmd += [str(output_path)]

    return cmd, total_video_dur


# ── 主流程 ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Step 5: ffmpeg 合成最终视频（图片 + TTS 配音 + dissolve 转场）",
    )
    parser.add_argument(
        "--project-dir", "-d",
        default=".",
        help="项目目录（含 script.json、scene-XX.png），默认当前目录",
    )
    parser.add_argument(
        "--tlimit", "-n",
        type=int,
        default=0,
        help="只合成前 N 个镜头的图片；0=全部（默认 0）",
    )
    parser.add_argument(
        "--output", "-o",
        default="output.mp4",
        help="输出文件名（默认 output.mp4，保存在 --project-dir 下）",
    )
    parser.add_argument(
        "--fade-duration",
        type=float,
        default=DEFAULT_FADE,
        help=f"dissolve 转场秒数（默认 {DEFAULT_FADE}）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅打印 ffmpeg 命令，不执行",
    )
    args = parser.parse_args()

    proj = Path(args.project_dir)
    t0 = time.time()

    # ── 1. 加载 script.json ──
    script_path = proj / "script.json"
    if not script_path.exists():
        print(f"❌ 未找到 {script_path}")
        sys.exit(1)
    script = load_json(script_path)
    scenes = script.get("scenes", [])
    if not scenes:
        print(f"❌ {script_path} 中 scenes 为空")
        sys.exit(1)
    print(f"📄  script.json: {len(scenes)} 个镜头")

    # ── 2. 分辨率 ──
    out_w, out_h, fps = resolve_output_size(script)
    print(f"📐  输出: {out_w}x{out_h} @ {fps}fps ({script.get('production_notes', {}).get('aspect_ratio', '?')})")

    # ── 3. 音频 ──
    audio_path = find_tts_audio(proj)
    if audio_path:
        sample_rate = detect_audio_sample_rate(audio_path)
        channels = detect_audio_channels(audio_path)
        print(f"🎤  音频: {audio_path.name} ({sample_rate}Hz, {channels}ch)")
    else:
        sample_rate, channels = 24000, 1
        print(f"🔇  无 TTS 音频，仅输出纯视频")

    # ── 4. scene_boundaries ──
    boundaries = load_scene_boundaries(proj)
    if boundaries:
        print(f"📋  场景边界: {len(boundaries)} 个镜头有配音时间戳")
    else:
        print(f"📋  无 scene_boundaries.json，使用 script duration_seconds")

    # ── 5. 限制镜头数 ──
    limit = args.tlimit if args.tlimit and args.tlimit > 0 else len(scenes)
    use_scenes = scenes[:limit]
    print(f"🎬  合成 {len(use_scenes)}/{len(scenes)} 个镜头")

    # ── 6. 全量表格：输出所有镜头的检测结果 ──
    print(f"\n{'─' * 80}")
    print(f"  {'镜头':<12} {'类型':<14} {'标题':<22} {'时长':>7} {'图片':>6} {'配音':>6} {'状态':>10}")
    print(f"{'─' * 80}")

    full_pngs = set()
    for f in proj.glob("scene-*.png"):
        if f.suffix.lower() == ".png":
            full_pngs.add(f.stem)

    for s in use_scenes:
        sid = s["id"]
        stype = s.get("type", "")
        title = s.get("title", "")
        dur_sec = s.get("duration_seconds", 0)
        img_ok = "✅" if sid in full_pngs else "❌"
        audio_ok = "✅" if sid in boundaries else "—"

        if dur_sec == 0:
            status = "跳过(dur=0)"
        elif sid not in full_pngs:
            status = "⚠️ 缺图"
        else:
            status = "✅ 就绪"

        disp_title = title if len(title) <= 20 else title[:19] + "…"
        print(f"  {sid:<12} {stype:<14} {disp_title:<22} {dur_sec:>6.1f}s {img_ok:>6} {audio_ok:>6} {status:>10}")

    print(f"{'─' * 80}")
    # 汇总
    total_ready = sum(1 for s in use_scenes if s.get("duration_seconds", 0) > 0 and s["id"] in full_pngs)
    total_missing = sum(1 for s in use_scenes if s.get("duration_seconds", 0) > 0 and s["id"] not in full_pngs)
    total_skip = sum(1 for s in use_scenes if s.get("duration_seconds", 0) == 0)
    print(f"  就绪: {total_ready}  |  缺图: {total_missing}  |  跳过(dur=0): {total_skip}")
    print()

    # ── 7. 过滤出需要图片的镜头（duration_seconds > 0 的） ──
    active_candidates = [s for s in use_scenes if s.get("duration_seconds", 0) > 0]

    # ── 8. 校验数量：镜头数 == PNG 数 ──
    expected_ids = {s["id"] for s in active_candidates}
    png_ids = set()
    for f in proj.glob("scene-*.png"):
        if f.suffix.lower() == ".png":
            png_ids.add(f.stem)

    missing = sorted(expected_ids - png_ids)
    extra = sorted(png_ids - expected_ids)

    if missing:
        print(f"❌ 缺少 {len(missing)} 个镜头图片（应有 {len(expected_ids)} 个，实有 {len(png_ids)} 个）:")
        for sid in missing:
            print(f"   - {proj / sid}.png")
        print(f"   请先运行 gen_scenes.py 生成缺失的图片")
        sys.exit(1)

    if extra:
        print(f"⚠️  发现 {len(extra)} 个多余图片文件:")
        for sid in extra:
            print(f"   - {proj / sid}.png")

    print(f"✅  图片数量匹配: {len(expected_ids)} 镜头 = {len(png_ids)} PNG")

    # ── 9. 确定每镜时长和音频区间 ──
    segment_durations: list[float] = []
    audio_segments: list = []           # None=静音, (start_ms, end_ms)=配音段
    active_scenes: list[dict] = []

    # 详细信息（只列需要合成的镜头）
    print(f"\n{'─' * 66}")
    print(f"  {'镜头':<12} {'标题':<22} {'时长':>7} {'配音来源':>14}")
    print(f"{'─' * 66}")

    for s in active_candidates:
        sid = s["id"]
        title = s.get("title", "")

        if sid in boundaries:
            b = boundaries[sid]
            dur = (b["end_ms"] - b["start_ms"]) / 1000.0
            audio_segments.append((b["start_ms"], b["end_ms"]))
            audio_src = "scene_boundaries"
        else:
            dur = float(s.get("duration_seconds", 0))
            audio_segments.append(None)
            audio_src = "无配音(静音)"

        segment_durations.append(dur)
        active_scenes.append(s)

        disp_title = title if len(title) <= 20 else title[:19] + "…"
        print(f"  {sid:<12} {disp_title:<22} {dur:>6.1f}s      {audio_src:<14}")

    print(f"{'─' * 66}")

    n = len(active_scenes)
    if n == 0:
        print("❌ 没有需要合成的镜头（所有 duration_seconds 均为 0）")
        sys.exit(1)

    # ── 8. 构建 ffmpeg 命令 ──
    output_path = proj / args.output
    cmd, total_video_dur = build_ffmpeg_command(
        project_dir=proj,
        scenes=active_scenes,
        segment_durations=segment_durations,
        audio_segments=audio_segments,
        audio_path=audio_path,
        out_w=out_w, out_h=out_h, fps=fps,
        fade_d=args.fade_duration,
        sample_rate=sample_rate,
        channels=channels,
        output_path=output_path,
    )

    # 转场统计
    num_xfade = n - 1
    raw_total = sum(segment_durations)

    print(f"\n{'─' * 56}")
    print(f"  🎞️  合成概要")
    print(f"{'─' * 56}")
    print(f"  镜头: {n} 个, 转场: dissolve x {num_xfade}")
    print(f"  原始总长: {raw_total:.1f}s → 去重叠: {total_video_dur:.1f}s")
    if audio_path and any(s is not None for s in audio_segments):
        print(f"  音频: {audio_path.name}")
    print(f"  输出: {output_path}")
    print(f"{'─' * 56}")

    if args.dry_run:
        print(f"\n🔍 DRY RUN — 将要执行的 ffmpeg 命令:\n")
        # 美化打印命令
        print(" ".join(cmd))
        print()
        return

    # ── 9. 执行 ──
    print(f"  🎬 正在合成...\n")
    try:
        subprocess.run(cmd, check=True)
        elapsed = time.time() - t0
        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"\n{'=' * 56}")
        print(f"  ✅  视频合成完成!")
        print(f"  📁  {output_path}")
        print(f"  ⏱️  耗时: {elapsed:.1f}s | 时长: {total_video_dur:.1f}s | 大小: {size_mb:.1f}MB")
        print(f"{'=' * 56}")
    except subprocess.CalledProcessError as e:
        print(f"\n❌  ffmpeg 执行失败 (exit {e.returncode})")
        print(f"   试试 --dry-run 查看完整命令")
        sys.exit(1)
    except FileNotFoundError:
        print(f"\n❌  未找到 ffmpeg，请安装并加入 PATH")
        sys.exit(1)


if __name__ == "__main__":
    main()
