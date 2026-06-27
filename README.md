# Science Video — AI 科普视频自动生成系统

基于 **Claude + TTS + 文生图** 的自动化科普视频生产流水线，输入选题主题即可全自动输出口播稿、分镜头脚本、配音、配图，并合成完整视频。

---

## 主要功能

- **脚本自动生成** — 输入选题，AI 自动输出全量口播稿 + 工业级分镜头脚本
- **TTS 配音** — 基于火山引擎双向 TTS V3 API，支持 120+ 音色
- **文生图** — 基于 `gpt-image-2` 模型逐镜生成配图
- **视频合成** — 自动对齐配音与画面，支持 dissolve 转场
- **流水线自动化** — Issue → 分支 → 开发 → 测试 → 合并 → 日志 全自动

---

## 快速开始

### 环境准备

```bash
# 克隆项目
git clone git@github.com:opcfactoryai/science-video.git
cd science-video

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入密钥
```

### 环境变量

在 `.env` 中配置以下密钥：

| 变量 | 说明 |
|------|------|
| `VOLC_APPID` | 火山引擎 App ID |
| `VOLC_ACCESS_TOKEN` | 火山引擎访问令牌 |
| `VOLC_SECRET_KEY` | 火山引擎密钥 |
| `IMAGE_API_KEY` | 图片生成 API 密钥 |

---

## 工作流程

### Step 1: 生成口播稿与分镜头脚本

```bash
cd D:/labs/science-video
# 使用 video-script-generator skill 生成 script.json
```

### Step 2: 生成 TTS 配音

```bash
PROJECT_DIR=projects/your-project
python -c "
import json
with open('$PROJECT_DIR/script.json', encoding='utf-8') as f:
    for s in json.load(f)['scenes']:
        if s.get('narration'): print(s['narration'])
" > "$PROJECT_DIR/tts_text.txt"

PYTHONPATH="$PWD/.claude/skills/video-script-generator/scripts" \
python .claude/skills/video-script-generator/scripts/gen_tts.py \
  --appid "${VOLC_APPID}" \
  --access_token "${VOLC_ACCESS_TOKEN}" \
  --resource_id "seed-tts-2.0" \
  --voice_type "zh_male_yizhipiannan_uranus_bigtts" \
  --text "$(cat $PROJECT_DIR/tts_text.txt)" \
  --encoding mp3 \
  --output-dir "$PROJECT_DIR"
```

### Step 3: 生成图片

```bash
python .claude/skills/video-script-generator/scripts/gen_scenes.py \
  --project-dir projects/your-project
```

### Step 4: 合成视频

```bash
python .claude/skills/video-script-generator/scripts/compose_video.py \
  --project-dir projects/your-project
```

---

## 项目结构

```
├── .claude/
│   └── skills/video-script-generator/  # 核心 SKILL
│       ├── prompts/                    # 系统提示词
│       ├── scripts/                    # 生成脚本
│       │   ├── gen_tts.py             # TTS 配音生成
│       │   ├── gen_scenes.py          # 图片生成
│       │   ├── compose_video.py       # 视频合成
│       │   └── align_scenes.py        # 场景对齐
│       └── templates/                  # 分镜模板
├── projects/                           # 项目输出目录
├── .github/
│   └── issue-log.md                   # 流水线执行日志
└── CONTRIBUTING.md                    # 贡献指南
```

---

## 流水线自动化

项目配置了定时任务（每 20 分钟），自动执行以下流程：

1. 检查 GitHub Issue
2. 标记 In Progress
3. 创建分支并开发
4. 提交 PR 并合并到 main
5. 记录执行日志
6. 关闭 Issue

---

## License

MIT
