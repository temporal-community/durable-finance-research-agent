---
slug: strands-agent-basics
id: gwxpvff6z68l
type: challenge
title: 'Module 1: A Simple Strands Agent'
teaser: A model, a prompt and one tool. Twelve lines of Strands, then pull the network
  out from under it.
notes:
- type: text
  contents: |-
    # What happens when the model is unreachable?

    An agent is a loop around a model call. Everything it knows, it knows because that call came back.

    You are about to write the smallest one that works. Then you will cut the line.
- type: text
  contents: |-
    # The desk

    Ledger Capital runs a fictional research desk. This workshop is for demo purposes only: all data is invented sample
    data, not real. Nothing you build is financial advice.
tabs:
- id: jxpcxd2vnks0
  title: Editor
  type: service
  hostname: workshop
  path: /?folder=/root/workshop/modules/01-strands-agent-basics/exercise
  port: 8080
- id: mkhhxtasfjex
  title: Terminal
  type: terminal
  hostname: workshop
  workdir: /root/workshop
- id: i4jn63l4uptb
  title: Research Desk
  type: service
  hostname: workshop
  path: /
  port: 8000
- id: 0vtgapoa3y7a
  title: Network Control Panel
  type: service
  hostname: workshop
  path: /
  port: 5050
difficulty: basic
timelimit: 1200
enhanced_loading: null
---

# A Simple Strands Agent

A Strands agent is a model, a system prompt and a list of tools. You will build one that answers
a question by calling a tool, then watch it fail when the model goes away.

> [!NOTE]
> **Your tabs.**
> - [button label="Editor" background="#444CE7"](tab-0) is your working copy. It saves as you type.
> - [button label="Terminal" background="#444CE7"](tab-1) runs the agent.
> - [button label="Research Desk" background="#444CE7"](tab-2) runs the same agent in a browser.
> - [button label="Network Control Panel" background="#444CE7"](tab-3) cuts the LLM gateway.

## The Code

Open `agent.py` in the [button label="Editor" background="#444CE7"](tab-0) tab.

- `SYSTEM_PROMPT` tells the model who it is.
- `percent_change` is a tool. The docstring and type hints become the schema the model sees.
- `build_agent` is empty. That is your job.

## Write the Agent

Do **TODO 1** and **TODO 2** in `build_agent`. Each one is a block to uncomment.

Check your work in the [button label="Terminal" background="#444CE7"](tab-1) tab:

```bash,run
just test 1
```

```bash,nocopy
..                                                                       [100%]
2 passed
```

## Run It

```bash,run
just m1 "Price moved from 98.2 to 112.4. What is the percent change?"
```

The reply streams in. The model does not do the arithmetic. It calls `percent_change` and reports
what the tool returns.

```bash,nocopy
The percent change is 14.5%.
```

Open the [button label="Research Desk" background="#444CE7"](tab-2) tab, pick **1 Basic agent**, and run the same
prompt. Same code, different front door.

## Break It

Open the [button label="Network Control Panel" background="#444CE7"](tab-3) tab and cut the **LLM gateway**.
Run the agent again in the [button label="Terminal" background="#444CE7"](tab-1) tab:

```bash,run
just m1 "Price moved from 98.2 to 112.4. What is the percent change?"
```

It fails within seconds:

```bash,nocopy
litellm.ServiceUnavailableError: ... [Workshop proxy] LLM gateway is currently disabled.
```

The proxy answers every call to the gateway with a 503.

> Your agent is one function call. Who retries it?

**Answer.** Nobody. The script has no retry loop, no record of what it already did, and no way to pick up
later. The process ends and the question goes unanswered.

Allow the gateway again in the control panel before you move on.

## Summary

| | Plain Strands script |
|---|---|
| Model call fails | Script raises and exits |
| Where the conversation lives | Process memory |
| Process dies | Everything is gone |
| Retries you wrote | None |

Click **Check** when done. Module 2 gives the agent real work to lose.
