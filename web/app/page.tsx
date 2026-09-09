import fs from "fs";
import path from "path";
import { SmallBarChart, SmallLine, SmallScatter } from "@/components/Charts";
import { Metric } from "@/components/Metric";
import { AnalysisChat } from "@/components/AnalysisChat";
import type { DashboardPayload } from "@/lib/types";

const DASHBOARDS = [
  { id: "shibuya", label: "渋谷", sub: "駅前新館", file: "dashboard_shibuya_juggler.json" },
  { id: "mizonokuchi", label: "溝の口", sub: "駅前新館", file: "dashboard_mizonokuchi_juggler.json" },
  { id: "kicona_shinjuku3", label: "キコーナ", sub: "新宿三丁目", file: "dashboard_kicona_shinjuku3_juggler.json" }
];

function loadData(file: string): DashboardPayload | null {
  const p = path.join(process.cwd(), "public", file);
  if (!fs.existsSync(p)) return null;
  return JSON.parse(fs.readFileSync(p, "utf-8"));
}

function fmtMedals(v: unknown) {
  const n = Number(v || 0);
  return `${n >= 0 ? "+" : ""}${Math.round(n).toLocaleString()}枚`;
}

function pct(v: unknown) {
  return `${Math.round(Number(v || 0) * 100)}%`;
}

