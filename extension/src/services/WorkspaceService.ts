// All workspace filesystem + active-editor access in one place.
//
// Two rules this enforces:
//  1. NEVER write without explicit user confirmation — every save goes through a
//     Save dialog (which natively confirms overwrites), so we can't clobber a
//     file silently.
//  2. Centralize editor/fs access so the rest of the code doesn't sprinkle
//     vscode.workspace.fs calls around.

import * as vscode from "vscode";

export class WorkspaceService {
  /** Active editor text (selection if any, else whole doc); undefined if none. */
  getActiveText(): string | undefined {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
      return undefined;
    }
    const { selection, document } = editor;
    return selection.isEmpty
      ? document.getText()
      : document.getText(selection);
  }

  /**
   * Save `content` to a file the user chooses. Defaults to
   * <firstWorkspaceFolder>/testcases/<fileName>; the Save dialog confirms any
   * overwrite. Creates the parent folder if needed. Returns the saved Uri, or
   * undefined if the user cancelled.
   */
  async saveArtifact(
    fileName: string,
    content: string
  ): Promise<vscode.Uri | undefined> {
    const target = await vscode.window.showSaveDialog({
      defaultUri: this.defaultUriFor(fileName),
      saveLabel: "Save",
      filters: this.filtersFor(fileName),
    });
    if (!target) {
      return undefined;
    }

    // Ensure the parent directory exists (idempotent, recursive).
    await vscode.workspace.fs.createDirectory(vscode.Uri.joinPath(target, ".."));
    await vscode.workspace.fs.writeFile(
      target,
      new TextEncoder().encode(content)
    );
    return target;
  }

  private defaultUriFor(fileName: string): vscode.Uri | undefined {
    const folder = vscode.workspace.workspaceFolders?.[0];
    return folder
      ? vscode.Uri.joinPath(folder.uri, "testcases", fileName)
      : undefined;
  }

  private filtersFor(fileName: string): { [label: string]: string[] } | undefined {
    const ext = fileName.split(".").pop();
    return ext ? { [ext.toUpperCase()]: [ext] } : undefined;
  }
}
