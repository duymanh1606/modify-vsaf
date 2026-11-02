#!/usr/bin/env node

/**
 * VDS Skill Pack — credential & config setup
 *
 * Creates ~/.vds/sdlc-config.env template with all required
 * environment variables for vds-skill-* skills.
 *
 * Usage:
 *   node install-deps.mjs [projectPath]
 */

import { existsSync, readFileSync, writeFileSync, mkdirSync, cpSync } from 'fs';
import { join, dirname } from 'path';
import { homedir } from 'os';

const projectPath = process.argv[2] || process.cwd();
const packDir = process.argv[3] || dirname(new URL(import.meta.url).pathname);

// ── Config ──

const VDS_DIR = join(homedir(), '.vds');
const CONFIG_FILE = join(VDS_DIR, 'sdlc-config.env');

const REQUIRED_VARS = [
  { name: 'VDS_CONFLUENCE_TOKEN', desc: 'Confluence personal access token', skills: 'push-prd, push-srs, search-confluence' },
  { name: 'VDS_JIRA_TOKEN', desc: 'Jira personal access token', skills: 'create-jira-epic, search-confluence' },
  { name: 'VDS_BITBUCKET_TOKEN', desc: 'Bitbucket personal access token', skills: 'create-bitbucket-pr' },
  { name: 'VDS_CONFLUENCE_SPACE_DEFAULT', desc: 'Default Confluence space key (e.g. CEP)', skills: 'push-prd, push-srs, search-confluence' },
  { name: 'VDS_JIRA_PROJECT_DEFAULT', desc: 'Default Jira project key (e.g. NTTC)', skills: 'create-jira-epic, search-confluence' },
];

// ── Helpers ──

function log(icon, msg) {
  console.log(`  ${icon} ${msg}`);
}

