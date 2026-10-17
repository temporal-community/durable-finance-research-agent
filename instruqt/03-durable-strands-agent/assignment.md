---
slug: durable-strands-agent
id: ncnil5nuolbk
type: challenge
title: 'Module 3: Make It Durable'
teaser: Run the research agent as a Temporal Workflow. Cut the network, kill the worker,
  wait on a human, lose nothing.
notes:
- type: text
  contents: |-
    # The memo is ready. Compliance is at lunch. What is the Workflow doing?

    The agent finished its research. A person has to approve the memo before it goes anywhere.
    That person might take four hours. Or four days.

    You are about to find out what a Workflow does while it waits.
- type: text
  contents: |-
    # Same agent, different home

    The Strands agent from module 2 moves into a Temporal Workflow.
    Same prompt, same tools. Watch what changes when things break.

    Demo only: the tickers are invented (none of the companies is publicly listed), and every number, filing and headline is invented and not real.
    Nothing here is financial advice.
tabs:
- id: dc0tjsntonlz
  title: Editor
  type: service
  hostname: workshop
  path: /?folder=/root/workshop/modules/03-durable-strands-agent/exercise
  port: 8080
- id: rmclsiavkvvs
  title: Worker
  type: terminal
  hostname: workshop
  workdir: /root/workshop
- id: kl5hzjstohyj
  title: Starter
  type: terminal
  hostname: workshop
  workdir: /root/workshop
- id: mx14ln0sjj8w
  title: Research Desk
  type: service
  hostname: workshop
  path: /
  port: 8000
- id: f0biphkzivfv
  title: Temporal UI
  type: service
  hostname: workshop
  path: /
  port: 8233
- id: z1ceww4voaix
  title: Network Control Panel
  type: service
  hostname: workshop
  path: /
  port: 5050
difficulty: advanced
timelimit: 2700
enhanced_loading: null
---

# Make It Durable

Same agent, same tools, same prompt. What changes is where it runs. A Workflow drives the agent,
a worker executes it, and Temporal records every step.

> [!NOTE]
> **Your tabs.**
> - [button label="Editor" background="#444CE7"](tab-0) is your working copy.
> - [button label="Worker" background="#444CE7"](tab-1) runs the worker. It blocks while it polls.
> - [button label="Starter" background="#444CE7"](tab-2) starts workflows and sends decisions.
> - [button label="Research Desk" background="#444CE7"](tab-3) shows your memos and the Approve and Reject buttons.
> - [button label="Temporal UI" background="#444CE7"](tab-4) is the Event History.
> - [button label="Network Control Panel" background="#444CE7"](tab-5) cuts the LLM gateway and breaks the data API.

## What Changed

Open the [button label="Editor" background="#444CE7"](tab-0) tab. Five files:

- `workflow.py` builds a `TemporalAgent` with the same prompt as module 2. Model calls run as Activities. Each data tool is wrapped with `activity_as_tool`.
- `activities.py` holds every call to the outside world: three data fetches and `publish_memo`.
- `worker.py` registers the Strands plugin, which tells the worker how to build the model.
- `start.py` starts a Workflow. `decide.py` sends the approval.

The Workflow never touches the network. Workflow code replays, so anything that talks to the world lives in an Activity.

## Close the Gaps

Three `TODO` blocks, each a durability gap: one in `activities.py`, two in `workflow.py`. Read the comment above each
one, then uncomment it. `ToolErrorReasons` in `workflow.py` is provided. It passes the real failure reason back to the model.

Run the tests in the [button label="Starter" background="#444CE7"](tab-2) tab:

```bash,run
just test 3
```

They need no API key and no running server. Before you start, ten of eleven fail. When you finish, all eleven pass.

```bash,nocopy
...........                                                              [100%]
11 passed
```

## Start the Worker

Click the [button label="Worker" background="#444CE7"](tab-1) terminal.

```bash,run
just worker
```

```bash,nocopy
Worker started on task queue finance-research-tq. Ctrl+C to stop.
```

It does not return a prompt. That blocked terminal is the worker polling for work. Leave it running.

## Run It

Click the [button label="Starter" background="#444CE7"](tab-2) terminal.

```bash,run
just start "Write a research memo on TWS."
```

```bash,nocopy
Started research-3f9a12bc
Find it in the Temporal UI tab: research-3f9a12bc
Approve: just approve research-3f9a12bc
```

