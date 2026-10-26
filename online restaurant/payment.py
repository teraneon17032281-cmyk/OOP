from abc import ABC, abstractmethod
from datetime import date


class PaymentStrategy(ABC):
    @abstractmethod
    def collect_payment(self, amount):
        pass


class CardPayment(PaymentStrategy):
    def __init__(self, number, month, year):
        self._number = number
        self._month = month
        self._year = year

    def collect_payment(self, amount):
        today = date.today()
        if (self._year, self._month) < (today.year, today.month):
            print("Карта просрочена, оплата не прошла")
            return False
        print(f"С карты {self._number} списано {amount:.2f} руб.")
        return True


class CashPayment(PaymentStrategy):
    def collect_payment(self, amount):
        print(f"Оплатите {amount:.2f} руб. наличными")
        return True


class CryptoPayment(PaymentStrategy):
    WALLET = "TTuBcEjprcR9oE3Y9WpfPXfzYU3FmkATUJ"
    RATE = 81.37  # сколько рублей стоит 1 USDT

    def collect_payment(self, amount):
        usdt = amount / self.RATE
        print("Оплата криптовалютой (только USDT, сеть TRC20)")
        print(f"Сумма: {usdt:.2f} USDT")
        print(f"Адрес кошелька: {self.WALLET}")
        answer = input("Вы отправили перевод? (да/нет): ")
        if answer == "да":
            return True
        print("Перевод не подтверждён, оплата не прошла")
        return False
