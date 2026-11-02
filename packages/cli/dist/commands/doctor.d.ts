export interface CheckResult {
    name: string;
    ok: boolean;
    version?: string;
    message?: string;
}
export type ProbeResult = 'ok' | 'auth' | 'unreachable';
export type ProbeFn = (url: string, headers: Record<string, string>) => Promise<ProbeResult>;
export interface DoctorOptions {
    probe?: ProbeFn;
}
/** Which of those cannot be resolved from here. Empty means telemetry can load. */
export declare function MissingOtelModules(modules?: string[]): string[];
/**
 * Count workflows one level deep as well: installing a pack puts its workflows in
 * `.vsaf/workflows/<pack>/`, so counting only the top level reports zero for a
 * project that in fact has plenty.
 */
export declare function countWorkflows(dir: string): number;
export declare function runChecks(projectPath: string, options?: DoctorOptions): Promise<CheckResult[]>;
export declare function formatChecks(results: CheckResult[]): string;
//# sourceMappingURL=doctor.d.ts.map