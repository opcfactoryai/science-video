/**
 * gen_scenes_xai.mjs — 用 XAI Router API (gpt-image-2) 生成各镜头的图片
 *
 * 用法:
 *   node .claude/skills/video-script-generator/scripts/gen_scenes_xai.mjs \
 *     --project-dir projects/gold-2026-0611
 *
 * 环境变量:
 *   XAI_API_KEY — XAI Router API Key（必填）
 *   XAI_API_URL — API 地址（默认 https://api.xairouter.com/v1/images/generations）
 *
 * 说明:
 *   读取 project-dir/script.json 中每个 scene 的 image_prompt，
 *   逐镜调用 gpt-image-2 生成图片，保存为 {scene-id}.png
 */

import fs from "node:fs";
import path from "node:path";
import { readFile, writeFile, mkdir } from "node:fs/promises";

const API_URL =
  process.env.XAI_API_URL ||
  "https://api.xairouter.com/v1/images/generations";
const API_KEY = process.env.XAI_API_KEY;

if (!API_KEY) {
  console.error("❌ 环境变量 XAI_API_KEY 未设置。请 source .env 后再运行。");
  process.exit(1);
}

function parseArgs() {
  const args = {};
  for (let i = 2; i < process.argv.length; i++) {
    const arg = process.argv[i];
    if (arg.startsWith("--")) {
      const key = arg.slice(2);
      const val = process.argv[i + 1];
      if (val && !val.startsWith("--")) {
        args[key] = val;
        i++;
      } else {
        args[key] = true;
      }
    }
  }
  return args;
}

async function generateImage(prompt, outputPath, retries = 2) {
  const body = {
    model: "gpt-image-2",
    prompt,
    size: "1024x1024",
    quality: "high",
    output_format: "png",
    response_format: "b64_json",
  };

  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const resp = await fetch(API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${API_KEY}`,
        },
        body: JSON.stringify(body),
      });

      if (!resp.ok) {
        const errText = await resp.text().catch(() => "");
        throw new Error(`HTTP ${resp.status}: ${errText.slice(0, 200)}`);
      }

      const data = await resp.json();
      const b64 = data.data?.[0]?.b64_json;
      if (!b64) {
        throw new Error("API 返回中没有 b64_json 字段");
      }

      const imageBuffer = Buffer.from(b64, "base64");
      await writeFile(outputPath, imageBuffer);
      return true;
    } catch (err) {
      if (attempt < retries) {
        console.log(`  ⚠️  重试 ${attempt + 1}/${retries}: ${err.message}`);
        await new Promise((r) => setTimeout(r, 2000));
      } else {
        throw err;
      }
    }
  }
  return false;
}

async function main() {
  const args = parseArgs();
  const projectDir = args["project-dir"] || args["project_dir"];
  if (!projectDir) {
    console.error("❌ 请指定 --project-dir");
    process.exit(1);
  }

  const scriptPath = path.resolve(projectDir, "script.json");
  let script;
  try {
    script = JSON.parse(await readFile(scriptPath, "utf-8"));
  } catch {
    console.error(`❌ 无法读取 script.json: ${scriptPath}`);
    process.exit(1);
  }

  const scenes = script.scenes || [];
  console.log(`🎬 ${script.meta?.title || "未命名"}`);
  console.log(`📁 ${path.resolve(projectDir)}`);
  console.log(`🖼️  共 ${scenes.length} 个镜头需要生成\n`);

  let ok = 0,
    fail = 0;
  for (const scene of scenes) {
    const prompt = scene.image_prompt;
    if (!prompt) {
      console.log(`  [${ok + fail + 1}/${scenes.length}] ⏭️  ${scene.id}: 无提示词`);
      continue;
    }

    const outputPath = path.resolve(projectDir, `${scene.id}.png`);
    process.stdout.write(`  [${ok + fail + 1}/${scenes.length}] 🖼️  ${scene.id} → ${scene.id}.png  `);

    try {
      await generateImage(prompt, outputPath);
      const size = fs.statSync(outputPath).size;
      console.log(`✅ (${(size / 1024).toFixed(0)} KB)`);
      ok++;
    } catch (err) {
      console.log(`❌ ${err.message}`);
      fail++;
    }
  }

  console.log(`\n📊 完成: ${ok} 成功, ${fail} 失败`);
  process.exit(fail > 0 ? 1 : 0);
}

main();
