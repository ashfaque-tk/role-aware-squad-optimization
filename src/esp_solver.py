#implementing the ESP algorithm used in the paper: H. Zhao et al.: Multi-Objective Optimization for Football Team Member Selection
import numpy as np
import numpy as np
import pandas as pd
import json

from typing import Dict, List, Tuple
from pymoo.core.repair import Repair
from pymoo.core.sampling import Sampling
from pymoo.core.problem import ElementwiseProblem, Problem
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.optimize import minimize
from pymoo.operators.sampling.rnd import IntegerRandomSampling
from pymoo.operators.crossover.pntx import TwoPointCrossover
from pymoo.operators.mutation.pm import PolynomialMutation

from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))


def categorize_players_by_roles(player_stats:List[Dict])->Dict:
    """
    Each player can be in different roles if available
    """
    gk_pool = []
    def_pool = []
    mid_pool = []
    fw_pool = []

    for idx,player in enumerate(player_stats):
        global_pos = player['GlobalPos'] #{'GK':'GK'}/{'RW':'FW','CAM':'MF'}
        roles = set(global_pos.values())
        player_with_idx = {**player,'original_idx':idx}
        if 'GK' in roles:
            gk_pool.append(player_with_idx)
        if 'DF' in roles:
            def_pool.append(player_with_idx)
        if 'MF' in roles:
            mid_pool.append(player_with_idx)
        if 'FW' in roles:
            fw_pool.append(player_with_idx)

    return {'GK':gk_pool,'DEF':def_pool,'MF':mid_pool,'FW':fw_pool}


class SalaryAwareSampling(Sampling):

    def _do(self,problem,n_samples,**kwargs):
        # x = np.zeros((n_samples,problem.n_var),dtype=int)

        x = []
        for i in range(n_samples):

            gk  = np.random.randint(len(problem.gk_players))
         
            outfield = np.random.choice(len(problem.outfield_players),size=10,replace=False)
            # print(type(outfield),outfield.tolist())
            
            x.append([gk] + outfield.tolist())
     
        return np.array(x)


class DuplicateRepair(Repair):
    """First converts floats to integers, then removes duplicates"""
    
    def _do(self, problem, X, **kwargs):
        # Round to integers
        X = np.round(X).astype(int)
        
        # Clip to bounds
        X[:, 0] = np.clip(X[:, 0], 0, len(problem.gk_players) - 1)
        X[:, 1:] = np.clip(X[:, 1:], 0, len(problem.outfield_players) - 1)
        
        # Remove duplicates
        for i in range(len(X)):
            outfield_indices = X[i, 1:]
            
            # Find duplicates
            seen = {}
            for j, idx in enumerate(outfield_indices):
                if idx in seen:
                    # Duplicate found! Replace with unused player
                    used = set(outfield_indices)
                    unused = set(range(len(problem.outfield_players))) - used
                    
                    if unused:
                        X[i, j+1] = unused.pop()
                else:
                    seen[idx] = True
        
        return X.astype(int)
    
class RoleAwareDuplicateRepair(Repair):

    def _do(self, problem, X, **kwargs):
        X = np.round(X).astype(int) # convert floats to int

        self.formation = problem.formation
        self.player_pool = problem.players_by_pos

        for i in range(len(X)):
            #clip to bounds
            idx = 0
            for pos in ['GK','DEF','MF','FW']:
                for j in range(self.formation[pos]):
                    X[i,idx] = np.clip(X[i,idx],0,len(self.player_pool[pos])-1)
                    idx+=1
            # remove duplicates within each role
            self._remove_duplicates_within_role(X[i],problem)
        
        return X

    def _remove_duplicates_within_role(self,genome:np.array,problem:Problem)->None:
        
        idx = 1
        print(f'original genome: {genome}')
        count = 0
        for pos in ['DEF','MF','FW']:
            end_idx = self.formation[pos]
            pos_indices = genome[idx:idx+end_idx]
            pos_unique = set(pos_indices)

            if len(pos_unique) < len(pos_indices):
                self._fix_duplicate_in_range(pos_indices,len(self.player_pool[pos]))

            genome[idx:idx+end_idx] = pos_indices
            idx+= end_idx
        
        DF = genome[1:self.formation['DEF']+1]
        MF = genome[self.formation['DEF']+1:self.formation['MF']+self.formation['DEF']+1]
        FW = genome[self.formation['MF']+1:self.formation['MF']+self.formation['FW']+1]

        # assert the formation is strictly enforced
        assert len(DF) == self.formation['DEF'],f'Defenders allowed {self.formation["DEF"]}\nnow: {len(DF)}'
        assert len(MF) == self.formation['MF'],f'Defenders allowed {self.formation["FF"]}'
        assert len(FW) == self.formation['FW'],f'Defenders allowed {self.formation["FW"]}'

        
    def _fix_duplicate_in_range(self,indices:List,pool_size:int)->None:

        seen = set()
        available = set(range(pool_size))

        for i in range(len(indices)):
            if indices[i] in seen:
                unused = list(available-seen)
                if unused:
                    indices[i] = np.random.choice(unused)
                
            seen.add(int(indices[i]))
            available.discard(int(indices[i]))


