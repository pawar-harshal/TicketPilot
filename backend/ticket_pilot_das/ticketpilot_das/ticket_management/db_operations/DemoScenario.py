"""
Demo-only: keeps a demo Order's TIMING fresh relative to "now", instead of
trusting whatever absolute timestamps were written into the DB once at
seed time -- without touching its status, items or total, which are now
the database's own fixed truth (set once, by us, in the DB -- not
re-decided by code every time a "Get Help" card is clicked).

Why this exists: OrderLookupTool computes is_late/minutes_late as
`now - O_DeliveryEta`. For a seeded order, O_DeliveryEta is a fixed
timestamp from whenever the DB was set up -- so that number only grows
the longer this project sits hosted somewhere. A recruiter opening the
live link weeks later would see "5000+ minutes late" instead of a
believable few-minutes-late order, which reads as obviously fake data
rather than a working support flow.

PREVIOUS approach (removed): clicking a "Get Help" scenario card used to
create-or-refresh ITS OWN dedicated Order row per (customer, scenario),
and the ticket was raised against that. That meant a customer with
several demo scenarios under their belt had several different orders,
and the one the customer's home-page status panel shows (their single
most recent order) could easily be a DIFFERENT one than whatever
scenario card they'd just clicked -- the chat would describe one order's
status while the dashboard showed another's. Wrong and confusing.

CURRENT approach: each demo customer has exactly ONE Order, period --
the same one the home-page status panel shows AND the same one any
ticket for that customer is raised against (via submit_ticket's normal
"customer's own most recent order" default). "Get Help" scenario cards
now ONLY supply canned message text (see frontend scenarios.js) -- they
no longer affect which order is used or create new ones.

That one Order can optionally be tagged with O_ScenarioKey (set directly
in the DB, once, by us) to borrow one of the templates below purely for
its relative TIMING offsets -- ensure_order_fresh() recomputes
O_OutForDeliveryDate/O_DeliveryEta/O_DeliveredDate relative to right now
on every read, so "it's 10 minutes late" stays true no matter when the
demo is viewed. Status/items/total are never touched here -- they stay
exactly what's in the DB, since there's now a real dashboard showing
them and they must not drift out from under it.
"""
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from ticketpilot_das.ticket_management.entity.DbModels import Order
from ticketpilot_das.utils.CommonEnums import OrderStatus
from ticketpilot_das.utils.Logger import get_logger

log = get_logger("ticket_management.db_operations.DemoScenario")


# Timing-only templates, keyed by O_ScenarioKey (set directly on an Order
# row in the DB -- see the SQL shared alongside this change). Offsets are
# minutes from "now" at the moment ensure_order_fresh() runs. None means
# that timestamp stays NULL. `status` here is documentation of which
# OrderStatus this timing pattern is meant to go with -- it is NOT
# written back to the Order; the Order's own O_StatusId is always the
# database's truth.
SCENARIO_TEMPLATES = {
    "late-order": {
        "status": OrderStatus.OUT_FOR_DELIVERY.value,  # doc only, not applied
        "out_for_delivery_offset_min": -55,
        "delivery_eta_offset_min": -10,
        "delivered_offset_min": None,
    },
    "not-received": {
        "status": OrderStatus.DELIVERED.value,
        "out_for_delivery_offset_min": -70,
        "delivery_eta_offset_min": -40,
        "delivered_offset_min": -35,
    },
    "missing-item": {
        "status": OrderStatus.DELIVERED.value,
        "out_for_delivery_offset_min": -50,
        "delivery_eta_offset_min": -25,
        "delivered_offset_min": -20,
    },
    "order-cancelled": {
        "status": OrderStatus.CANCELLED.value,
        "out_for_delivery_offset_min": None,
        "delivery_eta_offset_min": -15,
        "delivered_offset_min": None,
    },
    "late-quality": {
        "status": OrderStatus.DELIVERED.value,
        "out_for_delivery_offset_min": -140,
        "delivery_eta_offset_min": -110,
        "delivered_offset_min": -15,
    },
    "track-order": {
        "status": OrderStatus.OUT_FOR_DELIVERY.value,
        "out_for_delivery_offset_min": -15,
        "delivery_eta_offset_min": 20,
        "delivered_offset_min": None,
    },
    "cancel-change": {
        "status": OrderStatus.PLACED.value,
        "out_for_delivery_offset_min": None,
        "delivery_eta_offset_min": 45,
        "delivered_offset_min": None,
    },
    "refund-timing": {
        "status": OrderStatus.DELIVERED.value,
        "out_for_delivery_offset_min": -200,
        "delivery_eta_offset_min": -170,
        "delivered_offset_min": -165,
    },
}


def _offset(now: datetime, minutes: Optional[int]) -> Optional[datetime]:
    return None if minutes is None else now + timedelta(minutes=minutes)


def ensure_order_fresh(db: Session, order: Order, commit: bool = True) -> None:
    """If `order` is tagged with a known O_ScenarioKey, recompute its
    three timestamp columns relative to right now using that template's
    fixed relative offsets. No-op (including for a real, non-demo order,
    which simply has O_ScenarioKey = NULL) when there's no tag or the tag
    doesn't match a known template. Never touches O_StatusId/O_Items/
    O_TotalAmount -- those are the database's own fixed truth."""
    if not order.O_ScenarioKey:
        return
    template = SCENARIO_TEMPLATES.get(order.O_ScenarioKey)
    if template is None:
        log.warning("Order %s has unrecognized O_ScenarioKey '%s' -- leaving its timing untouched.",
                    order.O_Id, order.O_ScenarioKey)
        return

    now = datetime.now()
    order.O_OutForDeliveryDate = _offset(now, template["out_for_delivery_offset_min"])
    order.O_DeliveryEta = _offset(now, template["delivery_eta_offset_min"])
    order.O_DeliveredDate = _offset(now, template["delivered_offset_min"])
    db.add(order)
    if commit:
        db.commit()
    else:
        db.flush()
