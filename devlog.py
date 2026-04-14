#!/usr/bin/env python3
"""
DevLog — Single-File CLI
=========================
Persistent AI coding context.
Captures and restores AI coding context, scoped to your local project folder.

All core functionality in one file: CLI commands, context storage,
MCP server, and AI features.

Usage:
    python devlog.py <command> [options]
    devlog <command> [options]          (if aliased)
"""

import os
import sys
import json
import time
import hashlib
import secrets
import subprocess
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ─────────────────────────────────────────────────────────────
# SECTION 1: CONSTANTS & PATHS
# ─────────────────────────────────────────────────────────────

STORE_DIR = ".devlog"
CONTEXT_FILE = "context.json"
CONFIG_FILE = "config.json"


def get_store_path() -> Path:
    return Path.cwd() / STORE_DIR


def get_context_file() -> Path:
    return get_store_path() / CONTEXT_FILE


def get_config_file() -> Path:
    return get_store_path() / CONFIG_FILE


def ensure_store_dir() -> None:
    if not get_store_path().exists():
        print("Error: DevLog not initialized. Run 'devlog init' first.")
        sys.exit(1)


# ─────────────────────────────────────────────────────────────
# SECTION 2: DATA HELPERS
# ─────────────────────────────────────────────────────────────


def generate_id() -> str:
    return secrets.token_hex(8)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_entries() -> list[dict]:
    path = get_context_file()
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return []


def save_entries(entries: list[dict]) -> None:
    get_context_file().write_text(json.dumps(entries, indent=2))


def load_config() -> dict:
    path = get_config_file()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def save_config(config: dict) -> None:
    get_config_file().write_text(json.dumps(config, indent=2))


def relative_time(timestamp: str) -> str:
    try:
        dt = datetime.fromisoformat(timestamp)
        diff = datetime.now(timezone.utc) - dt.replace(tzinfo=timezone.utc)
        minutes = int(diff.total_seconds() / 60)
        hours = minutes // 60
        days = hours // 24

        if minutes < 1:
            return "just now"
        if minutes < 60:
            return f"{minutes}m ago"
        if hours < 24:
            return f"{hours}h ago"
        return f"{days}d ago"
    except Exception:
        return timestamp


def copy_to_clipboard(text: str) -> bool:
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(["pbcopy"], input=text.encode(), check=True)
        elif system == "Linux":
            try:
                subprocess.run(
                    ["xclip", "-selection", "clipboard"],
                    input=text.encode(),
                    check=True,
                )
            except FileNotFoundError:
                subprocess.run(
                    ["xsel", "--clipboard", "--input"],
                    input=text.encode(),
                    check=True,
                )
        elif system == "Windows":
            subprocess.run(["clip"], input=text.encode(), check=True)
        return True
    except Exception:
        return False


def prompt_input(question: str) -> str:
    try:
        return input(question).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return ""


def prompt_multiline(question: str) -> list[str]:
    print(f"{question} (enter each item, empty line to finish):")
    items = []
    while True:
        try:
            line = input("  > ").strip()
            if line == "":
                break
            items.append(line)
        except (EOFError, KeyboardInterrupt):
            print()
            break
    return items


def sorted_entries(entries: list[dict], newest_first: bool = True) -> list[dict]:
    return sorted(
        entries,
        key=lambda e: e.get("timestamp", ""),
        reverse=newest_first,
    )


# ─────────────────────────────────────────────────────────────
# SECTION 3: CORE COMMANDS
# ─────────────────────────────────────────────────────────────


def cmd_init() -> None:
    store = get_store_path()
    if store.exists():
        print("DevLog already initialized in this folder.")
        return

    store.mkdir(parents=True)
    (store / CONTEXT_FILE).write_text("[]")
    (store / CONFIG_FILE).write_text("{}")

    print(f"✅ DevLog initialized at {store}")


