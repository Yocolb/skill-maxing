#!/usr/bin/env python3
"""Static red-flag scanner for a quarantined Claude skill folder.

Reads files only: it never imports, executes or fetches anything from the
target. Its output is evidence for the auditor to read, not a verdict; a clean
scan does not mean a skill is safe.

Usage: python -I scan.py <skill-or-repo-dir> [--json]
"""
import json
import os
import re
import sys

MAX_BYTES = 2_000_000
TEXT_EXT = {
    ".md", ".txt", ".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".sh",
    ".bash", ".ps1", ".bat", ".cmd", ".json", ".yaml", ".yml", ".toml", ".html",
    ".css", ".csv", ".xml", ".ini", ".cfg", "",
}
BINARY_FLAG_EXT = {".exe", ".dll", ".so", ".dylib", ".bin", ".msi", ".scr", ".jar", ".pyc", ".node"}

RULES = [
    # (category, severity, regex)
    ("prompt-injection", "high", r"ignore (all |any )?(previous|prior|above) (instructions|rules)"),
    ("prompt-injection", "high", r"(disregard|override) (the |your )?(system|user|previous) (prompt|instructions)"),
    ("prompt-injection", "high", r"do not (tell|inform|mention to) the user"),
    ("prompt-injection", "high", r"(edit|modify|write to|append to) .{0,40}(CLAUDE\.md|settings(\.local)?\.json|\.claude/)"),
    ("prompt-injection", "medium", r"<!--.{0,200}(claude|assistant|instruction|must|always)"),
    ("prompt-injection", "medium", r"(dangerously|--dangerously-skip-permissions|bypassPermissions|allowed-tools:\s*.*Bash)"),
    ("hijack", "medium", r"(use this skill|trigger) (for )?(EVERY|ALL|ANY) "),
    ("hijack", "medium", r"always (use|load|read) this skill"),
    ("network", "medium", r"\b(curl|wget|Invoke-WebRequest|iwr|Invoke-RestMethod)\b"),
    ("network", "medium", r"\b(requests\.(get|post)|urllib\.request|http\.client|fetch\(|axios|XMLHttpRequest|WebSocket)\b"),
    ("network", "high", r"(webhook|discord(app)?\.com/api/webhooks|hooks\.slack\.com|ngrok|pastebin|transfer\.sh|0x0\.st|requestbin)"),
    ("exec", "high", r"(?<![.\w])(eval|exec)\s*\("),
    ("exec", "medium", r"\b(subprocess|child_process|os\.system|os\.popen|spawnSync|execSync|Start-Process)\b"),
    ("exec", "high", r"(curl|wget|iwr)[^\n|]{0,200}\|\s*(sh|bash|python|iex|powershell)"),
    ("exec", "high", r"\b(iex|Invoke-Expression)\b"),
    ("install", "medium", r"\b(npx\s+-y|npm\s+(i|install)|pip3?\s+install|uv\s+pip|cargo\s+install|go\s+install|brew\s+install|winget\s+install)\b"),
    ("install", "high", r"\"(pre|post)install\"\s*:"),
    ("secrets", "high", r"(\.ssh/|id_rsa|\.aws/credentials|Login Data|Cookies|keychain|wallet\.dat)"),
    ("secrets", "medium", r"(?-i:process\.env|os\.environ|getenv|\$env:|\b[A-Z_]*(API_KEY|SECRET|TOKEN|PASSWORD)[A-Z_]*\b)"),
    ("obfuscation", "high", r"(base64\s*(-d|--decode)|atob\(|b64decode|FromBase64String|\\x[0-9a-f]{2}(\\x[0-9a-f]{2}){20,})"),
    ("obfuscation", "medium", r"[A-Za-z0-9+/]{200,}={0,2}"),
    ("junk", "low", r"(utm_source=|[?&]tag=[a-z0-9-]+-20|affiliate|[?&]ref=)"),
]
COMPILED = [(c, s, re.compile(p, re.I)) for c, s, p in RULES]
INVISIBLE = re.compile("[​-‏‪-‮⁠-⁤﻿\U000e0000-\U000e007f]")


def scan(root):
    findings, files, skipped = [], 0, []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in {".git", "node_modules"}]
        for name in filenames:
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root)
            ext = os.path.splitext(name)[1].lower()
            if os.path.islink(path):
                findings.append(("symlink", "high", rel, 0, "symlink -> " + os.readlink(path)))
                continue
            if ext in BINARY_FLAG_EXT:
                findings.append(("binary", "high", rel, 0, "executable/binary file"))
                continue
            if ext not in TEXT_EXT or os.path.getsize(path) > MAX_BYTES:
                skipped.append(rel)
                continue
            files += 1
            with open(path, encoding="utf-8", errors="replace") as fh:
                for n, line in enumerate(fh, 1):
                    if INVISIBLE.search(line):
                        findings.append(("hidden-text", "high", rel, n, "invisible/bidi unicode characters"))
                    seen = set()
                    for cat, sev, rx in COMPILED:
                        if cat not in seen and rx.search(line):
                            seen.add(cat)
                            findings.append((cat, sev, rel, n, line.strip()[:160]))
    return files, skipped, findings


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) < 2 or not os.path.isdir(sys.argv[1]):
        print(__doc__)
        sys.exit(2)
    files, skipped, findings = scan(sys.argv[1])
    if "--json" in sys.argv:
        print(json.dumps({"files_scanned": files, "skipped": skipped, "findings": [
            dict(zip(("category", "severity", "file", "line", "text"), f)) for f in findings]}, indent=1))
        return
    order = {"high": 0, "medium": 1, "low": 2}
    print(f"Scanned {files} text files. Skipped (binary/large/unknown type): {len(skipped)}")
    for rel in skipped[:30]:
        print(f"  skipped: {rel}")
    if not findings:
        print("No pattern hits. Still read every file: patterns miss things.")
    for cat, sev, rel, n, text in sorted(findings, key=lambda f: (order[f[1]], f[0], f[2])):
        print(f"[{sev.upper():6}] {cat:16} {rel}:{n}  {text}")


if __name__ == "__main__":
    main()
