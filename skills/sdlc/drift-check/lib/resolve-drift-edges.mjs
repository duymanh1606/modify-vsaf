import { execFileSync } from 'node:child_process';
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
import yaml from 'js-yaml';

/**
 * For each artifact node, walk `depends_on` backwards through non-artifact
 * (gate) nodes to the nearest artifact ancestor(s). Returns {downstream, upstream}
 * pairs.
 *
 * @param {{ nodes: Array<{ id: string, depends_on?: string[], command?: string, type?: string }> }} graph
 *   Parsed workflow YAML.
 * @param {Set<string>} artifactNodeIds Node ids considered to produce a tracked artifact.
 * @returns {Array<{ downstream: string, upstream: string }>}
 */
export function resolveArtifactEdges(graph, artifactNodeIds) {
  const byId = new Map(graph.nodes.map((n) => [n.id, n]));
  const edges = [];
  for (const node of graph.nodes) {
    if (!artifactNodeIds.has(node.id)) continue;
    const seen = new Set();
    const stack = [...(node.depends_on ?? [])];
    while (stack.length) {
      const depId = stack.pop();
      if (seen.has(depId)) continue;
      seen.add(depId);
      if (artifactNodeIds.has(depId)) {
        edges.push({ downstream: node.id, upstream: depId });
      } else {
        const dep = byId.get(depId);
        for (const up of dep?.depends_on ?? []) stack.push(up);
      }
    }
  }
  return edges;
}

/**
 * Is the upstream artifact's last commit newer than the downstream artifact's
 * last commit? Uses git commit time (NOT filesystem mtime, which is unreliable
 * across git checkout/clone). Degrades safely (returns false) on any git error
 * or when either path has no commit history.
 *
 * @param {string} repoRoot
 * @param {string} downstreamPath
 * @param {string} upstreamPath
 * @returns {boolean}
 */
export function isStale(repoRoot, downstreamPath, upstreamPath) {
  const lastCommitEpoch = (p) => {
    try {
      const out = execFileSync('git', ['log', '-1', '--format=%ct', '--', p], {
        cwd: repoRoot,
        encoding: 'utf8',
        stdio: ['ignore', 'pipe', 'ignore'],
      }).trim();
      return out ? Number(out) : 0;
    } catch {
      return 0;
    }
  };
  const upstreamEpoch = lastCommitEpoch(upstreamPath);
  const downstreamEpoch = lastCommitEpoch(downstreamPath);
  if (upstreamEpoch === 0 || downstreamEpoch === 0) return false;
  return upstreamEpoch > downstreamEpoch;
}

// ── CLI glue (v1: prd / architecture / srs only) ──
//
// Maps a v1 artifact node id to the doc file it produces, per the naming
// convention documented in skills/sdlc/{prd,architecture,srs}/SKILL.md
// §Output (`.vsaf/docs/features/{feature-name}/<filename>`).
const NODE_ARTIFACT_FILENAME = {
  prd: '02-prd.md',
  architecture: '03-adr.md',
  srs: '05-srs.md',
};

/**
 * Finds the on-disk path of a node's artifact doc under
 * `<repoRoot>/.vsaf/docs/features/*\/`. Returns null if the node has no known
 * artifact filename or no feature directory contains it yet (e.g. not
 * written this run) — callers should degrade gracefully (isStale already
 * returns false for missing paths).
 *
 * @param {string} repoRoot
 * @param {string} nodeId
 * @returns {string | null}
 */
function findArtifactPath(repoRoot, nodeId) {
  const filename = NODE_ARTIFACT_FILENAME[nodeId];
  if (!filename) return null;
  const featuresDir = join(repoRoot, '.vsaf', 'docs', 'features');
  if (!existsSync(featuresDir)) return null;
  for (const entry of readdirSync(featuresDir, { withFileTypes: true })) {
    if (!entry.isDirectory()) continue;
    const candidate = join(featuresDir, entry.name, filename);
    if (existsSync(candidate)) return candidate;
  }
  return null;
}

/**
 * CLI entry point: `node resolve-drift-edges.mjs <workflowYamlPath> <artifactNodeIds> <repoRoot>`
 * - workflowYamlPath: path to a workflow YAML (e.g. skills/sdlc/workflows/master-sdlc.yaml)
 * - artifactNodeIds: comma-separated node ids that produce a tracked doc artifact (v1: prd,architecture,srs)
 * - repoRoot: repo root used to resolve artifact files and git history
 *
 * Prints a JSON array of `{ downstream, upstream, stale }` to stdout.
 */
function main() {
  const [workflowPath, artifactIdsArg, repoRoot] = process.argv.slice(2);
  if (!workflowPath || !artifactIdsArg || !repoRoot) {
    console.error(
      'Usage: node resolve-drift-edges.mjs <workflow.yaml> <artifactNodeId1,artifactNodeId2,...> <repoRoot>',
    );
    process.exitCode = 1;
    return;
  }

  const graph = yaml.load(readFileSync(workflowPath, 'utf8'));
  const artifactNodeIds = new Set(
    artifactIdsArg
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean),
  );

  const edges = resolveArtifactEdges(graph, artifactNodeIds);
  const result = edges.map(({ downstream, upstream }) => {
    const downstreamPath = findArtifactPath(repoRoot, downstream);
    const upstreamPath = findArtifactPath(repoRoot, upstream);
    const stale =
      downstreamPath && upstreamPath ? isStale(repoRoot, downstreamPath, upstreamPath) : false;
    return { downstream, upstream, stale };
  });

  console.log(JSON.stringify(result));
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  main();
}
