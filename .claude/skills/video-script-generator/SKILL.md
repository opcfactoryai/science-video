---
name: video-script-generator
description: 工业级视频脚本生成系统。输入选题主题 → 输出全量口播稿 + 分镜头脚本（每镜头2个AI提示词：视频+图像），含封面设计、钩子、转场、BGM建议。脚本经 JSON Schema 校验，100% 工程可用。
---

# 🎬 Video Script Generator — 工业级视频脚本生成系统

> ⚠️ **⚠️ 铁律：必须严格执行 Step 0 → 1 → 2 → 3 → 4 → 5 流程 ⚠️**
>
> | Step | 内容 | 强制要求 |
> |------|------|----------|
> | **0** | 创建项目目录 | 必须先建目录，否则文件无处可存 |
> | **1** | 搜索研究 | **不准跳过！** 没有 research.md 不准进入 Step 2 |
> | **2** | 生成分镜头脚本 | 必须注入全部 3 个系统提示词 + JSON 模板 |
> | **3** | 校验与保存 | 必须通过 JSON Schema 校验，失败就修正重试直到通过 |
> | **4** | 生产执行 | 全自动全量执行：TTS → 时间对齐 → AI 生图（所有镜头），一气呵成 |
> | **5** | 视频合成 | ffmpeg 合成最终视频（所有镜头），缺少 scene-XX.png 报错不合成 |
>
> 🔴 **不要偷懒。不要跳级。不要跳过 Step 1 直接生成。不要跳过 Step 3 校验。**

## 系统架构

```
用户输入选题主题
    │
    ├── Step 0: 创建项目目录 projects/{project-name}-{MMDD}/
    │
    ├── Step 1: 搜索研究 (web_search)
    │   └── 输出: research.md (核心事实、数据、受众痛点、竞品角度、独特视角)
    │
    ├── Step 2: 注入系统提示词 → 生成分镜头脚本
    │   ├── prompts/01-system-prompt.md            ← 角色/方法论/质量标准
    │   ├── prompts/02-video-prompt-engineering.md  ← 视频提示词工程规范
    │   └── prompts/03-image-prompt-engineering.md  ← 图像提示词工程规范
    │
    ├── Step 3: 校验与保存
    │   ├── 通过 storyboard-schema.json 校验
    │   ├── 提取 narration.txt（纯口播稿 → TTS 直接消费）
    │   └── 生成 prompts_report.md（提示词汇总 → 人工审阅）
    │
    ├── Step 4: 生产执行（全自动流水线）
    │   ├── gen_tts.py      → 逐段 TTS 音频
    │   ├── align_scenes.py → 场景时间对齐
    │   └── gen_scenes.py   → 逐镜 AI 图片（gpt-image-2）
    │
    └── Step 5: ffmpeg 合成最终视频
        └── compose_video.py → 逐镜 image + TTS 配音 + dissolve 转场 → MP4
```

---

## 触发条件

当用户输入以下任一类需求时自动触发：

| 类别 | 示例 |
|------|------|
| **视频脚本** | "帮我写个视频脚本"、"做个视频"、"视频分镜头" |
| **科普解说** | "科普一下XXX"、"用视频讲清楚XXX"、"5分钟讲清楚XXX" |
| **知识分享** | "做个知识类视频"、"短视频脚本"、"口播稿" |
| **产品评测** | "评测一下XXX"、"产品介绍视频" |
| **新闻快讯** | "做个新闻快讯视频"、"解读一下XXX" |

---

## Step 0 — 创建项目目录

```bash
# 从用户输入中提取项目名（拼音/英文/缩写），无法提取则用 topic
PROJECT_NAME="$(echo '${用户输入}' | sed 's/[^a-zA-Z0-9]/ /g' | awk '{print tolower($1)}')-$(date +%m%d)"
mkdir -p "projects/${PROJECT_NAME}"
```

项目目录路径记录为 `project_dir`，后续所有文件写入此目录。

---

## Step 1 — 搜索研究

用 `web_search` 搜索主题最新资讯。**必须覆盖以下 5 个维度：**

