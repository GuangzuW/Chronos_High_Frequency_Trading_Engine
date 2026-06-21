// Fixed-point scaling — the single TypeScript definition of the convention shared with
// the engine and bridge. Mirrors:
//   - contracts/WIRE_FORMAT.md / contracts proto Scaling enum
//   - libs/client-core/include/chronos/client/wire.hpp  (kPriceScale / kQuantityScale)
//   - bridge/wire.py                                     (PRICE_SCALE / QUANTITY_SCALE)
//
// Previously these magic numbers (×100 / ×1000) were duplicated inline across the store
// and the bridge — a known source of "scaling sync" bugs. Keep them defined ONLY here.

export const PRICE_SCALE = 100; // 2 decimal places
export const QUANTITY_SCALE = 1000; // 3 decimal places

/** Convert an engine fixed-point price to a display float. */
export const unscalePrice = (scaled: number): number => scaled / PRICE_SCALE;

/** Convert an engine fixed-point quantity to a display float. */
export const unscaleQuantity = (scaled: number): number => scaled / QUANTITY_SCALE;

/** Convert a display price to engine fixed-point. */
export const scalePrice = (price: number): number => Math.round(price * PRICE_SCALE);

/** Convert a display quantity to engine fixed-point. */
export const scaleQuantity = (qty: number): number => Math.round(qty * QUANTITY_SCALE);
