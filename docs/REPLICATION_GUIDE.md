# Chronos HFT Engine — Build-It-Yourself Guide

A step-by-step manual to **recreate this project from scratch**, assuming you know how to
program a little but nothing about trading systems, high-frequency C++, or this codebase.
Read it top to bottom the first time. Each module section tells you **what**, **why**,
**the order**, **the concepts you must understand first**, **the gotchas**, and **how to test it**.

> **The documentation set** (read the guide first, then dive in as needed):
> - **`REPLICATION_GUIDE.md`** (this file) — the build order, module by module.
> - **`docs/deepdive-communication-and-threading.md`** — how modules communicate (call vs message),
>   `main()` region by region, and the threading model.
> - **`docs/cpp-engine-reference.md`** — C++ coding standards + a class-by-class reference of the
>   engine, plus algorithms, memory model, testing, gotchas, and a glossary.
> - **`docs/full-stack-reference.md`** — advanced C++ concepts, the test suites, and a class/function
>   reference for the **Python bridge**, the **`services/` backend**, and the **Next.js dashboard**,
>   with data-flow diagrams.

---

## 0. What you are building

Chronos is a tiny but realistic **electronic trading system** in three separate programs that
talk to each other:

```
 Market data (Finnhub)  ─►  feeder.py ─┐
                                        │ 64-byte binary orders over ZeroMQ (:5555)
 Web dashboard (Next.js) ─► main.py ────┤
        ▲                                ▼
        │  JSON over WebSocket     ┌───────────────────────────┐
        └──── main.py  ◄───────────│  chronos_engine  (C++)    │
              (PUB :5556, JSON)    │  matching + risk + gateway │
                                   └───────────────────────────┘
```

1. **The Engine** (`C++`, the hard and interesting part): receives orders as raw bytes,
   checks them for risk, **matches** buyers with sellers, and publishes the resulting trades.
2. **The Bridge** (`Python` / FastAPI): a translator. The engine speaks raw binary; the web
   speaks JSON. The bridge converts between them and also relays live market data.
3. **The Dashboard** (`Next.js` / React): the screen a trader looks at — order book, price
   chart, trade tape, order entry.

There is also a **second, optional layer** added later: a pure-Python re-implementation of the
whole trading backend under `services/` plus a much richer dashboard. That layer is great for
learning the *business logic* without C++, but the **original project is the C++ engine + bridge
+ dashboard**, and that is what this guide builds first. `services/` is covered last as a bonus.

> **Mental model:** the "matching engine" is the referee of a marketplace. Buyers shout prices
> they'll pay ("bids"), sellers shout prices they'll accept ("asks"). When a bid ≥ an ask, a
> **trade** happens. The engine's whole job is to do that matching correctly and *fast*.

---

## 1. Trading domain knowledge you need first

Learn these words — the code is meaningless without them.

- **Order**: an instruction to buy or sell. Has a **side** (Buy/Sell), a **symbol** (e.g. `AAPL`),
  a **price**, and a **quantity**.
- **Limit order**: "buy up to price X" / "sell down to price X". This engine deals in limit orders.
- **Bid / Ask**: the best price someone will **buy** at (bid) vs **sell** at (ask). The **spread**
  is ask − bid.
- **Order book (LOB = Limit Order Book)**: the list of all resting (unmatched) orders, grouped by
  price. Bids sorted high→low, asks sorted low→high. The top of each is the "best" price.
- **Matching / execution**: when an incoming order crosses the book (a buy priced ≥ best ask, or a
  sell priced ≤ best bid), it **fills** against resting orders and produces **trades**.
- **Price–time priority (FIFO)**: at the same price, the order that arrived **first** gets filled
  first. This is the fairness rule almost every exchange uses.
- **Partial fill**: an order can be filled in pieces (you wanted 100, only 40 were available now).
- **Fixed-point prices**: computers should never store money as floating-point (`0.1 + 0.2 != 0.3`).
  Instead we store **scaled integers**: price × 100 (cents), quantity × 1000. `$150.25` → `15025`.