| 维度 | 要求 |
|------|------|
| 🔍 **核心事实** | 3-5 个必须传达的关键知识点，每个附带权威来源 |
| 📊 **数据支撑** | 精确数值、统计数据（年份、来源需标注） |
| 👥 **受众痛点** | 目标观众可能的认知误区、好奇点、反常识点 |
| 🏆 **竞品角度** | 已有视频的角度分析，明确本视频的差异化方向 |
| 💡 **独特视角** | 本视频的「一句话差异化定位」 |

将搜索结果整理保存为 `{project_dir}/research.md`，作为 Step 2 的上下文输入。

---

## Step 2 — 生成分镜头脚本

### 2.1 加载系统提示词

依次将以下三个文件注入为 System Message：

```yaml
1. prompts/01-system-prompt.md
   → 设定角色：资深视频编剧 + 提示词工程师
   → 定义脚本写作方法论
   → 定义镜头设计规范和提示词工程标准

2. prompts/02-video-prompt-engineering.md
   → 视频提示词语法规范（10 大要素）
   → 高质量 vs 低质量示例对比

3. prompts/03-image-prompt-engineering.md
   → 图像提示词语法规范（8 大要素）
   → 高质量 vs 低质量示例对比
```

### 2.2 加载输出模板

将 **`templates/storyboard-template.json`** 注入为输出格式约束。
严格要求 AI 遵循该 JSON 结构输出，字段顺序、类型、嵌套深度必须完全匹配。

### 2.3 执行生成

User Message 格式：

```
# 视频主题
{用户输入的选题}

# 研究资料
{research.md 的全部内容}

# 输出要求
请严格按照 storyboard-template.json 的结构输出完整的 JSON 文件。
字段说明和示例值见模板中的注释。
输出为纯 JSON，不要用 markdown 代码块包裹，不要添加前缀说明。
```

---

## Step 3 — 校验与保存

### 3.1 Schema 校验

```bash
python .claude/skills/video-script-generator/scripts/validate_script.py \
  --schema .claude/skills/video-script-generator/templates/storyboard-schema.json \
  --script "projects/${PROJECT_NAME}/script.json"
```

如校验失败则根据错误信息修正后重新生成，直到通过。

### 3.2 提取全量口播稿（由 scenes[] 拼接）

```bash
python -c "
import json
with open('projects/${PROJECT_NAME}/script.json', encoding='utf-8') as f:
    data = json.load(f)
# 按顺序拼接所有有口播的镜头 narration，用换行分隔
parts = [s['narration'] for s in data['scenes'] if s.get('narration')]
text = '\n\n'.join(parts)
with open('projects/${PROJECT_NAME}/narration.txt', 'w', encoding='utf-8') as out:
    out.write(text)
print(f'OK narration.txt saved ({len(parts)} scenes with narration)')
"
```

### 3.3 生成提示词汇总报告（人工审阅用）

