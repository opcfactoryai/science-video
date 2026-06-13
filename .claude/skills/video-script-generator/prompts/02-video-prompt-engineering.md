# 🎬 视频提示词工程规范

## 概述

AI 视频生成模型（如 Runway Gen-3、Pika、Sora、Kling）对提示词的质量极为敏感。
本规范定义了一套工业级的视频提示词撰写标准，确保输出可直接用于主流 AI 视频工具。

---

## 一、视频提示词语法模板

```
[{Shot Type}] of [{Subject}] [{Action}] in [{Environment}].
Camera [{Camera Movement}], [{Lighting}].
[{Color Palette}], [{Atmosphere}].
[{Style}], [{Motion Dynamics}].
[{Additional Details for richness}]
```

**注意**：这是语法骨架，最终输出必须是**流畅的自然语言段落**，而非清单。

---

## 二、10 大要素详解

### 1. Shot Type（景别）— 画面框架

| 术语 | 中文 | 视觉效果 | 适用场景 |
|------|------|----------|----------|
| `extreme wide shot` | 极远景 | 人被环境吞没 | 展示宏大场景、宇宙、城市 |
| `wide shot` / `full shot` | 全景 | 全身与环境 | 建立场景感 |
| `medium wide shot` | 中全景 | 膝盖以上 | 人物+环境平衡 |
| `medium shot` | 中景 | 腰部以上 | 解说、对话 |
| `medium close-up` | 中近景 | 胸部以上 | 情感表达、重点强调 |
| `close-up` | 特写 | 脸部/物体局部 | 细节展示、情绪强化 |
| `extreme close-up` | 极特写 | 局部放大 | 微观细节、戏剧性 |
| `aerial view` / `bird's eye` | 航拍/俯视 | 90度向下 | 布局展示、规模感 |
| `low angle` | 低角度 | 仰视，主体显高大 | 威压感、宏伟感 |
| `dutch angle` | 倾斜镜头 | 画面倾斜 | 不安感、紧张感 |
| `over-the-shoulder` | 过肩镜头 | 越过肩部拍摄 | 对话、观察视角 |
| `POV` | 第一人称视角 | 所见即所得 | 沉浸感、代入感 |
| `macro` | 微距 | 微观世界放大 | 细节、纹理、精密 |

### 2. Camera Movement（运镜）— 镜头运动

| 术语 | 说明 | 叙事效果 |
|------|------|----------|
| `static` | 固定镜头 | 稳定、庄重、观察感 |
| `pan right/left` | 左右摇摄 | 展示环境、跟随运动 |
| `tilt up/down` | 上下倾斜 | 揭示全貌、从局部到整体 |
| `dolly in` | 推近 | 进入场景、聚焦重点 |
| `dolly out` | 拉远 | 揭示环境、孤立感 |
| `tracking` | 跟拍 | 同步运动、沉浸跟随 |
| `crane up/down` | 升降 | 规模感、气势变化 |
| `handheld` | 手持 | 真实感、纪录片感 |
| `steadycam` | 稳定跟随 | 平滑专业感 |
| `zoom in/out` | 变焦 | 推拉效果（数字变焦） |
| `whip pan` | 甩镜头 | 快速转场、动感 |
| `rack focus` | 焦点的转移 | 切换注意力方向 |
| `orbit` / `rotate around` | 环绕 | 360度展示主体 |
| `push in` | 急推 | 冲击感、紧迫感 |
| `slide` | 横移 | 展示环境 |

### 3. Subject（主体）

描述主体时需要包含：
- 外观（颜色、形状、材质、大小）
- 状态（运行中、静止、生长、衰变）
- 数量（单个、群体、阵列）
- 位置（居中、偏移、前景、背景）

### 4. Action（动作/运动）

视频提示词和图像提示词最大的区别就是**运动**。必须描述：
- 主体自身的运动（旋转、移动、生长、断裂、闪烁）
- 环境的动态（粒子流动、光线变化、流体运动）
- 运动的质感（平滑的、急促的、波浪式的、混沌的）

### 5. Environment（环境/背景）

- 空间类型（实验室、太空、微观世界、城市、自然）
- 空间氛围（空旷、拥挤、有序、混乱）
- 背景细节（墙壁纹理、远处物体、景深）

### 6. Lighting（光照）

| 光照类型 | 效果 |
|----------|------|
| `natural light` | 自然光，柔和真实 |
| `golden hour` | 黄金时刻，暖色调柔和 |
| `dramatic lighting` | 强烈明暗对比 |
| `soft diffused light` | 柔光，无硬阴影 |
| `backlit` | 逆光，轮廓光效果 |
| `rim light` | 边缘光，突出轮廓 |
| `volumetric lighting` | 体积光，光柱效果 |
| `neon glow` | 霓虹光效 |
| `studio softbox` | 影棚柔光箱 |
| `chiaroscuro` | 明暗对比法（伦勃朗光） |
| `harsh overhead` | 顶光，戏剧性 |
| `flickering light` | 闪烁光，不安感 |