def cmd_save(quick_message: Optional[str] = None, auto: bool = False) -> None:
    ensure_store_dir()

    if auto:
        entry = {
            "id": generate_id(),
            "timestamp": now_iso(),
            "message": "Auto-save",
            "task": "Auto-captured session",
            "goal": "",
            "approaches": [],
            "decisions": [],
            "state": "",
            "nextSteps": [],
        }
    elif quick_message:
        entry = {
            "id": generate_id(),
            "timestamp": now_iso(),
            "message": quick_message,
            "task": quick_message,
            "goal": "",
            "approaches": [],
            "decisions": [],
            "state": "",
            "nextSteps": [],
        }
    else:
        print(f"\n📝 Saving context for: {Path.cwd()}\n")

        task = prompt_input("Task (what are you working on?): ")
        goal = prompt_input("Goal (why are you doing this?): ")
        approaches = prompt_multiline("Approaches tried (what you tried, what failed)")
        decisions = prompt_multiline("Key decisions made")
        state = prompt_input("Current state (where did you leave off?): ")
        next_steps = prompt_multiline("Next steps")

        entry = {
            "id": generate_id(),
            "timestamp": now_iso(),
            "message": task,
            "task": task,
            "goal": goal,
            "approaches": approaches,
            "decisions": decisions,
            "state": state,
            "nextSteps": next_steps,
        }

    entries = load_entries()
    entries.append(entry)
    save_entries(entries)

    print(f"\n✅ Context saved (id: {entry['id']})")


def cmd_resume() -> None:
    ensure_store_dir()
    entries = sorted_entries(load_entries())

    if not entries:
        print("No context found. Save some context first.")
        return

    latest = entries[0]
    history = entries[1:4]
    folder = Path.cwd().name

    lines = [f"# DevLog Resume — {folder}\n"]
    lines.append(f"## Current Task\n{latest['task']}\n")

    if latest.get("goal"):
        lines.append(f"## Goal\n{latest['goal']}\n")

    if latest.get("approaches"):
        lines.append("## Approaches Tried")
        for a in latest["approaches"]:
            lines.append(f"- {a}")
        lines.append("")

    if latest.get("decisions"):
        lines.append("## Key Decisions")
        for d in latest["decisions"]:
            lines.append(f"- {d}")
        lines.append("")

    if latest.get("state"):
        lines.append(f"## Current State\n{latest['state']}\n")

    if latest.get("nextSteps"):
        lines.append("## Next Steps")
        for s in latest["nextSteps"]:
            lines.append(f"- {s}")
        lines.append("")

    if latest.get("handoffTo"):
        lines.append(f"## Handoff Note\nThis was handed off to @{latest['handoffTo']}\n")

    if history:
        lines.append(f"## Session History ({len(history)} prior entries)")
        for h in history:
            lines.append(f"- **{h['timestamp']}**: {h['message']}")
        lines.append("")

    lines.append("---")
    lines.append("*Please continue from where I left off. Ask me clarifying questions if needed.*")

    prompt_text = "\n".join(lines)
    copied = copy_to_clipboard(prompt_text)

    print(f"\n📋 Resume prompt:\n")
    print(prompt_text)
    print()

    if copied:
        print("✅ Copied to clipboard! Paste into your AI editor to continue.")
    else:
        print("⚠️  Could not copy to clipboard. Copy the prompt above manually.")


def cmd_log() -> None:
    ensure_store_dir()
    entries = sorted_entries(load_entries())

    if not entries:
        print("No context entries found.")
        return

    print(f"\n📖 Context log ({len(entries)} entries):\n")

    for i, e in enumerate(entries, 1):
        ago = relative_time(e.get("timestamp", ""))
        print(f"  {i}. [{e['id'][:8]}] {ago}")
        print(f"     {e['message']}")
        if e.get("state"):
            print(f"     State: {e['state'][:80]}...")
        print()


# ─────────────────────────────────────────────────────────────
# SECTION 4: TEAM COMMANDS
# ─────────────────────────────────────────────────────────────


