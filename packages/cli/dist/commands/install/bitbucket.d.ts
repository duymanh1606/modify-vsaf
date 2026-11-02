/**
 * Read the repo list of a Bitbucket Server project.
 *
 * This is the whole point of accepting a project link: the list a person would otherwise
 * copy off the project page, one repo at a time, is a single read the tool can do.
 *
 * Only reads happen here, and only against the url the user pasted. The credential is put
 * in a header and is never written down, logged, or included in a message — an install
 * that leaks a credential into a workspace is worse than one that asks for twenty urls.
 */
import { type Credential } from './credentials.js';
/** A repo as the forge describes it. Both clone urls are kept; the caller picks. */
export interface ForgeRepo {
    slug: string;
    name: string;
    ssh?: string;
    http?: string;
}
/**
 * The server answered, and the answer was no.
 *
 * The status is kept beside the sentence because one caller has to act on it: a 401 is the
 * only status worth trying a second credential form for, and reading that out of a
 * Vietnamese message would break the next time the message is reworded.
 */
export declare class ApiRefusal extends Error {
    readonly status: number;
    constructor(status: number, message: string);
}
/**
 * List every repo of a project, following the pages to the end.
 *
 * The api serves a hundred at a time, so a project of more than a hundred repos looks
 * like a project of exactly a hundred to anything that reads the first page and stops.
 *
 * Two credential forms, at most, and only in this order. A credential taken from the
 * machine's git store is whatever that person typed the day they first cloned: on
 * Bitbucket Server that is usually a personal access token, which this server accepts as
 * `Bearer` and rejects as `Basic` — measured against bitbucket.digital.vn. But it can
 * equally be their login password, which is the other way round, and there is no way to
 * tell the two apart by looking.
 *
 * So a 401 buys exactly one more attempt in the other form. Not more, and not on any
 * other status: on Bitbucket Server a rejected credential counts as a failed login, and
 * three of those turn into a CAPTCHA lock that closes `git clone` for every repo in the
 * project — measured on this very account. 403 means the credential is fine and the
 * permission is not, so trying it a second way can only spend one of those three.
 *
 * `fetchImpl` exists so tests can answer without a network and without a credential;
 * nothing else should pass it.
 */
export declare function listProjectRepos(base: string, key: string, credential: string | Credential, fetchImpl?: typeof fetch): Promise<ForgeRepo[]>;
//# sourceMappingURL=bitbucket.d.ts.map