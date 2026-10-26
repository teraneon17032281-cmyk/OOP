from menu_items import MenuItem

STATUSES = ["новый", "готовится", "готов", "доставлен"]


class Order:
    def __init__(self):
        self.__items = []
        self.__status = 0
        self.__paid = False

    @property
    def status(self):
        return STATUSES[self.__status]

    @property
    def is_paid(self):
        return self.__paid

    @property
    def items(self):
        return list(self.__items)

    def next_step(self):
        if self.__status == len(STATUSES) - 1:
            raise ValueError("Заказ уже доставлен, дальше нельзя")
        self.__status += 1

    def add_item(self, item):
        if not isinstance(item, MenuItem):
            raise TypeError("Можно добавлять только блюда меню")
        if self.__status != 0:
            raise ValueError("Нельзя добавить блюдо, заказ уже не новый")
        self.__items.append(item)

    def get_total_cost(self):
        total = 0
        for item in self.__items:
            total += item.calculate_price()
        return total

    def pay(self, payment_method):
        if payment_method.collect_payment(self.get_total_cost()):
            self.__paid = True
            print("Заказ оплачен")
            return True
        print("Заказ не оплачен")
        return False

    def show(self):
        print("Заказ, статус:", self.status)
        for i, item in enumerate(self.__items, 1):
            print(f"{i}. {item}")
        print(f"Итого: {self.get_total_cost():.2f} руб.")