- **Latency**: how long a decision takes, measured in **nanoseconds (ns)**. HFT lives or dies on
  this. Every `malloc`, cache miss, or lock is the enemy.

---

## 2. C++ knowledge you need first

If a concept below is new, pause and learn it — it appears everywhere in the engine.

- **Header-only code**: this engine puts *all logic in `.hpp` headers* (in `include/chronos/`).
  There's only one `.cpp` (`src/main.cpp`). You `#include` a header and its inline code is compiled
  into your program. Simpler to build, and lets the compiler inline aggressively for speed.
- **Pointers (`T*`) vs references (`T&`)**: a pointer is "the address of a thing" and can be null;
  a reference is an alias that must always point at something. The book stores `Order*` (pointers)
  so many structures can refer to the *same* order without copying it.
- **`nullptr`**: the modern "no object" pointer value. `getBestBid()` returns `nullptr` when the
  book is empty — callers must check.
- **`std::optional<T>`**: "maybe a T, maybe nothing." The gateway returns `std::optional<Order>`:
  present if an order arrived, empty if not (non-blocking receive).
- **Templates**: compile-time generics. `StrongType<T, Tag>` is a template that builds a new distinct
  type from any underlying type. `template <typename T> T* allocate()` allocates any type.
- **`enum class`**: a *type-safe* enum. `OrderSide::Buy` cannot be accidentally mixed with an int.
- **Structs & memory layout**: a `struct` is just fields laid out in memory. The order they're
  declared, plus **alignment/padding**, determines the exact byte layout — which matters enormously
  here (see §4.1 and §5).
- **`alignas(64)` and cache lines**: CPUs read memory in 64-byte chunks ("cache lines"). Aligning a
  hot struct to 64 bytes means one struct = one cache line = fewer memory stalls.
- **RAII (Resource Acquisition Is Initialization)**: acquire a resource in the constructor, release
  it in the destructor. Used for ZMQ sockets, the audit thread, and the latency timer — cleanup is
  automatic when the object goes out of scope.
- **`std::pmr` (polymorphic memory resources)**: standard-library containers that let you plug in a
  custom allocator. We use it to make containers allocate from a **pre-allocated pool** instead of
  calling `malloc` on the hot path. This is the single most important performance idea here.
- **`std::map` vs `std::unordered_map`**: `map` is a sorted tree (keeps keys in order — perfect for
  "best price first"); `unordered_map` is a hash table (O(1) lookup, no order — perfect for
  "find this order id fast"). The book uses both.
- **`std::list`**: a doubly linked list. Inserting/removing in the middle is O(1) **if you already
  hold an iterator to the node** — which is exactly how we cancel an order instantly.
- **Atomics & threads (`std::atomic`, `std::thread`)**: used only off the hot path (audit logger,
  shutdown flag). The matching loop itself is single-threaded on purpose (no locks = no contention).

---

## 3. Environment & build setup (do this first)

**Tools:** a C++20 compiler (GCC 13+ / Clang 16+ / MSVC), **CMake 3.20+**, **ZeroMQ**
(`libzmq3-dev`), Python 3.12 (for the bridge), Node 20 (for the dashboard). ONNX Runtime is
*optional* (the risk engine works without it).

**Project skeleton:**
```
include/chronos/*.hpp    # the whole engine (header-only)
src/main.cpp             # the one translation unit — wires everything together
tests/*.cpp              # GoogleTest suites, one per module
CMakeLists.txt           # build config
```

**CMake essentials** (`CMakeLists.txt`):
- Set `CMAKE_CXX_STANDARD 20`.
- Treat warnings as errors (`-Wall -Wextra -Wpedantic -Werror`) — this catches bugs early.
- `FetchContent` to pull GoogleTest.
- `pkg_check_modules(ZMQ REQUIRED libzmq)` to find ZeroMQ.
- Two targets: `chronos_engine` (from `src/main.cpp`) and `unit_tests` (from `tests/*.cpp`).
- **Rule you must remember:** every new engine header that has a test must be added to *both* the
  engine include path and the `tests/CMakeLists.txt` (source list + an `add_test` filter entry).

