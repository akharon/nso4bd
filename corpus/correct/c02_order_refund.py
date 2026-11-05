"""Refund eligibility and issuance for a storefront."""


class RefundError(Exception):
    pass


def find_line_item(order, line_item_id):
    for item in order["line_items"]:
        if item["id"] == line_item_id:
            return item
    raise RefundError("line item not found on order")


def refundable_cents(item, already_refunded_cents):
    gross = item["unit_price_cents"] * item["quantity"]
    return max(0, gross - already_refunded_cents)


def issue_refund(gateway, order, line_item_id, requested_cents, actor_user_id):
    item = find_line_item(order, line_item_id)
    ceiling = refundable_cents(item, item.get("refunded_cents", 0))

    if requested_cents > ceiling:
        raise RefundError("refund exceeds remaining refundable amount")

    receipt = gateway.refund(
        charge_id=order["charge_id"],
        amount_cents=requested_cents,
        idempotency_key=order["idempotency_key"],
    )

    item["refunded_cents"] = item.get("refunded_cents", 0) + requested_cents
    order["audit"].append({
        "actor": actor_user_id,
        "order_id": order["id"],
        "line_item_id": line_item_id,
        "amount_cents": requested_cents,
        "receipt_id": receipt["id"],
    })
    return receipt
