# local-atlassian-mcp

Simple MCP server for reading Jira issues and Confluence pages.

## Installation

```bash
pnpm install
pnpm build
pnpm link --global
```

## MCP Configuration
### Via Claude add MCP command:
```shell
claude mcp add atlassian --scope user \
  --env ATLASSIAN_URL="https://your-domain.atlassian.net" \
  --env ATLASSIAN_EMAIL="your-email@company.com" \
  --env ATLASSIAN_TOKEN="your-api-token" \
  -- local-atlassian-mcp
```

### Claude-compatible MCP Configuration (cli)
```bash
claude mcp add --transport stdio atlassian --env ATLASSIAN_URL="https://your-company.atlassian.net" --env ATLASSIAN_EMAIL="your-email@company.com" --env ATLASSIAN_TOKEN="your-api-token" -- local-atlassian-mcp
```

### Claude-compatible MCP Configuration (json)
```json
{
  "mcpServers": {
    "atlassian": {
      "command": "local-atlassian-mcp",
      "env": {
        "ATLASSIAN_URL": "https://your-company.atlassian.net",
        "ATLASSIAN_EMAIL": "your-email@company.com",
        "ATLASSIAN_TOKEN": "your-api-token"
      }
    }
  }
}
```
### Codex-compatible MCP Configuration (toml)
```toml
[mcp_servers.atlassian]
command = "local-atlassian-mcp"
[mcp_servers.atlassian.env]
ATLASSIAN_URL = "https://your-company.atlassian.net"
ATLASSIAN_EMAIL = "your-email@company.com"
ATLASSIAN_TOKEN = "your-api-token"
```

## Getting an API Token

1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Copy the token and use it as `ATLASSIAN_TOKEN`

## Tools

| Tool                  | Description                              |
| --------------------- | ---------------------------------------- |
| `get_jira_issue`      | Get a Jira issue by key (e.g., PROJ-123) |
| `search_jira`         | Search Jira issues using JQL             |
| `get_my_jira_issues`  | Get issues assigned to current user      |
| `get_confluence_page` | Get a Confluence page by ID              |
| `search_confluence`   | Search Confluence pages by text          |
