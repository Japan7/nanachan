from collections import OrderedDict
from enum import Enum
from functools import partial

import numpy as np

from nanachan.rpg_model.character import Enemy
from nanachan.rpg_model.currencies import (
    AlchemyOrb,
    AlterationOrb,
    BlessedOrb,
    ChaosOrb,
    KartReparationKit,
    ScouringOrb,
    TransmutationOrb,
)
from nanachan.rpg_model.equipment import (
    BaseShield,
    BaseWeapon,
    BodyArmor,
    Modifier,
    Shield,
    Storable,
    Weapon,
    getWeaponMultiplierFromRankName,
    weaponMultiplier,
)
from nanachan.rpg_model.expedition import Combat, Expedition, Rest
from nanachan.rpg_model.HeroClass import (
    Berserk,
    Bold,
    Brute,
    FastLearner,
    GoodRest,
    HeroClass,
    Lucky,
    MagicCursed,
    PhysicalCursed,
    Prodigy,
    SecondWind,
    Trickster,
)
from nanachan.rpg_model.rpg_waicolle_utils import (
    DamageType,
    genElementArrayFromPool,
    genElementArrayFromPool2,
)


###########
# Affixes #
###########
class AffixesKey(Enum):
    FLAT_ARMOR = 'Flat armor'
    PERCENT_ARMOR = 'Percent armor'
    FLAT_LIFE = 'Flat life'
    PERCENT_LIFE = 'Percent life'
    PERCENT_EVASION = 'Percent evasion'
    TO_STR = 'To str'
    TO_DEX = 'To dex'
    TO_INT = 'To int'
    TO_LUK = 'To luk'
    BLUNT_RES = 'Blunt res'
    SLASH_RES = 'Slash res'
    PIERCING_RES = 'Piercing res'
    MAGICAL_RES = 'Magical res'
    ALL_RES = 'All res'
    ADD_BLUNT_DAMAGE = 'Add blunt damage'
    ADD_SLASH_DAMAGE = 'Add slash damage'
    ADD_PIERCING_DAMAGE = 'Add piercing damage'
    ADD_MAGICAL_DAMAGE = 'Add magical damage'
    PERCENT_BLUNT = 'Percent blunt'
    PERCENT_SLASH = 'Percent slash'
    PERCENT_PIERCING = 'Percent piercing'
    PERCENT_MAGICAL = 'Percent magical'
    PERCENT_LEECH = 'Percent leech'
    PERCENT_REFLECT = 'Percent reflect'
    LIFE_GAIN_ON_KILL = 'Life gain on kill'
    CRITICAL_RATE = 'Critical rate'
    CRITICAL_STRIKE_MULTIPLYER = 'Critical strike multiplyer'
    BLOCK_CHANCE = 'Block chance'


AFFIXES: dict[AffixesKey, dict[int, tuple[int, int]]] = {
    AffixesKey.FLAT_ARMOR: {1: (1, 5)},
    AffixesKey.PERCENT_ARMOR: {1: (10, 20)},
    AffixesKey.FLAT_LIFE: {1: (1, 5)},
    AffixesKey.PERCENT_LIFE: {1: (4, 8)},
    AffixesKey.PERCENT_EVASION: {1: (4, 8)},
    AffixesKey.TO_STR: {1: (3, 6)},
    AffixesKey.TO_DEX: {1: (3, 6)},
    AffixesKey.TO_INT: {1: (3, 6)},
    AffixesKey.TO_LUK: {1: (3, 6)},
    AffixesKey.BLUNT_RES: {1: (6, 11)},
    AffixesKey.SLASH_RES: {1: (6, 11)},
    AffixesKey.PIERCING_RES: {1: (6, 11)},
    AffixesKey.MAGICAL_RES: {1: (4, 9)},
    AffixesKey.ALL_RES: {1: (2, 4)},
    AffixesKey.ADD_BLUNT_DAMAGE: {1: ((0.07, 0.15), (0.1, 0.2))},
    AffixesKey.ADD_SLASH_DAMAGE: {1: ((0.07, 0.15), (0.1, 0.2))},
    AffixesKey.ADD_PIERCING_DAMAGE: {1: ((0.07, 0.15), (0.1, 0.2))},
    AffixesKey.ADD_MAGICAL_DAMAGE: {1: ((0.05, 0.1), (0.1, 0.15))},
    AffixesKey.PERCENT_BLUNT: {1: (10, 20)},
    AffixesKey.PERCENT_SLASH: {1: (10, 20)},
    AffixesKey.PERCENT_PIERCING: {1: (10, 20)},
    AffixesKey.PERCENT_MAGICAL: {1: (10, 20)},
    AffixesKey.PERCENT_LEECH: {1: (10, 20)},
    AffixesKey.PERCENT_REFLECT: {1: (10, 20)},
    AffixesKey.LIFE_GAIN_ON_KILL: {1: (2, 7)},
    AffixesKey.CRITICAL_RATE: {1: (2, 5)},
    AffixesKey.CRITICAL_STRIKE_MULTIPLYER: {1: (5, 15)},
    AffixesKey.BLOCK_CHANCE: {1: (1, 3)},
}


