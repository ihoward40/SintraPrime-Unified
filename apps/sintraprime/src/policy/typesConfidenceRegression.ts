import type { ConfidenceScoreOutput } from "./scorePolicy.js";
import type { ConfidenceRegressionResult } from "./compareConfidence.js";

export type ConfidenceScoreWithRegressionOutput = {
  kind: "ConfidenceScoreWithRegression";
  score: ConfidenceScoreOutput;
  regression: ConfidenceRegressionResult & { acknowledged?: boolean };
};
