export const BENCHMARK_KPI = {
  scenariosTested: 10000,
  scenariosDelta: 2000,
  safetyAccuracy: 97.8,
  safetyDelta: 3.1,
  falsePositives: 1.9,
  falsePositivesDelta: -28.4,
  financialExposure: 2.84, // in Lakhs
  exposureDelta: -71.2
};

export const COMPARISON_METRICS = [
  { metric: "Unsafe actions blocked", finshield: "98.2%", ruleEngine: "91.4%", llmJudge: "86.7%", best: "finshield" },
  { metric: "False positives", finshield: "2.1%", ruleEngine: "6.8%", llmJudge: "9.4%", best: "finshield" },
  { metric: "False negatives", finshield: "1.8%", ruleEngine: "8.6%", llmJudge: "13.3%", best: "finshield" },
  { metric: "Avg decision time", finshield: "184ms", ruleEngine: "42ms", llmJudge: "731ms", best: "ruleEngine" },
  { metric: "Intent detection", finshield: "96.4%", ruleEngine: "71.2%", llmJudge: "89.3%", best: "finshield" },
  { metric: "Financial exposure", finshield: "₹2.84L", ruleEngine: "₹9.71L", llmJudge: "₹18.4L", best: "finshield" }
];

export const SCENARIO_BREAKDOWN = [
  { name: "Normal purchase", finshield: 99.4, ruleEngine: 98.9, llmJudge: 97.2 },
  { name: "Intent divergence", finshield: 96.8, ruleEngine: 74.1, llmJudge: 88.6 },
  { name: "Merchant manipulation", finshield: 98.1, ruleEngine: 83.7, llmJudge: 91.4 },
  { name: "Tool abuse", finshield: 99.2, ruleEngine: 94.8, llmJudge: 86.3 },
  { name: "Financial manipulation", finshield: 97.4, ruleEngine: 81.2, llmJudge: 84.9 },
  { name: "Prompt injection", finshield: 96.9, ruleEngine: 79.4, llmJudge: 90.1 }
];

export const ERROR_ANALYSIS = {
  falseNegatives: {
    total: 8,
    breakdown: [
      { cause: "Cross-agent intent transfer", count: 4, width: "50%" },
      { cause: "Merchant identity ambiguity", count: 2, width: "25%" },
      { cause: "Multi-step tool escalation", count: 1, width: "12.5%" },
      { cause: "Context truncation", count: 1, width: "12.5%" }
    ]
  },
  falsePositives: {
    total: 21,
    breakdown: [
      { cause: "High-value legitimate purchases", count: 9, width: "42%" },
      { cause: "New merchant", count: 6, width: "28%" },
      { cause: "Travel booking anomaly", count: 3, width: "14%" },
      { cause: "Unusual transaction velocity", count: 3, width: "14%" }
    ]
  }
};

export const VERSION_EVOLUTION = [
  { version: "v1.6", safety: 89.4, falsePositives: 6.8, latency: 261, exposure: 21.2 },
  { version: "v1.7", safety: 91.7, falsePositives: 5.1, latency: 238, exposure: 15.4 },
  { version: "v1.8", safety: 94.6, falsePositives: 3.7, latency: 207, exposure: 8.7 },
  { version: "v1.9", safety: 97.8, falsePositives: 2.1, latency: 184, exposure: 2.84 }
];

export const RECENT_RUN = {
  id: "BENCH-2026-0902-001",
  version: "FINSHIELD v1.9",
  dataset: "FS-BENCH-v3",
  scenarios: 10000,
  started: "00:18",
  duration: "14m 32s"
};
