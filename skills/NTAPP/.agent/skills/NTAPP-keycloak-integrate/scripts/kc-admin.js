#!/usr/bin/env node
'use strict';

/**
 * kc-admin.js — CLI gọi thẳng Keycloak Admin REST API (generic, dùng cho mọi client/realm).
 * Lý do tồn tại: Admin Console "Partial Import" là hộp đen (nuốt lỗi thật, chỉ toast chung),
 * và không hỗ trợ tốt idempotent. Script gọi REST trực tiếp, in nguyên văn lỗi Keycloak,
 * tạo role/authorization idempotent (chạy lại nhiều lần an toàn).
 *
 * KHÔNG BAO GIỜ ghi access token ra file/log — chỉ giữ trong biến nhớ tiến trình.
 *
 * ENV bắt buộc:
 *   KEYCLOAK_BASE_URL   vd http://devops.digital.vn/keycloak
 *   KEYCLOAK_REALM      vd pmt-staging
 *   KEYCLOAK_ADMIN_USER
 *   KEYCLOAK_ADMIN_PASS
 * ENV tuỳ chọn:
 *   KEYCLOAK_ADMIN_CLIENT_ID   mặc định "admin-cli"
 *   KC_RESOURCE_TYPE           type mặc định cho resource (mặc định "urn:vds:resources:module")
 *
 * Các biến trên có thể đặt trong file .env cạnh skill (xem .env.example) — script TỰ NẠP khi chạy;
 * ENV thật của shell được ưu tiên. KHÔNG commit .env thật (đã có .gitignore).
 *
 * Usage:
 *   node kc-admin.js diagnose            --client <clientId>
 *   node kc-admin.js apply-roles         --client <clientId> --file <partial-import.json>
 *   node kc-admin.js apply-users         --client <clientId> --file <partial-import.json>
 *   node kc-admin.js apply-authz         --client <clientId> --file <authorization.json>
 *   node kc-admin.js run-partial-import  --file <file.json> --if-exists SKIP|OVERWRITE|FAIL
 *
 * Ghi chú dùng trong sandbox có proxy: Node core http/https KHÔNG tự đọc HTTP_PROXY nên đi thẳng
 * (giống curl --noproxy "*"); phù hợp domain nội bộ *.digital.vn bị squid chặn.
 */

// Mốc phiên bản của chính công cụ này. Tăng mỗi khi đổi hành vi apply.
// Bản sao nằm trong các skill khác phải mang cùng chuỗi này. Lệch chuỗi nghĩa là bản sao cũ, không được dùng để apply.
const KC_ADMIN_VERSION = '2026-08-21d';

const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');
const { URL } = require('url');

/**
 * Nạp biến từ file .env (KEY=VALUE) cạnh skill — ưu tiên <skill>/.env, dự phòng <skill>/scripts/.env.
 * ENV thật của shell được GIỮ NGUYÊN (không ghi đè). Không in giá trị (tránh lộ mật khẩu).
 */
function loadDotEnv() {
    const candidates = [path.join(__dirname, '..', '.env'), path.join(__dirname, '.env')];
    for (const envPath of candidates) {
        if (!fs.existsSync(envPath)) continue;
        for (const rawLine of fs.readFileSync(envPath, 'utf8').split(/\r?\n/)) {
            const line = rawLine.trim();
            if (!line || line.startsWith('#')) continue;
            const eq = line.indexOf('=');
            if (eq < 0) continue;
            const key = line.slice(0, eq).trim();
            let val = line.slice(eq + 1).trim();
            if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) val = val.slice(1, -1);
            if (process.env[key] === undefined || process.env[key] === '') process.env[key] = val;
        }
        return envPath;
    }
    return null;
}

function env(name, fallback) {
    const v = process.env[name];
    if (v === undefined || v === '') {
        if (fallback !== undefined) return fallback;
        throw new Error(`Thiếu biến môi trường bắt buộc: ${name}`);
    }
    return v;
}

function httpRequest(urlStr, { method = 'GET', headers = {}, body } = {}) {
    return new Promise((resolve, reject) => {
        const u = new URL(urlStr);
        const lib = u.protocol === 'https:' ? https : http;
        const req = lib.request(
            {
                hostname: u.hostname,
                port: u.port || (u.protocol === 'https:' ? 443 : 80),
                path: u.pathname + u.search,
                method,
                headers
            },
            res => {
                let data = '';
                res.on('data', chunk => (data += chunk));
                res.on('end', () => resolve({ status: res.statusCode, headers: res.headers, raw: data }));
            }
        );
        req.on('error', reject);
        if (body) req.write(body);
        req.end();
    });
}

async function requestJson(urlStr, opts = {}) {
    const res = await httpRequest(urlStr, opts);
    let json = null;
    if (res.raw) {
        try { json = JSON.parse(res.raw); } catch (e) { json = null; }
    }
    return { status: res.status, json, raw: res.raw, headers: res.headers };
}

class KeycloakClient {
    constructor({ baseUrl, realm, token }) {
        this.baseUrl = baseUrl.replace(/\/$/, '');
        this.realm = realm;
        this.token = token;
    }
    static async login({ baseUrl, realm, username, password, clientId = 'admin-cli' }) {
        const tokenUrl = `${baseUrl.replace(/\/$/, '')}/realms/${realm}/protocol/openid-connect/token`;
        const form = new URLSearchParams({ client_id: clientId, grant_type: 'password', username, password }).toString();
        const { status, json, raw } = await requestJson(tokenUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: form
        });
        if (status !== 200 || !json || !json.access_token) {
            throw new Error(`Đăng nhập Keycloak thất bại (HTTP ${status}). Response: ${redact(raw)}`);
        }
        return new KeycloakClient({ baseUrl, realm, token: json.access_token });
    }
    admin(p) { return `${this.baseUrl}/admin/realms/${this.realm}${p}`; }
    authHeaders(extra = {}) { return Object.assign({ Authorization: `Bearer ${this.token}` }, extra); }
    get(p) { return requestJson(this.admin(p), { headers: this.authHeaders() }); }
    post(p, body) { return requestJson(this.admin(p), { method: 'POST', headers: this.authHeaders({ 'Content-Type': 'application/json' }), body: JSON.stringify(body) }); }
    put(p, body) { return requestJson(this.admin(p), { method: 'PUT', headers: this.authHeaders({ 'Content-Type': 'application/json' }), body: JSON.stringify(body) }); }
    del(p) { return requestJson(this.admin(p), { method: 'DELETE', headers: this.authHeaders() }); }
}

/** Ẩn access_token nếu lỡ xuất hiện trong response lỗi. */
function redact(str) {
    if (!str) return str;
    return String(str).replace(/"access_token":"[^"]+"/g, '"access_token":"<redacted>"').slice(0, 2000);
}