function parseExistingConfig(filePath) {
  if (!existsSync(filePath)) return {};
  const vars = {};
  for (const line of readFileSync(filePath, 'utf-8').split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eq = trimmed.indexOf('=');
    if (eq > 0) {
      const key = trimmed.slice(0, eq);
      const val = trimmed.slice(eq + 1).replace(/^['"]|['"]$/g, '');
      if (val) vars[key] = val;
    }
  }
  return vars;
}

// ── Step 1: Ensure ~/.vds/ directory ──

console.log('\n[vds-skill] Setting up VDS credentials...\n');

mkdirSync(VDS_DIR, { recursive: true });

// ── Step 2: Create or merge config template ──

const existing = parseExistingConfig(CONFIG_FILE);
const missing = [];
const filled = [];

for (const v of REQUIRED_VARS) {
  if (existing[v.name]) {
    filled.push(v);
  } else {
    missing.push(v);
  }
}

if (!existsSync(CONFIG_FILE)) {
  // Create fresh template
  const lines = [
    '# VDS Skill Pack — credential config',
    '# File: ~/.vds/sdlc-config.env',
    '# Permissions: 600 (auto-set by credentials.sh)',
    '#',
    '# Fill in the values below. Skills will use these automatically.',
    '# To rotate a token: update the value here, skills pick it up next run.',
    '',
  ];

  for (const v of REQUIRED_VARS) {
    lines.push(`# ${v.desc}`);
    lines.push(`# Used by: ${v.skills}`);
    lines.push(`${v.name}=`);
    lines.push('');
  }

  writeFileSync(CONFIG_FILE, lines.join('\n'), { mode: 0o600 });
  log('✅', `Config created: ${CONFIG_FILE}`);
} else if (missing.length > 0) {
  // Append missing vars to existing config
  const appendLines = ['\n# --- Added by vds-skill install ---\n'];
  for (const v of missing) {
    if (!readFileSync(CONFIG_FILE, 'utf-8').includes(v.name)) {
      appendLines.push(`# ${v.desc}`);
      appendLines.push(`# Used by: ${v.skills}`);
      appendLines.push(`${v.name}=`);
      appendLines.push('');
    }
  }
  if (appendLines.length > 1) {
    writeFileSync(CONFIG_FILE, readFileSync(CONFIG_FILE, 'utf-8') + appendLines.join('\n'), { mode: 0o600 });
    log('✅', `Config updated: ${CONFIG_FILE}`);
  }
} else {
  log('✅', `Config already complete: ${CONFIG_FILE}`);
}

// ── Step 3: Print status ──

console.log('');
if (filled.length > 0) {
  log('✅', `${filled.length} credential(s) already configured:`);
  for (const v of filled) {
    log('  ', `${v.name} — ${v.desc}`);
  }
}

if (missing.length > 0) {
  console.log('');
  log('⚠️', `${missing.length} credential(s) need to be filled:`);
  console.log('');
  console.log('  ┌────────────────────────────────────┬──────────────────────────────────────────────┐');
  console.log('  │ Variable                           │ Description                                  │');
  console.log('  ├────────────────────────────────────┼──────────────────────────────────────────────┤');
  for (const v of missing) {
    const name = v.name.padEnd(36);
    const desc = v.desc.padEnd(44);
    console.log(`  │ ${name}│ ${desc}│`);
  }
  console.log('  └────────────────────────────────────┴──────────────────────────────────────────────┘');
  console.log('');
  log('📝', `Edit config file:`);
  console.log(`       ${CONFIG_FILE}`);
  console.log('');
  log('💡', 'Skills will also lazy-prompt at runtime if values are empty.');
}

// ── Step 4: Deploy bundled vds-scripts to project ──

console.log('');
const { execSync } = await import('child_process');

const localVdsScripts = join(projectPath, '.claude', 'vds-scripts');
const globalVdsScripts = join(homedir(), '.claude', 'vds-scripts');
const bundledVdsScripts = join(packDir, 'vds-scripts');

if (!existsSync(localVdsScripts) && existsSync(bundledVdsScripts)) {
  log('📦', 'Deploying bundled vds-scripts to .claude/vds-scripts/ ...');
  try {
    mkdirSync(join(projectPath, '.claude'), { recursive: true });
    cpSync(bundledVdsScripts, localVdsScripts, { recursive: true });
    log('✅', `vds-scripts deployed: ${localVdsScripts}`);
  } catch (e) {
    log('⚠️', `Failed to deploy vds-scripts: ${e.message}`);
  }
} else if (existsSync(localVdsScripts)) {
  log('✅', 'vds-scripts already exists at .claude/vds-scripts/');
}

// Detect vds-scripts location (project-local preferred, then global)
const vdsScriptsDir = existsSync(localVdsScripts) ? localVdsScripts
  : existsSync(globalVdsScripts) ? globalVdsScripts
  : null;

let vdsCliFound = false;

// Check if vds-cli is already on PATH
try {
  const version = execSync('vds-cli --version', { stdio: 'pipe', encoding: 'utf-8' }).trim();
  log('✅', `vds-cli ${version} (on PATH)`);
  vdsCliFound = true;
} catch {
  // Not on PATH — try to create project-local wrapper
}

// Create project-local vds-cli wrapper if vds-scripts exists but vds-cli not on PATH
if (!vdsCliFound && vdsScriptsDir) {
  const wrapperDir = join(projectPath, '.claude', 'bin');
  const wrapperPath = join(wrapperDir, 'vds-cli');
  const uvRunner = join(vdsScriptsDir, 'scripts', 'worktree_uv.sh');

  if (existsSync(uvRunner)) {
    mkdirSync(wrapperDir, { recursive: true });
    const wrapperContent = `#!/usr/bin/env bash
# Project-local vds-cli wrapper — created by vsaf install vds-skill
# Delegates to worktree_uv.sh in the detected vds-scripts directory.
set -euo pipefail
exec "${uvRunner}" run --directory "${vdsScriptsDir}" --package vds-cli vds-cli "$@"
`;
    writeFileSync(wrapperPath, wrapperContent, { mode: 0o755 });
    log('✅', `vds-cli wrapper created: ${wrapperPath}`);
    log('  ', `Points to: ${vdsScriptsDir}`);
    log('💡', 'Add to PATH:  export PATH=".claude/bin:$PATH"');
    vdsCliFound = true;
  }
}

if (!vdsCliFound) {
  log('⚠️', 'vds-cli not found — required for non-dry-run execution');
  log('  ', 'Option 1: Clone vds-scripts into .claude/vds-scripts/ then re-run install');
  log('  ', 'Option 2: Install vds-cli globally (pip install / Viettel internal)');
  log('  ', 'Verify:   command -v vds-cli && vds-cli --version');
}

// ── Step 5: Sync all vds-scripts packages (ensures subcommand binaries exist) ──

if (vdsScriptsDir) {
  log('📂', `vds-scripts: ${vdsScriptsDir}`);
  const uvRunner = join(vdsScriptsDir, 'scripts', 'worktree_uv.sh');
  if (existsSync(uvRunner)) {
    console.log('');
    log('🔄', 'Syncing vds-scripts packages (uv sync --all-packages)...');
    try {
      execSync(`"${uvRunner}" sync --directory "${vdsScriptsDir}" --all-packages`, {
        stdio: 'pipe',
        encoding: 'utf-8',
        timeout: 120000,
        cwd: vdsScriptsDir,
      });
      log('✅', 'All vds-scripts packages synced');
    } catch (e) {
      // Fallback: try direct uv sync
      try {
        execSync('uv sync --all-packages', {
          stdio: 'pipe',
          encoding: 'utf-8',
          timeout: 120000,
          cwd: vdsScriptsDir,
        });
        log('✅', 'All vds-scripts packages synced (direct uv)');
      } catch {
        log('⚠️', 'Failed to sync vds-scripts packages — subcommands like confluence/jira may not work');
        log('  ', `Fix: cd ${vdsScriptsDir} && uv sync --all-packages`);
      }
    }
  }
} else {
  log('⚠️', 'vds-scripts not found at .claude/vds-scripts/ or ~/.claude/vds-scripts/');
}

// ── Step 6: Verify vds-cli actually works (catch broken shims) ──

console.log('');
log('🔍', 'Verifying vds-cli...');

let verified = false;
try {
  const ver = execSync('vds-cli --version', { stdio: 'pipe', encoding: 'utf-8', timeout: 15000 }).trim();
  log('✅', `vds-cli ${ver} — working`);
  verified = true;
} catch {
  // Try with project-local wrapper in PATH
  try {
    const wrapperPath = join(projectPath, '.claude', 'bin');
    const ver = execSync('vds-cli --version', {
      stdio: 'pipe', encoding: 'utf-8', timeout: 15000,
      env: { ...process.env, PATH: `${wrapperPath}:${process.env.PATH}` },
    }).trim();
    log('✅', `vds-cli ${ver} — working (via .claude/bin/vds-cli)`);
    verified = true;
  } catch {
    // Check if a shim exists but is broken
    try {
      const shimPath = execSync('command -v vds-cli', { stdio: 'pipe', encoding: 'utf-8' }).trim();
      log('❌', `vds-cli BROKEN — ${shimPath} exists but fails to run`);
      log('  ', 'The shim likely points to a deleted venv or missing vds-scripts directory.');
      log('  ', `Fix: rm ${shimPath}  then re-run: vsaf install vds-skill`);
    } catch {
      log('❌', 'vds-cli not found');
    }
  }
}

// ── Step 7: Print verification commands for user ──

console.log('');
console.log('  ┌──────────────────────────────────────────────────────┐');
console.log('  │  Verify commands (run these to confirm setup):       │');
console.log('  ├──────────────────────────────────────────────────────┤');
console.log('  │  vds-cli --version          # CLI is executable     │');
console.log('  │  vds-cli confluence --help   # Confluence subcommand │');
console.log('  │  vds-cli jira --help         # Jira subcommand      │');
console.log('  │  vds-cli bitbucket --help    # Bitbucket subcommand │');
console.log('  └──────────────────────────────────────────────────────┘');

if (!verified) {
  console.log('');
  log('⚠️', 'vds-cli is NOT working — skills will be BLOCKED at runtime.');
  log('  ', 'Fix vds-cli first, then run the verify commands above.');
}

console.log('\n[vds-skill] Setup complete ✅\n');
