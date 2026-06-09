#!/usr/bin/env npx ts-node
/**
 * 主入口：一键运行完整视频生成流程
 * 用法: npx ts-node run.ts --topic "光合作用" [--projects-dir ~/projects]
 */

import fs from "fs";
import path from "path";
import { execSync } from "child_process";

// ── CLI 参数 ──────────────────────────────────────────────────
const args = process.argv.slice(2);
const getArg = (flag: string) => { const i = args.indexOf(flag); return i !== -1 ? args[i + 1] : null; };

const topic = getArg("--topic");
const projectsDir = getArg("--projects-dir") || path.join(process.env.HOME || "~", "projects");

if (!topic) {
  console.error("用法: npx ts-node run.ts --topic <主题> [--projects-dir <目录>]");
  console.error("示例: npx ts-node run.ts --topic '光合作用原理'");
  process.exit(1);
}

// ── 创建工作目录 ──────────────────────────────────────────────
const timestamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
const slug = topic.replace(/\s+/g, "-").slice(0, 20);
const projectDir = path.join(projectsDir, `${slug}-video-${timestamp}`);
fs.mkdirSync(projectDir, { recursive: true });
console.log(`\n📁 工作目录: ${projectDir}\n`);

// ── 初始化 config.json（读取环境变量或提示用户填写）───────────
const configPath = path.join(projectDir, "config.json");
const defaultConfig = {
  deepseek: {
    apiKey: process.env.DEEPSEEK_API_KEY || "请填写",
    baseUrl: "https://api.deepseek.com",
    model: "deepseek-chat",
  },
  openai: {
    apiKey: process.env.OPENAI_API_KEY || "请填写",
    imageModel: "gpt-image-2",
    imageSize: "1280x720",
    imageQuality: "standard",
  },
  volc: {
    appId: process.env.VOLC_APP_ID || "请填写",
    accessToken: process.env.VOLC_ACCESS_TOKEN || "请填写",
    cluster: "volcano_tts",
    voiceType: "zh_female_qingxin",
    speedRatio: 1.0,
  },
  video: {
    fps: 30,
    audioBitrate: "128k",
    videoBitrate: "2000k",
    coverDuration: 4,
    outroDuration: 4,
    coverBgColor: "#1a1a2e",
    fontPath: "",
    enableSubtitle: true,
    burnSubtitle: false,
  },
};

fs.writeFileSync(configPath, JSON.stringify(defaultConfig, null, 2));

// 检查关键 API Key 是否已填写
const missingKeys: string[] = [];
if (defaultConfig.deepseek.apiKey === "请填写") missingKeys.push("DEEPSEEK_API_KEY");
if (defaultConfig.openai.apiKey === "请填写") missingKeys.push("OPENAI_API_KEY");
if (defaultConfig.volc.appId === "请填写") missingKeys.push("VOLC_APP_ID");
if (defaultConfig.volc.accessToken === "请填写") missingKeys.push("VOLC_ACCESS_TOKEN");

if (missingKeys.length > 0) {
  console.error("❌ 缺少以下环境变量，请设置后重新运行：");
  missingKeys.forEach((k) => console.error(`   export ${k}=your_key`));
  console.error(`\n或直接编辑: ${configPath}`);
  process.exit(1);
}

// ── 按步骤执行 ────────────────────────────────────────────────
const skillDir = __dirname;

function runStep(script: string, extraArgs: string, label: string): void {
  const cmd = `npx ts-node "${path.join(skillDir, "scripts", script)}" --project "${projectDir}" ${extraArgs}`;
  console.log(`\n${"─".repeat(50)}`);
  console.log(`🚀 ${label}`);
  console.log(`${"─".repeat(50)}`);
  try {
    execSync(cmd, { stdio: "inherit" });
  } catch {
    console.error(`\n❌ ${label} 失败，流程终止`);
    process.exit(1);
  }
}

runStep("01_gen_script.ts", `--topic "${topic}"`, "Step 1: 生成脚本");
runStep("02_gen_assets.ts", "", "Step 2: 生成资产");
runStep("03_gen_concat.ts", "", "Step 3: 提取时长 + concat.txt");
runStep("04_compose_video.ts", "", "Step 4: 合成视频");

console.log(`\n${"═".repeat(50)}`);
console.log(`✅ 视频生成完成！`);
console.log(`   输出: ${path.join(projectDir, "output.mp4")}`);
console.log(`${"═".repeat(50)}\n`);
