"use client";

import { FormEvent, useState } from "react";

export function AnalysisChat() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("今日、どの店舗のジャグラーを見ますか？");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!question.trim() || loading) return;
    setLoading(true);
    try {
      const response = await fetch("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question }) });
      const data = (await response.json()) as { answer: string };
      setAnswer(data.answer);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="rounded-md border border-[#d8dee8] bg-white p-4">
      <h2 className="text-base font-semibold">分析チャット</h2>
      <p className="mt-1 text-xs text-gray-500">例：今日、渋谷のジャグラーどう？／今日おすすめの店は？</p>
      <form className="mt-3 flex gap-2" onSubmit={submit}>
        <input className="min-w-0 flex-1 rounded-md border border-[#cbd5e1] px-3 py-2 text-sm outline-none focus:border-[#0f766e]" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="聞きたいことを入力" />
        <button className="rounded-md bg-[#0f766e] px-4 py-2 text-sm font-bold text-white disabled:opacity-50" disabled={loading}>{loading ? "分析中" : "聞く"}</button>
      </form>
      <div className="mt-4 whitespace-pre-wrap rounded-md bg-[#f7f8fb] p-3 text-sm leading-6 text-gray-700">{answer}</div>
    </section>
  );
}
