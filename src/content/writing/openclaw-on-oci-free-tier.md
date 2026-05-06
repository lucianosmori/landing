---
title: "OpenClaw on Oracle Cloud Free Tier: Lobster in the shell"
description: "An AI assistant on $0/month infrastructure: open-source middleware on a free cloud VM that, once you live with it, looks suspiciously like the core of the AI hype itself."
pubDate: 2026-05-06
tags: [openclaw, oci, free-tier, agentic, devops]
draft: false
heroImage: https://lucianomori.cloud/images/adolfo-lobster.jpg
heroImageAlt: AI-rendered cartoon lobster perched on Luciano's shoulder while he eats dinner; the lobster wears an OpenClaw badge.
heroImageWidth: 3072
heroImageHeight: 2688
heroImageType: image/jpeg
---

<figure class="hero-figure">
  <img src="/images/adolfo-lobster.jpg" alt="AI-rendered cartoon lobster perched on Luciano's shoulder while he eats dinner; the lobster wears an OpenClaw badge." />
  <figcaption>Adolfo, riding shotgun.</figcaption>
</figure>

<blockquote class="lead-quote">

**TL;DR.** OpenClaw is open-source. Oracle's `VM.Standard.A1.Flex` is free forever. Stitched together with Terraform, you get a personal multi-channel AI assistant that bills you exactly `$0.00` a day. The pitch ends there. The reality is that you have now adopted a small AI that needs to live on a leash, and the leash is more interesting than the model.

</blockquote>

