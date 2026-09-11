---
name: chrome-devtools-mcp
description: Wire up the Chrome DevTools MCP server so Claude Code can inspect a live browser session — DOM, network requests, console output, and performance metrics. Use when debugging a web app, a failing browser test, or an unexplained network/auth issue in the browser.
---

# Chrome DevTools MCP

## Overview

Chrome DevTools MCP is an MCP server that connects an AI agent directly to Chrome DevTools for remote debugging — inspecting live browser sessions and reading DevTools data programmatically.

**Repository:** [ChromeDevTools/chrome-devtools-mcp](https://github.com/ChromeDevTools/chrome-devtools-mcp)

## What It Does

1. **Live browser session debugging** — connect to a running Chrome instance and read Elements, Network, Console, and Performance data while the browser is open
2. **Automated web debugging** — inspect DOM nodes, analyze requests/responses, capture performance metrics, read console errors, execute JS in page context
3. **Hybrid manual + AI debugging** — you inspect a page yourself, select an element or request, then ask the agent to investigate that exact context

## Why It's Worth Adding

It **complements** browser automation rather than duplicating it:

| Tool | Strength |
|---|---|
| Playwright | Automation — navigating, filling forms, clicking, asserting |
| Chrome DevTools MCP | Debugging — inspecting live state, network analysis, performance |

Together: automate the workflow, then debug it in-session without leaving the agent.

## Setup

Add to your MCP server config:

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": ["chrome-devtools-mcp@latest", "--autoConnect"]
    }
  }
}
```

**Requirements:**
- Node.js (for `npx`)
- Chrome 144+ for the `--autoConnect` flag; older versions work via manual remote debugging
- Remote debugging enabled: `chrome://inspect/#remote-debugging`
- Chrome running normally (not headless)

## Limitations

- **Chrome only** — no Safari, Firefox, or Edge
- **Not headless-friendly** — Chrome prompts for permission on each connection and shows the "controlled by test software" banner, so it's unsuited to fully unattended runs
- **Partial panel coverage** — Elements and Network are exposed; other panels are being added progressively

## Use Case Examples

**Debugging a failed test**
```
Playwright test fails on a selector assertion
→ "Inspect the DOM at selector #widget-container"
→ MCP returns actual DOM structure, classes, computed styles
→ Diagnose why the selector missed, fix, rerun
```

**Network request debugging**
```
App making unexpected API calls
→ "What requests failed with 401?"
→ MCP returns failed requests, status codes, headers
→ Identify the auth token issue
```

**Performance analysis**
```
Page slow in production
→ "Get performance metrics for this page"
→ MCP returns FCP, LCP, CLS timings
→ Locate the bottleneck
```

## References

- [Chrome DevTools MCP: Debug your browser session](https://developer.chrome.com/blog/chrome-devtools-mcp-debug-your-browser-session)
- [Chrome remote debugging docs](https://developer.chrome.com/docs/devtools/remote-debugging)
