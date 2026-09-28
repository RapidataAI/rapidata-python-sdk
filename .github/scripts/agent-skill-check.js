// Sets the `Agent Skill` commit status on a PR and keeps its sticky comment in
// sync. Called from .github/workflows/agent-skill.yml via actions/github-script.

const SKILL_DIR = 'src/rapidata/_skill/';
const MARKER = '<!-- agent-skill-check -->';

// Must stay a superset of the paths automerge-openapi-client.yml accepts, or
// the daily generator PR is left with a failing status nobody reviews.
const GENERATED = /^(openapi\/|src\/rapidata\/api_client\/|src\/rapidata\/api_client_README\.md$)/;
const VERSION_BUMP_FILES = new Set(['pyproject.toml', 'src/rapidata/__init__.py']);
const VERSION_BUMP_MESSAGE = /^Bump version from \S+ to \S+/;

function classify(paths, commitMessages) {
  if (paths.some((p) => p.startsWith(SKILL_DIR))) return 'changed';
  if (paths.length > 0 && paths.every((p) => GENERATED.test(p))) return 'generated';
  if (
    paths.length > 0 &&
    paths.every((p) => VERSION_BUMP_FILES.has(p)) &&
    commitMessages.length > 0 &&
    commitMessages.every((m) => VERSION_BUMP_MESSAGE.test(m))
  ) {
    return 'version-bump';
  }
  return 'unchanged';
}

function commentBody(outcome, ackLabel, actor) {
  const how = [
    `This PR does not modify \`${SKILL_DIR}\`. That directory is the agent skill that ships in every SDK release and that coding agents read through \`python -m rapidata skill\`.`,
    '',
    'Before merging, pick one:',
    `1. The change affects what an agent needs to know (new or renamed API, changed parameter, default or result field, new gotcha): update \`${SKILL_DIR}SKILL.md\` (or a companion guide next to it) in this PR.`,
    `2. Nothing the skill documents changed: a reviewer applies the \`${ackLabel}\` label. New commits remove the label again.`,
  ];
  if (outcome === 'acknowledged') {
    return [MARKER, `### ✅ No skill update needed — confirmed by @${actor}`, '', ...how].join('\n');
  }
  if (outcome === 'resolved') {
    return [MARKER, '### ✅ Agent skill check passed', '', 'The skill was updated or the PR only touches generated or release files.'].join('\n');
  }
  return [MARKER, '### ⚠ Agent skill not updated', '', ...how].join('\n');
}

module.exports = async function run({ github, context, core, ackLabel, statusContext }) {
  const { owner, repo } = context.repo;
  const pr = context.payload.pull_request;
  const action = context.payload.action;

  if (action === 'synchronize') {
    try {
      await github.rest.issues.removeLabel({ owner, repo, issue_number: pr.number, name: ackLabel });
      core.info(`Removed ${ackLabel}: new commits need a fresh confirmation.`);
    } catch (e) {
      if (e.status !== 404) throw e;
    }
  }

  const files = await github.paginate(github.rest.pulls.listFiles, { owner, repo, pull_number: pr.number, per_page: 100 });
  const paths = files.flatMap((f) => [f.filename, f.previous_filename].filter(Boolean));
  const commits = await github.paginate(github.rest.pulls.listCommits, { owner, repo, pull_number: pr.number, per_page: 100 });
  const kind = classify(paths, commits.map((c) => c.commit.message));

  const { data: issue } = await github.rest.issues.get({ owner, repo, issue_number: pr.number });
  const labelPresent = issue.labels.some((l) => (typeof l === 'string' ? l : l.name) === ackLabel);

  let state, description, outcome;
  if (kind === 'changed') {
    [state, description, outcome] = ['success', 'Agent skill updated in this PR.', 'resolved'];
  } else if (kind === 'generated') {
    [state, description, outcome] = ['success', 'Generated API client only; no skill update needed.', 'resolved'];
  } else if (kind === 'version-bump') {
    [state, description, outcome] = ['success', 'Release version bump; no skill update needed.', 'resolved'];
  } else if (labelPresent) {
    [state, description, outcome] = ['success', `No skill update needed (${ackLabel}).`, 'acknowledged'];
  } else {
    [state, description, outcome] = ['failure', `Update ${SKILL_DIR}SKILL.md or apply ${ackLabel}.`, 'pending'];
  }

  const comments = await github.paginate(github.rest.issues.listComments, { owner, repo, issue_number: pr.number, per_page: 100 });
  const existing = comments.find((c) => c.body && c.body.includes(MARKER));
  const body = commentBody(outcome, ackLabel, context.actor);
  if (existing) {
    if (existing.body !== body) {
      await github.rest.issues.updateComment({ owner, repo, comment_id: existing.id, body });
    }
  } else if (outcome !== 'resolved') {
    await github.rest.issues.createComment({ owner, repo, issue_number: pr.number, body });
  }

  await github.rest.repos.createCommitStatus({
    owner,
    repo,
    sha: pr.head.sha,
    state,
    context: statusContext,
    description: description.slice(0, 140),
    target_url: `${context.serverUrl}/${owner}/${repo}/actions/runs/${context.runId}`,
  });
  core.info(`${statusContext}: ${state} (${kind}${labelPresent ? ', labeled' : ''})`);
};

module.exports.classify = classify;
