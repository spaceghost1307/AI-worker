import * as fs from 'fs';
import * as path from 'path';
import { SessionMetadata, SessionSnapshot, SessionStatus } from './types';

const SESSIONS_DIR = path.join(
  process.env.AI_WORKER_HOME || path.join(process.env.HOME || '~', '.ai-worker'),
  'sessions'
);

function ensureSessionsDir(): void {
  fs.mkdirSync(SESSIONS_DIR, { recursive: true });
}

function sessionPath(sessionId: string): string {
  return path.join(SESSIONS_DIR, `${sessionId}.json`);
}

export function saveSession(snapshot: SessionSnapshot): void {
  ensureSessionsDir();
  const filePath = sessionPath(snapshot.metadata.id);
  fs.writeFileSync(filePath, JSON.stringify(snapshot, null, 2), 'utf-8');
}

export function loadSession(sessionId: string): SessionSnapshot | null {
  const filePath = sessionPath(sessionId);
  if (!fs.existsSync(filePath)) {
    return null;
  }
  const raw = fs.readFileSync(filePath, 'utf-8');
  return JSON.parse(raw) as SessionSnapshot;
}

export function deleteSession(sessionId: string): boolean {
  const filePath = sessionPath(sessionId);
  if (!fs.existsSync(filePath)) {
    return false;
  }
  fs.unlinkSync(filePath);
  return true;
}

export function listSessions(filter?: SessionStatus): SessionMetadata[] {
  ensureSessionsDir();
  const files = fs.readdirSync(SESSIONS_DIR).filter((f) => f.endsWith('.json'));
  const sessions: SessionMetadata[] = [];

  for (const file of files) {
    const raw = fs.readFileSync(path.join(SESSIONS_DIR, file), 'utf-8');
    const snapshot = JSON.parse(raw) as SessionSnapshot;
    if (!filter || snapshot.metadata.status === filter) {
      sessions.push(snapshot.metadata);
    }
  }

  return sessions.sort((a, b) => b.updatedAt - a.updatedAt);
}

export function getSessionsDir(): string {
  return SESSIONS_DIR;
}
