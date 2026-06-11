# 🎬 Video Script Generator — 架构文档

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v2.0 | 2026-06-10 | 初始架构：分镜头脚本生成 + TTS + Scene出图 |
| v2.1 | 2026-06-10 | 新增 Scene边界对齐算法分析（算法原理 + 文本规范） |

---

## 一、系统全链路

```
                          ┌─────────────────────────────┐
                          │      用户输入选题主题          │
                          └─────────────┬───────────────┘
                                        │
                          ┌─────────────▼───────────────┐
                          │   prompts/01-system-prompt.md │
                          │   prompts/02-video-prompt.md  │
                          │   prompts/03-image-prompt.md  │
                          └─────────────┬───────────────┘
                                        │ 注入 System Prompt
                          ┌─────────────▼───────────────┐
                          │      AI 生成 script.json      │
                          │                              │
                          │  ┌──────────────────────┐   │
                          │  │  meta (元信息)         │   │
                          │  │  cover (封面设计)      │   │
                          │  │  hook (钩子)           │   │
                          │  │  full_narration (全稿) │   │
                          │  │  scenes[] (分镜头)     │   │
                          │  │  │  ├ narration       │   │
                          │  │  │  ├ video_prompt    │   │
                          │  │  │  └ image_prompt    │   │
                          │  │  outro (结尾)          │   │
                          │  │  production_notes     │   │
                          │  └──────────────────────┘   │
                          └─────────────┬───────────────┘
                                        │
              ┌─────────────────────────┼─────────────────────────┐
              │                         │                         │
              ▼                         ▼                         ▼
   ┌──────────────────┐    ┌──────────────────────┐   ┌──────────────────┐
   │  validate_script  │    │ 提取 narration.txt    │   │ gen_scenes.py    │
   │  (Schema校验)     │    │ (去时间戳 → 纯口播)    │   │ (gpt-image-2)    │
   └──────────────────┘    └──────────┬───────────┘   └──────────────────┘
                                      │
                                      ▼
                           ┌──────────────────────┐
                           │    gen_tts.py         │
                           │   (火山引擎 TTS V3)    │
                           └──────────┬───────────┘
                                      │ 同时输出
                                      ├────────────────────┐
                                      ▼                    ▼
                           ┌────────────────┐    ┌───────────────────┐
                           │ audio.mp3      │    │ timestamps.json   │ ← 🆕
                           │ (连续无卡顿音频) │    │ (每字时间戳数组)   │
                           └────────────────┘    └────────┬──────────┘
                                                          │
                                                          ▼
                                               ┌──────────────────────┐
                                               │ scene_boundary.py    │ ← 🆕
                                               │ 双指针顺序匹配        │
                                               └──────────┬───────────┘
                                                          │
                                                          ▼
                                               ┌──────────────────────┐
                                               │ scene_boundaries.json│
                                               │ scene-01: 0-1050ms   │
                                               │ scene-02: 1051-3200ms│
                                               │ scene-03: 3201-4800ms│
                                               └──────────────────────┘
```

---

## 二、核心数据结构

### 2.1 script.json（已有）

```json
{
  "scenes": [
    {
      "id": "scene-01",
      "narration": "Anthropic 发布了 Fable 5，这是一个全新的 Mythos-class 模型。",
      "duration_seconds": 15,
      ...
    },
    {
      "id": "scene-02", 
      "narration": "它在旧金山举办黑客松，奖金高达15万美元。",
      "duration_seconds": 12,
      ...
    }
  ],
  "full_narration": "[00:00-00:15] Anthropic 发布了 Fable 5...\n[00:15-00:27] 它在旧金山举办黑客松..."
}
```

### 2.2 timestamps.json（🆕 新增）

gen_tts.py 在输出 audio.mp3 的同时，把 TTS 引擎返回的 `words` 时间戳写到这个文件：

```json
{
  "words": [
    {"text": "Anthropic", "start_ms": 0,    "end_ms": 420},
    {"text": "发布了",     "start_ms": 421,  "end_ms": 680},
    {"text": "Fable",     "start_ms": 681,  "end_ms": 820},
    {"text": "5",         "start_ms": 821,  "end_ms": 1050},
    {"text": "这是一个",   "start_ms": 1051, "end_ms": 1280},
    {"text": "全新的",     "start_ms": 1281, "end_ms": 1500},
    {"text": "Mythos",    "start_ms": 1501, "end_ms": 1750},
    {"text": "class",     "start_ms": 1751, "end_ms": 1920},
    {"text": "模型",      "start_ms": 1921, "end_ms": 2100},
    {"text": "它在",      "start_ms": 2101, "end_ms": 2320},
    ...
  ],
  "total_duration_ms": 27000,
  "generated_at": "2026-06-10T12:00:00Z",
  "voice_type": "zh_male_yizhipiannan_uranus_bigtts"
}
```