def cmd_handoff(target_user: str) -> None:
    ensure_store_dir()

    print(f"\n🤝 Creating handoff note for @{target_user}:\n")

    task = prompt_input("Task summary: ")
    state = prompt_input("Current state: ")
    next_steps = prompt_multiline("What they should do next")
    caveats = prompt_input("Any warnings or gotchas: ")

    entry = {
        "id": generate_id(),
        "timestamp": now_iso(),
        "message": f"Handoff to @{target_user}: {task}",
        "task": task,
        "goal": "",
        "approaches": [],
        "decisions": [f"⚠️ {caveats}"] if caveats else [],
        "state": state,
        "nextSteps": next_steps,
        "handoffTo": target_user,
    }

    entries = load_entries()
    entries.append(entry)
    save_entries(entries)

    print(f"\n✅ Handoff note created for @{target_user}.")
    print(f"   They can run 'devlog resume' in this folder to pick up.")


def cmd_watch() -> None:
    ensure_store_dir()
    config = load_config()
    interval = int(config.get("watchInterval", 300))

    print(f"👁️  Watching for file changes (auto-save every {interval}s)...")
    print("   Press Ctrl+C to stop.\n")

    last_snapshot = _folder_snapshot()

    try:
        while True:
            time.sleep(interval)
            current = _folder_snapshot()
            if current != last_snapshot:
                print("\n🔄 Changes detected, auto-saving...")
                cmd_save(auto=True)
                last_snapshot = current
    except KeyboardInterrupt:
        print("\n👁️  Watch stopped.")


def _folder_snapshot() -> str:
    """Get a quick hash of file modification times in the project."""
    parts = []
    cwd = Path.cwd()
    try:
        for item in sorted(cwd.iterdir()):
            if item.name.startswith(".") or item.name in ("node_modules", "__pycache__", ".venv", "venv"):
                continue
            try:
                if item.is_file():
                    parts.append(f"{item.name}:{item.stat().st_mtime}")
                elif item.is_dir():
                    for child in sorted(item.iterdir()):
                        if child.is_file() and not child.name.startswith("."):
                            parts.append(f"{child.name}:{child.stat().st_mtime}")
            except OSError:
                continue
    except OSError:
        pass
    return hashlib.md5("|".join(parts).encode()).hexdigest()


# ─────────────────────────────────────────────────────────────
# SECTION 5: AI-POWERED COMMANDS
# ─────────────────────────────────────────────────────────────


def _get_ai_key() -> str:
    config = load_config()
    key = config.get("aiApiKey") or os.environ.get("DEVLOG_AI_KEY")
    if not key:
        print("Error: No AI API key configured.")
        print("Set via: devlog config set aiApiKey <your-key>")
        print("Or:      export DEVLOG_AI_KEY=<your-key>")
        sys.exit(1)
    return key


def _call_ai(system_prompt: str, user_prompt: str) -> str:
    try:
        import urllib.request
    except ImportError:
        print("Error: urllib not available.")
        sys.exit(1)

    api_key = _get_ai_key()
    config = load_config()
    base_url = config.get("aiBaseUrl", "https://api.openai.com/v1")
    model = config.get("aiModel", "gpt-4o-mini")

    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": 2000,
    }).encode()

    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            return data.get("choices", [{}])[0].get("message", {}).get("content", "(no response)")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"AI API error: {e.code} {e.reason}")


def cmd_summarize() -> None:
    ensure_store_dir()
    print("🤖 Generating AI summary from recent context...\n")

    entries = sorted_entries(load_entries())[:5]
    context_str = (
        "\n".join(f"[{e['timestamp']}] {e['task']}: {e.get('state', '')}" for e in entries)
        if entries
        else "(no prior context)"
    )

    system = "You are a concise technical writer. Summarize the developer's recent work into a structured context entry with: Task, Goal, Key Decisions, Current State, and Next Steps."
    user = f"Recent context entries:\n{context_str}\n\nGenerate a structured context summary."

    try:
        summary = _call_ai(system, user)
        print(summary)

        answer = prompt_input("\nSave this as a context entry? (y/n): ")
        if answer.lower() == "y":
            entry = {
                "id": generate_id(),
                "timestamp": now_iso(),
                "message": "AI-generated summary",
                "task": summary,
                "goal": "",
                "approaches": [],
                "decisions": [],
                "state": "",
                "nextSteps": [],
            }
            all_entries = load_entries()
            all_entries.append(entry)
            save_entries(all_entries)
            print("✅ Saved.")
    except Exception as e:
        print(f"AI error: {e}")


