export type TxType = "income" | "expense";

export interface Transaction {
  id: string;
  date: string;
  type: TxType;
  category: string;
  description: string;
  amount: number;
  card_id: string | null;
  user: string | null;
  created_at: string;
}

export interface TransactionList {
  items: Transaction[];
  total: number;
}

export interface Card {
  id: string;
  name: string;
  type: "credit" | "debit";
  card_limit: number | null;
  closing_day: number | null;
  due_day: number | null;
  active: boolean;
  owner: string | null;
  created_at: string;
}

export interface Subscription {
  id: string;
  name: string;
  amount: number;
  frequency: "monthly" | "annual";
  next_date: string;
  active: boolean;
  created_at: string;
}

export interface Goal {
  id: string;
  name: string;
  target_amount: number;
  current_amount: number;
  deadline: string | null;
  completed: boolean;
  created_at: string;
}

export interface ForecastResponse {
  month: string;
  projected_income: number;
  projected_expenses: number;
  projected_balance: number;
  subscriptions_total: number;
  historical_avg_income: number;
  historical_avg_expenses: number;
  pace_factor: number;
  days_elapsed: number;
  days_in_month: number;
}

export interface AnalyticsSummary {
  period: string;
  total_income: number;
  total_expenses: number;
  balance: number;
  by_category: Record<string, number>;
  top_category: string | null;
}

export interface MonthlyTrend {
  month: string;
  income: number;
  expenses: number;
  balance: number;
}

export interface AnalyticsResponse {
  summary: AnalyticsSummary;
  monthly_trend: MonthlyTrend[];
}

export interface Settings {
  base_balance: number;
  scheduler_timezone: string;
  active_categories: string[];
  establishments: Record<string, string[]>;
  detail_markets: string[];
  default_pix_card: string;
  additional_system_prompt: string;
}
