"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.detectRepoScope = detectRepoScope;
exports.removeScopeBlock = removeScopeBlock;
exports.writeScopeBlock = writeScopeBlock;
const fs_1 = require("fs");
const path_1 = require("path");
const backup_js_1 = require("./backup.js");
/**
 * These exact markers are a contract with the pack's pre-commit hook, which reads
 * `repo_type` from between them. Renaming them makes the hook read `unknown` and
 * quietly stop enforcing anything — the block would look right and do nothing.
 */
const BLOCK_BEGIN = '<!-- >>> NTAPP repo scope (auto-managed, edit repo_type only) >>>';
const BLOCK_END = '<!-- <<< NTAPP repo scope <<< -->';
const UI_DEPS = /"(react|next|vue|svelte|@angular\/core|nuxt|remix|astro|solid-js|preact|qwik)"/;
const SERVICE_DEPS = /"(express|fastify|@nestjs\/core|koa|hapi|hono|@hapi\/hapi|restify)"/;
const SERVICE_MANIFESTS = [
    'pom.xml', 'build.gradle', 'build.gradle.kts',
    'go.mod', 'Cargo.toml', 'pyproject.toml', 'requirements.txt',
];
/**
 * Decide whether a repo holds services only, or UI as well.
 *
 * A repo with no telling manifest stays `unknown` rather than being guessed at: the
 * scope decides what the pre-commit rule forbids, and a wrong guess would block
 * legitimate work.
 */
function detectRepoScope(repoPath) {
    let ui = false;
    let service = false;
    let signal = '';
    const packageJson = (0, path_1.join)(repoPath, 'package.json');
    if ((0, fs_1.existsSync)(packageJson)) {
        let manifest = '';
        try {
            manifest = (0, fs_1.readFileSync)(packageJson, 'utf-8');
        }
        catch {
            manifest = '';
        }
        if (UI_DEPS.test(manifest)) {
            ui = true;
            signal = 'package.json with UI framework dependencies';
        }
        if (SERVICE_DEPS.test(manifest)) {
            service = true;
            signal ||= 'package.json with service framework dependencies only';
        }
    }
    if (!service) {
        const found = SERVICE_MANIFESTS.find(manifest => (0, fs_1.existsSync)((0, path_1.join)(repoPath, manifest)));
        if (found) {
            service = true;
            signal ||= `${found} present, no UI dependencies`;
        }
    }
    if (ui)
        return { scope: 'fullstack', signal: signal || 'UI dependencies present' };
    if (service)
        return { scope: 'service-only', signal };
    return { scope: 'unknown', signal: 'no manifest says whether this repo holds UI or services' };
}
const FORBIDDEN = [
    '`Dockerfile`, `docker-compose*.yml`',
    '`.github/workflows/`, `.gitlab-ci.yml`, `Jenkinsfile`, `azure-pipelines.yml`',
    '`helm/`, `chart/`, `k8s/`, `kubernetes/`, `manifests/`',
    '`terraform/`, `*.tf`, `*.tfvars`, `ansible/`',
    '`.devcontainer/`',
];
/**
 * The block body deliberately carries no "detected from X" line. The scope can be
 * corrected by hand, and a stored reason would then contradict the stored value —
 * it also made the block differ between the first and second write. The reason is
 * reported to the caller instead.
 */
