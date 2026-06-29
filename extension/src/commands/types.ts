// Shared dependency bundle passed to every command handler.
//
// Defined in its own module (not index.ts) so handlers and the registrar can
// both import it without a circular dependency. Grows as milestones add
// collaborators (e.g. the sidebar provider, workspace service).

import type { BackendService } from "../services/BackendService";
import type { Logger } from "../utils/logger";
import type { StatusBar } from "../utils/statusBar";

export interface CommandDeps {
  backend: BackendService;
  logger: Logger;
  statusBar: StatusBar;
}
