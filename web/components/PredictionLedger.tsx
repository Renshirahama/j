"use client";

import { useEffect, useState } from "react";
import type { PredictionLedgerEntry, RankingRow } from "@/lib/types";

export function PredictionLedger({
  store,
  machineName,
  targetDate,
  ranking,
}: {
  store: string;
  machineName: string;
  targetDate: string;
  ranking: RankingRow[];
}) {
  const systemPicks = ranking.slice(0, 3).map((row) => row.machine_number);
  const [personalPicks, setPersonalPicks] = useState("");
  const [note, setNote] = useState("");
  const [entry, setEntry] = useState<PredictionLedgerEntry | null>(null);
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetch("/api/predictions")
      .then((response) => response.json())
      .then((payload: { entries?: PredictionLedgerEntry[] }) => {
        const found = payload.entries?.find((item) => item.store === store && item.machine_name === machineName && item.target_date === targetDate);
        if (found) setEntry(found);
      })
      .catch(() => setMessage("既存の予想台帳を読み込めませんでした。"));
  }, [machineName, store, targetDate]);

  async function savePrediction() {
    const picks = personalPicks.split(/[、,\s]+/).map((value) => value.trim()).filter(Boolean).slice(0, 3);
    if (picks.length === 0) {
      setMessage("自分の候補台を1台以上入力してください。");
      return;
    }
    setSaving(true);
    setMessage("");
    const response = await fetch("/api/predictions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ store, machine_name: machineName, target_date: targetDate, system_picks: systemPicks, personal_picks: picks, note }),
    });
    const payload = await response.json();
    setSaving(false);
    if (!response.ok) {
      setMessage(payload.error || "保存できませんでした。");
      return;
    }
    setEntry(payload.entry);
    setMessage("予想を確定しました。結果を見る前の記録として保存されています。");
  }

  return (
    <section className="rounded-md border border-[#93c5fd] bg-[#eff6ff] px-3 py-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-base font-semibold">予想台帳</h2>
        <span className="text-xs text-gray-600">結果を見る前に確定してください</span>
      </div>
      <div className="mt-3 grid gap-3 text-sm md:grid-cols-2">
        <div className="rounded border border-[#bfdbfe] bg-white p-3">
          <div className="text-xs text-gray-500">システム候補（自動記録）</div>
          <div className="mt-1 font-semibold">{systemPicks.join(" / ")} 番台</div>
        </div>
        <div className="rounded border border-[#bfdbfe] bg-white p-3">
          <label className="text-xs text-gray-500" htmlFor="personal-picks">自分の候補（最大3台）</label>
          <input
            id="personal-picks"
            disabled={Boolean(entry)}
            value={entry ? entry.personal_picks.join(", ") : personalPicks}
            onChange={(event) => setPersonalPicks(event.target.value)}
            placeholder="例：2181, 2184, 2190"
            className="mt-1 w-full rounded border border-[#cbd5e1] px-2 py-1.5 outline-none focus:border-[#2563eb] disabled:bg-gray-100"
          />
        </div>
      </div>
      <label className="mt-3 block text-sm" htmlFor="prediction-note">
        <span className="text-xs text-gray-500">選定理由（任意）</span>
        <textarea
          id="prediction-note"
          disabled={Boolean(entry)}
          value={entry ? entry.note : note}
          onChange={(event) => setNote(event.target.value)}
          placeholder="例：末尾傾向と前日の稼働を重視"
          rows={2}
          className="mt-1 w-full rounded border border-[#cbd5e1] px-2 py-1.5 outline-none focus:border-[#2563eb] disabled:bg-gray-100"
        />
      </label>
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <button
          type="button"
          disabled={Boolean(entry) || saving}
          onClick={savePrediction}
          className="rounded bg-[#1d4ed8] px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-gray-400"
        >
          {entry ? "確定済み" : saving ? "保存中…" : "予想を確定する"}
        </button>
        {entry ? <span className="text-xs text-gray-600">確定日時：{new Date(entry.fixed_at).toLocaleString("ja-JP")}</span> : null}
        {message ? <span className="text-xs text-gray-700">{message}</span> : null}
      </div>
    </section>
  );
}
