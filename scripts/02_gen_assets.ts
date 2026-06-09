#!/usr/bin/env npx ts-node
/**
 * Step 2: 并行生成所有分镜资产（图像 + 语音 + 封面/片尾静态帧）
 * 用法: npx ts-node 02_gen_assets.ts --project /path/to/project
 */

import fs from "fs";
import path from "path";
import { execSync } from "child_process";

// ── CLI 参数 ──────────────────────────────────────────────────
const args = process.argv.slice(2);
const getArg = (flag: string) => { const i = args.indexOf(flag); return i !== -1 ? args[i + 1] : null; };
const projectDir = getArg("--project");
if (!projectDir) { console.error("用法: npx ts-node 02_gen_assets.ts --project <项目目录>"); process.exit(1); }

// ── 读取配置和脚本 ────────────────────────────────────────────
const config = JSON.parse(fs.readFileSync(path.join(projectDir, "config.json"), "utf-8"));
const script = JSON.parse(fs.readFileSync(path.join(projectDir, "script.json"), "utf-8"));
const assetsDir = path.join(projectDir, "assets");
fs.mkdirSync(assetsDir, { recursive: true });

const { openai, volc, video } = config;

// ── 工具函数 ──────────────────────────────────────────────────
function sleep(ms: number) { return new Promise((r) => setTimeout(r, ms)); }

function escapeDrawtext(text: string): string {
  return text.replace(/\\/g, "\\\\").replace(/'/g, "\\'").replace(/:/g, "\\:");
}

function detectFont(): string {
  const candidates = [
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "C:/Windows/Fonts/msyhbd.ttc",
  ];
  if (video.fontPath && fs.existsSync(video.fontPath)) return video.fontPath;
  for (const f of candidates) { if (fs.existsSync(f)) return f; }
  throw new Error("未找到可用中文字体，请在 config.json 中指定 video.fontPath");
}

// ── cover / outro：FFmpeg drawtext 生成 JPG + 静音 MP3 ────────
function genStaticFrame(scene: any): void {
  const font = detectFont();
  const jpgOut = path.join(assetsDir, `${scene.id}.jpg`);
  const silenceOut = path.join(projectDir, `silence_${scene.id}.mp3`);

  const title = escapeDrawtext(scene.title || "");
  const subtitle = escapeDrawtext(scene.subtitle || "");
  const bg = video.coverBgColor || "#1a1a2e";

  const vf = [
    `drawtext=text='${title}':fontfile=${font}:fontcolor=white:fontsize=64:x=(w-tw)/2:y=(h-th)/2-50:shadowcolor=black:shadowx=2:shadowy=2`,
    subtitle ? `drawtext=text='${subtitle}':fontfile=${font}:fontcolor=#aaaaaa:fontsize=32:x=(w-tw)/2:y=(h-th)/2+50` : null,
  ].filter(Boolean).join(",");

  execSync(
    `ffmpeg -y -f lavfi -i "color=c=${bg}:size=1280x720:duration=1" -vf "${vf}" -frames:v 1 "${jpgOut}"`,
    { stdio: "pipe" }
  );

  execSync(
    `ffmpeg -y -f lavfi -i "anullsrc=r=24000:cl=mono" -t ${scene.duration} -c:a libmp3lame -q:a 4 "${silenceOut}"`,
    { stdio: "pipe" }
  );

  console.log(`[Assets] [${scene.type}] ${scene.id} → JPG + 静音MP3 ✓`);
}

// ── GPT-Image-2 生成图像 ──────────────────────────────────────
async function genImage(scene: any, semaphore: Semaphore): Promise<void> {
  await semaphore.acquire();
  try {
    const outPath = path.join(assetsDir, `${scene.id}.jpg`);
    if (fs.existsSync(outPath)) { console.log(`[Assets] [image] ${scene.id} 已存在，跳过`); return; }

    const MAX_RETRY = 3;
    for (let attempt = 1; attempt <= MAX_RETRY; attempt++) {
      try {
        const res = await fetch("https://api.openai.com/v1/images/generations", {
          method: "POST",
          headers: { Authorization: `Bearer ${openai.apiKey}`, "Content-Type": "application/json" },
          body: JSON.stringify({
            model: openai.imageModel || "gpt-image-2",
            prompt: scene.image_prompt,
            n: 1,
            size: openai.imageSize || "1280x720",
            quality: openai.imageQuality || "standard",
            response_format: "b64_json",
          }),
        });
        if (!res.ok) throw new Error(`Image API ${res.status}: ${await res.text()}`);
        const data = await res.json();
        const b64 = data.data?.[0]?.b64_json;
        if (!b64) throw new Error("Image API 返回无 b64_json");
        fs.writeFileSync(outPath, Buffer.from(b64, "base64"));
        console.log(`[Assets] [image] ${scene.id} ✓`);
        return;
      } catch (e: any) {
        if (attempt === MAX_RETRY) throw e;
        console.warn(`[Assets] [image] ${scene.id} 第${attempt}次失败，重试...`);
        await sleep(2000 * attempt);
      }
    }
  } finally {
    semaphore.release();
  }
}

// ── 火山引擎 TTS 生成语音 ─────────────────────────────────────
async function genTTS(scene: any, semaphore: Semaphore): Promise<void> {
  await semaphore.acquire();
  try {
    const outPath = path.join(assetsDir, `${scene.id}.mp3`);
    if (fs.existsSync(outPath)) { console.log(`[Assets] [tts] ${scene.id} 已存在，跳过`); return; }

    const MAX_RETRY = 3;
    for (let attempt = 1; attempt <= MAX_RETRY; attempt++) {
      try {
        const reqId = `${Date.now()}-${scene.id}`;
        const res = await fetch("https://openspeech.bytedance.com/api/v1/tts", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            app: { appid: volc.appId, token: volc.accessToken, cluster: volc.cluster || "volcano_tts" },
            user: { uid: "science-video-skill" },
            audio: {
              voice_type: volc.voiceType || "zh_female_qingxin",
              encoding: "mp3",
              speed_ratio: volc.speedRatio || 1.0,
              volume_ratio: 1.0,
              pitch_ratio: 1.0,
            },
            request: { reqid: reqId, text: scene.narration, text_type: "plain", operation: "query" },
          }),
        });
        if (!res.ok) throw new Error(`TTS API ${res.status}: ${await res.text()}`);
        const data = await res.json();
        if (data.code !== 3000) throw new Error(`TTS 失败 code=${data.code} msg=${data.message}`);
        fs.writeFileSync(outPath, Buffer.from(data.data, "base64"));
        console.log(`[Assets] [tts] ${scene.id} ✓`);
        return;
      } catch (e: any) {
        if (attempt === MAX_RETRY) throw e;
        console.warn(`[Assets] [tts] ${scene.id} 第${attempt}次失败，重试...`);
        await sleep(2000 * attempt);
      }
    }
  } finally {
    semaphore.release();
  }
}

