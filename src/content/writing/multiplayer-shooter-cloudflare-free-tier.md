---
title: "$0/month realtime infrastructure on Cloudflare Durable Objects"
description: "A browser multiplayer shooter where one small server keeps the score and calls every hit, running at $0/month on Cloudflare's free tier. The trick is a Durable Object: one named, long-lived instance per room that Cloudflare places at the edge and bills nothing while it sleeps. Fourth in a $0 series after OpenClaw, Holtwick, and the wrist meter."
pubDate: 2026-06-14
tags: [cloudflare, durable-objects, workers, websockets, netcode, finops, free-tier, threejs, playwright]
draft: false
heroImage: https://lucianomori.cloud/images/voxel-shooter/hero.jpg
heroImageAlt: First-person view of a blocky voxel arena shooter; a held weapon in the foreground, low-poly cover blocks across a sandy plaza, a scoreboard and health bar in the HUD, and a second player visible across the map.
heroImageWidth: 1200
heroImageHeight: 630
heroImageType: image/jpeg
---

<figure class="hero-figure">
  <img src="/images/voxel-shooter/hero.jpg" alt="First-person view of a blocky voxel arena shooter; a held weapon in the foreground, low-poly cover blocks across a sandy plaza, a scoreboard and health bar in the HUD, and a second player visible across the map." />
  <figcaption>A browser FPS where one small server, not your tab, keeps the score. That whole server costs zero dollars a month at this scale.</figcaption>
</figure>

<blockquote class="lead-quote">

