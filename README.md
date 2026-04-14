# DevLog

Persistent AI coding context. Never lose track of where you left off.

DevLog captures and restores your coding context so you (or your AI assistant) can pick up exactly where you left off — across sessions, tools, and teammates.

## The Problem

Every time you close your AI editor, switch branches, or hand off work, you lose context. You spend the first 10 minutes of every session re-explaining what you were doing, what you tried, and what's next. DevLog fixes that.

## Quick Start

```bash
# 1. Clone and navigate
git clone https://github.com/umangelucidata20/DevLogs.git
cd DevLogs

# 2. Initialize in your project
cd /path/to/your-project
python3 /path/to/devlog.py init

# 3. Save your context before ending a session
python3 devlog.py save

# 4. Resume next time
python3 devlog.py resume
```

### Optional: Create an alias

Add to your `~/.zshrc` or `~/.bashrc`:

```bash
alias devlog="python3 /path/to/devlog.py"
```

Then use it anywhere:

```bash
devlog init
devlog save
devlog resume
```

## Commands

### Core

| Command | Description |
|---|---|
| `devlog init` | Initialize DevLog in the current project folder |
| `devlog save` | Interactively save your current context (task, goal, decisions, state, next steps) |
| `devlog save "message"` | Quick-save with a one-line message |
| `devlog save --auto` | Non-interactive auto-save (for scripts/watchers) |
| `devlog resume` | Generate an AI-ready prompt from your latest context and copy to clipboard |
| `devlog log` | View all saved context entries |

### Team

| Command | Description |
|---|---|
| `devlog handoff @user` | Create a structured handoff note for a teammate |
| `devlog watch` | Auto-save context when files change |

### AI-Powered (requires API key)

| Command | Description |
|---|---|
| `devlog summarize` | AI-generate a structured summary from recent context |
| `devlog suggest` | Get AI-suggested next steps based on your context |
| `devlog compress` | Compress multiple entries into a single summary |

### Configuration

| Command | Description |
|---|---|
| `devlog config set <key> <value>` | Set a configuration value |
| `devlog config list` | View current configuration |

**Config keys:**

| Key | Description | Default |
|---|---|---|
| `aiApiKey` | LLM API key (or set `DEVLOG_AI_KEY` env var) | — |
| `aiModel` | Model name | `gpt-4o-mini` |
| `aiBaseUrl` | API base URL | `https://api.openai.com/v1` |
| `watchInterval` | Watch auto-save interval (seconds) | `300` |

## MCP Server

DevLog includes a built-in [Model Context Protocol](https://modelcontextprotocol.io/) server, allowing AI assistants like Claude to directly save and retrieve your context.

### Setup with Claude Desktop / Claude Code

Add to your MCP configuration:

```json
{
  "mcpServers": {
    "devlog": {
      "command": "python3",
      "args": ["/absolute/path/to/devlog.py", "mcp"]
    }
  }
}
```

### Exposed MCP Tools

| Tool | Description |
|---|---|
| `devlog_save` | Save coding context with task, state, and decisions |
| `devlog_resume` | Retrieve the latest saved context |
| `devlog_log` | List all context entries |

### Exposed MCP Resources

| URI | Description |
|---|---|
| `devlog://context` | Latest context entry (JSON) |

## How It Works

```
You code → Save context → Close editor → Reopen later → Resume → AI has full context
```

DevLog stores everything locally in a `.devlog/` directory inside your project:

```
your-project/
  .devlog/
    context.json    # All saved context entries
    config.json     # Local configuration
  src/
  ...
```

Each context entry captures:
- **Task** — What you're working on
- **Goal** — Why you're doing it
- **Approaches** — What you tried (including what failed)
- **Decisions** — Key choices you made
- **State** — Where you left off
- **Next Steps** — What to do next

## Requirements

- Python 3.10+
- No external dependencies (standard library only)