```bash
python -c "
import json
with open('projects/${PROJECT_NAME}/script.json', encoding='utf-8') as f:
    data = json.load(f)
lines = ['# 🎬 提示词汇总报告', '---', '']
lines.append(f'## 📺 封面图像提示词')
lines.append(f'```\n{data[\"cover\"][\"image_prompt\"]}\n```')
lines.append('')
lines.append('## 🎥 各分镜提示词')
lines.append('')
for s in data['scenes']:
    lines.append(f'### {s[\"id\"]}: {s[\"title\"]} ({s[\"duration_seconds\"]}s)')
    lines.append(f'**🎬 视频提示词:**')
    lines.append(f'```\n{s[\"video_prompt\"]}\n```')
    lines.append(f'**🖼️ 图像提示词:**')
    lines.append(f'```\n{s[\"image_prompt\"]}\n```')
    lines.append('')
lines.append(f'## 📺 结尾图像提示词')
lines.append(f'```\n{data[\"outro\"][\"image_prompt\"]}\n```')
with open('projects/${PROJECT_NAME}/prompts_report.md', 'w', encoding='utf-8') as out:
    out.write('\n'.join(lines))
print('✅ prompts_report.md saved')
"
```

---

## Step 4 — 生产执行（自动流程）

script.json 校验通过后，直接执行以下生产流水线：

### 🎤 TTS 语音合成

```bash
source .env
PROJECT_DIR=projects/${PROJECT_NAME}
PYTHONPATH="$PWD/.claude/skills/video-script-generator/scripts" \
python .claude/skills/video-script-generator/scripts/gen_tts.py \
  --appid "${VOLC_APPID}" \
  --access_token "${VOLC_ACCESS_TOKEN}" \
  --resource_id "seed-tts-2.0" \
  --voice_type "zh_male_yizhipiannan_uranus_bigtts" \
  --text "$(cat $PROJECT_DIR/narration.txt)" \
  --encoding mp3 \
  --output-dir "$PROJECT_DIR"
```

### ⏱️ 场景时间对齐

```bash
PYTHONPATH="$PWD/.claude/skills/video-script-generator/scripts" \
python .claude/skills/video-script-generator/scripts/align_scenes.py \
  --script "$PROJECT_DIR/script.json" \
  --timestamps "$PROJECT_DIR/timestamps.json"
```

产出：`timestamps.json` + `scene_boundaries.json`（每镜 start_ms / end_ms / duration_ms）

### 🖼️ 逐镜 AI 生图（gpt-image-2，SSE 流式）

```bash
source .env && python .claude/skills/video-script-generator/scripts/gen_scenes.py \
  --project-dir "$PROJECT_DIR"
```

| 参数 | 说明 |
|------|------|
| `--project-dir` / `-d` | 项目目录，默认当前目录 |
| `--limit` / `-n` | 只生成前 N 个镜头，**默认 0=全部镜头**；仅用于临时测试 |
| `--delay` | 每镜间隔秒数，默认 2 |
| `--skip-existing` | 跳过已存在的 PNG 文件 |

**⚠️ 生产规则：默认全量执行全部镜头，不加 `--limit`。**

### 执行策略
- **全自动全量执行（默认）**：Step 3 校验通过后，TTS → 时间对齐 → AI 生图 → 视频合成 一气呵成，**所有镜头全量执行，不加 `--limit`/`--tlimit`**
- **禁止局部默认**：任何步骤都不默认加 `--limit`/`--tlimit`。这些参数仅限临时测试，测试完成后必须删掉重新全量执行
- **局部 ≠ 完成**：用 `--limit 3` 测试前几镜后，必须删掉 limit 重新跑完整流程，保证全部镜头生成完毕

video_prompt 字段可供 Runway / Pika / Sora 等 AI 视频工具直接使用。

---

## Step 5 — ffmpeg 合成最终视频

图片生成完成后，调用 `compose_video.py` 合成最终 MP4：

### 用法

```bash
PYTHONPATH="$PWD/.claude/skills/video-script-generator/scripts" \
python .claude/skills/video-script-generator/scripts/compose_video.py \
  --project-dir "projects/${PROJECT_NAME}"
```

### 参数

| 参数 | 说明 |
|------|------|
| `--project-dir` / `-d` | 项目目录，默认当前目录 |
| `--tlimit` / `-n` | 只合成前 N 个镜头，0=全部（默认 0） |
| `--output` / `-o` | 输出文件名，默认 `output.mp4`，保存在项目目录下 |
| `--fade-duration` | dissolve 转场秒数，默认 0.5 |
| `--dry-run` | 只打印 ffmpeg 命令，不执行 |

### 前置校验

- **`script.json`** — 必选，读取分镜列表和 `duration_seconds`
- **`scene-XX.png`** — 每个镜头必须有对应图片，缺失则报错退出
- **`scene_boundaries.json`** — 可选，有则精确对齐配音时间；无则用 `duration_seconds`
- **TTS `*.mp3`** — 可选，有则合成配音；无则纯视频输出

### 时长规则

| 镜头类型 | 时长来源 | 说明 |
|----------|----------|------|
| `cover`（duration_seconds=0） | 跳过 | 封面卡无独立停留，与首镜 hook 合并 |
| `cover`（duration_seconds=1） | script.duration_seconds | 纯视觉停留，无声 |
| 有口播的镜头（有 scene_boundaries） | scene_boundaries start_ms/end_ms | 配音精确对齐 |
| 有口播但无 scene_boundaries | script.duration_seconds | 回退到脚本配置时长 |

### 输出规格

- 分辨率: 由 `production_notes.aspect_ratio` + `quality` 决定（如 9:16 2K → 1152×2048）
- 编码: H.264 + AAC
- 转场: 全部镜头之间 dissolve 0.5s（可调），首尾 fade in/out
- 每镜有配音 → 截取 TTS 对应区间；无配音 → 静音
- 总时长 = Σ(每镜时长) - (镜头数 - 1) × 转场秒数

### 合成策略

- **全量合成（默认）**：不加 `--tlimit`，**所有镜头全量合成，缺图直接报错不跑**
- **测试预览**：`--tlimit 3` 仅限临时测试前 3 镜效果，测试完必须全量重跑

---

## 📁 文件索引

| 文件 | 说明 |
|------|------|
| `SKILL.md` | **本文件** — 技能定义与完整执行流程 |
| `prompts/01-system-prompt.md` | **核心系统提示词** — 定义AI角色、脚本写作方法论、质量标准 |
| `prompts/02-video-prompt-engineering.md` | 视频提示词工程规范（10大要素 + 示例） |
| `prompts/03-image-prompt-engineering.md` | 图像提示词工程规范（8大要素 + 示例） |
| `templates/storyboard-template.json` | 分镜头脚本 JSON 模板（含字段注释和示例值） |
| `templates/storyboard-schema.json` | JSON Schema 校验文件 |
| `scripts/validate_script.py` | 脚本校验工具（读取 schema 校验 script.json） |
| `scripts/gen_tts.py` | **不动** — 火山引擎双向 TTS V3 |
| `scripts/align_scenes.py` | **不动** — TTS 时间戳与场景口播对齐 |
| `scripts/gen_scenes.py` | gpt-image-2 文字生图（Python，通过 Chat Completions 接口） |
| `scripts/compose_video.py` | **Step 5** — ffmpeg 合成最终视频（图片 + TTS 配音 + 转场） |
| `scripts/protocols/` | **不动** — TTS WebSocket 协议 |
| `examples/example-storyboard.json` | 完整示例（选题：量子计算科普） |

## 📐 工业级质量标准清单

每个生成的脚本必须满足以下全部条件：

- [ ] **scenes 包含全部镜头** — `cover`、`hook`、`outro` 都必须在 `scenes[]` 中独占一个镜头，一个不缺。视频合成直接遍历 `scenes[]`，不再读取顶层字段
- [ ] **结构完整** — 包含 `cover`、`hook`、`scenes`(≥5个)、`outro`
- [ ] **ID 唯一递增** — 每个 scene 有唯一递增 ID（scene-01 ~ scene-N）
- [ ] **时间对齐** — 各 scene 的 `duration_seconds` 之和 ≈ narration.txt 朗读时长
- [ ] **口播完整** — 镜头切换时口播不中断，type=hook 的首镜 narration 与 hook.text 一致，type=outro 的末镜 narration 与 outro.text 一致
- [ ] **无口播镜头** — 纯视觉镜头（封面卡、b-roll）narration 留空字符串 `""`
- [ ] **双提示词** — 每个 scene 同时包含 `video_prompt` 和 `image_prompt`
- [ ] **提示词可用** — 提示词是**完整自然语言描述**，可直接输入 AI 工具使用
- [ ] **提示词锁风格不锁尺寸** — 画幅和画质由 production_notes + Python 脚本通过 API size 传入，提示词只锁风格、光影、叙事逻辑
- [ ] **production_notes 包含 aspect_ratio 和 quality** — 不得再使用 resolution 字段
- [ ] **钩子有效** — hook 文本 ≤ 30 字，前 3 秒内完成注意力抓取
- [ ] **CTA 明确** — outro 包含明确的行动号召
- [ ] **Schema 通过** — 通过 `storyboard-schema.json` 校验，零错误
