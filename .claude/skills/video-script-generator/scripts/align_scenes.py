#!/usr/bin/env python3
"""
align_scenes.py — 将 TTS 字级时间戳与 scene 口播文本对齐，输出每镜头的起止时间

用法:
    python align_scenes.py --script script.json --timestamps timestamps.json

输出:
    scene_boundaries.json — 每镜头的 start_ms / end_ms / duration_ms
"""
import argparse
import json
import re
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def normalize(text: str) -> str:
    """归一化：去标点、去空格、统一大小写"""
    text = text.lower()
    text = re.sub(r"[\s　\'\"“”‘’\[\]【】\(\)]", "", text)
    text = re.sub(r"[，。！？、：；·～—…\-\–\—,\.!\?:;]", "", text)
    return text


def match_scenes(scenes, words):
    """
    双指针顺序匹配：每个 scene.narration 在 words 拼接文本中的位置
    返回 scene_boundaries: [{id, text, start_ms, end_ms, duration_ms}]
    """
    # 1. 把所有 words 拼成一个字符串 + 记录每字对应的时间
    full_text = ""
    char_timing = []  # [(char, start_ms, end_ms)]
    for w in words:
        ch = w.get("text", "")
        if not ch:
            continue
        start = w.get("start_ms", 0)
        end = w.get("end_ms", 0)
        # 逐字符记录时间
        for c in ch:
            char_timing.append((c, start, end))

    # 2. 归一化后的全文本用于搜索
    full_norm = normalize(full_text)

    # 3. 如果 words 拼接文本为空，尝试从 char_timing 重建
    if not full_text and char_timing:
        full_text = "".join(c for c, _, _ in char_timing)
        full_norm = normalize(full_text)

    if not full_text:
        print("❌ 错误：timestamps.json 中 words 数组为空或文本为空")
        return []

    print(f"📄 TTS 文本长度: {len(full_text)} 字符, 归一化后: {len(full_norm)} 字符")
    print(f"📄 scenes 总数: {len(scenes)}")

    # 4. 对每个 scene，在 full_norm 中顺序搜索其 narration
    results = []
    search_pos = 0  # 指针：只往前走

    for scene in scenes:
        sid = scene.get("id", "unknown")
        raw_text = scene.get("narration", "")
        if not raw_text:
            continue

        target = normalize(raw_text)
        if len(target) < 2:
            print(f"  ⚠️  {sid}: 口播过短 ({len(target)}字)，跳过")
            continue

        # 从 search_pos 开始找
        idx = full_norm.find(target, search_pos)
        if idx == -1:
            print(f"  ❌ {sid}: 未在 TTS 文本中找到匹配")
            print(f"     寻找: '{target[:50]}...'")
            print(f"     位置: {search_pos} 之后")
            continue

        # 找到起始字符在 char_timing 中的位置
        # 需要计算 idx 在原始（归一化前）文本中的字符位置
        # 简化：用归一化前的文本找
        # 因为在 full_norm 中删除了标点，idx 对应的是归一化后的位置
        # 需要找到原始文本中对应的字符范围

        # 更可靠的方案：直接用原始文本中的内容在 full_text 中找
        raw_clean = raw_text.strip()
        raw_idx = full_text.find(raw_clean)
        if raw_idx == -1:
            # 如果原始文本没找到（可能标点不同），用归一化找到的位置估算
            start_char = idx
            end_char = idx + len(target)
        else:
            start_char = raw_idx
            end_char = raw_idx + len(raw_clean)

        # 查找 start_char 和 end_char 对应的时间
        if start_char < len(char_timing):
            start_ms = char_timing[start_char][1]
        else:
            start_ms = char_timing[-1][1] if char_timing else 0

        if end_char > 0 and end_char <= len(char_timing):
            end_ms = char_timing[end_char - 1][2]
        else:
            end_ms = char_timing[-1][2] if char_timing else 0

        duration_ms = end_ms - start_ms

        results.append({
            "id": sid,
            "text": raw_text,
            "start_ms": start_ms,
            "end_ms": end_ms,
            "duration_ms": duration_ms,
        })

        print(f"  ✅ {sid}: {start_ms}ms → {end_ms}ms ({duration_ms}ms)")
        print(f"     文本: '{raw_text[:40]}...'")

        # 更新搜索位置
        search_pos = idx + len(target)

    return results


def main():
    parser = argparse.ArgumentParser(description="对齐 TTS 时间戳与场景口播")
    parser.add_argument("--script", required=True, help="script.json 路径")
    parser.add_argument("--timestamps", required=True, help="timestamps.json 路径")
    parser.add_argument("--output", default="", help="输出路径（默认与 script 同目录）")
    args = parser.parse_args()

    # 加载
    script_path = Path(args.script)
    ts_path = Path(args.timestamps)

    with open(script_path, encoding="utf-8") as f:
        script = json.load(f)
    with open(ts_path, encoding="utf-8") as f:
        ts_data = json.load(f)

    scenes = script.get("scenes", [])
    words = ts_data.get("words", [])

    print(f"🎬 {script.get('meta', {}).get('title', '未命名')}")
    print(f"📊 TTS words: {len(words)} 个字, 总时长: {ts_data.get('total_duration_ms', 0)}ms")
    print()

    # 对齐
    boundaries = match_scenes(scenes, words)

    if not boundaries:
        print("\n❌ 未能对齐任何场景")
        sys.exit(1)

    # 输出
    output_path = args.output or (script_path.parent / "scene_boundaries.json")
    output = {
        "total_duration_ms": ts_data.get("total_duration_ms", 0),
        "scenes": boundaries,
        "generated_at": "2026-06-11T10:00:00Z",
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ scene_boundaries.json saved -> {output_path}")
    total = sum(s.get("duration_ms", 0) for s in boundaries)
    print(f"📊 已对齐 {len(boundaries)}/{len(scenes)} 个场景, 总时长: {total}ms")

    # 摘要
    print("\n=== 场景边界摘要 ===")
    for s in boundaries:
        print(f"  {s['id']}: {s['start_ms']}ms → {s['end_ms']}ms ({s['duration_ms']}ms)")


if __name__ == "__main__":
    main()
