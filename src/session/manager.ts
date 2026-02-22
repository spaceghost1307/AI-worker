import { v4 as uuidv4 } from 'uuid';
import {
  SessionCheckpoint,
  SessionMetadata,
  SessionSnapshot,
  SessionStatus,
  PendingOperation,
} from './types';
import { saveSession, loadSession, listSessions, deleteSession } from './store';

export class SessionManager {
  private currentSession: SessionSnapshot | null = null;

  createSession(workingDirectory: string, tags: string[] = []): SessionSnapshot {
    const now = Date.now();
    const sessionId = `session_${uuidv4().replace(/-/g, '').slice(0, 20)}`;

    const metadata: SessionMetadata = {
      id: sessionId,
      createdAt: now,
      updatedAt: now,
      status: SessionStatus.Active,
      workingDirectory,
      pid: process.pid,
      checkpoints: [],
      tags,
    };

    const snapshot: SessionSnapshot = {
      metadata,
      environment: this.captureEnvironment(),
      pendingOperations: [],
    };

    this.currentSession = snapshot;
    saveSession(snapshot);
    return snapshot;
  }

  checkpoint(state: Record<string, unknown>, context: string[]): SessionCheckpoint {
    if (!this.currentSession) {
      throw new Error('No active session to checkpoint');
    }

    const checkpoint: SessionCheckpoint = {
      id: `chk_${uuidv4().replace(/-/g, '').slice(0, 12)}`,
      timestamp: Date.now(),
      state,
      context,
      cursorPosition: this.currentSession.metadata.checkpoints.length,
    };

    this.currentSession.metadata.checkpoints.push(checkpoint);
    this.currentSession.metadata.updatedAt = Date.now();
    saveSession(this.currentSession);
    return checkpoint;
  }

  suspend(): void {
    if (!this.currentSession) {
      throw new Error('No active session to suspend');
    }
    this.currentSession.metadata.status = SessionStatus.Suspended;
    this.currentSession.metadata.updatedAt = Date.now();
    saveSession(this.currentSession);
  }

  markRecoverable(): void {
    if (!this.currentSession) {
      throw new Error('No active session to mark as recoverable');
    }
    this.currentSession.metadata.status = SessionStatus.Recoverable;
    this.currentSession.metadata.updatedAt = Date.now();
    saveSession(this.currentSession);
  }

  terminate(): void {
    if (!this.currentSession) {
      throw new Error('No active session to terminate');
    }
    this.currentSession.metadata.status = SessionStatus.Terminated;
    this.currentSession.metadata.pid = null;
    this.currentSession.metadata.updatedAt = Date.now();
    saveSession(this.currentSession);
    this.currentSession = null;
  }

  addPendingOperation(type: string, description: string, state: Record<string, unknown>): PendingOperation {
    if (!this.currentSession) {
      throw new Error('No active session');
    }

    const op: PendingOperation = {
      id: `op_${uuidv4().replace(/-/g, '').slice(0, 12)}`,
      type,
      description,
      state,
      createdAt: Date.now(),
    };

    this.currentSession.pendingOperations.push(op);
    this.currentSession.metadata.updatedAt = Date.now();
    saveSession(this.currentSession);
    return op;
  }

  completePendingOperation(operationId: string): void {
    if (!this.currentSession) {
      throw new Error('No active session');
    }
    this.currentSession.pendingOperations = this.currentSession.pendingOperations.filter(
      (op) => op.id !== operationId
    );
    this.currentSession.metadata.updatedAt = Date.now();
    saveSession(this.currentSession);
  }

  loadExistingSession(sessionId: string): SessionSnapshot | null {
    const snapshot = loadSession(sessionId);
    if (snapshot) {
      this.currentSession = snapshot;
    }
    return snapshot;
  }

  getCurrentSession(): SessionSnapshot | null {
    return this.currentSession;
  }

  listAllSessions(filter?: SessionStatus): SessionMetadata[] {
    return listSessions(filter);
  }

  deleteSessionById(sessionId: string): boolean {
    if (this.currentSession?.metadata.id === sessionId) {
      this.currentSession = null;
    }
    return deleteSession(sessionId);
  }

  private captureEnvironment(): Record<string, string> {
    const safeKeys = ['PATH', 'HOME', 'USER', 'SHELL', 'TERM', 'LANG', 'NODE_ENV'];
    const env: Record<string, string> = {};
    for (const key of safeKeys) {
      if (process.env[key]) {
        env[key] = process.env[key]!;
      }
    }
    return env;
  }
}
