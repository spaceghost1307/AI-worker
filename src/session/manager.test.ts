import * as fs from 'fs';
import * as path from 'path';
import { SessionManager } from './manager';
import { SessionStatus } from './types';
import { getSessionsDir } from './store';

describe('SessionManager', () => {
  let manager: SessionManager;

  beforeEach(() => {
    manager = new SessionManager();
    // Clean up test sessions
    const sessionsDir = getSessionsDir();
    if (fs.existsSync(sessionsDir)) {
      for (const file of fs.readdirSync(sessionsDir)) {
        if (file.endsWith('.json')) {
          try {
            fs.unlinkSync(path.join(sessionsDir, file));
          } catch {
            // File may already be deleted by parallel test suite
          }
        }
      }
    }
  });

  describe('createSession', () => {
    it('should create a new session with correct defaults', () => {
      const snapshot = manager.createSession('/tmp/test');

      expect(snapshot.metadata.id).toMatch(/^session_/);
      expect(snapshot.metadata.status).toBe(SessionStatus.Active);
      expect(snapshot.metadata.workingDirectory).toBe('/tmp/test');
      expect(snapshot.metadata.pid).toBe(process.pid);
      expect(snapshot.metadata.checkpoints).toHaveLength(0);
      expect(snapshot.metadata.tags).toHaveLength(0);
    });

    it('should create a session with tags', () => {
      const snapshot = manager.createSession('/tmp/test', ['dev', 'feature']);

      expect(snapshot.metadata.tags).toEqual(['dev', 'feature']);
    });

    it('should capture safe environment variables', () => {
      const snapshot = manager.createSession('/tmp/test');

      // Should only capture safe keys
      const keys = Object.keys(snapshot.environment);
      const safeKeys = ['PATH', 'HOME', 'USER', 'SHELL', 'TERM', 'LANG', 'NODE_ENV'];
      for (const key of keys) {
        expect(safeKeys).toContain(key);
      }
    });
  });

  describe('checkpoint', () => {
    it('should create a checkpoint on the current session', () => {
      manager.createSession('/tmp/test');
      const checkpoint = manager.checkpoint({ step: 1 }, ['First step done']);

      expect(checkpoint.id).toMatch(/^chk_/);
      expect(checkpoint.state).toEqual({ step: 1 });
      expect(checkpoint.context).toEqual(['First step done']);
      expect(checkpoint.cursorPosition).toBe(0);
    });

    it('should increment cursor position for subsequent checkpoints', () => {
      manager.createSession('/tmp/test');
      manager.checkpoint({ step: 1 }, ['First']);
      const second = manager.checkpoint({ step: 2 }, ['Second']);

      expect(second.cursorPosition).toBe(1);
    });

    it('should throw if no active session', () => {
      expect(() => manager.checkpoint({}, [])).toThrow('No active session');
    });
  });

  describe('suspend and markRecoverable', () => {
    it('should suspend the current session', () => {
      manager.createSession('/tmp/test');
      manager.suspend();

      const session = manager.getCurrentSession();
      expect(session?.metadata.status).toBe(SessionStatus.Suspended);
    });

    it('should mark session as recoverable', () => {
      manager.createSession('/tmp/test');
      manager.markRecoverable();

      const session = manager.getCurrentSession();
      expect(session?.metadata.status).toBe(SessionStatus.Recoverable);
    });
  });

  describe('terminate', () => {
    it('should terminate and clear the current session', () => {
      manager.createSession('/tmp/test');
      manager.terminate();

      expect(manager.getCurrentSession()).toBeNull();
    });
  });

  describe('pending operations', () => {
    it('should add and complete pending operations', () => {
      manager.createSession('/tmp/test');

      const op = manager.addPendingOperation('build', 'Running build', { target: 'dist' });
      expect(op.id).toMatch(/^op_/);
      expect(op.type).toBe('build');

      let session = manager.getCurrentSession();
      expect(session?.pendingOperations).toHaveLength(1);

      manager.completePendingOperation(op.id);
      session = manager.getCurrentSession();
      expect(session?.pendingOperations).toHaveLength(0);
    });
  });

  describe('loadExistingSession', () => {
    it('should load a previously saved session', () => {
      const snapshot = manager.createSession('/tmp/test');
      const sessionId = snapshot.metadata.id;

      const newManager = new SessionManager();
      const loaded = newManager.loadExistingSession(sessionId);

      expect(loaded).not.toBeNull();
      expect(loaded?.metadata.id).toBe(sessionId);
    });

    it('should return null for non-existent session', () => {
      const result = manager.loadExistingSession('session_nonexistent');
      expect(result).toBeNull();
    });
  });

  describe('listAllSessions', () => {
    it('should list all sessions', () => {
      manager.createSession('/tmp/test1');
      manager.createSession('/tmp/test2');

      const sessions = manager.listAllSessions();
      expect(sessions.length).toBeGreaterThanOrEqual(2);
    });

    it('should filter by status', () => {
      manager.createSession('/tmp/test1');
      manager.suspend();
      manager.createSession('/tmp/test2');

      const suspended = manager.listAllSessions(SessionStatus.Suspended);
      expect(suspended.length).toBeGreaterThanOrEqual(1);
      for (const s of suspended) {
        expect(s.status).toBe(SessionStatus.Suspended);
      }
    });
  });

  describe('deleteSessionById', () => {
    it('should delete a session', () => {
      const snapshot = manager.createSession('/tmp/test');
      const sessionId = snapshot.metadata.id;

      const deleted = manager.deleteSessionById(sessionId);
      expect(deleted).toBe(true);

      const loaded = manager.loadExistingSession(sessionId);
      expect(loaded).toBeNull();
    });

    it('should return false for non-existent session', () => {
      const deleted = manager.deleteSessionById('session_nonexistent');
      expect(deleted).toBe(false);
    });
  });
});
