# GPT-Image-2 图像 Prompt 规范

> 用于 Step2 中向 GPT-Image-2 API 提交的图像生成 Prompt 规范。
> 所有 Prompt 必须用英文撰写，风格统一。

---

## 通用风格前缀

所有图像 Prompt 必须以以下固定风格前缀开头：

```
Flat illustration, educational style, clean composition, vibrant yet soft colors, 
no text overlays, centered subject, 16:9 landscape aspect ratio, white or light background,
```

---

## 各段落类型 Prompt 模板

### hook（钩子）

```
{{通用风格前缀}}
A curious {{target_audience}} looking at {{visual_element}}, 
questioning expression, {{scene_context}},
subtle lighting highlighting the subject, surreal yet educational atmosphere
```

**示例**（主题：光合作用）：
```
Flat illustration, educational style, clean composition, vibrant yet soft colors, 
no text overlays, centered subject, 16:9 landscape aspect ratio, white or light background,
A curious child looking at a glowing green leaf under sunlight, 
questioning expression, surrounded by floating oxygen bubbles and light particles,
subtle lighting highlighting the leaf, surreal yet educational atmosphere
```

### content（内容分镜）

```
{{通用风格前缀}}
{{scientific_concept}} visualized as a clear diagram, 
{{visual_elements}}, labeled elements in a minimalist style, 
step-by-step visual explanation, {{color_scheme}} color palette
```

**示例**（主题：光合作用——光反应阶段）：
```
Flat illustration, educational style, clean composition, vibrant yet soft colors, 
no text overlays, centered subject, 16:9 landscape aspect ratio, white or light background,
Photosynthesis light reaction visualized as a clear diagram, 
chloroplast structure with thylakoid membrane, sun rays hitting the membrane, 
water molecules splitting, ATP and NADPH production arrows, 
labeled elements in a minimalist style, step-by-step visual explanation, 
green and yellow color palette
```

### summary（总结）

```
{{通用风格前缀}}
Mind map or infographic style summary of {{topic}} key points, 
{{number_of_points}} main ideas connected with simple lines, 
icon-based visual anchors for each point, study notes aesthetic, 
cohesive overview design
```

**示例**：
```
Flat illustration, educational style, clean composition, vibrant yet soft colors, 
no text overlays, centered subject, 16:9 landscape aspect ratio, white or light background,
Mind map or infographic style summary of photosynthesis key points, 
4 main ideas connected with simple lines: sunlight, water, chlorophyll, glucose, 
icon-based visual anchors for each point, study notes aesthetic, cohesive overview design
```

---

## Prompt 编写原则

| 原则 | 说明 | 反例 | 正例 |
|------|------|------|------|
| **具体而非抽象** | 具体描述画面元素 | "展示光合作用" | "叶绿体内部的类囊体膜结构，阳光粒子射入" |
| **视觉优先** | 描述看到的东西而非概念 | "解释电子传递链" | "蛋白质复合体嵌入膜中，电子沿阶梯向下传递" |
| **色彩引导** | 指定主色调 | "好看的图" | "绿色和黄色为主色调，蓝色点缀" |
| **构图明确** | 描述主体位置关系 | "讲解图" | "主体居中，左侧标注箭头从右往左" |
| **无文字** | 画面不包含文字 | 画面上写字 | 纯视觉元素表达 |
| **风格一致** | 所有分镜保持同一插画风格 | 前一个写实后一个卡通 | 全部 Flati Illustration |

---

## 禁止项

- ❌ 画面中包含文字/标注（文字由 FFmpeg drawtext 处理）
- ❌ 写实摄影风格（统一扁平化插画）
- ❌ 复杂的 3D 渲染风格
- ❌ 暗黑/恐怖/血腥元素
- ❌ 政治敏感或争议性内容
- ❌ 人物面部特写（增加生成难度，改为全身/半身）

---

## 推荐配色方案

| 主题类型 | 推荐配色 |
|----------|---------|
| 自然科学（生物/化学） | 绿色 + 黄色 + 白色 |
| 物理/天文 | 深蓝 + 紫色 + 白色 |
| 地理/环境 | 蓝色 + 绿色 + 大地色 |
| 数学/逻辑 | 橙色 + 蓝色 + 灰色 |
| 技术/编程 | 蓝色 + 紫色 + 白色 |

---

## 质量检查清单

每个生成的 Prompt 在发送前应检查：

- [ ] 是否以通用风格前缀开头？
- [ ] 是否全部使用英文？
- [ ] 是否包含具体视觉元素描述？
- [ ] 是否指定了色彩？
- [ ] 是否无文字要求？
- [ ] 是否符合该段落类型模板？
- [ ] 是否在 50~200 个英文单词之间？
- [ ] 画面描述是否在物理上可绘制？