Build & test:
```bash
cmake -B build -S . -DCMAKE_BUILD_TYPE=Release && cmake --build build      # the engine
cmake -B build-debug -S . -DCMAKE_BUILD_TYPE=Debug && cmake --build build-debug
cd build-debug && ctest --output-on-failure                                 # the tests
```

---

## 4. Build the engine — module by module (in this order)

Work bottom-up: types → memory → one price level → the book → the router → risk → networking →
the main loop. Each layer only depends on the ones before it. Write the test for each module
**before moving on**.

### 4.1 `types.hpp` and `strong_type.hpp` — the vocabulary  *(do this first)*

**Purpose:** define the core data (`Order`, `Trade`) and *safe* numeric types.

**`strong_type.hpp` first.** Problem it solves: a price and a quantity are both `int64_t`, so the
compiler will happily let you pass one where the other is expected — a silent, dangerous bug.
`StrongType<T, Tag>` wraps an integer in a distinct type:
```cpp
template <typename T, typename Tag>
class StrongType {
    T value_{};
public:
    constexpr explicit StrongType(T v) : value_(std::move(v)) {}
    constexpr const T& value() const noexcept { return value_; }  // get the raw number
    auto operator<=>(const StrongType&) const = default;          // C++20: free <, >, == 
};
```
- `Tag` is a dummy type used *only* to make `Price` and `Quantity` different types. `using Price =
  StrongType<int64_t, struct PriceTag>;` — `struct PriceTag` is never defined, it's just a label.
- `explicit` stops accidental implicit conversion from a bare int.
- The **spaceship operator `<=>`** (C++20) auto-generates all comparisons.
- You call `.value()` to get the raw integer when you actually need arithmetic.
- There's a `std::hash` specialization so `OrderId` can be a key in `unordered_map`.

**`types.hpp`.** Defines `OrderSide`/`OrderStatus` enums and the two structs. The critical part is
the **exact 64-byte layout**:
```cpp
struct alignas(64) Order {
    OrderId id;                 // 8 bytes  @ offset 0
    std::array<char, 8> symbol; // 8 bytes  @ 8   (max 8-char ticker, NUL-padded)
    Price price;                // 8 bytes  @ 16
    Quantity quantity;          // 8 bytes  @ 24
    OrderSide side;             // 1 byte   @ 32
    OrderStatus status;         // 1 byte   @ 33
    uint64_t timestamp;         // 8 bytes  @ 40  (6 bytes padding sit at 34–39)
    std::byte padding[16];      //          @ 48–63  -> total 64
};
```
**Take note:**
- `alignas(64)` = one cache line. `sizeof(Order)` must be exactly 64.
- The explicit `padding` and the natural gap after `side`/`status` are **not decoration** — they
  make the byte layout predictable so Python can reconstruct it (see §5).
- **Test (`test_types.cpp`):** `static_assert`/`EXPECT_EQ(sizeof(Order), 64)` and
  `alignof(Order) == 64`. If this fails, nothing downstream will work.

### 4.2 `memory_pool.hpp` — zero-allocation memory

**Purpose:** hand out memory *without calling `malloc`* during trading.

**Why:** `malloc`/`new` can take microseconds and are unpredictable. In HFT that's unacceptable.
So at startup we grab one big block (100 MB) and carve pieces out of it.

**How it works:**
```cpp
std::vector<std::byte> buffer_;                          // one big pre-allocated block
std::pmr::monotonic_buffer_resource pool_resource_{      // hands out slices of buffer_
    buffer_.data(), buffer_.size(), std::pmr::null_memory_resource()};
```
- A **monotonic buffer resource** only ever moves a pointer forward as you allocate (super fast,
  no bookkeeping). It doesn't free individual objects — it's reset/destroyed all at once.
- The third argument, **`null_memory_resource()`**, is the "upstream" it falls back to when the
  buffer is exhausted. `null` means: *throw `std::bad_alloc` instead of silently calling `malloc`*.
  That's deliberate — you want to find out at test time that 100 MB wasn't enough, not discover a
  surprise `malloc` in production.
- `get_resource()` returns the `std::pmr::memory_resource*` you thread into every container.

