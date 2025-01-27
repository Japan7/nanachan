from abc import abstractmethod

from nanachan.rpg_model.equipment import Equipable, Storable
from nanachan.rpg_model.exploration_kart import ExplorationKart


################
# Currency Abs #
################
class Currency(Storable):
    def __init__(self):
        super().__init__()
        self.stackable = True
        self.key = 1
        self.description = ''

    @abstractmethod
    def use(self, modifiable: Equipable):
        pass

    def onStore(self):
        return super().onStore()

    def onLoot(self):
        return super().onLoot()


#####################
# Transmutation Orb #
#####################
# upgrade common to magic
class TransmutationOrb(Currency):
    def __init__(self):
        super().__init__()
        self.name = 'Transmutation Orb'
        self.key = 2
        self.description = 'Upgrade a common equipment to a magic equipment'

    def use(self, modifiable: Equipable):
        if modifiable.rarity == 0:
            modifiable.upgradeRarity(1)


##################
# Alteration Orb #
##################
# reroll affixes of a magic item
class AlterationOrb(Currency):
    def __init__(self):
        super().__init__()
        self.name = 'Alteration Orb'
        self.key = 3
        self.description = 'Reroll the affixes of a magic equipment'

    def use(self, modifiable: Equipable):
        if modifiable.rarity == 1:
            modifiable.prefixes = {}
            modifiable.suffixes = {}
            modifiable.rollAffixes()


##################
# Alchemy Orb #
##################
# Upgrade a common item to a rare item
class AlchemyOrb(Currency):
    def __init__(self):
        super().__init__()
        self.name = 'Alchemy Orb'
        self.key = 4
        self.description = 'Upgrade a common equipment to a rare equipment'

    def use(self, modifiable: Equipable):
        if modifiable.rarity == 0:
            modifiable.upgradeRarity(2)


###############
# Blessed Orb #
###############
# Upgrade a magic item to a rare item
class BlessedOrb(Currency):
    def __init__(self):
        super().__init__()
        self.name = 'Blessed Orb'
        self.key = 5
        self.description = 'Upgrade a magic equipment to a rare equipment'

    def use(self, modifiable: Equipable):
        if modifiable.rarity == 1:
            modifiable.upgradeRarity(2)


##################
# Scouring Orb #
##################
# Return an item to rarity 0
class ScouringOrb(Currency):
    def __init__(self):
        super().__init__()
        self.name = 'Alteration Orb'
        self.key = 6
        self.description = 'Return an equipment to its common rarity'

    def use(self, modifiable: Equipable):
        if modifiable.rarity > 0:
            modifiable.rarity = 0
            modifiable.prefixes = {}
            modifiable.suffixes = {}


#############
# Chaos Orb #
#############
# reroll everything on an item
class ChaosOrb(Currency):
    def __init__(self):
        super().__init__()
        self.name = 'Chaos Orb'
        self.key = 7
        self.description = 'reroll everything on an item'

    def use(self, modifiable: Equipable):
        modifiable.roll()


#######################
# Kart reparation kit #
#######################
# Add a sit to an exploration kart
class KartReparationKit(Currency):
    def __init__(self):
        super().__init__()
        self.key = 8
        self.description = 'Add a sit to an exploration kart'

    def use(self, explorationKart: ExplorationKart):
        status = explorationKart.repare()
        if status == 0:
            raise Exception