async function findClientByClientId(kc, clientId) {
    const { json } = await kc.get(`/clients?clientId=${encodeURIComponent(clientId)}`);
    return Array.isArray(json) && json.length ? json[0] : null;
}
async function listClientRoles(kc, uuid) {
    const { json } = await kc.get(`/clients/${uuid}/roles`);
    return Array.isArray(json) ? json : [];
}
async function listRealmRoles(kc) {
    const { json } = await kc.get('/roles?max=1000');
    return Array.isArray(json) ? json : [];
}
async function ensureRealmRole(kc, role) {
    const found = (await listRealmRoles(kc)).find(r => r.name === role.name);
    if (found) return { created: false, role: found };
    const res = await kc.post('/roles', { name: role.name, description: role.description || '' });
    if (res.status !== 201) throw new Error(`Tạo realm role '${role.name}' thất bại (HTTP ${res.status}): ${redact(res.raw)}`);
    const { json: full } = await kc.get(`/roles/${encodeURIComponent(role.name)}`);
    return { created: true, role: full };
}
/**
 * Bang tra ten role -> id, dung cho role policy. Mot so du an dat quyen o CLIENT role
 * (vd ems-stg: ADMIN/SOC/DEV/BA/CSKH), du an khac dat o REALM role (vd pcm-stg: PCM_ADMIN,
 * PCM_KHAI_BAO). Ham nay tra ve ca hai nguon nen file khai bao khong phai biet role nam o dau.
 *
 * Tra ve { byName, clientByName, realmByName }: 'byName' uu tien CLIENT role (giu nguyen hanh vi
 * truoc day cho cac du an dang chay), realm role chi bu vao nhung ten con thieu. Muon chi dinh
 * dut khoat thi file khai bao dung 'realmRoleNames' thay cho 'roleNames'.
 */
async function buildRoleLookup(kc, uuid) {
    const clientByName = Object.fromEntries((await listClientRoles(kc, uuid)).map(r => [r.name, r.id]));
    const realmByName = Object.fromEntries((await listRealmRoles(kc)).map(r => [r.name, r.id]));
    return { byName: { ...realmByName, ...clientByName }, clientByName, realmByName };
}
async function ensureClientRole(kc, uuid, role) {
    const found = (await listClientRoles(kc, uuid)).find(r => r.name === role.name);
    if (found) return { created: false, role: found };
    const res = await kc.post(`/clients/${uuid}/roles`, { name: role.name, description: role.description || '' });
    if (res.status !== 201) throw new Error(`Tạo role '${role.name}' thất bại (HTTP ${res.status}): ${redact(res.raw)}`);
    const { json: full } = await kc.get(`/clients/${uuid}/roles/${encodeURIComponent(role.name)}`);
    return { created: true, role: full };
}

// ---------------- Authorization Services ----------------
async function listResources(kc, uuid) {
    const { json } = await kc.get(`/clients/${uuid}/authz/resource-server/resource?deep=false&max=500`);
    return Array.isArray(json) ? json : [];
}
async function ensureResource(kc, uuid, res, defaultType) {
    const found = (await listResources(kc, uuid)).find(r => r.name === res.name);
    const payload = {
        name: res.name,
        displayName: res.displayName || res.name,
        type: res.type || defaultType,
        uris: res.uris || [],
        scopes: (res.scopes || []).map(s => ({ name: s }))
    };
    if (found) {
        const id = found._id || found.id;
        const r = await kc.put(`/clients/${uuid}/authz/resource-server/resource/${id}`, payload);
        if (r.status >= 300) throw new Error(`Cập nhật resource '${res.name}' thất bại (HTTP ${r.status}): ${redact(r.raw)}`);
        return { created: false, id };
    }
    const r = await kc.post(`/clients/${uuid}/authz/resource-server/resource`, payload);
    if (r.status !== 201) throw new Error(`Tạo resource '${res.name}' thất bại (HTTP ${r.status}): ${redact(r.raw)}`);
    return { created: true, id: r.json._id || r.json.id };
}
async function listScopes(kc, uuid) {
    const { json } = await kc.get(`/clients/${uuid}/authz/resource-server/scope?max=500`);
    return Array.isArray(json) ? json : [];
}
async function listPolicies(kc, uuid) {
    const { json } = await kc.get(`/clients/${uuid}/authz/resource-server/policy?max=500&permission=false`);
    return Array.isArray(json) ? json : [];
}
/**
 * Role policy cua Keycloak nhan CA realm role LAN client role, va tron duoc trong cung mot policy —
 * o duoi la id role, Keycloak khong quan tam no thuoc realm hay client. Da kiem thuc te: tren cung
 * mot server, policy cua mot du an tro client role con du an khac tro realm role, ca hai deu chay.
 *
 * KHONG lien quan gi den 'app.keycloak.use-resource-role-mappings'. Co do chi quyet dinh adapter dung
 * claim nao de dung Spring authorities (hoac resource_access, hoac realm_access — if/else, khong phai
 * ca hai). Con policy thi Keycloak danh gia o phia server tu role mapping that cua nguoi dung.
 *
 * Ba cach khai, chon theo do chac chan can co:
 *   roleNames[]        - tra ca hai nguon, CLIENT uu tien khi trung ten (tuong thich nguoc)
 *   realmRoleNames[]   - BUOC phai la realm role
 *   clientRoleNames[]  - BUOC phai la client role cua chinh client dang ap
 * Trung ten giua realm role va client role la co that va rat kho thay, nen khi co kha nang do thi
 * dung hai truong sau chu khong dung roleNames.
 */
