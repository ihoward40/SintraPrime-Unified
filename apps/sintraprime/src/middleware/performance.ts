import { Request, Response, NextFunction } from 'express';
import { performance } from 'perf_hooks';

interface PerformanceMetrics {
  requests: Map<string, number[]>;
  slowQueries: Array<{ route: string; duration: number; timestamp: number }>;
}

const metrics: PerformanceMetrics = {
  requests: new Map(),
  slowQueries: []
};

export function performanceMiddleware(
  req: Request, 
  res: Response, 
  next: NextFunction
) {
  const start = performance.now();
  const route = req.route?.path || req.path;
  
  res.on('finish', () => {
    const duration = performance.now() - start;
    
    if (!metrics.requests.has(route)) {
      metrics.requests.set(route, []);
    }
    
    const times = metrics.requests.get(route)!;
    times.push(duration);
    
    // Keep only last 1000 entries per route
    if (times.length > 1000) {
      times.shift();
    }
    
    // Log slow queries (>1s)
    if (duration > 1000) {
      metrics.slowQueries.push({ 
        route, 
        duration, 
        timestamp: Date.now() 
      });
      
      // Keep only last 100 slow queries
      if (metrics.slowQueries.length > 100) {
        metrics.slowQueries.shift();
      }
    }
  });
  
  next();
}

export function getMetrics() {
  const stats = Object.fromEntries(
    Array.from(metrics.requests.entries()).map(([route, times]) => {
      const sorted = [...times].sort((a, b) => a - b);
      return [
        route,
        {
          count: times.length,
          avg: times.reduce((a, b) => a + b, 0) / times.length,
          min: sorted[0],
          max: sorted[sorted.length - 1],
          p50: sorted[Math.floor(times.length * 0.5)],
          p95: sorted[Math.floor(times.length * 0.95)],
          p99: sorted[Math.floor(times.length * 0.99)]
        }
      ];
    })
  );
  
  return { 
    stats, 
    slowQueries: metrics.slowQueries.slice(-50) 
  };
}

export function clearMetrics() {
  metrics.requests.clear();
  metrics.slowQueries = [];
}
