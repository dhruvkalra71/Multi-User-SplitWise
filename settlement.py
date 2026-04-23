def minimize_cash_flow(net_balance):

    # Make a copy so original data is not modified
    balances = net_balance.copy()
    settlements = []

    # Continue until all balances are zero
    while True:
        # Find max creditor and debtor
        max_creditor = max(balances, key=balances.get)
        max_debtor = min(balances, key=balances.get)

        # If all settled
        if abs(balances[max_creditor]) < 1e-6 and abs(balances[max_debtor]) < 1e-6:
            break

        # Amount to settle
        amount = min(
            balances[max_creditor],
            -balances[max_debtor]
        )

        # Update balances
        balances[max_creditor] -= amount
        balances[max_debtor] += amount

        # Store transaction
        settlements.append({
            "from": max_debtor,
            "to": max_creditor,
            "amount": round(amount, 2)
        })

    return settlements