async function ensureRolePolicy(kc, uuid, pol, roleLookup) {
    const pick = (name, table, nguon) => {
        const id = table[name];
        if (!id) {
            throw new Error(`Policy '${pol.name}' tham chiếu ${nguon} '${name}' chưa tồn tại`
                + ` — tạo role đó trước (client role: chạy apply-roles; realm role: khai roles.realm rồi apply-roles).`);
        }
        return { id, required: false };
    };
    const roles = [
        ...(pol.roleNames || []).map(n => pick(n, roleLookup.byName, 'role')),
        ...(pol.realmRoleNames || []).map(n => pick(n, roleLookup.realmByName, 'realm role')),
        ...(pol.clientRoleNames || []).map(n => pick(n, roleLookup.clientByName, 'client role'))
    ];
    if (!roles.length) {
        throw new Error(`Policy '${pol.name}' không có role nào`
            + ` — khai 'roleNames', 'realmRoleNames' hoặc 'clientRoleNames'.`);
    }
    // Cung mot role khai o hai truong -> Keycloak nhan trung id. Bat som cho de hieu.
    const trung = roles.map(r => r.id).filter((id, i, a) => a.indexOf(id) !== i);
    if (trung.length) {
        throw new Error(`Policy '${pol.name}' khai TRÙNG cùng một role ở nhiều trường`
            + ` (roleNames / realmRoleNames / clientRoleNames) — chỉ khai một chỗ.`);
    }
    const payload = { name: pol.name, description: pol.description || '', logic: pol.logic || 'POSITIVE', roles };
    const existing = (await listPolicies(kc, uuid)).find(p => p.name === pol.name);
    if (existing) {
        const r = await kc.put(`/clients/${uuid}/authz/resource-server/policy/role/${existing.id}`, payload);
        if (r.status >= 300) throw new Error(`Cập nhật policy '${pol.name}' thất bại (HTTP ${r.status}): ${redact(r.raw)}`);
        return { created: false, id: existing.id };
    }
    const r = await kc.post(`/clients/${uuid}/authz/resource-server/policy/role`, payload);
    if (r.status !== 201) throw new Error(`Tạo policy '${pol.name}' thất bại (HTTP ${r.status}): ${redact(r.raw)}`);
    return { created: true, id: r.json.id };
}
async function ensureScopePermission(kc, uuid, perm, resIdByName, scopeIdByName, polIdByName) {
    const resources = (perm.resources || []).map(n => { const id = resIdByName[n]; if (!id) throw new Error(`Permission '${perm.name}' tham chiếu resource '${n}' chưa tồn tại.`); return id; });
    const scopes = (perm.scopes || []).map(n => { const id = scopeIdByName[n]; if (!id) throw new Error(`Permission '${perm.name}' tham chiếu scope '${n}' chưa tồn tại.`); return id; });
    const policies = (perm.policies || []).map(n => { const id = polIdByName[n]; if (!id) throw new Error(`Permission '${perm.name}' tham chiếu policy '${n}' chưa tồn tại.`); return id; });
    const payload = { name: perm.name, description: perm.description || '', decisionStrategy: perm.decisionStrategy || 'AFFIRMATIVE', logic: perm.logic || 'POSITIVE', resources, scopes, policies };
    // Gan theo TYPE ("Apply to resource type" tren Console): permission ap cho MOI resource cung type.
    // Da do thuc te 30/07/2026: RPT sinh ra chuoi "<ten-resource> : <scope>" cho tung resource cung type,
    // nho vay tach resource nho ma so permission KHONG tang. Khong duoc khai kem 'resources'.
    if (perm.resourceType) {
        if (resources.length) throw new Error(`Permission '${perm.name}': khai CA resourceType lan resources — chon MOT trong hai.`);
        payload.resourceType = perm.resourceType;
        delete payload.resources;
    }
    const existing = ((await kc.get(`/clients/${uuid}/authz/resource-server/permission?max=500`)).json || []).find(p => p.name === perm.name);
    if (existing) {
        const r = await kc.put(`/clients/${uuid}/authz/resource-server/permission/scope/${existing.id}`, payload);
        if (r.status >= 300) throw new Error(`Cập nhật permission '${perm.name}' thất bại (HTTP ${r.status}): ${redact(r.raw)}`);
        return { created: false, id: existing.id };
    }
    const r = await kc.post(`/clients/${uuid}/authz/resource-server/permission/scope`, payload);
    if (r.status !== 201) throw new Error(`Tạo permission '${perm.name}' thất bại (HTTP ${r.status}): ${redact(r.raw)}`);
    return { created: true, id: r.json.id };
}

async function deleteResourceByName(kc, uuid, name) {
    const found = (await listResources(kc, uuid)).find(r => r.name === name);
    if (!found) return false;
    const id = found._id || found.id;
    const r = await kc.del(`/clients/${uuid}/authz/resource-server/resource/${id}`);
    if (r.status >= 300) throw new Error(`Xoá resource '${name}' thất bại (HTTP ${r.status}): ${redact(r.raw)}`);
    return true;
}

// ---------------- Validate URI-SPEC ----------------
/**
 * Keycloak lưu `uris` là chuỗi tự do và KHÔNG validate — khai sai cú pháp thì dòng đó im lặng
 * không có tác dụng (PERMIT: lọt quyền / DENY: 403 hàng loạt). Nên kiểm TRƯỚC KHI apply.
 * Cú pháp: <SCOPE-EXPR> <METHODS> <PATH>[?<QUERY>]  (xem keycloak/ems-authz-redesign.md §3.1)
 * PHẢI khớp với vn.com.viettel.vds.keycloak.configuration.UriSpec của vds-keycloak-adapter >= 2.0.0-WEB.
 */
// Ten scope trung HTTP method thi dong vai BO LOC PHUONG THUC (cach doc TAP SCOPE cua lib >= 2.1.0-WEB),
// khong phai quyen nghiep vu. Giu dong bo voi UriSpec.HTTP_METHOD_NAMES.
const HTTP_METHOD_NAMES = new Set(['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS', 'TRACE']);
const isMethodName = s => HTTP_METHOD_NAMES.has(String(s).trim().toUpperCase());

/**
 * Kiem TEN artifact truoc khi cham Keycloak. Ly do rat cu the: da gap tren client pcm-stg mot policy
 * ten 'PCM_THUOC_TINH\t_POLICY' — co ky tu TAB o giua. Tren Console nhin y het ten dung, nen lan sau
 * ai go lai ten do se tao ra ban THU HAI thay vi cap nhat ban cu, va moi lenh xoa theo ten deu truot.
 * Bat luon ca khoang trang dau/cuoi va ky tu dieu khien khac.
 */
function validateArtifactNames(spec) {
    const problems = [];
    const hien = s => JSON.stringify(s);
    const check = (name, loai) => {
        if (typeof name !== 'string' || !name) { problems.push(`${loai} có tên rỗng hoặc không phải chuỗi`); return; }
        if (/[\t\r\n\f\v]/.test(name)) {
            problems.push(`${loai} ${hien(name)}: chứa ký tự trắng lạ (tab/newline) — trên Console trông y hệt`
                + ` tên đúng nhưng là tên KHÁC, mọi lệnh tra/xoá theo tên sẽ trượt.`);
        } else if (name !== name.trim()) {
            problems.push(`${loai} ${hien(name)}: có khoảng trắng ở đầu hoặc cuối tên.`);
        }
    };
    for (const r of spec.resources || []) check(r.name, 'resource');
    for (const p of spec.rolePolicies || []) check(p.name, 'policy');
    for (const p of spec.scopePermissions || []) check(p.name, 'permission');
    // Ben remove thi ky tu la lai HOP LE — do chinh la ten rac dang co tren Keycloak, phai go
    // nguyen van moi xoa duoc. Chi canh bao de nguoi doc biet la co y.
    for (const [khoa, ds] of Object.entries(spec.remove || {})) {
        if (!Array.isArray(ds)) continue;
        for (const n of ds) {
            if (typeof n === 'string' && /[\t\r\n\f\v]/.test(n)) {
                console.log(`[CHU Y] remove.${khoa} có ${hien(n)} — tên chứa ký tự trắng lạ. Đúng là cố ý thì bỏ qua`
                    + ` dòng này, đây là artifact rác đang tồn tại trên Keycloak và phải gõ nguyên văn mới xoá được.`);
            }
        }
    }
    if (problems.length) {
        throw new Error(`Tên artifact không hợp lệ (${problems.length} lỗi) — KHÔNG apply:\n  - ${problems.join('\n  - ')}`);
    }
    console.log('[OK] validate tên artifact: không có ký tự trắng lạ.');
}