### 2.3 scene_boundaries.json（🆕 新增）

```json
{
  "scenes": [
    {"id": "scene-01", "start_ms": 0,     "end_ms": 2100, "duration_ms": 2100},
    {"id": "scene-02", "start_ms": 2101,  "end_ms": 5000, "duration_ms": 2899}
  ],
  "narration_word_count": 380,
  "total_audio_duration_ms": 27000,
  "total_scenes_duration_ms": 27000
}
```

---

## 三、双指针顺序匹配算法

### 3.1 算法原理图

```
场景列表 (scenes[])
   scene-01: "Anthropic 发布了 Fable 5"
   scene-02: "它在旧金山举办黑客松"
   scene-03: "你需要去旧金山参加活动"
     │
     │ 指针 P 在场景列表上:
     │ scene-01 → scene-02 → scene-03 (只向右移动)
     ▼

TTS words 数组 (words[])
   pos 0: "Anthropic"   (0-420ms)    ◄── P=scene-01 从这里开始匹配
   pos 1: "发布了"      (421-680ms)       │
   pos 2: "Fable"       (681-820ms)       │ 
   pos 3: "5"           (821-1050ms)      │ 拼接 = "Anthropic发布了Fable5"
   pos 4: "这是一个"    (1051-1280ms)  ◄── 匹配完成，P=scene-01 end=1050ms
   pos 5: "全新的"      (1281-1500ms)  ◄── P=scene-02 从这里开始
   pos 6: "Mythos"      (1501-1750ms)      │
   pos 7: "class"       (1751-1920ms)      │
   pos 8: "模型"        (1921-2100ms)      │
   pos 9: "它在"        (2101-2320ms)      │
   pos10: "旧金山"       (2321-2550ms)      │ 拼接 = "这是一个全新的Mythosclass..."
   pos11: "举办"        (2551-2780ms)  ◄── 匹配完成，P=scene-02 end=2780ms
   pos12: "黑客松"       (2781-3000ms)  ◄── P=scene-03 从这里开始
   ...
```

### 3.2 伪代码

```python
def match_scene_boundaries(scenes, words):
    """
    输入：scenes[] — 场景列表（含 narration 字段）
    输入：words[]  — TTS 时间戳数组（含 text/start_ms/end_ms 字段）
    输出：scene_boundaries[]
    
    约束条件：
    - scenes 和 words 的顺序完全一致
    - 每个 scene.narration 是 full_narration 的一个子串
    - 指针只往前走，不回溯
    """
    result = []
    word_pos = 0  # 指针 Q：在 words 数组上的位置
    
    for scene in scenes:
        # 1. 标准化：去空格、去标点、统一大小写
        target = normalize(scene.narration)
        
        # 2. 从当前 word_pos 开始拼接字符
        buf = ""
        start_ms = words[word_pos].start_ms  # 记录开始时间
        matched = False
        tolerance = 0  # 容错：TTS 可能额外插入 1-2 个字
        
        while word_pos < len(words) and len(buf) < len(target) + 3:
            buf += normalize(words[word_pos].text)
            
            # 3. 检查前缀匹配
            if target.startswith(buf):
                matched = True
                word_pos += 1
                continue
            
            # 4. 防 TTS 插字：如果前缀对不上但有容错额度，跳过当前 word
            if tolerance < 2 and not target.startswith(buf):
                tolerance += 1
                # 回退：当前 word 可能是 TTS 额外插入的
                buf = buf[:-len(normalize(words[word_pos].text))] if len(normalize(words[word_pos].text)) <= len(buf) else ""
                word_pos += 1
                continue
            
            word_pos += 1
        
        end_ms = words[word_pos - 1].end_ms
        
        if not matched:
            raise MatchError(f"无法匹配 scene {scene.id}")
        
        result.append({
            "id": scene.id,
            "start_ms": start_ms,
            "end_ms": end_ms,
            "duration_ms": end_ms - start_ms
        })
    
    return result
```

### 3.3 归一化规则

```python
def normalize(text):
    """标准化：去空格、去标点、统一大小写、NFC 归一化"""
    import unicodedata
    import re
    text = unicodedata.normalize('NFC', text)        # Unicode 归一化
    text = text.lower()                               # 转小写（英文）
    text = re.sub(r'[\s　\'"“”‘’\[\]【】\(\)]', '', text)  # 去空格+引号+括号
    text = re.sub(r'[，。！？、：；·～—…\-\–\—]', '', text)       # 去中文标点
    return text
```

