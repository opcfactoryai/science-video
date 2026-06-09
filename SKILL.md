# Science Video Skill

> 科普视频自动生成 Skill — 根据用户输入的主题，通过 DeepSeek 生成脚本、GPT-Image-2 生成图像、火山引擎 TTS 生成语音、FFmpeg 合成最终视频。
> 类 B 站科普风格：封面引入 → 钩子 → 内容讲解 → 总结 → 片尾。

---

## 1. 何时触发

用户请求涉及以下任一场景时激活本 Skill：

- 制作科普视频 / 知识类短视频
- B 站风格视频生成
- 将某个知识点做成短视频
- 输入主题，输出完整 MP4 视频
- 提及"分镜脚本"+"视频合成"

**不触发**：纯文本内容生成、非视频类多媒体处理、长视频（>10分钟）制作。

---

## 2. 执行前检查

每次执行前验证以下依赖是否就绪：

| 依赖 | 用途 | 验证命令 | 必须 |
|------|------|----------|------|
| `ffmpeg` + `ffprobe` | 视频/音频处理 | `ffmpeg -version && ffprobe -version` | 是 |
| 中文字体（NotoSansCJK-Bold） | FFmpeg drawtext | `fc-list :lang=zh 2>/dev/null` 或检查 `FONT_PATH` | 是 |
| DeepSeek API Key | 脚本生成 | 环境变量 `DEEPSEEK_API_KEY` | 是 |
| OpenAI API Key | 图像生成 | 环境变量 `OPENAI_API_KEY` | 是 |
| 火山引擎 TTS API Key | 语音合成 | 环境变量 `VOLC_ACCESS_KEY` + `VOLC_SECRET_KEY` | 是 |
| Python 3.8+ | 脚本处理辅助 | `python --version` | 否（有替代方案时） |

**检查清单**：
- [ ] 所有 API Key 已配置
- [ ] FFmpeg 可用且支持 libx264 和 concat demuxer
- [ ] 中文字体路径存在
- [ ] 输出目录可写，磁盘空间充足（每个视频约 50~200MB）

---

## 3. 执行概述

```
用户输入主题
     │
     ▼
Step 1  DeepSeek 生成完整分镜脚本 → script.json
     │
     ▼
Step 2  按 scene.type 分类生成资产（并行）
        ├── type=cover/outro  → FFmpeg drawtext 生成 JPG + anullsrc 生成 MP3
        └── type=hook/content/summary → GPT-Image-2 生成 JPG + 火山 TTS 生成 MP3
     │
     ▼
Step 3  ffprobe 提取每段 MP3 时长 → durations[]
     │
     ▼
Step 4  FFmpeg 合成
        ├── 4a  合并全部音频（含静音段）→ merged_audio.mp3
        ├── 4b  生成 concat.txt（按段落顺序 + 时长）
        ├── 4c  生成字幕 subtitle.srt（可选，跳过 cover/outro）
        └── 4d  合成最终视频 → output.mp4
```

---

## 4. 项目目录规范

每次执行生成一个独立项目目录，所有中间产物和最终视频均存放于此。

### 4.1 根路径

项目根路径通过配置项 `OUTPUT_ROOT` 设定，默认值：

