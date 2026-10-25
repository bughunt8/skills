class Payment:
    def charge(self, amount):
        return amount > 0


class Checkout:
    def submit(self, payment, amount):
        if amount <= 0:
            return False
        return payment.charge(amount)
