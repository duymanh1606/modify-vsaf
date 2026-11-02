"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.detectCycle = detectCycle;
// Kahn's algorithm — BFS-based topological sort for cycle detection.
// Returns null if acyclic, or the list of node IDs involved in cycles.
function detectCycle(nodes) {
    const inDegree = new Map();
    const downstream = new Map();
    for (const id of nodes.keys()) {
        inDegree.set(id, 0);
        downstream.set(id, []);
    }
    for (const [id, node] of nodes) {
        for (const dep of node.dependsOn) {
            downstream.get(dep)?.push(id);
            inDegree.set(id, (inDegree.get(id) ?? 0) + 1);
        }
    }
    const queue = [];
    for (const [id, degree] of inDegree) {
        if (degree === 0)
            queue.push(id);
    }
    const processed = new Set();
    while (queue.length > 0) {
        const id = queue.shift();
        processed.add(id);
        for (const neighbor of downstream.get(id)) {
            const newDegree = inDegree.get(neighbor) - 1;
            inDegree.set(neighbor, newDegree);
            if (newDegree === 0)
                queue.push(neighbor);
        }
    }
    if (processed.size === nodes.size)
        return null;
    return [...nodes.keys()].filter(id => !processed.has(id));
}
//# sourceMappingURL=cycle-detector.js.map