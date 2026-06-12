#!/usr/bin/env python3
"""
validate_script.py — 校验 script.json 是否符合 storyboard-schema.json

用法:
    python validate_script.py --script path/to/script.json
    python validate_script.py --schema schema.json --script script.json

返回值:
    0 = 校验通过
    1 = 校验失败（输出错误详情）
"""
import argparse
import json
import sys
import os
import io
from pathlib import Path

# Windows console UTF-8 support
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_scene_ids(scenes):
    """检查 scene ID 是否唯一递增"""
    ids = [s.get("id", "") for s in scenes]
    errors = []

    # 检查唯一性
    if len(ids) != len(set(ids)):
        duplicates = [id for id in ids if ids.count(id) > 1]
        errors.append(f"❌ scene ID 重复: {set(duplicates)}")

    # 检查递增格式
    for i, sid in enumerate(ids):
        expected = f"scene-{i + 1:02d}"
        if sid != expected and sid != f"scene-{i + 1}":
            errors.append(f"⚠️  scene ID '{sid}' 不符合递增格式（预期 '{expected}'）")

    return errors


def validate_timing(scenes):
    """检查总时长是否合理"""
    total = sum(s.get("duration_seconds", 0) for s in scenes)
    return total, None


def validate_narration_consistency(script):
    """
    验证口播一致性：
    1. scenes[] 中至少有一个有口播的镜头
    2. hook.text 与第一个有口播的 scene.narration 一致
    3. outro.text 与最后一个有口播的 scene.narration 一致
    """
    scenes = script.get("scenes", [])
    hook = script.get("hook", {})
    outro = script.get("outro", {})
    errors = []

    # 收集有口播的镜头
    voiced = [s for s in scenes if s.get("narration", "").strip()]
    if not voiced:
        errors.append("❌ 没有找到有口播的镜头（所有 scene.narration 为空）")
        return errors

    # hook 一致性检查：首镜 narration 必须以 hook.text 开头
    hook_text = hook.get("text", "").strip()
    if hook_text:
        first_narration = voiced[0].get("narration", "").strip()
        import re
        def clean(t): return re.sub(r'[\s，。！？、：；…—]', '', t)
        if not clean(first_narration).startswith(clean(hook_text)):
            errors.append(
                f"⚠️  首镜 narration 不以 hook.text 开头\n"
                f"    hook.text:     '{hook_text[:40]}'\n"
                f"    首镜 narration: '{first_narration[:60]}'"
            )
    else:
        errors.append("⚠️  hook.text 为空")

    # outro 一致性检查：末镜 narration 必须以 outro.text 结尾
    outro_text = outro.get("text", "").strip()
    if outro_text:
        last_narration = voiced[-1].get("narration", "").strip()
        import re
        def clean(t): return re.sub(r'[\s，。！？、：；…—]', '', t)
        if not clean(last_narration).endswith(clean(outro_text)):
            errors.append(
                f"⚠️  末镜 narration 不以 outro.text 结尾\n"
                f"    outro.text:    '{outro_text[:40]}'\n"
                f"    末镜 narration: '{last_narration[:60]}'"
            )

    # 口播总长度
    total_len = sum(len(s.get("narration", "")) for s in voiced)
    if total_len < 100:
        errors.append(f"⚠️  口播总长度过短 ({total_len}字，建议≥100)")

    return errors


