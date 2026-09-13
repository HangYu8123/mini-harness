#!/usr/bin/env python3
"""Regenerate harness_gui.html's embedded template snapshots.

The GUI page carries byte-exact copies of every ``request_template/*.md``
inside its ``<script type="application/json" id="hf-templates">`` block so it
still works when opened via ``file://`` (no live-sync). Whenever a template
changes, run this
script from the pack root to rebuild that block from the files on disk instead
of hand-editing JSON:

    python3 sync_gui_templates.py

The whole block is replaced (never patched), so stale hand-edited snapshot
text cannot survive a sync. Key order follows the existing block where
possible so diffs stay minimal.
"""

import json
import os
import re
import sys

PAGE = "harness_gui.html"
OPEN_TAG = '<script type="application/json" id="hf-templates">'
CLOSE_TAG = "</script>"
SUFFIX = "_request_template.md"


def main():
    root = os.path.dirname(os.path.abspath(__file__))
    page_path = os.path.join(root, PAGE)
    tpl_dir = os.path.join(root, "request_template")
    if not os.path.exists(page_path):
        raise SystemExit("{} not found next to this script ({}).".format(PAGE, root))
    if not os.path.isdir(tpl_dir):
        raise SystemExit("request_template/ not found next to this script ({}).".format(root))

    templates = {}
    for fname in sorted(os.listdir(tpl_dir)):
        if fname.endswith(SUFFIX):
            key = fname[: -len(SUFFIX)]
            with open(os.path.join(tpl_dir, fname), encoding="utf-8") as fh:
                templates[key] = fh.read().replace("\r\n", "\n")
    if not templates:
        raise SystemExit("no *{} files found in request_template/.".format(SUFFIX))

    with open(page_path, encoding="utf-8") as fh:
        page = fh.read()
    m = re.search(re.escape(OPEN_TAG) + r"\n(.*?)\n" + re.escape(CLOSE_TAG), page, re.S)
    if not m:
        raise SystemExit("hf-templates block not found in {}.".format(PAGE))

    # Preserve the existing key order; append any brand-new templates after it.
    old = json.loads(m.group(1))
    order = [k for k in old if k in templates] + [k for k in templates if k not in old]
    body = json.dumps({k: templates[k] for k in order}, indent=2, ensure_ascii=True)
    body = body.replace("</", "<\\/")  # HTML-safe inside <script>; still valid JSON

    new_block = OPEN_TAG + "\n" + body + "\n" + CLOSE_TAG
    if page[m.start() : m.end()] == new_block:
        print("hf-templates block already in sync ({} templates).".format(len(templates)))
        return
    with open(page_path, "w", encoding="utf-8") as fh:
        fh.write(page[: m.start()] + new_block + page[m.end() :])
    changed = [k for k in order if old.get(k) != templates[k]]
    dropped = [k for k in old if k not in templates]
    print("hf-templates block rewritten: {} templates ({} changed{}).".format(
        len(templates), len(changed),
        ", dropped: " + ", ".join(dropped) if dropped else ""))


if __name__ == "__main__":
    sys.exit(main())
