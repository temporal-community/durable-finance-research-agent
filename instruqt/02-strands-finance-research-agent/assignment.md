---
slug: strands-finance-research-agent
id: ifvxy4zfb9i9
type: challenge
title: 'Module 2: A Finance Research Agent'
teaser: Three data tools, a research brief and a memo. Then see exactly what a crash
  costs.
notes:
- type: text
  contents: |-
    # The agent has made three paid calls. The process dies. What do you pay for again?

    A research memo takes several model calls and several data fetches. Each one costs time,
    and the model calls cost money.

    You are about to build the agent that makes them. Then you will kill it halfway.
- type: text
  contents: |-
    # Sample data only

    The tickers are fictional: ACME, GLBX and INIT. The numbers are made up.
    Nothing here is financial advice.
tabs:
- id: vhgpzaiuqsgr
  title: Editor
  type: service
  hostname: workshop
  path: /?folder=/root/workshop/modules/02-strands-finance-research-agent/exercise
  port: 8080
- id: zneanrrreyur
  title: Terminal
  type: terminal
  hostname: workshop
  workdir: /root/workshop
- id: gsbvlrwodert
  title: Research Desk
  type: service
  hostname: workshop
  path: /
  port: 8000
- id: 7xgmt8jiz3zv
  title: Network Control Panel
  type: service
  hostname: workshop
  path: /
  port: 5050
difficulty: intermediate
timelimit: 1500
enhanced_loading: null
---

# A Finance Research Agent

Same Strands agent, now with something to do. It pulls a quote, filings and news for a ticker,
then writes a memo with sources.

> [!NOTE]
> **Your tabs.**
> - [button label="Editor" background="#444CE7"](tab-0) is your working copy.
> - [button label="Terminal" background="#444CE7"](tab-1) runs the agent.
> - [button label="Research Desk" background="#444CE7"](tab-2) runs it in a browser.
> - [button label="Network Control Panel" background="#444CE7"](tab-3) cuts the LLM gateway and breaks the data API.

## The Code

Two files in the [button label="Editor" background="#444CE7"](tab-0) tab:

- `tools.py` has `get_quote`, which calls the mock market data API. It is your template.
- `agent.py` builds the model and the agent.

There are three `TODO` blocks to uncomment: two tools in `tools.py`, then the system prompt and the
agent in `agent.py`. Read the prompt as you go. It carries the domain expertise: the memo format,
the sourcing rule, and the ban on buy or sell calls.

Check your work in the [button label="Terminal" background="#444CE7"](tab-1) tab:

```bash,run
just test 2
```

## Run It

```bash,run
just m2 "Write a research memo on ACME."
```

Watch the output. The agent announces each tool call before it writes anything:

```bash,nocopy
Tool #1: get_quote
Tool #2: get_filings
Tool #3: get_news
## Summary
...
## Sources
- get_quote, get_filings, get_news
Sample data. Not financial advice.
```

Try `GLBX`, then `INIT`. Then ask for a ticker that does not exist:

```bash,run
just m2 "Write a research memo on ZZZZ."
```

The data API answers 404. The agent should say what is missing and write nothing it cannot source.

## Break It

Open the [button label="Network Control Panel" background="#444CE7"](tab-3) tab.

**Flaky data.** Set **Market data API** to `unavailable (503)` and apply it. Run the memo again.
The tools fail, and the agent has to work around it. Set it back to `ok`.

**No model.** Cut the **LLM gateway**. Run the memo again. It dies on the first model call.

Now do the expensive version. Allow the gateway, start a run, and cut the gateway while the tool
lines are still printing. The next model call fails and the run ends. Allow the gateway and run it again.

> What did the second run pay for again?

**Answer.** All of it. The first model call, every tool call, every token. The process held the only record of
progress, and the process is gone. Nothing in this script can say "I already did that."

## Summary

| | Plain Strands script |
|---|---|
| Data API returns 503 | Tool fails, agent improvises |
| Unknown ticker (404) | Same path as any other failure |
| Model call fails mid-run | Run lost, paid work repeated |
| Where progress lives | Process memory |

Click **Check** when done. In module 3 the same agent runs under Temporal.
