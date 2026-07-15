# Deep Dive: Communication, `main()`, and Threads

Companion to `REPLICATION_GUIDE.md`. This answers three questions in detail:
1. **How does each module talk to the others?** (every channel, its transport, direction, format)
2. **What exactly does `main()` do**, region by region, and why in that order?
3. **How are threads created, stopped, and coordinated** — and why the hot path has no locks?

Read `REPLICATION_GUIDE.md` §0–§5 first for the vocabulary.

---

## 1. Two worlds of communication

There are **two fundamentally different kinds** of communication in Chronos, and mixing them up is
the main source of confusion:

| Kind | Where | Mechanism | Cost |
|---|---|---|---|
| **In-process** | inside the C++ engine | direct **function calls** + shared **pointers** | ~nanoseconds |
| **Cross-process** | engine ↔ bridge ↔ dashboard | **message passing** (ZeroMQ, WebSocket, REST) | ~micro/milliseconds |

The whole design philosophy is: **inside the engine, everything is a function call** (fast, no
copying, no serialization); **between programs, everything is a message** (decoupled, language-
agnostic). The engine never knows JSON exists; the dashboard never sees a raw C++ struct.

### 1.1 In-process (inside the engine): calls + pointers, not messages

The C++ modules do **not** send each other messages. `main()` builds all the objects once and wires
them together by handing out pointers/references. After that, they call each other directly:

```
main loop ──(by value)──►  RiskEngine.validateOrder(order)         returns float
main loop ──(Order*)────►  ShardedMatchingEngine.processOrder(&order)
                              │  routes by symbol
                              ▼
                           LimitOrderBook.processOrder(order*, resource*)
                              │  matches
                              ├──► PriceLevel.front()/popFront()/fillFront()   (owns the FIFO queue)
                              └──► EventPublisher.publishTrade / publishOrderUpdate   ◄── the book
                                     holds an EventPublisher* and calls it directly
```

Key wiring facts (all established in `main()`):
- `ShardedMatchingEngine` is constructed with **two pointers**: the memory-pool
  `std::pmr::memory_resource*` and an `EventPublisher*`. It passes both down to every
  `LimitOrderBook` it creates.
- **The book publishes its own events.** When a match happens, `LimitOrderBook` calls
  `publisher_->publishTrade(...)` itself — the main loop doesn't do it. This is why `processOrder`
  needs no "return the events to caller and let caller publish" plumbing.
- `PriceLevel` stores `Order*` (pointers), and `order_lookup_` stores an iterator into that list, so
  a cancel jumps straight to the node. These are all pointers into the **same** order object — no
  copies.

**Ownership & lifetime — the subtle part you must get right.** Follow one order's memory:
1. `ZmqGateway.receiveOrder()` copies the 64 incoming bytes into an `Order` inside a
   `ReceivedMessage`, returned inside a `std::optional`. That lives **on the main loop's stack** for
   this iteration.
2. The loop passes `&order` (a pointer to that stack object) into `processOrder`.
3. If the order **fully matches**, the pointer is only used *during* the call — safe.
4. If the order **rests** (unfilled remainder), `addToBook` stores that pointer in the price-level
   list and `order_lookup_`. **But the stack `Order` is destroyed when the loop iterates again** →
   the stored pointer now dangles.

> ⚠️ **Take note (a real limitation in the reference engine, and a great C++ lesson):** the current
> code is correct for *immediately matched* orders but does **not** give resting orders stable
> storage. The proper fix when you rebuild: on rest, **copy the order into pool-allocated memory**
> (`memory_pool.allocate<Order>()`, placement-construct it) and store *that* pointer in the book, so
> its lifetime matches the book's — not the stack frame's. This is exactly why the `MemoryPool` was
> threaded through everything. If you skip this, cancels/late fills read freed memory.

### 1.2 Cross-process channel A — order ingress (into the engine)

- **Transport:** ZeroMQ **ROUTER** socket, engine `bind`s `tcp://*:5555`. Clients (bridge `main.py`,
  `feeder.py`) use **DEALER** sockets that `connect` to it.
