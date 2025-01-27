from nanachan.rpg_model.character import Hero


class ExplorationKart:
    def __init__(self) -> None:
        self.absolute_max_space = 3
        self.current_max_space = 1
        self.speed = 1
        self.team: list[Hero] = []
        self.exploring = False

    # return 1 if that worked, 0 otherwise
    def repare(self) -> int:
        if self.current_max_space < self.absolute_max_space:
            self.current_max_space += 1
            return 1
        return 0

    def addHeroToTeam(self, hero: Hero) -> int:
        if len(self.team) >= self.current_max_space:
            return 0
        self.team.append(hero)
        return 1

    def resetTeam(self) -> None:
        self.team = []

    @property
    def isDead(self):
        return any(h.isDead for h in self.team)
