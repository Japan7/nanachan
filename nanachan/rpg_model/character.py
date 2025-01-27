from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

import nanachan.rpg_model.expedition_collection as collection
from nanachan.nanapi._client import success
from nanachan.nanapi.client import get_nanapi
from nanachan.nanapi.model import WaicolleRank, WaifuSelectResult
from nanachan.rpg_model.equipment import BodyArmor, Holdable, Shield, Weapon
from nanachan.rpg_model.HeroClass import HeroClass, Skills, chooseHeroClass
from nanachan.rpg_model.rpg_waicolle_utils import (
    AttackStatus,
    DamageType,
    Stats,
    rollInArrayWithRate,
)

RANK_STAT_MAP = [
    WaicolleRank.S,
    WaicolleRank.A,
    WaicolleRank.B,
    WaicolleRank.C,
    WaicolleRank.D,
    WaicolleRank.E,
]
STAT_UP_RATES = [0.9, 0.85, 0.80, 0.75, 0.6, 0.5]

if TYPE_CHECKING:
    from .expedition_collection import SkillKey


# stats [STR, DEX, INT, LUK]
# STR = HP
# DEX = DODGE && who start combat in first
# INT = RES Magique && magic damage multiplier
# LUK = :shrug:
async def getHeroRank(waifu: WaifuSelectResult) -> int:
    chara_resp = await get_nanapi().anilist.anilist_get_charas(str(waifu.character.id_al))
    if not success(chara_resp):
        raise RuntimeError(chara_resp.result)

    return RANK_STAT_MAP.index(chara_resp.result[0].rank)


def selectStatFromHeroClassRate(heroClass: HeroClass) -> int:
    res = 0
    r = np.random.uniform(0, 1)
    accumulator = heroClass.lvlUpRate[0]
    for i in range(len(heroClass.lvlUpRate)):
        if r > accumulator:
            accumulator = accumulator + heroClass.lvlUpRate[i]
        else:
            res = i
            break
    return res


