from menu_items import Pizza, Drink, ComboSet
from order import Order
from payment import CardPayment, CashPayment, CryptoPayment

pizzas = {"1": ("Маргарита", 500), "2": ("Пепперони", 600), "3": ("Четыре сыра", 550)}
drinks = {"1": ("Кола", 100), "2": ("Лимонад", 150), "3": ("Чай", 80)}
sizes = {"1": "маленькая", "2": "средняя", "3": "большая"}


def make_pizza():
    print("Пицца: 1 - Маргарита (500), 2 - Пепперони (600), 3 - Четыре сыра (550)")
    p = input("Выбор: ")
    print("Размер: 1 - маленькая, 2 - средняя, 3 - большая (+30%)")
    s = input("Выбор: ")
    if p not in pizzas or s not in sizes:
        print("Неверный ввод")
        return None
    return Pizza(pizzas[p][0], pizzas[p][1], sizes[s])


def make_drink():
    print("Напиток: 1 - Кола (100), 2 - Лимонад (150), 3 - Чай (80)")
    d = input("Выбор: ")
    ice = input("Со льдом? (да/нет): ") == "да"
    if d not in drinks:
        print("Неверный ввод")
        return None
    return Drink(drinks[d][0], drinks[d][1], ice)


def make_combo():
    print("Комбо: пицца + напиток, скидка 15%")
    pizza = make_pizza()
    drink = make_drink()
    if pizza is None or drink is None:
        return None
    return ComboSet("Обед", [pizza, drink])


def add_dish(order):
    print("1 - пицца, 2 - напиток, 3 - комбо")
    choice = input("Выбор: ")
    if choice == "1":
        item = make_pizza()
    elif choice == "2":
        item = make_drink()
    elif choice == "3":
        item = make_combo()
    else:
        print("Неверный ввод")
        return
    if item is None:
        return
    try:
        order.add_item(item)
        print("Добавлено:", item)
    except ValueError as e:
        print("Ошибка:", e)


def pay_order(order):
    if order.is_paid:
        print("Заказ уже оплачен")
        return
    print(f"К оплате: {order.get_total_cost():.2f} руб.")
    choice = input("1 - карта, 2 - наличные, 3 - крипта: ")
    if choice == "1":
        number = input("Номер карты: ")
        try:
            month = int(input("Месяц окончания: "))
            year = int(input("Год окончания: "))
        except ValueError:
            print("Нужно ввести числа")
            return
        order.pay(CardPayment(number, month, year))
    elif choice == "2":
        order.pay(CashPayment())
    elif choice == "3":
        order.pay(CryptoPayment())
    else:
        print("Неверный ввод")


def main():
    order = Order()
    while True:
        print()
        print("Статус заказа:", order.status)
        print("1 - добавить блюдо")
        print("2 - показать заказ")
        print("3 - оплатить")
        print("4 - следующий статус")
        print("0 - выход")
        choice = input("Что делаем? ")

        if choice == "1":
            add_dish(order)
        elif choice == "2":
            order.show()
        elif choice == "3":
            pay_order(order)
        elif choice == "4":
            if not order.is_paid:
                print("Сначала оплатите заказ")
            else:
                try:
                    order.next_step()
                    print("Новый статус:", order.status)
                except ValueError as e:
                    print("Ошибка:", e)
        elif choice == "0":
            break
        else:
            print("Неверный ввод")


main()
