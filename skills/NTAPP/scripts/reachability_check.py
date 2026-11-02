#!/usr/bin/env python3
"""Endpoint reachability check — project-agnostic adapter contract.

Purpose
-------
Prove that every HTTP call a *consumer* actually makes resolves to a *provider*
route across one or more hops (consumer -> proxy/BFF -> service). Catches, at the
(method, path) resolution level, the two feature-integration failure modes:

    404  no provider route serves this path at all
    405  a route serves this path but under a different HTTP verb

This is the shared extraction/matching engine used by two NTAPP workflow gates:
  * slice-loop `slice-integration` (raise seam checks from atom -> endpoint)
  * staging-deploy `feature-integration-smoke` (static tier, feature-wide)

Adapter contract
----------------
Two pluggable extractor kinds, chosen per stack:
    extract_consumer_calls(dir, adapter)  -> set[(METHOD, normalized_path)]
    extract_provider_routes(dir, adapter) -> set[(METHOD, normalized_path)]

A matcher normalises path params ({id} / :id / ${x} -> *) and compares
(method, path). Reference adapters shipped (dependency-free, regex-light):
    consumer: angular-httpclient, spring-restclient
    provider: spring-mapping, openapi
Unknown adapter names raise UnknownAdapterError so a project can register its own
(see reachability_check.README.md).

Config — `.bmm-config.yaml` `reachability:` block (project supplies dirs/adapters,
NEVER hardcoded here):

    reachability:
      hops:
        - consumer_dir: "web/fe"
          consumer_adapter: angular-httpclient
          provider_dir: "services/bff"
          provider_adapter: spring-mapping
        - consumer_dir: "services/bff/src/main/java/.../adapter"
          consumer_adapter: spring-restclient
          provider_dir: "services/core"
          provider_adapter: spring-mapping

CLI
---
    python3 scripts/reachability_check.py --config .bmm-config.yaml
    python3 scripts/reachability_check.py \
        --consumer-dir web/fe --consumer-adapter angular-httpclient \
        --provider-dir services/bff --provider-adapter spring-mapping
    python3 scripts/reachability_check.py --list-adapters

Exit codes: 0 = all resolved (or nothing configured), 1 = unresolved calls found,
2 = usage / config error (unknown adapter, missing args).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import namedtuple
from pathlib import Path

Call = namedtuple("Call", ["method", "path", "source"])

CONSUMER_KIND = "consumer"
PROVIDER_KIND = "provider"

DEFAULT_CONSUMER_ADAPTER = "angular-httpclient"
DEFAULT_PROVIDER_ADAPTER = "spring-mapping"

_HTTP_METHODS = {"get", "post", "put", "delete", "patch", "head", "options"}
_SKIP_DIRS = {".git", "node_modules", "target", "dist", "build", ".idea",
              "__pycache__", ".gradle", "coverage"}


# ── path normalisation + matcher ──────────────────────────────────────────────

_PARAM_RE = re.compile(r"\$\{[^}/]*\}|\{[^}/]*\}|:[A-Za-z_]\w*")


def normalize_path(path: str) -> str:
    """Normalise a URL/route to a comparable path: strip scheme+authority and
    query, collapse duplicate slashes, and replace path params with `*`."""
    path = (path or "").strip()
    path = path.split("?", 1)[0].split("#", 1)[0]
    if "://" in path:
        rest = path.split("://", 1)[1]
        idx = rest.find("/")
        path = rest[idx:] if idx != -1 else "/"
    path = _PARAM_RE.sub("*", path)
    path = re.sub(r"/{2,}", "/", path)
    if not path.startswith(("/", "*")):
        path = "/" + path
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return path


def match_calls(consumer_calls, provider_routes):
    """Return the set of (method, path) consumer calls with no matching route."""
    routes = set(provider_routes)
    return {(m, p) for (m, p) in consumer_calls if (m, p) not in routes}


def _diff(calls, routes):
    """Diff Call objects against provider routes, classifying 404 vs 405."""
    provider_paths = {p for (_, p) in routes}
    unresolved = []
    for c in sorted(calls):
        if (c.method, c.path) not in routes:
            kind = "405" if c.path in provider_paths else "404"
            unresolved.append((c, kind))
    return unresolved


# ── shared file/regex helpers ─────────────────────────────────────────────────

def _iter_files(directory, exts):
    for base, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for name in files:
            if os.path.splitext(name)[1].lower() in exts:
                yield os.path.join(base, name)


def _read(path):
    try:
        return Path(path).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _rel(path, root):
    try:
        return os.path.relpath(path, root)
    except ValueError:
        return path


# ── consumer adapter: angular-httpclient ──────────────────────────────────────

_ANGULAR_CALL = re.compile(
    r"\bhttp\w*\.(get|post|put|delete|patch)\s*(?:<[^>]*>)?\s*\(\s*([`'\"])(.*?)\2",
    re.DOTALL,
)


def extract_angular_calls(directory):
    """Consumer: this.http.get/post/put/delete/patch('...') in *.ts files."""
    calls = set()
    for path in _iter_files(directory, {".ts"}):
        text = _read(path)
        rel = _rel(path, directory)
        for m in _ANGULAR_CALL.finditer(text):
            calls.add(Call(m.group(1).upper(), normalize_path(m.group(3)), rel))
    return calls


# ── spring annotation helpers (shared by provider + feign consumer) ────────────

_MAPPING_METHOD = {
    "GetMapping": "GET", "PostMapping": "POST", "PutMapping": "PUT",
    "DeleteMapping": "DELETE", "PatchMapping": "PATCH",
}
_ANN_RE = re.compile(r"@(\w+Mapping)\b\s*(?:\((?P<args>[^)]*)\))?", re.DOTALL)
_VALUE_RE = re.compile(r"(?:value|path)\s*=\s*([\"'])(.*?)\1", re.DOTALL)
_POS_STR_RE = re.compile(r"^\s*([\"'])(.*?)\1")
_REQ_METHOD_RE = re.compile(r"RequestMethod\.(\w+)")


def _ann_path(args):
    m = _VALUE_RE.search(args)
    if m:
        return m.group(2)
    m = _POS_STR_RE.search(args)
    return m.group(2) if m else ""


def _join(prefix, path):
    return normalize_path("/" + (prefix or "").strip("/") + "/" + (path or "").strip("/"))


def _class_prefix(text):
    m = re.search(r"@RequestMapping\s*\(([^)]*)\)[\s\S]{0,300}?\bclass\b", text)
    return _ann_path(m.group(1)) if m else ""


# ── provider adapter: spring-mapping ──────────────────────────────────────────

def extract_spring_routes(directory):
    """Provider: @GetMapping/@PostMapping/... + class-level @RequestMapping prefix."""
    routes = set()
    for path in _iter_files(directory, {".java"}):
        text = _read(path)
        prefix = _class_prefix(text)
        for m in _ANN_RE.finditer(text):
            _collect_mapping(routes, m.group(1), m.group("args") or "", prefix)
    return routes


def _collect_mapping(routes, ann, args, prefix):
    if ann in _MAPPING_METHOD:
        routes.add((_MAPPING_METHOD[ann], _join(prefix, _ann_path(args))))
    elif ann == "RequestMapping":
        for meth in _REQ_METHOD_RE.findall(args):
            routes.add((meth.upper(), _join(prefix, _ann_path(args))))


# ── consumer adapter: spring-restclient (BFF -> service hop) ───────────────────

_RESTTEMPLATE_METHOD = {
    "getForObject": "GET", "getForEntity": "GET",
    "postForObject": "POST", "postForEntity": "POST",
    "put": "PUT", "delete": "DELETE", "patchForObject": "PATCH",
}
_EXCHANGE_RE = re.compile(r"\.exchange\s*\(\s*([\"'])(.*?)\1\s*,\s*HttpMethod\.(\w+)", re.DOTALL)
_WEBCLIENT_RE = re.compile(r"\.(get|post|put|delete|patch)\(\)\s*\.uri\s*\(\s*([\"'])(.*?)\2", re.DOTALL)
_FEIGN_PATH_RE = re.compile(r"path\s*=\s*([\"'])(.*?)\1")


def extract_spring_client_calls(directory):
    """Consumer: RestTemplate / WebClient / FeignClient outbound calls in *.java."""
    calls = set()
    for path in _iter_files(directory, {".java"}):
        text = _read(path)
        rel = _rel(path, directory)
        _collect_resttemplate(calls, text, rel)
        _collect_feign(calls, text, rel)
    return calls


def _collect_resttemplate(calls, text, rel):
    for name, meth in _RESTTEMPLATE_METHOD.items():
        for m in re.finditer(r"\." + name + r"\s*\(\s*([\"'])(.*?)\1", text, re.DOTALL):
            calls.add(Call(meth, normalize_path(m.group(2)), rel))
    for m in _EXCHANGE_RE.finditer(text):
        calls.add(Call(m.group(3).upper(), normalize_path(m.group(2)), rel))
    for m in _WEBCLIENT_RE.finditer(text):
        calls.add(Call(m.group(1).upper(), normalize_path(m.group(3)), rel))


def _collect_feign(calls, text, rel):
    if "@FeignClient" not in text:
        return
    fm = re.search(r"@FeignClient\s*\(([^)]*)\)", text, re.DOTALL)
    prefix = ""
    if fm:
        pm = _FEIGN_PATH_RE.search(fm.group(1))
        prefix = pm.group(2) if pm else ""
    for m in _ANN_RE.finditer(text):
        ann, args = m.group(1), m.group("args") or ""
        if ann in _MAPPING_METHOD:
            calls.add(Call(_MAPPING_METHOD[ann], _join(prefix, _ann_path(args)), rel))


# ── provider adapter: openapi ─────────────────────────────────────────────────

def extract_openapi_routes(directory):
    """Provider: paths section of an OpenAPI/Swagger json/yaml spec."""
    routes = set()
    for path in _iter_files(directory, {".json", ".yaml", ".yml"}):
        name = os.path.basename(path).lower()
        if "openapi" not in name and "swagger" not in name:
            continue
        _collect_openapi(routes, _load_spec(path))
    return routes


def _collect_openapi(routes, spec):
    paths = (spec or {}).get("paths")
    if not isinstance(paths, dict):
        return
    for route, item in paths.items():
        if not isinstance(item, dict):
            continue
        for method in item:
            if str(method).lower() in _HTTP_METHODS:
                routes.add((str(method).upper(), normalize_path(str(route))))


def _load_spec(path):
    text = _read(path)
    if not text:
        return {}
    if path.lower().endswith(".json"):
        return _try_json(text)
    return _try_yaml(text)


def _try_json(text):
    try:
        return json.loads(text)
    except ValueError:
        return {}


def _try_yaml(text):
    try:
        import yaml  # optional: only needed to parse YAML OpenAPI specs
    except ImportError:
        sys.stderr.write("[warn] PyYAML not installed; cannot parse YAML spec — use JSON.\n")
        return {}
    try:
        return yaml.safe_load(text) or {}
    except yaml.YAMLError:
        return {}


# ── adapter registry ──────────────────────────────────────────────────────────

class UnknownAdapterError(Exception):
    """Raised when a hop references an adapter name that is not registered."""


CONSUMER_ADAPTERS = {
    DEFAULT_CONSUMER_ADAPTER: extract_angular_calls,
    "spring-restclient": extract_spring_client_calls,
}
PROVIDER_ADAPTERS = {
    DEFAULT_PROVIDER_ADAPTER: extract_spring_routes,
    "openapi": extract_openapi_routes,
}


def _resolve_adapter(registry, name, kind):
    fn = registry.get(name)
    if fn is None:
        known = ", ".join(sorted(registry)) or "(none)"
        raise UnknownAdapterError(
            f"unknown {kind} adapter '{name}'. Known: {known}. "
            f"Register your own in {kind.upper()}_ADAPTERS (see the README)."
        )
    return fn


def extract_consumer_calls(directory, adapter=DEFAULT_CONSUMER_ADAPTER):
    """Adapter contract: dir -> set[(METHOD, normalized_path)]."""
    fn = _resolve_adapter(CONSUMER_ADAPTERS, adapter, CONSUMER_KIND)
    return {(c.method, c.path) for c in fn(directory)}


def extract_provider_routes(directory, adapter=DEFAULT_PROVIDER_ADAPTER):
    """Adapter contract: dir -> set[(METHOD, normalized_path)]."""
    fn = _resolve_adapter(PROVIDER_ADAPTERS, adapter, PROVIDER_KIND)
    return set(fn(directory))


# ── config parsing (minimal, dependency-free) ─────────────────────────────────

def load_reachability_hops(config_path):
    """Parse the `reachability.hops` list from a .bmm-config.yaml.

    Understands only the small subset used by this contract: a top-level
    `reachability:` mapping with a `hops:` list of mappings of scalar strings.
    Everything else in the file is ignored — no external YAML dependency.
    """
    text = _read(config_path)
    hops = []
    current = None
    section = None
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not raw.startswith((" ", "\t")):
            section = "reachability" if stripped.startswith("reachability:") else None
            current = None
            continue
        if section is None:
            continue
        if stripped.startswith("hops:"):
            section = "hops"
            continue
        if section != "hops":
            continue
        if stripped.startswith("-"):
            current = {}
            hops.append(current)
            stripped = stripped[1:].strip()
        if current is not None:
            _assign_kv(current, stripped)
    return hops


def _assign_kv(mapping, text):
    if ":" not in text:
        return
    key, _, val = text.partition(":")
    key = key.strip()
    if key:
        mapping[key] = val.strip().strip('"').strip("'")


# ── hop execution ─────────────────────────────────────────────────────────────

def _resolve_dir(root, rel):
    path = rel if os.path.isabs(rel) else os.path.join(root, rel)
    if not os.path.isdir(path):
        sys.stderr.write(f"[warn] directory not found: {path}\n")
    return path


def run_hop(hop, root="."):
    """Run one hop: extract consumer calls + provider routes, return unresolved
    list of (Call, kind) where kind is '404' or '405'."""
    c_fn = _resolve_adapter(CONSUMER_ADAPTERS, hop.get("consumer_adapter", ""), CONSUMER_KIND)
    p_fn = _resolve_adapter(PROVIDER_ADAPTERS, hop.get("provider_adapter", ""), PROVIDER_KIND)
    calls = c_fn(_resolve_dir(root, hop.get("consumer_dir", "")))
    routes = set(p_fn(_resolve_dir(root, hop.get("provider_dir", ""))))
    return _diff(calls, routes)


def _run_hops(hops, root):
    rows = []
    for idx, hop in enumerate(hops, 1):
        label = hop.get("label") or f"hop-{idx}"
        try:
            unresolved = run_hop(hop, root)
        except UnknownAdapterError as exc:
            sys.stderr.write(f"[error] {label}: {exc}\n")
            return 2
        rows.extend((label, c, kind) for c, kind in unresolved)
    _print_report(rows)
    return 1 if rows else 0


# ── CLI ───────────────────────────────────────────────────────────────────────

def _print_report(rows):
    if not rows:
        print("OK — every consumer call resolves to a provider route.")
        return
    print("UNRESOLVED consumer calls (feature-integration would 404/405):")
    print(f"{'HOP':<12} {'METHOD':<7} {'STATUS':<6} {'PATH':<40} SOURCE")
    for label, c, kind in rows:
        print(f"{label:<12} {c.method:<7} {kind:<6} {c.path:<40} {c.source}")
    print(f"\n{len(rows)} unresolved call(s).")


def _print_adapters():
    print("Consumer adapters:", ", ".join(sorted(CONSUMER_ADAPTERS)))
    print("Provider adapters:", ", ".join(sorted(PROVIDER_ADAPTERS)))


def _gather_hops(args):
    if args.config:
        return load_reachability_hops(args.config)
    if args.consumer_dir and args.provider_dir:
        return [{
            "label": "cli",
            "consumer_dir": args.consumer_dir,
            "consumer_adapter": args.consumer_adapter,
            "provider_dir": args.provider_dir,
            "provider_adapter": args.provider_adapter,
        }]
    return None


def _resolve_root(args):
    if args.root:
        return args.root
    if args.config:
        return os.path.dirname(os.path.abspath(args.config)) or "."
    return "."


def _build_parser():
    parser = argparse.ArgumentParser(
        description="Check every consumer HTTP call resolves to a provider route "
                    "across configured hops (project-agnostic adapter contract).")
    parser.add_argument("--config", help="path to .bmm-config.yaml with a reachability: block")
    parser.add_argument("--consumer-dir", help="ad-hoc single-hop: consumer source dir")
    parser.add_argument("--consumer-adapter", default=DEFAULT_CONSUMER_ADAPTER,
                        help=f"consumer adapter name (default: {DEFAULT_CONSUMER_ADAPTER})")
    parser.add_argument("--provider-dir", help="ad-hoc single-hop: provider source dir")
    parser.add_argument("--provider-adapter", default=DEFAULT_PROVIDER_ADAPTER,
                        help=f"provider adapter name (default: {DEFAULT_PROVIDER_ADAPTER})")
    parser.add_argument("--root", help="base dir for relative hop dirs "
                                       "(default: config dir, else cwd)")
    parser.add_argument("--list-adapters", action="store_true",
                        help="list registered adapters and exit")
    return parser


def main(argv=None):
    args = _build_parser().parse_args(argv)
    if args.list_adapters:
        _print_adapters()
        return 0
    hops = _gather_hops(args)
    if hops is None:
        sys.stderr.write("[error] provide --config, or both --consumer-dir and --provider-dir.\n")
        return 2
    if not hops:
        print("No reachability hops configured — skipping static reachability check.")
        return 0
    return _run_hops(hops, _resolve_root(args))


if __name__ == "__main__":
    sys.exit(main())
