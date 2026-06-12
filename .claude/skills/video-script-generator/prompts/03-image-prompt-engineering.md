# 🖼️ 图像提示词工程规范

## 概述

本规范定义分镜脚本中 `image_prompt`（关键帧/缩略图图像提示词）的撰写标准。
高质量图像提示词需要兼顾**艺术性**、**工程可用性**和**风格一致性**。

---

## 一、图像提示词语法模板

```
[{Subject}], [{Composition}].
[{Background/Environment}], [{Lighting}].
[{Color Scheme}], [{Mood}].
[{Style}], [{Quality Markers}].
```

最终输出需为**流畅的自然语言段落**。

---

## 二、8 大要素详解

### 1. Subject（主体）

主体描述需要具体到可渲染级别：
- **外观**：颜色、形状、材质、大小比例、纹理
- **状态**：运行中/静止/打开/关闭/发光/透明
- **细节**：表面刻印、指示灯、连接线、反射
- **数量**：单个/一对/阵列/群体

> ✅ "A glowing quantum processor chip with intricate gold circuit patterns, approximately 2cm square, mounted on a circular PCB"
> ❌ "A quantum chip"

### 2. Composition（构图）

| 构图方式 | 效果 | 使用场景 |
|----------|------|----------|
| `centered composition` | 稳定、庄重 | 封面、正式展示 |
| `rule of thirds` | 平衡、自然 | 大多数场景 |
| `asymmetric` | 动感、现代 | 科技、创意内容 |
| `symmetrical` | 正式、对称美 | 建筑、官方展示 |
| `leading lines` | 引导视线 | 引导到主体 |
| `frame within frame` | 层次感 | 叙事场景 |
| `top-down view` | 俯视平面 | 布局、数据展示 |
| `eye-level` | 自然的 | 代入感 |
| `low angle looking up` | 主体显高大 | 大场景 |
| `dynamic diagonal` | 不稳定感 | 冲突、变化 |
| `negative space on top` | 留下空间 | 封面文字叠加 |

> **封面图特别要求**：必须使用 `negative space on top` 或 `dark gradient area on upper third` 为标题文字预留空间。

### 3. Background / Environment（背景/环境）

- 具体场景类型（实验室/太空/显微镜下/城市夜景/白棚）
- 深度层次（前景/中景/背景分离）
- 背景细节丰富度（极简/丰富/混乱/有序）

### 4. Lighting（光照）

同视频提示词规范。图像提示词中光照描述可以更精细：

| 光照描述 | 效果 |
|----------|------|
| `studio softbox lighting from the left` | 专业产品照 |
| `dramatic side lighting` | 强烈明暗对比 |
| `soft natural light from window` | 柔和自然 |
| `bi-directional lighting, cool left + warm right` | 双色调效果 |
| `rim light highlighting the edges` | 轮廓突出 |
| `glowing light emitted from within the subject` | 自发光效果 |
| `god rays through volumetric fog` | 神圣感 |
| `underlit from below` | 诡异/科技感 |

### 5. Color Scheme（配色方案）

| 配色 | 主色+辅助色示例 |
|------|-----------------|
| `monochromatic blue` | 深蓝#0a1628 + 冰蓝#7ec8e3 |
| `tech cyan-orange` | 青色#00d4ff + 橙色#ff6b35 |
| `scientific cool` | 靛蓝#1a237e + 银灰#b0bec5 |
| `nature warm` | 翠绿#2e7d32 + 琥珀#ff8f00 |
| `futuristic neon` | 品红#ff0080 + 霓虹蓝#00f0ff |
| `minimalist grayscale` | 冷灰#37474f + 白#ffffff |
| `academic classic` | 深红#8b0000 + 象牙白#fffff0 |

> **不用精确写出色值**，用描述性语言：「深蓝与冰蓝的冷色调搭配，辅以金色高光」

### 6. Mood / Atmosphere（情绪/氛围）

同视频规范。额外建议：
- 封面图：`awe-inspiring`, `mysterious`, `premium`
- 解释性镜头：`clear`, `educational`, `inviting`
- 数据镜头：`professional`, `trustworthy`, `crisp`

### 7. Style（艺术风格）

