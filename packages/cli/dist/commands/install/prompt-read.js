"use strict";
/**
 * Telling apart "nobody answered" from "the answer could not be read".
 *
 * Every prompt in the installer used to end in a bare `catch`: whatever went wrong, the
 * command carried on as though the person had pressed Enter. That is the right reading for
 * exactly one kind of failure — Ctrl-C, Ctrl-D, a pipe closing — and the wrong reading for
 * every other one, because "I chose nothing" and "your answer was lost" lead somewhere
 * different, and only the second is worth a line on screen.
 *
 * The cost of not saying it, measured: `vsaf install NTAPP --new`, a project link pasted,
 * 13 repos listed, `1-3` typed — and the run ended with "Chưa clone repo nào" and not one
 * word of why. Three repos asked for, none attempted, nothing printed. The parser was
 * right, the resolver was right; the answer never got out of the prompt, and the `catch`
 * turned that into a silent "no".
 *
 * So: a cut-off prompt stays silent, and anything else has to be said.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.promptWasCutOff = promptWasCutOff;
exports.promptFailureReason = promptFailureReason;
/**
 * Node's names for a prompt that was cut off rather than broken.
 *
 * Ctrl-C and Ctrl-D do not, on their own, reject `readline.question` — the process is
 * killed or the interface simply closes. What reaches a `catch` is the wreckage
 * afterwards: a question asked of a closed interface, a stream that ended mid-read, an
 * `AbortError` from whoever wired the signal. Those are the person leaving, not a fault.
 *
 * Anything not on this list is a fault, and the caller must say so. Keep the list narrow:
 * every code added here is one more way for a typed answer to vanish without a word.
 */
const CUT_OFF_CODES = new Set([
    'ABORT_ERR', // an AbortSignal fired — how Ctrl-C arrives when someone wired it
    'ERR_USE_AFTER_CLOSE', // asked of a readline that had already closed: stdin hit EOF
    'ERR_STREAM_PREMATURE_CLOSE', // stdin ended in the middle of the question
    'ERR_STREAM_DESTROYED',
    'EPIPE', // the terminal on the other end went away
    'EOF',
]);
/** True when the prompt ended because the person, or the shell, closed it. */
function promptWasCutOff(error) {
    if (error === null || error === undefined)
        return false;
    const { code, name } = error;
    if (typeof code === 'string' && CUT_OFF_CODES.has(code))
        return true;
    return name === 'AbortError';
}
/**
 * One line naming what went wrong, to hand to somebody who has to do something about it.
 *
 * First line only: a stack trace pasted into a prompt-failure message is a wall nobody
 * reads, and the next line printed after this one is the one that says what to do.
 */
function promptFailureReason(error) {
    const message = error instanceof Error ? error.message : String(error ?? '');
    return message.split('\n')[0].trim() || 'lỗi không rõ';
}
//# sourceMappingURL=prompt-read.js.map