import pulp as pl 
from typing import Dict, List,Tuple


class SquadMILPSolver:
    def __init__(
        self,
        player_info: List[Dict],
        formation: Tuple[int, int, int],  # (DF, MF, FW)
        total_players: int,
        role_aware: bool = False):

        self.players = player_info
        self.formation = formation
        self.total_players = total_players
        self.role_aware = role_aware

        self.model = pl.LpProblem("Squad_Optimization", pl.LpMaximize)
        self.x = {}
        self.global_roles = {  "CB": "DF", "FB": "DF",
                            "DM": "MF", "CM": "MF", "AM": "MF",
                            "CF": "FW", "ST": "FW", "WM": "FW"
                        }
    def build_variables(self):
        if not self.role_aware:
            # x[player] ∈ {0,1}
            self.x = {p["name"]: pl.LpVariable(f"x_{p['name']}", cat="Binary")
                for p in self.players}
        else:
            # x[player, role] ∈ {0,1}
            self.x = {(p["name"], r): pl.LpVariable(f"x_{p['name']}_{r}", cat="Binary")
                for p in self.players
                for r in p["roles"]}

    def build_objective(self):
        if not self.role_aware:
            self.model += pl.lpSum(p["score"] * self.x[p["name"]] for p in self.players)
        else:
            self.model += pl.lpSum(p["score"][r] * self.x[(p["name"], r)]
                for p in self.players
                for r in p["roles"])

    def build_constraints(self):
        DF, MF, FW = self.formation

        if not self.role_aware:
            # total players
            self.model += pl.lpSum(self.x[p["name"]] for p in self.players) == self.total_players
            # formation
            self.model += pl.lpSum(self.x[p["name"]] for p in self.players if "DF" in p["roles"]) == DF
            self.model += pl.lpSum(self.x[p["name"]] for p in self.players if "MF" in p["roles"]) == MF
            self.model += pl.lpSum(self.x[p["name"]] for p in self.players if "FW" in p["roles"]) == FW

        else:
            # total players
            self.model += pl.lpSum(self.x.values()) == self.total_players
            # each player at most one role
            for p in self.players:
                self.model += pl.lpSum(self.x[(p["name"], r)] for r in p["roles"]) <= 1
            # formation by role
            # self.model += pl.lpSum(self.x[(p["name"], "DF")] for p in self.players if "DF" in p["roles"]) == DF
            # self.model += pl.lpSum(self.x[(p["name"], "MF")] for p in self.players if "MF" in p["roles"]) == MF
            # self.model += pl.lpSum(self.x[(p["name"], "FW")] for p in self.players if "FW" in p["roles"]) == FW
            for gb_role,required in zip(['DF','MF','FW'], self.formation):
                role_sum = []
                for p in self.players:
                    for r in p['roles']:
                        if self.global_roles[r]==gb_role:
                            role_sum.append(self.x[(p['name'],r)])
                self.model += (pl.lpSum(role_sum)==required)

    def solve(self):
        self.build_variables()
        self.build_objective()
        self.build_constraints()
        self.model.solve()
        return self.extract_solution()

    def extract_solution(self):
        selected = []
        if not self.role_aware:
            for p in self.players:
                if self.x[p["name"]].value() == 1:
                    selected.append({"name": p["name"],
                        "roles": p["roles"],
                        "score": p["score"]})
        else:
    
            for (name, role), var in self.x.items():
                if var.value() == 1:
                    selected.append({"name": name,
                                     
                        "role": role})
                    
        return {"status": pl.LpStatus[self.model.status],
            "objective": pl.value(self.model.objective),
            "selected_players": selected }
