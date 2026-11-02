"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.ajv = void 0;
const ajv_1 = __importDefault(require("ajv"));
exports.ajv = new ajv_1.default({
    allErrors: true,
    strict: false,
});
//# sourceMappingURL=ajv-instance.js.map