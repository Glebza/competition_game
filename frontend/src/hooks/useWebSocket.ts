import { useEffect, useRef, useState } from 'react';

export const useWebSocket = (sessionCode: string, options: any) => {
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!sessionCode) return;

    const ws = new WebSocket(`ws://localhost:8000/api/v1/ws/${sessionCode}`);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      switch(data.type) {
        case 'player_joined':
          options.onPlayerJoined?.(data);
          break;
        case 'game_started':
          options.onGameStarted?.(data);
          break;
        case 'vote_update':
          options.onVoteUpdate?.(data);
          break;
        case 'next_pair':
          options.onNextPair?.(data);
          break;
        case 'game_complete':
          options.onGameComplete?.(data);
          break;
      }
    };

    ws.onclose = () => {
      setConnected(false);
    };

    return () => {
      ws.close();
    };
  }, [sessionCode]);

  const sendMessage = (type: string, data: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type, data }));
    }
  };

  return { connected, sendMessage };
};
