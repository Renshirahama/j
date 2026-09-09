import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

type Dashboard = {
  store: string;
  machine_name: string;
  target_date: string;
  ranking: Array<{ machine_number: string; score: number; reasons: string[] }>;
  backtest: Record<string, number | string>;
};

const dashboards = [
  { aliases: ["渋谷", "しぶや"], file: "dashboard_shibuya_juggler.json" },
  { aliases: ["溝の口", "みぞのくち", "溝口"], file: "dashboard_mizonokuchi_juggler.json" },
  { aliases: ["キコーナ", "新宿", "新宿三丁目"], file: "dashboard_kicona_shinjuku3_juggler.json" },
];

function readDashboard(file: string): Dashboard | null {
  const target = path.join(process.cwd(), "public", file);
  if (!fs.existsSync(target)) return null;
  return JSON.parse(fs.readFileSync(target, "utf8")) as Dashboard;
}

function answer(question: string): string {
  const selected = dashboards.find((item) => item.aliases.some((alias) => question.includes(alias)));
  if (!selected && question.includes("店")) {
    return dashboards
      .map((item) => readDashboard(item.file))
      .filter((item): item is Dashboard => Boolean(item))
      .sort((a, b) => Number(b.backtest.top3_avg_diff || 0) - Number(a.backtest.top3_avg_diff || 0))
      .map((item, index) => `${index + 1}. ${item.store}：${item.ranking.slice(0, 3).map((row) => `${row.machine_number}番台（${row.score}点）`).join("、")}`)
      .join("\n");
  }
  const data = readDashboard((selected || dashboards[0]).file);
  if (!data) return "まだ分析データがありません。店舗名を指定して聞いてください。";
  const top = data.ranking.slice(0, 3).map((row, index) => `${index + 1}位：${row.machine_number}番台（${row.score}点）\n  ${row.reasons.slice(0, 2).join("／")}`);
  const reliability = data.backtest.predictive_power === "confirmed_vs_random_95" ? "バックテストではランダム95%区間を上回っています。" : "バックテストではランダムより明確に良いとは未確認です。";
  return `${data.target_date}の${data.store}・${data.machine_name}の候補です。\n\n${top.join("\n")}\n\n${reliability}\n※過去データによる相対評価で、当日の結果を保証するものではありません。`;
}

export async function POST(request: Request) {
  const body = (await request.json()) as { question?: string };
  const question = String(body.question || "").trim();
  if (!question) return NextResponse.json({ answer: "店舗名を入れて質問してください。例：今日、渋谷のジャグラーどう？" }, { status: 400 });
  return NextResponse.json({ answer: answer(question) });
}