function validateUriSpecs(spec) {
    const publicTypes = new Set(spec.publicResourceTypes || ['urn:vds:public']);
    // Bat cach doc TAP SCOPE khi file khai bao noi ro (khop app.authz.scope-set-mode ben backend).
    const scopeSetMode = spec.scopeSetMode === true;
    const problems = [];
    const identity = new Map();

    for (const res of spec.resources || []) {
        const scopes = new Set(res.scopes || []);
        const isPublic = !!(res.type && publicTypes.has(res.type));
        const bizScopes = scopeSetMode && !isPublic ? [...scopes].filter(s => !isMethodName(s)) : [];
        const methodScopes = scopeSetMode && !isPublic ? [...scopes].filter(isMethodName) : [];
        if (methodScopes.length >= 2 && bizScopes.length >= 2) {
            problems.push(`resource '${res.name}' scopes=${JSON.stringify([...scopes])}: có từ 2 tên method VÀ từ 2 tên`
                + ` nghiệp vụ -> KHÔNG suy ra được cặp (method, quyền), lib sẽ BỎ CẢ RESOURCE.`
                + ` Tách thành nhiều resource, mỗi resource một cặp.`);
            continue;
        }
        for (const rawLine of res.uris || []) {
            const line = String(rawLine).trim();
            const where = `resource '${res.name}' uri '${line}'`;
            const tokens = line.split(/\s+/);
            const pathToken = tokens[tokens.length - 1];

            if (tokens.length > 3) {
                problems.push(`${where}: ${tokens.length} token, tối đa 3 (SCOPE METHODS PATH) — có phải để khoảng trắng quanh '|' hoặc '+'?`);
                continue;
            }
            if (!pathToken.startsWith('/')) {
                problems.push(`${where}: token cuối phải là PATH bắt đầu bằng '/' (nhận được '${pathToken}')`);
                continue;
            }
            // Keycloak khong co bien duong dan. AntPathMatcher doc '{id}' la KY TU THUONG nen
            // '/products/{id}/deleted' KHONG BAO GIO khop '/products/123/deleted' -> resource cheat lang.
            // Da gap that: pcm-stg co 2 resource kieu nay ton tai ma chua tung khop request nao.
            const braces = pathToken.match(/\{[^}]*\}/g);
            if (braces) {
                problems.push(`${where}: PATH chứa ${JSON.stringify(braces)} — Keycloak/AntPathMatcher coi đây là`
                    + ` ký tự thường, KHÔNG phải biến, nên dòng này sẽ không bao giờ khớp request thật.`
                    + ` Dùng '*' cho một đoạn (vd '/products/*/deleted') hoặc '**' cho nhiều đoạn.`);
                continue;
            }
            if (isPublic && tokens.length === 3) {
                problems.push(`${where}: resource công khai (type=${res.type}) không cần scope — chỉ khai [METHOD] PATH`);
                continue;
            }

            let methodsKey = '*';
            if (tokens.length >= 2) {
                const mt = tokens[tokens.length - 2];
                if (mt !== '*') {
                    const parts = mt.split(',').map(s => s.trim());
                    if (parts.some(s => !s)) { problems.push(`${where}: danh sách METHODS có phần tử rỗng`); continue; }
                    methodsKey = parts.map(s => s.toUpperCase()).sort().join(',');
                }
            } else if (methodScopes.length) {
                // Cach doc TAP SCOPE: dong 1 token lay bo loc phuong thuc TU scopes[] cua resource.
                // Phai tinh vao khoa nhan dang, neu khong se bao TRUNG sai cho hai resource cung path
                // nhung khac tang method (vd RS_VIEW{VIEW,GET} va RS_WRITE{WRITE,POST}).
                methodsKey = methodScopes.map(s => s.toUpperCase()).sort().join(',');
            }
            if (tokens.length === 1 && !isPublic && scopes.size === 0) {
                problems.push(`${where}: resource không có scope nào -> không enforce được theo scope`);
                continue;
            }
            // Cach doc TAP SCOPE: dong 1-2 token lay quyen tu scopes[] (ten nghiep vu), method tu
            // scopes[] hoac tu chinh dong -> khong con doi "dung 1 scope".
            if (tokens.length === 1 && !isPublic && !scopeSetMode && bizScopes.length === 0
                    && ![...scopes].some(isMethodName)) {
                problems.push(`${where}: dạng 1 token (kiểu cũ) đòi scopes[] chứa tên HTTP method,`
                    + ` hiện ${JSON.stringify([...scopes])}. Nếu muốn dùng cách đọc TẬP SCOPE thì đặt "scopeSetMode": true`
                    + ` trong file khai báo VÀ app.authz.scope-set-mode=true ở backend.`);
                continue;
            }
            if (tokens.length === 2 && !isPublic && bizScopes.length === 0 && scopes.size !== 1) {
                problems.push(`${where}: dạng 2 token đòi resource có ĐÚNG 1 scope nghiệp vụ (hiện ${scopes.size}: ${JSON.stringify([...scopes])})`);
                continue;
            }
            if (tokens.length === 3) {
                const st = tokens[0];
                const hasOr = st.includes('|');
                const hasAnd = st.includes('+');
                if (hasOr && hasAnd) { problems.push(`${where}: KHÔNG được trộn '|' với '+' trong một biểu thức scope`); continue; }
                const names = st.split(hasAnd ? '+' : '|').map(s => s.trim());
                if (names.some(n => !n)) { problems.push(`${where}: biểu thức scope có phần tử rỗng`); continue; }
                const missing = names.filter(n => !scopes.has(n));
                if (missing.length) {
                    problems.push(`${where}: scope ${JSON.stringify(missing)} không nằm trong scopes của resource ${JSON.stringify([...scopes])}`);
                    continue;
                }
            }

            const q = pathToken.indexOf('?');
            const pathPattern = q < 0 ? pathToken : pathToken.slice(0, q);
            if (!pathPattern) { problems.push(`${where}: PATH rỗng`); continue; }
            let badQuery = false;
            const qpairs = [];
            if (q >= 0) {
                for (const pair of pathToken.slice(q + 1).split('&')) {
                    const t = pair.trim();
                    if (!t) continue;
                    if (t.indexOf('=') <= 0) { problems.push(`${where}: điều kiện query '${t}' phải có dạng k=v`); badQuery = true; break; }
                    qpairs.push(t);
                }
            }
            if (badQuery) continue;
            qpairs.sort();

            const key = `${pathPattern}|${methodsKey}|${qpairs.join('&')}`;
            if (!identity.has(key)) identity.set(key, []);
            identity.get(key).push(`${res.name} -> '${line}'`);
        }
    }

    for (const [key, where] of identity) {
        if (where.length > 1) {
            problems.push(`KHAI TRÙNG cùng một mẫu [${key}] tại ${where.join(' , ')}`
                + ` -> các dòng này sẽ bị AND (đòi hỏi CÓ TẤT CẢ), chặn ngoài ý muốn.`
                + ` Muốn 'hoặc' thì viết TRÊN MỘT DÒNG bằng toán tử '|'.`);
        }
    }
    if (problems.length) {
        throw new Error(`Khai báo URI-SPEC không hợp lệ (${problems.length} lỗi) — KHÔNG apply:\n  - ${problems.join('\n  - ')}`);
    }
    console.log(`[OK] validate URI-SPEC: ${identity.size} luật khớp, không có lỗi cú pháp / khai trùng.`);
}

