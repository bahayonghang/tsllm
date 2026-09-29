import { arrayAt, isRecord, numberOrNull, recordAt, stringOrNull } from "./guards";

export type ChannelStats = {
  nullRate: number | null;
  mean: number | null;
  std: number | null;
};

export type DatasetMeta = {
  rows: number | null;
  eligiblePoints: number | null;
  segmentCount: number | null;
  channelNames: string[];
  channels: Record<string, ChannelStats>;
  segments: { start: string; end: string }[];
  splitBoundaries: Record<string, string>;
};

/** Read the cache `meta.json` that `GET /api/datasets/{id}` returns as a free object. */
export function readDatasetMeta(meta: unknown): DatasetMeta | null {
  if (!isRecord(meta)) return null;
  const channels: Record<string, ChannelStats> = {};
  for (const [name, value] of Object.entries(recordAt(meta, "channels") ?? {})) {
    if (!isRecord(value)) continue;
    channels[name] = {
      nullRate: numberOrNull(value.null_rate),
      mean: numberOrNull(value.eligible_mean),
      std: numberOrNull(value.eligible_std),
    };
  }
  const segments = arrayAt(meta, "segments").flatMap((item) => {
    const start = isRecord(item) ? stringOrNull(item.start) : null;
    const end = isRecord(item) ? stringOrNull(item.end) : null;
    return start && end ? [{ start, end }] : [];
  });
  const splitBoundaries: Record<string, string> = {};
  for (const [split, value] of Object.entries(recordAt(meta, "split_boundaries") ?? {})) {
    if (typeof value === "string") splitBoundaries[split] = value;
  }
  return {
    rows: numberOrNull(meta.rows),
    eligiblePoints: numberOrNull(meta.eligible_points),
    segmentCount: numberOrNull(meta.segment_count),
    channelNames: arrayAt(meta, "channel_names").filter((name) => typeof name === "string"),
    channels,
    segments,
    splitBoundaries,
  };
}
