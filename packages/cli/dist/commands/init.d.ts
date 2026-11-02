import type { TelemetryArtifactsConfig } from '@vsaf/core';
/**
 * Write `.vsaf/config.yaml`, or top up one that is already there.
 *
 * The old behaviour was all-or-nothing: an existing file was left completely
 * alone, so any project whose config predates telemetry — or was written by
 * hand, or scaffolded by something other than `vsaf init` — could never acquire
 * the section, not even with `--force`. Telemetry stayed off forever with no
 * hint as to why.
 *
 * Appending is the whole change. The file belongs to the user (they keep notes
 * in it), so existing bytes are never rewritten or reordered, and a file that
 * does not parse is left untouched rather than guessed at.
 */
export declare function writeProjectConfig(configPath: string, artifacts?: TelemetryArtifactsConfig): void;
/**
 * TEMPORARILY DISABLED (2026-07-23): during scaffold, `vsaf init` does NOT
 * write the gateway env block (ANTHROPIC_BASE_URL / ANTHROPIC_AUTH_TOKEN /
 * ANTHROPIC_MODEL) into .claude/settings.json, and no virtual key is required
 * or prompted for. Flip to true to restore key validation, the CLI prompt,
 * and env writes. The SessionStart hook is unaffected either way.
 */
export declare const GATEWAY_ENV_ENABLED = false;
/**
 * Reports whether the project's .claude/settings.json already carries a
 * gateway virtual key — in that case `vsaf init` doesn't require a new one.
 */
export declare function hasGatewayToken(projectPath: string): boolean;
/**
 * Những gì `vsaf init` nhận.
 *
 * Không có tên flow nào ở đây, và đó là chủ ý: `init` dựng thư mục cho dự án, `vsaf
 * install <flow>` mới là chỗ cài skill và flow. Trước đây `init` tự cài pack `sdlc` —
 * đo được 62 skill, 12 workflow và 29 lệnh slash sau một lượt `vsaf init` trên thư mục
 * rỗng — tức là nó làm luôn phần việc của `install`, và trên nhánh này còn đi qua mạng
 * để lấy flow đó về.
 */
export interface InitOptions {
    /**
     * AI Gateway virtual key, written to .claude/settings.json as
     * ANTHROPIC_AUTH_TOKEN. Required unless settings.json already carries one.
     */
    gatewayKey?: string;
    /**
     * Reinitialize an existing .vsaf/ in place: keep docs/, storage/, and an
     * existing config.yaml.
     */
    force?: boolean;
}
export declare function execInit(projectPath: string, options?: InitOptions): Promise<void>;
//# sourceMappingURL=init.d.ts.map