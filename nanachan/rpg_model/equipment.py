from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Callable, Generic, Literal, TypeVar, override

import numpy as np

import nanachan.rpg_model.expedition_collection as collection
from nanachan.rpg_model.rpg_waicolle_utils import Stats, rollInArrayWithRate

if TYPE_CHECKING:
    from .expedition_collection import AffixesKey

# from nanachan.rpg_model.Weapon import Weapon

weaponMultiplier = [('S', 1.2), ('A', 1.0), ('B', 0.9), ('C', 0.8), ('D', 0.6), ('E', 0.5)]
WEAPON_ROLL_RATE = [0.01, 0.1, 0.25, 0.39, 0.15, 0.1]


def getWeaponMultiplierFromRankName(rank: str = ''):
    for d in weaponMultiplier:
        if d[0] == rank:
            return d
    return weaponMultiplier[len(weaponMultiplier) - 1]


def rollWeaponRank(rate: list[float] = WEAPON_ROLL_RATE):
    return weaponMultiplier[rollInArrayWithRate(np.random.normal(), rate)]


############
# Modifier #
############
T = TypeVar('T')


class Modifier(Generic[T]):
    def __init__(self, modif: Callable[[int], T]) -> None:
        self.modifiers: Callable[[int], T] = modif
        self.level: int = 1
        self._value: T = self.modifiers(self.level)

    def reroll(self):
        self._value = self.modifiers(self.level)

    @property
    def value(self) -> T | Literal[0]:
        return getattr(self, '_value', 0)


################
# Storable Abs #
################
class Storable(ABC):
    def __init__(self):
        super().__init__()
        self.key: int = 0
        self.stackable: bool = False
        self.name: str = ''

    @override
    def __eq__(self, o: object) -> bool:
        if not isinstance(o, Storable):
            return False

        return self.key == o.key

    @abstractmethod
    def onStore(self):
        pass

    @abstractmethod
    def onLoot(self):
        pass


#############
# Equipable #
#############
class Equipable(Storable, ABC):
    EQUIPMENT_RARITY: list[str] = ['COMMON', 'MAGIC', 'RARE', 'LEGENDARY']

    def __init__(self, base: Base, name: str = 'eq') -> None:
        super().__init__()
        self.rarity: int = 0
        self.prefixes: dict[AffixesKey, Modifier] = {}
        self.suffixes: dict[AffixesKey, Modifier] = {}
        self.base: Base = base
        self.name: str = name

    @override
    def onStore(self):
        return super().onStore()

    @override
    def onLoot(self):
        self.roll()

    @abstractmethod
    def onEquip(self):
        pass

    @abstractmethod
    def getItemPowerValue(self) -> float:
        pass

    def scrap(self):
        # Ecrire la fonction de scrap qui retourne un tableau de currency
        # en fonction du power level de l'équipement
        pass

    # return if it worked, 1 if yes, 0 if not
    def upgradeRarity(self, to: int) -> int:
        currentR = self.rarity
        upgradeR = to
        if upgradeR <= currentR:
            return 0

        self.rarity = upgradeR
        pn = len(self.prefixes)
        sn = len(self.suffixes)
        pnNew = self.prefixNumber
        snNew = self.suffixNumber

        s = np.random.default_rng()
        pToAdd = s.integers(0, pn - pnNew[1], endpoint=True)
        sToAdd = s.integers(0, sn - snNew[1], endpoint=True)
        for _ in range(pToAdd):
            tu = self.base.rollAffix(self.base.prefixes_pool)
            self.prefixes[tu[0]] = tu[1]

        for _ in range(sToAdd):
            tu = self.base.rollAffix(self.base.suffixes_pool)
            self.suffixes[tu[0]] = tu[1]

        return 1

    # return 1 if it worked 0 else
    def addPrefix(self, prefix: tuple) -> int:
        if len(self.prefixes) == self.prefixNumber[1]:
            return 0
        self.prefixes[prefix[0]] = prefix[1]
        return 1

    # return 1 if it worked 0 else
    def addSuffix(self, suffix: tuple) -> int:
        if len(self.suffixes) == self.suffixNumber[1]:
            return 0
        self.suffixes[suffix[0]] = suffix[1]
        return 1

    # Return the affixe value
    def getAffixValue(self, key: AffixesKey):
        if key in self.prefixes:
            return self.prefixes[key].value

        if key in self.suffixes:
            return self.suffixes[key].value

        return 0

    # roll the entire equipment based on its basis
    def roll(self):
        self.rollRarity()
        self.base.roll(self)

    # Roll the item rarity
    def rollRarity(self):
        self.rarity = rollInArrayWithRate(np.random.uniform(0, 1), [100, 50, 25, 10])

    # roll the affixes according to the item rarity
    def rollAffixes(self):
        self.base.rollPrefixes(self)
        self.base.rollSuffixes(self)

    # Return the range number of available prefix slots on the item according to its rarity
    @property
    def prefixNumber(self) -> tuple:
        if self.rarity == 0:
            return (0, 0)
        if self.rarity == 1:
            return (0, 1)
        if self.rarity == 2:
            return (1, 3)
        if self.rarity == 3:
            return (-1, -1)

        return (0, 0)

    # Return the range number of available suffix slots on the item according to its rarity
    @property
    def suffixNumber(self) -> tuple:
        if self.rarity == 0:
            return (0, 0)
        if self.rarity == 1:
            return (0, 1)
        if self.rarity == 2:
            return (1, 3)
        if self.rarity == 3:
            return (-1, -1)

        return (0, 0)