s = np.random.default_rng()


def modifier1(key: AffixesKey, skill_level: int) -> float:
    t = AFFIXES[key][skill_level]
    return s.integers(*t, endpoint=True)


def modifier2(key: AffixesKey, skill_level: int) -> tuple:
    t = AFFIXES[key][skill_level]
    return (np.random.uniform(*t[0]), np.random.uniform(*t[1]))


flat_armor = partial(modifier1, AffixesKey.FLAT_ARMOR)
percent_armor = partial(modifier1, AffixesKey.PERCENT_ARMOR)
flat_life = partial(modifier1, AffixesKey.FLAT_LIFE)
percent_life = partial(modifier1, AffixesKey.PERCENT_LIFE)
percent_evasion = partial(modifier1, AffixesKey.PERCENT_EVASION)
to_str = partial(modifier1, AffixesKey.TO_STR)
to_dex = partial(modifier1, AffixesKey.TO_DEX)
to_int = partial(modifier1, AffixesKey.TO_INT)
to_luk = partial(modifier1, AffixesKey.TO_LUK)
blunt_res = partial(modifier1, AffixesKey.BLUNT_RES)
slash_res = partial(modifier1, AffixesKey.SLASH_RES)
piercing_res = partial(modifier1, AffixesKey.PIERCING_RES)
magical_res = partial(modifier1, AffixesKey.MAGICAL_RES)
all_res = partial(modifier1, AffixesKey.ALL_RES)
percent_blunt = partial(modifier1, AffixesKey.PERCENT_BLUNT)
percent_slash = partial(modifier1, AffixesKey.PERCENT_SLASH)
percent_piercing = partial(modifier1, AffixesKey.PERCENT_PIERCING)
percent_magical = partial(modifier1, AffixesKey.PERCENT_MAGICAL)
percent_leech = partial(modifier1, AffixesKey.PERCENT_LEECH)
percent_reflect = partial(modifier1, AffixesKey.PERCENT_REFLECT)
life_gain_on_kill = partial(modifier1, AffixesKey.LIFE_GAIN_ON_KILL)
critical_rate = partial(modifier1, AffixesKey.CRITICAL_RATE)
critical_strike_multiplyer = partial(modifier1, AffixesKey.CRITICAL_STRIKE_MULTIPLYER)
block_chance = partial(modifier1, AffixesKey.BLOCK_CHANCE)
add_blunt_damage = partial(modifier2, AffixesKey.ADD_BLUNT_DAMAGE)
add_slash_damage = partial(modifier2, AffixesKey.ADD_SLASH_DAMAGE)
add_piercing_damage = partial(modifier2, AffixesKey.ADD_PIERCING_DAMAGE)
add_magical_damage = partial(modifier2, AffixesKey.ADD_MAGICAL_DAMAGE)


# Body armor affixes
BODY_ARMOR_PREFIX: dict[AffixesKey, Modifier] = {}
BODY_ARMOR_PREFIX[AffixesKey.FLAT_ARMOR] = Modifier(flat_armor)
BODY_ARMOR_PREFIX[AffixesKey.PERCENT_ARMOR] = Modifier(percent_armor)
BODY_ARMOR_PREFIX[AffixesKey.FLAT_LIFE] = Modifier(percent_armor)
BODY_ARMOR_PREFIX[AffixesKey.PERCENT_EVASION] = Modifier(percent_evasion)


