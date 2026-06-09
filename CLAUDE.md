# 科普视频自动生成项目

## 项目结构

```
D:\labs\science-video
├── .env                          # API 凭证
├── CLAUDE.md                     # 本文件
├── package.json                  # 视频生成流水线
├── tsconfig.json
├── scripts/
│   ├── run.ts                    # 主入口
│   ├── 01_gen_script.ts          # 生成脚本
│   ├── 02_gen_assets.ts          # 生成素材
│   ├── 03_gen_concat.ts          # 拼接
│   └── 04_compose_video.ts       # 合成视频
├── examples/volcengine/
│   └── bidirection.py            # 火山引擎官方双向 TTS demo（不要修改）
├── protocols/                    # TTS 协议库
│   ├── __init__.py
│   └── protocols.py
├── volcengine_bidirection_demo/  # SDK 源码（已 pip install -e）
├── prompts/
│   ├── script.md
│   └── image.md
└── *.mp3                         # TTS 生成的音频文件
```

---

## 🔑 凭证（.env）

```
VOLC_APPID=7109772318
VOLC_ACCESS_TOKEN=dLDLksfdv5EbpscxVR76sYs6R4JqPkzQ
VOLC_SECRET_KEY=TSx5GzzLVFJrgQW4tD75dm3B9FaZYYJ7
```

---

## 🎤 火山引擎双向 TTS V3 调用

### 文档
- **双向 TTS V3 协议**: https://www.volcengine.com/docs/6561/1329505
- **音色列表**: https://www.volcengine.com/docs/6561/1257544

### 执行命令

```bash
cd D:/labs/science-video
PYTHONPATH="$PWD" python examples/volcengine/bidirection.py \
  --appid "${VOLC_APPID}" \
  --access_token "${VOLC_ACCESS_TOKEN}" \
  --resource_id "seed-tts-2.0" \
  --voice_type "zh_female_vv_uranus_bigtts" \
  --text "要合成的文本。" \
  --encoding mp3
```

**关键参数：**
| 参数 | 说明 | 必填 |
|------|------|------|
| `--appid` | APP ID（从 .env 读取） | 是 |
| `--access_token` | Access Token（从 .env 读取） | 是 |
| `--resource_id` | **必须用 `seed-tts-2.0`**（V3 双向） | 否（但 V3 必须指定） |
| `--voice_type` | 音色名称 | 是 |
| `--text` | 合成文本（句号自动分句，每句一个文件） | 是 |
| `--encoding` | `mp3`/`pcm`/`wav`/`ogg_opus`（默认 mp3） | 否 |
| `--endpoint` | `wss://openspeech.bytedance.com/api/v3/tts/bidirection`（默认） | 否 |

**注意：** 必须加 `PYTHONPATH="$PWD"`，否则找不到 `protocols` 模块。

### 音频输出
文件保存在当前目录，命名 `{voice_type}_session_{序号}.{encoding}`。

---

## 🎭 音色列表（seed-tts-2.0 资源）

> **已验证：** `zh_female_vv_uranus_bigtts` ✅
> S_ 开头的音色（如 `S_中文女声`）**不兼容** seed-tts-2.0，会报 "resource ID is mismatched"

### 中文女声

| 音色名称 | 风格描述 |
|----------|---------|
| `zh_female_vv_uranus_bigtts` | ✅ 已验证可用的自然女声 |
| `zh_female_vv_jupiter_bigtts` | 活泼灵动女声 |
| `zh_female_xiaohe_jupiter_bigtts` | 甜美活泼（台湾口音） |
| `zh_female_xueayi_saturn_bigtts` | 儿童绘本风格 |
| `zh_female_yueyunv_mars_bigtts` | 粤语口音 |

### 中文男声

| 音色名称 | 风格描述 |
|----------|---------|
| `zh_male_yunzhou_jupiter_bigtts` | 清爽沉稳男声 |
| `zh_male_yunzhou_bigtts` | 沉稳男声 |
| `zh_male_xiaotian_jupiter_bigtts` | 清爽磁性男声 |
| `zh_male_bv139_audiobook_ummv3_bigtts` | 高冷沉稳（有声阅读） |
| `zh_male_shenyeboke_emo_v2_mars_bigtts` | 深夜播客风格 |

### 角色扮演音色（可能需要不同 resource_id）

| 音色名称 | 风格描述 |
|----------|---------|
| `ICL_zh_female_liumengdie_v1_tob` | 清冷高雅 |
| `ICL_zh_female_linxueying_v1_tob` | 甜美娇俏 |
| `ICL_zh_female_rouguhunshi_v1_tob` | 柔骨魂师 |
| `ICL_zh_female_tianmei_v1_tob` | 甜美活泼 |
| `ICL_zh_female_chengshu_v1_tob` | 成熟温柔 |
| `ICL_zh_female_xnx_v1_tob` | 贴心闺蜜 |
| `ICL_zh_female_yry_v1_tob` | 温柔白月光 |
| `ICL_zh_male_xiaoge_v1_tob` | 寡言小哥 |
| `ICL_zh_male_renyuwangzi_v1_tob` | 清朗温润 |
| `ICL_zh_male_xiaosha_v1_tob` | 潇洒随性 |
| `ICL_zh_male_liyisheng_v1_tob` | 清冷矜贵 |
| `ICL_zh_male_qinglen_v1_tob` | 沉稳优雅 |
| `ICL_zh_male_chongqingzhanzhan_v1_tob` | 清逸苏感 |
| `ICL_zh_male_xingjiwangzi_v1_tob` | 温柔内敛 |
| `ICL_zh_male_sigeshiye_v1_tob` | 低沉缱绻 |
| `ICL_zh_male_lanyingcaohunshi_v1_tob` | 蓝银草魂师 |

> 完整音色列表请查阅：https://www.volcengine.com/docs/6561/1257544

---

## 🚀 视频生成流水线

```bash
npm start                    # 完整流程
npm run step1                # 生成脚本
npm run step2                # 生成素材
npm run step3                # 拼接
npm run step4                # 合成视频
```

需 Node.js >= 18.0.0。

---

## ⚠️ 踩坑记录

| 问题 | 原因 | 解决 |
|------|------|------|
| 403 Forbidden | Resource ID 不对 | 用 `seed-tts-2.0`，不用 `volc.megatts.default` |
| "resource ID is mismatched" | 音色与 resource_id 不匹配 | 用 bigtts 系列音色，不用 S_ 系列 |
| ModuleNotFoundError: protocols | 缺少 PYTHONPATH | 加 `PYTHONPATH="$PWD"` |
| Secret Key 不知道怎么用 | 当前 demo 只用 appid + access_token | Secret Key 保留备用 |