**TL;DR.** [OpenClaw on Oracle Cloud](/writing/openclaw-on-oci-free-tier/) was the lesson "the leash is the product." The [town of $0 AI characters](/writing/holtwick-in-a-week/) was "the gate is the product." The [wrist meter](/writing/one-token-on-your-wrist/) was "the response headers are the product." This one is about a single Cloudflare primitive that quietly does a lot: the **Durable Object**. It let me build a browser multiplayer shooter where one little server keeps everyone honest, place that server at the edge, and pay exactly nothing while nobody is playing. You can shoot at yourself right now at [boxshoot.pages.dev](https://boxshoot.pages.dev/). The rest of this is what a Durable Object is, and what it sits on top of, and why that turned out to be the whole game.

</blockquote>

I wanted a browser FPS where the game keeps an honest score: where your tab cannot simply tell everyone else "I hit you for 100" from the dev console, because some neutral thing in the middle is the one actually keeping track. Normally that "neutral thing in the middle" is a server you rent, run, and pay for around the clock. I wanted the recurring bill to be zero. Cloudflare has one building block that makes both of those true at once: the **Durable Object**. Most of this post just explains what it is, and the Worker runtime it rides on, because once you get those two the game is almost a footnote.

If you would rather play than read: it is live at [boxshoot.pages.dev](https://boxshoot.pages.dev/). Open two tabs, join the same room code, and shoot at yourself.

## Cloudflare Durable Objects: the whole server in one named object

<figure class="section-figure" aria-hidden="true">
  <svg viewBox="0 0 80 80" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" focusable="false">
    <rect x="22" y="14" width="36" height="52" rx="3" />
    <path d="M40 26 l10 6 v10 l-10 6 -10 -6 v-10 z" />
    <line x1="40" y1="32" x2="40" y2="44" />
    <line x1="30" y1="38" x2="50" y2="38" />
  </svg>
</figure>

The one primitive this whole project rests on is the **Cloudflare Durable Object**. The shortest definition that is still true: it is a **stateful class with a name and exposed methods**, and there is exactly *one* live instance of it per name, anywhere in the world. You ask Cloudflare for the object called `room-7` and that name always resolves to the same single instance; ask again from another continent and you reach that same one. It keeps state between requests, in memory and in an optional SQLite database sitting right next to the code, and it wakes in about **five milliseconds** (the next section is why). In one object, it is the entire honest server for one game room.

If you live in AWS, the fastest way to place it is by what it replaces: **a Durable Object is an AWS Lambda and its own private S3 bucket fused into one named thing, and better than gluing those two together.** Lambda is compute with no memory of its own; S3 is storage with no compute; a Durable Object is a single addressable object that is *both*, with no network hop between the code and its data (they are literally the same instance) and nothing to keep consistent across machines (there is only ever one writer, so you never reach for a lock or a cross-node transaction).

You never hold the object directly. You get a **stub** (a local proxy) by name and call its **exposed methods** as if it were in the same process:

```js
const id   = env.GAME_ROOM.idFromName(room);   // a name -> the one instance
const stub = env.GAME_ROOM.get(id);            // a local proxy to it
await stub.fetch(request);                      // call a method; it runs over there
```

Cloudflare routes each call to that single real instance, runs your code *there*, and returns the result, even across an ocean. The methods are just functions on the class: this game passes its WebSocket through the object's `fetch` method, while the newer style lets you expose plain methods (`stub.shoot(...)`, `stub.join(...)`) and call them like RPC. You never write a lock, because only the object can touch its own state. The takeaway that travels past games: when a problem needs *one owner of the truth* (a game room, a chat room, a document, a rate limiter, a job that must not double-run), reach for the primitive that gives you a single named instance, not the one that gives you infinite anonymous copies.

## Cloudflare Workers: the V8 isolate it rides on

<figure class="section-figure" aria-hidden="true">
  <svg viewBox="0 0 80 80" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" focusable="false">
    <rect x="10" y="22" width="60" height="42" rx="3" />
    <path d="M14 22 v-7 h14 v7" />
    <path d="M30 22 v-7 h14 v7" />
    <line x1="10" y1="32" x2="70" y2="32" />
  </svg>
</figure>

A Durable Object wakes in five milliseconds because of what it is built on: a **Cloudflare Worker**. A Worker is code that runs at the edge per request, and the interesting part is *how*. It does not get a container or a micro-VM the way an **AWS Lambda** does. It runs inside a **V8 isolate**, the exact same sandbox primitive Chrome uses to keep one browser tab from reading another tab's memory. Thousands of these isolates share **one big host process** on each machine, so a single Worker costs a few megabytes instead of a whole VM, and there is no operating system to boot per request. The result is **roughly a 5 ms start and effectively no cold start**: the heavy runtime is already running, and your code is just a fresh JavaScript context dropped into it.

The reason the AWS pair lands around a hundred milliseconds is worth spelling out, because it is the same cost twice. A cold **Lambda** has to boot a fresh micro-VM (AWS uses Firecracker) *and* start a whole language runtime inside it before your handler runs, which is the tens-to-hundreds of milliseconds everyone calls a "cold start." Then **S3** is a *separate service*: every object read is a network round trip out of your function and back, another chunk of milliseconds each time. Stack them (a Lambda that wakes up and then calls S3) and you pay both. A **V8 isolate** pays neither: there is no VM and no runtime to start (the process is already up, so a cold isolate is roughly 5 ms), and a Durable Object's SQLite lives *in the same instance as the code*, so reading state is a local call, not a hop. Same job, the two slow parts designed out.

A plain Worker is **stateless** (each request can hit a different isolate on a different machine, nothing remembered), which is perfect for serving the static game but useless for a room that has to remember a score. That is exactly the gap a Durable Object fills: the same isolate speed, plus a name and a memory. Here is the whole stack against its AWS equivalents:

| Need | AWS | Cloudflare | Start-up |
|---|---|---|---|
| Stateless compute | Lambda (container / micro-VM) | **Worker** (V8 isolate) | ~100 ms+ vs **~5 ms** |
| One stateful owner | DynamoDB + Lambda + your own locks | **Durable Object** (one named instance) | n/a vs **~5 ms** |
| Storage by the compute | S3 (separate service, network hop) | DO's built-in SQLite (same instance) | hop vs none |

The only place a bare Worker bites you is the URL: a Worker is always `name.your-account-subdomain.workers.dev` (that account segment is unavoidable), while only Cloudflare **Pages** gives a clean `name.pages.dev`. I wanted `boxshoot.pages.dev`, so the game ships as a Pages project and the `/ws` requests get forwarded to the Durable Object behind the scenes. The small generalized lesson: on a managed platform the URL is a hard input, not a finishing touch, so pick it before it picks your architecture.

## The server is the referee, not your tab

<figure class="section-figure" aria-hidden="true">
  <svg viewBox="0 0 80 80" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" focusable="false">
    <circle cx="40" cy="40" r="22" />
    <circle cx="40" cy="40" r="4" fill="currentColor" stroke="none" />
    <line x1="40" y1="12" x2="40" y2="22" />
    <line x1="40" y1="58" x2="40" y2="68" />
    <line x1="12" y1="40" x2="22" y2="40" />
    <line x1="58" y1="40" x2="68" y2="40" />
    <polyline points="52,28 44,40 50,46" />
  </svg>
</figure>

With one owner of the truth, the anti-cheat design writes itself, and it is simpler than it sounds. The clients are not allowed to announce what happened. They only announce what they are *trying* to do, and the room decides the rest.

```
room <- client    move {pos,dir}     shoot {pos,dir,weapon}     respawn
room -> clients   welcome  join  leave  state  hit  kill  death  score
```

When you fire, your tab does not say "I killed Bob." It says "I shot from here, pointing there, with the pistol." The Durable Object does the math itself: it traces that shot against where it thinks every other player is, using its own damage numbers, decides if it connected, subtracts the health, works out whether Bob died, credits you the kill, and tells everyone what happened. Your tab still pops a hitmarker the instant you click, because that feels good, but the hitmarker is cosmetic; it changes nobody's health and counts nobody's kill. The room even gives you a couple of seconds of spawn protection so you cannot be camped, and it enforces that too, because a client asking "am I still protected?" is exactly the kind of question you do not let the client answer.

This is the same instinct behind [an agent that is only allowed to send intent, never outcomes](/writing/openclaw-on-oci-free-tier/): the thing on the outside proposes, the thing you control disposes. You can poke at it yourself from the console at [boxshoot.pages.dev](https://boxshoot.pages.dev/); the worst a tampered client can do is lie about where it is aiming, because the part that matters happens somewhere it cannot reach. The general rule, in or out of games: decide who is allowed to be right once, put that decision where you own the code, and treat everything a client tells you as a request, not a fact.

## The practical bits: cost, wiring, and proof

<figure class="section-figure" aria-hidden="true">
  <svg viewBox="0 0 80 80" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" focusable="false">
    <rect x="20" y="14" width="40" height="54" rx="3" />
    <rect x="31" y="10" width="18" height="9" rx="2" />
    <polyline points="27,33 31,37 39,29" />
    <line x1="44" y1="33" x2="55" y2="33" />
    <polyline points="27,49 31,53 39,45" />
    <line x1="44" y1="49" x2="55" y2="49" />
  </svg>
</figure>

Three realities make it real, briefly. The first is **cost**, and it shaped the code. Durable Objects are on the free plan (SQLite-backed, one line of migration), billed on compute *duration*, and a sleeping room costs nothing; but anything that keeps a room awake (a `setInterval`, a `setTimeout`, an `alarm()`) bills you for every second it runs. A textbook game server runs a fixed clock forever, which on this pricing is a meter that never stops. So there is no clock: clients push position about twelve times a second, a shot resolves the moment it arrives, and the instant a room empties it sleeps and bills nothing. The free ceiling is then a one-line estimate, `13,000 GB-s/day ÷ 0.125 GB (128 MB per room) ≈ 29 room-hours/day`, which is plenty precisely because idle rooms are free. The rule generalizes past games: on consumption pricing, do not run a clock you do not need.

The second is **wiring**, the price of that clean URL. Cloudflare will not let a Durable Object be defined inside a Pages project, so the app is two deployables: the Pages site (the static game plus a tiny function that forwards `/ws` to the right room), and a second Worker with no public URL of its own whose only job is to hold the `GameRoom` object. The browser opens a same-origin socket and never knows the split exists.

The third is **proof**. A typecheck says the code compiles, not that two players see each other or that the room rejects a faked kill, and those only appear once something connects. So two cheap tests, neither needing me to watch: a no-browser Node script opens two WebSocket clients into one room, has one shoot the other, and asserts the damage and death arrive *from the room* (`WS_BASE=wss://boxshoot.pages.dev/ws` points it at production); and a Playwright run drives two real tabs into one room, checks each sees `Players: 2`, and screenshots both views every iteration as a flip-book of the build. "It builds" and "it works" are different claims, and for anything stateful or visual the gap between them is exactly where the bugs hide.

## What's next on the $0 shelf

This is the odd entry on a shelf I have been calling "$0 AI projects," because there is no model behind the glass: the AI built it ([the same overnight Ralph loops that built Holtwick](/writing/holtwick-in-a-week/)), but the shipped thing is pure infrastructure. That is the point. The free-tier discipline that made [OpenClaw](/writing/openclaw-on-oci-free-tier/), [Holtwick](/writing/holtwick-in-a-week/), and the [wrist meter](/writing/one-token-on-your-wrist/) cost nothing was never about AI; it was about reading a platform's primitives and prices as the architecture, before writing code. Swap the shooter for a collaborative editor, an MCP server holding a session, or an agent that should only be awake while it works, and the Durable Object underneath barely changes: one named owner of the truth, built on an isolate that wakes in milliseconds, asleep and free until someone needs it.

You can play it at [boxshoot.pages.dev](https://boxshoot.pages.dev/). Open two tabs with the same room code and shoot at yourself; the tab that takes the damage is the one the room decided was hit.
