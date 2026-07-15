# Chronos C++ Engine — Complete Reference

The exhaustive companion to `REPLICATION_GUIDE.md` and
`docs/deepdive-communication-and-threading.md`. This document explains:

- **Part 1** — the **C++ coding standards and conventions** the engine follows, with the *why*.
- **Part 2** — **every class and struct**, member by member: responsibility, data, methods,
  complexity, invariants, ownership, threading, failure modes, and worked examples.
- **Part 3** — the **algorithms and data structures** (matching, cancel, fixed-point, byte layout).
- **Part 4** — the **memory model** (PMR pools) and **concurrency model**.
- **Part 5–9** — error-handling philosophy, performance engineering, testing, a gotchas catalog,
  and a glossary.

Everything here describes `include/chronos/*.hpp` and `src/main.cpp`. The engine is **header-only**:
all logic lives in headers; `src/main.cpp` is the single translation unit.

---

# Part 1 — C++ coding standards & conventions

These are the rules the codebase follows. When you rebuild it, follow them too — they are what make
the engine fast, safe, and readable. Each rule states **what**, **why**, and shows an **example**.

## 1.1 Language level and build discipline

- **C++20, no compiler extensions.** `set(CMAKE_CXX_STANDARD 20)`, `CMAKE_CXX_EXTENSIONS OFF`. C++20
  gives us the spaceship operator, `[[likely]]`, concepts-adjacent features, and mature `std::pmr`.
- **Warnings are errors.** `-Wall -Wextra -Wpedantic -Werror` (`/W4 /WX` on MSVC). A warning is a
  latent bug; failing the build forces you to fix it now. This single setting catches unused
  variables, sign-comparison mistakes, narrowing conversions, and missing returns.
- **Static analysis in CI.** `cppcheck --enable=warning,performance,portability`. Runs before merge.

**Why it matters for HFT:** subtle undefined behavior (signed overflow, uninitialized reads) can
change timing or corrupt the order book. The strict build is your first line of defense.

## 1.2 File and module conventions

- **`#pragma once`** at the top of every header (simpler and just as portable in practice as include
  guards for this project).
