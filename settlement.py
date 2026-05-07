def minimize_cash_flow(participants: list[str], transactions: list[tuple[str, str, float]]) -> list[tuple[str, str, float]]:
    """
    participants : list of participant names
    transactions : list of (debtor, payee, amount)
    returns      : list of (payer, receiver, amount) for minimum cash flow
    """
    n = len(participants)
    index_of = {p: i for i, p in enumerate(participants)}

    graph = [[0] * n for _ in range(n)]
    for debtor, payee, amount in transactions:
        graph[index_of[debtor]][index_of[payee]] += amount

    net = [0] * n
    for i in range(n):
        for j in range(n):
            net[i] += graph[j][i]
            net[i] -= graph[i][j]

    def get_min_idx():
        return min(range(n), key=lambda i: net[i] if net[i] != 0 else float('inf'))

    def get_max_idx():
        return max(range(n), key=lambda i: net[i] if net[i] != 0 else float('-inf'))

    result = []
    zeros = sum(1 for x in net if x == 0)

    while zeros != n:
        min_i = get_min_idx()
        max_i = get_max_idx()

        amount = min(abs(net[min_i]), net[max_i])
        result.append((participants[min_i], participants[max_i], amount))

        net[min_i] += amount
        net[max_i] -= amount

        if net[min_i] == 0:
            zeros += 1
        if net[max_i] == 0:
            zeros += 1

    return result