########
# Base #
########
class Base(ABC):
    def __init__(
        self, prefixesPool: dict[str, Modifier], suffixesPool: dict[str, Modifier]
    ) -> None:
        super().__init__()
        self.prefixes_pool = prefixesPool
        self.suffixes_pool = suffixesPool

    @abstractmethod
    def roll(self, equipment: Equipable):
        pass

    def rollAffix(affix: dict[str, Modifier]) -> tuple(str, Modifier):
        itemList = list(affix.items())
        randomElem = random.choice(itemList)
        return randomElem

    def rollPrefixes(self, equipable: Equipable):
        prefixNum = 0
        s = np.random.default_rng()
        if equipable.rarity > 0:
            prfxnmb = equipable.prefixNumber
            prefixNum = s.integers(prfxnmb[0], prfxnmb[1], endpoint=True)

        for _ in range(prefixNum):
            t = Base.rollAffix(self.prefixes_pool)
            equipable.prefixes[t[0]] = t[1]

    def rollSuffixes(self, equipable: Equipable):
        suffixNum = 0
        s = np.random.default_rng()
        if equipable.rarity > 0:
            sffxxnmb = equipable.suffixNumber
            suffixNum = s.integers(sffxxnmb[0], sffxxnmb[1], endpoint=True)

        for _ in range(suffixNum):
            t = Base.rollAffix(self.suffixes_pool)
            equipable.suffixes[t[0]] = t[1]


############
# Holdable #
############
class Holdable(Equipable):
    def __init__(self, base: Base = None, name: str = 'eq') -> None:
        super().__init__(base=base, name=name)
        self.main_hand: bool = True
        self.off_hand: bool = True


##########
# Weapon #
##########
class BaseWeapon(Base):
    def __init__(
        self, prefixesPool: dict[str, Modifier], suffixesPool: dict[str, Modifier]
    ) -> None:
        super().__init__(prefixesPool, suffixesPool)
        self.baseDamageRollMin: list[tuple(float, float)] = [(0, 0), (0, 0), (0, 0), (0, 0)]
        self.baseDamageRollMax: list[tuple(float, float)] = [(0, 0), (0, 0), (0, 0), (0, 0)]
        self.probabilityArrayForMultiplicator: list[list[float]]

    def roll(self, weapon: Weapon):
        self.rollBaseDamage(weapon)
        self.rollMultipliers(weapon)
        self.rollPrefixes(weapon)
        self.rollSuffixes(weapon)

    def rollBaseDamage(self, weapon: Weapon):
        for i in range(len(weapon.baseAttackValueRange)):
            weapon.baseAttackValueRange[i] = [
                np.random.uniform(self.baseDamageRollMin[i][0], self.baseDamageRollMin[i][1]),
                np.random.uniform(self.baseDamageRollMax[i][0], self.baseDamageRollMax[i][1]),
            ]

    def rollMultipliers(self, weapon: Weapon):
        indexMulSTR = rollInArrayWithRate(
            np.random.uniform(0, 1), self.probabilityArrayForMultiplicator[Stats.STR.value]
        )
        indexMulDEX = rollInArrayWithRate(
            np.random.uniform(0, 1), self.probabilityArrayForMultiplicator[Stats.DEX.value]
        )
        indexMulINT = rollInArrayWithRate(
            np.random.uniform(0, 1), self.probabilityArrayForMultiplicator[Stats.INT.value]
        )

        weapon.multiplierSTR = weaponMultiplier[indexMulSTR]
        weapon.multiplierDEX = weaponMultiplier[indexMulDEX]
        weapon.multiplierINT = weaponMultiplier[indexMulINT]