Open the [button label="Temporal UI" background="#444CE7"](tab-4) tab and click your workflow. Open the
**History** tab. Every model call is an Activity of type `invoke_model`. Every tool call is an Activity
named `get_quote`, `get_filings` or `get_news`. You wrote no retry code and no state store for any of them.

Now open the [button label="Research Desk" background="#444CE7"](tab-3) tab. The memo is written and the status is
`awaiting_approval`. The Workflow is not running code. It is waiting on a Timer and a Signal.

Approve it from the Research Desk, or from the terminal:

```bash,run
just approve research-3f9a12bc
```

Replace the id with yours. The Workflow publishes the memo and completes. The file lands in
`modules/03-durable-strands-agent/exercise/published`, named after the Workflow ID.

## Break It: Cut the Model

Open the [button label="Network Control Panel" background="#444CE7"](tab-5) tab and cut the **LLM gateway**. Start another memo:

```bash,run
just start "Write a research memo on KAVERI."
```

In the [button label="Temporal UI" background="#444CE7"](tab-4) tab the Workflow stays **Running**. Open the
**Pending Activities** section: `invoke_model` shows **Retrying**, the attempt count climbing, and the
last failure from the proxy.

> Module 1 died here. What is different?

**Answer.** Temporal is retrying the Activity, not your code. The plugin runs each model call as an Activity, and
every Activity has a retry policy. The agent has no idea anything went wrong. It is still awaiting a call that has not returned.

Allow the gateway again. Retries back off, so the next attempt can take up to about 100 seconds. Then the same execution finishes.
Approve it.

Changed code? Restart `just worker`. A running worker keeps the old code.

## Break It: Flaky Data

Set **Market data API** to `rate limited (429)` and start a memo. The mock API answers 429 with a
`Retry-After` of 2 seconds. In **Pending Activities**, `get_quote` shows **Retrying** with the failure
`Rate limited`. The retries are spaced by the server's delay, not by a guess.

Switch to `unavailable (503)`. Same story, default backoff. Tool retries are capped at two minutes.
After that the agent is told the last failure and reports the data as missing.

Set it back to `ok`. Then start a memo for a ticker that does not exist:

```bash,run
just start "Write a research memo on ZZZZ."
```

The data API answers 404. This one fails once, with no retries, because you told Temporal it is permanent.
The Workflow does not fail. The agent reads the reason, says what is missing, and the memo waits for review.

## Break It: Kill the Worker

Start a memo and wait until the [button label="Research Desk" background="#444CE7"](tab-3) shows `awaiting_approval`.
Then, in the [button label="Starter" background="#444CE7"](tab-2) terminal:

```bash,run
pkill -9 -f worker.py
```

`-9` is SIGKILL: no cleanup, no goodbye. That is what a crash looks like. The
[button label="Worker" background="#444CE7"](tab-1) terminal drops back to a prompt.

Refresh the Workflow in the [button label="Temporal UI" background="#444CE7"](tab-4) tab. Still **Running**. Nobody is
polling, and the Workflow does not care.

Restart the worker in the [button label="Worker" background="#444CE7"](tab-1) terminal:

```bash,run
just worker
```

Approve the memo. It publishes. Open the **History** tab and count the `invoke_model` Activities.
One. The worker that ran it is dead, and the new worker replayed the history instead of paying for the call again.

> If you kill the worker in the middle of a model call instead, expect a pause of up to 90 seconds
> before the retry. That is the Start-To-Close Timeout on the model Activity. Temporal cannot know the worker died sooner.

## Break It: Nobody Answers

Compliance does not always come back. Start a memo with a 30 second approval window:

```bash,run
just start-short "Write a research memo on CLOUD."
```

Do not approve it. After 30 seconds the Timer fires. In the History tab you will see `TimerStarted`,
then `TimerFired`. The Workflow returns `escalated` and publishes nothing. In production the window is
four hours. The mechanism is the same.

Start one more and press **Reject**. Outcome `rejected`, nothing published.

## Key Takeaways

| | Plain Strands script | Strands inside a Workflow |
|---|---|---|
| Model call fails | Run ends | Activity retries, Workflow stays Running |
| Data API returns 429 | Tool fails | Retries after the server's `Retry-After` |
| Unknown ticker (404) | Same as any failure | One attempt, marked non-retryable |
| Worker dies | Everything lost | New worker replays history, completed calls are not repeated |
| Human takes four hours | Process held open or state lost | Timer and Signal, no process needed |
| Memo published twice | Duplicate send | Workflow ID as idempotency key |

Click **Check** when done.