### 7. Color Palette（色调）

| 色调 | 情绪 | 适用主题 |
|------|------|----------|
| `warm amber tones` | 温暖、怀旧 | 历史、人文 |
| `cool blue palette` | 冷静、科技感 | 科技、医疗 |
| `cyberpunk neon` | 赛博朋克 | 未来、科幻 |
| `monochrome` | 简约、专注 | 艺术、深度内容 |
| `vintage sepia` | 复古 | 历史、回忆 |
| `high contrast` | 强烈视觉冲击 | 动作、音乐 |
| `pastel` | 柔和、治愈 | 教育、心理 |
| `vibrant saturated` | 充满活力 | 产品、旅行 |
| `moody desaturated` | 低沉、严肃 | 深度报道 |
| `natural color` | 真实 | 纪录片 |

### 8. Atmosphere（氛围）

描述场景的情感质量：`mysterious`, `awe-inspiring`, `tense`, `peaceful`, `dramatic`, `whimsical`, `clinical`, `futuristic`, `nostalgic`, `hopeful`, `ominous`

### 9. Style（风格）

| 风格 | 说明 |
|------|------|
| `cinematic` | 电影感，24fps质感 |
| `documentary style` | 纪录片风格，真实感 |
| `3D animation` | 3D动画 |
| `2D motion graphics` | 2D动效设计 |
| `clay animation` | 黏土动画 |
| `photorealistic CG` | 照片级CG渲染 |
| `hand-drawn illustration` | 手绘插画风格 |
| `stop motion` | 定格动画 |
| `anime style` | 日本动画风格 |
| `infographic style` | 信息图风格 |
| `whiteboard animation` | 白板动画 |

### 10. Motion Dynamics（运动动态）

| 动态 | 效果 |
|------|------|
| `slow motion` | 慢动作，强调细节 |
| `time-lapse` | 延时摄影，表现时间流逝 |
| `hyperlapse` | 移动延时 |
| `smooth glide` | 平滑滑行 |
| `flowing` | 流动感，液体般 |
| `explosive` | 爆发式运动 |
| `gentle drift` | 轻柔漂移 |
| `pulsing` | 脉动感 |

---

### 10. 注意：画幅与画质由脚本自动处理

`aspect_ratio` 和 `quality` 是工程参数，由 Python 脚本通过 API `size` 参数统一传入。**绝对不要在 `video_prompt` 中写这些**。

> 🔴 **禁令：`video_prompt` 中不得出现：** `9:16`、`16:9`、`竖屏`、`横屏`、`aspect ratio`、`vertical composition`、`1K`、`2K`、`4K`、`quality`。这些由工程参数自动处理，出现在提示词中会造成 API 冲突。

提示词应锁死的是视觉风格、光影调性、构图逻辑、叙事氛围这些影响画面审美的要素。

---

## 三、高质量 vs 低质量对比

### 科技解释类场景

**❌ 低质量：**
> "A computer chip zooming in."

**✅ 高质量：**
> "A cinematic macro dolly-in from an extreme wide shot of a server room to an extreme close-up of a single quantum processor chip. The camera glides smoothly past rows of cooling infrastructure. The chip's surface reveals intricate etched circuits with laser-like light pulsing through waveguides. Cool blue volumetric lighting with dramatic shadows, creating a mysterious high-tech atmosphere. Photorealistic CG style with shallow depth of field. Slow motion particles of light float around the chip. Colors are deep indigo with cyan highlights."

### 科普类比场景

**❌ 低质量：**
> "A cat in a box."

**✅ 高质量：**
> "A medium shot of a stylized 3D animated cat inside a glass box with soft glow. The cat appears simultaneously sharp and ghostly transparent, suggesting quantum superposition. Camera slowly orbits around the box. Soft pastel lighting with warm pink and cool purple dual-tone color scheme. Whimsical but scientific atmosphere. 3D animation style with cel-shaded rendering. Gentle floating particles around the box. The scene should feel like a thought experiment visualized."

---

## 四、常见错误与修正

| 错误 | 问题 | 修正方案 |
|------|------|----------|
| 只有静态描述 | 无运动 = 浪费视频能力 | 加入至少 2 个动态动词 |
| 要素堆砌 | "close-up medium shot" 矛盾 | 确定一个主景别 |
| 过度修饰 | "8K cinematic ultra-HDR photorealistic" | 选 2-3 个质量词 |
| 缺少主体 | "Beautiful lighting in space" | 明确画面中有什么 |
| 情绪空洞 | 只有视觉没有情感 | 加入 atmosphere 词 |
