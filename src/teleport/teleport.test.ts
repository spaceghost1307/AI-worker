import * as fs from 'fs';
import * as path from 'path';
import { SessionManager, SessionStatus, getSessionsDir } from '../session';
import { TeleportHandler } from './teleport';

describe('TeleportHandler', () => {
  let manager: SessionManager;
  let teleporter: TeleportHandler;

  beforeEach(() => {
    manager = new SessionManager();
    teleporter = new TeleportHandler(manager);

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

  describe('teleport', () => {
    it('should fail for non-existent session', async () => {
      const result = await teleporter.teleport({
        sessionId: 'session_nonexistent',
        force: false,
      });

      expect(result.success).toBe(false);
      expect(result.error).toContain('not found');
    });

    it('should teleport to a suspended session', async () => {
      const snapshot = manager.createSession('/tmp/test');
      manager.checkpoint({ step: 'init' }, ['Initialized']);
      manager.suspend();
      const sessionId = snapshot.metadata.id;

      // Use a new manager to simulate a new process
      const newManager = new SessionManager();
      const newTeleporter = new TeleportHandler(newManager);

      const result = await newTeleporter.teleport({
        sessionId,
        force: false,
      });

      expect(result.success).toBe(true);
      expect(result.sessionId).toBe(sessionId);
      expect(result.restoredCheckpoint).toBeTruthy();
    });

    it('should teleport to a recoverable session', async () => {
      const snapshot = manager.createSession('/tmp/test');
      manager.checkpoint({ phase: 'working' }, ['In progress']);
      manager.markRecoverable();
      const sessionId = snapshot.metadata.id;

      const newManager = new SessionManager();
      const newTeleporter = new TeleportHandler(newManager);

      const result = await newTeleporter.teleport({
        sessionId,
        force: false,
      });

      expect(result.success).toBe(true);
    });

    it('should fail to teleport to terminated session without force', async () => {
      const snapshot = manager.createSession('/tmp/test');
      manager.terminate();
      const sessionId = snapshot.metadata.id;

      const newManager = new SessionManager();
      const newTeleporter = new TeleportHandler(newManager);

      const result = await newTeleporter.teleport({
        sessionId,
        force: false,
      });

      expect(result.success).toBe(false);
      expect(result.error).toContain('terminated');
    });

    it('should teleport to terminated session with force', async () => {
      const snapshot = manager.createSession('/tmp/test');
      const sessionId = snapshot.metadata.id;
      manager.terminate();

      const newManager = new SessionManager();
      const newTeleporter = new TeleportHandler(newManager);

      const result = await newTeleporter.teleport({
        sessionId,
        force: true,
      });

      expect(result.success).toBe(true);
      expect(result.warnings.length).toBeGreaterThan(0);
    });

    it('should teleport to a specific checkpoint', async () => {
      const snapshot = manager.createSession('/tmp/test');
      const chk1 = manager.checkpoint({ step: 1 }, ['Step 1']);
      manager.checkpoint({ step: 2 }, ['Step 2']);
      manager.suspend();
      const sessionId = snapshot.metadata.id;

      const newManager = new SessionManager();
      const newTeleporter = new TeleportHandler(newManager);

      const result = await newTeleporter.teleport({
        sessionId,
        targetCheckpoint: chk1.id,
        force: false,
      });

      expect(result.success).toBe(true);
      expect(result.restoredCheckpoint).toBe(chk1.id);
    });

    it('should fail for invalid checkpoint', async () => {
      const snapshot = manager.createSession('/tmp/test');
      manager.suspend();
      const sessionId = snapshot.metadata.id;

      const newManager = new SessionManager();
      const newTeleporter = new TeleportHandler(newManager);

      const result = await newTeleporter.teleport({
        sessionId,
        targetCheckpoint: 'chk_nonexistent',
        force: false,
      });

      expect(result.success).toBe(false);
      expect(result.error).toContain('Checkpoint');
    });

    it('should warn about pending operations', async () => {
      const snapshot = manager.createSession('/tmp/test');
      manager.addPendingOperation('build', 'Running build', {});
      manager.suspend();
      const sessionId = snapshot.metadata.id;

      const newManager = new SessionManager();
      const newTeleporter = new TeleportHandler(newManager);

      const result = await newTeleporter.teleport({
        sessionId,
        force: false,
      });

      expect(result.success).toBe(true);
      expect(result.warnings.some((w) => w.includes('pending operation'))).toBe(true);
    });
  });
});
