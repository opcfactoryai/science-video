我设计了一个SKILL，视频生成系统。需求如下：1. 我输入选题主题。架构,输出全体口播稿全量+分镜头的script。脚本必须能满足工程真实需求包括封面，hock，脚本里面要详细给出提示词，没一个镜头的提示词，（每个镜头，2个提示词，一个视频，一个图像）
给我输出：

1.SKILL.md
2.分镜头的script。脚本必须能满足工程真实需求包括封面，hock，脚本里面要详细给出提示词，每一个镜头的提示词，（每个镜头，2个提示词，一个视频，一个图像）。脚本里面包括全量口播稿。 脚本需要工业级可用，每个细节都要做好，封面是什么，钩子，分镜头的细节，提示词全部要100%符合工业级。
3.生成script，要写好系统提示词，系统提示词你需要用一个单独文件描述，系统提示词关键点设计，如何让ai写一个好的视频分镜头脚本。
4.分镜头脚本模版，需要单独保存。确保根据前面提示词输出的脚本，必须每次100%可用。
4.根据分镜头脚本。1.输出tts 2.输出分镜头 。你用占位符我自己搞定。

给我输出整个SKILL zip。skill必须完整包含所有模版，提示词，SKILL.MD




```bash
cd D:/labs/science-video
PROJECT_DIR=projects/n1x-news-0610

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

### 🖼️ 生成图片

```bash
cd D:/labs/science-video
python .claude/skills/video-script-generator/scripts/gen_scenes.py \
  --project-dir projects/n1x-news-0610
```
