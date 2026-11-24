"""
Synthetic Purchase Order and Lifecycle Event Generator for Oryva Planning.
Generates procurement transactions and an append-only audit event history table.
Incorporates:
- Sourcing from qualified SKU-Supplier relationships
- Realistic lead times and transport delays (skewed tail)
- Explicit event histories (DRAFT -> CONFIRMED -> IN_TRANSIT -> DELIVERED / CANCELLED)
- Current PO status strictly derived from the latest event
"""

from typing import Tuple, List, Dict
from datetime import date, timedelta
import numpy as np
import pandas as pd

from oryva_planning.schema.enums import POStatus
from oryva_planning.schema.id_builders import build_po_id, build_po_event_id
from oryva_planning.schema.entities import PurchaseOrder, PurchaseOrderEvent
from oryva_planning.generators.base import validate_and_sort_dataframe


def generate_purchase_orders(
    num_orders: int,
    sku_df: pd.DataFrame,
    sku_supplier_df: pd.DataFrame,
    supplier_df: pd.DataFrame,
    lead_time_df: pd.DataFrame,
    rng: np.random.Generator,
    year: int = 2026,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate PurchaseOrder and PurchaseOrderEvent records.
    Every PO has a complete event chain in PurchaseOrderEvent that determines its current_status.
    """
    sku_cost_map = dict(zip(sku_df["sku_id"], sku_df["unit_cost"]))
    supplier_rel_map = dict(zip(supplier_df["supplier_id"], supplier_df["reliability_score"]))

    # Index lead times by (supplier_id, sku_id, destination_location_id)
    lt_map = {}
    for _, row in lead_time_df.iterrows():
        key = (row["supplier_id"], row["sku_id"], row["destination_location_id"])
        lt_map[key] = (row["planned_lead_time_days"], row["minimum_order_qty"], row["order_multiple_qty"])

    # Available sourcing routes
    available_routes = lead_time_df[["supplier_id", "sku_id", "destination_location_id"]].drop_duplicates().to_dict("records")
    n_routes = len(available_routes)

    po_rows = []
    event_rows = []
    event_seq = 1

    start_date = date(year, 1, 1)

    for i in range(num_orders):
        po_id = build_po_id(i + 1, year)

        # Pick a valid sourcing route
        route = available_routes[rng.choice(n_routes)]
        sup_id = route["supplier_id"]
        sku_id = route["sku_id"]
        loc_id = route["destination_location_id"]

        planned_lt_days, moq, lot_size = lt_map.get((sup_id, sku_id, loc_id), (14, 50.0, 10.0))

        # Order quantity: multiple of lot_size, >= MOQ
        multiples = int(rng.integers(1, 10))
        order_qty = float(np.round(moq + multiples * lot_size, 2))

        # Unit purchase cost with +/- 5% vendor pricing variance
        base_cost = sku_cost_map.get(sku_id, 25.0)
        unit_cost = float(np.round(base_cost * rng.uniform(0.95, 1.05), 2))

        # Order date: spread across planning horizon (day 1 to 350)
        order_day_offset = int(rng.integers(0, 350))
        order_dt = start_date + timedelta(days=order_day_offset)

        # Promised delivery date
        promised_dt = order_dt + timedelta(days=planned_lt_days)

        # Transport delays: 15% probability of delivery delay, skewed tail
        is_delayed = (rng.random() < 0.15)
        if is_delayed:
            # Skewed tail: exponential delay between 3 and 21 days
            delay_days = int(np.round(rng.exponential(scale=6.0) + 3))
            revised_dt = promised_dt + timedelta(days=delay_days)
        else:
            revised_dt = promised_dt

        # Lifecycle progression based on simulated date relative to promised delivery
        # Progression options:
        # 1. DELIVERED (55%)
        # 2. IN_TRANSIT (25%)
        # 3. CONFIRMED (15%)
        # 4. CANCELLED (5%)
        status_choice = rng.choice(
            [POStatus.DELIVERED.value, POStatus.IN_TRANSIT.value, POStatus.CONFIRMED.value, POStatus.CANCELLED.value],
            p=[0.55, 0.25, 0.15, 0.05]
        )

        actual_dt_str = None
        current_status = status_choice

        # Build chronological event chain
        # 1. Event: DRAFT -> CONFIRMED
        t0 = order_dt.isoformat() + "T08:00:00Z"
        eid1 = build_po_event_id(event_seq, year)
        event_seq += 1
        event_rows.append({
            "event_id": eid1,
            "po_id": po_id,
            "from_status": POStatus.DRAFT.value,
            "to_status": POStatus.CONFIRMED.value,
            "event_ts": t0,
            "event_reason": "Purchase order approved and confirmed by supplier",
            "actor": "BuyerSystem",
        })

        if status_choice == POStatus.CANCELLED.value:
            t_cancel = (order_dt + timedelta(days=1)).isoformat() + "T10:00:00Z"
            eid_c = build_po_event_id(event_seq, year)
            event_seq += 1
            event_rows.append({
                "event_id": eid_c,
                "po_id": po_id,
                "from_status": POStatus.CONFIRMED.value,
                "to_status": POStatus.CANCELLED.value,
                "event_ts": t_cancel,
                "event_reason": "Order cancelled due to demand revision or supplier notice",
                "actor": "ProcurementManager",
            })
        elif status_choice in (POStatus.IN_TRANSIT.value, POStatus.DELIVERED.value):
            # In-transit event
            ship_days = max(1, planned_lt_days - 5)
            t_ship = (order_dt + timedelta(days=ship_days)).isoformat() + "T12:00:00Z"
            eid_ship = build_po_event_id(event_seq, year)
            event_seq += 1
            event_rows.append({
                "event_id": eid_ship,
                "po_id": po_id,
                "from_status": POStatus.CONFIRMED.value,
                "to_status": POStatus.IN_TRANSIT.value,
                "event_ts": t_ship,
                "event_reason": "Shipment picked up by carrier, in transit to destination",
                "actor": "LogisticsCarrier",
            })

            if status_choice == POStatus.DELIVERED.value:
                # Delivered event
                actual_dt = revised_dt
                actual_dt_str = actual_dt.isoformat()
                t_deliv = actual_dt.isoformat() + "T16:00:00Z"
                eid_deliv = build_po_event_id(event_seq, year)
                event_seq += 1
                event_rows.append({
                    "event_id": eid_deliv,
                    "po_id": po_id,
                    "from_status": POStatus.IN_TRANSIT.value,
                    "to_status": POStatus.DELIVERED.value,
                    "event_ts": t_deliv,
                    "event_reason": "Goods received, inspected, and checked into warehouse inventory",
                    "actor": "WarehouseReceiving",
                })

        created_at_ts = order_dt.isoformat() + "T07:30:00Z"

        po_rows.append({
            "po_id": po_id,
            "supplier_id": sup_id,
            "sku_id": sku_id,
            "destination_location_id": loc_id,
            "order_qty": order_qty,
            "unit_cost": unit_cost,
            "currency": "USD",
            "order_date": order_dt.isoformat(),
            "promised_delivery_date": promised_dt.isoformat(),
            "revised_delivery_date": revised_dt.isoformat(),
            "actual_delivery_date": actual_dt_str,
            "current_status": current_status,
            "created_at": created_at_ts,
        })

    df_po = pd.DataFrame(po_rows)
    po_order = list(PurchaseOrder.model_fields.keys())
    df_po = validate_and_sort_dataframe(df_po, PurchaseOrder, "po_id", po_order)

    df_events = pd.DataFrame(event_rows)
    event_order = list(PurchaseOrderEvent.model_fields.keys())
    df_events = validate_and_sort_dataframe(df_events, PurchaseOrderEvent, "event_id", event_order)

    return df_po, df_events