### 3.4 为什么各种边缘场景都不会错

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 场景                                    │ 不会错的原因                      │
├────────────────────────────────────────┼──────────────────────────────────┤
│ "旧金山" 在 scene-02 和 scene-03 都出现  │ 指针 Q 匹配完 scene-02 后已走过   │
│                                         │ 第一个"旧金山"，不会回头再看       │
├────────────────────────────────────────┼──────────────────────────────────┤
│ "Fable 5" 中英文混合                    │ 去空格后 "Fable5" = "Fable5"     │
├────────────────────────────────────────┼──────────────────────────────────┤
│ TTS 把 "旧金山" 分成"旧"+"金"+"山"        │ words 拼接还是"旧金山"，匹配的是   │
│                                         │ 字符序列，不是词边界              │
├────────────────────────────────────────┼──────────────────────────────────┤
│ TTS 额外插了一个"嗯"                     │ 容错窗口跳过该 word，继续匹配       │
├────────────────────────────────────────┼──────────────────────────────────┤
│ scene 口播很长，包含3个句号               │ 整个 scene.narration 作为一个整体  │
│                                         │ 匹配，不按句号切分                │
├────────────────────────────────────────┼──────────────────────────────────┤
│ 两个场景口播内容完全一样                   │ 指针位置不同，search window 起点  │
│ (如都说"总而言之AI很重要")               │ 不同，匹配到的是不同位置的文本       │
└────────────────────────────────────────┴──────────────────────────────────┘
```

---

## 四、口播文本规范（Narration Constraints）

### 4.1 核心约束

为了让上述算法 100% 工作，**只需满足一条规则**：

> **每个 `scene.narration` 必须是 `full_narration` 中按顺序出现的一个连续子串。**

不需要任何标点规范。不需要中英文规范。

### 4.2 详细解释

```json
{
  "full_narration": "今天我们要讲Fable 5。这是一个强大的模型。它在旧金山有活动。",
  
  "scenes": [
    {"narration": "今天我们要讲Fable 5。这是一个强大的模型。"},   ✅ 连续子串
    {"narration": "它在旧金山有活动。"}                           ✅ 连续子串
  ]
}
```

```json
{
  "full_narration": "今天我们要讲Fable 5。",
  
  "scenes": [
    {"narration": "今天我们要讲Fable 5。"},    ✅ 子串
    {"narration": "这是一个强大的模型。"}      ❌ 不在 full_narration 中 → 无法匹配
  ]
}
```

### 4.3 系统提示词需新增的要求

在 `prompts/01-system-prompt.md` 中新增一条输出质量检查（第 7 章）：

```
新增检查项：

[ ] **文本一致性** — 每个 scene.narration 必须是 full_narration 的连续子串，
    且所有 scene.narration 按顺序拼接后 ≈ full_narration。
    不要在 scene.narration 里写 full_narration 中没有的过渡句。
```

### 4.4 不需要的约束

以下内容不需要在提示词中限制：

| 不需要限制 | 原因 |
|-----------|------|
| 句号数量 | 算法按完整文本匹配，不依赖句号 |
| 逗号规范 | 归一化会去掉逗号 |
| 中英文比例 | 字符序列匹配自动处理 |
| 标点使用 | 归一化层统一处理 |
| 场景口播长度 | 只要 ≥10 字即可（过短有误匹配风险） |

### 4.5 场景口播最小长度

| 长度 | 风险 | 建议 |
|------|------|------|
| <5 字 | 🟠 高 — 可能在 words 中误匹配到不相关的字 | 避免，合并到相邻场景 |
| 5-15 字 | 🟢 低 — 基本安全，但容错窗口不可用 | 可接受 |
| >15 字 | ✅ 零风险 | 推荐 |

---

## 五、输出文件依赖关系

```
script.json
    │
    ├──→ validate_script.py    → 校验通过/失败
    │
    ├──→ narration.txt          → gen_tts.py
    │                                │
    │                                ├──→ audio.mp3
    │                                └──→ timestamps.json
    │                                        │
    │                                        └──→ align_scenes.py
    │                                                 │ (同时读取 script.json)
    │                                                 ▼
    │                                          scene_boundaries.json
    │
    └──→ gen_scenes.py         → scene-01.png, scene-02.png...
```

---

## 七、与现有系统的兼容性

| 现有功能 | 受影响？ | 说明 |
|---------|---------|------|
| `gen_tts.py --no-split` | 不影响 | 时间戳保存对单段/多段模式通用 |
| `gen_tts.py` 默认模式 | 不影响 | 新增的 timestamps.json 是额外输出，不改变原有音频 |
| `validate_script.py` | 不影响 | schema 不变 |
| `gen_scenes.py` | 不影响 | 图片生成逻辑不改 |
| 现有 project 目录 | 兼容 | 新跑的项目才有 timestamps.json，旧项目不受影响 |
