import {
  SessionManager,
  SessionSnapshot,
  SessionStatus,
  TeleportRequest,
  TeleportResult,
} from '../session';

export class TeleportHandler {
  private sessionManager: SessionManager;

  constructor(sessionManager: SessionManager) {
    this.sessionManager = sessionManager;
  }

  async teleport(request: TeleportRequest): Promise<TeleportResult> {
    const warnings: string[] = [];

    const snapshot = this.sessionManager.loadExistingSession(request.sessionId);
    if (!snapshot) {
      return {
        success: false,
        sessionId: request.sessionId,
        restoredCheckpoint: null,
        warnings: [],
        error: `Session '${request.sessionId}' not found`,
      };
    }

    const validationResult = this.validateSession(snapshot, request.force);
    if (!validationResult.valid) {
      return {
        success: false,
        sessionId: request.sessionId,
        restoredCheckpoint: null,
        warnings: validationResult.warnings,
        error: validationResult.error,
      };
    }
    warnings.push(...validationResult.warnings);

    let restoredCheckpoint: string | null = null;

    if (request.targetCheckpoint) {
      const checkpoint = snapshot.metadata.checkpoints.find(
        (c) => c.id === request.targetCheckpoint
      );
      if (!checkpoint) {
        return {
          success: false,
          sessionId: request.sessionId,
          restoredCheckpoint: null,
          warnings,
          error: `Checkpoint '${request.targetCheckpoint}' not found in session`,
        };
      }
      restoredCheckpoint = checkpoint.id;
    } else if (snapshot.metadata.checkpoints.length > 0) {
      const latest = snapshot.metadata.checkpoints[snapshot.metadata.checkpoints.length - 1];
      restoredCheckpoint = latest.id;
    }

    this.restoreEnvironment(snapshot);

    snapshot.metadata.status = SessionStatus.Active;
    snapshot.metadata.pid = process.pid;
    snapshot.metadata.updatedAt = Date.now();

    if (snapshot.pendingOperations.length > 0) {
      warnings.push(
        `${snapshot.pendingOperations.length} pending operation(s) found from previous session`
      );
    }

    return {
      success: true,
      sessionId: request.sessionId,
      restoredCheckpoint,
      warnings,
    };
  }

  private validateSession(
    snapshot: SessionSnapshot,
    force: boolean
  ): { valid: boolean; warnings: string[]; error?: string } {
    const warnings: string[] = [];

    if (snapshot.metadata.status === SessionStatus.Terminated) {
      if (!force) {
        return {
          valid: false,
          warnings,
          error: 'Session has been terminated. Use --force to recover anyway.',
        };
      }
      warnings.push('Recovering a terminated session; some state may be inconsistent');
    }

    if (snapshot.metadata.status === SessionStatus.Active && snapshot.metadata.pid) {
      if (this.isProcessRunning(snapshot.metadata.pid)) {
        if (!force) {
          return {
            valid: false,
            warnings,
            error: `Session is still active (PID ${snapshot.metadata.pid}). Use --force to take over.`,
          };
        }
        warnings.push(`Taking over from active process (PID ${snapshot.metadata.pid})`);
      } else {
        warnings.push('Previous session process is no longer running; recovering orphaned session');
      }
    }

    const ageMs = Date.now() - snapshot.metadata.updatedAt;
    const ageHours = ageMs / (1000 * 60 * 60);
    if (ageHours > 24) {
      warnings.push(`Session is ${Math.floor(ageHours)} hours old; state may be stale`);
    }

    return { valid: true, warnings };
  }

  private isProcessRunning(pid: number): boolean {
    try {
      process.kill(pid, 0);
      return true;
    } catch {
      return false;
    }
  }

  private restoreEnvironment(snapshot: SessionSnapshot): void {
    for (const [key, value] of Object.entries(snapshot.environment)) {
      if (!process.env[key]) {
        process.env[key] = value;
      }
    }
  }
}
