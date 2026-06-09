---
name: science-video
description: 生成科普类短视频，效果类似人讲PPT。输入主题，自动生成封面→钩子→内容分镜→总结→片尾的完整视频。图像调用GPT-Image-2生成，语音调用火山引擎TTS，视频合成使用FFmpeg。当用户提到"生成科普视频"、"做一个讲解视频"、"科普短片"、"PPT讲解视频"时，务必使用此skill。
---

# Science Video Skill

将一个主题自动生成一段完整科普短视频（MP4），包含封面、钩子、内容分镜、总结、片尾，画面与语音精确同步。

---

## 目录结构（两层分离）

```
~/.skills/science-video/          ← Skill 本身（只读）
    SKILL.md
    prompts/
        script.md                 ← DeepSeek 脚本生成 Prompt
        image.md                  ← 图像 Prompt 规范
    scripts/
        01_gen_script.ts          ← Step1: 调用 DeepSeek 生成脚本
        02_gen_assets.ts          ← Step2: 并行生成图像+语音+封面
        03_gen_concat.ts          ← Step3: ffprobe 提取时长，生成 concat.txt
        04_compose_video.ts       ← Step4: FFmpeg 合成视频+字幕

~/projects/{topic}-video-{timestamp}/   ← 每次执行新建（工作目录）
    script.json
    assets/
        cover.jpg
        outro.jpg
        scene_hook.jpg / .mp3
        scene_01.jpg / .mp3
        ...
        scene_summary.jpg / .mp3
    silence_cover.mp3
    silence_outro.mp3
    merged_audio.mp3
    concat.txt
    subtitle.srt
    output.mp4
```

---

## 执行流程总览

```
用户输入主题
     ↓
Step 1  scripts/01_gen_script.ts   → script.json
     ↓
Step 2  scripts/02_gen_assets.ts   → assets/*.jpg + assets/*.mp3 + silence_*.mp3
     ↓
Step 3  scripts/03_gen_concat.ts   → durations[] + concat.txt
     ↓
Step 4  scripts/04_compose_video.ts → merged_audio.mp3 + subtitle.srt + output.mp4
```

每个 script 独立可运行，Agent 按顺序调用，出错可单步重跑。

---

## 视频段落结构

共 5 类段落，顺序固定：

| 顺序 | type | 画面来源 | 音频来源 | 时长 |
|------|------|---------|---------|------|
| 1 | `cover` | FFmpeg drawtext 生成 JPG | anullsrc 静音 MP3 | 固定 4s |
| 2 | `hook` | GPT-Image-2 | 火山引擎 TTS | TTS 实测时长 |
| 3 | `content` ×5~8 | GPT-Image-2 | 火山引擎 TTS | TTS 实测时长 |
| 4 | `summary` | GPT-Image-2 | 火山引擎 TTS | TTS 实测时长 |
| 5 | `outro` | FFmpeg drawtext 生成 JPG | anullsrc 静音 MP3 | 固定 4s |

**同步原理**：`画面展示时长 = 对应音频时长`，ffprobe 实测后写入 concat.txt，天然对齐。

---

## Step 1 — 脚本生成

运行：`npx ts-node scripts/01_gen_script.ts --topic "光合作用" --out ./projects/xxx-video/`

读取 `prompts/script.md` 作为 system prompt，调用 DeepSeek JSON mode，输出 `script.json`。

### script.json 结构

```json
{
  "title": "视频总标题",
  "scenes": [
    {
      "id": "cover",
      "type": "cover",
      "title": "光合作用的秘密",
      "subtitle": "植物是怎么把阳光变成食物的？",
      "narration": "",
      "image_prompt": "",
      "duration": 4
    },
    {
      "id": "hook",
      "type": "hook",
      "title": "钩子",
      "narration": "你有没有想过，植物为什么是绿色的……",
      "image_prompt": "Flat illustration, a curious child looking at a glowing green leaf..."
    },
    {
      "id": "scene_01",
      "type": "content",
      "title": "什么是光合作用",
      "narration": "光合作用是植物利用阳光……",
      "image_prompt": "Flat illustration, diagram of photosynthesis process..."
    },
    {
      "id": "summary",
      "type": "summary",
      "title": "总结",
      "narration": "今天我们学到了……",
      "image_prompt": "Flat illustration, recap mind map of key points..."
    },
    {
      "id": "outro",
      "type": "outro",
      "title": "觉得有用就点个关注吧 👇",
      "subtitle": "下期预告：呼吸作用是什么？",
      "narration": "",
      "image_prompt": "",
      "duration": 4
    }
  ]
}
```

字段说明见 `prompts/script.md`。

---

## Step 2 — 资产生成

运行：`npx ts-node scripts/02_gen_assets.ts --project ./projects/xxx-video/`

读取 `script.json`，按 `type` 分两类处理：

### cover / outro → FFmpeg drawtext + anullsrc

详细命令参数见 `prompts/image.md` § FFmpeg drawtext 规范。

脚本内调用 FFmpeg 命令行生成静态 JPG 和静音 MP3：