/**
 * Kiem phan DAY NOI permission -> policy (khong lien quan cu phap uris):
 *  1. policy duoc tham chieu phai co trong file (bat loi go sai TRUOC khi cham Keycloak);
 *  2. permission tro TU 2 POLICY TRO LEN thi decisionStrategy PHAI la AFFIRMATIVE. Voi kieu khai
 *     "policy = mot role" (danh sach ai-duoc-lam-gi nam o permission), de UNANIMOUS nghia la doi
 *     nguoi dung phai co DU CA 4-5 role cung luc -> CHAN SACH, ma log chi noi "thieu quyen".
 *     Console mac dinh UNANIMOUS khi tao permission tay nen day la loi rat de xay ra;
 *  3. invariants.samePolicies: cac nhom permission PHAI co cung tap policy. Dung khi mot tang quyen
 *     duoc nhieu permission dung chung (vd 4 permission *_APPROVE): ban khai theo tang co MOT policy
 *     dung chung nen sua mot cho la du, ban khai theo role thi phai sua tung permission -> bo sot mot
 *     cai la role do van lam duoc tren menu do. Khai bat bien de may canh thay nguoi.
 */
function validatePermissionWiring(spec) {
    const problems = [];
    const polNames = new Set((spec.rolePolicies || []).map(p => p.name));
    const permByName = new Map();

    for (const perm of spec.scopePermissions || []) {
        permByName.set(perm.name, perm);
        const pols = perm.policies || [];
        for (const pn of pols) {
            if (!polNames.has(pn)) problems.push(`permission '${perm.name}' tham chiếu policy '${pn}' không có trong file`);
        }
        const strategy = perm.decisionStrategy || 'AFFIRMATIVE';
        if (pols.length >= 2 && strategy !== 'AFFIRMATIVE') {
            problems.push(`permission '${perm.name}' trỏ ${pols.length} policy nhưng decisionStrategy='${strategy}'`
                + ` — phải là AFFIRMATIVE (= HOẶC). '${strategy}' đòi thoả ĐỒNG THỜI mọi policy ⇒ chặn sạch.`);
        }
    }

    for (const group of (spec.invariants || {}).samePolicies || []) {
        const missing = group.filter(n => !permByName.has(n));
        if (missing.length) {
            problems.push(`invariants.samePolicies nêu permission không có trong file: ${JSON.stringify(missing)}`);
            continue;
        }
        const sets = new Map();
        for (const n of group) sets.set(n, JSON.stringify([...(permByName.get(n).policies || [])].sort()));
        const distinct = new Set(sets.values());
        if (distinct.size > 1) {
            problems.push(`invariants.samePolicies: nhóm ${JSON.stringify(group)} phải có CÙNG tập policy, hiện lệch:\n      `
                + [...sets].map(([n, v]) => `${n} -> ${v}`).join('\n      '));
        }
    }

    if (problems.length) {
        throw new Error(`Dây nối permission → policy không hợp lệ (${problems.length} lỗi) — KHÔNG apply:\n  - ${problems.join('\n  - ')}`);
    }
    const nInv = ((spec.invariants || {}).samePolicies || []).length;
    console.log(`[OK] validate permission → policy: ${(spec.scopePermissions || []).length} permission,`
        + ` mọi permission nhiều policy đều AFFIRMATIVE${nInv ? `, ${nInv} bất biến samePolicies đạt` : ''}.`);
}