export default async function Home({ searchParams }: { searchParams?: Promise<{ dashboard?: string }> }) {
  const params = await searchParams;
  const selected = DASHBOARDS.find((item) => item.id === params?.dashboard) || DASHBOARDS[0];
  const data = loadData(selected.file);
  if (!data) {
    return (
      <main className="min-h-screen bg-[#f7f8fb] px-4 py-8 text-[#111827]">
        <h1 className="text-2xl font-bold tracking-normal">ジャグラー狙い台分析</h1>
        <p className="mt-4 text-sm text-gray-700">`python -m juggler_analysis.cli export-dashboard`で分析JSONを生成してください。</p>
      </main>
    );
  }
  const top3 = data.ranking.slice(0, 3);
  const hasPower = data.backtest.predictive_power === "confirmed_vs_random_95";
  return (
    <main className="min-h-screen bg-[#f7f8fb] text-[#111827] md:flex">
      <aside className="sticky top-0 z-10 border-b border-[#d8dee8] bg-white px-3 py-3 md:flex md:h-screen md:w-60 md:flex-col md:border-b-0 md:border-r">
        <a href="/" className="block shrink-0 rounded-md border border-[#d8dee8] bg-[#f7f8fb] px-3 py-2 text-center text-base font-black text-[#111827]">
          ジャグラー確率予測機
        </a>
        <div className="my-3 h-px w-full shrink-0 bg-[#d8dee8]" />
        <div className="mb-2 text-xs font-semibold text-gray-500">店舗切替</div>
        <div className="mt-3 flex gap-2 overflow-x-auto md:mt-0 md:flex-col">
          {DASHBOARDS.map((item) => (
            <a
              key={item.id}
              href={`/?dashboard=${item.id}`}
              title={`${item.label}${item.sub}`}
              className={`block min-w-28 shrink-0 rounded-md px-3 py-2 text-sm font-bold transition md:w-full ${
                item.id === selected.id ? "bg-[#dbeafe] text-[#111827]" : "bg-[#f7f8fb] text-[#111827] hover:bg-[#eef2f7]"
              }`}
            >
              <span className="block">{item.label}</span>
              <span className="block text-xs font-normal text-gray-500">{item.sub}</span>
            </a>
          ))}
        </div>
      </aside>

      <div className="min-w-0 flex-1 bg-[#f7f8fb]">
      <header className="sticky top-[130px] z-10 border-b border-[#d8dee8] bg-white/95 px-4 py-4 backdrop-blur md:top-0">
        <div className="text-xs text-gray-600">{data.store}</div>
        <div className="mt-1 flex flex-wrap items-end justify-between gap-2">
          <h1 className="text-xl font-bold tracking-normal">{data.machine_name}</h1>
          <div className="text-sm text-gray-700">翌日候補 {data.target_date}</div>
        </div>
      </header>

      <section className="px-4 py-5">
        <AnalysisChat />
      </section>

      <section className="px-4 py-5">
        <h2 className="text-base font-semibold tracking-normal text-[#111827]">明日の候補</h2>
        <div className="mt-3 grid grid-cols-3 gap-2">
          {top3.map((row, idx) => (
            <div key={`${row.machine_name}-${row.machine_number}`} className="rounded-md border border-[#d8dee8] bg-white p-3">
              <div className="text-sm text-gray-500">{idx + 1}</div>
              <div className="mt-1 text-2xl font-bold tracking-normal">{row.machine_number}</div>
              {row.machine_name ? <div className="mt-1 truncate text-xs text-gray-500">{row.machine_name}</div> : null}
              <div className="mt-1 text-lg font-semibold text-[#0f766e]">{Math.round(row.score)}点</div>
            </div>
          ))}
        </div>
        <div className={`mt-4 rounded-md border px-3 py-2 text-sm ${hasPower ? "border-[#0f766e] text-[#34d399]" : "border-[#b45309] text-[#fbbf24]"}`}>
          {hasPower ? "バックテスト上、ランダム95%区間を上回っています。" : "現時点ではランダムより明確に良いとは判定していません。"}
        </div>
      </section>

      <section className="grid grid-cols-2 border-y border-[#d8dee8] md:grid-cols-4">
        <Metric label="TOP3平均差枚" value={fmtMedals(data.backtest.top3_avg_diff)} />
        <Metric label="ランダムTOP3平均" value={fmtMedals(data.random.random_avg)} sub={`95% ${fmtMedals(data.random.random_95_lo)}〜${fmtMedals(data.random.random_95_hi)}`} />
        <Metric label="TOP3プラス率" value={pct(data.backtest.top3_plus_rate)} />
        <Metric label="採用スコア" value={String(data.backtest.score_profile || "balanced")} sub={`${data.backtest.past30_wins || 0}勝 / ${data.backtest.past30_losses || 0}敗`} />
      </section>

      <section className="px-4 py-5">
        <h2 className="text-base font-semibold tracking-normal">スコア別比較</h2>
        <div className="mt-3 overflow-x-auto rounded-md border border-[#d8dee8] bg-white">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="bg-gray-100 text-xs text-gray-600">
              <tr><th className="p-2">スコア</th><th className="p-2">TOP3</th><th className="p-2">ランダム</th><th className="p-2">差分</th><th className="p-2">勝率</th><th className="p-2">判定</th></tr>
            </thead>
            <tbody>
              {(data.scorer_comparison || []).map((s) => (
                <tr key={String(s.score_profile)} className="border-t border-[#d8dee8]">
                  <td className="p-2 font-semibold">{s.score_profile}</td>
                  <td className="p-2">{fmtMedals(s.top3_avg_diff)}</td>
                  <td className="p-2">{fmtMedals(s.random_random_avg)}</td>
                  <td className="p-2">{fmtMedals(s.top3_vs_random_delta)}</td>
                  <td className="p-2">{pct(s.top3_plus_rate)}</td>
                  <td className="p-2">{s.predictive_power}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="px-4 py-5">
        <h2 className="text-base font-semibold tracking-normal">機種別比較</h2>
        <div className="mt-3 overflow-x-auto rounded-md border border-[#d8dee8] bg-white">
          <table className="w-full min-w-[820px] text-left text-sm">
            <thead className="bg-gray-100 text-xs text-gray-600">
              <tr><th className="p-2">機種</th><th className="p-2">日数</th><th className="p-2">台数</th><th className="p-2">採用スコア</th><th className="p-2">TOP3</th><th className="p-2">ランダム</th><th className="p-2">差分</th><th className="p-2">勝率</th></tr>
            </thead>
            <tbody>
              {(data.machine_comparison || []).map((m) => (
                <tr key={String(m.machine_name)} className="border-t border-[#d8dee8]">
                  <td className="p-2 font-semibold">{m.machine_name}</td>
                  <td className="p-2">{m.days}</td>
                  <td className="p-2">{m.machines}</td>
                  <td className="p-2">{m.best_profile}</td>
                  <td className="p-2">{fmtMedals(m.top3_avg_diff)}</td>
                  <td className="p-2">{fmtMedals(m.random_avg)}</td>
                  <td className="p-2">{fmtMedals(m.top3_vs_random_delta)}</td>
                  <td className="p-2">{pct(m.top3_plus_rate)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="px-4 py-5">
        <h2 className="text-base font-semibold tracking-normal">全台ランキング</h2>
        <div className="mt-3 divide-y divide-[#d8dee8] rounded-md border border-[#d8dee8] bg-white">
          {data.ranking.map((row, idx) => (
            <article key={`${row.machine_name}-${row.machine_number}`} className="p-3">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <span className="text-sm text-gray-500">{idx + 1}位</span>
                  <span className="ml-3 text-xl font-semibold tracking-normal">{row.machine_number}番台</span>
                </div>
                <div className="text-lg font-bold text-[#0f766e]">{row.score}点</div>
              </div>
              {row.machine_name ? <div className="mt-1 text-xs text-gray-500">{row.machine_name}</div> : null}
              <ul className="mt-2 space-y-1 text-sm text-gray-700">
                {row.reasons.map((reason) => (
                  <li key={reason}>・{reason}</li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </section>

      <section className="space-y-6 px-4 py-5">
        <h2 className="text-base font-semibold tracking-normal">可視化</h2>
        <Panel title="台番号別平均差枚"><SmallBarChart data={data.charts.by_machine_avg_diff} xKey="machine_number" yKey="avg_diff" /></Panel>
        <Panel title="曜日別平均差枚"><SmallBarChart data={data.charts.by_weekday_avg_diff} xKey="weekday" yKey="avg_diff" /></Panel>
        <Panel title="特定日別平均差枚"><SmallBarChart data={data.charts.by_special_day_avg_diff} xKey="name" yKey="avg_diff" /></Panel>
        <Panel title="前日差枚 vs 翌日差枚"><SmallScatter data={data.charts.prev_vs_next_diff} /></Panel>
        <Panel title="予測スコア vs 実差枚"><SmallScatter data={data.charts.score_vs_actual_diff} /></Panel>
        <Panel title="TOP3累積差枚"><SmallLine data={data.charts.top3_cumulative_diff} /></Panel>
      </section>

      <section className="px-4 py-5">
        <h2 className="text-base font-semibold tracking-normal">仮説検証</h2>
        <div className="mt-3 overflow-x-auto rounded-md border border-[#d8dee8] bg-white">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="bg-gray-100 text-xs text-gray-600">
              <tr><th className="p-2">仮説</th><th className="p-2">件数</th><th className="p-2">平均差枚</th><th className="p-2">勝率</th><th className="p-2">REG</th><th className="p-2">判定</th></tr>
            </thead>
            <tbody>
              {data.hypotheses.map((h) => (
                <tr key={String(h.hypothesis)} className="border-t border-[#d8dee8]">
                  <td className="p-2">{h.hypothesis}</td>
                  <td className="p-2">{h.sample_size}</td>
                  <td className="p-2">{fmtMedals(h.avg_diff)}</td>
                  <td className="p-2">{pct(h.win_rate)}</td>
                  <td className="p-2">{Math.round(Number(h.avg_reg_probability || 0))}</td>
                  <td className="p-2">{h.judgement}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
        </div>
    </main>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-md border border-[#d8dee8] bg-white p-3">
      <h3 className="mb-3 text-sm font-semibold tracking-normal">{title}</h3>
      {children}
    </section>
  );
}
