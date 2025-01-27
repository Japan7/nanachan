from nanachan.rpg_model.equipment import Storable


#############
# Inventory #
#############
class Inventory:
    def __init__(self) -> None:
        self.storageContainer: list[Storable] = []
        self.quantity: list[int] = []

    def addNewStorable(self, item: Storable, number: int = 1):
        self.storageContainer.append(item)
        self.quantity.append(number)

    def store(self, item: Storable, number: int = 1) -> int:
        item.onStore()
        if item.stackable:
            try:
                id = self.storageContainer.index(item)
                self.quantity[id] += number
            except ValueError:
                self.addNewStorable(item, number)
        else:
            self.addNewStorable(item, number)

    def takeFromInventory(self, item: Storable, number: int = 1) -> Storable:
        res = item

        id = self.storageContainer.index(item)
        numberStored = self.quantity[id]
        if item.stackable and numberStored > number:
            self.quantity -= number
        else:
            del self.storageContainer[id]
            del self.quantity[id]

        return res