// ---------------- Commands ----------------
async function cmdDiagnose(kc, { client }) {
    console.log(`== Realm: ${kc.realm}  Client: ${client}`);
    const c = await findClientByClientId(kc, client);
    if (!c) { console.log(`Client '${client}' CHƯA tồn tại — tạo trên Console (bật Authorization Services) rồi chạy lại.`); return; }
    console.log(`Client đã tồn tại: id=${c.id}  authorizationServicesEnabled=${c.authorizationServicesEnabled}  directAccessGrantsEnabled=${c.directAccessGrantsEnabled}`);
    const roles = await listClientRoles(kc, c.id);
    console.log(`  Client roles (${roles.length}):`, roles.map(r => r.name).join(', ') || '(none)');
    if (c.authorizationServicesEnabled) {
        const resources = await listResources(kc, c.id);
        const policies = await listPolicies(kc, c.id);
        console.log(`  Resources (${resources.length}):`, resources.map(r => r.name).join(', ') || '(none)');
        console.log(`  Policies (${policies.length}):`, policies.map(r => r.name).join(', ') || '(none)');
    }
}
async function cmdApplyRoles(kc, { client, file }) {
    const spec = JSON.parse(fs.readFileSync(file, 'utf8'));
    const clientRoles = (spec.roles && spec.roles.client && spec.roles.client[client]) || [];
    // roles.realm[]: dung cho du an dat quyen o REALM role thay vi client role (vd pcm-stg dung
    // PCM_ADMIN / PCM_KHAI_BAO / PCM_SOC). Tao role la viec CO Y va tach rieng — apply-authz KHONG
    // tu tao role tu file khai bao, vi go sai mot ky tu se am tham sinh ra role moi.
    const realmRoles = (spec.roles && spec.roles.realm) || [];
    if (!clientRoles.length && !realmRoles.length) {
        throw new Error(`File ${file} không có roles.client.${client} lẫn roles.realm`);
    }
    for (const role of realmRoles) {
        const { created } = await ensureRealmRole(kc, role);
        console.log(`${created ? '[CREATED]' : '[SKIP-EXISTS]'} realm-role ${role.name}`);
    }
    if (!clientRoles.length) return;
    const c = await findClientByClientId(kc, client);
    if (!c) throw new Error(`Client '${client}' chưa tồn tại — tạo trước rồi chạy lại.`);
    for (const role of clientRoles) {
        const { created } = await ensureClientRole(kc, c.id, role);
        console.log(`${created ? '[CREATED]' : '[SKIP-EXISTS]'} client-role ${role.name}`);
    }
}
async function cmdApplyUsers(kc, { client, file }) {
    const spec = JSON.parse(fs.readFileSync(file, 'utf8'));
    const users = spec.users || [];
    if (!users.length) throw new Error(`File ${file} không có users`);
    const c = await findClientByClientId(kc, client);
    if (!c) throw new Error(`Client '${client}' chưa tồn tại.`);
    const roleByName = Object.fromEntries((await listClientRoles(kc, c.id)).map(r => [r.name, r]));
    for (const u of users) {
        const { json: existing } = await kc.get(`/users?username=${encodeURIComponent(u.username)}&exact=true`);
        let userId;
        if (Array.isArray(existing) && existing.length) {
            userId = existing[0].id;
            console.log(`[SKIP-EXISTS] user ${u.username}`);
        } else {
            const r = await kc.post('/users', { username: u.username, enabled: u.enabled !== false, emailVerified: !!u.emailVerified, firstName: u.firstName, lastName: u.lastName, email: u.email, credentials: u.credentials });
            if (r.status !== 201) throw new Error(`Tạo user '${u.username}' thất bại (HTTP ${r.status}): ${redact(r.raw)}`);
            const { json: created } = await kc.get(`/users?username=${encodeURIComponent(u.username)}&exact=true`);
            userId = created[0].id;
            console.log(`[CREATED] user ${u.username}`);
        }
        const want = (u.clientRoles && u.clientRoles[client]) || [];
        const toAssign = want.map(n => roleByName[n]).filter(Boolean).map(r => ({ id: r.id, name: r.name }));
        if (toAssign.length) {
            const r = await kc.post(`/users/${userId}/role-mappings/clients/${c.id}`, toAssign);
            if (r.status >= 300 && r.status !== 409) throw new Error(`Gán role cho '${u.username}' thất bại (HTTP ${r.status}): ${redact(r.raw)}`);
            console.log(`  -> gán role: ${toAssign.map(r => r.name).join(', ')}`);
        }
    }
}
async function cmdApplyAuthz(kc, { client, file }) {
    const spec = JSON.parse(fs.readFileSync(file, 'utf8'));
    const defaultType = env('KC_RESOURCE_TYPE', 'urn:vds:resources:module');
    validateArtifactNames(spec);
    validateUriSpecs(spec);
    validatePermissionWiring(spec);
    const c = await findClientByClientId(kc, client);
    if (!c) throw new Error(`Client '${client}' chưa tồn tại.`);
    if (!c.authorizationServicesEnabled) throw new Error(`Client '${client}' chưa bật Authorization Services (Settings > Capability config).`);

    // THU TU CO Y — dung doi:
    //  1) xoa permission cu  2) xoa policy cu  3) ensure resource  4) ensure policy
    //  5) ensure permission  6) xoa resource cu (CUOI CUNG)
    // Vi sao xoa permission TRUOC khi ensure resource: ensure resource ghi de scopes[]; neu permission
    // cu con tro tap (resource, scope) ma scope do bi go khoi resource thi trang thai treo/khong xac dinh.
    // Vi sao xoa resource CUOI: xoa resource khi con permission/policy tro toi no se loi.
    const rm = spec.remove || {};
    for (const name of (rm.permissions || [])) {
        const found = ((await kc.get(`/clients/${c.id}/authz/resource-server/permission?max=500`)).json || []).find(p => p.name === name);
        if (!found) { console.log(`[SKIP-ABSENT] permission ${name}`); continue; }
        const r = await kc.del(`/clients/${c.id}/authz/resource-server/policy/${found.id}`);
        if (r.status >= 300) throw new Error(`Xoá permission '${name}' thất bại (HTTP ${r.status}): ${redact(r.raw)}`);
        console.log(`[DELETED] permission ${name}`);
    }
    for (const name of (rm.policies || [])) {
        const found = (await listPolicies(kc, c.id)).find(p => p.name === name);
        if (!found) { console.log(`[SKIP-ABSENT] policy ${name}`); continue; }
        const r = await kc.del(`/clients/${c.id}/authz/resource-server/policy/${found.id}`);
        if (r.status >= 300) throw new Error(`Xoá policy '${name}' thất bại (HTTP ${r.status}): ${redact(r.raw)}`);
        console.log(`[DELETED] policy ${name}`);
    }

    for (const res of spec.resources || []) {
        const { created } = await ensureResource(kc, c.id, res, defaultType);
        console.log(`${created ? '[CREATED]' : '[UPDATED]'} resource ${res.name}`);
    }
    const roleLookup = await buildRoleLookup(kc, c.id);
    const resIdByName = Object.fromEntries((await listResources(kc, c.id)).map(r => [r.name, r._id || r.id]));
    const scopeIdByName = Object.fromEntries((await listScopes(kc, c.id)).map(s => [s.name, s.id]));
    const polIdByName = {};
    for (const pol of spec.rolePolicies || []) {
        const { created, id } = await ensureRolePolicy(kc, c.id, pol, roleLookup);
        polIdByName[pol.name] = id;
        console.log(`${created ? '[CREATED]' : '[UPDATED]'} role-policy ${pol.name}`);
    }
    for (const perm of spec.scopePermissions || []) {
        const { created } = await ensureScopePermission(kc, c.id, perm, resIdByName, scopeIdByName, polIdByName);
        console.log(`${created ? '[CREATED]' : '[UPDATED]'} scope-permission ${perm.name}`);
    }
    // Resource xoá CUỐI CÙNG (permission/policy cũ đã xoá ở đầu hàm).
    // BẮT BUỘC phải xoá hết resource cũ — resource sót lại vẫn nằm trong catalog mà filter nạp,
    // trùng mẫu với dòng mới -> rơi vào luật AND -> chặn cứng (xem ems-authz-redesign.md §3.2b).
    for (const name of (rm.resources || [])) {
        const deleted = await deleteResourceByName(kc, c.id, name);
        console.log(`${deleted ? '[DELETED]' : '[SKIP-ABSENT]'} resource ${name}`);
    }
}
async function cmdRunPartialImport(kc, { file, ifExists }) {
    const body = JSON.parse(fs.readFileSync(file, 'utf8'));
    body.ifResourceExists = ifExists || 'FAIL';
    const res = await kc.post('/partialImport', body);
    console.log(`HTTP ${res.status}`);
    console.log(res.json ? JSON.stringify(res.json, null, 2) : (redact(res.raw) || '(empty body)'));
    if (res.status >= 300) throw new Error('partialImport thất bại — xem chi tiết ở trên.');
}

/** Khoá của bản ghi client mà Keycloak tự tính lúc đọc, hoặc gắn với vòng đời của chính bản ghi cũ. */
const CLIENT_KEYS_TO_DROP = ['id', 'secret', 'protocolMappers', 'defaultClientScopes', 'optionalClientScopes',
    'registrationAccessToken', 'authorizationSettings', 'origin', 'access'];
/** Ba bản ghi Keycloak tự sinh khi bật Authorization Services. Bản Default Policy là kiểu js có mã nhúng,
 *  mà các bản Keycloak mới đã bỏ đường nạp script từ ngoài vào, nên mang theo là tự chuốc lỗi nạp tệp. */
const AUTHZ_DEFAULT_RECORDS = ['Default Resource', 'Default Policy', 'Default Permission'];
/** Vai trò Keycloak tự tạo kèm Authorization Services, không cần khai lại. */
const AUTO_CREATED_ROLE = 'uma_protection';
const CLIENT_ID_PLACEHOLDER = '__CLIENT_ID__';

