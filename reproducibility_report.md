# Oryva AI - Deterministic Reproducibility Report

**Evaluation Seed:** `20261022`  
**Scale:** `starter` (50 SKUs, 5 Locations)  
**Overall Status:** `PASSED (Bit-for-Bit Deterministic)`

## Table Checksum Comparison

| Table | Run 1 Rows | Run 2 Rows | Run 1 SHA-256 | Run 2 SHA-256 | Status |
|---|---|---|---|---|---|
| `forecastdemand` | 13,000 | 13,000 | `2c13741d0866...` | `2c13741d0866...` | ✅ PASS |
| `inventory` | 250 | 250 | `afbe78e7dcc0...` | `afbe78e7dcc0...` | ✅ PASS |
| `leadtime` | 481 | 481 | `6d7eca420807...` | `6d7eca420807...` | ✅ PASS |
| `location` | 5 | 5 | `1e8a1f455819...` | `1e8a1f455819...` | ✅ PASS |
| `mitigationoption` | 26,607 | 26,607 | `2b6abefff8c2...` | `2b6abefff8c2...` | ✅ PASS |
| `productionplan` | 2,808 | 2,808 | `9216774b1dac...` | `9216774b1dac...` | ✅ PASS |
| `projected_balance` | 13,000 | 13,000 | `9aeaa561d7a4...` | `9aeaa561d7a4...` | ✅ PASS |
| `purchaseorder` | 100 | 100 | `302f22887dcf...` | `302f22887dcf...` | ✅ PASS |
| `purchaseorderevent` | 244 | 244 | `f92f426e231c...` | `f92f426e231c...` | ✅ PASS |
| `shortage` | 9,460 | 9,460 | `f0b33b3788af...` | `f0b33b3788af...` | ✅ PASS |
| `shortageevidence` | 18,920 | 18,920 | `c59f084c81fc...` | `c59f084c81fc...` | ✅ PASS |
| `sku` | 50 | 50 | `3c06e1784364...` | `3c06e1784364...` | ✅ PASS |
| `sku_substitute` | 50 | 50 | `51bebd232f52...` | `51bebd232f52...` | ✅ PASS |
| `sku_supplier` | 122 | 122 | `e21d67b31a4d...` | `e21d67b31a4d...` | ✅ PASS |
| `supplier` | 10 | 10 | `6dc0fe2f4c5a...` | `6dc0fe2f4c5a...` | ✅ PASS |
| `suppliercapacity` | 6,344 | 6,344 | `7eba3c8d424c...` | `7eba3c8d424c...` | ✅ PASS |

## Methodological Proof of Determinism
1. **Isolated PRNG Streams:** Each generator draws numbers exclusively from its own `SeedSequence.spawn()` child stream.
2. **Strict Primary Key Ordering:** All tables are sorted deterministically by primary key prior to serialisation.
3. **Fixed Floating-Point Representation:** All numeric floats are formatted with fixed decimal precision (`%.4f`).
4. **Standard Line Terminators:** All files use standard Unix line-feed (`\n`) endings.
5. **Zero Host Clocks:** No system `datetime.now()` or unbounded Python `set` iteration is utilized.