| 平台 | 默认路径 | 说明 |
|------|---------|------|
| Linux/macOS | `~/Videos/science-video/` | 用户视频目录下 |
| Windows | `%USERPROFILE%\Videos\science-video\` | 同上 |

Agent 在执行第一步前先创建 `OUTPUT_ROOT`（如不存在）。

### 4.2 项目目录命名

```
{topic-en}-{YYYYMMDD}-{HHMMSS}
```

| 部分 | 规则 | 示例 |
|------|------|------|
| `topic-en` | 主题的英文短名，kebab-case，2~4 个词，不含时间日期信息 | `photosynthesis`、`how-black-holes-work` |
| `YYYYMMDD` | 执行日期（北京时间） | `20260608` |
| `HHMMSS` | 执行时间（24小时制） | `143022` |

**转换规则**：
1. 用 LLM 将用户的中文/英文主题翻译为英文短名
2. 取 2~4 个核心词，去掉冠词介词
3. 转小写，空格转连字符
4. 移除标点特殊字符

| 用户输入 | 生成的 topic-en |
|----------|----------------|
| "光合作用" | `photosynthesis` |
| "黑洞是怎么形成的" | `how-black-holes-form` |
| "How Vaccines Work" | `how-vaccines-work` |
| "中国古代四大发明" | `ancient-china-inventions` |

**完整示例**：`photosynthesis-20260608-143022/`

### 4.3 目录结构

项目目录内的所有路径均以项目根为基准，所有命令在项目根目录下执行。

```
{topic-en}-{YYYYMMDD}-{HHMMSS}/
├── script.json                 ← [Step 1] 分镜脚本（唯一数据源）
├── assets/                     ← [Step 2] 原始素材
│   ├── cover.jpg               ←   封面图像
│   ├── outro.jpg               ←   片尾图像
│   ├── scene_hook.jpg          ←   钩子分镜图像
│   ├── scene_hook.mp3          ←   钩子分镜语音
│   ├── scene_01.jpg            ←   内容 01 分镜图像
│   ├── scene_01.mp3            ←   内容 01 分镜语音
│   ├── ...                     ←   更多 content scene
│   ├── scene_summary.jpg       ←   总结分镜图像
│   ├── scene_summary.mp3       ←   总结分镜语音
│   ├── silence_cover.mp3       ←   封面静音段
│   └── silence_outro.mp3       ←   片尾静音段
└── output/                     ← [Step 4] 合成产物
    ├── merged_audio.mp3        ←   4a 合并音频
    ├── concat.txt              ←   4b 拼接描述
    ├── subtitle.srt            ←   4c 字幕文件（可选）
    └── output.mp4              ←   4d ★ 最终视频
```

### 4.4 多项目共存

- 每个项目目录独立，互不干扰
- Agent 不在已有项目目录内重新执行（每次新建）
- 旧项目由用户自行清理，Agent 不自动删除

---

## 5. Step 1 — 脚本生成

**产物**：`项目目录/script.json` — 完整分镜脚本

**调用参数**：

| 项 | 值 |
|----|-----|
| API | DeepSeek Chat API |
| 模型 | `deepseek-chat` |
| 模式 | JSON mode（`response_format={type:"json_object"}`） |
| Prompt | `prompts/script.md`（Skill 内嵌模板） |

**输出 JSON 结构**：

```json
{
  "title": "视频总标题（字符串）",
  "scenes": [
    {
      "id": "cover",
      "type": "cover",
      "title": "封面大字标题",
      "subtitle": "副标题文字",
      "narration": "",
      "image_prompt": "",
      "duration": 4
    },
    {
      "id": "hook",
      "type": "hook",
      "title": "钩子",
      "narration": "60~120 字 TTS 文案，设悬念/引好奇",
      "image_prompt": "英文 GPT-Image-2 Prompt",
      "duration": 0
    },
    {
      "id": "scene_01",
      "type": "content",
      "title": "内容段落标题",
      "narration": "60~120 字知识点讲解",
      "image_prompt": "英文 GPT-Image-2 Prompt",
      "duration": 0
    },
    {
      "id": "summary",
      "type": "summary",
      "title": "总结",
      "narration": "60~120 字回顾总结",
      "image_prompt": "英文 GPT-Image-2 Prompt",
      "duration": 0
    },
    {
      "id": "outro",
      "type": "outro",
      "title": "引导关注文字",
      "subtitle": "下期预告",
      "narration": "",
      "image_prompt": "",
      "duration": 4
    }
  ]
}
```

**字段规则**：

| 字段 | 适用 type | 说明 |
|------|-----------|------|
| `type` | 全部 | 枚举值：`cover` / `hook` / `content` / `summary` / `outro` |
| `title` | 全部 | 段落标题，cover/outro 用于 drawtext 大字渲染 |
| `subtitle` | cover/outro | 副标题文字，用于 drawtext 第二行 |
| `narration` | hook/content/summary | TTS 朗读文案，约 60~120 字；cover/outro 为空字符串 |
| `image_prompt` | hook/content/summary | GPT-Image-2 英文 Prompt；cover/outro 为空字符串 |
| `duration` | cover/outro | 固定展示秒数，默认 4；其他 type 为 0（由音频时长决定） |

**内容分镜数量**：默认 5~8 个 `content` 类型 scene，至少 3 个，最多 12 个。`id` 递增编号：`scene_01`、`scene_02`……

**后处理验证**：
- scenes 数组包含完整的 5 类段落（cover/hook/content×N/summary/outro）
- id 无重复，递增有序
- cover/outro 的 narration 和 image_prompt 为空字符串
- content 数量在 3~12 范围
- 验证失败则重新调用 DeepSeek API（最多 3 次）

---

## 6. Step 2 — 资产生成

**产物**（均在 `项目目录/assets/` 下）：

| 文件 | 来源 | 说明 |
|------|------|------|
| `cover.jpg` | FFmpeg drawtext | 封面画面 |
| `outro.jpg` | FFmpeg drawtext | 片尾画面 |
| `silence_cover.mp3` | FFmpeg anullsrc | 封面静音轨 |
| `silence_outro.mp3` | FFmpeg anullsrc | 片尾静音轨 |
| `scene_{id}.jpg` | GPT-Image-2 | hook/content/summary 图像 |
| `scene_{id}.mp3` | 火山引擎 TTS | hook/content/summary 语音 |

### 5.1 cover / outro：FFmpeg 静态画面 + 静音

```bash
# 封面图 — {{COVER_BG_COLOR}} 和 {{FONT_PATH}} 从配置项读取
ffmpeg -y \
  -f lavfi -i "color=c={{COVER_BG_COLOR}}:size=1280x720:duration=1" \
  -vf "
    drawtext=text='{{title}}':fontcolor=white:fontsize=64:x=(w-tw)/2:y=(h-th)/2-40:font={{FONT_PATH}},
    drawtext=text='{{subtitle}}':fontcolor=#aaaaaa:fontsize=32:x=(w-tw)/2:y=(h-th)/2+60:font={{FONT_PATH}}
  " \
  -frames:v 1 assets/cover.jpg
