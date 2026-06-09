#!/usr/bin/env npx ts-node
/**
 * Step 4: FFmpeg 合成最终视频（合并音频 + 生成字幕 + 合成 MP4）
 * 用法: npx ts-node 04_compose_video.ts --project /path/to/project
 */

import fs from "fs";
import path from "path";
import { execSync } from "child_process";

// ── CLI 参数 ──────────────────────────────────────────────────
const args = process.argv.slice(2);
const getArg = (flag: string) => { const i = args.indexOf(flag); return i !== -1 ? args[i + 1] : null; };
const projectDir = getArg("--project");
if (!projectDir) { console.error("用法: npx ts-node 04_compose_video.ts --project <项目目录>"); process.exit(1); }

const config = JSON.parse(fs.readFileSync(path.join(projectDir, "config.json"), "utf-8"));
const script = JSON.parse(fs.readFileSync(path.join(projectDir, "script.json"), "utf-8"));
const durations: Record<string, number> = JSON.parse(
  fs.readFileSync(path.join(projectDir, "durations.json"), "utf-8")
);
const assetsDir = path.join(projectDir, "assets");
const { video } = config;

// ── 工具 ──────────────────────────────────────────────────────
function run(cmd: string, label: string): void {
  console.log(`[${label}] 执行中...`);
  try {
    execSync(cmd, { stdio: "pipe" });
    console.log(`[${label}] ✓`);
  } catch (e: any) {
    console.error(`[${label}] 失败:\n${e.stderr?.toString() || e.message}`);
    process.exit(1);
  }
}

function getAudioPath(scene: any): string {
  if (scene.type === "cover" || scene.type === "outro") {
    return path.join(projectDir, `silence_${scene.id}.mp3`);
  }
  return path.join(assetsDir, `${scene.id}.mp3`);
}

// ── 4a: 合并全部音频 ──────────────────────────────────────────
function mergeAudio(): string {
  const outPath = path.join(projectDir, "merged_audio.mp3");
  const inputs = script.scenes.map((s: any) => `-i "${getAudioPath(s)}"`).join(" \\\n  ");
  const n = script.scenes.length;
  const filterIn = script.scenes.map((_: any, i: number) => `[${i}:a]`).join("");
  const filterComplex = `${filterIn}concat=n=${n}:v=0:a=1[aout]`;

  run(
    `ffmpeg -y \\\n  ${inputs} \\\n  -filter_complex "${filterComplex}" \\\n  -map "[aout]" \\\n  -b:a ${video.audioBitrate || "128k"} \\\n  "${outPath}"`,
    "Step4a 合并音频"
  );
  return outPath;
}

// ── 4b: 生成字幕 SRT ──────────────────────────────────────────
function toSrtTime(seconds: number): string {
  const ms = Math.floor((seconds % 1) * 1000);
  const s = Math.floor(seconds) % 60;
  const m = Math.floor(seconds / 60) % 60;
  const h = Math.floor(seconds / 3600);
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")},${String(ms).padStart(3, "0")}`;
}

function generateSRT(): string {
  const srtPath = path.join(projectDir, "subtitle.srt");
  const lines: string[] = [];
  let cursor = 0;
  let index = 1;

  for (const scene of script.scenes) {
    const dur = durations[scene.id];
    if (scene.type === "cover" || scene.type === "outro") {
      cursor += dur;
      continue;
    }
    const start = toSrtTime(cursor);
    const end = toSrtTime(cursor + dur);
    // 每20字换行
    const text: string = scene.narration || "";
    const wrapped = text.match(/.{1,20}/g)?.join("\n") || text;
    lines.push(`${index}`);
    lines.push(`${start} --> ${end}`);
    lines.push(wrapped);
    lines.push("");
    index++;
    cursor += dur;
  }

  fs.writeFileSync(srtPath, lines.join("\n"), "utf-8");
  console.log(`[Step4b 字幕] ✓ → ${srtPath}`);
  return srtPath;
}

// ── 4c: 合成最终视频 ──────────────────────────────────────────
function composeVideo(mergedAudio: string): string {
  const concatPath = path.join(projectDir, "concat.txt");
  const outPath = path.join(projectDir, "output.mp4");
  const fps = video.fps || 30;
  const vBitrate = video.videoBitrate || "2000k";
  const aBitrate = video.audioBitrate || "128k";

  run(
    `ffmpeg -y \\
  -f concat -safe 0 -i "${concatPath}" \\
  -i "${mergedAudio}" \\
  -c:v libx264 -pix_fmt yuv420p -r ${fps} -b:v ${vBitrate} \\
  -vf "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2" \\
  -c:a aac -b:a ${aBitrate} \\
  -shortest \\
  "${outPath}"`,
    "Step4c 合成视频"
  );
  return outPath;
}

// ── 4d: 烧录字幕（可选）─────────────────────────────────────
function burnSubtitle(videoPath: string, srtPath: string): string {
  const outPath = path.join(projectDir, "output_subtitled.mp4");
  run(
    `ffmpeg -y \\
  -i "${videoPath}" \\
  -vf "subtitles='${srtPath}':force_style='FontSize=22,PrimaryColour=&Hffffff,Outline=1'" \\
  -c:a copy \\
  "${outPath}"`,
    "Step4d 烧录字幕"
  );
  return outPath;
}

// ── 主流程 ────────────────────────────────────────────────────
function main(): void {
  console.log("[Step 4] 开始合成视频");

  const mergedAudio = mergeAudio();

  let srtPath: string | null = null;
  if (video.enableSubtitle !== false) {
    srtPath = generateSRT();
  }

  const outputPath = composeVideo(mergedAudio);

  if (video.burnSubtitle && srtPath) {
    const subtitledPath = burnSubtitle(outputPath, srtPath);
    console.log(`\n[Step 4] 完成 ✓`);
    console.log(`  最终视频（含字幕）: ${subtitledPath}`);
  } else {
    console.log(`\n[Step 4] 完成 ✓`);
    console.log(`  最终视频: ${outputPath}`);
    if (srtPath) console.log(`  字幕文件: ${srtPath}`);
  }

  // 打印总时长
  const total = Object.values(durations).reduce((a: number, b: number) => a + b, 0);
  console.log(`  视频时长: ${total.toFixed(1)}s (${(total / 60).toFixed(1)}min)`);
}

main();
