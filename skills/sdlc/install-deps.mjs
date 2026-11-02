#!/usr/bin/env node

/**
 * SDLC Skill Pack — npm dependency installer
 *
 * Cross-platform (Windows, Linux, macOS).
 * Installs project-local (devDependencies), not global.
 *
 * Usage:
 *   node install-deps.mjs [projectPath]
 *
 * What it does:
 *   1. Ensures package.json exists
 *   2. Checks/installs npm package: gitnexus (includes MCP server built-in)
 *   3. Provisions .mcp.json with GitNexus MCP server entry (npx gitnexus mcp)
 */

import { existsSync, readFileSync, writeFileSync } from 'fs';
import { join } from 'path';
import { execSync } from 'child_process';

const projectPath = process.argv[2] || process.cwd();
const isWin = process.platform === 'win32';

// ── Config ──

const NPM_DEPS = [
  { pkg: 'gitnexus', bin: 'gitnexus' },
];

const MCP_ENTRY = {
  gitnexus: {
    command: 'npx',
    args: ['gitnexus', 'mcp'],
    env: {},
  },
};

// ── Helpers ──

function log(icon, msg) {
  console.log(`  ${icon} ${msg}`);
}

function isInstalled(pkg, bin) {
  const pkgJson = join(projectPath, 'node_modules', ...pkg.split('/'), 'package.json');
  const binPath = join(projectPath, 'node_modules', '.bin', bin);
  const binExists = existsSync(binPath) || (isWin && existsSync(binPath + '.cmd'));
  return existsSync(pkgJson) && binExists;
}

function getVersion(pkg) {
  try {
    const meta = JSON.parse(readFileSync(
      join(projectPath, 'node_modules', ...pkg.split('/'), 'package.json'), 'utf-8'
    ));
    return meta.version || 'unknown';
  } catch { return 'unknown'; }
}

// ── Step 1: Ensure package.json ──

console.log('\n[sdlc-setup] Checking npm dependencies...\n');

if (!existsSync(join(projectPath, 'package.json'))) {
  log('📦', 'No package.json found — creating...');
  execSync('npm init -y', { cwd: projectPath, stdio: 'pipe' });
  log('✅', 'package.json created');
}

// ── Step 2: Check and install npm packages ──

const missing = [];

for (const dep of NPM_DEPS) {
  if (isInstalled(dep.pkg, dep.bin)) {
    log('✅', `${dep.pkg} (${getVersion(dep.pkg)})`);
  } else {
    log('⬇️', `${dep.pkg} — missing, will install`);
    missing.push(dep.pkg);
  }
}

if (missing.length > 0) {
  console.log('');
  log('📦', `Installing ${missing.length} package(s)...`);
  try {
    // --ignore-scripts avoids rebuilding unrelated project deps (e.g. onnxruntime-node)
    // Then rebuild only our deps to run their postinstall scripts
    execSync(`npm install --save-dev --ignore-scripts ${missing.join(' ')}`, {
      cwd: projectPath,
      stdio: 'inherit',
    });
    execSync(`npm rebuild ${missing.join(' ')}`, {
      cwd: projectPath,
      stdio: 'inherit',
    });
    console.log('');
    for (const pkg of missing) {
      const dep = NPM_DEPS.find(d => d.pkg === pkg);
      if (dep && isInstalled(dep.pkg, dep.bin)) {
        log('✅', `${dep.pkg} (${getVersion(dep.pkg)}) — installed`);
      } else {
        log('❌', `${dep.pkg} — install failed`);
      }
    }
  } catch {
    log('❌', 'npm install failed — check network and try again');
    process.exit(1);
  }
} else {
  console.log('');
  log('✅', 'All npm packages already installed');
}

// ── Step 3: Provision .mcp.json ──

console.log('');
console.log('[sdlc-setup] Checking .mcp.json...\n');

const mcpPath = join(projectPath, '.mcp.json');

if (!existsSync(mcpPath)) {
  writeFileSync(mcpPath, JSON.stringify({ mcpServers: MCP_ENTRY }, null, 2) + '\n', 'utf-8');
  log('✅', '.mcp.json created with gitnexus MCP server');
} else {
  try {
    const config = JSON.parse(readFileSync(mcpPath, 'utf-8'));
    if (!config.mcpServers) config.mcpServers = {};
    if (!config.mcpServers.gitnexus) {
      config.mcpServers.gitnexus = MCP_ENTRY.gitnexus;
      writeFileSync(mcpPath, JSON.stringify(config, null, 2) + '\n', 'utf-8');
      log('✅', '.mcp.json — gitnexus MCP server added');
    } else {
      log('✅', '.mcp.json — gitnexus already configured');
    }
  } catch {
    log('⚠️', '.mcp.json — invalid JSON, skipped to avoid data loss');
  }
}

// ── Done ──

console.log('\n[sdlc-setup] npm dependencies ready ✅\n');
console.log('  Next: run `/sdlc-init` to create project structure, then `/sdlc-onboard-code` to index code\n');