```

```bash
# 片尾图 — 同理，换文字内容和字号
ffmpeg -y \
  -f lavfi -i "color=c=#1a1a2e:size=1280x720:duration=1" \
  -vf "
    drawtext=text='{{outro_title}}':fontcolor=white:fontsize=56:x=(w-tw)/2:y=(h-th)/2-30:font={{FONT_PATH}},
    drawtext=text='{{outro_subtitle}}':fontcolor=#aaaaaa:fontsize=28:x=(w-tw)/2:y=(h-th)/2+60:font={{FONT_PATH}}
  " \
  -frames:v 1 assets/outro.jpg
```

```bash
# 静音段 — 时长为 duration 字段（默认 4s）
ffmpeg -y -f lavfi -i "anullsrc=r=24000:cl=mono" -t {{duration}} -c:a libmp3lame -q:a 4 assets/silence_cover.mp3
ffmpeg -y -f lavfi -i "anullsrc=r=24000:cl=mono" -t {{duration}} -c:a libmp3lame -q:a 4 assets/silence_outro.mp3
```

### 5.2 hook / content / summary：图像 + 语音

**图像 — GPT-Image-2**：

```
POST https://api.openai.com/v1/images/generations
Authorization: Bearer {{OPENAI_API_KEY}}

{
  "model": "gpt-image-2",
  "prompt": "{{scene.image_prompt}}",
  "size": "1280x720",
  "response_format": "b64_json",
  "n": 1
}
```

返回 base64 → 解码 → 写入 `assets/scene_{{id}}.jpg`。所有图像统一为扁平化科普插画风格。

**语音 — 火山引擎 TTS**：

```
POST https://openspeech.bytedance.com/api/v1/tts
Authorization: Bearer;access_token={{VOLC_ACCESS_KEY}}

