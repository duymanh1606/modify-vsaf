export interface IsolationConfig {
    /**
     * 'ephemeral' (mặc định): copy/worktree riêng — hành vi cũ.
     * 'none': không copy, không worktree — AI/bash thao tác trực tiếp trên
     * projectPath. Trước đây giá trị này bị mọi entry point bỏ qua (luôn tạo
     * bản copy /tmp), khiến test-gate không thấy code vừa ghi (bug A).
     */
    type: 'ephemeral' | 'none';
    cleanup: 'after_success' | 'after_always' | 'never';
    exclude: string[];
    max_workspaces: number;
}
export interface TelemetryLangfuseConfig {
    host?: string;
    public_key?: string;
    secret_key?: string;
}
export interface TelemetryOtlpConfig {
    endpoint?: string;
    headers?: Record<string, string>;
}
/**
 * Which paths the per-node output metrics count. Defaults suit the sdlc pack,
 * whose artifacts land in `.vsaf/docs/`; a pack writing anywhere else (NTAPP
 * uses `NTAPP-output/`) reported zero artifacts forever without this.
 */
export interface TelemetryArtifactsConfig {
    /** Created files under these prefixes count as artifacts. Replaces the default. */
    include?: string[];
    /** Never counted at all. Added to the engine's own noise list, never replaces it. */
    exclude?: string[];
    /**
     * Extra repos to measure besides the project dir, for a dual-repo project whose
     * source lives outside the spec repo. Paths are relative to the project dir, or
     * absolute. Left out, the repos listed in the workspace file are measured.
     */
    code_roots?: string[];
}
export interface TelemetryConfig {
    otlp?: TelemetryOtlpConfig;
    artifacts?: TelemetryArtifactsConfig;
    /** @deprecated Auto-mapped to the Langfuse OTLP endpoint — migrate to `otlp`. */
    langfuse?: TelemetryLangfuseConfig;
}
export interface VSAFConfig {
    provider: string;
    model: string;
    isolation: IsolationConfig;
    telemetry?: TelemetryConfig;
    /** Project test command, referenced by workflows as $CONFIG.test_command. */
    test_command?: string;
    /**
     * Refuse to start a run while another one holds this project. Off by default so
     * existing projects keep today's behaviour; workflows that fan out over shared
     * state (NTAPP) turn it on.
     */
    run_lock?: boolean;
}
export declare function loadConfig(projectPath: string): VSAFConfig;
//# sourceMappingURL=config-loader.d.ts.map