export interface SummaryData {
    answer_count: Record<string, number>;
    project: {
      id: string;
      name: string;
      results_summary: string;
    } | null;
    gate_url: string | null;
  }