// Pure composer: structured form fields -> a Markdown requirement the backend
// parser understands. Kept free of the vscode API so it can be unit-tested in
// plain Node (mirrors render.ts).
//
// The backend parser only reads three things (see requirement_parser.py): the
// `# Feature` heading, a `## User Story` section, and `## Acceptance Criteria`
// bullets. Business rules and risks are generated downstream, so they are NOT
// inputs here — collecting them would be misleading.

export interface RequirementInput {
  feature: string;
  userStory: string;
  acceptanceCriteria: string[];
}

export function buildRequirementMarkdown(input: RequirementInput): string {
  const lines: string[] = [`# ${input.feature.trim()}`];

  const story = input.userStory.trim();
  if (story) {
    lines.push("", "## User Story", story);
  }

  const criteria = input.acceptanceCriteria
    .map((c) => c.trim())
    .filter((c) => c.length > 0);
  if (criteria.length) {
    lines.push("", "## Acceptance Criteria", ...criteria.map((c) => `- ${c}`));
  }

  return lines.join("\n") + "\n";
}