/** Thay tên client nguồn bằng tên đích ở mọi vị trí, kể cả chỗ nằm chìm trong chuỗi lồng. */
function retargetClientId(value, sourceClientId, targetClientId) {
    return JSON.parse(JSON.stringify(value).split(sourceClientId).join(targetClientId));
}

function stripClientRepresentation(clientRep) {
    const out = {};
    for (const [key, val] of Object.entries(clientRep)) {
        if (!CLIENT_KEYS_TO_DROP.includes(key)) out[key] = val;
    }
    if (out.attributes) delete out.attributes['client.secret.creation.time'];
    return out;
}

/** Gom người dùng theo từng vai trò của client rồi dồn về một danh sách, mỗi người một bản ghi. */
async function collectUsersByClientRoles(kc, uuid, roleNames) {
    const byUsername = new Map();
    for (const roleName of roleNames) {
        const { json } = await kc.get(`/clients/${uuid}/roles/${encodeURIComponent(roleName)}/users?max=1000`);
        for (const u of (Array.isArray(json) ? json : [])) {
            if (!byUsername.has(u.username)) byUsername.set(u.username, { user: u, roles: [] });
            byUsername.get(u.username).roles.push(roleName);
        }
    }
    return byUsername;
}

function buildUserRepresentation(entry, targetClientId, password) {
    const u = entry.user;
    const rep = {
        username: u.username,
        enabled: u.enabled !== false,
        emailVerified: u.emailVerified === true
    };
    if (u.firstName) rep.firstName = u.firstName;
    if (u.lastName) rep.lastName = u.lastName;
    if (u.email) rep.email = u.email;
    if (password) rep.credentials = [{ type: 'password', value: password, temporary: false }];
    rep.clientRoles = { [targetClientId]: entry.roles };
    return rep;
}

/**
 * Xuất cấu hình của một client đang chạy thành bộ tệp nạp tay được trên Console.
 * Sinh tối đa ba tệp — client kèm vai trò, client kèm vai trò kèm người dùng, và phần phân quyền.
 * Tên client được thay bằng chỗ giữ chỗ để tệp dùng lại được ở môi trường đặt tên khác.
 */
/**
 * Bỏ tiền tố khỏi tên vai trò trên toàn bộ kết quả xuất.
 * Đổi cả tên vai trò lẫn mọi chỗ nhắc tới nó, gồm tên policy có nhúng tên vai trò
 * và chuỗi định danh nằm chìm trong cấu hình của role policy.
 * Trả về bảng đổi tên để in ra cho người dùng đối chiếu.
 */
function buildRoleRenameMap(roleNames, prefix) {
    const map = new Map();
    for (const name of roleNames) {
        if (!name.startsWith(prefix)) continue;
        const stripped = name.slice(prefix.length);
        if (!stripped) throw new Error(`Bỏ tiền tố '${prefix}' khỏi vai trò '${name}' thì còn chuỗi rỗng.`);
        if (roleNames.includes(stripped)) throw new Error(`Bỏ tiền tố sẽ làm vai trò '${name}' trùng tên với vai trò '${stripped}' đã có.`);
        map.set(name, stripped);
    }
    return map;
}

function applyRoleRename(value, renameMap) {
    if (!renameMap.size) return value;
    let text = JSON.stringify(value);
    // Đổi tên dài trước để tên ngắn không cắt mất phần đuôi của tên dài.
    for (const [from, to] of [...renameMap].sort((a, b) => b[0].length - a[0].length)) {
        text = text.split(from).join(to);
    }
    return JSON.parse(text);
}
/**
 * Bỏ định danh do Keycloak nguồn cấp phát khỏi phần phân quyền.
 * Các mã này trỏ về resource server của chính bản ghi cũ nên sang nơi khác là vô nghĩa,
 * và giữ lại thì lần nạp ở môi trường mới bị từ chối. Keycloak tự cấp mã mới khi tạo.
 * Liên kết giữa các bản ghi đi bằng TÊN nên bỏ mã không làm mất quan hệ nào.
 */