**Concept to understand:** you pass this one resource pointer to every `std::pmr::` container in
the system, and they all draw from the same pool. **Test:** allocate a few objects, check the
pool's byte count moves; verify containers built on it work.

### 4.3 `price_level.hpp` — all orders at one price

**Purpose:** hold the queue of orders resting at a single price, in FIFO order.

**Data structure:** `std::pmr::list<Order*>` — a linked list of *pointers* to orders.
- Why a list? Because we need **O(1) insertion at the back** (new order) and **O(1) removal from
  anywhere** (a cancel) — a linked list gives both, *if* you keep the node's iterator.
- Why pointers (`Order*`) not `Order`? So the same order object can live here and also be found via
  the book's id-lookup map, without copying.

**Key functions:**
- `addOrder(Order*)` → pushes to the back, returns the **iterator** to the new node. The caller
  stores that iterator so it can later remove this exact order in O(1).
- `removeOrder(it)` → erases that node (used by cancel).
- `front()` → the oldest order (the one with time priority).
- `fillFront(qty)` → reduce the front order's quantity (a partial fill).
- `popFront()` → remove a fully-filled front order.
- `total_quantity_` is kept in sync so you can show book depth cheaply.

**Gotcha:** every mutation must update `total_quantity_`. If it drifts, depth numbers lie.
**Test:** add several orders, fill/pop the front, check order and totals.

### 4.4 `limit_order_book.hpp` — the matching brain  *(the core algorithm)*

**Purpose:** hold one symbol's whole book and run the matching algorithm.

**Data structures (understand these choices):**
```cpp
std::pmr::map<Price, PriceLevel, std::greater<Price>> bids_;   // high price first
std::pmr::map<Price, PriceLevel, std::less<Price>>    asks_;   // low price first
std::pmr::unordered_map<OrderId, OrderEntry>          order_lookup_;  // id -> where it lives
```
- `std::map` keeps prices **sorted**, so `bids_.begin()` is always the **best bid** and
  `asks_.begin()` is always the **best ask**. That's why matching can always look at `begin()`.
- The custom comparator (`std::greater` for bids) flips the sort so "best" is always first.
- `order_lookup_` maps an order id to `{price, list-iterator, side}` so **cancel is O(1)**: find
  the entry, jump straight to its price level and list node, remove it.

**The matching algorithm (`processOrder`)** — the heart of everything:
1. If it's a **Buy**, try to match against **asks** (cheapest sellers). If a **Sell**, match against
   **bids** (highest buyers).