def validate_aspect_quality(script):
    """检查所有 prompt 是否锁死 aspect_ratio 和 quality"""
    errors = []

    # 检查根层级字段（Python 脚本直接读取）
    root_ar = script.get("aspect_ratio", "")
    root_ql = script.get("quality", "")
    if not root_ar:
        errors.append("❌ 根层级缺少 aspect_ratio（必须为 16:9 或 9:16，Python脚本直接读取）")
    elif root_ar not in ("16:9", "9:16"):
        errors.append(f"❌ 根层级 aspect_ratio 值无效: '{root_ar}'（必须为 16:9 或 9:16）")
    if not root_ql:
        errors.append("❌ 根层级缺少 quality（必须为 1K / 2K / 4K，Python脚本直接读取）")
    elif root_ql not in ("1K", "2K", "4K"):
        errors.append(f"❌ 根层级 quality 值无效: '{root_ql}'（必须为 1K / 2K / 4K）")

    # 检查 production_notes（与根层级一致）
    pn = script.get("production_notes", {})
    ar = pn.get("aspect_ratio", "") or root_ar
    ql = pn.get("quality", "") or root_ql
    if not ar:
        errors.append("❌ production_notes 缺少 aspect_ratio（必须为 16:9 或 9:16）")
    elif ar not in ("16:9", "9:16"):
        errors.append(f"❌ production_notes.aspect_ratio 值无效: '{ar}'（必须为 16:9 或 9:16）")
    if not ql:
        errors.append("❌ production_notes 缺少 quality（必须为 1K / 2K / 4K）")
    elif ql not in ("1K", "2K", "4K"):
        errors.append(f"❌ production_notes.quality 值无效: '{ql}'（必须为 1K / 2K / 4K）")

    # 构建期望的末尾片段（全部小写，与被检查文本 vid_lower/img_lower 匹配）
    expected_ar = f"aspect ratio {ar}".lower()
    expected_ql = f"quality {ql}".lower()

    scenes = script.get("scenes", [])
    for s in scenes:
        sid = s.get("id", "?")
        vid = s.get("video_prompt", "")
        img = s.get("image_prompt", "")

        vid_lower = vid.lower()
        img_lower = img.lower()

        # video_prompt 检查
        if vid:
            if expected_ar not in vid_lower:
                errors.append(f"❌ scene {sid} video_prompt 末尾缺少 '{expected_ar}' → 提示词未锁死 aspect_ratio")
            if expected_ql not in vid_lower:
                errors.append(f"❌ scene {sid} video_prompt 末尾缺少 '{expected_ql}' → 提示词未锁死 quality")

        # image_prompt 检查
        if img:
            if expected_ar not in img_lower:
                errors.append(f"❌ scene {sid} image_prompt 末尾缺少 '{expected_ar}' → 提示词未锁死 aspect_ratio")
            if expected_ql not in img_lower:
                errors.append(f"❌ scene {sid} image_prompt 末尾缺少 '{expected_ql}' → 提示词未锁死 quality")

    # 检查 cover image_prompt
    cover = script.get("cover", {})
    cover_img = cover.get("image_prompt", "")
    if cover_img:
        if expected_ar not in cover_img.lower():
            errors.append(f"❌ cover image_prompt 末尾缺少 '{expected_ar}' → 提示词未锁死 aspect_ratio")
        if expected_ql not in cover_img.lower():
            errors.append(f"❌ cover image_prompt 末尾缺少 '{expected_ql}' → 提示词未锁死 quality")

    # 检查 outro image_prompt
    outro = script.get("outro", {})
    outro_img = outro.get("image_prompt", "")
    if outro_img:
        if expected_ar not in outro_img.lower():
            errors.append(f"❌ outro image_prompt 末尾缺少 '{expected_ar}' → 提示词未锁死 aspect_ratio")
        if expected_ql not in outro_img.lower():
            errors.append(f"❌ outro image_prompt 末尾缺少 '{expected_ql}' → 提示词未锁死 quality")

    return errors


def validate_prompt_quality(scenes):
    """检查提示词质量（基本启发式）"""
    errors = []
    for s in scenes:
        vid = s.get("video_prompt", "")
        img = s.get("image_prompt", "")

        # 视频提示词必须有运镜或景别关键词
        video_keywords = [
            "shot", "close-up", "wide", "medium", "aerial", "dolly",
            "pan", "zoom", "tracking", "camera", "angle", "POV",
            "static", "crane", "tilt", "handheld", "orbit",
        ]
        if vid and not any(kw in vid.lower() for kw in video_keywords):
            errors.append(f"⚠️  scene {s.get('id')} video_prompt 缺少运镜/景别描述")

        # 图像提示词必须构图关键词
        image_keywords = [
            "composition", "centered", "rule of thirds", "lighting",
            "style", "render", "photorealistic", "cinematic", "background",
            "foreground", "depth", "perspective",
        ]
        if img and not any(kw in img.lower() for kw in image_keywords):
            errors.append(f"⚠️  scene {s.get('id')} image_prompt 缺少构图/风格描述")

        # 提示词长度检查
        if vid and len(vid) < 50:
            errors.append(f"⚠️  scene {s.get('id')} video_prompt 过短 ({len(vid)}字，建议≥50)")

        if img and len(img) < 50:
            errors.append(f"⚠️  scene {s.get('id')} image_prompt 过短 ({len(img)}字，建议≥50)")

    return errors


