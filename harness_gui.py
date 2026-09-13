#!/usr/bin/env python3
"""Launch the mini-harness Request Builder GUI.

One command, no install, no dependencies:

    python3 harness_gui.py

Starts a tiny local web server rooted at this folder and opens
``harness_gui.html`` in your default browser automatically. Serving over http
(instead of opening the file directly) lets the page live-sync the templates
from ``request_template/`` AND enables the native "Browse" file picker.

WHY a native picker: browsers deliberately hide the full filesystem path of a
dragged or chosen file (you only ever get the bare file name). The page therefore
calls back to this server's ``/__pick__`` endpoint, which opens a native OS file
dialog (stdlib ``tkinter`` — no third-party dependency) and returns the real
absolute paths. Paths that live under this folder come back repo-relative with
forward slashes, matching how the request templates reference files.

Set ``HARNESS_GUI_PORT`` to pin a port (default ``0`` picks a free one).
Press Ctrl+C to stop.
"""
import http.server
import json
import os
import socketserver
import subprocess
import sys
import urllib.parse
import webbrowser

PAGE = "harness_gui.html"


def _repo_name(root):
    """Best-effort name of the repo enclosing this pack (for the page header).

    Resolution order (first hit wins, resolved once at startup):
    1. ``.repo_name`` written next to this script by the initialize workflow —
       the exact folder that was initialized. Authoritative and deterministic.
    2. Installed layout ``<repo>/.github/<pack>``: the initialized repo is the
       folder that *contains* ``.github`` (two levels up). Taken from the path,
       not from git — ``git rev-parse --show-toplevel`` here can walk *up* into
       an ancestor repo when the initialized folder is not itself a git repo,
       which would show the repo's parent folder instead of the repo.
    3. Source / pack-root layout: ``git rev-parse --show-toplevel``.
    4. Last resort: the pack root's own folder name.
    """
    try:
        with open(os.path.join(root, ".repo_name"), encoding="utf-8") as fh:
            name = fh.read().strip()
        if name:
            return name
    except OSError:  # no override file -> fall through to inference
        pass

    parent = os.path.dirname(root)
    if os.path.basename(parent) == ".github":   # <repo>/.github/<pack>
        return os.path.basename(os.path.dirname(parent))

    try:
        top = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=root, capture_output=True, text=True, timeout=5,
        )
        name = os.path.basename((top.stdout or "").strip())
        if top.returncode == 0 and name:
            return name
    except Exception:  # noqa: BLE001 - git missing / not a repo -> path fallback
        pass
    return os.path.basename(root)


def _pick_paths(mode, root):
    """Open a native file/folder dialog and return the chosen paths.

    Runs in its own short-lived process (see ``--pick`` in ``__main__``) so the
    Tk interpreter never touches the HTTP server's thread/event state. Paths under
    ``root`` are returned repo-relative with forward slashes (e.g.
    ``repo_info/codebase_overview.md``); anything else stays absolute and native.
    """
    import tkinter as tk
    from tkinter import filedialog

    win = tk.Tk()
    win.withdraw()
    win.attributes("-topmost", True)  # surface the dialog above the browser
    try:
        if mode == "dir":
            sel = filedialog.askdirectory(parent=win, title="Select a folder")
            chosen = [sel] if sel else []
        else:
            sel = filedialog.askopenfilenames(parent=win, title="Select file(s)")
            chosen = list(sel)
    finally:
        win.destroy()

    out = []
    for p in chosen:
        ap = os.path.abspath(p)
        rel = None
        try:
            rel = os.path.relpath(ap, root)
        except ValueError:
            rel = None  # different drive on Windows -> keep absolute
        if rel and not rel.startswith(".."):
            out.append(rel.replace(os.sep, "/"))
        else:
            out.append(ap)
    return out


def main():
    root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(root)
    if not os.path.exists(PAGE):
        raise SystemExit("{} not found next to this script ({}).".format(PAGE, root))

    repo_name = _repo_name(root)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass  # keep the console quiet

        def do_GET(self):
            # DNS-rebinding guard: only local Host headers are served.
            host = (self.headers.get("Host") or "").strip()
            hostname = host.rsplit(":", 1)[0] if not host.startswith("[") else host.split("]", 1)[0] + "]"
            if hostname not in ("127.0.0.1", "localhost", "[::1]"):
                self.send_error(403, "Forbidden: non-local Host header")
                return
            path = urllib.parse.urlparse(self.path).path
            if path == "/__pick__":
                self._serve_pick()
                return
            # GET /__repo__ -> {"name": ...}: the page shows it as "mini-harness · <name>".
            if path == "/__repo__":
                self._serve_json({"name": repo_name})
                return
            super().do_GET()

        def _serve_json(self, obj):
            data = json.dumps(obj).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        # GET /__pick__?mode=files|dir -> {"paths": [...]} from a native dialog.
        # We shell out to ``this_file --pick <mode>`` so Tk gets a clean main
        # thread; the dialog blocks this single-threaded server only while open,
        # which is fine for a local single-user tool.
        def _serve_pick(self):
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            mode = "dir" if (qs.get("mode") or ["files"])[0] == "dir" else "files"
            try:
                proc = subprocess.run(
                    [sys.executable, os.path.abspath(__file__), "--pick", mode],
                    capture_output=True, text=True, timeout=600,
                )
                body = (proc.stdout or "").strip() or '{"paths": []}'
            except Exception as e:  # noqa: BLE001 - report any failure to the UI
                body = json.dumps({"paths": [], "error": str(e)})
            data = body.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

    try:
        port = int(os.environ.get("HARNESS_GUI_PORT", "0"))
    except ValueError:
        raise SystemExit(
            "HARNESS_GUI_PORT is not a valid port number: {!r}".format(os.environ["HARNESS_GUI_PORT"])
        )
    socketserver.TCPServer.allow_reuse_address = True
    try:
        httpd = socketserver.TCPServer(("127.0.0.1", port), Handler)
    except OSError as e:
        raise SystemExit("Cannot bind 127.0.0.1:{} — port in use? ({})".format(port, e))
    with httpd:
        url = "http://127.0.0.1:{}/{}".format(httpd.server_address[1], PAGE)
        print("mini-harness Request Builder -> {}".format(url), flush=True)
        print("Press Ctrl+C to stop.", flush=True)
        webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == "__main__":
    # Child-process mode for the native picker: print the chosen paths as JSON and
    # exit. Kept out of main() so importing/serving never pulls in tkinter.
    if "--pick" in sys.argv:
        pick_mode = "dir" if "dir" in sys.argv[sys.argv.index("--pick") + 1:] else "files"
        pick_root = os.path.dirname(os.path.abspath(__file__))
        try:
            print(json.dumps({"paths": _pick_paths(pick_mode, pick_root)}))
        except Exception as e:  # noqa: BLE001 - surface picker errors to the UI
            print(json.dumps({"paths": [], "error": str(e)}))
    else:
        main()