function stripAuthzIdentifiers(authz) {
    for (const r of (authz.resources || [])) { delete r._id; delete r.id; }
    for (const p of (authz.policies || [])) { delete p.id; }
    for (const sc of (authz.scopes || [])) { delete sc.id; delete sc.iconUri; }
    return authz;
}
async function cmdExportClient(kc, { client, out, newClientId, users, userPassword, excludeRoles, prefix, userFilter, stripRolePrefix }) {
    const c = await findClientByClientId(kc, client);
    if (!c) throw new Error(`Client '${client}' chưa tồn tại trên realm ${kc.realm}.`);
    const target = newClientId || CLIENT_ID_PLACEHOLDER;
    const outDir = out || process.cwd();
    if (!fs.existsSync(outDir)) throw new Error(`Thư mục đích không tồn tại: ${outDir}`);
    const base = prefix || target;
    const mode = users || 'both';
    if (!['yes', 'no', 'both'].includes(mode)) throw new Error(`--users chỉ nhận yes, no hoặc both. Nhận được: ${mode}`);

    const skipRoles = new Set([AUTO_CREATED_ROLE, ...(excludeRoles ? String(excludeRoles).split(',').map(s => s.trim()).filter(Boolean) : [])]);
    const allRoles = await listClientRoles(kc, c.id);
    const roles = allRoles.filter(r => !skipRoles.has(r.name))
        .map(r => ({ name: r.name, description: r.description || '', clientRole: true }))
        .sort((a, b) => a.name.localeCompare(b.name));
    const skipped = allRoles.map(r => r.name).filter(n => skipRoles.has(n));
    const renameMap = stripRolePrefix ? buildRoleRenameMap(roles.map(r => r.name), stripRolePrefix) : new Map();

    const clientRep = applyRoleRename(retargetClientId(stripClientRepresentation(c), client, target), renameMap);
    const rolesBlock = { client: { [target]: applyRoleRename(retargetClientId(roles, client, target), renameMap) } };
    const written = [];

    const writeJson = (name, body) => {
        const p = path.join(outDir, name);
        fs.writeFileSync(p, JSON.stringify(body, null, 2) + '\n', 'utf8');
        written.push(p);
        return p;
    };

    if (mode === 'no' || mode === 'both') {
        writeJson(`${base}-partial-import-no-user.json`, { clients: [clientRep], roles: rolesBlock });
    }
    let exportedUsers = [];
    let skippedByFilter = 0;
    if (mode === 'yes' || mode === 'both') {
        const collected = await collectUsersByClientRoles(kc, c.id, roles.map(r => r.name));
        let entries = [...collected.values()];
        const totalFound = entries.length;
        if (userFilter) {
            const re = new RegExp(userFilter);
            entries = entries.filter(e => re.test(e.user.username));
        }
        skippedByFilter = totalFound - entries.length;
        entries.sort((a, b) => a.user.username.localeCompare(b.user.username));
        entries.forEach(e => e.roles.sort());
        exportedUsers = applyRoleRename(entries.map(e => buildUserRepresentation(e, target, userPassword)), renameMap);
        writeJson(`${base}-partial-import-with-user.json`, { clients: [clientRep], roles: rolesBlock, users: exportedUsers });
    }

    const authz = (await kc.get(`/clients/${c.id}/authz/resource-server/settings`)).json || {};
    delete authz.id; delete authz.clientId; delete authz.name;
    authz.resources = (authz.resources || []).filter(r => !AUTHZ_DEFAULT_RECORDS.includes(r.name));
    authz.policies = (authz.policies || []).filter(p => !AUTHZ_DEFAULT_RECORDS.includes(p.name));
    stripAuthzIdentifiers(authz);
    const authzOut = applyRoleRename(retargetClientId(authz, client, target), renameMap);
    // Nạp tệp này vào chính client nguồn sẽ ghi đè role policy bằng tên của môi trường đích,
    // làm mọi permission trỏ tới vai trò không tồn tại. Ghi cảnh báo vào đầu tệp để người mở ra nhìn thấy.
    writeJson(`${base}-authz-export.json`, authzOut);

    console.log(`Nguồn: client '${client}' trên realm ${kc.realm}`);
    console.log(`Tên client trong tệp: ${target}${newClientId ? '' : '  (chỗ giữ chỗ — phải thay trước khi nạp)'}`);
    console.log(`Vai trò xuất ra (${roles.length}): ${roles.map(r => r.name).join(', ') || '(không có)'}`);
    if (skipped.length) console.log(`Vai trò bỏ qua: ${skipped.join(', ')}`);
    if (renameMap.size) console.log(`Đổi tên vai trò: ${[...renameMap].map(([a, b]) => a + ' -> ' + b).join(', ')}`);
    const permCount = (authz.policies || []).filter(p => p.type === 'scope').length;
    console.log(`Phân quyền: ${(authz.resources || []).length} resource, ${(authz.policies || []).length} policy (${permCount} permission), ${(authz.scopes || []).length} scope`);
    if (mode === 'yes' || mode === 'both') {
        console.log(`Người dùng xuất ra (${exportedUsers.length}): ${exportedUsers.map(u => u.username).join(', ') || '(không có)'}`);
        if (skippedByFilter) console.log(`Bộ lọc đã loại ${skippedByFilter} người dùng không khớp.`);
        console.log('CẢNH BÁO: đây là MỌI người dùng đang mang vai trò của client, gồm cả tài khoản nhân viên thật.');
        console.log('          Rà lại danh sách trước khi lưu tệp vào kho mã. Lọc bớt bằng --user-filter với biểu thức chính quy trên tên đăng nhập.');
        if (!userPassword) {
            console.log('CẢNH BÁO: Keycloak không bao giờ trả mật khẩu ra ngoài, nên các người dùng này xuất ra KHÔNG có mật khẩu.');
            console.log('          Người nạp phải tự đặt lại, hoặc chạy lại kèm --user-password để đóng sẵn một mật khẩu dùng chung cho môi trường thử.');
        }
    }
    const referencedRoles = new Set();
    for (const p of (authz.policies || [])) {
        if (p.type !== 'role' || !p.config || !p.config.roles) continue;
        try {
            for (const entry of JSON.parse(p.config.roles)) {
                const id = String(entry.id || '');
                referencedRoles.add(id.includes('/') ? id.slice(id.indexOf('/') + 1) : id);
            }
        } catch (e) { /* cấu hình hỏng thì bỏ qua, phần validate lo việc báo lỗi */ }
    }
    const unreferenced = roles.map(r => r.name).filter(n => !referencedRoles.has(n));
    if (unreferenced.length) {
        console.log(`GHI CHÚ: vai trò không được policy nào tham chiếu: ${unreferenced.join(', ')}. Cân nhắc bỏ bằng --exclude-roles.`);
    }
    console.log('CẢNH BÁO: bộ tệp này nhắm client ' + target + '. Nạp vào client nguồn hoặc client khác sẽ ghi đè role policy của nơi đó và làm mất sạch phân quyền.');
    console.log('Đã ghi:');
    written.forEach(p => console.log('  ' + p));
}

function parseArgs(argv) {
    const out = {};
    for (let i = 0; i < argv.length; i++) {
        if (argv[i].startsWith('--')) {
            const key = argv[i].slice(2);
            const val = argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[++i] : true;
            out[key] = val;
        }
    }
    return out;
}

async function main() {
    console.log(`kc-admin.js v${KC_ADMIN_VERSION}`);
    const envFile = loadDotEnv();
    if (envFile) console.log(`(đã nạp biến môi trường từ ${envFile})`);
    const [, , command, ...rest] = process.argv;
    const args = parseArgs(rest);
    if (!command) {
        console.log('Usage: node kc-admin.js <diagnose|validate-authz|export-client|apply-roles|apply-users|apply-authz|run-partial-import> [--client <id>] [--file <path>] [--if-exists SKIP|OVERWRITE|FAIL]');
        console.log('  export-client --client <id> [--out <dir>] [--new-client-id <ten>] [--users yes|no|both] [--user-password <pwd>] [--exclude-roles <a,b>] [--user-filter <regex>] [--strip-role-prefix <tien-to>] [--prefix <ten>]');
        process.exit(1);
    }
    // validate-authz: kiểm cú pháp URI-SPEC của file, KHÔNG cần mạng / không đăng nhập Keycloak.
    if (command === 'validate-authz') {
        const f = path.resolve(process.cwd(), args.file);
        const spec = JSON.parse(fs.readFileSync(f, 'utf8'));
        validateArtifactNames(spec);
        validateUriSpecs(spec);
        validatePermissionWiring(spec);
        return;
    }
    const kc = await KeycloakClient.login({
        baseUrl: env('KEYCLOAK_BASE_URL'), realm: env('KEYCLOAK_REALM'),
        username: env('KEYCLOAK_ADMIN_USER'), password: env('KEYCLOAK_ADMIN_PASS'),
        clientId: env('KEYCLOAK_ADMIN_CLIENT_ID', 'admin-cli')
    });
    const file = args.file ? path.resolve(process.cwd(), args.file) : null;
    switch (command) {
        case 'diagnose': await cmdDiagnose(kc, { client: args.client }); break;
        case 'apply-roles': await cmdApplyRoles(kc, { client: args.client, file }); break;
        case 'apply-users': await cmdApplyUsers(kc, { client: args.client, file }); break;
        case 'apply-authz': await cmdApplyAuthz(kc, { client: args.client, file }); break;
        case 'run-partial-import': await cmdRunPartialImport(kc, { file, ifExists: args['if-exists'] }); break;
        case 'export-client': await cmdExportClient(kc, { client: args.client, out: args.out, newClientId: args['new-client-id'], users: args.users, userPassword: args['user-password'], excludeRoles: args['exclude-roles'], prefix: args.prefix, userFilter: args['user-filter'], stripRolePrefix: args['strip-role-prefix'] }); break;
        default: throw new Error(`Lệnh không hỗ trợ: ${command}`);
    }
}
main().catch(err => { console.error('LỖI:', err.message); process.exit(1); });
