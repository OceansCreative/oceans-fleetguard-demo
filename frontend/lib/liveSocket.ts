/**
 * A self-healing WebSocket: connects, surfaces status, and transparently
 * reconnects with exponential backoff when the socket drops.
 *
 * The reconnection logic lives here (rather than inside the React hook) so it
 * can be unit-tested with a fake socket and fake timers. The browser's
 * `WebSocket` constructor is injectable for the same reason.
 */

export type SocketStatus = "connecting" | "live" | "reconnecting";

/** The slice of the `WebSocket` API this manager relies on. */
export interface WebSocketLike {
  onopen: ((event: unknown) => void) | null;
  onclose: ((event: unknown) => void) | null;
  onerror: ((event: unknown) => void) | null;
  onmessage: ((event: { data: unknown }) => void) | null;
  close: () => void;
}

export interface LiveSocketOptions {
  url: string;
  onMessage: (data: unknown) => void;
  onStatus: (status: SocketStatus) => void;
  /** Initial reconnect delay; doubles per consecutive failure. */
  baseDelayMs?: number;
  /** Upper bound on the reconnect delay. */
  maxDelayMs?: number;
  /** Socket factory; defaults to the global `WebSocket`. Injected in tests. */
  create?: (url: string) => WebSocketLike;
}

export interface LiveSocket {
  /** Stop reconnecting and close the current socket. */
  close: () => void;
}

const DEFAULT_BASE_DELAY_MS = 1_000;
const DEFAULT_MAX_DELAY_MS = 30_000;

export function connectLive(options: LiveSocketOptions): LiveSocket {
  const {
    url,
    onMessage,
    onStatus,
    baseDelayMs = DEFAULT_BASE_DELAY_MS,
    maxDelayMs = DEFAULT_MAX_DELAY_MS,
    create = (target) => new WebSocket(target) as unknown as WebSocketLike,
  } = options;

  let stopped = false;
  let attempt = 0;
  let socket: WebSocketLike | null = null;
  let timer: ReturnType<typeof setTimeout> | null = null;

  const open = (): void => {
    if (stopped) return;
    onStatus(attempt === 0 ? "connecting" : "reconnecting");
    socket = create(url);
    socket.onopen = () => {
      attempt = 0; // a healthy connection resets the backoff
      onStatus("live");
    };
    socket.onmessage = (event) => onMessage(event.data);
    // A browser fires `onerror` then `onclose`; reconnect from close alone so we
    // never schedule twice.
    socket.onerror = () => onStatus("reconnecting");
    socket.onclose = () => scheduleReconnect();
  };

  const scheduleReconnect = (): void => {
    if (stopped) return;
    onStatus("reconnecting");
    const delay = Math.min(maxDelayMs, baseDelayMs * 2 ** attempt);
    attempt += 1;
    timer = setTimeout(open, delay);
  };

  open();

  return {
    close: () => {
      stopped = true;
      if (timer !== null) clearTimeout(timer);
      socket?.close();
    },
  };
}