def cmd_suggest() -> None:
    ensure_store_dir()
    print("🤖 Analyzing context for suggestions...\n")

    entries = sorted_entries(load_entries())[:3]
    if not entries:
        print("No context entries found. Save some context first.")
        return

    context_str = "\n---\n".join(
        f"Task: {e['task']}\nState: {e.get('state', '')}\nDecisions: {', '.join(e.get('decisions', []))}"
        for e in entries
    )

    system = "You are a senior developer advisor. Based on the developer's context, suggest concrete next steps, potential issues to watch for, and improvements."
    user = f"Recent context:\n{context_str}\n\nSuggest next steps and potential issues."

    try:
        print(_call_ai(system, user))
    except Exception as e:
        print(f"AI error: {e}")


def cmd_compress() -> None:
    ensure_store_dir()
    entries = load_entries()

    if len(entries) < 3:
        print("Not enough entries to compress (need at least 3).")
        return

    print(f"🤖 Compressing {len(entries)} entries into a summary...\n")

    context_str = "\n".join(
        f"[{e['timestamp']}] {e['task']}: {e.get('state', '')}"
        for e in sorted_entries(entries, newest_first=False)
    )

    system = "You are a technical writer. Compress the following context history into a single, concise summary that preserves all important decisions, approaches tried, and current state. Output as JSON with fields: task, goal, approaches (array), decisions (array), state, nextSteps (array)."

    try:
        result = _call_ai(system, context_str)
        print("Compressed summary:\n", result)

        answer = prompt_input("\nReplace all entries with this compressed summary? (y/n): ")
        if answer.lower() == "y":
            try:
                parsed = json.loads(result)
                compressed = {
                    "id": generate_id(),
                    "timestamp": now_iso(),
                    "message": f"Compressed from {len(entries)} entries",
                    "task": parsed.get("task", ""),
                    "goal": parsed.get("goal", ""),
                    "approaches": parsed.get("approaches", []),
                    "decisions": parsed.get("decisions", []),
                    "state": parsed.get("state", ""),
                    "nextSteps": parsed.get("nextSteps", []),
                }
                save_entries([compressed])
                print("✅ Context compressed.")
            except json.JSONDecodeError:
                print("Could not parse AI response as JSON.")
    except Exception as e:
        print(f"AI error: {e}")


# ─────────────────────────────────────────────────────────────
# SECTION 6: CONFIGURATION
# ─────────────────────────────────────────────────────────────


def cmd_config_set(key: str, value: str) -> None:
    ensure_store_dir()
    config = load_config()
    config[key] = value
    save_config(config)
    print(f"✅ Config set: {key} = {value}")


def cmd_config_list() -> None:
    ensure_store_dir()
    config = load_config()

    if not config:
        print("No configuration set. Defaults are used.")
        return

    print("\n⚙️  DevLog Configuration:\n")
    for key, val in config.items():
        display = "****" if "key" in key.lower() else val
        print(f"  {key}: {display}")


# ─────────────────────────────────────────────────────────────
# SECTION 7: MCP SERVER
# ─────────────────────────────────────────────────────────────


