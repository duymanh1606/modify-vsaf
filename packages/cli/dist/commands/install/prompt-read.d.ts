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
/** True when the prompt ended because the person, or the shell, closed it. */
export declare function promptWasCutOff(error: unknown): boolean;
/**
 * One line naming what went wrong, to hand to somebody who has to do something about it.
 *
 * First line only: a stack trace pasted into a prompt-failure message is a wall nobody
 * reads, and the next line printed after this one is the one that says what to do.
 */
export declare function promptFailureReason(error: unknown): string;
//# sourceMappingURL=prompt-read.d.ts.map