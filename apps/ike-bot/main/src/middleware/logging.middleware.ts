import { Request, Response, NextFunction } from 'express';
import { v4 as uuidv4 } from 'uuid';
import { logger } from '../config/logger';
import { supabase } from '../config/supabase';

// Extend Express Request type to include custom properties
declare global {
  namespace Express {
    interface Request {
      traceId?: string;
      correlationId?: string;
      startTime?: number;
    }
  }
}

/**
 * Middleware to add trace ID and correlation ID to each request
 */
export const traceMiddleware = (req: Request, res: Response, next: NextFunction) => {
  // Generate or extract trace ID
  req.traceId = (req.headers['x-trace-id'] as string) || uuidv4();
  req.correlationId = (req.headers['x-correlation-id'] as string) || req.traceId;
  req.startTime = Date.now();

  // Add trace ID to response headers
  res.setHeader('X-Trace-Id', req.traceId);
  res.setHeader('X-Correlation-Id', req.correlationId);

  next();
};

/**
 * Middleware to log incoming requests
 */
export const requestLogger = (req: Request, res: Response, next: NextFunction) => {
  const logData = {
    traceId: req.traceId,
    correlationId: req.correlationId,
    method: req.method,
    path: req.path,
    query: req.query,
    ip: req.ip,
    userAgent: req.get('user-agent'),
  };

  logger.info(logData, 'Incoming request');
  next();
};

/**
 * Middleware to log response and save to audit trail
 */
export const responseLogger = (req: Request, res: Response, next: NextFunction) => {
  const originalSend = res.send;

  res.send = function (data: any): Response {
    const duration = Date.now() - (req.startTime || Date.now());

    const logData = {
      traceId: req.traceId,
      correlationId: req.correlationId,
      method: req.method,
      path: req.path,
      statusCode: res.statusCode,
      duration,
    };

    // Log the response
    if (res.statusCode >= 400) {
      logger.error(logData, 'Request failed');
    } else {
      logger.info(logData, 'Request completed');
    }

    // Save to agent_logs asynchronously (don't block response)
    saveToAgentLogs(req, res, duration).catch((error) => {
      logger.error({ error, traceId: req.traceId }, 'Failed to save audit log');
    });

    return originalSend.call(this, data);
  };

  next();
};

/**
 * Save request/response to agent_logs table in Supabase
 */
async function saveToAgentLogs(req: Request, res: Response, duration: number) {
  const level = res.statusCode >= 500 ? 'error' : res.statusCode >= 400 ? 'warn' : 'info';

  await supabase.from('agent_logs').insert({
    trace_id: req.traceId || uuidv4(),
    correlation_id: req.correlationId,
    level,
    message: `${req.method} ${req.path}`,
    action: `${req.method.toLowerCase()}_${req.path.replace(/\//g, '_')}`,
    request_method: req.method,
    request_path: req.path,
    response_status: res.statusCode,
    duration_ms: duration,
    metadata: {
      query: req.query,
      ip: req.ip,
      userAgent: req.get('user-agent'),
    },
  });
}

/**
 * Error logging middleware - logs errors to both console and database
 */
export const errorLogger = (err: Error, req: Request, res: Response, next: NextFunction) => {
  const logData = {
    traceId: req.traceId,
    correlationId: req.correlationId,
    method: req.method,
    path: req.path,
    error: {
      name: err.name,
      message: err.message,
      stack: err.stack,
    },
  };

  logger.error(logData, 'Request error');

  // Save error to agent_logs asynchronously (don't block)
  saveErrorToAgentLogs(req, err).catch((dbError) => {
    logger.error({ dbError, traceId: req.traceId }, 'Failed to save error log to database');
  });

  next(err);
};

async function saveErrorToAgentLogs(req: Request, err: Error) {
  await supabase.from('agent_logs').insert({
    trace_id: req.traceId || uuidv4(),
    correlation_id: req.correlationId,
    level: 'error',
    message: err.message,
    action: 'error',
    request_method: req.method,
    request_path: req.path,
    error_stack: err.stack,
    metadata: {
      errorName: err.name,
    },
  });
}
