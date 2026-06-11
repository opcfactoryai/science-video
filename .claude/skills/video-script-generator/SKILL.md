---
name: video-script-generator
description: 工业级视频脚本生成系统。输入选题主题 → 输出全量口播稿 + 分镜头脚本（每镜头2个AI提示词：视频+图像），含封面设计、钩子、转场、BGM建议。脚本经 JSON Schema 校验，100% 工程可用。
---

# 🎬 Video Script Generator — 工业级视频脚本生成系统

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
    ├── Step 3: 基于 templates/storyboard-template.json 输出 JSON
    │   └── 自动通过 templates/storyboard-schema.json 校验
    │
    ├── Step 4: 保存到 projects/{project-name}-{MMDD}/
    │   ├── script.json          ← 完整分镜头脚本（核心产出）
    │   ├── narration.txt        ← 全量口播稿（TTS 直接消费）
    │   └── prompts_report.md    ← 提示词汇总（人工审阅用）
    │
    └── Step 5: 生产（用户自行调用已有脚本）
        ├── gen_tts.py           → 逐段 TTS 音频
        └── gen_scenes.py        → 逐镜 AI 图片
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

## Step 4 — 后续生产（用户自行调用）

`script.json` 可直接被已有脚本消费：

> ⚠️ **环境变量说明**：TTS 命令依赖 `.env` 文件中的 `VOLC_APPID` / `VOLC_ACCESS_TOKEN`。
> 每次执行前必须 `source .env` 加载变量，否则会报空。下面命令已包含。

### 🎤 生成 TTS 语音

```bash
cd D:/labs/science-video
source .env   # 👈 必须，加载火山引擎凭证
PROJECT_DIR=projects/${PROJECT_NAME}

# TTS 合成（--text 直接读取 Step 3 生成的 narration.txt）
PYTHONPATH="$PWD/.claude/skills/video-script-generator/scripts" \
source .env && python .claude/skills/video-script-generator/scripts/gen_tts.py \
  --appid "${VOLC_APPID}" \
  --access_token "${VOLC_ACCESS_TOKEN}" \
  --resource_id "seed-tts-2.0" \
  --voice_type "zh_male_yizhipiannan_uranus_bigtts" \
  --text "$(cat $PROJECT_DIR/narration.txt)" \
  --encoding mp3 \
  --output-dir "$PROJECT_DIR"
```

### 🖼️ 生成各分镜图片（XAI Router gpt-image-2）

```bash
# 脚本自动读取 .env，无需手动 source
cd D:/labs/science-video
node .claude/skills/video-script-generator/scripts/gen_scenes_xai.mjs \
  --project-dir "projects/${PROJECT_NAME}"
  # --count 2   # 限制只生成前N个镜头（调试省钱），默认500=全部生成
```

### 🎥 生成视频（待接入）

video_prompt 字段可供 Runway / Pika / Sora 等 AI 视频工具直接使用。

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
| `scripts/gen_scenes.py` | 旧版 — gpt-image-2 文字生图（Python） |
| `scripts/gen_scenes_xai.mjs` | **新版** — gpt-image-2 文字生图（Node.js，推荐） |
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
- [ ] **钩子有效** — hook 文本 ≤ 30 字，前 3 秒内完成注意力抓取
- [ ] **CTA 明确** — outro 包含明确的行动号召
- [ ] **Schema 通过** — 通过 `storyboard-schema.json` 校验，零错误
