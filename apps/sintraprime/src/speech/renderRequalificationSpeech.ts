import type { RequalificationStatus } from "./getRequalificationStatus.js";

export function renderRequalificationSpeech(prev: RequalificationStatus, curr: RequalificationStatus): string {
  if (!curr.state || curr.state === prev.state) return "";

  switch (curr.state) {
    case "SUSPENDED":
      return `Autonomy suspended${curr.cause ? ` due to ${String(curr.cause).toLowerCase()}` : ""}.`;
    case "PROBATION":
      return "Autonomy entered probation mode.";
    case "ELIGIBLE":
      return "Autonomy is eligible for reactivation.";
    case "ACTIVE":
      return "Autonomy reactivated.";
    default:
      return "";
  }
}
