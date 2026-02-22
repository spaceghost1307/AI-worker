#!/usr/bin/env node

import { Command } from 'commander';
import { SessionManager, SessionStatus } from './session';
import { TeleportHandler } from './teleport';
import { Worker } from './worker';

const program = new Command();

program
  .name('ai-worker')
  .description('AI worker with teleport session recovery')
  .version('1.0.0');

program
  .option('--teleport <sessionId>', 'Teleport to (recover) a previous session')
  .option('--checkpoint <checkpointId>', 'Target a specific checkpoint when teleporting')
  .option('--force', 'Force teleport even if session is active or terminated', false)
  .option('--list-sessions', 'List all saved sessions')
  .option('--session-status <status>', 'Filter sessions by status (active, suspended, terminated, recoverable)')
  .option('--delete-session <sessionId>', 'Delete a saved session')
  .option('--tags <tags>', 'Comma-separated tags for the new session')
  .action(async (options) => {
    const sessionManager = new SessionManager();

    if (options.listSessions) {
      const statusFilter = options.sessionStatus as SessionStatus | undefined;
      const sessions = sessionManager.listAllSessions(statusFilter);

      if (sessions.length === 0) {
        console.log('No sessions found.');
        return;
      }

      console.log('Sessions:');
      console.log('─'.repeat(80));
      for (const session of sessions) {
        const age = formatAge(Date.now() - session.updatedAt);
        const checkpoints = session.checkpoints.length;
        console.log(
          `  ${session.id}  [${session.status}]  ${checkpoints} checkpoint(s)  ${age} ago`
        );
        if (session.tags.length > 0) {
          console.log(`    tags: ${session.tags.join(', ')}`);
        }
      }
      return;
    }

    if (options.deleteSession) {
      const deleted = sessionManager.deleteSessionById(options.deleteSession);
      if (deleted) {
        console.log(`Session '${options.deleteSession}' deleted.`);
      } else {
        console.error(`Session '${options.deleteSession}' not found.`);
        process.exit(1);
      }
      return;
    }

    if (options.teleport) {
      const teleporter = new TeleportHandler(sessionManager);
      const result = await teleporter.teleport({
        sessionId: options.teleport,
        targetCheckpoint: options.checkpoint,
        force: options.force,
      });

      if (!result.success) {
        console.error(`Teleport failed: ${result.error}`);
        for (const warning of result.warnings) {
          console.warn(`  Warning: ${warning}`);
        }
        process.exit(1);
      }

      console.log(`Teleported to session: ${result.sessionId}`);
      if (result.restoredCheckpoint) {
        console.log(`Restored checkpoint: ${result.restoredCheckpoint}`);
      }
      for (const warning of result.warnings) {
        console.warn(`  Warning: ${warning}`);
      }

      const snapshot = sessionManager.getCurrentSession();
      if (snapshot) {
        const worker = new Worker(sessionManager);
        worker.resume(snapshot);
      }
      return;
    }

    // Default: start a new session
    const worker = new Worker(sessionManager);
    const tags = options.tags ? options.tags.split(',').map((t: string) => t.trim()) : [];
    worker.start({
      workingDirectory: process.cwd(),
      tags,
    });
  });

function formatAge(ms: number): string {
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h`;
  const days = Math.floor(hours / 24);
  return `${days}d`;
}

program.parse();