| 风格 | 适用场景 |
|------|----------|
| `photorealistic` | 实拍感，产品展示 |
| `cinematic still` | 电影质感，叙事类 |
| `3D render` | CG 渲染感，科技内容 |
| `isometric 3D` | 信息图示、架构 |
| `vector illustration` | 扁平化、科普 |
| `hand-drawn sketch` | 白板、轻松感 |
| `infographic style` | 数据展示 |
| `watercolor` | 艺术类、人文 |
| `concept art` | 世界观展示 |
| `minimalist flat design` | 简洁、现代 |
| `retro futurism` | 复古未来感 |

> **一致性要求**：同一视频的所有分镜图，style 描述必须一致。不要一个镜头是 photorealistic，另一个是 vector illustration。

### 8. Quality Markers（质量标记）

适量使用（2-3 个即可，不要堆砌）：

```
8K resolution, highly detailed, sharp focus
award-winning photography, intricate details
trending on ArtStation, masterpiece quality
ultra HD, hyperrealistic, crisp detail
professional photography, extreme detail
```

---

### 8. Aspect Ratio & Quality（画幅与画质）— 末尾必锁

每个 `image_prompt` 的末尾**必须**追加 `aspect_ratio` 和 `quality`。格式统一如下：
```
, aspect ratio 16:9, quality 2K
```

| 参数 | 可选值 | 说明 |
|------|--------|------|
| `aspect_ratio` | `16:9` 或 `9:16` | 横屏/竖屏，全片统一 |
| `quality` | `1K` / `2K` / `4K` | 默认 `2K`。LLM 不支持自定义分辨率 |

> ⚠️ **这是硬性要求：** 每个 `image_prompt` 末尾都必须锁死这两个参数，100%覆盖，一个镜头不能少。生成脚本后通过 validate_script.py 自动校验。

---

## 三、场景类型与提示词策略

### 封面图 (cover)

```yaml
目标: 吸引点击，传达主题
构图: negative space on top / dark gradient on upper third
文字: 预留上方 1/3 空间
风格: premium, high-impact, magazine-cover quality
技巧: 使用 dramatic lighting + deep shadows 制造视觉冲击
```

### 概念解释图 (explainer)

```yaml
目标: 讲清楚抽象概念
构图: centered or rule of thirds
风格: 清晰为主，可以偏教育风格
技巧: 使用 visual metaphors（视觉隐喻）
```

### 数据可视化 (data-viz)

```yaml
目标: 展示数据或对比
构图: symmetrical or top-down
风格: infographic, clean, precise
技巧: 包括图表的视觉元素（柱状、折线、粒子）
```

### 类比图 (analogy)

```yaml
目标: 用熟悉事物解释陌生概念
构图: side-by-side comparison 或 split view
风格: illustrative, creative
技巧: 并置对比（左边旧/右边新，左边大/右边小）
```

---

## 四、高质量 vs 低质量对比

### 封面图对比

**❌ 低质量：**
> "量子计算机，蓝色，科技感"

**✅ 高质量：**
> "A dramatic wide shot of an open quantum computer revealing its inner cryogenic chamber with golden wire cascades. Composition follows the rule of thirds with the glowing chip on the lower-left and intricate cooling pipes filling the upper-right. Deep blue and warm gold color scheme creates a premium technology feel. Volumetric fog with subtle light rays. Photorealistic CG render, 8K, sharp focus. The upper third of the image has dark negative space suitable for text overlay. Cinematic lighting with strong contrast."

### 解释性镜头对比

**❌ 低质量：**
> "芯片内部结构"

**✅ 高质量：**
> "An extreme close-up macro view of a quantum chip surface, revealing intricate etching patterns and golden bond wires. Centered composition with the chip at 45-degree angle for depth. Dark background with blue ambient lighting. The circuit traces glow with cyan light, suggesting data flow. Shallow depth of field with focus on the chip center. Photorealistic style. High contrast with metallic reflections. Scientific and precise atmosphere."

---

## 五、风格一致性检查清单

- [ ] 所有分镜的 art style 描述一致
- [ ] 所有分镜的光照风格协调
- [ ] 所有分镜的色调在同一色系内
- [ ] 封面图预留了文字空间
- [ ] 每个提示词都包含主体、构图、背景、光照、风格
- [ ] 没有使用模糊词（beautiful / nice / amazing）