- **Direction:** clients → engine (one-way from the app's view; the engine just consumes).
- **Why ROUTER/DEALER:** it lets *many* clients send to one server asynchronously, and the ROUTER
  automatically prefixes each message with the sender's **identity** frame so a server *could* reply
  to the right client. Chronos doesn't reply on this channel, but the frame is still there.
- **Frame format (multipart):** `[identity][maybe empty delimiter][payload]`. `receiveOrder()` reads
  the identity, skips an empty delimiter if present, and expects the payload to be exactly
  `sizeof(Order)` (64) bytes, which it `std::copy`s straight onto an `Order`.
- **Non-blocking:** it uses `ZMQ_DONTWAIT` and returns `std::optional` — empty means "nothing waiting
  right now," which lets the hot loop spin instead of blocking.

### 1.3 Cross-process channel B — event egress (out of the engine)

- **Transport:** ZeroMQ **PUB** socket, engine `bind`s `tcp://*:5556`. Subscribers use **SUB**.
- **Direction:** engine → everyone listening (fan-out).
- **Subscribers:** (1) the bridge's listener thread (relays to the web), (2) the `AuditLogger`
  thread (writes to disk).
- **Frame format:** two frames per event — a **topic string** (`"TRADE"` or `"ORDER"`) then the
  64-byte binary struct. SUB sockets filter by subscribing to a topic prefix.
- **Semantics you must understand:** PUB/SUB is **lossy and asynchronous**. If a subscriber connects
  *after* a message is published, it misses it (the "slow joiner" problem). That's acceptable for a
  UI feed, and it's why the audit logger is started early in `main()`.

### 1.4 Cross-process channel C — bridge ↔ dashboard

- **Orders in:** dashboard → `POST /order` (JSON, REST) → bridge scales to fixed-point, encodes 64
  bytes, sends on its DEALER socket to `:5555`.
- **Events out:** bridge listener thread decodes `:5556` events → broadcasts **JSON over a WebSocket**
  to every connected browser.
- The dashboard never touches ZeroMQ or binary; the engine never touches JSON or HTTP.

**One order's full round trip (the sequence you should be able to recite):**
```
Browser click
  → POST /order (JSON)                     [dashboard → bridge, REST]
  → scale ×100/×1000, encode 64 bytes
  → DEALER send                            [bridge → engine :5555, ZMQ]
  → gateway.receiveOrder() (non-blocking)  [engine, in-process from here]
  → risk.validateOrder()
  → engine.processOrder(&order)  → LOB matches → publisher.publishTrade()
  → PUB "TRADE" + 64 bytes                 [engine :5556 → bridge, ZMQ, fan-out]
  → bridge decodes, /100 /1000
  → WebSocket JSON broadcast               [bridge → dashboard]
  → Zustand store update → React re-render
```

---

## 2. `main()` dissected (`src/main.cpp`)

`main()` has exactly one job: **construct every component in dependency order, wire them with
pointers, then run the hot loop until a signal says stop.** Nothing else. Here is what each region
does and *why it must be in that order*.

**Region 1 — install signal handlers (first).**
```cpp
std::atomic<bool> running{true};
void signalHandler(int) { running = false; }
std::signal(SIGINT,  signalHandler);
std::signal(SIGTERM, signalHandler);
```
`running` is an **`std::atomic<bool>`** because the signal handler and the main loop both touch it;
atomic makes that read/write safe and visible across the interruption. This is set up *before*
anything else so Ctrl-C works even during startup.

**Region 2 — construct in dependency order (order matters).**
```cpp
auto pool     = std::make_unique<MemoryPool>(100*1024*1024);   // (a) nothing depends on nothing
ZmqGateway    gateway("tcp://*:5555");                          // (b) binds ingress
EventPublisher publisher("tcp://*:5556");                       // (c) binds egress — needed by (f)
AuditLogger   logger("tcp://127.0.0.1:5556", "trading_audit.log"); // (d) will SUBSCRIBE to (c)
RiskEngine    risk_engine("models/risk_model.onnx");            // (e) independent
ShardedMatchingEngine engine(pool->get_resource(), &publisher);// (f) needs (a) pool + (c) publisher
engine.addSymbol("AAPL"); engine.addSymbol("BTC"); engine.addSymbol("ETH");
```
Why this order:
- The **pool** must exist before the engine, because the engine stores the pool's resource pointer
  and its containers allocate from it immediately.
- The **publisher** must exist before the engine, because `engine` takes `&publisher` and the book
  will call it during matching. (Passing the address of a not-yet-constructed object = crash.)
- `addSymbol` up front because **orders for unregistered symbols are silently dropped** — the books
  must exist before any order arrives.

**Region 3 — start the background audit thread, then tune the main thread.**
```cpp
logger.start();                 // spawns the audit std::thread (see §3)
if (pinThreadToCore(1)) { ... } // lock THIS (matching) thread to CPU core 1
setMaxPriority();               // request real-time scheduling for THIS thread
```
The logger is started *after* the publisher binds so it can subscribe. Pinning + priority apply to
the **calling thread** (the one about to run the hot loop), isolating matching from OS scheduler
jitter.

**Region 4 — the hot loop (the entire point of the program).**
```cpp
while (running) {
    auto msg = gateway.receiveOrder();        // non-blocking; std::optional
    if (!msg) continue;                        // nothing waiting -> spin again
    Order& order = msg->order;
    float score = risk_engine.validateOrder(order);
    if (score > 0.8f) { order.status = OrderStatus::Rejected;
                        publisher.publishOrderUpdate(order); continue; }
    auto trades = engine.processOrder(&order, pool->get_resource());
}
```
Properties to preserve when you rewrite it:
- **Single-threaded.** All matching happens here, on one core, with no locks — so there is zero
  lock contention and fully deterministic ordering.
- **Busy-spin.** `continue` on empty keeps the CPU hot for lowest latency (a production system might
  add a tiny sleep to save power; HFT usually doesn't).
- **No allocation.** No `new`/`std::string`/containers created here — trades come from the pool.
- **The loop doesn't publish trades** — the book already did that inside `processOrder`. The loop
  only publishes the *rejection* case, because a rejected order never reaches the book.

**Region 5 — graceful shutdown.**
```cpp
logger.stop();   // signals the audit thread to finish and join()s it
```
When a signal flips `running` to false, the loop exits, `logger.stop()` joins the background thread,
and destructors fire in reverse construction order (RAII): sockets close, the ZMQ contexts
terminate, the pool frees its 100 MB. The whole thing is wrapped in a `try/catch` so a construction
failure prints an error instead of crashing silently.

---

## 3. Threading model

Chronos is deliberately **almost single-threaded**. Understanding which threads exist and how they
avoid stepping on each other is the key systems lesson.

### 3.1 Every thread in the engine process

| Thread | Created by | Job | Lifecycle control |
|---|---|---|---|
| **Main / matching thread** | the OS at startup | run the hot loop (receive→risk→match); pinned to core 1, real-time priority | `std::atomic<bool> running` |
| **Audit thread** | `logger.start()` → `std::thread` | SUBSCRIBE to `:5556`, append events to disk | `std::atomic<bool> running_` + `join()` in `stop()` |
| **ZeroMQ I/O thread(s)** | the ZMQ context (`zmq_ctx_new`) | actually move bytes on the sockets in the background | managed by ZMQ; ends at `zmq_ctx_term` |

That's it for the engine. Matching is single-threaded on purpose.

### 3.2 How the audit thread is managed (the pattern to copy)

```cpp
void start() {                       // called from main thread
    if (running_) return;
    running_ = true;
    logger_thread_ = std::thread(&AuditLogger::run, this);   // spawn
}
void run() {                         // runs ON the audit thread
    void* ctx = zmq_ctx_new();       // its OWN context + socket (see §3.4)
    void* sub = zmq_socket(ctx, ZMQ_SUB);
    zmq_connect(sub, endpoint);
    zmq_setsockopt(sub, ZMQ_SUBSCRIBE, "", 0);               // all topics
    int timeout = 100; zmq_setsockopt(sub, ZMQ_RCVTIMEO, &timeout, sizeof(timeout));
    while (running_) {               // poll loop
        // recv returns -1 after 100ms if nothing arrived -> re-check running_
        ...
    }
    zmq_close(sub); zmq_ctx_term(ctx);
}
void stop() {                        // called from main thread on shutdown
    running_ = false;
    if (logger_thread_.joinable()) logger_thread_.join();    // wait for run() to return
}
```
The two ideas to internalize:
- **`std::atomic<bool>` as a lifecycle flag.** The main thread sets it; the worker reads it. Atomic
  guarantees the worker actually *sees* the change (no torn/cached read).
- **Receive timeout instead of a blocking recv.** A plain blocking `recv` would never notice
  `running_` went false. `ZMQ_RCVTIMEO = 100ms` makes `recv` return periodically so the `while
  (running_)` check can exit. `stop()` then `join()`s to guarantee the thread has fully finished
  (and closed its file) before the object is destroyed.

### 3.3 How the threads communicate — messages, not shared memory

The matching thread and the audit thread share **no mutable data**. They communicate **only** by
ZeroMQ messages: matching thread → PUB `:5556` → audit thread's SUB. This is the reason there are
**no mutexes anywhere near the hot path**:
- No shared data ⇒ no locks ⇒ no lock contention ⇒ no priority inversion ⇒ deterministic latency.
- The only cross-thread shared variables are the two `std::atomic<bool>` flags, used purely for
  start/stop — never for data.

This is the **"share memory by communicating, don't communicate by sharing memory"** principle.

### 3.4 Thread-safety rules you must follow

- **A ZeroMQ *socket* is NOT thread-safe.** Never touch one socket from two threads. Chronos obeys
  this: the audit thread creates its **own** context and socket inside `run()`; the publisher socket
  is only ever used by the matching thread (via the book). If you need a socket in another thread,
  make a new one there.
- **A ZeroMQ *context* is thread-safe** and is what spawns the background I/O threads. You can share
  a context, but this code keeps them separate per thread for simplicity.
- **CPU pinning is per-thread.** `pinThreadToCore(1)` affects whichever thread calls it (the main
  loop). If you pinned the audit thread too, pick a *different* core so it doesn't steal cycles from
  matching.

### 3.5 The bridge's threading model (Python — different, worth knowing)

The Python bridge isn't single-threaded; it has its own arrangement:
- **The asyncio event loop** (uvicorn/FastAPI) handles HTTP `POST /order` and the WebSocket
  connections.
- **A daemon `threading.Thread`** runs the ZMQ SUB listener (a blocking `recv` loop). It can't
  `await`, so to push a decoded event onto the async WebSocket broadcast it uses
  `asyncio.run_coroutine_threadsafe(manager.broadcast(...), loop)` — the safe bridge from a plain
  thread into the event loop.
- **The feeder** runs as a **separate subprocess** (`subprocess.Popen`), not a thread, so a crash in
  the market-data feed can't take down the API.

Takeaway: two languages, two concurrency styles, but the same discipline — **long/blocking work
(ZMQ recv, disk, market data) is kept off the thread that must stay responsive** (the matching loop
in C++, the asyncio loop in Python).

---

## 4. Quick checklist of "who talks to whom"

- `main` → `gateway` : call `receiveOrder()` (pull orders)
- `main` → `risk_engine` : call `validateOrder()` (gate)
- `main` → `engine` : call `processOrder(&order)` (match)
- `engine` → `LimitOrderBook` : route by symbol
- `LimitOrderBook` ↔ `PriceLevel` : manage the FIFO queue
- `LimitOrderBook` → `EventPublisher` : publish trades/updates **itself**
- `gateway` ⇄ external : ZMQ ROUTER `:5555` (orders in)
- `EventPublisher` → external : ZMQ PUB `:5556` (events out)
- `AuditLogger` (own thread) ← ZMQ SUB `:5556` → disk file
- bridge `main.py` : DEALER→`:5555`, SUB←`:5556`, WebSocket/REST↔dashboard
- `feeder.py` (subprocess) : Finnhub WS → DEALER→`:5555`

If you can draw that diagram from memory and explain *why each edge is a call vs a message*, you
understand the system.