class Weapon(Holdable):
    DAMAGE_TYPE = ['BLUNT', 'SLASH', 'PIERCING', 'MAGICAL']

    def __init__(self, base: BaseWeapon, name: str = 'eq'):
        super().__init__(base, name)
        self.baseAttackValueRange: list[tuple(float, float)] = [(0, 0), (0, 0), (0, 0), (0, 0)]
        idx = len(weaponMultiplier) - 1
        self.multiplierSTR: tuple(str, float) = weaponMultiplier[idx]
        self.multiplierDEX: tuple(str, float) = weaponMultiplier[idx]
        self.multiplierINT: tuple(str, float) = weaponMultiplier[idx]
        self.two_handed: bool = False
        self.main_hand = True
        self.off_hand = False

    def onEquip():
        super().onEquip()

    @property
    def totalAttackRange(self):
        res = self.baseAttackValueRange.copy()

        # Flate modifier
        flatModifier = [
            self.getAffixValue(collection.AffixesKey.ADD_BLUNT_DAMAGE),
            self.getAffixValue(collection.AffixesKey.ADD_SLASH_DAMAGE),
            self.getAffixValue(collection.AffixesKey.ADD_PIERCING_DAMAGE),
            self.getAffixValue(collection.AffixesKey.ADD_MAGICAL_DAMAGE),
        ]

        for i in range(len(res)):
            if flatModifier[i] != 0:
                res[i] = (res[i][0] + flatModifier[i][0], res[i][1] + flatModifier[i][1])

        # Percent modifier
        percentModifier = [
            self.getAffixValue(collection.AffixesKey.PERCENT_BLUNT),
            self.getAffixValue(collection.AffixesKey.PERCENT_SLASH),
            self.getAffixValue(collection.AffixesKey.PERCENT_PIERCING),
            self.getAffixValue(collection.AffixesKey.PERCENT_MAGICAL),
        ]

        for i in range(len(res)):
            res[i] = (
                res[i][0] + res[i][0] * percentModifier[i] / 100,
                res[i][1] + res[i][1] * percentModifier[i] / 100,
            )

        return res

    def getItemPowerValue(self) -> float:
        flat_mul = 1
        percent_mul = 1
        leech_mul = 1
        synergy_mul = 1
        stats_mul = 1
        res_mul = 1
        crit_mul = 1
        crit_synergy_mul = 1

        # Flate modifier
        Rabd = self.getAffixValue(collection.AffixesKey.ADD_BLUNT_DAMAGE)
        abd = (Rabd[0] + Rabd[1]) / 2
        Rasd = self.getAffixValue(collection.AffixesKey.ADD_SLASH_DAMAGE)
        asd = (Rasd[0] + Rasd[1]) / 2
        Rapd = self.getAffixValue(collection.AffixesKey.ADD_PIERCING_DAMAGE)
        apd = (Rapd[0] + Rapd[1]) / 2
        Ramd = self.getAffixValue(collection.AffixesKey.ADD_MAGICAL_DAMAGE)
        amd = (Ramd[0] + Ramd[1]) / 2

        # Percent modifier
        pb = self.getAffixValue(collection.AffixesKey.PERCENT_BLUNT)
        ps = self.getAffixValue(collection.AffixesKey.PERCENT_SLASH)
        pp = self.getAffixValue(collection.AffixesKey.PERCENT_PIERCING)
        pm = self.getAffixValue(collection.AffixesKey.PERCENT_MAGICAL)

        pl = self.getAffixValue(collection.AffixesKey.PERCENT_LEECH)

        strM = self.getAffixValue(collection.AffixesKey.TO_STR)
        dexM = self.getAffixValue(collection.AffixesKey.TO_DEX)
        intM = self.getAffixValue(collection.AffixesKey.TO_INT)
        lukM = self.getAffixValue(collection.AffixesKey.TO_LUK)

        br = self.getAffixValue(collection.AffixesKey.BLUNT_RES)
        sr = self.getAffixValue(collection.AffixesKey.SLASH_RES)
        pr = self.getAffixValue(collection.AffixesKey.PIERCING_RES)
        mr = self.getAffixValue(collection.AffixesKey.MAGICAL_RES)

        cr = self.getAffixValue(collection.AffixesKey.CRITICAL_RATE)
        csm = self.getAffixValue(collection.AffixesKey.CRITICAL_STRIKE_MULTIPLYER)

        return (
            flat_mul * (abd + asd + apd + amd)
            + percent_mul * (pb + ps + pp + pm)
            + leech_mul * pl
            + synergy_mul * ((abd * pb) + (asd * ps) + (apd * pp) + (amd * pm))
            + stats_mul * (strM + dexM + intM + lukM)
            + res_mul * (br + sr + pr + mr)
            + crit_mul * (cr + csm)
            + crit_synergy_mul * (cr * csm)
        )

    def attackValue(self, charaStatValue) -> float:
        multipliers = [
            charaStatValue[Stats.STR.value] * self.multiplierSTR[1],
            charaStatValue[Stats.DEX.value] * self.multiplierDEX[1],
            charaStatValue[Stats.INT.value] * self.multiplierINT[1],
        ]

        att_roll = [0, 0, 0, 0]
        att = self.totalAttackRange
        for i in range(len(self.baseAttackValueRange)):
            att_roll[i] = np.random.uniform(att[i][0], att[i][1]) * sum(multipliers)

        return att_roll