#############
# Character #
#############
class Character:
    # take dammage status :
    # 0 = take damage
    # 1 = dodge

    def __init__(self, waifu: WaifuSelectResult | None = None, name: str = '') -> None:
        self.id: int
        self.waifu: WaifuSelectResult | None = waifu
        self.name: str = name
        # r: int = getHeroRank(waifu)
        self.heroRank: int = 0

        self.omamori = None
        self.bodyArmor: BodyArmor = collection.Skin
        self.main_hand: Holdable = collection.fist
        self.off_hand: Holdable = collection.fist

        self.level: int = 1
        self.stats: list[float] = [2.0, 2.0, 2.0, 1.0]
        self.hp: float = self.maxHPNumber

        self.criticMultiplicator = 1.2
        self.skillSet = Skills(collection.STANDARD_SKILL_ROLL_RATE_WEIGHT.copy())
        skillNumber = 0
        if self.heroRank == 0:
            skillNumber = 2
        elif self.heroRank > 0:
            skillNumber = 1

        if skillNumber > 0:
            self.skillSet.rollSkill(skillNumber)

    def setSkill(self, skillToActivate: list[SkillKey]):
        for sn in skillToActivate:
            self.skillSet.skills[sn] = 1

    async def setHeroRank(self):
        self.heroRank = await getHeroRank(self.waifu)

    # def getHPMultiplicator(self) -> float:
    #     return 1 + (self.stats[0]/10)

    #################
    # natural stats #
    #################
    @property
    def naturalSTR(self) -> float:
        return self.stats[Stats.STR.value]

    @property
    def naturalDEX(self) -> float:
        return self.stats[Stats.DEX.value]

    @property
    def naturalINT(self) -> float:
        return self.stats[Stats.INT.value]

    @property
    def naturalLUK(self) -> float:
        return self.stats[Stats.LUK.value]

    @property
    def naturalEvade(self) -> float:
        return self.stats[Stats.DEX.value] / (self.stats[Stats.DEX.value] + 200)

    @property
    def naturalLife(self) -> float:
        return np.floor(self.level * 2 + 5)

    @property
    def naturalCriticalRate(self) -> float:
        luk = self.totalLUK
        dex = self.totalDEX
        lukModifier = luk / (luk + 100)
        dexModifier = dex / (dex + 200)
        return min(lukModifier + dexModifier, 1)

    @property
    def naturalCriticalStrike(self) -> float:
        return 1.2

    @property
    def naturalAccuracy(self) -> float:
        base = 90
        # Bold
        bold = self.skillSet.skills[collection.SkillKey.BOLD]
        if bold.have:
            base -= bold.accurracy_modifier
        natural = min(base + self.totalLUK, 100)

        return natural / 100

    @property
    def initiativeRoll(self) -> float:
        dex = self.stats[Stats.DEX.value]

        # Trickster
        trickster = self.skillSet.skills[collection.SkillKey.TRICKSTER]
        if trickster.have and self.currentHPPercentage <= trickster.hp_threshold:
            return 707340

        # Brute
        brute = self.skillSet.skills[collection.SkillKey.BRUTE]
        if brute.have:
            return -1

        res = np.random.uniform(0, dex)
        return res

    @property
    def currentHPPercentage(self) -> float:
        return self.hp / self.maxHPNumber

    #########
    # Stats #
    #########
    @property
    def totalSTR(self) -> float:
        res = self.naturalSTR
        str_key = collection.AffixesKey.TO_STR
        res += self.bodyArmor.getAffixValue(str_key)
        res += self.main_hand.getAffixValue(str_key)
        res += self.off_hand.getAffixValue(str_key)
        return res

    @property
    def totalDEX(self) -> float:
        res = self.naturalDEX
        dex_key = collection.AffixesKey.TO_DEX
        res += self.bodyArmor.getAffixValue(dex_key)
        res += self.main_hand.getAffixValue(dex_key)
        res += self.off_hand.getAffixValue(dex_key)
        return res

    @property
    def totalINT(self) -> float:
        res = self.naturalINT
        int_key = collection.AffixesKey.TO_INT
        res += self.bodyArmor.getAffixValue(int_key)
        res += self.main_hand.getAffixValue(int_key)
        res += self.off_hand.getAffixValue(int_key)
        return res

    @property
    def totalLUK(self) -> float:
        res = self.naturalLUK
        luk_key = collection.AffixesKey.TO_LUK
        res += self.bodyArmor.getAffixValue(luk_key)
        res += self.main_hand.getAffixValue(luk_key)
        res += self.off_hand.getAffixValue(luk_key)
        return res

    ###########
    # defense #
    ###########
    @property
    def armorScore(self) -> float:
        res = 0
        fa_key = collection.AffixesKey.FLAT_ARMOR
        pa_key = collection.AffixesKey.PERCENT_ARMOR

        armor = self.bodyArmor
        ba_value = armor.armor
        ba_value += armor.getAffixValue(fa_key)
        ba_value += ba_value * (armor.getAffixValue(pa_key) / 100)
        res += ba_value

        oh_value = 0
        if isinstance(self.off_hand, Shield):
            oh_value += self.off_hand.armor
            oh_value += self.off_hand.getAffixValue(fa_key)
            oh_value += oh_value * (self.off_hand.getAffixValue(pa_key) / 100)

        res += oh_value

        return res

    @property
    def evadeScore(self) -> float:
        res = self.naturalEvade

        res += self.bodyArmor.evade

        res += self.bodyArmor.getAffixValue(collection.AffixesKey.PERCENT_EVASION)

        if isinstance(self.off_hand, Shield):
            res += self.off_hand.evade

        return res / 100

    @property
    def blockScore(self) -> float:
        res = 0
        if isinstance(self.off_hand, Shield):
            res += self.off_hand.block
        return res

    @property
    def criticalRate(self) -> float:
        crit_rate_key = collection.AffixesKey.CRITICAL_RATE
        res = self.naturalCriticalRate
        res += self.main_hand.getAffixValue(crit_rate_key)
        res += self.off_hand.getAffixValue(crit_rate_key)

        return res

    @property
    def criticalStrike(self) -> float:
        crit_strike_key = collection.AffixesKey.CRITICAL_STRIKE_MULTIPLYER
        res = self.naturalCriticalStrike
        res += self.main_hand.getAffixValue(crit_strike_key)
        res += self.off_hand.getAffixValue(crit_strike_key)

        return res

    @property
    def accuracy(self) -> float:
        res = self.naturalAccuracy
        # Add modifier

        return res

    #######
    # Res #
    #######
    @property
    def bluntRes(self) -> float:
        br_key = collection.AffixesKey.BLUNT_RES
        res = 0

        res += self.bodyArmor.getAffixValue(br_key)

        res += self.main_hand.getAffixValue(br_key)

        res += self.off_hand.getAffixValue(br_key)

        return res / 100

    @property
    def slashRes(self) -> float:
        sr_key = collection.AffixesKey.SLASH_RES
        res = 0

        res += self.bodyArmor.getAffixValue(sr_key)

        res += self.main_hand.getAffixValue(sr_key)

        res += self.off_hand.getAffixValue(sr_key)

        return res / 100

    @property
    def piercingRes(self) -> float:
        pr_key = collection.AffixesKey.PIERCING_RES
        res = 0

        res += self.bodyArmor.getAffixValue(pr_key)

        res += self.main_hand.getAffixValue(pr_key)

        res += self.off_hand.getAffixValue(pr_key)

        return res / 100

    @property
    def magicalRes(self) -> float:
        mr_key = collection.AffixesKey.MAGICAL_RES
        res = 0

        res += self.bodyArmor.getAffixValue(mr_key)

        res += self.main_hand.getAffixValue(mr_key)

        res += self.off_hand.getAffixValue(mr_key)

        return res / 100

    @property
    def maxHPNumber(self) -> int:
        # flat hp
        res = self.naturalLife
        res += self.bodyArmor.getAffixValue(collection.AffixesKey.FLAT_LIFE)

        # multiplyer
        res += res * (self.bodyArmor.getAffixValue(collection.AffixesKey.PERCENT_LIFE) / 100)

        return res

    #########
    # Equip #
    #########
    def equipMainHand(self, new_weapon: Holdable) -> Holdable | None:
        if not new_weapon.main_hand:
            return None

        currentWeapon = self.main_hand
        self.main_hand = new_weapon
        return currentWeapon

    def equipOffHand(self, new_off_hand: Holdable) -> Holdable | None:
        if self.main_hand.two_handed or not new_off_hand.off_hand:
            return None
        currentOffHand = self.off_hand
        self.off_hand = new_off_hand
        return currentOffHand

    def equipBodyArmor(self, new_body_armor: BodyArmor) -> BodyArmor:
        current_body_armor = self.bodyArmor
        self.bodyArmor = new_body_armor
        return current_body_armor

    #########
    # utils #
    #########
    @property
    def leachPercentage(self) -> float:
        res = 0
        res += self.main_hand.getAffixValue(collection.AffixesKey.PERCENT_LEECH)

        return res / 100

    @property
    def healOnKill(self) -> float:
        res = 0
        res += self.main_hand.getAffixValue(collection.AffixesKey.LIFE_GAIN_ON_KILL)
        return res

    @property
    def reflectPercentage(self) -> float:
        res = 0
        res += self.off_hand.getAffixValue(collection.AffixesKey.PERCENT_REFLECT)

        return res / 100

    ###########
    # actions #
    ###########
    @property
    def totalAttackValue(self) -> list[float]:
        attackValue = self.main_hand.attackValue(self.stats)
        # Skill modifier
        # Bold
        bold = self.skillSet.skills[collection.SkillKey.BOLD]
        if bold.have:
            mul = bold.damage_multiplicator
            attackValue = self.applyMulToAttackRoll(attackValue, mul)

        # Berserk
        berserk = self.skillSet.skills[collection.SkillKey.BERSERK]
        if berserk.have and self.currentHPPercentage <= berserk.hp_threshold:
            mul = berserk.damage_multiplicator
            attackValue = self.applyMulToAttackRoll(attackValue, mul)

        # Brute
        brute = self.skillSet.skills[collection.SkillKey.BERSERK]
        if brute.have:
            mul = brute.damage_multiplicator
            attackValue = self.applyMulToAttackRoll(attackValue, mul)

        return attackValue

    def applyMulToAttackRoll(self, attackValue: list, mul) -> list:
        return [
            attackValue[DamageType.BLUNT.value] * mul,
            attackValue[DamageType.SLASH.value] * mul,
            attackValue[DamageType.PIERCING.value] * mul,
            attackValue[DamageType.MAGICAL.value] * mul,
        ]

    def attack(self, target: Character) -> str:
        logResult = ''
        attackValue: list[float] = self.totalAttackValue

        # Miss
        if np.random.uniform(0, 1) > self.accuracy:
            logResult += f'{self.name} missed :slddfrts:\n'
            return logResult

        # Critic
        if self.isCritic:
            mul = self.criticalStrike
            attackValue = self.applyMulToAttackRoll(attackValue, mul)
            logResult += f'{self.name} try attacking {target.name} (critic) for {attackValue}\n'
        else:
            logResult += f'{self.name} try attacking {target.name} for {attackValue}\n'

        status, damage_delt = target.takeDamage(attackValue, self)

        # Target dodged
        if status == AttackStatus.DODGED:
            logResult += f'{target.name} dodged !\n'
            return logResult

        # Target blocked
        if status == AttackStatus.BLOCKED:
            logResult += f'{target.name} blocked !\n'
            return logResult

        logResult += f'{self.name} inflict {damage_delt} to {target.name}\n'

        heal_amount = damage_delt * self.leachPercentage

        # leached life
        if heal_amount > 0:
            self.heal(heal_amount)
            logResult += f'{self.name} leach {heal_amount}HP\n'

        # target dead
        if target.isDead:
            amount = self.healOnKill
            self.heal(amount)
            logResult += f'{self.name} killed {target.name}\n'
            if amount > 0:
                logResult += f'{self.name} heal {amount}HP'

        return logResult

    def takeFlatDamage(self, dmg: float):
        self.hp - dmg

    # return status and damage taken
    def takeDamage(self, dmg: list[float], takeFrom: Character) -> tuple(AttackStatus, float):
        if self.isDodged:
            return (AttackStatus.DODGED, 0)

        if self.isBlocked:
            return (AttackStatus.BLOCKED, 0)

        blunt_dmg = dmg[DamageType.BLUNT.value] * (1.0 - self.bluntRes)
        slash_dmg = dmg[DamageType.SLASH.value] * (1.0 - self.slashRes)
        piercing_dmg = dmg[DamageType.PIERCING.value] * (1.0 - self.piercingRes)
        magical_dmg = dmg[DamageType.MAGICAL.value] * (1.0 - self.magicalRes)
        armor_score = self.armorScore

        actualDmg = blunt_dmg + slash_dmg + piercing_dmg
        actualDmg -= armor_score
        actualDmg = max(0, actualDmg) + magical_dmg

        self.hp = self.hp - actualDmg

        takeFrom.takeFlatDamage(self.reflectPercentage * actualDmg)

        if self.hp < 0:
            self.hp = 0

        second_wind = self.skillSet.skills[collection.SkillKey.SECOND_WIND]
        if self.hp == 0 and second_wind.have and second_wind.use() > 0:
            self.hp = 1

        return (0, actualDmg)

    @property
    def isDodged(self) -> bool:
        return np.random.uniform(0, 1) < self.evadeScore

    @property
    def isBlocked(self) -> bool:
        return np.random.uniform(0, 1) < self.blockScore

    @property
    def isCritic(self) -> bool:
        return np.random.uniform(0, 1) < self.criticalRate

    @property
    def isDead(self) -> bool:
        return self.hp <= 0

    def heal(self, amount):
        self.hp += amount
        if self.hp > self.maxHPNumber:
            self.hp = self.maxHPNumber

    def turnCooldown(self):
        for s in self.skillSet.skills:
            self.skillSet.skills[s].onCooldownTurn()

    def combatCooldown(self):
        for s in self.skillSet.skills:
            self.skillSet.skills[s].onCooldownCombat()

    @property
    def levelThreshold(self) -> int:
        x = (self.level * 5) / 2
        return np.floor(x * x)