- **Header-only.** Each component is a self-contained `.hpp` with inline definitions. Benefits:
  trivial build wiring, and the compiler can **inline** hot functions across "module" boundaries
  (there are no real boundaries — it's all one translation unit through `main.cpp`).
- **One class/concept per header**, named after it: `limit_order_book.hpp` → `class LimitOrderBook`.
- **Include order**: the component's own domain headers (`<chronos/...>`) first, then third-party
  (`<zmq.h>`), then standard library (`<vector>`, `<map>`). Keeps dependencies visible.
- **Everything lives in `namespace chronos { ... }`.** No `using namespace` in headers (it would
  leak into every includer). The only namespace opened at global scope is the required
  `std::hash` specialization for `StrongType`.

## 1.3 Naming conventions

| Kind | Style | Example |
|---|---|---|
| Types (class/struct/enum) | `PascalCase` | `LimitOrderBook`, `OrderSide` |
| Functions / methods | `camelCase` | `processOrder`, `getBestBid`, `pinThreadToCore` |
| Public data (struct fields) | `snake_case` | `order->buy_order_id`, `order->timestamp` |
| Private members | trailing underscore | `bids_`, `orders_`, `running_`, `total_quantity_` |
| Constants / enumerators | `PascalCase` in `enum class` | `OrderStatus::Filled` |
| Local variables | `snake_case` | `best_ask_it`, `match_qty` |
| Template type params | `PascalCase`/`T`, tag types | `template <typename T, typename Tag>` |

The **trailing-underscore for private members** is the most important one — at a glance you can tell
`bids_` (member state) from `bids` (a local). It also avoids shadowing between constructor
parameters and members.

## 1.4 `const`-correctness

- Methods that don't mutate are marked `const`: `getBestBid() const`, `price() const`,
  `numOrders() const`. This lets them be called on `const` objects and documents intent.
- Parameters that aren't modified are passed by `const&` (for objects) to avoid copies:
  `validateOrder(const Order& order)`, `publishTrade(const Trade& trade)`.
- Return `const T*`/`const T&` when handing out a read-only view: `const PriceLevel* getBestBid()`.

**Why:** `const` is free documentation the compiler enforces. A `const` method physically cannot
corrupt the book, so you can reason about it locally.

## 1.5 `noexcept`, `[[nodiscard]]`, `explicit`, and other attributes

- **`noexcept`** on functions that must never throw (accessors, comparisons). It enables optimizer
  assumptions and, for move operations, lets containers use moves instead of copies.
  Example: `[[nodiscard]] bool empty() const noexcept;`
- **`[[nodiscard]]`** on functions whose return value must not be ignored (`empty()`, `price()`,
  `numOrders()`). Ignoring them is almost always a bug, and the compiler now warns.
- **`explicit`** on single-argument constructors to prevent silent implicit conversions.
  `explicit StrongType(T v)` stops `Price p = 5;` from compiling (you must write `Price p{5};`).
  `explicit operator T()` stops a strong type from silently decaying to its raw integer.
- **`[[likely]]` / `[[unlikely]]`** branch hints on the hot path: buys are common
  (`if (side == Buy) [[likely]]`), "price doesn't cross" is rare (`[[unlikely]] break;`). Pure
  performance hints — they don't change behavior, only code layout.
- **`[[maybe_unused]]`** on parameters used only under some `#ifdef` (e.g. the ONNX model path when
  ONNX isn't compiled in) to silence `-Werror` unused-parameter warnings.

## 1.6 Construction and initialization

- **Member initializer lists**, not assignment in the body:
  `PriceLevel(Price price, ...) : price_(price), orders_(resource), total_quantity_(0) {}`.
  This constructs members once (assignment would default-construct then overwrite).
- **Default member initializers** for simple defaults: `T value_{};`, `void* socket_ = nullptr;`.
- **Brace initialization `{}`** to avoid the "most vexing parse" and narrowing:
  `std::atomic<bool> running{true};`.
- **`= default` / `= delete`** to express intent: `StrongType() = default;`,
  `ZmqGateway(const ZmqGateway&) = delete;` (you must not copy a socket wrapper).

## 1.7 RAII and the Rule of Zero/Five

- **RAII everywhere for resources.** A class acquires in its constructor and releases in its
  destructor: ZMQ context+socket (`ZmqGateway`, `EventPublisher`), the audit thread
  (`AuditLogger`), the latency timer (`LatencyLogger`), and the 100 MB block (`MemoryPool` via its
  `std::vector`).
- **Rule of Five** when you own a raw resource: if you write a destructor, you must consider the
  copy/move constructor and assignment. `ZmqGateway`/`EventPublisher` own a raw `void*` socket, so
  they **`= delete` copy** (copying a socket handle would double-close it). This is the deliberate
  Rule-of-Five decision: "non-copyable resource holder."
- **Rule of Zero** everywhere else: classes that only hold value-type or standard-container members
  (`LimitOrderBook`, `PriceLevel`, `MemoryPool`) write **no** destructor/copy/move — the compiler's
  defaults are correct because the members clean themselves up.

## 1.8 Pointers vs references vs values — the decision rules

- **`T&` (reference)** for "must exist, I won't take ownership, and I'll use it now":
  `validateOrder(const Order&)`.
- **`T*` (raw pointer, non-owning)** for "might be null / stored for later / one of many refers to
  it": the book stores `Order*`; the engine holds a `std::pmr::memory_resource*` and an
  `EventPublisher*`. **Raw pointers here never own** — nobody `delete`s them.
- **`std::unique_ptr<T>` (owning pointer)** for "I own this heap object": the sharded engine owns
  each book via `std::unique_ptr<LimitOrderBook>`. Destroyed automatically.
- **By value / `std::optional<T>`** for results: `receiveOrder()` returns `std::optional<...>`.
- **Rule:** exactly one owner per heap object (`unique_ptr`); everyone else uses a **non-owning**
  raw pointer or reference. Ownership is never ambiguous.

## 1.9 Error-handling philosophy (no exceptions on the hot path)

- **Startup / construction** may throw (e.g. `ZmqGateway` throws `std::runtime_error` if `bind`
  fails). `main()` wraps construction in `try/catch`. Throwing at startup is fine — it happens once.
- **The hot path never throws.** Matching, risk, and receive use **return codes and
  `std::optional`**: `receiveOrder()` returns empty instead of throwing; `cancelOrder()` returns
  `bool`; `validateOrder()` returns a `float` score. Exceptions unwind the stack unpredictably —
  unacceptable when you're counting nanoseconds.
- **`RiskEngine` fails closed at the edges but never crashes**: static-rule violations return `1.0`
  (reject) rather than throwing.

## 1.10 Type safety with strong types and `enum class`

- Money and quantities are **strong types** (`Price`, `Quantity`, `OrderId`), not bare `int64_t`, so
  the compiler rejects mixing them. See §2.1.
- All small constant sets are **`enum class`** (`OrderSide`, `OrderStatus`) with explicit underlying
  type (`: uint8_t`) so the byte layout is fixed and no implicit int conversion happens.

## 1.11 Performance conventions

- **Zero allocation on the hot path.** All hot containers are `std::pmr::` and draw from the
  `MemoryPool`. `std::pmr::vector<Trade> trades(trade_resource); trades.reserve(16);` pre-reserves
  so the common case never reallocates.
- **Cache-line alignment.** Hot structs are `alignas(64)`.
- **Prefer `std::map::begin()` over search.** Because the book is sorted, the best price is always
  `begin()` — O(1) amortized access to what matters most.
- **`try_emplace`** to avoid double lookups when inserting-or-getting a price level.

## 1.12 Testing conventions

- **GoogleTest**, one suite per module (`test_types.cpp`, `test_matching.cpp`, ...).
- Registered in `tests/CMakeLists.txt` **twice**: as a source file in the `unit_tests` target and as
  an `add_test(NAME ... COMMAND unit_tests --gtest_filter=Suite.*)` entry, so each suite is runnable
  in isolation via `ctest -R Suite`.
- Test **invariants and edge cases**, not just happy paths: struct sizes, empty book, partial fills,
  FIFO order, price priority, oversize risk rejects.

---

# Part 2 — Class-by-class reference

For each type: **Responsibility · Header · Data members · Interface · Complexity · Invariants ·
Ownership · Threading · Failure modes · Example.**

## 2.1 `StrongType<T, Tag>`  — `strong_type.hpp`

**Responsibility:** wrap a primitive (`int64_t`, `uint64_t`) into a *distinct*, type-safe value so
the compiler prevents mixing e.g. a price with a quantity.

**Template parameters:**
- `T` — the underlying primitive (the stored number).
- `Tag` — a *phantom* type used only to make two `StrongType`s different. `struct PriceTag` is
  declared but never defined; it exists purely as a label. `StrongType<int64_t, PriceTag>` and
  `StrongType<int64_t, QuantityTag>` are unrelated types even though both store `int64_t`.

**Data member:** `T value_{};` (zero-initialized by default).

**Interface:**
- `constexpr explicit StrongType(T val)` — build from a raw number; `explicit` blocks implicit
  conversion. `constexpr` allows compile-time construction.
- `constexpr StrongType() = default` — zero value.
- `constexpr T& value() noexcept` / `const T& value() const noexcept` — access the raw number for
  arithmetic. You must call `.value()` deliberately; the number never leaks implicitly.
- `constexpr explicit operator T() const noexcept` — explicit cast to the raw type when truly needed.
- `auto operator<=>(const StrongType&) const = default` — C++20 **three-way comparison**;
  auto-generates `<`, `<=`, `>`, `>=`, `==`, `!=`. This is why `bids_`/`asks_` can be keyed on `Price`.
- `operator+=`, `operator-=`, and friend `operator+`, `operator-` — arithmetic that stays within the
  strong type (adding two `Price`s yields a `Price`, never an int). Implemented by mutating `value_`.

**`std::hash` specialization** (in `namespace std`): hashes by the underlying value, so `OrderId`
can be a key in `std::unordered_map`. Required because `order_lookup_` is keyed on `OrderId`.

**Complexity:** all operations are trivial/inlined; zero runtime overhead vs a bare integer.

**Invariant:** the wrapped value is the single source of truth; no other state.

**Example:**
```cpp
using Price = StrongType<int64_t, struct PriceTag>;
using Quantity = StrongType<int64_t, struct QuantityTag>;
Price p1{15025};                 // $150.25 in cents; explicit braces required
Price p2 = p1 + Price{100};      // -> Price{15125}; stays a Price
// Quantity q = p1;              // COMPILE ERROR: cannot convert Price to Quantity  ✅
int64_t raw = p1.value();        // 15025, obtained deliberately
```

**Why it exists:** in a bare-`int64_t` world, `matchLevel(price, qty)` called as
`matchLevel(qty, price)` compiles and silently trades wrong. Strong types make that a compile error.

## 2.2 `Order` (struct)  — `types.hpp`

**Responsibility:** the canonical representation of a single order, laid out for cache efficiency and
byte-for-byte cross-language compatibility.

**Declaration & layout** (`alignas(64)`, total 64 bytes):

| Offset | Field | Type | Bytes | Notes |
|---|---|---|---|---|
| 0 | `id` | `OrderId` (u64) | 8 | strong type |
| 8 | `symbol` | `std::array<char,8>` | 8 | ASCII ticker, NUL-padded, **max 8 chars** |
| 16 | `price` | `Price` (i64) | 8 | scaled ×100 |
| 24 | `quantity` | `Quantity` (i64) | 8 | scaled ×1000 |
| 32 | `side` | `OrderSide` (u8) | 1 | Buy=0, Sell=1 |
| 33 | `status` | `OrderStatus` (u8) | 1 | New/Partial/Filled/Canceled/Rejected |
| 34–39 | (padding) | — | 6 | natural alignment gap before the u64 |
| 40 | `timestamp` | `uint64_t` | 8 | nanoseconds |
| 48–63 | `padding[16]` | `std::byte[16]` | 16 | pad to 64 |

**Invariants:** `sizeof(Order) == 64`, `alignof(Order) == 64` (assert this in tests). Symbol strings
longer than 8 chars are illegal.

**Ownership/threading:** a plain aggregate; owned by whoever holds it. On the hot path an `Order`
lives on the main loop's stack (from the gateway) and is referenced by pointer while matching.

**Why the exact layout:** the gateway `memcpy`s raw bytes onto this struct, and Python decodes the
same bytes with a `struct` format string. Any field/padding change silently breaks decoding.

## 2.3 `Trade` (struct)  — `types.hpp`

**Responsibility:** a completed execution between a buyer and seller.

**Layout** (`alignas(64)`, 64 bytes): `buy_order_id`(u64@0), `sell_order_id`(u64@8), `price`(i64@16),
`quantity`(i64@24), `timestamp`(u64@32), `padding[24]`(@40). Python `TRADE_FORMAT = "<QQqqQ24x"`.

**Note:** the trade `price` is the **resting (passive) order's** price, set in `matchLevel`. The
`timestamp` field is present but the reference sets it to 0 in matching (a production build would
stamp `clock::now()` — a deliberate simplification).

## 2.4 `OrderSide` / `OrderStatus` (enums)  — `types.hpp`

`enum class OrderSide : uint8_t { Buy = 0, Sell = 1 };`
`enum class OrderStatus : uint8_t { New=0, Partial=1, Filled=2, Canceled=3, Rejected=4 };`

- `enum class` = scoped + no implicit int conversion (`OrderSide::Buy`, not `Buy`).
- `: uint8_t` fixes the storage to 1 byte, which the wire layout depends on.
- The numeric values are part of the **wire contract** — the dashboard maps `side===0` to Buy.

## 2.5 `MemoryPool`  — `memory_pool.hpp`

**Responsibility:** provide fast, pre-allocated memory so the hot path never calls `malloc`.

**Data members:**
- `std::vector<std::byte> buffer_` — one contiguous block (default 100 MB), allocated **once** at
  construction.
- `std::pmr::monotonic_buffer_resource pool_resource_` — a PMR resource that carves slices out of
  `buffer_` by simply advancing a pointer.

**Construction:**
```cpp
explicit MemoryPool(std::size_t initial_size_bytes = 100*1024*1024)
    : buffer_(initial_size_bytes),
      pool_resource_(buffer_.data(), buffer_.size(), std::pmr::null_memory_resource()) {}
```
- The 3rd argument is the **upstream** resource used when `buffer_` is exhausted. It is
  `null_memory_resource()`, which **throws `std::bad_alloc`** instead of silently falling back to
  the global `malloc`. This is intentional: you want a loud failure in testing that tells you the
  pool is undersized, not a hidden `malloc` in production.

**Interface:**
- `std::pmr::memory_resource* get_resource()` — the pointer you thread into every `std::pmr`
  container so they all draw from this pool.
- `template <typename T> T* allocate()` — raw typed allocation (`allocate(sizeof(T), alignof(T))`).
- `std::size_t size() const` — total buffer bytes.

**Complexity:** allocation is O(1) (pointer bump). There is **no per-object free**; a monotonic
resource reclaims everything only when reset/destroyed.

**Invariant:** total live allocations must fit in `initial_size_bytes` or it throws.

**Threading:** not thread-safe for concurrent allocation; only the single matching thread uses it.

**Gotcha:** because it never frees individual objects, don't use it for long-lived churn without a
reset strategy. For per-order-batch trade vectors it's ideal.

## 2.6 `PriceLevel`  — `price_level.hpp`

**Responsibility:** hold all orders resting at **one** price, in strict FIFO (time-priority) order,
with O(1) add and O(1) remove.

**Type alias:** `using OrderListIterator = std::pmr::list<Order*>::iterator;` — the handle the book
stores so it can remove a specific order in O(1).

**Data members:**
- `Price price_` — this level's price.
- `std::pmr::list<Order*> orders_` — doubly linked list of **non-owning** order pointers, front =
  oldest = highest time priority.
- `int64_t total_quantity_` — running sum of resting quantity, for cheap depth queries.

**Interface & complexity:**
- `addOrder(Order*) -> OrderListIterator` — `push_back` (FIFO), updates total; returns the node
  iterator. **O(1).**
- `removeOrder(OrderListIterator)` — `erase` that node; updates total. **O(1)** (no search — the
  caller supplies the iterator).
- `front()` / `front() const` -> `Order*` — oldest order or `nullptr`. **O(1).**
- `fillFront(int64_t qty)` — reduce the front order's quantity (partial fill) and total. **O(1).**
- `popFront()` — remove a fully-filled front order; updates total. **O(1).**
- `empty()`, `price()`, `totalQuantity()`, `numOrders()` — accessors, `[[nodiscard]]`, `noexcept`.

**Invariant:** `total_quantity_` == sum of `quantity` of all orders in `orders_`. **Every** mutation
maintains it; if it drifts, depth reporting lies.

**Ownership:** stores `Order*` it does **not** own — lifetime belongs to whoever created the order.

**Example (FIFO):**
```cpp
PriceLevel lvl(Price{15025}, pool.get_resource());
auto it_a = lvl.addOrder(&a);   // a arrives first
auto it_b = lvl.addOrder(&b);   // b second
lvl.front();                    // -> &a (oldest first)
lvl.removeOrder(it_b);          // cancel b in O(1) using its iterator
```

## 2.7 `LimitOrderBook`  — `limit_order_book.hpp`  *(the core)*

**Responsibility:** maintain one symbol's full book (bids + asks) and execute the matching algorithm;
publish resulting trades and order-status updates.

**Data members:**
- `std::pmr::map<Price, PriceLevel, std::greater<Price>> bids_` — price→level, **descending** (best
  bid = highest = `begin()`).
- `std::pmr::map<Price, PriceLevel, std::less<Price>> asks_` — **ascending** (best ask = lowest =
  `begin()`).
- `std::pmr::unordered_map<OrderId, OrderEntry> order_lookup_` — id → `{price, list_iterator, side}`,
  enabling **O(1) cancel**.
- `EventPublisher* publisher_` — non-owning; may be null (tests pass none).

**Private helper struct:** `struct OrderEntry { Price price; PriceLevel::OrderListIterator
list_iterator; OrderSide side; };` — everything needed to locate and remove a resting order fast.

**Interface:**
- `std::pmr::vector<Trade> processOrder(Order* order, std::pmr::memory_resource* trade_resource)` —
  match the incoming order, rest the remainder, publish events, return the trades produced.
- `bool cancelOrder(OrderId id)` — remove a resting order; `true` if found. **O(1)** average.
- `const PriceLevel* getBestBid() const` / `getBestAsk() const` — top of book or `nullptr`.
- `numBidLevels()`, `numAskLevels()`, `numOrders()` — sizes.

**The matching algorithm (annotated).** `processOrder`:
```cpp
std::pmr::vector<Trade> processOrder(Order* order, std::pmr::memory_resource* trade_resource) {
    std::pmr::vector<Trade> trades(trade_resource);
    trades.reserve(16);                              // avoid reallocation in the common case
    if (order->side == OrderSide::Buy) [[likely]]    // buys are common
        matchAgainstAsks(order, trades);
    else
        matchAgainstBids(order, trades);
    if (order->quantity.value() > 0) [[likely]] {    // leftover -> rest in the book
        order->status = (order->status == New) ? New : Partial;
        addToBook(order);
    } else {
        order->status = OrderStatus::Filled;
    }
    if (publisher_) {                                // the BOOK publishes, not the caller
        for (const auto& t : trades) publisher_->publishTrade(t);
        publisher_->publishOrderUpdate(*order);
    }
    return trades;
}
```
`matchAgainstAsks` (buy side):
```cpp
while (order->quantity.value() > 0 && !asks_.empty()) {
    auto best = asks_.begin();                       // lowest ask (sorted map)
    if (order->price < best->first) [[unlikely]] break;   // can't afford -> stop
    matchLevel(order, best->second, trades);
    if (best->second.empty()) [[likely]] asks_.erase(best);   // level drained -> remove
}
```
`matchLevel` (FIFO within a price):
```cpp
while (order->quantity.value() > 0 && !level.empty()) {
    Order* resting = level.front();                              // oldest first (time priority)
    int64_t fill = std::min(order->quantity.value(), resting->quantity.value());
    Trade t; t.price = level.price(); t.quantity = Quantity(fill); t.timestamp = 0;
    if (order->side == Buy) { t.buy_order_id = order->id;  t.sell_order_id = resting->id; }
    else                    { t.buy_order_id = resting->id; t.sell_order_id = order->id; }
    trades.push_back(t);
    order->quantity = Quantity(order->quantity.value() - fill);
    if (resting->quantity.value() == fill) {                     // resting fully filled
        resting->status = Filled; resting->quantity = Quantity(0);
        if (publisher_) publisher_->publishOrderUpdate(*resting);
        order_lookup_.erase(resting->id);                        // remove from BOTH structures
        level.popFront();
    } else {                                                     // resting partially filled
        resting->status = Partial; level.fillFront(fill);
        if (publisher_) publisher_->publishOrderUpdate(*resting);
    }
}
```
**Complexity:** matching touches only the crossing price levels; each fill is O(1) plus map erase
O(log L) where L = number of price levels. Cancel and best-price access are O(1)/O(1)-amortized.

**Invariants:** (1) `bids_.begin()` is always the best bid, `asks_.begin()` the best ask;
(2) every resting order appears in exactly one `PriceLevel` **and** in `order_lookup_`;
(3) empty price levels are erased immediately.

**Ownership/threading:** stores `Order*` and a non-owning `EventPublisher*`; single-threaded use.

**Failure modes / gotchas:** forgetting to erase a filled resting order from `order_lookup_` leaves a
stale iterator → a later `cancelOrder` dereferences freed memory. Storing a pointer to a stack order
that then rests → dangling (see the lifetime note in the deep-dive; fix by pool-allocating resting
orders).

## 2.8 `ShardedMatchingEngine`  — `sharded_matching_engine.hpp`

**Responsibility:** own one `LimitOrderBook` per symbol and route each order to the right book.

**Data members:**
- `std::pmr::memory_resource* resource_` — threaded into every book (non-owning).
- `EventPublisher* publisher_` — passed to every book (non-owning, may be null).
- `std::pmr::unordered_map<std::string, std::unique_ptr<LimitOrderBook>> shards_` — **owns** the
  books via `unique_ptr`.

**Interface:**
- `void addSymbol(const std::string& symbol)` — create a book for a symbol if absent
  (`std::make_unique<LimitOrderBook>(resource_, publisher_)`).
- `std::pmr::vector<Trade> processOrder(Order* order, std::pmr::memory_resource* trade_resource)` —
  read `order->symbol`, trim at the first `\0`, look up the shard, forward; **unknown symbol →
  return empty trades (silently dropped)**.
- `LimitOrderBook* getShard(const std::string&)`, `std::size_t numShards() const`.

**Complexity:** routing is one hash lookup, O(1) average. Adds a `[[likely]]` on the "symbol found"
branch.

**Gotcha (important):** **symbols must be pre-registered.** Silent drops make missing `addSymbol` a
confusing "orders vanish" bug. To add a symbol you must edit three places: `main.cpp`'s `addSymbol`
calls, the feeder's `SYMBOL_MAP`, and the dashboard.

## 2.9 `RiskConfig` / `RiskEngine`  — `risk_engine.hpp`

**`RiskConfig` (struct):** hard limits — `max_order_quantity = 10'000`,
`max_order_value = 1'000'000` (price × quantity ceiling).

**`RiskEngine` responsibility:** pre-trade validation returning a risk **score** in [0, 1]; the main
loop rejects if `> 0.8`.

**Interface:**
- `explicit RiskEngine(const std::string& model_path, RiskConfig config = RiskConfig{})` — the model
  path is `[[maybe_unused]]` when ONNX isn't compiled in.
- `float validateOrder(const Order& order)`:
  1. `checkStaticRules` (always): quantity in `(0, max]`, price > 0, `price*qty ≤ max_value`. Any
     violation → **`1.0`** (reject).
  2. If `HAS_ONNXRUNTIME`: build a feature tensor and (in a full build) run inference; the reference
     returns a constant placeholder. Without ONNX: return a small mock score.

**Conditional compilation:** the ONNX members and code exist only under `#ifdef HAS_ONNXRUNTIME`;
CMake defines it only if the library is found. This is how the engine "degrades gracefully."

**Design note:** static checks *fail closed* (reject) and never throw — safe on the hot path.

## 2.10 `ZmqGateway` (+ `ReceivedMessage`)  — `zmq_gateway.hpp`

**Responsibility:** ingress — receive binary orders from clients over a ZeroMQ ROUTER socket.

**Data members:** `void* context_`, `void* socket_` (raw ZMQ handles). **RAII:** the constructor
`zmq_ctx_new` + `zmq_socket(ZMQ_ROUTER)` + `zmq_bind`; the destructor `zmq_close` + `zmq_ctx_term`.
Copy is `= delete` (Rule of Five: non-copyable resource holder).

**Nested struct:** `struct ReceivedMessage { std::vector<uint8_t> identity; Order order; };` — the
sender's ROUTER identity plus the decoded order.

**Interface:** `std::optional<ReceivedMessage> receiveOrder()` — **non-blocking** (`ZMQ_DONTWAIT`):
1. Receive the identity frame; if none waiting, return `std::nullopt`.
2. Receive the next frame; if it's an empty DEALER/REQ delimiter, skip it and read the payload.
3. If the payload is exactly `sizeof(Order)` bytes, `std::copy` them onto a fresh `Order` and return
   it; otherwise `std::nullopt`.

**Threading:** used only by the matching thread. A ZMQ socket is **not** thread-safe — never share it.

**Failure modes:** wrong-sized payload → dropped (returns nullopt). Constructor throws
`std::runtime_error` if `bind` fails (caught in `main`).

## 2.11 `EventPublisher`  — `event_publisher.hpp`

**Responsibility:** egress — broadcast trades and order updates over a ZeroMQ PUB socket.

**Data members:** `void* context_`, `void* socket_` (ZMQ_PUB). RAII + non-copyable, same pattern as
the gateway.

**Interface:**
- `void publishTrade(const Trade&)` → `publishEvent("TRADE", &trade, sizeof(Trade))`.
- `void publishOrderUpdate(const Order&)` → `publishEvent("ORDER", &order, sizeof(Order))`.
- private `publishEvent(topic, data, size)` sends **two frames**: the topic string (`ZMQ_SNDMORE`)
  then the raw struct bytes.

**Semantics:** PUB/SUB is fan-out, asynchronous, and **lossy** (a subscriber that joins late misses
messages — the "slow joiner" problem). Fine for a UI/audit feed.

**Threading:** used only by the matching thread (via the book). Do not share the socket.

## 2.12 `AuditLogger`  — `audit_logger.hpp`

**Responsibility:** off-critical-path persistence — subscribe to all published events and append them
to a file, on a **background thread**, so slow disk I/O never blocks matching.

**Data members:** `std::string pub_endpoint_`, `std::string filename_`,
`std::thread logger_thread_`, `std::atomic<bool> running_`.

**Interface:**
- `start()` — set `running_ = true`, spawn `std::thread(&AuditLogger::run, this)`.
- `stop()` — set `running_ = false`, `join()` the thread (also called by the destructor → RAII).
- private `run()` (on the worker thread): creates its **own** ZMQ context + SUB socket
  (`ZMQ_SUBSCRIBE, "")` = all topics), sets `ZMQ_RCVTIMEO = 100ms` so the blocking recv returns
  periodically to re-check `running_`, and writes each event as **length-prefixed binary frames**
  (`size_t` topic length, topic bytes, `size_t` payload length, payload bytes) then `flush()`.

**Threading pattern (the one to memorize):** lifecycle via `std::atomic<bool>` + recv timeout +
`join()`. The worker owns its own socket/context — never shared with the main thread. Communication
with the engine is **only** via ZMQ messages (no shared memory, no locks).

## 2.13 `thread_utils.hpp` (free functions)

- `bool pinThreadToCore(int core_id)` — pin the **calling** thread to a CPU core. Linux:
  `pthread_setaffinity_np` with a `cpu_set_t`. macOS: thread affinity *tags* (a hint, not hard
  pinning). Other platforms: returns `false`. Guarded by `#ifdef __linux__ / __APPLE__`.
- `void setMaxPriority()` — Linux only: request `SCHED_FIFO` real-time scheduling at max priority for
  the calling thread. Reduces scheduler-induced jitter on the matching loop.

**Why:** pinning keeps the hot thread on one core so its L1/L2 cache stays warm and the OS can't
migrate it mid-match (which would flush caches and spike latency).

## 2.14 `LatencyLogger`  — `latency_utils.hpp`

**Responsibility:** an RAII stopwatch for ad-hoc measurement.

**Mechanics:** constructor records `high_resolution_clock::now()`; destructor computes the elapsed
nanoseconds and prints `[Latency] <name>: <ns> ns`. Wrap a scope:
```cpp
{ LatencyLogger t("processOrder"); engine.processOrder(&order, res); }  // prints on scope exit
```
**Note:** `std::cout` is *not* something you want in the real hot path (I/O is slow); this is a
debugging/benchmark aid.

## 2.15 `main()`  — `src/main.cpp`

Covered in depth in `docs/deepdive-communication-and-threading.md` §2. In one sentence: **construct
in dependency order (pool → publisher → engine), register symbols, start the audit thread, pin +
prioritize the matching thread, then run the non-blocking receive→risk→match loop until a signal
flips the `std::atomic<bool> running` flag, then join and tear down via RAII.**

---

# Part 3 — Algorithms & data structures

## 3.1 Why these three container choices

| Need | Container | Why |
|---|---|---|
| "best price first," iterate in price order | `std::map` (sorted tree) | keeps keys ordered; `begin()` is the best price; O(log n) insert/erase |
| "find this order id instantly" | `std::unordered_map` (hash) | O(1) average lookup; order doesn't matter |
| "queue at one price, remove any node fast" | `std::list` | O(1) push_back and O(1) erase-by-iterator |

Using the wrong one is a classic mistake: a hash map for the book would lose price ordering; a vector
for a price level would make mid-queue cancel O(n).

## 3.2 Price–time priority, worked example

Book for AAPL (asks ascending):
```
ASK  150.30 x 5   (order S3, arrived 3rd)
ASK  150.25 x 4   (order S1)         ← best ask
ASK  150.25 x 3   (order S2, after S1 at same price)
BID  150.20 x 10  (order B1)         ← best bid
```
Incoming: **Buy 9 @ 150.25**.
1. Best ask 150.25 ≤ 150.25 → cross. Enter `matchLevel(150.25)`.
2. Front is **S1** (time priority): fill `min(9,4)=4` → Trade(buy=incoming, sell=S1, px=150.25, qty=4).
   Incoming left = 5. S1 fully filled → pop, erase from `order_lookup_`.
3. Front now **S2**: fill `min(5,3)=3` → Trade(..., sell=S2, qty=3). Incoming left = 2. S2 filled →
   pop. Level 150.25 now empty → erase from `asks_`.
4. Next best ask is 150.30 > 150.25 (incoming price) → **stop** (can't afford).
5. Incoming has 2 left → **rests** as a new ask at 150.25 (status Partial), added to `order_lookup_`.

Two trades printed at **150.25** (the resting price), FIFO honored (S1 before S2), remainder rests.

## 3.3 O(1) cancel mechanics

`order_lookup_[id]` yields `{price, list_iterator, side}`. Cancel:
1. Pick `bids_` or `asks_` by `side`; find the `PriceLevel` at `price` (O(log L)).
2. `level.removeOrder(list_iterator)` — O(1), no scan, because we stored the exact node.
3. If the level is now empty, erase it from the map.
4. `order_lookup_.erase(id)`.

The trick: the `PriceLevel` handed back an **iterator** when the order was added, and we saved it.
That iterator stays valid across other list insertions/removals (a property of `std::list`), so it's
still a direct handle to the node later.

## 3.4 Fixed-point arithmetic

- Price stored as integer **cents** (×100); quantity as integer **milli-units** (×1000).
- Never use floating point for money: `0.1 + 0.2 == 0.30000000000000004`. Integers are exact.
- Convert at the edges: bridge does `round(price*100)` in (use `round`, not `int`, or `0.29*100`
  truncates to 28); dashboard divides by 100/1000 for display.
- Notional (order value) = `price_scaled * qty_scaled / 1000` → cents.

## 3.5 The 64-byte layout and padding math

Compilers insert **padding** so each field sits on its natural alignment (a `uint64_t` must start on
an 8-byte boundary). In `Order`, after `side`(@32) and `status`(@33) the next field `timestamp`
(u64) must start at offset 40, so the compiler leaves 6 bytes (34–39) empty. The explicit
`padding[16]` then rounds the struct to 64. `alignas(64)` also forces the struct's own start address
to a 64-byte boundary. The Python `struct` string encodes these gaps as `6x` and `16x`.

If you reorder fields, the padding changes and `sizeof` may stay 64 by luck but the **byte offsets**
shift — silently breaking the wire contract. Always assert size *and* decode a golden fixture.

---

# Part 4 — Memory model & concurrency

## 4.1 The PMR pool, mechanically

`std::pmr` decouples a container from *how it allocates*. A `std::pmr::vector<Trade>` holds a
`memory_resource*`; when it needs memory it calls `resource->allocate(bytes, align)`. By passing the
`MemoryPool`'s `monotonic_buffer_resource`, every container draws from the same 100 MB block. The
monotonic resource just bumps a pointer, so allocation is a few instructions with no lock and no
`malloc`. Because the upstream is `null_memory_resource`, exhaustion throws instead of silently
mallocing — a design choice to catch under-sizing.

**Consequence for you:** any container you want on the hot path must be a `std::pmr::` type and must
be constructed with the pool resource, e.g. `std::pmr::vector<Trade> trades(trade_resource);`.

## 4.2 The concurrency model, precisely

- **One matching thread**, pinned + real-time, running the loop. All book mutation happens here, so
  the book needs **no locks**.
- **One audit thread**, its own ZMQ context/socket, communicating with the engine **only via PUB/SUB
  messages** — no shared mutable state.
- **ZMQ's own I/O threads** move bytes in the background (created by the context).
- **The only cross-thread shared state** is `std::atomic<bool>` lifecycle flags. Atomics guarantee a
  write on one thread is *seen* by another without a mutex.
- **Rule:** "share memory by communicating." Threads exchange messages, not pointers. This is why
  there is no mutex, condition variable, or shared queue in the whole engine.

## 4.3 Thread-safety rules

- A ZMQ **socket** is single-threaded: one socket, one thread, forever. Each thread that needs a
  socket makes its own.
- A ZMQ **context** is thread-safe and spawns the I/O threads; it can be shared, but this code keeps
  one per thread for simplicity.
- CPU pinning is per-thread; if you pin more than one thread, use different cores.

---

# Part 5 — Error-handling philosophy (recap + rationale)

- **Construction can throw** (once, at startup) → wrapped in `try/catch` in `main`.
- **Hot path returns codes**, never throws: `std::optional` (receive), `bool` (cancel), `float`
  score (risk). Exceptions unwind unpredictably and defeat latency guarantees.
- **Fail closed** in risk: any doubt → reject (`1.0`), never crash.
- **Silent drops** are used where a bad input is expected and non-fatal (unknown symbol, wrong-sized
  frame). Trade-off: fast and robust, but you must log/monitor drops in production so they're visible.

---

# Part 6 — Performance engineering notes

- **Zero allocation on the hot path.** PMR pool + `reserve(16)` on the trades vector.
- **Cache-line alignment** (`alignas(64)`) so a hot struct is one cache line; false sharing avoided.
- **Branch hints** (`[[likely]]`/`[[unlikely]]`) steer code layout toward the common path.
- **Sorted map access** so best price is `begin()` — no scanning for the top of book.
- **Single-threaded, lock-free** hot loop — no contention, deterministic ordering.
- **Busy-spin receive** for lowest latency (trade-off: burns a core).
- **CPU pinning + real-time priority** to remove scheduler jitter.
- **Header-only + inlining** so cross-module calls (book→publisher) compile to direct/inlined calls.
- **Measure, don't guess:** wrap suspected hot scopes in `LatencyLogger`; the README baseline is
  ~286 ns per match.

---

# Part 7 — Testing standards

- **GoogleTest**, one suite per module; suites map 1:1 to headers.
- **Every new header with logic gets a suite**, added to `tests/CMakeLists.txt` in two places
  (source list + `add_test` filter). Run one suite via `ctest -R MatchingTest`.
- **Assert invariants, not just outputs:** `sizeof(Order)==64`; empty-book behavior; partial fills;
  FIFO ordering; price priority; risk rejects on oversize; O(1) cancel correctness.
- **Golden-bytes test** for the wire format — encode a known order, assert the exact 64 bytes, and
  keep the C++ and Python fixtures identical.
- **Debug build enables coverage** (`--coverage -O0`); CI runs `ctest` and `cppcheck`.

---

# Part 8 — Gotchas catalog (learn from these)

1. **`sizeof(Order) != 64`.** Reordering fields or changing types changes padding. Assert size *and*
   alignment; decode a golden fixture.
2. **Wire/scaling drift** across C++ ↔ Python ↔ dashboard. Keep the format string and the ×100/×1000
   convention in lockstep; test both sides against one fixture.
3. **Filled resting order not erased from `order_lookup_`.** Later cancel dereferences a stale
   iterator → crash. Erase from **both** the level and the lookup map.
4. **Resting order points at stack memory.** The gateway's `Order` lives on the loop stack; if it
   rests, copy it into pool-allocated storage first, or the pointer dangles next iteration.
5. **Unknown symbol silently dropped.** Register every symbol with `addSymbol` (and in the feeder +
   dashboard). Log drops in production.
6. **Sharing a ZMQ socket across threads.** Undefined behavior. One socket per thread.
7. **PUB/SUB slow joiner.** Subscribers that connect late miss messages; start the audit logger
   early, and don't rely on PUB/SUB for anything that must be durable without a separate store.
8. **`int()` truncation when scaling money.** Use `round()`; `int(0.29*100)` is `28`, not `29`.
9. **Throwing on the hot path.** Don't. Return `optional`/`bool`/codes.
10. **`std::cout` in hot code.** I/O is slow and locks; keep it to debug/benchmark scopes only.

---

# Part 9 — Glossary

- **Ask / Offer** — the price a seller will accept. Best ask = lowest.
- **Bid** — the price a buyer will pay. Best bid = highest.
- **Spread** — best ask − best bid.
- **LOB (Limit Order Book)** — all resting limit orders, grouped and sorted by price.
- **Aggressive / Passive order** — the incoming (marketable) order is aggressive; the resting one it
  hits is passive. Trades print at the **passive** price.
- **FIFO / price–time priority** — same price → earliest order fills first.
- **Fill / Partial fill** — an execution; partial if only some quantity trades.
- **Fixed-point** — money as scaled integers (×100 price, ×1000 qty), never floats.
- **Notional** — order value = price × quantity.
- **Latency** — decision time, in nanoseconds; the metric HFT optimizes.
- **RAII** — tie resource lifetime to object lifetime (acquire in ctor, release in dtor).
- **PMR** — polymorphic memory resources; std containers with pluggable allocators.
- **Monotonic buffer resource** — a bump allocator that never frees individual objects.
- **Cache line** — the 64-byte unit the CPU moves between memory and cache.
- **Strong type** — a distinct type wrapping a primitive to prevent mixing (Price vs Quantity).
- **ROUTER/DEALER, PUB/SUB** — ZeroMQ messaging patterns (async request routing; fan-out broadcast).
- **Slow joiner** — a PUB/SUB subscriber that connects after messages were sent and misses them.
- **Sharding** — splitting state by key (here, one order book per symbol) to scale.
- **`std::optional<T>`** — a value that may be absent; the "maybe" type.
- **`std::atomic<T>`** — a variable safe to read/write from multiple threads without a lock.
- **Spaceship operator (`<=>`)** — C++20 three-way comparison that generates all relational operators.
- **`[[nodiscard]] / [[likely]] / [[maybe_unused]]`** — C++ attributes: don't-ignore-return /
  branch-probability hint / suppress-unused warning.

---

*End of reference. Read alongside `REPLICATION_GUIDE.md` (the build order) and
`docs/deepdive-communication-and-threading.md` (communication, `main()`, threads).*
