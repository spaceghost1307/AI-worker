export enum SessionStatus {
  Active = 'active',
  Suspended = 'suspended',
  Terminated = 'terminated',
  Recoverable = 'recoverable',
}

export interface SessionCheckpoint {
  id: string;
  timestamp: number;
  state: Record<string, unknown>;
  context: string[];
  cursorPosition: number;
}

export interface SessionMetadata {
  id: string;
  createdAt: number;
  updatedAt: number;
  status: SessionStatus;
  workingDirectory: string;
  pid: number | null;
  checkpoints: SessionCheckpoint[];
  tags: string[];
}

export interface SessionSnapshot {
  metadata: SessionMetadata;
  environment: Record<string, string>;
  pendingOperations: PendingOperation[];
}

export interface PendingOperation {
  id: string;
  type: string;
  description: string;
  state: Record<string, unknown>;
  createdAt: number;
}

export interface TeleportRequest {
  sessionId: string;
  targetCheckpoint?: string;
  force: boolean;
}

export interface TeleportResult {
  success: boolean;
  sessionId: string;
  restoredCheckpoint: string | null;
  warnings: string[];
  error?: string;
}