class SquadOptimizatoinProblem(ElementwiseProblem):

    def __init__(self,player_info:Dict,budget:float,team_size:int=11,formation:Dict={'DEF':4,'MF':3,'FW':3,'GK':1}):
        """
        Docstring for __init__
        
        :param player_info: player info as dictionary, each row corresponds to a single player
        :type player_info: Dict
        :param player_number: number of players in the team (11 1GK+10players)
        """
        self.players_by_pos = categorize_players_by_roles(player_info)
        self.formation  = formation
        self.budget = budget
        self.team_size = team_size

        # build genome bounds
        xl = []
        xu  = []

        for pos in ['GK','DEF','MF','FW']:
            for _ in range(self.formation[pos]):
                xl.append(0)
                xu.append(len(self.players_by_pos[pos])-1)
        
        assert len(xl) == len(xu) == 11, 'Bounds must match chromosome length (11)'

        super().__init__(n_var = team_size ,
                         n_obj=5,
                         n_ieq_constr=1,
                         xl= np.array(xl),
                         xu= np.array(xu))

    def _evaluate(self, x, out, *args, **kwargs):
        # return super()._evaluate(x, out, *args, **kwargs)
        idx = 0 
        gk = self.players_by_pos['GK'][int(x[idx])]
        idx+=1
        players = {'DEF':[],'MF':[],'FW':[]}

        for pos in ['DEF','MF','FW']:
            for _ in range(self.formation[pos]):
                players[pos].append(self.players_by_pos[pos][int(x[idx])])
                idx+=1
        assert idx == len(x),'Final index after looping should be genome length(11)'

        # selected_gk = self.gk_players[int(x[0])]
        # selected_outfield = [self.outfield_players[int(x[i])] for i in range(1, 11)]

        team = [gk] + players['DEF']+players['MF']+players['FW']

        # actual_player_ids = [p['original_idx'] for p in team]

        total_cost = sum(p['WageEUR'] for p in team)

        # objective functions
        out['F'] = [-sum(p['Overall'] for p in team),
                    -sum(p['Potential'] for p in team),
                    -sum(p['attack_score'] for p in team[1:]),
                    
                    -sum(p['defense_score'] for p in team[1:]),
                    -team[0]['gk_score']]

        out['G'] = [total_cost - self.budget]



if __name__ == '__main__':

    print(f'{BASE_DIR}')
    player_data_file = BASE_DIR /"data"/"final_squad_cleaned.json"

    with open(player_data_file, "r") as f:
        player_squad = json.load(f) 

    budget = 1_000_000
    
    #define the problem
    problem = SquadOptimizatoinProblem(player_squad,budget=budget)

    # configure the algorithm
    algorithm = NSGA2(pop_size=100,
                      sampling= IntegerRandomSampling(),
                      crossover=TwoPointCrossover(prob=0.9),
                      mutation =PolynomialMutation(eta=30,prob=1/11),
                      repair = RoleAwareDuplicateRepair(),
                      eliminate_duplicates=True)

    # run optimization
    result = minimize(  problem,
                        algorithm,
                        ('n_gen', 200),
                        seed=1,
                        verbose=True
                        )
    
    # 4. Extract results
    print("Number of solutions:", len(result.F))
    print("\nBest teams (Pareto front):")
    for i in range(len(result.X)):
        genome = result.X[i]
        objectives = result.F[i]

        unique = set(genome[1:])
        if len(unique)<10:
            print(f'solution {i} contains duplicate players')
        
        # Decode genome to actual team
        idx=1
        gk = problem.players_by_pos['GK'][int(genome[0])]
        outfield_players = []
        for pos in ['DEF','MF','FW']:
            for _ in range(problem.formation[pos]):
                outfield_players.append(problem.players_by_pos[pos][int(genome[idx])])
                idx+=1


        team = [gk] + outfield_players

        
        print(f"\nTeam {i+1}:")
        print(f"  Overall: {-objectives[0]:.1f}")
        print(f"  Potential: {-objectives[1]:.1f}")
        print(f"  Attack: {-objectives[2]:.1f}")
        print(f"  Defense: {-objectives[3]:.1f}")
        print(f"  GK: {-objectives[4]:.1f}")
        # print(f"  Players: {[p['Name'] for p in team]}")
        rows = []
        print(genome)
        for p in team:
            rows.append({
                "Name": p["Name"],
                "Position": p["GlobalPos"],
                "Overall": p["Overall"]
            })

        df = pd.DataFrame(rows)
        print(df)

        if i ==2:
            break