def validate_schema(script, schema_path=None):
    """
    使用 JSON Schema 校验。
    内置简单校验，避免引入 jsonschema 依赖。
    如安装了 jsonschema 库则使用之。
    """
    try:
        import jsonschema
        schema = load_json(schema_path) if schema_path else None
        if schema:
            jsonschema.validate(script, schema)
            return []
        return []
    except ImportError:
        # 无 jsonschema 库时做基本类型校验
        return basic_schema_check(script)
    except jsonschema.exceptions.ValidationError as e:
        return [f"❌ Schema 校验失败: {e.message} (path: {list(e.absolute_path)})"]
    except Exception as e:
        return [f"❌ Schema 校验异常: {e}"]


def basic_schema_check(script):
    """简易 Schema 检查（无 jsonschema 依赖时的回退）"""
    errors = []

    required_root = ["meta", "cover", "hook", "scenes", "outro", "production_notes"]
    for field in required_root:
        if field not in script:
            errors.append(f"❌ 缺少顶级字段: {field}")

    if "scenes" in script and not isinstance(script["scenes"], list):
        errors.append("❌ scenes 必须是数组")
    elif "scenes" in script and len(script["scenes"]) < 5:
        errors.append(f"❌ scenes 至少需要5个镜头（当前{len(script['scenes'])}个）")

    if "cover" in script:
        cover_required = ["title", "image_prompt"]
        for field in cover_required:
            if field not in script["cover"]:
                errors.append(f"❌ cover 缺少字段: {field}")

    if "hook" in script:
        hook_required = ["text", "type"]
        for field in hook_required:
            if field not in script["hook"]:
                errors.append(f"❌ hook 缺少字段: {field}")

    if "outro" in script:
        outro_required = ["text", "cta_type", "cta_text", "image_prompt"]
        for field in outro_required:
            if field not in script["outro"]:
                errors.append(f"❌ outro 缺少字段: {field}")

    return errors


def main():
    parser = argparse.ArgumentParser(description="校验视频分镜头脚本 JSON")
    parser.add_argument("--script", required=True, help="script.json 路径")
    parser.add_argument("--schema", default="", help="storyboard-schema.json 路径（可选）")
    args = parser.parse_args()

    script_path = Path(args.script)
    if not script_path.exists():
        print(f"❌ 文件不存在: {script_path}")
        sys.exit(1)

    try:
        script = load_json(script_path)
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析失败: {e}")
        sys.exit(1)

    all_errors = []

    # 1. Schema 校验
    schema_path = args.schema or (
        Path(__file__).parent.parent / "templates" / "storyboard-schema.json"
    )
    if Path(schema_path).exists():
        all_errors.extend(validate_schema(script, schema_path))

    # 2. scene ID 校验
    if "scenes" in script:
        all_errors.extend(validate_scene_ids(script["scenes"]))

    # 3. 时长校验
    if "scenes" in script:
        total, _ = validate_timing(script["scenes"])
        target = script.get("meta", {}).get("target_duration_seconds", 0)
        if target and abs(total - target) > target * 0.3:
            all_errors.append(
                f"⚠️  总时长 {total}s 与目标 {target}s 偏差较大 (>30%)"
            )
        print(f"📊 总时长: {total}s (目标: {target}s)")

    # 4. aspect_ratio + quality 锁死校验
    all_errors.extend(validate_aspect_quality(script))

    # 5. 口播一致性校验（hook/outro vs scenes）
    if "scenes" in script:
        all_errors.extend(validate_narration_consistency(script))

    # 6. 提示词质量
    if "scenes" in script:
        all_errors.extend(validate_prompt_quality(script["scenes"]))

    # 6. 基本信息
    meta = script.get("meta", {})
    scenes_count = len(script.get("scenes", []))
    print(f"📹 标题: {meta.get('title', 'N/A')}")
    print(f"🎬 分镜数: {scenes_count}")
    narration_words = sum(len(s.get("narration", "")) for s in script.get("scenes", []) if s.get("narration"))
    print(f"📝 口播字数: {narration_words}")

    # 输出结果
    if all_errors:
        print(f"\n❌ 发现 {len(all_errors)} 个问题:")
        for err in all_errors:
            print(f"  {err}")
        print("\n⚠️  请修正后重新生成。")
        return 1
    else:
        print("\n✅ 校验通过！脚本工业级可用。")
        return 0


if __name__ == "__main__":
    sys.exit(main())
