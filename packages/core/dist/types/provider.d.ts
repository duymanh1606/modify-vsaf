export interface AIProviderConfig {
    model: string;
    cwd?: string;
    allowedTools?: string[];
    outputFormat?: object;
    freshContext?: boolean;
}
export interface AIProviderResult {
    output: string;
    structuredOutput?: Record<string, unknown>;
    tokensUsed: number;
    durationMs: number;
}
export interface AIProvider {
    name: string;
    execute(prompt: string, config: AIProviderConfig): Promise<AIProviderResult>;
    isAvailable(): Promise<boolean>;
}
//# sourceMappingURL=provider.d.ts.map