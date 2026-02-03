import pulp as pl 
from typing import Dict, List,Tuple
import sys
from pathlib import Path
# import pandas as pd
import json 
BASE_DIR = Path(__file__).resolve().parents[1]

sys.path.append(str(BASE_DIR))

class SquadMILPSolver:
    def __init__(
        self,
        player_info: List[Dict],
        formation: Tuple[int, int, int],  # (DF, MF, FW)
        age : Tuple,#(min,max)
        total_budget: int,
        playing_style : str,
        locked_players:Dict,
        total_players: int = 11,
        role_aware: bool = True):

        self.players = player_info
        self.players_pre_selected = locked_players
        self.avg_age = age
        self.formation = formation
        self.total_players = total_players
        self.role_aware = role_aware
        self.budget = total_budget
        self.model = pl.LpProblem("Squad_Optimization", pl.LpMaximize)
        self.x = {}
        self.style = playing_style
        self.locked_players = locked_players

        # self.playting_styles = {''}
    def _get_formation_constraints(self,formation,style):
        formation_styles=  {( (4,3,3), 'attack'): {
                            'CAM': (1, 2),  # (min, max)
                            'CM':  (0, 2),
                            'CDM': (0, 1),
                            'LW':  (0, 1),
                            'RW':  (0, 1),
                            'ST':  (0, 1),
                            'CF': (0,1),
                            'CB':  (2, 2),
                            'LB':  (1, 1),
                            'RB':  (1, 1),
                            'LM': (0,1),
                            'RM': (0,1)
                            
                                                },
                            ((4,3,3), 'defend'): {
                            'CAM': (0, 1),  # (min, max)
                            'CM':  (1, 2),
                            'CDM': (1, 2),
                            'LW':  (0, 1),
                            'RW':  (0, 1),
                            'ST':  (1, 1),
                            'CF': (0,1),
                            'CB':  (2, 2),
                            'LB':  (1, 1),
                            'RB':  (1, 1),
                            'LM' : (0,1),
                            'RM' :(0,1)  
                            }
                            }      

        style_weights = {'attack':[1,0.8,0.4],'defend':[0.6,0.7,1]}         

        return formation_styles[(formation,style)],style_weights[style]                             
        
    def build_variables(self):
        if not self.role_aware:
            # x[player] ∈ {0,1}
            self.x = {p["Name"]: pl.LpVariable(f"x_{p['Name']}", cat="Binary")
                for p in self.players}
        else:
            # x[player, role] ∈ {0,1}
            self.x = {(p["Name"], r): pl.LpVariable(f"x_{p['Name']}_{r}", cat="Binary")
                for p in self.players
                for r in p["PossiblePositions"]}

    def build_objective(self):
        if not self.role_aware:
            self.model += pl.lpSum(p["Overall"] * self.x[p["Name"]] for p in self.players)
        else:
            self.model += pl.lpSum(p["rating_per_roles"][r] * self.x[(p["Name"], r)]
                for p in self.players
                for r in p["PossiblePositions"])
            # giving a  weight depending on the style of play
            # formation= self.formation[:3]
            # _,[w_attack,w_mid,w_def] = self._get_formation_constraints(formation,style=self.style)

            # self.model+= pl.lpSum()

    def build_constraints(self):
        DF, MF, FW ,GK = self.formation

        if self.locked_players:
            for key,values in self.locked_players.items():
                self.model+=(self.x[(key,values['role'])])==1
            # for name,role in self.locked_players.items():
            #     self.model+= ( self.x[(name,role)]) == 1

        if not self.role_aware:
            # total players
            self.model += pl.lpSum(self.x[p["Name"]] for p in self.players) == self.total_players
            # formation
            self.model += pl.lpSum(self.x[p["Name"]] for p in self.players if "DF" in p["GlobalPos"]) == DF
            self.model += pl.lpSum(self.x[p["Name"]] for p in self.players if "MF" in p["GlobalPos"]) == MF
            self.model += pl.lpSum(self.x[p["Name"]] for p in self.players if "FW" in p["GlobalPos"]) == FW

        else:
            # total players
            self.model += pl.lpSum(self.x.values()) == self.total_players
            # each player at most one role
            for p in self.players:
                self.model += pl.lpSum(self.x[(p["Name"], r)] for r in p["PossiblePositions"]) <= 1
                # self.model+= pl.lpSum(self.x[(p['Name'],r )] for r in p['PossiblePostions'])
            formation= self.formation[:3]
            formation_constraints,_ = self._get_formation_constraints(formation,self.style)

            for position,limits in formation_constraints.items():
                self.model+=pl.lpSum(self.x[(p['Name'],position)] for p in self.players if position in p['PossiblePositions'])>=limits[0]
                self.model+=pl.lpSum(self.x[(p['Name'],position)] for p in self.players if position in p['PossiblePositions'])<=limits[1]
            
            #formation
            for gb_role,required in zip(['DF','MF','FW' , 'GK'], self.formation):
                role_sum = []
                for p in self.players:
                    for r in p['PossiblePositions']:
                        if p['GlobalPos'][r]==gb_role:
                            role_sum.append(self.x[(p['Name'],r)])
                self.model += (pl.lpSum(role_sum)==required)
            # budget 
            self.model+=pl.lpSum(self.x[(p['Name'],r)]*p['WageEUR'] for p in self.players for r in p['PossiblePositions'])<=self.budget
            # # average age
            if self.avg_age is not None:
                # print(self.avg_age)
                for p in self.players:
                    if p['Name'] not in self.locked_players.keys():
                        for r in p['PossiblePositions']:
                            self.model+= pl.lpSum(self.x[(p['Name'],r)]*p['Age'])>=self.avg_age[0]*pl.lpSum(self.x[(p['Name'],r)])
                            self.model+= pl.lpSum(self.x[(p['Name'],r)]*p['Age'])<=self.avg_age[1]*pl.lpSum(self.x[(p['Name'],r)])
                # self.model += (pl.lpSum(self.x[(p['Name'],r)]*p['Age'] for p in self.players for r in p['PossiblePositions'] if p['Name'] not in self.locked_players.keys())) <= self.avg_age * pl.lpSum(self.x[(p['Name'], r)] 
                # for p in self.players for r in p['PossiblePositions'] if p['Name'] not in self.locked_players.keys()  )


    def solve(self):
        self.build_variables()
        self.build_objective()
        self.build_constraints()
        self.model.solve()
        return self.extract_solution()

    def extract_solution(self):

        status = pl.LpStatus[self.model.status]

        if status != 'Optimal':
            return {"status":status,'feasible':False
                    }
        else:
            selected = []
            if not self.role_aware:
                for p in self.players:
                    if self.x[p["Name"]].value() == 1:
                        selected.append({"Name": p["Name"],
                            "roles": p["GlobalPos"],
                            "score": p["Overall"]})
            else: 
                for (name, role), var in self.x.items():
                    if var.value() == 1:
                            selected.append({"Name": name,                
                                "role": role
                                })

            # calculating the budget and average age of selected players
            budget = 0 
            age = 0

            for player_info in selected:  # Only 11 players
                # Find the full player data
                p = next(p for p in self.players if p['Name'] == player_info['Name'])
                player_info['Rating'] = p['Overall']
                player_info['WageEur'] = p['WageEUR']
                budget += p['WageEUR']
                age += p['Age']
            avg_age = age/len(selected)
            
            return {"status": pl.LpStatus[self.model.status],
                "objective": pl.value(self.model.objective),
                "selected_players": selected,
                'total_budget':budget,
                'average age': avg_age }


def optimize_squad(budget,formation,style,age,locked_players):

    player_data_file = BASE_DIR /"data"/"final_squad_cleaned.json"

    with open(player_data_file, "r") as f:
        player_squad = json.load(f)    
    sqsolve = SquadMILPSolver(player_squad,formation=formation,total_players=11,total_budget=budget,playing_style=style,age=age,locked_players=locked_players)
    results = sqsolve.solve()
    return results