BODY_ARMOR_SUFFIX: dict[AffixesKey, Modifier] = {}
BODY_ARMOR_SUFFIX[AffixesKey.TO_STR] = Modifier(to_str)
BODY_ARMOR_SUFFIX[AffixesKey.TO_DEX] = Modifier(to_dex)
BODY_ARMOR_SUFFIX[AffixesKey.TO_INT] = Modifier(to_int)
BODY_ARMOR_SUFFIX[AffixesKey.TO_LUK] = Modifier(to_luk)
BODY_ARMOR_SUFFIX[AffixesKey.BLUNT_RES] = Modifier(blunt_res)
BODY_ARMOR_SUFFIX[AffixesKey.SLASH_RES] = Modifier(slash_res)
BODY_ARMOR_SUFFIX[AffixesKey.PIERCING_RES] = Modifier(piercing_res)
BODY_ARMOR_SUFFIX[AffixesKey.MAGICAL_RES] = Modifier(magical_res)
BODY_ARMOR_SUFFIX[AffixesKey.PERCENT_LIFE] = Modifier(percent_life)
BODY_ARMOR_SUFFIX[AffixesKey.ALL_RES] = Modifier(all_res)


# weapon affixes
WEAPON_PREFIX: dict[AffixesKey, Modifier] = {}
WEAPON_PREFIX[AffixesKey.ADD_BLUNT_DAMAGE] = Modifier(add_blunt_damage)
WEAPON_PREFIX[AffixesKey.ADD_SLASH_DAMAGE] = Modifier(add_slash_damage)
WEAPON_PREFIX[AffixesKey.ADD_PIERCING_DAMAGE] = Modifier(add_piercing_damage)
WEAPON_PREFIX[AffixesKey.ADD_MAGICAL_DAMAGE] = Modifier(add_magical_damage)
WEAPON_PREFIX[AffixesKey.PERCENT_BLUNT] = Modifier(percent_blunt)
WEAPON_PREFIX[AffixesKey.PERCENT_SLASH] = Modifier(percent_slash)
WEAPON_PREFIX[AffixesKey.PERCENT_PIERCING] = Modifier(percent_piercing)
WEAPON_PREFIX[AffixesKey.PERCENT_MAGICAL] = Modifier(percent_magical)
WEAPON_PREFIX[AffixesKey.PERCENT_LEECH] = Modifier(percent_leech)


WEAPON_SUFFIX: dict[AffixesKey, Modifier] = {}
WEAPON_SUFFIX[AffixesKey.TO_STR] = Modifier(to_str)
WEAPON_SUFFIX[AffixesKey.TO_DEX] = Modifier(to_dex)
WEAPON_SUFFIX[AffixesKey.TO_INT] = Modifier(to_int)
WEAPON_SUFFIX[AffixesKey.TO_LUK] = Modifier(to_luk)
WEAPON_SUFFIX[AffixesKey.BLUNT_RES] = Modifier(blunt_res)
WEAPON_SUFFIX[AffixesKey.SLASH_RES] = Modifier(slash_res)
WEAPON_SUFFIX[AffixesKey.PIERCING_RES] = Modifier(piercing_res)
WEAPON_SUFFIX[AffixesKey.MAGICAL_RES] = Modifier(magical_res)
WEAPON_SUFFIX[AffixesKey.LIFE_GAIN_ON_KILL] = Modifier(life_gain_on_kill)
WEAPON_SUFFIX[AffixesKey.CRITICAL_RATE] = Modifier(critical_rate)
WEAPON_SUFFIX[AffixesKey.CRITICAL_STRIKE_MULTIPLYER] = Modifier(critical_strike_multiplyer)


# shield affix
SHIELD_PREFIX: dict[AffixesKey, Modifier] = {}
SHIELD_PREFIX[AffixesKey.FLAT_ARMOR] = Modifier(flat_armor)
SHIELD_PREFIX[AffixesKey.FLAT_LIFE] = Modifier(flat_life)
SHIELD_PREFIX[AffixesKey.PERCENT_ARMOR] = Modifier(percent_armor)
SHIELD_PREFIX[AffixesKey.PERCENT_REFLECT] = Modifier(percent_reflect)


SHIELD_SUFFIX: dict[AffixesKey, Modifier] = {}
SHIELD_SUFFIX[AffixesKey.BLUNT_RES] = Modifier(blunt_res)
SHIELD_SUFFIX[AffixesKey.SLASH_RES] = Modifier(slash_res)
SHIELD_SUFFIX[AffixesKey.PIERCING_RES] = Modifier(piercing_res)
SHIELD_SUFFIX[AffixesKey.MAGICAL_RES] = Modifier(magical_res)
SHIELD_SUFFIX[AffixesKey.ALL_RES] = Modifier(all_res)
SHIELD_SUFFIX[AffixesKey.BLOCK_CHANCE] = Modifier(block_chance)


