import { useCallback, useEffect, useRef } from 'react';
import type { WsEvent } from './types';

interface UseWebSocketOptions {
  runId: string | null;
  onMessage: (event: WsEvent) => void;
  onOpen?: () => void;
  onClose?: () => void;
  enabled?: boolean;
}

export function useWebSocket({ runId, onMessage, onOpen, onClose, enabled = true }: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const pingRef = useRef<ReturnType<typeof setInterval> | undefined>(undefined);
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  // Keep callbacks in refs — prevents WebSocket reconnect on every render
  const onMessageRef = useRef(onMessage);
  const onOpenRef = useRef(onOpen);
  const onCloseRef = useRef(onClose);
  useEffect(() => { onMessageRef.current = onMessage; });
  useEffect(() => { onOpenRef.current = onOpen; });
  useEffect(() => { onCloseRef.current = onClose; });

  useEffect(() => {
    if (!runId || !enabled) return;

    let stopped = false;

    function connect() {
      if (stopped) return;

      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      const url = `${protocol}//${host}/ws/runs/${runId}`;

      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        onOpenRef.current?.();
        // Heartbeat every 30s
        pingRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, 30000);
      };

      ws.onmessage = (e) => {
        try {
          const event: WsEvent = JSON.parse(e.data);
          onMessageRef.current(event);
        } catch {
          // ignore parse errors
        }
      };

      ws.onclose = () => {
        if (pingRef.current) clearInterval(pingRef.current);
        onCloseRef.current?.();
        // Auto-reconnect after 2s unless unmounted
        if (!stopped) {
          reconnectRef.current = setTimeout(connect, 2000);
        }
      };

      ws.onerror = () => {
        ws.close();
      };
    }

    connect();

    return () => {
      stopped = true;
      if (pingRef.current) clearInterval(pingRef.current);
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
      wsRef.current?.close();
    };
  }, [runId, enabled]); // Only reconnect when runId or enabled truly changes

  const send = useCallback((data: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  return { send };
}
