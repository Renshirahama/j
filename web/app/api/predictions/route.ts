import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import type { PredictionLedgerEntry } from "@/lib/types";

const ledgerPath = path.join(process.cwd(), "data", "prediction-ledger.json");

function readLedger(): PredictionLedgerEntry[] {
  if (!fs.existsSync(ledgerPath)) return [];
  try {
    return JSON.parse(fs.readFileSync(ledgerPath, "utf8")) as PredictionLedgerEntry[];
  } catch {
    return [];
  }
}

function writeLedger(entries: PredictionLedgerEntry[]) {
  fs.mkdirSync(path.dirname(ledgerPath), { recursive: true });
  fs.writeFileSync(ledgerPath, JSON.stringify(entries, null, 2) + "\n", "utf8");
}

export async function GET() {
  return NextResponse.json({ entries: readLedger() });
}

export async function POST(request: Request) {
  const body = (await request.json()) as Partial<PredictionLedgerEntry>;
  const store = String(body.store || "").trim();
  const machineName = String(body.machine_name || "").trim();
  const targetDate = String(body.target_date || "").trim();
  const personalPicks = Array.isArray(body.personal_picks)
    ? body.personal_picks.map((value) => String(value).trim()).filter(Boolean).slice(0, 3)
    : [];
  const note = String(body.note || "").trim().slice(0, 500);
  const systemPicks = Array.isArray(body.system_picks)
    ? body.system_picks.map((value) => String(value).trim()).filter(Boolean).slice(0, 3)
    : [];

  if (!store || !machineName || !targetDate || personalPicks.length === 0 || systemPicks.length === 0) {
    return NextResponse.json({ error: "店舗、機種、対象日、システム候補、自分の候補は必須です。" }, { status: 400 });
  }

  const entries = readLedger();
  const alreadyFixed = entries.find((entry) => entry.store === store && entry.machine_name === machineName && entry.target_date === targetDate);
  if (alreadyFixed) {
    return NextResponse.json({ error: "この店舗・機種・対象日の予想はすでに確定済みです。", entry: alreadyFixed }, { status: 409 });
  }

  const entry: PredictionLedgerEntry = {
    id: `${targetDate}-${Date.now()}`,
    store,
    machine_name: machineName,
    target_date: targetDate,
    system_picks: systemPicks,
    personal_picks: personalPicks,
    note,
    fixed_at: new Date().toISOString(),
  };
  entries.push(entry);
  writeLedger(entries);
  return NextResponse.json({ entry }, { status: 201 });
}