def cmd_mcp() -> None:
    """
    Minimal MCP (Model Context Protocol) server.
    Communicates via stdin/stdout using JSON-RPC 2.0.
    Exposes tools: devlog_save, devlog_resume, devlog_log
    Exposes resource: devlog://context
    """
    import io
    import select

    # Use unbuffered binary streams
    stdin = io.open(sys.stdin.fileno(), "rb", buffering=0)
    stdout = io.open(sys.stdout.fileno(), "wb", buffering=0)

    def _log(msg: str) -> None:
        """Log to stderr so it shows in Claude Desktop logs."""
        sys.stderr.write(f"[devlog-mcp] {msg}\n")
        sys.stderr.flush()

    def send(obj: dict) -> None:
        body = json.dumps(obj).encode("utf-8")
        header = f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8")
        stdout.write(header + body)
        stdout.flush()

    def respond(msg_id, result):
        send({"jsonrpc": "2.0", "id": msg_id, "result": result})

    def respond_error(msg_id, code, message):
        send({"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}})

    def read_exact(n: int) -> bytes:
        """Read exactly n bytes from stdin."""
        data = b""
        while len(data) < n:
            chunk = stdin.read(n - len(data))
            if not chunk:
                raise EOFError("stdin closed")
            data += chunk
        return data

    def read_line() -> str:
        """Read a single line ending with \\r\\n from stdin."""
        line = b""
        while True:
            byte = stdin.read(1)
            if not byte:
                raise EOFError("stdin closed")
            line += byte
            if line.endswith(b"\r\n"):
                return line[:-2].decode("utf-8")

    _log("MCP server starting...")

    while True:
        try:
            # 1. Read headers until we hit an empty line
            content_length = None
            while True:
                header_line = read_line()
                if header_line == "":
                    break  # End of headers
                if header_line.lower().startswith("content-length:"):
                    content_length = int(header_line.split(":", 1)[1].strip())

            if content_length is None:
                _log("Warning: no Content-Length header, skipping message")
                continue

            # 2. Read the exact body
            body = read_exact(content_length).decode("utf-8")

            # 3. Parse and handle
            try:
                msg = json.loads(body)
                _log(f"Received: {msg.get('method', 'response')} (id={msg.get('id')})")
                _handle_mcp(msg, respond, respond_error)
            except json.JSONDecodeError as e:
                _log(f"JSON parse error: {e}")

        except EOFError:
            _log("stdin closed, shutting down")
            break
        except KeyboardInterrupt:
            _log("interrupted, shutting down")
            break
        except Exception as e:
            _log(f"Error: {e}")
            break


def _handle_mcp(msg, respond, respond_error):
    msg_id = msg.get("id")
    method = msg.get("method", "")
    params = msg.get("params", {})

    if method == "initialize":
        respond(msg_id, {
            "protocolVersion": params.get("protocolVersion", "2024-11-05"),
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {"subscribe": False, "listChanged": False},
            },
            "serverInfo": {"name": "devlog", "version": "1.0.0"},
        })

    elif method == "tools/list":
        respond(msg_id, {
            "tools": [
                {
                    "name": "devlog_save",
                    "description": "Save current coding context",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "message": {"type": "string", "description": "Context message"},
                            "task": {"type": "string", "description": "Current task"},
                            "state": {"type": "string", "description": "Current state"},
                        },
                    },
                },
                {
                    "name": "devlog_resume",
                    "description": "Get the latest context",
                    "inputSchema": {"type": "object", "properties": {}},
                },
                {
                    "name": "devlog_log",
                    "description": "List all context entries",
                    "inputSchema": {"type": "object", "properties": {}},
                },
            ]
        })

    elif method == "tools/call":
        tool = params.get("name", "")
        args = params.get("arguments", {})

        if tool == "devlog_save":
            # Auto-init if .devlog/ doesn't exist yet
            store = get_store_path()
            if not store.exists():
                store.mkdir(parents=True)
                (store / CONTEXT_FILE).write_text("[]")
                (store / CONFIG_FILE).write_text("{}")

            entry = {
                "id": generate_id(),
                "timestamp": now_iso(),
                "message": args.get("message", "MCP save"),
                "task": args.get("task", args.get("message", "")),
                "goal": args.get("goal", ""),
                "approaches": args.get("approaches", []),
                "decisions": args.get("decisions", []),
                "state": args.get("state", ""),
                "nextSteps": args.get("nextSteps", []),
            }
            entries = load_entries()
            entries.append(entry)
            save_entries(entries)
            respond(msg_id, {"content": [{"type": "text", "text": f"Context saved (id: {entry['id']})"}]})

        elif tool == "devlog_resume":
            entries = sorted_entries(load_entries())
            latest = entries[0] if entries else None
            text = json.dumps(latest, indent=2) if latest else "No context found."
            respond(msg_id, {"content": [{"type": "text", "text": text}]})

        elif tool == "devlog_log":
            entries = sorted_entries(load_entries())
            respond(msg_id, {"content": [{"type": "text", "text": json.dumps(entries, indent=2)}]})

        else:
            respond_error(msg_id, -32602, f"Unknown tool: {tool}")

    elif method == "resources/list":
        respond(msg_id, {
            "resources": [{
                "uri": "devlog://context",
                "name": "Current DevLog Context",
                "description": "Latest context entry",
                "mimeType": "application/json",
            }]
        })

    elif method == "resources/read":
        uri = params.get("uri", "")
        if uri == "devlog://context":
            entries = sorted_entries(load_entries())
            latest = entries[0] if entries else {"message": "No context found"}
            respond(msg_id, {
                "contents": [{
                    "uri": "devlog://context",
                    "mimeType": "application/json",
                    "text": json.dumps(latest, indent=2),
                }]
            })
        else:
            respond_error(msg_id, -32602, f"Unknown resource: {uri}")

    elif method == "notifications/initialized":
        pass

    else:
        if msg_id is not None:
            respond_error(msg_id, -32601, f"Method not found: {method}")


