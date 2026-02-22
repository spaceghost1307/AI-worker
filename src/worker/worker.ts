import { SessionManager, SessionSnapshot, SessionStatus } from '../session';

export interface WorkerOptions {
  workingDirectory: string;
  tags?: string[];
}

export class Worker {
  private sessionManager: SessionManager;
  private shutdownHandlers: Array<() => void> = [];

  constructor(sessionManager: SessionManager) {
    this.sessionManager = sessionManager;
  }

  start(options: WorkerOptions): SessionSnapshot {
    const session = this.sessionManager.createSession(
      options.workingDirectory,
      options.tags || []
    );

    this.setupGracefulShutdown();

    console.log(`Worker started with session: ${session.metadata.id}`);
    console.log(`Working directory: ${session.metadata.workingDirectory}`);
    console.log(`PID: ${process.pid}`);

    this.sessionManager.checkpoint(
      { phase: 'initialized' },
      ['Worker started', `Directory: ${options.workingDirectory}`]
    );

    return session;
  }

  resume(snapshot: SessionSnapshot): void {
    console.log(`Resuming session: ${snapshot.metadata.id}`);
    console.log(`Original working directory: ${snapshot.metadata.workingDirectory}`);
    console.log(`Checkpoints available: ${snapshot.metadata.checkpoints.length}`);

    if (snapshot.pendingOperations.length > 0) {
      console.log(`\nPending operations from previous session:`);
      for (const op of snapshot.pendingOperations) {
        console.log(`  - [${op.type}] ${op.description}`);
      }
    }

    this.setupGracefulShutdown();

    this.sessionManager.checkpoint(
      { phase: 'resumed', previousCheckpoints: snapshot.metadata.checkpoints.length },
      ['Session resumed via teleport']
    );
  }

  onShutdown(handler: () => void): void {
    this.shutdownHandlers.push(handler);
  }

  private setupGracefulShutdown(): void {
    const shutdown = (signal: string) => {
      console.log(`\nReceived ${signal}. Suspending session...`);

      for (const handler of this.shutdownHandlers) {
        try {
          handler();
        } catch (err) {
          console.error('Shutdown handler error:', err);
        }
      }

      try {
        this.sessionManager.markRecoverable();
        const session = this.sessionManager.getCurrentSession();
        if (session) {
          console.log(`Session ${session.metadata.id} marked as recoverable.`);
          console.log(`To resume, run: ai-worker --teleport ${session.metadata.id}`);
        }
      } catch {
        // Session may already be cleaned up
      }

      process.exit(0);
    };

    process.on('SIGINT', () => shutdown('SIGINT'));
    process.on('SIGTERM', () => shutdown('SIGTERM'));
  }
}
