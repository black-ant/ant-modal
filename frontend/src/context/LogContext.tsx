import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { EventsOn } from '../../wailsjs/runtime/runtime';

export type LogType = 'info' | 'error' | 'warning' | 'command';

export interface LogEntry {
  timestamp: string;
  type: LogType;
  message: string;
}

interface LogContextType {
  logs: LogEntry[];
  addLog: (type: LogType, message: string) => void;
  clearLogs: () => void;
  isVisible: boolean;
  toggleVisibility: () => void;
}

const LogContext = createContext<LogContextType | undefined>(undefined);

export const useLogs = () => {
  const context = useContext(LogContext);
  if (!context) {
    throw new Error('useLogs must be used within a LogProvider');
  }
  return context;
};

interface LogProviderProps {
  children: ReactNode;
}

export const LogProvider: React.FC<LogProviderProps> = ({ children }) => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isVisible, setIsVisible] = useState(false);

  const addLog = (type: LogType, message: string) => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs((prev) => [...prev, { timestamp, type, message }]);
  };

  const clearLogs = () => {
    setLogs([]);
  };

  const toggleVisibility = () => {
    setIsVisible((prev) => !prev);
  };

  useEffect(() => {
    // 监听后端日志事件
    const unsubscribe = EventsOn('log:entry', (entry: LogEntry) => {
      setLogs((prev) => [...prev, entry]);
    });

    // 捕获全局未处理的 Promise 错误
    const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
        addLog('error', `UI Unhandled Rejection: ${event.reason}`);
    };

    // 捕获全局错误
    const handleError = (event: ErrorEvent) => {
        addLog('error', `UI Error: ${event.message} at ${event.filename}:${event.lineno}`);
    };

    window.addEventListener('unhandledrejection', handleUnhandledRejection);
    window.addEventListener('error', handleError);

    return () => {
      // Wails cleanup if needed (EventsOn usually returns a cleanup function in some versions, 
      // but standard Wails v2 JS runtime doesn't always return an unlistener directly for named events in the same way. 
      // Actually EventsOn returns an unsubscribe function in Wails v2.
      if (unsubscribe) unsubscribe();
      window.removeEventListener('unhandledrejection', handleUnhandledRejection);
      window.removeEventListener('error', handleError);
    };
  }, []);

  return (
    <LogContext.Provider value={{ logs, addLog, clearLogs, isVisible, toggleVisibility }}>
      {children}
    </LogContext.Provider>
  );
};