################
# Hero Classes #
################
Warrior = HeroClass('Warrior', [3.0, 1.0, 1.0, 1.0], [0.9, 0.04, 0.03, 0.03], 100)
Thief = HeroClass('Thief', [1.0, 3.0, 1.0, 1.0], [0.04, 0.9, 0.03, 0.03], 100)
Mage = HeroClass('Mage', [1.0, 1.0, 3.0, 1.0], [0.03, 0.03, 0.9, 0.04], 100)
Eiyuu = HeroClass('Eiyuu', [2.0, 2.0, 2.0, 1.0], [0.3, 0.3, 0.3, 0.1], 10)
Bakemono = HeroClass('Bakemono', [4.0, 3.0, 0.0, 1.0], [0.49, 0.49, 0.01, 0.01], 10)
Idol = HeroClass('Idol', [0.0, 1.0, 3.0, 3.0], [0.01, 0.09, 0.70, 0.20], 10)
Hikikomori = HeroClass('Hikikomori', [0.0, 0.0, 7.0, 0.0], [1, 1, 1, 1], 10)
Tsundere = HeroClass('Tsundere', [2.0, 3.0, 0.0, 2.0], [20, 10, 1, 20], 10)
Yandere = HeroClass('Yandere', [3.0, 1.0, 3.0, 0.0], [10, 1, 20, 0.1], 10)


BASE_CLASS_POOL = [Warrior, Mage, Thief, Tsundere, Yandere, Hikikomori]


###############
# Weapon Base #
###############
oneHandedBaseDamageMin = (0.2, 0.35)
oneHandedBaseDamageMax = (0.45, 0.6)

twoHandedBaseDamageMin = (0.3, 0.5)
twoHandedBaseDamageMax = (0.6, 0.75)


sword_multiplicator_probability = [
    [0.01, 0.1, 0.2, 0.3, 0.3, 0.09],  # STR
    [0.01, 0.1, 0.2, 0.3, 0.3, 0.09],  # DEX
    [0.00, 0.01, 0.09, 0.1, 0.3, 0.5],  # INT
]

axe_multiplicator_probability = [
    [0.02, 0.15, 0.3, 0.2, 0.13, 0.05],  # STR
    [0.0, 0.1, 0.1, 0.2, 0.3, 0.3],  # DEX
    [0.0, 0.01, 0.09, 0.1, 0.3, 0.5],  # INT
]

wand_multiplicator_probability = [
    [0.01, 0.01, 0.01, 0.03, 0.04, 0.9],  # STR
    [0.01, 0.01, 0.01, 0.03, 0.04, 0.9],  # DEX
    [0.05, 0.1, 0.3, 0.35, 0.1, 0.1],  # INT
]

dagger_multiplicator_probability = [
    [0.01, 0.01, 0.01, 0.03, 0.04, 0.9],  # STR
    [0.05, 0.1, 0.3, 0.35, 0.1, 0.1],  # DEX
    [0.01, 0.01, 0.01, 0.03, 0.04, 0.9],  # INT
]

oneHandedSwordBase: BaseWeapon = BaseWeapon(WEAPON_PREFIX, WEAPON_SUFFIX)
oneHandedSwordBase.baseDamageRollMin[DamageType.SLASH.value] = oneHandedBaseDamageMin
oneHandedSwordBase.baseDamageRollMax[DamageType.SLASH.value] = oneHandedBaseDamageMax
oneHandedSwordBase.probabilityArrayForMultiplicator = sword_multiplicator_probability

twoHandedSwordBase: BaseWeapon = BaseWeapon(WEAPON_PREFIX, WEAPON_SUFFIX)
twoHandedSwordBase.baseDamageRollMin[DamageType.SLASH.value] = twoHandedBaseDamageMin
twoHandedSwordBase.baseDamageRollMax[DamageType.SLASH.value] = twoHandedBaseDamageMax
twoHandedSwordBase.probabilityArrayForMultiplicator = sword_multiplicator_probability

oneHandedAxeBase: BaseWeapon = BaseWeapon(WEAPON_PREFIX, WEAPON_SUFFIX)
oneHandedAxeBase.baseDamageRollMin[DamageType.SLASH.value] = oneHandedBaseDamageMin
oneHandedAxeBase.baseDamageRollMax[DamageType.SLASH.value] = oneHandedBaseDamageMax
oneHandedAxeBase.probabilityArrayForMultiplicator = axe_multiplicator_probability

twoHandedAxeBase: BaseWeapon = BaseWeapon(WEAPON_PREFIX, WEAPON_SUFFIX)
twoHandedAxeBase.baseDamageRollMin[DamageType.SLASH.value] = twoHandedBaseDamageMin
twoHandedAxeBase.baseDamageRollMax[DamageType.SLASH.value] = twoHandedBaseDamageMax
twoHandedAxeBase.probabilityArrayForMultiplicator = axe_multiplicator_probability