2. `matchAgainstAsks`: while the incoming buy still has quantity **and** its price ≥ best ask price,
   trade against that price level. Stop the moment `order->price < best_ask` (can't afford it).
3. `matchLevel`: repeatedly take the **front** resting order (FIFO), compute
   `fill = min(incoming.qty, resting.qty)`, create a `Trade` at the **resting order's price**
   (the passive order sets the price), decrement both quantities. If the resting order is fully
   filled, `popFront()` and erase it from `order_lookup_`; else `fillFront()`.
4. If the incoming order still has quantity left after sweeping, it **rests**: `addToBook` inserts
   it into the right side and records it in `order_lookup_`.
5. The book **publishes events itself** (it holds an `EventPublisher*`): a `Trade` per fill, and an
   `Order` status update for both the resting counterpart and the incoming order.

**C++ notes:**
- `[[likely]]` / `[[unlikely]]` are C++20 hints telling the compiler which branch is common (buys
  are common, "price doesn't cross" is rare) so it optimizes the layout. Purely a speed hint.
- `try_emplace` on a `map` inserts a `PriceLevel` only if that price doesn't exist yet, avoiding a
  double lookup.

**Domain gotchas:**
- Trade price = the **resting (passive)** order's price, not the incoming (aggressive) one. This is
  standard exchange behavior and easy to get wrong.
- Erase a fully-filled resting order from **both** the price level **and** `order_lookup_`, or a
  later cancel will touch freed memory.
**Test (`test_matching.cpp`, `test_lob.cpp`):** full cross, partial fill, no-cross (rests),
FIFO within a level, and price priority across levels.

### 4.5 `sharded_matching_engine.hpp` — one book per symbol

**Purpose:** route an order to the correct symbol's book. AAPL and BTC have separate books.

**How:** `std::pmr::unordered_map<std::string, std::unique_ptr<LimitOrderBook>>`. `addSymbol("AAPL")`
creates a book; `processOrder` reads `order->symbol`, trims at the first `\0`, looks up the book,
and forwards.

**Take note (a real gotcha):** **symbols must be pre-registered** with `addSymbol`. An order for an
unknown symbol is **silently dropped** (returns empty trades). When you add a symbol you must add it
in *three* places later: here (`main.cpp`), the feeder's `SYMBOL_MAP`, and the dashboard.
`std::unique_ptr` gives automatic cleanup (RAII) of each book.

### 4.6 `risk_engine.hpp` — the pre-trade guard

**Purpose:** reject dangerous orders *before* they reach the book.

**Logic:** `validateOrder` returns a score 0.0–1.0; the main loop rejects if `> 0.8`.
- **Static checks** always run: quantity > 0 and ≤ max, price > 0, `price × quantity ≤ max notional`.
  Any violation → return `1.0` (reject).
- **AI path** is a placeholder: if built with ONNX Runtime (`HAS_ONNXRUNTIME`), it *would* run a
  model; today it returns a constant. Without ONNX it returns a small mock score.

**Concept:** `#ifdef HAS_ONNXRUNTIME` is **conditional compilation** — the ONNX code only exists in
the binary if the library was found at build time. This is how the project "degrades gracefully."
**Test (`test_risk.cpp`):** oversized qty/notional rejected; normal order passes.

### 4.7 `zmq_gateway.hpp` + `event_publisher.hpp` — the network edge

**Purpose:** get orders *in* and push events *out*, over **ZeroMQ** (a fast messaging library).

**Gateway (ingress):** binds a **ROUTER** socket on `:5555`.
- ROUTER/DEALER is a ZMQ pattern where the server can talk to many clients. Messages arrive
  **multipart**: `[client identity][maybe empty frame][payload]`.
- `receiveOrder()` is **non-blocking** (`ZMQ_DONTWAIT`) and returns `std::optional<ReceivedMessage>`
  — empty if nothing is waiting, so the hot loop can busy-spin.
- It reads the frames, and when the payload frame is exactly `sizeof(Order)` (64) bytes, it
  `std::copy`s the raw bytes straight onto an `Order` struct. **This raw `memcpy`-style read is why
  the byte layout must match exactly** (§5).

**Publisher (egress):** binds a **PUB** socket on `:5556`.
- `publishTrade`/`publishOrderUpdate` send **two frames**: a string **topic** (`"TRADE"` or
  `"ORDER"`) then the 64-byte struct. Subscribers filter by topic string.

**C++/systems notes:**
- These classes are **RAII wrappers**: constructor creates the ZMQ context+socket and `bind`s;
  destructor `zmq_close`/`zmq_ctx_term`. Copy is deleted (`= delete`) — you must not copy a socket.
- **PUB/SUB is lossy & async**: a subscriber that isn't connected yet misses messages. That's fine
  for a UI feed; it's why the audit logger connects early.

### 4.8 `audit_logger.hpp`, `thread_utils.hpp`, `latency_utils.hpp` — the support cast

- **`audit_logger.hpp`**: a background `std::thread` that SUBscribes to `:5556`, and appends every
  event to a file as length-prefixed binary frames. Uses `std::atomic<bool> running_` + a socket
  receive timeout (`ZMQ_RCVTIMEO`) so it can notice a shutdown request and stop. This is the
  "fire-and-forget persistence" pattern: slow disk I/O never blocks trading.
- **`thread_utils.hpp`**: `pinThreadToCore(1)` (Linux `pthread_setaffinity_np`) locks the matching
  thread to one CPU core so the OS scheduler can't bounce it around and blow the cache;
  `setMaxPriority()` requests real-time scheduling. Platform-specific (`#ifdef __linux__`).
- **`latency_utils.hpp`**: a tiny RAII timer — records `now()` in the constructor, prints the ns
  elapsed in the destructor. Wrap a scope in `{ LatencyLogger t("match"); ... }` to measure it.

### 4.9 `src/main.cpp` — wiring the hot loop  *(do this last)*

**Purpose:** construct every component and run the trading loop.

Sequence:
1. Create the `MemoryPool` (100 MB).
2. Create `ZmqGateway(:5555)`, `EventPublisher(:5556)`, `AuditLogger`, `RiskEngine`.
3. Create `ShardedMatchingEngine`, threading the pool resource + publisher in, and
   `addSymbol("AAPL"/"BTC"/"ETH")`.
4. Start the audit thread; `pinThreadToCore(1)`, `setMaxPriority()`.
5. **The hot loop** (this is the whole point):
   ```
   while (running):
       msg = gateway.receiveOrder()        // non-blocking; continue if empty
       score = risk.validateOrder(order)   // reject & publish "Rejected" if > 0.8
       trades = engine.processOrder(order) // match; the book publishes events itself
   ```
6. `std::signal(SIGINT/SIGTERM, ...)` flips an `std::atomic<bool> running` so Ctrl-C exits cleanly.

**Take note:** the loop is single-threaded and allocation-free by design. Don't add `new`,
`std::string`, or locks inside it.

---

## 5. The cross-language wire contract  *(the #1 source of bugs — read twice)*

The engine (C++) and the bridge (Python) must agree on the **exact bytes** of `Order`/`Trade`, and on
the **fixed-point scaling**. They don't share code — they share a *convention*, so it's easy to break.

- **Byte layout:** Python reconstructs the C++ struct with `struct` format strings:
  - `ORDER_FORMAT = "<Q8sqqBB6xQ16x"`  (u64 id, 8-char symbol, i64 price, i64 qty, u8 side, u8
    status, 6 pad, u64 timestamp, 16 pad = 64 bytes)
  - `TRADE_FORMAT = "<QQqqQ24x"` (u64 buy id, u64 sell id, i64 price, i64 qty, u64 ts, 24 pad = 64)
  - `<` = little-endian, explicit, so it's identical on every machine.
- **Scaling:** price × 100, quantity × 1000, everywhere. `$150.25` ↔ `15025`; `5.0` units ↔ `5000`.
- **Rule:** if you ever change a field or padding in `types.hpp`, you **must** change the format
  strings too, or Python's 64-byte length check fails and decoding silently stops. Symbols are max
  8 chars.

> In this repo the contract is also written down once in `contracts/WIRE_FORMAT.md` with a golden
> byte fixture, and there's a C++ test (`tests/test_wire_codec.cpp`) plus a Python test
> (`bridge/tests/test_wire.py`) that both assert the exact same bytes. Do the same — a "golden bytes"
> test is the cheapest insurance you'll ever write.

---

## 6. The Bridge (Python / FastAPI)

**Purpose:** translate binary↔JSON and serve the web app. Files in `bridge/`.

Build in this order:
1. **`schemas.py`** — Pydantic models (`Order`, `Trade`, `OrderRequest`) and the `OrderSide`/
   `OrderStatus` enums. Just data shapes + validation.
2. **`wire.py`** (the single source of truth) — the `struct` format strings, `encode_order`/
   `decode_order`/`decode_trade`, and the scaling helpers (`scale_price`, `scale_quantity`). Use
   `round()` not `int()` when scaling, or float error drops a cent (`int(0.29*100)==28`).
3. **`main.py`** (FastAPI): 
   - Opens a ZMQ **DEALER** socket to `:5555` (to send orders to the engine).
   - `POST /order`: takes JSON, scales to fixed-point, `encode_order`, sends the 64 bytes.
   - A **background thread** SUBscribes to `:5556`, decodes each event, and broadcasts JSON to all
     connected WebSocket clients (via an `asyncio` loop — note the thread→asyncio handoff).
   - Enables CORS so the dashboard (different port) can call it.
4. **`feeder.py`** — connects to Finnhub's WebSocket, maps external symbols to engine symbols
   (`SYMBOL_MAP`), turns each live trade into a synthesized buy+sell pair, and sends them to `:5555`
   to drive the engine. Needs `FINNHUB_API_KEY` in `bridge/.env`.

**Concept:** the engine is deliberately dumb about JSON/web. All that complexity lives in the bridge,
so the C++ hot path stays tiny.

---

## 7. The Dashboard (Next.js / React)

**Purpose:** the trader's screen. Files in `dashboard/src/`.

- **`store/useTradeStore.ts`** (Zustand) — global state: `bids`, `asks`, `trades`, selected symbol.
  It divides incoming scaled integers back to floats (`/100`, `/1000`) for display.
- **`app/page.tsx`** — opens a **WebSocket** to the bridge, and on each `TRADE`/`ORDER` message
  updates the store.
- **Components:** `OrderBook` (bid/ask depth bars), `TradeTape` (scrolling executions),
  `PriceChart` (candles via `lightweight-charts`), `OrderEntry` (POSTs to `/order`).

**Take note:** the dashboard is the *third* place the scaling convention lives — keep it in sync with
the engine and bridge. Start it with `npm install && npm run dev` on `:3000`.

---

## 8. Running the whole thing end-to-end

```bash
# 1. Engine
./build/bin/chronos_engine                       # binds :5555 (orders in), :5556 (events out)
# 2. Bridge (+ optional live feeder)
cp bridge/.env.example bridge/.env               # add FINNHUB_API_KEY
START_FEEDER=1 PYTHONPATH=. python bridge/main.py  # serves :8000
# 3. Dashboard
cd dashboard && npm install && npm run dev       # http://localhost:3000
```
Place an order in the UI → it POSTs to the bridge → the bridge sends 64 bytes to the engine → the
engine matches and PUBlishes → the bridge relays JSON → the UI updates. If you see that loop work,
you've rebuilt Chronos.

---

## 9. (Bonus) The pure-Python backend under `services/`

This is an *optional second implementation* that recreates the trading **business logic** in plain
Python (no C++, no ZMQ), so you can study concepts like a **double-entry ledger**, **buying-power
holds**, **order types** (market/stop, GTC/IOC/FOK), **options pricing/Greeks**, and **settlement**
without the systems-programming difficulty. It runs behind a small standard-library HTTP + SSE API
(`services/api`). Recommended path: build the C++ engine first (§4) to learn *how* matching works at
the metal, then read `services/core/matching.py` — it's the same algorithm in ~80 readable lines,
and the rest of `services/core/` shows what a real broker wraps around it. Every module there has a
`unittest` suite you can run with:
```bash
PYTHONPATH=. python3 -m unittest discover -t . -s services -p "test_*.py"
```

---

## 10. Recommended build order (checklist)

1. `strong_type.hpp` → `types.hpp` (+ size test)  ← the vocabulary
2. `memory_pool.hpp` (+ test)                       ← zero-alloc memory
3. `price_level.hpp` (+ test)                       ← FIFO queue at one price
4. `limit_order_book.hpp` (+ matching tests)        ← the core algorithm
5. `sharded_matching_engine.hpp` (+ test)           ← per-symbol routing
6. `risk_engine.hpp` (+ test)                        ← pre-trade checks
7. `event_publisher.hpp`, `zmq_gateway.hpp`          ← networking edge
8. `audit_logger.hpp`, `thread_utils.hpp`, `latency_utils.hpp`
9. `src/main.cpp`                                    ← the hot loop
10. Lock down the **wire contract** + golden test (§5)
11. Bridge: `schemas.py` → `wire.py` → `main.py` → `feeder.py`
12. Dashboard: store → page/WebSocket → components
13. (Bonus) `services/` pure-Python backend

**Three things beginners get wrong here, so watch for them:**
1. `sizeof(Order) != 64` (bad padding) → everything downstream breaks. Test it immediately.
2. Wire format / scaling drift between C++, Python, and the dashboard → silent decode failures.
3. Forgetting to remove a filled order from **both** the price level and `order_lookup_` → crashes
   on the next cancel.

Good luck — build it layer by layer, test each layer, and the whole thing will click together.
