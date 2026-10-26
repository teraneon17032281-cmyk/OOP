from abc import ABC, abstractmethod


class MenuItem(ABC):
    def __init__(self, name, base_price):
        self._name = name
        self._base_price = base_price

    @property
    def name(self):
        return self._name

    @property
    def base_price(self):
        return self._base_price

    @abstractmethod
    def calculate_price(self):
        pass

    def __str__(self):
        return f"{self.name} - {self.calculate_price():.2f} руб."


class Pizza(MenuItem):
    def __init__(self, name, base_price, size):
        super().__init__(name, base_price)
        self._size = size

    def calculate_price(self):
        if self._size == "большая":
            return self.base_price * 1.3
        return self.base_price

    def __str__(self):
        return f"Пицца {self.name} ({self._size}) - {self.calculate_price():.2f} руб."


class Drink(MenuItem):
    def __init__(self, name, base_price, is_ice):
        super().__init__(name, base_price)
        self._is_ice = is_ice

    @property
    def name(self):
        if self._is_ice:
            return self._name + " со льдом"
        return self._name

    def calculate_price(self):
        return self.base_price

    def __str__(self):
        return f"Напиток {self.name} - {self.calculate_price():.2f} руб."


class ComboSet(MenuItem):
    def __init__(self, name, items):
        super().__init__(name, 0)
        self._items = items

    def calculate_price(self):
        total = 0
        for item in self._items:
            total += item.calculate_price()
        return total * 0.85

    def __str__(self):
        names = [item.name for item in self._items]
        return f"Комбо {self.name} ({', '.join(names)}) - {self.calculate_price():.2f} руб."
