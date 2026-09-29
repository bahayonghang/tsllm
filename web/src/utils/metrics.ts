import {
  arrayAt,
  isRecord,
  numberMatrix,
  numberOrNull,
  pointList,
  recordAt,
  stringOrNull,
} from "./guards";

export type NumberTable = Record<string, Record<string, number | null>>;

export type SplitMetrics = {
  split: string;
  overall: Record<string, number | null>;
  confusion: number[][] | null;
  perLead: NumberTable;
  perChannel: NumberTable;
  roc: [number, number][];
  pr: [number, number][];
  nOrigins: number | null;
  originSetHash: string | null;
};

export type RunMetrics = {
  task: string | null;
  splits: SplitMetrics[];
  resources: Record<string, number | null>;
  warnings: string[];
};

const SPLIT_ORDER = ["train", "fit", "val", "cal", "test"];

function numbers(value: unknown): Record<string, number | null> {
  if (!isRecord(value)) return {};
  const out: Record<string, number | null> = {};
  for (const [key, item] of Object.entries(value)) {
    if (item === null || typeof item === "number") out[key] = numberOrNull(item);
  }
  return out;
}

function table(value: unknown): NumberTable {
  if (!isRecord(value)) return {};
  return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, numbers(item)]));
}

function splitRank(split: string): number {
  const index = SPLIT_ORDER.indexOf(split);
  return index < 0 ? SPLIT_ORDER.length : index;
}

/** Read `metrics.json` (parent design §6.1), which the API returns as a free object. */
export function readMetrics(metrics: unknown): RunMetrics {
  const splits = Object.entries(recordAt(metrics, "splits") ?? {})
    .filter((entry): entry is [string, Record<string, unknown>] => isRecord(entry[1]))
    .map(([split, value]) => {
      const overall = recordAt(value, "overall");
      const confusion = numberMatrix(overall?.confusion);
      return {
        split,
        overall: numbers(overall),
        confusion: confusion.length > 0 ? confusion : null,
        perLead: table(value.per_lead),
        perChannel: table(value.per_channel),
        roc: pointList(recordAt(value, "curves")?.roc),
        pr: pointList(recordAt(value, "curves")?.pr),
        nOrigins: numberOrNull(value.n_origins),
        originSetHash: stringOrNull(value.origin_set_hash),
      };
    })
    .sort((a, b) => splitRank(a.split) - splitRank(b.split));
  return {
    task: isRecord(metrics) ? stringOrNull(metrics.task) : null,
    splits,
    resources: numbers(recordAt(metrics, "resources")),
    warnings: arrayAt(metrics, "warnings").map((item) =>
      typeof item === "string" ? item : JSON.stringify(item),
    ),
  };
}

/** Column names of every row, in first-seen order. */
export function columnsOf(rows: Record<string, Record<string, number | null>>): string[] {
  const names: string[] = [];
  for (const row of Object.values(rows)) {
    for (const key of Object.keys(row)) if (!names.includes(key)) names.push(key);
  }
  return names;
}