#########
# Armor #
#########
class Armor(Equipable):
    def __init__(self, base: Base = None, name: str = 'eq') -> None:
        super().__init__(base, name)
        self.armor: float = 0
        self.evade: float = 0


##########
# Shield #
##########
class BaseShield(Base):
    def __init__(
        self, prefixesPool: dict[str, Modifier], suffixesPool: dict[str, Modifier]
    ) -> None:
        super().__init__(prefixesPool, suffixesPool)
        self.blockRange: tuple(float, float)
        self.armorRange: tuple(float, float)
        self.evadeRange: tuple(float, float)

    def roll(self, shield: Shield):
        self.rollBaseDef(shield)
        self.rollPrefixes(shield)
        self.rollSuffixes(shield)

    def rollBaseDef(self, shield: Shield):
        shield.block = np.random.uniform(self.blockRange[0], self.blockRange[1])
        shield.armor = np.random.uniform(self.armorRange[0], self.armorRange[1])
        shield.evade = np.random.uniform(self.evadeRange[0], self.evadeRange[1])


class Shield(Holdable):
    def __init__(self, base: Base = None, name: str = 'eq') -> None:
        super().__init__(base, name)
        self.block: float
        self.main_hand = False
        self.off_hand = True

    def getItemPowerValue(self) -> float:
        return super().getItemPowerValue()

    def onEquip():
        pass


##############
# Body Armor #
##############
class BaseBodyArmor(Base):
    def __init__(
        self, prefixesPool: dict[str, Modifier], suffixesPool: dict[str, Modifier]
    ) -> None:
        super().__init__(prefixesPool, suffixesPool)
        self.armorRange: tuple(float, float)
        self.evadeRange: tuple(float, float)

    def roll(self, bodyArmor: BodyArmor):
        self.rollBaseDef(bodyArmor)
        self.rollPrefixes(bodyArmor)
        self.rollSuffixes(bodyArmor)

    def rollBaseDef(self, bodyArmor: BodyArmor):
        bodyArmor.armor = np.random.uniform(self.armorRange[0], self.armorRange[1])
        bodyArmor.evade = np.random.uniform(self.evadeRange[0], self.evadeRange[1])


class BodyArmor(Armor):
    def onEquip(self):
        super().onEquip()

    def onStore(self):
        return super().onStore()

    def getItemPowerValue(self) -> float:
        return super().getItemPowerValue()
