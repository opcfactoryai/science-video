#!/usr/bin/env python3
"""Step 3 helper: extract narration.txt + prompts_report.md"""
import json, sys

proj = "projects/starship20-0613"
with open(f"{proj}/script.json", encoding="utf-8") as f:
    data = json.load(f)

# narration.txt
parts = [s["narration"] for s in data["scenes"] if s.get("narration")]
with open(f"{proj}/narration.txt", "w", encoding="utf-8") as out:
    out.write("\n\n".join(parts))
print(f"narration.txt saved ({len(parts)} scenes)")

# prompts_report.md
lines = ["# 提示词汇总报告", "---", ""]
lines.append("## 封面图像提示词")
lines.append("```\n" + data["cover"]["image_prompt"] + "\n```")
lines.append("")
lines.append("## 各分镜提示词")
for s in data["scenes"]:
    lines.append("")
    lines.append(f'### {s["id"]}: {s["title"]} ({s["duration_seconds"]}s)')
    lines.append("**视频提示词:**")
    lines.append("```\n" + s["video_prompt"] + "\n```")
    lines.append("**图像提示词:**")
    lines.append("```\n" + s["image_prompt"] + "\n```")
lines.append("")
lines.append("## 结尾图像提示词")
lines.append("```\n" + data["outro"]["image_prompt"] + "\n```")
with open(f"{proj}/prompts_report.md", "w", encoding="utf-8") as out:
    out.write("\n".join(lines))
print("prompts_report.md saved")
