"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ProviderRegistry = void 0;
class ProviderRegistry {
    providers = new Map();
    register(provider) {
        this.providers.set(provider.name, provider);
    }
    get(name) {
        const provider = this.providers.get(name);
        if (!provider) {
            throw new Error(`AI provider not found: "${name}". Registered: [${this.list().join(', ')}]`);
        }
        return provider;
    }
    list() {
        return [...this.providers.keys()];
    }
}
exports.ProviderRegistry = ProviderRegistry;
//# sourceMappingURL=provider-registry.js.map