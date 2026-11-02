import type { AIProvider } from '../types/provider.js';
export declare class ProviderRegistry {
    private providers;
    register(provider: AIProvider): void;
    get(name: string): AIProvider;
    list(): string[];
}
//# sourceMappingURL=provider-registry.d.ts.map