daggerBase: BaseWeapon = BaseWeapon(WEAPON_PREFIX, WEAPON_SUFFIX)
daggerBase.baseDamageRollMin[DamageType.PIERCING.value] = oneHandedBaseDamageMin
daggerBase.baseDamageRollMax[DamageType.PIERCING.value] = oneHandedBaseDamageMax
daggerBase.probabilityArrayForMultiplicator = dagger_multiplicator_probability

wandBase: BaseWeapon = BaseWeapon(WEAPON_PREFIX, WEAPON_SUFFIX)
wandBase.baseDamageRollMin[DamageType.MAGICAL.value] = oneHandedBaseDamageMin
wandBase.baseDamageRollMax[DamageType.MAGICAL.value] = oneHandedBaseDamageMax
wandBase.probabilityArrayForMultiplicator = wand_multiplicator_probability

staffBase: BaseWeapon = BaseWeapon(WEAPON_PREFIX, WEAPON_SUFFIX)
staffBase.baseDamageRollMin[DamageType.MAGICAL.value] = twoHandedBaseDamageMin
staffBase.baseDamageRollMax[DamageType.MAGICAL.value] = twoHandedBaseDamageMax
staffBase.probabilityArrayForMultiplicator = wand_multiplicator_probability

###########
# Weapons #
###########
fist = Weapon(None, 'Fist')
fist.multiplierSTR = weaponMultiplier[5]
fist.multiplierDEX = weaponMultiplier[5]
fist.multiplierINT = weaponMultiplier[5]
fist.baseAttackValueRange[0] = (0.1, 0.15)  # blunt damage

oneHandedSword = Weapon(oneHandedSwordBase, 'One handed sword')
oneHandedSword.two_handed = False

twoHandedSword = Weapon(oneHandedSwordBase, 'Two handed sword')
twoHandedSword.two_handed = True

oneHandedAxe = Weapon(oneHandedAxeBase, 'One handed axe')
oneHandedAxe.two_handed = False

twoHandedAxe = Weapon(twoHandedAxeBase, 'Two handed axe')
twoHandedAxe.two_handed = True

dagger = Weapon(daggerBase, 'Dagger')
dagger.two_handed = False
dagger.off_hand = True

wand = Weapon(wandBase, 'Wand')
wand.two_handed = False

staff = Weapon(staffBase, 'Staff')
staff.two_handed = True


############
# Off hand #
############


###############
# Shield Base #
###############
shieldBlockStatsBaseRange = (6, 17)
shieldEvadeStatsBaseRange = (10, 20)
hybridStatsBaseRange = (5, 10)
shieldBaseArmor = (1, 4)
hybridBaseArmor = (0, 2)

towerShieldBase: BaseShield = BaseShield(SHIELD_PREFIX, SHIELD_SUFFIX)
towerShieldBase.blockRange = shieldBlockStatsBaseRange
towerShieldBase.evadeRange = (0, 0)
towerShieldBase.armorRange = shieldBaseArmor

bucklerShieldBase: BaseShield = BaseShield(SHIELD_PREFIX, SHIELD_SUFFIX)
bucklerShieldBase.blockRange = (0, 0)
bucklerShieldBase.evadeRange = shieldEvadeStatsBaseRange
bucklerShieldBase.armorRange = (0, 0)

hybridShieldBase: BaseShield = BaseShield(SHIELD_PREFIX, SHIELD_SUFFIX)
hybridShieldBase.blockRange = hybridStatsBaseRange
hybridShieldBase.evadeRange = hybridStatsBaseRange
hybridShieldBase.armorRange = hybridBaseArmor

##########
# Shield #
##########
towerShield = Shield(towerShieldBase, 'Tower Shield')

bucklerShield = Shield(bucklerShieldBase, 'Buckler Shield')

hybridShield = Shield(hybridShieldBase, 'Hybrid Shield')


###################
# Body Armor Base #
###################


##############
# Body armor #
##############
Skin = BodyArmor(None, 'Skin')


