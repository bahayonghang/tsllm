import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { isRecord } from "../utils/guards";

export type RunEvent = {
  id: number;
  kind: string;
  data: Record<string, unknown>;
};

export const MAX_EVENTS = 5000;
const EVENT_KINDS = ["log", "progress", "metric", "stage"];
const FLUSH_MS = 200;

type StreamState = {
  events: RunEvent[];
  dropped: number;
  lastId: number;
  ended: boolean;
};

// Events received per run survive a remount, so a new stream starts after the last id.
const streams = new Map<string, StreamState>();

function streamFor(runId: string): StreamState {
  let state = streams.get(runId);
  if (state === undefined) {
    state = { events: [], dropped: 0, lastId: 0, ended: false };
    streams.set(runId, state);
  }
  return state;
}

export function resetRunEvents(): void {
  streams.clear();
}

export function useRunEvents(
  runId: string,
  enabled: boolean,
): {
  events: RunEvent[];
  dropped: number;
  ended: boolean;
  error: string | null;
} {
  const client = useQueryClient();
  const [snapshot, setSnapshot] = useState(() => ({ ...streamFor(runId) }));
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const state = streamFor(runId);
    setSnapshot({ ...state });
    if (!enabled || state.ended) return;

    const url = `/api/runs/${encodeURIComponent(runId)}/events?from=${state.lastId}`;
    const source = new EventSource(url);

    // A replayed log delivers many events at once; render and refetch at most once per interval.
    let flushTimer: number | undefined;
    let invalidatePending = false;
    const flush = () => {
      window.clearTimeout(flushTimer);
      flushTimer = undefined;
      setSnapshot({ ...state, events: [...state.events] });
      if (invalidatePending) {
        invalidatePending = false;
        void client.invalidateQueries({ queryKey: ["run", runId] });
        void client.invalidateQueries({ queryKey: ["metrics", runId] });
      }
    };
    const scheduleFlush = () => {
      if (flushTimer === undefined) flushTimer = window.setTimeout(flush, FLUSH_MS);
    };

    const onEvent = (message: MessageEvent<string>) => {
      const id = Number(message.lastEventId);
      // The browser resends from Last-Event-ID after a reconnect; skip what is already kept.
      if (!Number.isFinite(id) || id <= state.lastId) return;
      let data: unknown;
      try {
        data = JSON.parse(message.data);
      } catch {
        data = { msg: message.data };
      }
      state.lastId = id;
      state.events.push({
        id,
        kind: message.type,
        data: isRecord(data) ? data : {},
      });
      if (state.events.length > MAX_EVENTS) {
        const extra = state.events.length - MAX_EVENTS;
        state.events.splice(0, extra);
        state.dropped += extra;
      }
      setError(null);
      if (message.type === "stage") invalidatePending = true;
      scheduleFlush();
    };

    const onEnd = () => {
      state.ended = true;
      source.close();
      invalidatePending = true;
      flush();
    };

    for (const kind of EVENT_KINDS) source.addEventListener(kind, onEvent);
    source.addEventListener("end", onEnd);
    source.onerror = () => {
      setError(
        source.readyState === EventSource.CLOSED ? "事件流已断开" : "事件流连接中断，正在重连",
      );
    };

    return () => {
      window.clearTimeout(flushTimer);
      source.close();
    };
  }, [client, runId, enabled]);

  return {
    events: snapshot.events,
    dropped: snapshot.dropped,
    ended: snapshot.ended,
    error,
  };
}
