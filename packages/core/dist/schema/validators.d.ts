import type { OutputFormat, InputParamDef } from '../types/workflow.js';
export declare function validateWorkflowSchema(raw: unknown): {
    valid: boolean;
    errors: string[];
};
export declare function validateOutputFormat(output: Record<string, unknown> | undefined, format: OutputFormat): {
    valid: boolean;
    errors: string[];
};
export declare function validateInputs(args: string, inputs: Record<string, InputParamDef>): string[];
//# sourceMappingURL=validators.d.ts.map