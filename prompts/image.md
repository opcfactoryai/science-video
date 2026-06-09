# 图像生成规范

## GPT-Image-2 Prompt 规范

### 固定风格前缀
所有 image_prompt 必须以以下前缀开头：
```
Flat illustration style, clean background,
```

### 内容描述规则
- 聚焦单一画面，避免复杂场景
- 禁止出现文字、数字、标注
- 人物使用卡通风格，无具体面孔
- 色彩明亮，适合科普受众（全年龄）

### 示例
```
Flat illustration style, clean background, a glowing green leaf absorbing sunlight with small arrow icons showing energy flow, yellow sun in corner, soft blue sky

Flat illustration style, clean background, a simple diagram of a plant cell with chloroplast highlighted in bright green, other organelles shown in muted colors, minimal labels

Flat illustration style, clean background, a cheerful cartoon scientist holding a magnifying glass, surrounded by floating molecular structures, warm color palette
```

### API 参数
```
model:           gpt-image-2
size:            1280x720
quality:         standard
response_format: b64_json
n:               1
```

---

## FFmpeg drawtext 规范（cover / outro 专用）

### 字体要求
优先使用系统中文字体，按以下顺序尝试：
```
/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc    # Linux
/System/Library/Fonts/PingFang.ttc                      # macOS
C:/Windows/Fonts/msyhbd.ttc                             # Windows
```

### cover 生成命令模板
```bash
ffmpeg -y \
  -f lavfi -i "color=c=#1a1a2e:size=1280x720:duration=1" \
  -vf "
    drawtext=text='{TITLE}':fontfile={FONT}:fontcolor=white:fontsize=64:x=(w-tw)/2:y=(h-th)/2-50:shadowcolor=black:shadowx=2:shadowy=2,
    drawtext=text='{SUBTITLE}':fontfile={FONT}:fontcolor=#aaaaaa:fontsize=32:x=(w-tw)/2:y=(h-th)/2+50
  " \
  -frames:v 1 \
  assets/cover.jpg
```

### outro 生成命令模板
```bash
ffmpeg -y \
  -f lavfi -i "color=c=#1a1a2e:size=1280x720:duration=1" \
  -vf "
    drawtext=text='{TITLE}':fontfile={FONT}:fontcolor=white:fontsize=52:x=(w-tw)/2:y=(h-th)/2-50:shadowcolor=black:shadowx=2:shadowy=2,
    drawtext=text='{SUBTITLE}':fontfile={FONT}:fontcolor=#aaaaaa:fontsize=28:x=(w-tw)/2:y=(h-th)/2+50
  " \
  -frames:v 1 \
  assets/outro.jpg
```

### 静音 MP3 生成命令模板
```bash
ffmpeg -y \
  -f lavfi -i "anullsrc=r=24000:cl=mono" \
  -t {DURATION} \
  -c:a libmp3lame -q:a 4 \
  silence_{ID}.mp3
```

### 注意事项
- title/subtitle 中的特殊字符（单引号、冒号）需转义：`'` → `\'`
- 字体路径不存在时 Agent 需自动探测系统可用中文字体
- `frames:v 1` 确保只输出单帧 JPG，不产生视频文件
