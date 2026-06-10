"""从 script.json 读取分镜提示词，逐镜调用 gpt-image-2 生成图片
用法: python gen_scenes.py --project-dir projects/01-00-0610
"""
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

API_KEY = os.environ.get("IMAGE_API_KEY")
if not API_KEY:
    print("❌ 环境变量 IMAGE_API_KEY 未设置。请 source .env 或 export IMAGE_API_KEY=xxx")
    sys.exit(1)
API_URL = os.environ.get("IMAGE_API_URL", "https://api.mmh1.top/v1/chat/completions")
MODEL = os.environ.get("IMAGE_MODEL", "gpt-image-2")


def main():
    parser = argparse.ArgumentParser(description="从 script.json 逐镜生成图片")
    parser.add_argument("--project-dir", default=".", help="项目目录（含 script.json），图片输出到此目录")
    parser.add_argument("--delay", type=int, default=2, help="每镜间隔秒数")
    args = parser.parse_args()

    proj = Path(args.project_dir)
    script_path = proj / "script.json"

    with open(script_path, "r", encoding="utf-8") as f:
        script_data = json.load(f)

    scenes_raw = script_data.get("scenes", [])
    scenes = []
    for s in scenes_raw:
        sid = s["id"]
        prompt = s.get("image_prompt", "")
        if not prompt:
            continue  # 跳过 cover / outro 等无提示词场景
        scenes.append((sid, prompt))

    if not scenes:
        print(f"❌ {script_path} 中未找到 scenes 或提示词为空")
        sys.exit(1)

    print(f"🎬 {script_data.get('title', '未命名')} — 共 {len(scenes)} 个场景")
    print(f"📁 {proj.resolve()}\n")

    ok = fail = 0
    for idx, (name, prompt) in enumerate(scenes):
        safe = re.sub(r"[^\w\-]", "_", name) or "scene"
        fpath = proj / f"{safe}.png"

        print(f"  [{idx + 1}/{len(scenes)}] 🖼️  {name} → {safe}.png  ", end="", flush=True)
        try:
            resp = requests.post(
                API_URL,
                headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
                json={"model": MODEL, "messages": [{"role": "user", "content": prompt}]},
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]

            urls = re.findall(r"https?://[^\s)\]\"]+", content)
            if not urls:
                raise RuntimeError(f"API 返回无图片 URL: {content[:120]}")

            img_url = urls[-1]  # 取最后一个 (download link)
            img_resp = requests.get(img_url, timeout=60)
            img_resp.raise_for_status()

            with open(fpath, "wb") as f:
                f.write(img_resp.content)

            print(f"✅ ({len(img_resp.content) / 1024:.0f} KB)")
            ok += 1
        except Exception as e:
            print(f"❌ {e}")
            fail += 1

        if idx < len(scenes) - 1:
            time.sleep(args.delay)

    print(f"\n📊 完成: {ok} 成功, {fail} 失败")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