```
cover.jpg     ← ffmpeg drawtext（深色背景 + 大标题 + 副标题）
outro.jpg     ← ffmpeg drawtext（同上，换文字）
silence_cover.mp3  ← ffmpeg anullsrc，时长 = scene.duration
silence_outro.mp3  ← ffmpeg anullsrc，时长 = scene.duration
```

### hook / content / summary → API 并行调用

- **图像**：调用 GPT-Image-2，`response_format: b64_json`，解码写入 `assets/scene_{id}.jpg`
- **语音**：调用火山引擎 TTS，返回 base64 MP3，解码写入 `assets/scene_{id}.mp3`
- **并发**：图像限 3 并发，TTS 限 5 并发，图像与语音并行发起

API 参数详见配置节。

---

## Step 3 — 时长提取与 concat.txt 生成

运行：`npx ts-node scripts/03_gen_concat.ts --project ./projects/xxx-video/`

### ffprobe 提取时长

```bash
ffprobe -v quiet -print_format json -show_streams <file.mp3>
# 取 streams[0].duration（浮点秒）
```

对所有音频文件（含 silence_*.mp3）统一执行，结果存为内存对象 `durations`。

### concat.txt 格式

按 `script.json` scenes 顺序写入，最后一帧重复（FFmpeg 要求）：

```
file 'assets/cover.jpg'
duration 4.000000

file 'assets/scene_hook.jpg'
duration 13.254000

file 'assets/scene_01.jpg'
duration 18.731000

file 'assets/scene_summary.jpg'
duration 14.502000

file 'assets/outro.jpg'
duration 4.000000

file 'assets/outro.jpg'
```

---

## Step 4 — FFmpeg 视频合成

运行：`npx ts-node scripts/04_compose_video.ts --project ./projects/xxx-video/`

### 4a 合并全部音频

按 scenes 顺序，`n` 为段落总数：

```bash
ffmpeg -y \
  -i silence_cover.mp3 \
  -i assets/scene_hook.mp3 \
  -i assets/scene_01.mp3 \
  -i assets/scene_summary.mp3 \
  -i silence_outro.mp3 \
  -filter_complex "[0:a][1:a][2:a][3:a][4:a]concat=n=5:v=0:a=1[aout]" \
  -map "[aout]" \
  merged_audio.mp3
```

### 4b 生成字幕 subtitle.srt

时间轴：各段开始时间 = 前所有段时长累加。`cover` / `outro` 段跳过不写字幕行。

```
1
00:00:04,000 --> 00:00:17,254
你有没有想过，植物为什么是绿色的……

2
00:00:17,254 --> 00:00:35,985
光合作用是植物利用阳光……
```

### 4c 合成最终视频

```bash
ffmpeg -y \
  -f concat -safe 0 -i concat.txt \
  -i merged_audio.mp3 \
  -c:v libx264 -pix_fmt yuv420p -r 30 \
  -vf "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2" \
  -c:a aac -b:a 128k \
  -shortest \
  output.mp4
```

### 4d 烧录字幕（可选，由配置控制）

```bash
ffmpeg -y \
  -i output.mp4 \
  -vf "subtitles=subtitle.srt:force_style='FontSize=22,PrimaryColour=&Hffffff,Outline=1'" \
  -c:a copy \
  output_subtitled.mp4
```

---

## 配置项

Agent 在工作目录根写入 `config.json`，脚本读取：

```json
{
  "deepseek": {
    "apiKey": "",
    "baseUrl": "https://api.deepseek.com",
    "model": "deepseek-chat"
  },
  "openai": {
    "apiKey": "",
    "imageModel": "gpt-image-2",
    "imageSize": "1280x720",
    "imageQuality": "standard"
  },
  "volc": {
    "appId": "",
    "accessToken": "",
    "cluster": "volcano_tts",
    "voiceType": "zh_female_qingxin",
    "speedRatio": 1.0
  },
  "video": {
    "fps": 30,
    "audioBitrate": "128k",
    "videoBitrate": "2000k",
    "coverDuration": 4,
    "outroDuration": 4,
    "coverBgColor": "#1a1a2e",
    "fontPath": "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    "enableSubtitle": true,
    "burnSubtitle": false
  }
}
```

---

## 完整时序图

```
时间轴 ──────────────────────────────────────────────────────────────────────►

画面轨  [cover─4s][scene_hook──13s──][scene_01──18s──]···[scene_summary──14s──][outro─4s]

音频轨  [静音─4s ][TTS hook────13s──][TTS 01────18s──]···[TTS summary────14s──][静音─4s ]

字幕轨           [钩子字幕           ][分镜1字幕       ]···[总结字幕             ]

类型     COVER    HOOK               CONTENT              SUMMARY              OUTRO
```

---

## 参考文件

- `prompts/script.md` — DeepSeek 脚本生成完整 Prompt，含字段约束与示例
- `prompts/image.md` — GPT-Image-2 Prompt 规范 + FFmpeg drawtext 参数规范
- `scripts/01_gen_script.ts` — Step1 实现
- `scripts/02_gen_assets.ts` — Step2 实现
- `scripts/03_gen_concat.ts` — Step3 实现
- `scripts/04_compose_video.ts` — Step4 实现
