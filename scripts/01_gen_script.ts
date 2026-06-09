#!/usr/bin/env npx ts-node
/**
 * Step 1: 调用 DeepSeek 生成分镜脚本
 * 用法: npx ts-node 01_gen_script.ts --topic "光合作用" --project /path/to/project
 */

import fs from "fs";
import path from "path";

// ── CLI 参数解析 ─────────────────────────────────────────────
const args = process.argv.slice(2);
const getArg = (flag: string) => {
  const i = args.indexOf(flag);
  return i !== -1 ? args[i + 1] : null;
};

const topic = getArg("--topic");
const projectDir = getArg("--project");

if (!topic || !projectDir) {
  console.error("用法: npx ts-node 01_gen_script.ts --topic <主题> --project <项目目录>");
  process.exit(1);
}

// ── 读取配置 ─────────────────────────────────────────────────
const configPath = path.join(projectDir, "config.json");
if (!fs.existsSync(configPath)) {
  console.error(`未找到配置文件: ${configPath}`);
  process.exit(1);
}
const config = JSON.parse(fs.readFileSync(configPath, "utf-8"));
const { apiKey, baseUrl, model } = config.deepseek;

// ── 读取 Prompt 模板 ──────────────────────────────────────────
const skillDir = path.join(__dirname, "..");
const promptPath = path.join(skillDir, "prompts", "script.md");
const promptRaw = fs.readFileSync(promptPath, "utf-8");

// 从 script.md 中提取 System Prompt（```代码块内容）
const systemMatch = promptRaw.match(/## System Prompt\s+```\n([\s\S]+?)```/);
const userMatch = promptRaw.match(/## User Prompt 模板\s+```\n([\s\S]+?)```/);

if (!systemMatch || !userMatch) {
  console.error("prompts/script.md 格式异常，无法提取 System/User Prompt");
  process.exit(1);
}

const systemPrompt = systemMatch[1].trim();
const userPrompt = userMatch[1].trim().replace("{topic}", topic);

// ── 调用 DeepSeek ─────────────────────────────────────────────
async function genScript(): Promise<void> {
  console.log(`[Step 1] 调用 DeepSeek 生成脚本，主题: ${topic}`);

  const MAX_RETRY = 3;
  let lastError: Error | null = null;

  for (let attempt = 1; attempt <= MAX_RETRY; attempt++) {
    try {
      const res = await fetch(`${baseUrl}/v1/chat/completions`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${apiKey}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          model,
          messages: [
            { role: "system", content: systemPrompt },
            { role: "user", content: userPrompt },
          ],
          temperature: 0.7,
          response_format: { type: "json_object" },
        }),
      });

      if (!res.ok) {
        throw new Error(`DeepSeek API 错误: ${res.status} ${await res.text()}`);
      }

      const data = await res.json();
      const content = data.choices?.[0]?.message?.content;
      if (!content) throw new Error("DeepSeek 返回内容为空");

      const script = JSON.parse(content);

      // 基本结构校验
      if (!Array.isArray(script.scenes) || script.scenes.length === 0) {
        throw new Error("script.json 结构异常：scenes 为空或不是数组");
      }

      const types = script.scenes.map((s: any) => s.type);
      if (!types.includes("cover")) throw new Error("缺少 cover 段落");
      if (!types.includes("hook")) throw new Error("缺少 hook 段落");
      if (!types.includes("summary")) throw new Error("缺少 summary 段落");
      if (!types.includes("outro")) throw new Error("缺少 outro 段落");

      // 写入 script.json
      fs.mkdirSync(projectDir, { recursive: true });
      const outPath = path.join(projectDir, "script.json");
      fs.writeFileSync(outPath, JSON.stringify(script, null, 2), "utf-8");

      console.log(`[Step 1] 完成 ✓ 共 ${script.scenes.length} 个段落 → ${outPath}`);
      script.scenes.forEach((s: any) =>
        console.log(`         [${s.type}] ${s.id}: ${s.title}`)
      );
      return;

    } catch (err: any) {
      lastError = err;
      console.warn(`[Step 1] 第 ${attempt} 次尝试失败: ${err.message}`);
      if (attempt < MAX_RETRY) await sleep(2000 * attempt);
    }
  }

  console.error(`[Step 1] 失败，已重试 ${MAX_RETRY} 次`);
  throw lastError;
}

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

genScript().catch((e) => {
  console.error(e.message);
  process.exit(1);
});