# ─────────────────────────────────────────────────────────────
# SECTION 8: CLI ROUTER
# ─────────────────────────────────────────────────────────────

HELP = """
DevLog — Persistent AI coding context

USAGE:
  devlog <command> [options]

CORE COMMANDS:
  init                    Initialize DevLog in current folder
  save [message]          Save context (interactive or quick mode)
  save --auto             Auto-save (non-interactive)
  resume                  Generate AI prompt & copy to clipboard
  log                     View context history

TEAM:
  handoff <@user>         Create handoff note for a teammate
  watch                   Auto-save context on file changes

AI-POWERED (requires API key):
  summarize               AI-generate context from recent entries
  suggest                 AI suggest next steps based on context
  compress                Compress context history into summary

MCP SERVER:
  mcp                     Start MCP server (stdin/stdout)

CONFIGURATION:
  config set <key> <val>  Set preferences
  config list             View all configuration

CONFIG KEYS:
  aiApiKey                LLM API key (or use DEVLOG_AI_KEY env var)
  aiModel                 Model name (default: gpt-4o-mini)
  aiBaseUrl               API base URL
  watchInterval           Watch interval in seconds (default: 300)
"""


def main() -> None:
    args = sys.argv[1:]

    if not args or args[0] in ("--help", "-h"):
        print(HELP)
        return

    cmd = args[0]

    if cmd == "init":
        cmd_init()

    elif cmd == "save":
        if "--auto" in args:
            cmd_save(auto=True)
        elif len(args) > 1 and not args[1].startswith("--"):
            cmd_save(quick_message=" ".join(args[1:]))
        else:
            cmd_save()

    elif cmd == "resume":
        cmd_resume()

    elif cmd == "log":
        cmd_log()

    elif cmd == "handoff":
        if len(args) < 2:
            print("Usage: devlog handoff <@user>")
            sys.exit(1)
        cmd_handoff(args[1].lstrip("@"))

    elif cmd == "watch":
        cmd_watch()

    elif cmd == "summarize":
        cmd_summarize()

    elif cmd == "suggest":
        cmd_suggest()

    elif cmd == "compress":
        cmd_compress()

    elif cmd == "mcp":
        cmd_mcp()

    elif cmd == "config":
        if len(args) >= 4 and args[1] == "set":
            cmd_config_set(args[2], " ".join(args[3:]))
        elif len(args) >= 2 and args[1] == "list":
            cmd_config_list()
        else:
            print("Usage: devlog config set <key> <value> | devlog config list")

    else:
        print(f"Unknown command: {cmd}")
        print(HELP)
        sys.exit(1)


if __name__ == "__main__":
    main()