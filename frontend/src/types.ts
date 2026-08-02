export type FlowLevel = "light" | "medium" | "heavy";

export interface Period {
  id: number;
  start_date: string;
  end_date: string | null;
  flow: FlowLevel;
  symptoms: string[];
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface PeriodPayload {
  start_date: string;
  end_date: string | null;
  flow: FlowLevel;
  symptoms: string[];
  notes: string;
}

export interface Insights {
  average_cycle_length: number;
  average_period_length: number;
  cycle_variation: number | null;
  next_period_start: string;
  next_period_end: string;
  ovulation_date: string;
  fertile_window_start: string;
  fertile_window_end: string;
  days_until_next_period: number;
  completed_cycles: number;
  confidence: "low" | "medium" | "high";
  is_estimate: boolean;
}

