export declare const workflowSchema: {
    type: "object";
    required: string[];
    additionalProperties: boolean;
    properties: {
        name: {
            type: "string";
            minLength: number;
        };
        description: {
            type: "string";
        };
        provider: {
            type: "string";
        };
        model: {
            type: "string";
        };
        inputs: {
            type: "object";
            additionalProperties: {
                type: "object";
                properties: {
                    type: {
                        type: "string";
                        enum: string[];
                    };
                    required: {
                        type: "boolean";
                    };
                    default: {
                        type: "string";
                    };
                };
            };
        };
        nodes: {
            type: "array";
            minItems: number;
            items: {
                type: "object";
                required: string[];
                oneOf: {
                    required: string[];
                    not: {
                        anyOf: {
                            required: string[];
                        }[];
                    };
                }[];
                additionalProperties: boolean;
                properties: {
                    id: {
                        type: "string";
                        minLength: number;
                    };
                    description: {
                        type: "string";
                    };
                    prompt: {
                        type: "string";
                    };
                    bash: {
                        type: "string";
                    };
                    command: {
                        type: "string";
                    };
                    depends_on: {
                        type: "array";
                        items: {
                            type: "string";
                        };
                    };
                    when: {
                        type: "string";
                    };
                    trigger_rule: {
                        type: "string";
                        enum: string[];
                    };
                    context: {
                        type: "string";
                        enum: string[];
                    };
                    model: {
                        type: "string";
                    };
                    workspace: {
                        type: "boolean";
                    };
                    ledger: {
                        type: "string";
                        minLength: number;
                    };
                    fanout: {
                        type: "object";
                        required: string[];
                        additionalProperties: boolean;
                        properties: {
                            over: {
                                type: "string";
                                minLength: number;
                            };
                            as: {
                                type: "string";
                                minLength: number;
                            };
                            max_concurrency: {
                                type: "integer";
                                minimum: number;
                            };
                        };
                    };
                    allowed_tools: {
                        type: "array";
                        items: {
                            type: "string";
                        };
                    };
                    on_error: {
                        type: "string";
                        enum: string[];
                    };
                    output_format: {
                        type: "object";
                        required: string[];
                        properties: {
                            type: {
                                type: "string";
                                enum: string[];
                            };
                            properties: {
                                type: "object";
                                additionalProperties: {
                                    type: "object";
                                    properties: {
                                        type: {
                                            type: "string";
                                        };
                                        enum: {
                                            type: "array";
                                            items: {
                                                type: "string";
                                            };
                                        };
                                    };
                                };
                            };
                            required: {
                                type: "array";
                                items: {
                                    type: "string";
                                };
                            };
                        };
                    };
                    loop: {
                        type: "object";
                        required: string[];
                        properties: {
                            on_fail: {
                                type: "string";
                            };
                            max_retries: {
                                type: "integer";
                                minimum: number;
                            };
                            inject_error: {
                                type: "boolean";
                            };
                            backoff_ms: {
                                type: "integer";
                                minimum: number;
                            };
                        };
                        additionalProperties: boolean;
                    };
                };
            };
        };
    };
};
//# sourceMappingURL=workflow-schema.d.ts.map