The assistant is named Adolfo (Project Hail Mary's Rocky, with a faded Johnny Silverhand overlay). It answers DMs on Telegram and Discord, hangs out in four WhatsApp groups, and sends me a daily summary at 7 a.m. The lobster is a process. The shell is the VM. After living with it for a few months, the strange conclusion I keep landing on is that this pile of middleware and spaghetti `.md` files is, structurally, what the current wave of "AI" actually *is*. Models are the engine. The leash, the harness, and the config telling the engine when to shut up are the product.

## The shell that costs nothing but isn't free

<figure class="section-figure" aria-hidden="true">
  <svg viewBox="0 0 80 80" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" focusable="false">
    <circle cx="40" cy="8" r="2" fill="currentColor" stroke="none" />
    <line x1="40" y1="14" x2="40" y2="20" />
    <rect x="14" y="20" width="52" height="20" rx="3" />
    <circle cx="22" cy="30" r="1.5" fill="currentColor" stroke="none" />
    <line x1="28" y1="30" x2="58" y2="30" />
    <rect x="14" y="44" width="52" height="20" rx="3" />
    <circle cx="22" cy="54" r="1.5" fill="currentColor" stroke="none" />
    <line x1="28" y1="54" x2="58" y2="54" />
    <line x1="40" y1="64" x2="40" y2="72" />
    <line x1="20" y1="72" x2="60" y2="72" />
  </svg>
</figure>

Three constraints fall out of "Always Free" the moment you take it seriously. Tailscale-only ingress removes the public-internet attack surface, the cert dance, and the question of whether any given probe is hostile or curious. Single VM means there is nothing to scale out because there is no second box, which forces every feature to fit inside a fixed process budget. And Always-Free reaps any instance that goes idle for seven days, so the cron jobs that make the assistant useful (morning summary, daily work log, group icebreakers) double as the heartbeat that keeps the host alive.

```
shell
├── VM.Standard.A1.Flex   4 OCPU / 24 GB
├── Tailscale only        no public ports
├── Terraform IaC         single source of truth for the box
└── single VM             everything colocated
```

What you are paying instead of dollars is attention. The free tier is a contract: stay inside the box, keep the box warm, do not paint yourself into a corner that requires a bigger box to get out of. None of these are difficult on their own. Together they shape the architecture more than any technical choice would. The whole stack is provisioned in Terraform, so if the box ever does get reaped, a `terraform apply` brings it back and an idempotent deploy script puts the assistant back on top.

## The provider cascade

<figure class="section-figure" aria-hidden="true">
  <svg viewBox="0 0 80 80" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" focusable="false">
    <polyline points="10 14 26 14 26 28 42 28 42 42 58 42 58 56 74 56" />
    <polyline points="70 52 74 56 70 60" />
    <circle cx="18" cy="14" r="2" fill="currentColor" stroke="none" />
    <circle cx="34" cy="28" r="2" fill="currentColor" stroke="none" />
    <circle cx="50" cy="42" r="2" fill="currentColor" stroke="none" />
    <circle cx="66" cy="56" r="2" fill="currentColor" stroke="none" />
  </svg>
</figure>

The hard part of running an assistant on free-tier infrastructure is not the infrastructure. It is the inference. Models are the actual recurring cost, and "free" inference comes with rate limits, randomly-dropped sessions, and the occasional `410` with no body and no log line.

| Tier | What it is | Used for |
|------|------------|----------|
| Reasoning | A frontier-model CLI behind subscription OAuth | DM thinking, hard cron tasks |
| Default chat | Free-tier hosted models (Kimi K2.5, GLM-5.1, Qwen3-Coder, Nemotron via NVIDIA NIM) | WhatsApp groups, fast turns |
| Cheap fast | Gemini 2.5 Flash and Pro | Cron icebreakers, summaries |
| Last resort | Cerebras Qwen-3-235B, Groq Llama-4-Scout | When everything else times out |

The reasoning tier deliberately does not run through an API key. Going through the CLI's subscription OAuth means inference counts against my flat-rate plan, which is what I am already paying for. The split also lets me reserve the heaviest model for DM conversations, where multi-turn context preservation matters most, and keep group replies on cheaper free-tier models that ship answers in under three seconds.

The mechanism that makes this stack actually work is the **fallback chain**. Each cron and each agent has an explicit, ordered list of LLM backends; the runtime walks it any time the current candidate errors, times out, or returns garbage. The four critical crons all carry the same eight-deep chain: one frontier-model CLI tier, four free-tier hosted models, two Google variants, and a specialty fast-inference provider as the last resort. Empirically Kimi K2.5 returns a `410` at least once a day, and the chain catches it inside a minute.

<blockquote class="pull-quote">

With the chain, the bot is more reliable than any single LLM behind it.

</blockquote>

If "free-tier infrastructure with paid inference" sounds slightly cheating, fair. The point is not that nothing has costs. The point is that costs are visible, capped, and live where the value is, in the model rather than the shell.

## The leash *is* the product

<figure class="section-figure" aria-hidden="true">
  <svg viewBox="0 0 80 80" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" focusable="false">
    <path d="M30 18 Q22 10 14 8" />
    <path d="M50 18 Q58 10 66 8" />
    <ellipse cx="18" cy="32" rx="8" ry="5" transform="rotate(-25 18 32)" />
    <line x1="13" y1="29" x2="22" y2="34" />
    <ellipse cx="62" cy="32" rx="8" ry="5" transform="rotate(25 62 32)" />
    <line x1="67" y1="29" x2="58" y2="34" />
    <ellipse cx="40" cy="42" rx="12" ry="9" />
    <circle cx="36" cy="40" r="1.5" fill="currentColor" stroke="none" />
    <circle cx="44" cy="40" r="1.5" fill="currentColor" stroke="none" />
    <line x1="30" y1="44" x2="50" y2="44" />
    <line x1="30" y1="48" x2="24" y2="56" />
    <line x1="50" y1="48" x2="56" y2="56" />
    <path d="M32 50 Q40 56 48 50" />
    <path d="M30 56 Q40 62 50 56" />
    <path d="M30 62 L26 72 L40 68 L54 72 L50 62" />
  </svg>
</figure>

The model itself is not doing anything special in this story. The reasoning model that drafts my morning email rollup is the same reasoning model anyone with a subscription can talk to in any browser. What makes Adolfo *Adolfo* is roughly twelve kilobytes of system prompt across `IDENTITY.md`, `TOOLS.md`, and per-group rules. It is the cron schedule. It is the eight-deep fallback chain. It is the exec policy that says the assistant can read but not write outside its workspace directory. It is hundreds of refusal-pattern test cases that taught the bot to decline an off-color request without sounding like an HR memo. Iterated by hand, in markdown, in a directory I version like code.

<blockquote class="pull-quote">

Models are the engine. The leash is the product.

</blockquote>

The clearest place to feel this is in group chats. Adding the bot to a friends' group is a multiplier on day one: it ice-breaks dead threads, follows up on running jokes, references inside-baseball from previous conversations because it actually has memory of them. Then a quieter day arrives where the room is doing fine without it, and the bot keeps replying anyway, and you realize you have built something that does not know when to be silent. The fix is not a smarter model. The fix is configuration: per-group reply rates, trigger words that hard-mute the bot for a fixed window, a soft-mute heuristic that goes quiet for the rest of the session if anyone tells it to shut up. Designing the off-switch took more iterations than designing the on-switch.

The hype around AI right now is largely model launches, but the value people experience is shaped by middleware that nobody has named yet. OpenClaw is one such middleware. Cursor, Aider, n8n, the various agent frameworks are too. The model is the steam engine. The locomotive, the rails, the timetable, and the conductor's whistle are the product you actually buy a ticket for, and we are not yet very good at any of those.

## What free-tier teaches that paid infrastructure doesn't

<figure class="section-figure" aria-hidden="true">
  <svg viewBox="0 0 80 80" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" focusable="false">
    <line x1="40" y1="16" x2="40" y2="58" />
    <circle cx="40" cy="14" r="2" fill="currentColor" stroke="none" />
    <line x1="18" y1="24" x2="62" y2="24" />
    <line x1="22" y1="24" x2="18" y2="32" />
    <line x1="22" y1="24" x2="26" y2="32" />
    <path d="M14 32 L30 32 L26 40 L18 40 Z" />
    <line x1="58" y1="24" x2="54" y2="32" />
    <line x1="58" y1="24" x2="62" y2="32" />
    <path d="M50 32 L66 32 L62 40 L54 40 Z" />
    <rect x="30" y="58" width="20" height="8" rx="1" />
  </svg>
</figure>

Constraints make every decision visible. Always-Free forces the colocation question early. Tailscale-only forces the access question early. Subscription-rate inference forces the fallback chain early. Each of these is a question you would answer eventually anyway. The difference is whether you answer it before deploying or after the bot has gone mute in the family chat for four hours and your mother has texted you twice.

The lobster is fine. The shell is fine. They both cost zero. The attention I pay instead is, in some sense, the fee. The side effect of paying it is that I now believe the future of "AI" is going to look much more like middleware than like model releases. The engine is impressive. You just cannot ride it without the harness.
