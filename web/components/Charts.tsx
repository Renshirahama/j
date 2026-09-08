"use client";

import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from "recharts";

export function SmallBarChart({ data, xKey, yKey }: { data: Array<Record<string, number | string>>; xKey: string; yKey: string }) {
  return (
    <div className="h-56 w-full">
      <ResponsiveContainer>
        <BarChart data={data}>
          <CartesianGrid stroke="#d8dee8" />
          <XAxis dataKey={xKey} tick={{ fontSize: 11, fill: "#111827" }} />
          <YAxis tick={{ fontSize: 11, fill: "#111827" }} />
          <Tooltip />
          <Bar dataKey={yKey} fill="#0f766e" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function SmallScatter({ data }: { data: Array<Record<string, number | string>> }) {
  return (
    <div className="h-56 w-full">
      <ResponsiveContainer>
        <ScatterChart>
          <CartesianGrid stroke="#d8dee8" />
          <XAxis dataKey="x" tick={{ fontSize: 11, fill: "#111827" }} />
          <YAxis dataKey="y" tick={{ fontSize: 11, fill: "#111827" }} />
          <Tooltip />
          <Scatter data={data} fill="#f59e0b" />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}

export function SmallLine({ data }: { data: Array<Record<string, number | string>> }) {
  return (
    <div className="h-56 w-full">
      <ResponsiveContainer>
        <LineChart data={data}>
          <CartesianGrid stroke="#d8dee8" />
          <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#111827" }} />
          <YAxis tick={{ fontSize: 11, fill: "#111827" }} />
          <Tooltip />
          <Line type="monotone" dataKey="cumulative" stroke="#0f766e" dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
