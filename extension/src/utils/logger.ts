// Structured logging to a dedicated VS Code Output Channel.
//
// An OutputChannel is the right home for developer-facing diagnostics: it's a
// named, scrollable pane in the Output panel that the user can open on demand,
// unlike toast notifications (ephemeral) or console.log (invisible in a packaged
// extension). We log API requests, errors, and timings so a misbehaving backend
// call is traceable after the fact.
//
// Honors the `enableLogs` setting: when off, writes are dropped at the source.

import * as vscode from "vscode";

import { OUTPUT_CHANNEL_NAME } from "../config/constants";
import { areLogsEnabled } from "../config/settings";

export class Logger {
  private readonly channel: vscode.OutputChannel;

  constructor() {
    this.channel = vscode.window.createOutputChannel(OUTPUT_CHANNEL_NAME);
  }

  info(message: string): void {
    this.write("INFO ", message);
  }

  error(message: string): void {
    this.write("ERROR", message);
  }

  /** Log an outbound HTTP call (no bodies — keep it terse and PII-free). */
  request(method: string, url: string): void {
    this.write("HTTP ", `${method} ${url}`);
  }

  /**
   * Start a timer; the returned function logs the elapsed time when called.
   * Usage: `const stop = logger.time("generate"); ...; stop();`
   */
  time(label: string): () => void {
    const start = Date.now();
    return () => this.write("TIME ", `${label} took ${Date.now() - start}ms`);
  }

  /** Bring the channel into view (used when reporting an error to the user). */
  show(): void {
    this.channel.show(true);
  }

  dispose(): void {
    this.channel.dispose();
  }

  private write(level: string, message: string): void {
    if (!areLogsEnabled()) {
      return;
    }
    this.channel.appendLine(`[${new Date().toISOString()}] ${level} ${message}`);
  }
}
