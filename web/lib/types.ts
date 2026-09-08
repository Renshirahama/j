export type RankingRow = {
  machine_name?: string;
  machine_number: string;
  score: number;
  reasons: string[];
  past_7d_avg_diff?: number | null;
  past_7d_reg_probability?: number | null;
  prev_difference_medals?: number | null;
};

export type DashboardPayload = {
  store: string;
  machine_name: string;
  latest_date: string;
  target_date: string;
  ranking: RankingRow[];
  backtest: Record<string, number | string>;
  random: Record<string, number>;
  scorer_comparison?: Array<Record<string, number | string>>;
  machine_comparison?: Array<Record<string, number | string>>;
  hypotheses: Array<Record<string, number | string>>;
  charts: Record<string, Array<Record<string, number | string>>>;
};
