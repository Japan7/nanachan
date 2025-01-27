import nanachan.rpg_model.expedition_collection as collection
from nanachan.nanapi.model import WaifuSelectResult
from nanachan.rpg_model.character import Hero
from nanachan.rpg_model.equipment import Weapon
from nanachan.rpg_model.exploration_kart import ExplorationKart
from nanachan.rpg_model.Inventory import Inventory


class Player:
    MAX_TEAM_SIZE = 3

    def __init__(self):
        self.heroList: list[Hero] = []
        self.inventory: Inventory = Inventory()
        self.team: list[Hero] = []
        self.explorationKart: list[ExplorationKart] = [ExplorationKart()]

    def addNewHero(self, waifu: WaifuSelectResult, name: str):
        # If the waifu is ascend and not already a hero
        # mark the waifu as Herofied (that it can't be a hero again)
        h = Hero(waifu, name)
        h.setHeroRank()
        self.heroList.append(h)

    def unequipWeaponToHero(self, hero: Hero):
        w = hero.unequipWeapon()
        if w != collection.fist:
            self.inventory.store(w)

    def equipWeaponToHero(self, hero: Hero, weapon: Weapon):
        self.unequipWeaponToHero(hero)
        hero.equipWeapon(weapon)

    def addHeroToExpeditionTeam(self, hero: Hero):
        if len(self.team) == Player.MAX_TEAM_SIZE:
            print('No slot available for this hero remove an hero from the team first')
            return
        else:
            self.team.append(hero)

    def removeHeroFromExpeditionTeam(self, hero: Hero):
        try:
            idx = self.team.index(hero)
            self.team.pop(idx)
        except ValueError:
            print('the hero is not in the player team')
