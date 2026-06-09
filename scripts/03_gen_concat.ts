#!/usr/bin/env npx ts-node
/**
 * Step 3: ffprobe 提取所有音频时长，生成 concat.txt
 * 用法: npx ts-node 03_gen_concat.ts --project /path/to/project
 */

import fs from "fs";
import path from "path";
import { execSync } from "child_process";

// ── CLI 参数 ──────────────────────────────────────────────────
const args = process.argv.slice(2);
const getArg = (flag: string) => { const i = args.indexOf(flag); return i !== -1 ? args[i + 1] : null; };
const projectDir = getArg("--project");
if (!projectDir) { console.error("用法: npx ts-node 03_gen_concat.ts --project <项目目录>"); process.exit(1); }

const script = JSON.parse(fs.readFileSync(path.join(projectDir, "script.json"), "utf-8"));
const assetsDir = path.join(projectDir, "assets");

// ── ffprobe 提取时长 ──────────────────────────────────────────
function getDuration(audioPath: string): number {
  try {
    const out = execSync(
      `ffprobe -v quiet -print_format json -show_streams "${audioPath}"`,
      { encoding: "utf-8" }
    );
    const json = JSON.parse(out);
    const stream = json.streams?.find((s: any) => s.codec_type === "audio");
    if (stream?.duration) return parseFloat(stream.duration);
  } catch (_) {}

  // 备选：读取 format 层
  try {
    const out = execSync(
      `ffprobe -v quiet -print_format json -show_format "${audioPath}"`,
      { encoding: "utf-8" }
    );
    const json = JSON.parse(out);
    if (json.format?.duration) return parseFloat(json.format.duration);
  } catch (_) {}

  throw new Error(`无法提取时长: ${audioPath}`);
}

function getAudioPath(scene: any): string {
  if (scene.type === "cover" || scene.type === "outro") {
    return path.join(projectDir, `silence_${scene.id}.mp3`);
  }
  return path.join(assetsDir, `${scene.id}.mp3`);
}

// ── 生成 concat.txt ───────────────────────────────────────────
function main(): void {
  console.log("[Step 3] 提取音频时长 + 生成 concat.txt");

  const durations: Record<string, number> = {};

  for (const scene of script.scenes) {
    const audioPath = getAudioPath(scene);
    if (!fs.existsSync(audioPath)) {
      console.error(`音频文件不存在: ${audioPath}`);
      process.exit(1);
    }
    const dur = getDuration(audioPath);
    durations[scene.id] = dur;
    console.log(`  [${scene.type}] ${scene.id}: ${dur.toFixed(3)}s`);
  }

  // 写入 durations.json（供 Step4 使用）
  fs.writeFileSync(
    path.join(projectDir, "durations.json"),
    JSON.stringify(durations, null, 2)
  );

  // 生成 concat.txt
  const lines: string[] = [];
  for (const scene of script.scenes) {
    const jpgPath = path.join(assetsDir, `${scene.id}.jpg`);
    const dur = durations[scene.id];
    lines.push(`file '${jpgPath}'`);
    lines.push(`duration ${dur.toFixed(6)}`);
    lines.push("");
  }
  // FFmpeg concat demuxer 要求：最后一帧重复（无 duration）
  const lastScene = script.scenes[script.scenes.length - 1];
  lines.push(`file '${path.join(assetsDir, `${lastScene.id}.jpg`)}'`);

  const concatPath = path.join(projectDir, "concat.txt");
  fs.writeFileSync(concatPath, lines.join("\n"), "utf-8");

  const total = Object.values(durations).reduce((a, b) => a + b, 0);
  console.log(`[Step 3] 完成 ✓ 视频总时长: ${total.toFixed(1)}s (${(total / 60).toFixed(1)}min) → ${concatPath}`);
}

main();