{
  "app": {"appid": "{{VOLC_APP_ID}}"},
  "user": {"uid": "1"},
  "audio": {
    "voice_type": "zh_female_qingxin",
    "encoding": "mp3",
    "speed_ratio": 1.0,
    "volume_ratio": 1.0,
    "pitch_ratio": 1.0
  },
  "request": {
    "reqid": "{{uuid}}",
    "text": "{{scene.narration}}",
    "text_type": "plain"
  }
}
```

返回 base64 → 解码 → 写入 `assets/scene_{{id}}.mp3`。格式：MP3，采样率 24000Hz。

### 5.3 并发策略

1. 先完成 cover/outro 的 FFmpeg 静态图 + 静音（本地操作，很快）
2. 再并行处理所有 hook/content/summary 的图像 + 语音
3. 每个 scene 内部：图像和语音**同时发起**（两个独立异步任务）

| 类型 | 最大并发 | 说明 |
|------|---------|------|
| GPT-Image-2 | 3 | OpenAI API 限速 |
| 火山 TTS | 5 | 通常无严格限速 |
| 总体 | 10 | Agent 控制上限 |

---

## 7. Step 3 — 提取音频时长

对每段已生成的音频文件执行 ffprobe：

```bash
ffprobe -v quiet -print_format json -show_streams assets/scene_{{id}}.mp3
# 取 streams[0].duration，浮点秒
```

| 段落类型 | 时长来源 | 说明 |
|----------|---------|------|
| `cover` / `outro` | `script.json` 中的 `duration` 字段 | 固定值（默认 4 秒） |
| `hook` / `content` / `summary` | ffprobe 实测 | 从 MP3 文件读取 |

**同步原理**：画面展示时长 = 对应音频时长，天然音画同步。

**产物**：内存中的 `durations[]` 数组（每个 scene 对应的浮点数秒），供 Step 4 使用。

---

## 8. Step 4 — FFmpeg 合成

### 7.1 合并全部音频

按段落顺序，将所有 MP3（含静音段）合并为一个连续音频轨：

```bash
ffmpeg -y \
  -i assets/silence_cover.mp3 \
  -i assets/scene_hook.mp3 \
  -i assets/scene_01.mp3 \
  ... \
  -i assets/scene_summary.mp3 \
  -i assets/silence_outro.mp3 \
  -filter_complex "[0:a][1:a][2:a]...[N:a]concat=n={{total}}:v=0:a=1[aout]" \
  -map "[aout]" \
  output/merged_audio.mp3
```

**产物**：`项目目录/output/merged_audio.mp3`

### 7.2 生成 concat.txt

按 scenes 顺序 + Step 3 的 durations 写入 `output/concat.txt`：

```
file 'assets/cover.jpg'
duration 4.000

file 'assets/scene_hook.jpg'
duration {{hook_duration}}

file 'assets/scene_01.jpg'
duration {{scene_01_duration}}

...

file 'assets/scene_summary.jpg'
duration {{summary_duration}}

file 'assets/outro.jpg'
duration 4.000

file 'assets/outro.jpg'         ← 最后一帧重复（FFmpeg concat demuxer 要求）
```

**产物**：`项目目录/output/concat.txt`

### 7.3 合成最终视频

```bash
ffmpeg -y \
  -f concat -safe 0 -i output/concat.txt \
  -i output/merged_audio.mp3 \
  -c:v libx264 -pix_fmt yuv420p -r 30 \
  -vf "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2" \
  -c:a aac -b:a 128k \
  -shortest \
  output/output.mp4
```

**产物**：`项目目录/output/output.mp4`

> 默认使用 concat demuxer 硬切。如需 xfade 淡入淡出，见附录。

### 7.4 字幕生成（可选）

**开关**：`ENABLE_SUBTITLE=true`（默认开启）

**时间轴计算**：每段开始时间 = 前所有段时长累加，跳过 cover/outro。

```
{{index}}
{{start_time}} --> {{end_time}}
{{narration_text}}
```

**产物**：`项目目录/output/subtitle.srt`

**烧录字幕**（可选步骤，生成 `output_subtitled.mp4`）：

```bash
ffmpeg -y \
  -i output/output.mp4 \
  -vf "subtitles=output/subtitle.srt:force_style='FontSize=22,PrimaryColour=&Hffffff,Outline=1'" \
  -c:a copy \
  output/output_subtitled.mp4