#####################
# Looting functions #
#####################
def getLootFromMobLevel(level: int) -> list[Storable]:
    itemWeight = max(0, level / 3 - 2)
    currencyWeightMul = max(0, level / 4 - 1)
    notingWeight = 10 / level + 10
    lootPool = [
        (oneHandedSword, itemWeight),
        (oneHandedAxe, itemWeight),
        (twoHandedSword, itemWeight),
        (twoHandedAxe, itemWeight),
        (staff, itemWeight),
        (wand, itemWeight),
        (dagger, itemWeight),
        (towerShield, itemWeight),
        (bucklerShield, itemWeight),
        (hybridShield, itemWeight),
        (TransmutationOrb(), 10 * currencyWeightMul),
        (AlterationOrb(), 20 * currencyWeightMul),
        (AlchemyOrb(), 1 * currencyWeightMul),
        (BlessedOrb(), 0.2 * currencyWeightMul),
        (ScouringOrb(), 0.2 * currencyWeightMul),
        (ChaosOrb(), 0.1 * currencyWeightMul),
        (None, notingWeight),
    ]

    lootNumber = np.ceil(level / 10)
    return genElementArrayFromPool2((lootNumber, lootNumber), lootPool)


##########
# Skills #
##########
class SkillKey(Enum):
    LUCKY = 'Lucky'
    GOOD_REST = 'Good Rest'
    SECOND_WIND = 'Second Wind'
    PRODIGY = 'Prodigy'
    BOLD = 'Bold'
    BERSERK = 'Berserk'
    TRICKSTER = 'Trickster'
    BRUTE = 'Brute'
    FAST_LEARNER = 'Fast learner'
    MAGIC_CURSED = 'Magic cursed'
    PHYSICAL_CURSED = 'Physical cursed'


STANDARD_SKILL_ROLL_RATE_WEIGHT = [0, 100, 100, 10, 100, 100, 100, 100, 1, 0, 0]


def get_skill_dict():
    skills = OrderedDict()
    skills[SkillKey.LUCKY] = Lucky()
    skills[SkillKey.GOOD_REST] = GoodRest()
    skills[SkillKey.SECOND_WIND] = SecondWind()
    skills[SkillKey.PRODIGY] = Prodigy()
    skills[SkillKey.BOLD] = Bold()
    skills[SkillKey.BERSERK] = Berserk()
    skills[SkillKey.TRICKSTER] = Trickster()
    skills[SkillKey.BRUTE] = Brute()
    skills[SkillKey.FAST_LEARNER] = FastLearner()
    skills[SkillKey.MAGIC_CURSED] = MagicCursed()
    skills[SkillKey.PHYSICAL_CURSED] = PhysicalCursed()
    return skills


##################
# Enemies Weapon #
##################
GreenAcidSlime = Weapon(None, 'Green acide slime')
GreenAcidSlime.two_handed = True
GreenAcidSlime.baseAttackValueRange[DamageType.MAGICAL.value] = (0.2, 0.5)
GreenAcidSlime.multiplierSTR = getWeaponMultiplierFromRankName('E')
GreenAcidSlime.multiplierDEX = getWeaponMultiplierFromRankName('E')
GreenAcidSlime.multiplierINT = getWeaponMultiplierFromRankName('D')

GoblinFist = Weapon(None, 'Goblin Fist')
GoblinFist.two_handed = True
GoblinFist.baseAttackValueRange[DamageType.BLUNT.value] = (0.2, 0.5)
GoblinFist.multiplierSTR = getWeaponMultiplierFromRankName('E')
GoblinFist.multiplierDEX = getWeaponMultiplierFromRankName('D')
GoblinFist.multiplierINT = getWeaponMultiplierFromRankName('E')

RustedDagger = Weapon(None, 'Robber rusted dagger')
RustedDagger.two_handed = False
RustedDagger.baseAttackValueRange[DamageType.SLASH.value] = (0.25, 0.6)
RustedDagger.multiplierSTR = getWeaponMultiplierFromRankName('D')
RustedDagger.multiplierDEX = getWeaponMultiplierFromRankName('C')
RustedDagger.multiplierINT = getWeaponMultiplierFromRankName('E')

WolfClaw = Weapon(None, 'Wolf Claw')
WolfClaw.two_handed = True
WolfClaw.baseAttackValueRange[DamageType.SLASH.value] = (0.25, 0.7)
WolfClaw.multiplierSTR = getWeaponMultiplierFromRankName('D')
WolfClaw.multiplierDEX = getWeaponMultiplierFromRankName('D')
WolfClaw.multiplierINT = getWeaponMultiplierFromRankName('E')

BlueAcidSlime = Weapon(None, 'Green acide slime')
BlueAcidSlime.two_handed = True
BlueAcidSlime.baseAttackValueRange[DamageType.MAGICAL.value] = (0.3, 0.75)
BlueAcidSlime.multiplierSTR = getWeaponMultiplierFromRankName('E')
BlueAcidSlime.multiplierDEX = getWeaponMultiplierFromRankName('E')
BlueAcidSlime.multiplierINT = getWeaponMultiplierFromRankName('C')

