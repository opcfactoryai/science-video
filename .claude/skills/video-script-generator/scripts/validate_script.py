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


def validate_narration_coverage(scenes, full_narration):
    """检查 full_narration 的基本完整性"""
    if not full_narration:
        return ["full_narration 为空"]
    if len(full_narration) < 100:
        return [f"full_narration 过短 ({len(full_narration)}字，建议>=100)"]
    # 以场景数为参考，确保口播稿长度合理
    expected_min = len(scenes) * 30  # 每镜至少30字
    if len(full_narration) < expected_min:
        return [f"full_narration 长度 ({len(full_narration)}字) 低于预期 ({expected_min}字)"]
    return []


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

    required_root = ["meta", "cover", "hook", "full_narration", "scenes", "outro", "production_notes"]
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

    if "full_narration" in script and len(script["full_narration"]) < 100:
        errors.append(f"❌ full_narration 过短（{len(script.get('full_narration', ''))}字，建议≥100）")

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

    # 4. 口播覆盖率
    if "scenes" in script and "full_narration" in script:
        all_errors.extend(
            validate_narration_coverage(script["scenes"], script["full_narration"])
        )

    # 5. 提示词质量
    if "scenes" in script:
        all_errors.extend(validate_prompt_quality(script["scenes"]))

    # 6. 基本信息
    meta = script.get("meta", {})
    scenes_count = len(script.get("scenes", []))
    print(f"📹 标题: {meta.get('title', 'N/A')}")
    print(f"🎬 分镜数: {scenes_count}")
    print(f"📝 口播字数: {len(script.get('full_narration', ''))}")

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
