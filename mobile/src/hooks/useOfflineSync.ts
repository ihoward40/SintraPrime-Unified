import { useState, useEffect, useCallback, useRef } from 'react';
import NetInfo, { NetInfoState } from '@react-native-community/netinfo';

interface QueuedAction {
  id: string;
  type: string;
  payload: unknown;
  timestamp: number;
}

export function useOfflineSync() {
  const [isOnline, setIsOnline] = useState(true);
  const [isConnected, setIsConnected] = useState(true);
  const actionQueue = useRef<QueuedAction[]>([]);

  useEffect(() => {
    const unsubscribe = NetInfo.addEventListener((state: NetInfoState) => {
      const online = state.isConnected === true && state.isInternetReachable === true;
      setIsOnline(online ?? false);
      setIsConnected(state.isConnected ?? false);

      if (online && actionQueue.current.length > 0) {
        processQueue();
      }
    });

    return unsubscribe;
  }, []);

  const enqueueAction = useCallback((type: string, payload: unknown) => {
    const action: QueuedAction = {
      id: `${type}_${Date.now()}`,
      type,
      payload,
      timestamp: Date.now(),
    };
    actionQueue.current = [...actionQueue.current, action];
  }, []);

  const processQueue = useCallback(async () => {
    const queue = [...actionQueue.current];
    actionQueue.current = [];

    for (const action of queue) {
      try {
        console.log(`Processing queued action: ${action.type}`, action.payload);
        // In real implementation, dispatch actions to API
      } catch (error) {
        console.error(`Failed to process action ${action.type}:`, error);
        // Re-queue failed actions
        actionQueue.current.push(action);
      }
    }
  }, []);

  return {
    isOnline,
    isConnected,
    pendingActionsCount: actionQueue.current.length,
    enqueueAction,
  };
}
