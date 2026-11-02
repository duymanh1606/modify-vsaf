interface NodeOutput {
    output?: string;
    structuredOutput?: Record<string, unknown>;
}
export declare function evaluateCondition(condition: string | undefined, nodeOutputs: Record<string, NodeOutput>): boolean;
export {};
//# sourceMappingURL=condition-evaluator.d.ts.map