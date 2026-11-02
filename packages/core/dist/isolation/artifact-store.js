"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ArtifactStore = void 0;
// packages/core/src/isolation/artifact-store.ts
const fs_1 = require("fs");
const path_1 = require("path");
class ArtifactStore {
    basePath;
    constructor(basePath) {
        this.basePath = basePath;
    }
    async write(name, content) {
        const filePath = (0, path_1.join)(this.basePath, name);
        (0, fs_1.mkdirSync)((0, path_1.dirname)(filePath), { recursive: true });
        (0, fs_1.writeFileSync)(filePath, content, 'utf-8');
    }
    async read(name) {
        return (0, fs_1.readFileSync)((0, path_1.join)(this.basePath, name), 'utf-8');
    }
    async exists(name) {
        return (0, fs_1.existsSync)((0, path_1.join)(this.basePath, name));
    }
    async list() {
        if (!(0, fs_1.existsSync)(this.basePath))
            return [];
        return (0, fs_1.readdirSync)(this.basePath);
    }
}
exports.ArtifactStore = ArtifactStore;
//# sourceMappingURL=artifact-store.js.map