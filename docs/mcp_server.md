# MCP Server

The Rapidata MCP server lets an MCP-capable agent (Claude Desktop, Cursor, an
IDE assistant, or your own client) run human labeling tasks on Rapidata
directly through tool calls — without writing SDK code.

It is a thin wrapper over this SDK and currently exposes the core loop: create a
classification or comparison task, start it, poll its status, and fetch results.

## Install and run

```bash
pip install "rapidata[mcp]"
```

The server authenticates with the same credentials as the SDK. Set your client
credentials in the environment:

```bash
export RAPIDATA_CLIENT_ID="..."
export RAPIDATA_CLIENT_SECRET="..."
```

Add it to your MCP client's configuration:

```json
{
  "mcpServers": {
    "rapidata": {
      "command": "rapidata-mcp",
      "env": {
        "RAPIDATA_CLIENT_ID": "...",
        "RAPIDATA_CLIENT_SECRET": "..."
      }
    }
  }
}
```

That's it — the agent can now create and manage labeling tasks.

## Tools

| Tool | What it does |
|------|--------------|
| `create_classification_task` | Create a task where humans pick one option per item. Created in draft; does not spend. |
| `create_comparison_task` | Create a pairwise comparison task (choose between two items). Created in draft; does not spend. |
| `run_task` | Start collecting responses. **This is the step that spends.** |
| `get_task_status` | Current status of a task. |
| `get_task_results` | Fetch results — partial while running, final once complete. Never blocks. |
| `list_tasks` | List your most recent tasks. |
| `pause_task` | Pause a running task to stop collecting responses. |

### Spending is an explicit step

Creating a task never spends. `create_*` returns `total_responses` (the number
of human responses that will be collected) and a `details_url` to inspect the
task. Only `run_task` starts collection. Have the agent confirm the cost before
calling it.

### Datapoints are URLs

Provide datapoints as publicly reachable URLs (image, video, audio, or text).
Local file upload is not supported by the server.

### Results never block

`get_task_results` returns immediately whatever the task's state. While the task
is processing it returns the partial snapshot collected so far
(`result_status: "partial"`); once finished it returns the final aggregated
results (`result_status: "complete"`). Per-annotator detail is omitted unless
you pass `include_details=true`.

## Notes

- Use `python -m rapidata.mcp` if you prefer not to rely on the console script.
- The transport defaults to stdio; set `RAPIDATA_MCP_TRANSPORT=streamable-http`
  to serve over HTTP.
