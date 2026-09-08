export function Metric({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="border-b border-[#d8dee8] bg-white px-4 py-3">
      <div className="text-xs text-gray-500">{label}</div>
      <div className="mt-1 text-xl font-semibold tracking-normal text-[#111827]">{value}</div>
      {sub ? <div className="mt-1 text-xs text-gray-500">{sub}</div> : null}
    </div>
  );
}
