import copy
from enum import Enum

import numpy as np


def rollInArrayWithRate(randomNumber: float, rollRateArray: list[float]) -> int:
    acc = 0.0
    for i in range(len(rollRateArray)):
        acc += rollRateArray[i]
        if randomNumber <= acc:
            return i
    return len(rollRateArray) - 1


def normalizeArray(array: list[float]) -> list[float]:
    total = 0.0
    res = array
    for i in range(len(array)):
        total += array[i]

    for i in range(len(array)):
        res[i] = array[i] / total

    return res


def genElementArrayFromPool(numberToGen: tuple, elemPool: dict) -> list:
    elem = []
    proba = []
    for e in elemPool:
        elem.append(e)
        proba.append(elemPool[e])

    proba = normalizeArray(proba)
    resultArray = []
    gen = np.random.default_rng()
    numElem = gen.integers(*numberToGen, endpoint=True)
    for _ in range(numElem):
        id = rollInArrayWithRate(np.random.uniform(0, 1), proba)
        resultArray.append(copy.deepcopy(elem[id]))

    return resultArray


def genElementArrayFromPool2(numberToGen: tuple, elemPool: list) -> list:
    elem = []
    proba = []
    for e in elemPool:
        elem.append(e[0])
        proba.append(e[1])

    proba = normalizeArray(proba)
    resultArray = []
    gen = np.random.default_rng()
    numElem = gen.integers(*numberToGen, endpoint=True)
    for _ in range(numElem):
        id = rollInArrayWithRate(np.random.uniform(0, 1), proba)
        elementPicked = elem[id]
        if elementPicked is not None:
            resultArray.append(copy.deepcopy(elementPicked))

    return resultArray


#########
# enums #
#########
class Stats(Enum):
    STR = 0
    DEX = 1
    INT = 2
    LUK = 3


class DamageType(Enum):
    BLUNT = 0
    SLASH = 1
    PIERCING = 2
    MAGICAL = 3


class AttackStatus(Enum):
    TAKEN = 0
    BLOCKED = 1
    DODGED = 2