```

---

## 9. 配置项

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `COVER_DURATION` | `4` | 封面展示秒数 |
| `OUTRO_DURATION` | `4` | 片尾展示秒数 |
| `COVER_BG_COLOR` | `#1a1a2e` | 封面背景色（十六进制） |
| `COVER_FONT_SIZE` | `64` | 封面主标题字号 |
| `OUTRO_FONT_SIZE` | `56` | 片尾主标题字号 |
| `VOICE_TYPE` | `zh_female_qingxin` | 火山引擎 TTS 音色 |
| `SPEED_RATIO` | `1.0` | 语速 0.5~2.0 |
| `SCENE_COUNT` | `5~8` | 内容分镜数量 |
| `ENABLE_SUBTITLE` | `true` | 是否生成字幕 |
| `FONT_PATH` | `/usr/share/fonts/NotoSansCJK-Bold.ttc` | FFmpeg drawtext 中文字体路径 |
| `VIDEO_WIDTH` / `VIDEO_HEIGHT` | `1280` / `720` | 视频分辨率 |
| `VIDEO_FPS` | `30` | 帧率 |
| `AUDIO_SAMPLE_RATE` | `24000` | 音频采样率 |
| `IMAGE_CONCURRENCY` | `3` | GPT-Image-2 并发数 |
| `TTS_CONCURRENCY` | `5` | 火山 TTS 并发数 |
| `OUTPUT_ROOT` | `~/Videos/science-video/` | 项目根目录父路径 |

---

## 10. 视频段落时序

```
时间轴 ──────────────────────────────────────────────────────────────────────►

画面轨  [cover.jpg─4s─][scene_hook.jpg──13s──][scene_01.jpg──18s──][...][scene_summary.jpg──14s──][outro.jpg─4s─]

音频轨  [静音──4s─────][TTS hook────13s──────][TTS 01─────18s─────][...][TTS summary────14s──────][静音──4s─────]

字幕轨               [钩子字幕               ][分镜1字幕           ][...][总结字幕                ]

段落类型 COVER        HOOK                    CONTENT               SUMMARY                  OUTRO
```

---

## 11. 转场处理

### 默认方案：硬切

使用 concat demuxer 直接拼接，简单可靠。先用硬切跑通全流程。

### 进阶方案：xfade 淡入淡出（0.5s）

段落间 0.5s 淡入淡出，改用 `-loop 1` 逐帧输入。

**offset 计算**：`offset_N = sum(duration_0..N-1) - N × 0.5`

```bash
ffmpeg -y \
  -loop 1 -t {{dur_cover}}      -i assets/cover.jpg \
  -loop 1 -t {{dur_hook}}       -i assets/scene_hook.jpg \
  -loop 1 -t {{dur_01}}         -i assets/scene_01.jpg \
  -loop 1 -t {{dur_summary}}    -i assets/scene_summary.jpg \
  -loop 1 -t {{dur_outro}}      -i assets/outro.jpg \
  -i output/merged_audio.mp3 \
  -filter_complex "
    [0:v][1:v]xfade=transition=fade:duration=0.5:offset={{offset_1}}[v01];
    [v01][2:v]xfade=transition=fade:duration=0.5:offset={{offset_2}}[v012];
    [v012][3:v]xfade=transition=fade:duration=0.5:offset={{offset_3}}[v0123];
    [v0123][4:v]xfade=transition=fade:duration=0.5:offset={{offset_4}}[vout]
  " \
  -map "[vout]" -map 5:a \
  -c:v libx264 -pix_fmt yuv420p -r 30 \
  -c:a aac -b:a 128k \
  -shortest \
  output/output.mp4
```

---

## 12. 错误处理

| 错误场景 | 处理方式 | 重试 |
|----------|---------|------|
| DeepSeek 返回无效 JSON | 重新生成 | 最多 3 次，立即 |
| OpenAI 图像超时/限速 | 退避重试，加入队列尾部 | 最多 3 次，指数退避 |
| 火山 TTS 返回空/错误码 | 记录日志，重试该段 | 最多 2 次 |
| FFmpeg 命令失败 | 检查参数和文件路径，输出 stderr | 不复，人工排查 |
| 磁盘空间不足 | 报错提示清理磁盘 | 不复 |
| 中文字体缺失 | fallback 提示安装字体，给出命令 | 不复 |

---

## 13. 用户交互规范

1. **开始前**：确认主题、期望时长（如"3 分钟"）、目标受众（如"初中生"）
2. **Step 1 后**：展示脚本摘要（标题、分镜数、估算总时长），让用户确认/修改
3. **Step 2 中**：报告进度（"已生成 3/7 张图片，4/7 段语音"）
4. **合成前**：告知用户即将合成（耗时较长）
5. **完成后**：提供 `output/output.mp4` 路径，询问是否调整（换语音/加字幕/改背景色）
