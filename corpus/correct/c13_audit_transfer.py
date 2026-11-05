"""Internal ledger transfer between accounts."""


class InsufficientFunds(Exception):
    pass


def balance_cents(ledger, account_id):
    return ledger["balances"].get(account_id, 0)


def post_entry(ledger, account_id, delta_cents, memo):
    ledger["entries"].append({
        "account_id": account_id,
        "delta_cents": delta_cents,
        "memo": memo,
    })
    ledger["balances"][account_id] = (
        balance_cents(ledger, account_id) + delta_cents)


def transfer(ledger, source_account_id, dest_account_id, amount_cents, memo):
    if amount_cents <= 0:
        raise ValueError("transfer amount must be positive")
    if source_account_id == dest_account_id:
        raise ValueError("source and destination must differ")

    available = balance_cents(ledger, source_account_id)
    if available < amount_cents:
        raise InsufficientFunds("source account lacks funds")

    post_entry(ledger, source_account_id, -amount_cents, memo)
    post_entry(ledger, dest_account_id, amount_cents, memo)
    return {
        "source_balance_cents": balance_cents(ledger, source_account_id),
        "dest_balance_cents": balance_cents(ledger, dest_account_id),
    }