// ── 简单信号量 ────────────────────────────────────────────────
class Semaphore {
  private count: number;
  private queue: Array<() => void> = [];
  constructor(max: number) { this.count = max; }
  acquire(): Promise<void> {
    if (this.count > 0) { this.count--; return Promise.resolve(); }
    return new Promise((r) => this.queue.push(r));
  }
  release(): void {
    const next = this.queue.shift();
    if (next) { next(); } else { this.count++; }
  }
}

// ── 主流程 ────────────────────────────────────────────────────
async function main(): Promise<void> {
  console.log(`[Step 2] 开始生成资产，共 ${script.scenes.length} 个段落`);

  const imageSem = new Semaphore(3);
  const ttsSem = new Semaphore(5);

  const tasks: Promise<void>[] = [];

  for (const scene of script.scenes) {
    if (scene.type === "cover" || scene.type === "outro") {
      // 同步生成（FFmpeg 命令行，很快）
      genStaticFrame(scene);
    } else {
      // 并行：图像 + 语音同时发起
      tasks.push(genImage(scene, imageSem));
      tasks.push(genTTS(scene, ttsSem));
    }
  }

  const results = await Promise.allSettled(tasks);
  const failed = results.filter((r) => r.status === "rejected");
  if (failed.length > 0) {
    failed.forEach((r: any) => console.error("[Assets] 失败:", r.reason?.message));
    process.exit(1);
  }

  console.log("[Step 2] 所有资产生成完成 ✓");
}

main().catch((e) => { console.error(e.message); process.exit(1); });