RustedSword = Weapon(None, 'Rusted Sword')
RustedSword.two_handed = False
RustedSword.baseAttackValueRange[DamageType.SLASH.value] = (0.4, 0.9)
RustedSword.multiplierSTR = getWeaponMultiplierFromRankName('C')
RustedSword.multiplierDEX = getWeaponMultiplierFromRankName('D')
RustedSword.multiplierINT = getWeaponMultiplierFromRankName('E')


SimpleShortBow = Weapon(None, 'Simple Short Bow')
SimpleShortBow.two_handed = True
SimpleShortBow.baseAttackValueRange[DamageType.PIERCING.value] = (0.6, 0.95)
SimpleShortBow.multiplierSTR = getWeaponMultiplierFromRankName('E')
SimpleShortBow.multiplierDEX = getWeaponMultiplierFromRankName('B')
SimpleShortBow.multiplierINT = getWeaponMultiplierFromRankName('E')

OldStaff = Weapon(None, 'Old Staff')
OldStaff.two_handed = True
OldStaff.baseAttackValueRange[DamageType.MAGICAL.value] = (0.5, 1.0)
OldStaff.multiplierSTR = getWeaponMultiplierFromRankName('E')
OldStaff.multiplierDEX = getWeaponMultiplierFromRankName('E')
OldStaff.multiplierINT = getWeaponMultiplierFromRankName('B')

RedAcidSlime = Weapon(None, 'Red Acid Slime')
RedAcidSlime.two_handed = True
RedAcidSlime.baseAttackValueRange[DamageType.MAGICAL.value] = (0.4, 1.0)
RedAcidSlime.multiplierSTR = getWeaponMultiplierFromRankName('E')
RedAcidSlime.multiplierDEX = getWeaponMultiplierFromRankName('E')
RedAcidSlime.multiplierINT = getWeaponMultiplierFromRankName('C')

LizzardMenSpear = Weapon(None, 'Lizzard Men Spear')
LizzardMenSpear.two_handed = False
LizzardMenSpear.baseAttackValueRange[DamageType.PIERCING.value] = (0.5, 1.1)
LizzardMenSpear.multiplierSTR = getWeaponMultiplierFromRankName('C')
LizzardMenSpear.multiplierDEX = getWeaponMultiplierFromRankName('C')
LizzardMenSpear.multiplierINT = getWeaponMultiplierFromRankName('E')

WoodenClub = Weapon(None, 'Wooden Club')
WoodenClub.two_handed = False
WoodenClub.baseAttackValueRange[DamageType.BLUNT.value] = (0.4, 1.2)
WoodenClub.multiplierSTR = getWeaponMultiplierFromRankName('A')
WoodenClub.multiplierDEX = getWeaponMultiplierFromRankName('E')
WoodenClub.multiplierINT = getWeaponMultiplierFromRankName('E')

WyvernClaw = Weapon(None, 'Wyvern Claw')
WyvernClaw.two_handed = True
WyvernClaw.baseAttackValueRange[DamageType.SLASH.value] = (1, 2)
WyvernClaw.multiplierSTR = getWeaponMultiplierFromRankName('B')
WyvernClaw.multiplierDEX = getWeaponMultiplierFromRankName('D')
WyvernClaw.multiplierINT = getWeaponMultiplierFromRankName('C')

RustedBucklerShield = Shield(None, 'Rusted Buckler Shield')
RustedBucklerShield.block = 2
RustedBucklerShield.evade = 20
RustedBucklerShield.armor = 2

RustedTowerShield = Shield(None, 'Rusted Tower Shield')
RustedTowerShield.block = 20
RustedTowerShield.evade = 2
RustedTowerShield.armor = 7

RustedHybridShield = Shield(None, 'Rusted Hybrid Shield')
RustedHybridShield.block = 10
RustedHybridShield.evade = 10
RustedHybridShield.armor = 4

###########
# Enemies #
###########
GreenSlime = Enemy(None, 'Green Slime')
GreenSlime.main_hand = GreenAcidSlime
GreenSlime.stats = [2, 1, 3, 1]
GreenSlime.level = 1
GreenSlime.generate()

Goblin = Enemy(None, 'Goblin')
Goblin.main_hand = GoblinFist
Goblin.stats = [2, 5, 2, 2]
Goblin.level = 5
Goblin.generate()

