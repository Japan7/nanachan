from abc import ABC, abstractmethod
from enum import Enum

import numpy as np

import nanachan.rpg_model.expedition_collection as collection
from nanachan.rpg_model.character import Character, Enemy, Hero
from nanachan.rpg_model.exploration_kart import ExplorationKart
from nanachan.rpg_model.Player import Player


class EncounterStatus(Enum):
    UNRESOLVED = 0
    LOST = 1
    RESOLVED = 2


class Encounter(ABC):
    def __init__(self):
        super().__init__()
        self.status: EncounterStatus = EncounterStatus.UNRESOLVED
        self._reward: dict = {'xp': 0, 'loot': []}
        self.encounterLog: list[str] = []

    @abstractmethod
    def resolve(self, explorationKart: ExplorationKart):
        pass

    @property
    def reward(self):
        return self._reward


class Rest(Encounter):
    QUALITY_MUL = [1, 0.75, 0.5, 0.25, 0.10]

    # quality = int [0,5]
    def __init__(self, quality):
        super().__init__()
        self.quality = quality

    def resolve(self, explorationKart: ExplorationKart):
        log = 'The heroes find a place to rest\n'
        for hero in explorationKart.team:
            amount = hero.maxHPNumber * Rest.QUALITY_MUL[self.quality]

            rest = hero.skillSet.skills[collection.SkillKey.GOOD_REST]
            if rest.have:
                amount += amount * rest.use()

            if not hero.isDead:
                hero.heal(amount)
            log += f'{hero.name} regen {amount} hp\n'
        self.encounterLog.append(log)
        self.status = EncounterStatus.RESOLVED


class Combat(Encounter):
    MAX_TURN = 200

    def __init__(self, eTeam: list[Enemy]):
        super().__init__()
        self.eTeam: list[Enemy] = eTeam
        self.hTeam: list[Hero] = []
        self.turn = 0

    def selectTurnOrder(
        self, heroTeam: list[Character], enemyTeam: list[Character]
    ) -> list[Character]:
        turnOrder: list[Character] = []
        for h in heroTeam:
            if not h.isDead:
                turnOrder.append(h)

        turnOrder.extend(enemyTeam)
        turnOrder.sort(key=lambda x: x.initiativeRoll, reverse=True)
        return turnOrder

    def nextTurn(self, numberOfCharacter: int):
        self.turn = (self.turn + 1) % numberOfCharacter

    def selectOponent(self, team: list[Character]) -> Character:
        # add aggro management here
        id_list: list[int] = []
        for i in range(len(team)):
            if not team[i].isDead:
                id_list.append(i)
        return team[np.random.choice(id_list)]

    def checkIfTeamDefeated(self, team: list[Character]) -> bool:
        res = True
        for c in team:
            res = res and c.isDead
        return res

    def combatFinished(self, turnNumber: int) -> bool:
        return (
            self.checkIfTeamDefeated(self.eTeam)
            or self.checkIfTeamDefeated(self.hTeam)
            or turnNumber > Combat.MAX_TURN
        )

    def resolve(self, kart: ExplorationKart):
        self.hTeam = kart.team
        turnOrder: list[Character] = self.selectTurnOrder(self.hTeam, self.eTeam)
        # print(len(turnOrder))

        log = ''
        log += 'the hero encounter an enemy\n'
        log += f'{turnOrder[self.turn].name} has the initiative\n'
        self.encounterLog.append(log)

        turnNumber = 0
        # combat loop
        while not self.combatFinished(turnNumber):
            turnLog = ''
            turnNumber += 1
            attacker: Character = turnOrder[self.turn]
            defender: Character
            if attacker in self.hTeam:
                defender = self.selectOponent(self.eTeam)
            else:
                defender = self.selectOponent(self.hTeam)

            log = attacker.attack(defender)
            turnLog += log
            turnLog += f'{defender.name} have {defender.hp} hp left\n'

            if defender.isDead:
                turnLog += f'{defender.name} is defeated !\n'
                turnOrder.remove(defender)

            self.nextTurn(len(turnOrder))
            self.encounterLog.append(turnLog)

        if self.checkIfTeamDefeated(self.hTeam):
            self.status = EncounterStatus.LOST
            self.encounterLog.append('The heroes has been defeated\n')
        else:
            self.status = EncounterStatus.RESOLVED
            self.encounterLog.append('The heroes won the fight\n')

    @property
    def reward(self) -> dict:
        res = super().reward
        for e in self.eTeam:
            if e.isDead:
                r = e.reward
                res['xp'] += r['xp']
                res['loot'].extend(r['loot'])
        return res


class Expedition:
    def __init__(self, expeditionLength):
        self.expeditionLength = expeditionLength
        self.encounters: list[Encounter] = []
        self.reward: dict = {'xp': 0, 'loot': []}

    def addEncounter(self, encounter: Encounter):
        if len(self.encounters) == self.expeditionLength:
            pass
        self.encounters.append(encounter)

    def setEncounterList(self, encounters: list[Encounter]):
        self.encounters = encounters

    def launch(self, player: Player, kart: ExplorationKart):
        for h in kart.team:
            h.hp = h.maxHPNumber

        for encounter in self.encounters:
            encounter.resolve(kart)
            if kart.isDead:
                break

    # compute reward here
    def getRewards(self, player: Player, explKart: ExplorationKart) -> dict:
        totalXP = 0
        totalLoot = []
        resolvedEncounter = 0
        for encounter in self.encounters:
            if encounter.status == EncounterStatus.RESOLVED:
                r = encounter.reward
                totalXP += r['xp']
                totalLoot.extend(r['loot'])
                resolvedEncounter += 1

        if resolvedEncounter == self.expeditionLength:
            totalXP += self.reward['xp']
            totalLoot += self.reward['loot']

        teamSize = len(explKart.team)
        for h in explKart.team:
            h.gainXP(totalXP / teamSize)

        for l in totalLoot:
            l.onLoot()
            player.inventory.store(l, 1)

        return {'xp': totalXP, 'loot': totalLoot}
