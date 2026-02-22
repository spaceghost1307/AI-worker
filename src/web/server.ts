import express from 'express';
import cors from 'cors';
import path from 'path';
import { SessionManager, SessionStatus } from '../session';
import { TeleportHandler } from '../teleport';
import { Worker } from '../worker';

export function createServer(port: number = 3000) {
  const app = express();
  const sessionManager = new SessionManager();
  const teleportHandler = new TeleportHandler(sessionManager);
  let activeWorker: Worker | null = null;

  app.use(cors());
  app.use(express.json());
  app.use(express.static(path.join(__dirname, '..', '..', 'public')));

  // List sessions
  app.get('/api/sessions', (_req, res) => {
    const filter = _req.query.status as SessionStatus | undefined;
    const sessions = sessionManager.listAllSessions(filter);
    res.json({ sessions });
  });

  // Get current session
  app.get('/api/sessions/current', (_req, res) => {
    const session = sessionManager.getCurrentSession();
    if (!session) {
      res.json({ session: null });
      return;
    }
    res.json({ session });
  });

  // Create a new session
  app.post('/api/sessions', (req, res) => {
    const { workingDirectory, tags } = req.body;
    const dir = workingDirectory || process.cwd();
    const tagList = tags || [];

    const worker = new Worker(sessionManager);
    activeWorker = worker;
    const session = worker.start({ workingDirectory: dir, tags: tagList });

    res.json({ session });
  });

  // Create a checkpoint
  app.post('/api/sessions/checkpoint', (req, res) => {
    const { state, context } = req.body;
    try {
      const checkpoint = sessionManager.checkpoint(state || {}, context || []);
      res.json({ checkpoint });
    } catch (err: any) {
      res.status(400).json({ error: err.message });
    }
  });

  // Suspend current session
  app.post('/api/sessions/suspend', (_req, res) => {
    try {
      sessionManager.suspend();
      res.json({ success: true, message: 'Session suspended' });
    } catch (err: any) {
      res.status(400).json({ error: err.message });
    }
  });

  // Mark session recoverable
  app.post('/api/sessions/recoverable', (_req, res) => {
    try {
      sessionManager.markRecoverable();
      res.json({ success: true, message: 'Session marked as recoverable' });
    } catch (err: any) {
      res.status(400).json({ error: err.message });
    }
  });

  // Terminate current session
  app.post('/api/sessions/terminate', (_req, res) => {
    try {
      sessionManager.terminate();
      activeWorker = null;
      res.json({ success: true, message: 'Session terminated' });
    } catch (err: any) {
      res.status(400).json({ error: err.message });
    }
  });

  // Delete a session
  app.delete('/api/sessions/:sessionId', (req, res) => {
    const deleted = sessionManager.deleteSessionById(req.params.sessionId);
    if (deleted) {
      res.json({ success: true, message: `Session '${req.params.sessionId}' deleted` });
    } else {
      res.status(404).json({ error: `Session '${req.params.sessionId}' not found` });
    }
  });

  // Teleport to a session
  app.post('/api/teleport', async (req, res) => {
    const { sessionId, targetCheckpoint, force } = req.body;
    if (!sessionId) {
      res.status(400).json({ error: 'sessionId is required' });
      return;
    }

    const result = await teleportHandler.teleport({
      sessionId,
      targetCheckpoint,
      force: force || false,
    });

    if (result.success) {
      const snapshot = sessionManager.getCurrentSession();
      if (snapshot) {
        const worker = new Worker(sessionManager);
        activeWorker = worker;
        worker.resume(snapshot);
      }
    }

    res.json(result);
  });

  // Add a pending operation
  app.post('/api/sessions/operations', (req, res) => {
    const { type, description, state } = req.body;
    try {
      const op = sessionManager.addPendingOperation(type || 'task', description || '', state || {});
      res.json({ operation: op });
    } catch (err: any) {
      res.status(400).json({ error: err.message });
    }
  });

  // Complete a pending operation
  app.delete('/api/sessions/operations/:operationId', (req, res) => {
    try {
      sessionManager.completePendingOperation(req.params.operationId);
      res.json({ success: true });
    } catch (err: any) {
      res.status(400).json({ error: err.message });
    }
  });

  // Fallback to index.html for SPA
  app.use((_req, res) => {
    res.sendFile(path.join(__dirname, '..', '..', 'public', 'index.html'));
  });

  const server = app.listen(port, () => {
    console.log(`AI Worker web UI running at http://localhost:${port}`);
  });

  return server;
}
