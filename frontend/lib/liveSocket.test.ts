import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  connectLive,
  type SocketStatus,
  type WebSocketLike,
} from "./liveSocket";

class FakeSocket implements WebSocketLike {
  onopen: ((event: unknown) => void) | null = null;
  onclose: ((event: unknown) => void) | null = null;
  onerror: ((event: unknown) => void) | null = null;
  onmessage: ((event: { data: unknown }) => void) | null = null;
  closed = false;

  close(): void {
    this.closed = true;
  }

  fireOpen(): void {
    this.onopen?.(null);
  }
  fireMessage(data: unknown): void {
    this.onmessage?.({ data });
  }
  fireClose(): void {
    this.onclose?.(null);
  }
  fireError(): void {
    this.onerror?.(null);
  }
}

function harness() {
  const sockets: FakeSocket[] = [];
  const statuses: SocketStatus[] = [];
  const messages: unknown[] = [];
  const live = connectLive({
    url: "ws://test/ws",
    baseDelayMs: 1_000,
    maxDelayMs: 8_000,
    onStatus: (status) => statuses.push(status),
    onMessage: (data) => messages.push(data),
    create: () => {
      const socket = new FakeSocket();
      sockets.push(socket);
      return socket;
    },
  });

  // Indexed access narrowing helper (tsconfig has noUncheckedIndexedAccess).
  const at = (index: number): FakeSocket => {
    const socket = sockets.at(index);
    if (socket === undefined) throw new Error(`no socket at index ${index}`);
    return socket;
  };

  return { sockets, statuses, messages, live, at };
}

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

describe("connectLive", () => {
  it("connects, goes live on open, and forwards messages", () => {
    const { sockets, statuses, messages, live, at } = harness();

    expect(sockets).toHaveLength(1);
    expect(statuses).toEqual(["connecting"]);

    at(0).fireOpen();
    expect(statuses.at(-1)).toBe("live");

    at(0).fireMessage('{"vehicles":[]}');
    expect(messages).toEqual(['{"vehicles":[]}']);

    live.close();
  });

  it("reconnects after the socket closes", () => {
    const { sockets, statuses, live, at } = harness();
    at(0).fireOpen();

    at(0).fireClose();
    expect(statuses.at(-1)).toBe("reconnecting");
    expect(sockets).toHaveLength(1); // not yet — waiting out the backoff

    vi.advanceTimersByTime(1_000);
    expect(sockets).toHaveLength(2); // reconnected

    at(1).fireOpen();
    expect(statuses.at(-1)).toBe("live");
    live.close();
  });

  it("backs off exponentially across consecutive failures", () => {
    const { sockets, live, at } = harness();

    at(0).fireClose(); // 1st failure -> 1000ms
    vi.advanceTimersByTime(999);
    expect(sockets).toHaveLength(1);
    vi.advanceTimersByTime(1);
    expect(sockets).toHaveLength(2);

    at(1).fireClose(); // 2nd failure -> 2000ms
    vi.advanceTimersByTime(1_999);
    expect(sockets).toHaveLength(2);
    vi.advanceTimersByTime(1);
    expect(sockets).toHaveLength(3);

    live.close();
  });

  it("caps the backoff at maxDelayMs", () => {
    const { sockets, live, at } = harness();
    // Delays would grow 1s,2s,4s,8s,16s... but the cap is 8s.
    for (let i = 0; i < 5; i += 1) {
      at(-1).fireClose();
      vi.advanceTimersByTime(8_000);
    }
    // Each close eventually produced exactly one new socket despite the cap.
    expect(sockets).toHaveLength(6);
    live.close();
  });

  it("resets the backoff after a successful reconnect", () => {
    const { sockets, live, at } = harness();

    at(0).fireClose(); // -> 1000ms
    vi.advanceTimersByTime(1_000);
    at(1).fireOpen(); // healthy again: backoff resets

    at(1).fireClose(); // next delay is base again, not 2000ms
    vi.advanceTimersByTime(1_000);
    expect(sockets).toHaveLength(3);

    live.close();
  });

  it("reports reconnecting on error", () => {
    const { statuses, live, at } = harness();
    at(0).fireOpen();
    at(0).fireError();
    expect(statuses.at(-1)).toBe("reconnecting");
    live.close();
  });

  it("stops reconnecting once closed", () => {
    const { sockets, live, at } = harness();
    at(0).fireOpen();

    live.close();
    expect(at(0).closed).toBe(true);

    at(0).fireClose(); // a late close event must not schedule a reconnect
    vi.advanceTimersByTime(60_000);
    expect(sockets).toHaveLength(1);
  });
});
