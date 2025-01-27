from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import numpy as np

import nanachan.rpg_model.expedition_collection as collection
from nanachan.nanapi.model import WaifuSelectResult
from nanachan.rpg_model.rpg_waicolle_utils import normalizeArray, rollInArrayWithRate

if TYPE_CHECKING:
    from .expedition_collection import SkillKey

##########
# Skills #
##########


class Skill(ABC):
    def __init__(self):
        self.name = ''
        self.activable = False
        self.cooldownTurn = -1
        self.cooldownCombat = -1
        self.currentCooldownTurn = -1
        self.currentCooldownCombat = -1
        self.have = False

    def onCooldownTurn(self):
        self.currentCooldownTurn = min(self.currentCooldownTurn + 1, self.cooldownTurn)
        if self.currentCooldownTurn > 0:
            self.activable = True

    def onCooldownCombat(self):
        self.currentCooldownCombat = min(self.currentCooldownCombat + 1, self.cooldownCombat)
        if self.currentCooldownCombat > 0:
            self.activable = True

    @abstractmethod
    def use(self) -> float:
        pass


class Lucky(Skill):
    def __init__(self):
        super().__init__()
        self.cooldownCombat = 1
        self.currentCooldownCombat = 1
        self.name = 'Lucky'
        self.activable = True

    # return 1 if reroll available 0 else
    def use(self):
        res = 0
        if self.activable:
            res = 1
            self.currentCooldownCombat = 0
            self.activable = False
        return res


class GoodRest(Skill):
    def __init__(self):
        super().__init__()
        self.name = 'Rest'
        self.multiplyer = 0.5

    # return the multiplicator of hp got for resting
    def use(self) -> float:
        return self.multiplyer


class SecondWind(Skill):
    def __init__(self):
        super().__init__()
        self.name = 'Second wind'
        self.cooldownCombat = 1
        self.currentCooldownCombat = 1
        self.rate = 0.66

    # return 1 if usable 0 else
    def use(self):
        res = 0
        if self.activable:
            if np.random.uniform(0, 1) < self.rate:
                res = 1
            self.currentCooldownCombat = 0
            self.activable = False
        return res


class Prodigy(Skill):
    def __init__(self):
        super().__init__()
        self.chance = 0.1

    # return 1 if it activate 0 else
    def use(self) -> float:
        r = np.random.uniform(0, 1)
        if r < self.chance:
            return 1
        return 0


class Bold(Skill):
    def __init__(self):
        super().__init__()
        self.accurracy_modifier = 5
        self.damage_multiplicator = 1.1

    def use(self) -> float:
        return super().use()


class Berserk(Skill):
    def __init__(self):
        super().__init__()
        self.damage_multiplicator = 1.3
        self.hp_threshold = 0.2

    def use(self) -> float:
        return super().use()


class Trickster(Skill):
    def __init__(self):
        super().__init__()
        self.hp_threshold = 0.5

    def use(self) -> float:
        return super().use()


class Brute(Skill):
    def __init__(self):
        super().__init__()
        self.damage_multiplicator = 1.3

    def use(self) -> float:
        return super().use()


class FastLearner(Skill):
    def __init__(self):
        super().__init__()
        self.xp_multiplier = 1.2

    def use(self) -> float:
        return super().use()


class MagicCursed(Skill):
    def use(self) -> float:
        return super().use()


class PhysicalCursed(Skill):
    def use(self) -> float:
        return super().use()


class Skills:
    def __init__(self, skillRollRate: list[float] = None) -> None:
        # self.activeSkills: list[int] = []
        self.skillRate: list[float] = normalizeArray(skillRollRate or [])
        # print(self.skillRate)
        self.skills: dict[SkillKey, Skill] = collection.get_skill_dict()

    def rollSkill(self, number: int):
        for _ in range(number):
            rNum = np.random.uniform(0, 1)
            idx = rollInArrayWithRate(rNum, self.skillRate)
            self.skills[list(self.skills.keys())[idx]].have = True
            self.skillRate[idx] = 0
            self.skillRate = normalizeArray(self.skillRate)
            # print(self.skillRate)


##############
# Hero Class #
##############


class HeroClass:
    def __init__(self, name: str, init: list[float], lvlUpRate: list[float], weight: float):
        self.stats: list[float] = []
        self.stats = init
        self.lvlUpRate = normalizeArray(lvlUpRate)
        self.weight = weight  # the class weight in the pool (for rand purpose)
        self.name = name


def chooseHeroClass(waifu: WaifuSelectResult) -> HeroClass:
    pool = collection.BASE_CLASS_POOL
    # pool = addEcclusiveClassForWaifuTagsToThePool(WaifuSelectResult.anime.tags, pool)
    rates = []
    for c in pool:
        rates.append(c.weight)
    rates = normalizeArray(rates)
    return pool[rollInArrayWithRate(np.random.uniform(0, 1), rates)]
