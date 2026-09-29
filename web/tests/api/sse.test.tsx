import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MAX_EVENTS, resetRunEvents, useRunEvents } from "../../src/api/sse";
import { newQueryClient, withQueryClient } from "../helpers";

type Listener = (event: MessageEvent<string>) => void;

class FakeEventSource {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSED = 2;
  static instances: FakeEventSource[] = [];

  readonly url: string;
  readyState = FakeEventSource.OPEN;
  onerror: (() => void) | null = null;
  private listeners = new Map<string, Listener[]>();

  constructor(url: string) {
    this.url = url;
    FakeEventSource.instances.push(this);
  }

  addEventListener(type: string, listener: Listener) {
    this.listeners.set(type, [...(this.listeners.get(type) ?? []), listener]);
  }

  close() {
    this.readyState = FakeEventSource.CLOSED;
  }

  emit(type: string, id: number, data: Record<string, unknown>) {
    const event = new MessageEvent(type, {
      data: JSON.stringify(data),
      lastEventId: String(id),
    });
    for (const listener of this.listeners.get(type) ?? []) listener(event);
  }
}

function lastSource(): FakeEventSource {
  const source = FakeEventSource.instances[FakeEventSource.instances.length - 1];
  if (!source) throw new Error("no EventSource was opened");
  return source;
}

describe("useRunEvents", () => {
  beforeEach(() => {
    FakeEventSource.instances = [];
    resetRunEvents();
    vi.stubGlobal("EventSource", FakeEventSource);
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  const flush = () => act(() => vi.advanceTimersByTime(500));

  it("resumes after the last id on remount and skips repeated events", () => {
    const client = newQueryClient();
    const invalidate = vi.spyOn(client, "invalidateQueries");
    const wrapper = withQueryClient(client);
    const first = renderHook(() => useRunEvents("run-1", true), { wrapper });
    expect(lastSource().url).toBe("/api/runs/run-1/events?from=0");

    act(() => {
      lastSource().emit("log", 1, { msg: "a" });
      lastSource().emit("stage", 2, { name: "fit" });
      lastSource().emit("progress", 3, { step: 1, total: 2 });
      // A browser reconnect resends from Last-Event-ID; an id at or below the last one is skipped.
      lastSource().emit("stage", 2, { name: "fit" });
    });
    flush();
    expect(first.result.current.events.map((event) => event.id)).toEqual([1, 2, 3]);
    // One stage event in the interval refetches the run and its metrics once.
    expect(invalidate).toHaveBeenCalledTimes(2);
    const closedSource = lastSource();
    first.unmount();
    expect(closedSource.readyState).toBe(FakeEventSource.CLOSED);

    const second = renderHook(() => useRunEvents("run-1", true), { wrapper });
    expect(lastSource().url).toBe("/api/runs/run-1/events?from=3");
    expect(second.result.current.events.map((event) => event.id)).toEqual([1, 2, 3]);

    act(() => {
      lastSource().emit("log", 4, { msg: "b" });
      lastSource().emit("end", 5, { state: "succeeded" });
    });
    expect(second.result.current.events.map((event) => event.id)).toEqual([1, 2, 3, 4]);
    expect(second.result.current.ended).toBe(true);
    expect(lastSource().readyState).toBe(FakeEventSource.CLOSED);

    // An ended stream does not open a new connection.
    const count = FakeEventSource.instances.length;
    renderHook(() => useRunEvents("run-1", true), { wrapper });
    expect(FakeEventSource.instances.length).toBe(count);
  });

  it("keeps the newest events and counts dropped ones", () => {
    const wrapper = withQueryClient(newQueryClient());
    const { result } = renderHook(() => useRunEvents("run-2", true), {
      wrapper,
    });
    act(() => {
      for (let id = 1; id <= MAX_EVENTS + 2; id += 1) lastSource().emit("log", id, { msg: "x" });
    });
    flush();
    expect(result.current.events).toHaveLength(MAX_EVENTS);
    expect(result.current.events[0]?.id).toBe(3);
    expect(result.current.dropped).toBe(2);
  });

  it("does not connect when disabled", () => {
    const wrapper = withQueryClient(newQueryClient());
    renderHook(() => useRunEvents("run-3", false), { wrapper });
    expect(FakeEventSource.instances).toHaveLength(0);
  });
});
