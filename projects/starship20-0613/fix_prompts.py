#!/usr/bin/env python3
"""Fix script.json: remove aspect_ratio/quality from prompts"""
import json, re

path = "projects/starship20-0613/script.json"
with open(path, encoding="utf-8") as f:
    data = json.load(f)

prompt_fields = ["video_prompt", "image_prompt"]

patterns = [
    r',?\s*aspect ratio 9:16[^,]*',
    r',?\s*9:16竖屏[^,\)]*',
    r',?\s*9:16[^,\)]*',
    r',?\s*quality 2K[^,\)]*',
    r',?\s*竖屏[^,\)]*',
    r',?\s*vertical composition[^,\)]*',
]

def clean_prompt(text):
    for p in patterns:
        text = re.sub(p, '', text)
    text = re.sub(r',\s*,', ',', text)
    text = re.sub(r',\s*$', '', text)
    return text.strip()

# cover
data["cover"]["image_prompt"] = clean_prompt(data["cover"]["image_prompt"])

# scenes
for s in data["scenes"]:
    for f in prompt_fields:
        if f in s:
            s[f] = clean_prompt(s[f])

# outro
data["outro"]["image_prompt"] = clean_prompt(data["outro"]["image_prompt"])

with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("OK prompts cleaned")