Robber = Enemy(None, 'Robber')
Robber.main_hand = RustedDagger
Robber.stats = [4, 4, 3, 1]
Robber.level = 6
Robber.generate()

Wolf = Enemy(None, 'Wolf')
Wolf.main_hand = WolfClaw
Wolf.stats = [3, 7, 1, 2]
Wolf.level = 8
Wolf.generate()

BlueSlime = Enemy(None, 'Blue Slime')
BlueSlime.main_hand = BlueAcidSlime
BlueSlime.stats = [4, 1, 9, 1]
BlueSlime.level = 11
BlueSlime.generate()

Skeleton = Enemy(None, 'Blue Slime')
Skeleton.main_hand = RustedSword
Skeleton.off_hand = RustedTowerShield
Skeleton.stats = [10, 5, 0, 4]
Skeleton.level = 15
Skeleton.generate()

GoblinArcher = Enemy(None, 'Goblin Archer')
GoblinArcher.main_hand = SimpleShortBow
GoblinArcher.stats = [4, 9, 3, 4]
GoblinArcher.level = 16
GoblinArcher.generate()

GoblinMage = Enemy(None, 'Goblin Mage')
GoblinMage.main_hand = SimpleShortBow
GoblinMage.stats = [2, 2, 14, 4]
GoblinMage.level = 18
GoblinMage.generate()

RedSlime = Enemy(None, 'RedSlime')
RedSlime.main_hand = RedAcidSlime
RedSlime.stats = [5, 2, 10, 5]
RedSlime.level = 20
RedSlime.generate()

LizzardMan = Enemy(None, 'Lizzard Man')
LizzardMan.main_hand = LizzardMenSpear
LizzardMan.off_hand = RustedBucklerShield
LizzardMan.stats = [6, 9, 5, 5]
LizzardMan.level = 22
LizzardMan.generate()

HobGoblin = Enemy(None, 'Hob Goblin')
HobGoblin.main_hand = WoodenClub
HobGoblin.stats = [12, 7, 3, 5]
HobGoblin.level = 25
HobGoblin.generate()

Wyvern = Enemy(None, 'Wyvern')
Wyvern.main_hand = WyvernClaw
Wyvern.stats = [23, 10, 21, 10]
Wyvern.level = 69
Wyvern.generate()

##############
# Encounters #
##############
# Resting Zone
perfectRestingZone = lambda: Rest(0)
goodRestingZone = lambda: Rest(1)
mediumRestingZone = lambda: Rest(2)
badRestingZone = lambda: Rest(3)
mediocreRestingZone = lambda: Rest(4)

# enemy pool
ennemyPoolForest1 = {GreenSlime: 1}

ennemyPoolForest_2_1 = {GreenSlime: 10, Wolf: 1}

ennemyPoolForest_2_2 = {Goblin: 1, Wolf: 1}


###############
# Expeditions #
###############
# The forest
expedition11 = Expedition(3)
expedition11.addEncounter(Combat(genElementArrayFromPool((1, 1), ennemyPoolForest1)))
expedition11.addEncounter(mediumRestingZone())
expedition11.addEncounter(Combat(genElementArrayFromPool((1, 1), ennemyPoolForest1)))
expedition11.reward['loot'].append(TransmutationOrb())

expedition12 = Expedition(4)
expedition12.addEncounter(Combat(genElementArrayFromPool((1, 1), ennemyPoolForest1)))
expedition12.addEncounter(Combat(genElementArrayFromPool((1, 1), ennemyPoolForest1)))
expedition12.addEncounter(mediumRestingZone())
expedition12.addEncounter(Combat(genElementArrayFromPool((1, 2), ennemyPoolForest1)))
expedition12.reward['loot'].append(KartReparationKit())


expedition13 = Expedition(7)
expedition13.addEncounter(Combat(genElementArrayFromPool((1, 3), ennemyPoolForest_2_1)))
expedition13.addEncounter(Combat(genElementArrayFromPool((2, 4), ennemyPoolForest_2_1)))
expedition13.addEncounter(Combat(genElementArrayFromPool((2, 4), ennemyPoolForest_2_1)))
expedition13.addEncounter(badRestingZone())
expedition13.addEncounter(Combat(genElementArrayFromPool((2, 4), ennemyPoolForest_2_1)))
expedition13.addEncounter(Combat(genElementArrayFromPool((3, 5), ennemyPoolForest_2_1)))
expedition13.addEncounter(Combat(genElementArrayFromPool((4, 7), ennemyPoolForest_2_2)))
expedition13.reward['loot'].append(AlterationOrb())