########
# Hero #
########
class Hero(Character):
    def __init__(self, waifu: WaifuSelectResult, name: str = '') -> None:
        super().__init__(waifu=waifu, name=name)
        self.level = 1
        self.xp = 0
        self.heroClass = chooseHeroClass(waifu)
        self.stats = self.heroClass.stats
        self.main_hand = collection.fist

        self.name = waifu.custom_name if waifu.custom_name else name
        # self.skills = [getRandomSkill()]
        # if (self.heroRank == 0)
        #    self.sills.append(getRandomSkill())

    async def resetHero(self):
        self.heroRank = await getHeroRank(self.waifu)
        self.level = 1
        self.xp = 0
        self.heroClass = chooseHeroClass(self.waifu)
        self.stats = self.heroClass.stats
        self.omamori = None

    def unequipWeapon(self) -> Weapon:
        return self.equipMainHand(collection.fist)

    def equipWeapon(self, weapon: Weapon) -> Weapon:
        return self.equipMainHand(weapon)

    def gainXP(self, amount):
        fast_learner = self.skillSet.skills[collection.SkillKey.FAST_LEARNER]
        if fast_learner.have:
            amount = amount * fast_learner.xp_multiplier

        while amount > 0:
            thresholdForCurrentLevel = self.levelThreshold
            xpToGainForLevel = amount

            if amount >= thresholdForCurrentLevel:
                xpToGainForLevel = thresholdForCurrentLevel
                self.levelUp()

            self.xp += xpToGainForLevel
            amount -= xpToGainForLevel

    def levelUp(self):
        self.level += 1
        if np.random.uniform(0, 1) < STAT_UP_RATES[self.heroRank]:
            self.stats[rollInArrayWithRate(np.random.uniform(0, 1), self.heroClass.lvlUpRate)] += 1

        prodigy = self.skillSet.skills[collection.SkillKey.PRODIGY]
        if prodigy.have and prodigy.use() == 1:
            self.stats[rollInArrayWithRate(np.random.uniform(0, 1), self.heroClass.lvlUpRate)] += 1

    def goToLevel(self, level: int):
        if level < self.level:
            return

        for _ in range(self.level, level):
            self.gainXP(self.levelThreshold)


#########
# Enemy #
#########
class Enemy(Character):
    def generate(self):
        self.hp: float = self.maxHPNumber

    @property
    def reward(self):
        xp = max(self.levelThreshold / 100, 1)
        loot = []
        loot = collection.getLootFromMobLevel(self.level)
        if self.main_hand != collection.fist:
            loot.extend(self.main_hand.scrap())
        if self.off_hand != collection.fist:
            loot.extend(self.off_hand.scrap())
        return {'xp': xp, 'loot': loot}