function body(scope) {
    if (scope === 'service-only') {
        return [
            '## Repo scope',
            '',
            '`repo_type`: service-only',
            '',
            'Repo này chỉ chứa **mã dịch vụ**. Phần hạ tầng thuộc repo khác của team khác.',
            '**Tác nhân KHÔNG được sinh file thuộc các đường dẫn dưới đây vào repo này** — hook trước khi',
            'commit sẽ chặn:',
            '',
            ...FORBIDDEN.map(line => `- ${line}`),
            '',
            'Cấu hình khung kiểm thử KHÔNG thuộc nhóm bị chặn — đó là mã kiểm thử, không phải hạ tầng.',
            '',
            'Khi tính năng thật sự cần đụng hạ tầng: chuyển cho team chủ repo hạ tầng, không tự sinh ở đây.',
        ];
    }
    if (scope === 'fullstack') {
        return [
            '## Repo scope',
            '',
            '`repo_type`: fullstack',
            '',
            'Repo này chứa cả mã dịch vụ và mã giao diện. Hook trước khi commit KHÔNG chặn đường dẫn hạ tầng.',
        ];
    }
    return [
        '## Repo scope',
        '',
        '`repo_type`: unknown',
        '',
        'Sửa giá trị trên thành `service-only` hoặc `fullstack` nếu biết. Hook trước khi commit KHÔNG chặn',
        'đường dẫn hạ tầng khi giá trị còn là unknown.',
    ];
}
/** The scope currently recorded in the block, if there is one. */
function existingScope(content) {
    const start = content.indexOf(BLOCK_BEGIN);
    const end = content.indexOf(BLOCK_END);
    if (start === -1 || end <= start)
        return null;
    const match = content.slice(start, end).match(/`repo_type`:\s*(service-only|fullstack|unknown)/);
    return match?.[1] ?? null;
}
/**
 * Take the scope block back out, leaving the rest of the file.
 *
 * Separate from removing files the installer created: `CLAUDE.md` belongs to the
 * repo, and deleting it to undo an appended block would destroy the user's own
 * documentation.
 *
 * Returns the file written, or null when there was no block.
 */
function removeScopeBlock(repoPath) {
    const path = (0, path_1.join)(repoPath, 'CLAUDE.md');
    if (!(0, fs_1.existsSync)(path))
        return null;
    const current = (0, fs_1.readFileSync)(path, 'utf-8');
    const start = current.indexOf(BLOCK_BEGIN);
    const end = current.indexOf(BLOCK_END);
    if (start === -1 || end <= start)
        return null;
    const next = (current.slice(0, start) + current.slice(end + BLOCK_END.length)).replace(/\n{3,}$/, '\n');
    // A repo that had no CLAUDE.md got one just to hold this block. Stripping the block
    // would leave an empty husk, which is worth less than no file at all.
    if (next.trim() === '') {
        (0, fs_1.rmSync)(path, { force: true });
        return path;
    }
    (0, fs_1.writeFileSync)(path, next, 'utf-8');
    return path;
}
/**
 * Record what kind of code a repo holds, in a marker block in its `CLAUDE.md`.
 *
 * A scope already written in the block wins over a fresh guess — someone may have
 * corrected it by hand, and detection cannot tell a correction from a stale value.
 * Only `unknown` is re-detected, since that one is an admission of not knowing.
 *
 * Returns the file written, or null when nothing changed.
 */
function writeScopeBlock(repoPath) {
    const path = (0, path_1.join)(repoPath, 'CLAUDE.md');
    const current = (0, fs_1.existsSync)(path) ? (0, fs_1.readFileSync)(path, 'utf-8') : '';
    const recorded = existingScope(current);
    const detected = detectRepoScope(repoPath);
    const scope = recorded && recorded !== 'unknown' ? recorded : detected.scope;
    const block = [BLOCK_BEGIN, ...body(scope), BLOCK_END].join('\n');
    const start = current.indexOf(BLOCK_BEGIN);
    const end = current.indexOf(BLOCK_END);
    let next;
    if (start !== -1 && end > start) {
        next = current.slice(0, start) + block + current.slice(end + BLOCK_END.length);
    }
    else {
        const base = current.length === 0 || current.endsWith('\n') ? current : `${current}\n`;
        next = `${base}${base.length > 0 ? '\n' : ''}${block}\n`;
    }
    if (next === current)
        return null;
    (0, backup_js_1.backupIfModified)(path, next);
    (0, fs_1.writeFileSync)(path, next, 'utf-8');
    return path;
}
//# sourceMappingURL=repo-scope.js.map