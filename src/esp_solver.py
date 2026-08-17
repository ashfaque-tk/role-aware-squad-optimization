#implementing the ESP algorithm used in the paper: H. Zhao et al.: Multi-Objective Optimization for Football Team Member Selection
import numpy as np
import numpy as np
import pandas as pd
import json
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))

from typing import Dict, List, Tuple

from src.formations import FORMATIONS_SPEC, MICRO_TO_SUBROLE, GLOBAL_ROLE_MAPING

from pymoo.core.repair import Repair
from pymoo.core.sampling import Sampling
from pymoo.core.problem import ElementwiseProblem, Problem
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.optimize import minimize
from pymoo.operators.sampling.rnd import IntegerRandomSampling
from pymoo.operators.crossover.pntx import TwoPointCrossover
from pymoo.operators.mutation.pm import PolynomialMutation




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

    return {'GK':gk_pool,'DF':def_pool,'MF':mid_pool,'FW':fw_pool}


def categorize_players_by_subroles(player_stats: List[Dict]) -> Dict:
    pools = {
        'DF': {'LB_LWB': [], 'CB': [], 'RB_RWB': []},
        'MF':  {'CM_CAM': [], 'CDM': [], 'LM': [], 'RM': []},
        'FW':  {'LW': [], 'RW': [], 'ST_CF': []}
    }

    for idx, p in enumerate(player_stats):
        p = {**p, 'original_idx': idx}

        for role in p['PossiblePositions']:
            if role in MICRO_TO_SUBROLE:
                sub = MICRO_TO_SUBROLE[role]
                # print(sub)
                global_pos = p['GlobalPos'].get(role)

                if global_pos in pools:
                    pools[global_pos][sub].append(p)
    return pools




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
            for pos in ['GK','DF','MF','FW']:
                for j in range(self.formation[pos]):
                    X[i,idx] = np.clip(X[i,idx],0,len(self.player_pool[pos])-1)
                    idx+=1
            # remove duplicates within each role
            self._remove_duplicates_within_role(X[i],problem)
        
        return X

    def _remove_duplicates_within_role(self,genome:np.array,problem:Problem)->None:
        
        idx = 1
        # print(f'original genome: {genome}')
        count = 0
        for pos in ['DF','MF','FW']:
            end_idx = self.formation[pos]
            pos_indices = genome[idx:idx+end_idx]
            pos_unique = set(pos_indices)

            if len(pos_unique) < len(pos_indices):
                self._fix_duplicate_in_range(pos_indices,len(self.player_pool[pos]))

            genome[idx:idx+end_idx] = pos_indices
            idx+= end_idx
        
        DF = genome[1:self.formation['DF']+1]
        MF = genome[self.formation['DF']+1:self.formation['MF']+self.formation['DF']+1]
        FW = genome[self.formation['MF']+1:self.formation['MF']+self.formation['FW']+1]

        # assert the formation is strictly enforced
        assert len(DF) == self.formation['DF'],f'Defenders allowed {self.formation["DEF"]}\nnow: {len(DF)}'
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


class MicroRoleAwareDuplicateRepair(Repair):
    def _do(self, problem, X, **kwargs):
        # print(f" REPAIR called with X.shape = {X.shape}")  # ← ADD THIS
        X = np.round(X).astype(int)

        self.formation = problem.formation
        self.player_pool_global = problem.players_by_pos
        self.player_pool_micro = problem.players_by_subroles
        self.solutions_counter = 0
        self.id_to_relative_idx = {
                                    'DF': {int(p['original_idx']): i for i, p in enumerate(self.player_pool_global['DF'])},
                                    'MF': {int(p['original_idx']): i for i, p in enumerate(self.player_pool_global['MF'])},
                                    'FW': {int(p['original_idx']): i for i, p in enumerate(self.player_pool_global['FW'])}
                                }

        
        # X = np.array([[ 738 ,2395 ,3363 ,1684, 3676, 2193, 4356, 4199,  951,  370, 2091],[7,  102,  976,   38, 3381 , 656 , 155 , 606,  675,  579,  606],
        #                   [ 424, 3233, 3220,  500, 1218,  443, 2422, 3720,  589, 1188, 1512]])
        for i in range(len(X)):
            #clip to bounds
            self.roles_assigned = []
            # print(f"  Repairing solution {i}, genome[0:3] = {X[i]}")  # ← ADD THIS
            idx = 0
            self.roles_assigned =  ['GK']

            for pos in ['GK','DF','MF','FW']:
                for j in range(self.formation[pos]):
                    X[i,idx] = np.clip(X[i,idx],0,len(self.player_pool_global[pos])-1)
                    idx+=1
            
            # remove duplicates within each role
            self._remove_duplicates_within_role(X[i],problem)
            # make the genome a new key and populate roles to it
            final_genome = X[i]
            genome_key = tuple(final_genome)
            problem.assigned_roles[genome_key] = self.roles_assigned
            

        return X
    
    def _remove_duplicates_within_role(self,genome:np.array,problem:Problem)->None:

        idx = 1
        
        for pos in ['DF','MF','FW']:
            end_idx = self.formation[pos]
            pos_indices = genome[idx:idx+end_idx]
            # fix the formation constraint without duplicates
            self._fix_duplicate_in_range(pos_indices,len(self.player_pool_global[pos]))
            # fix the micro role constraint without duplicates
            self._fix_micro_roles(pos,pos_indices)
            genome[idx:idx+end_idx] = pos_indices
            idx+= end_idx
        
        DF = genome[1:self.formation['DF']+1]
        MF = genome[self.formation['DF']+1:self.formation['MF']+self.formation['DF']+1]
        FW = genome[self.formation['MF']+1:self.formation['MF']+self.formation['FW']+1]

        # assert the formation is strictly enforced
        assert len(DF) == self.formation['DF'],f'Defenders allowed {self.formation["DEF"]}\nnow: {len(DF)}'
        assert len(MF) == self.formation['MF'],f'Mid allowed {self.formation["FF"]}'
        assert len(FW) == self.formation['FW'],f'Forward allowed {self.formation["FW"]}'
        # print('no problem: quiting')
        # quit()
     
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
       

    def _fix_micro_roles(self, global_role: str, indices: List) -> None:

        og_length = len(indices)
        players_global = self.player_pool_global[global_role]
        role_limits = FORMATIONS_SPEC[(4,3,3)]
        subrole_limits = {r: v for r, v in role_limits.items() if r in GLOBAL_ROLE_MAPING[global_role]}
  
        # Fill everyone currently in the indices by their subrole
        current_players_by_role:Dict[str,Tuple[int,str]] = {r: [] for r in subrole_limits}

        for idx in indices:
            p = players_global[idx]
            playable = [MICRO_TO_SUBROLE[pos] for pos in p['PossiblePositions'] 
                        if pos in MICRO_TO_SUBROLE and MICRO_TO_SUBROLE[pos] in subrole_limits]
           
            role_pool = np.random.choice(playable) if playable else list(subrole_limits.keys())[0]
            assigned_role  = np.random.choice([role for role in p['PossiblePositions'] if role in role_pool])
            current_players_by_role[role_pool].append((idx,assigned_role)) # for RB_RWB- RB/RWB was chosen or not
            
        # 2. START THE REBUILD
        new_squad = []
        
        new_squad_role = {r:[] for r in subrole_limits}  
        # Priority A: Satisfy all MINIMUMS first
        for r, (mini, maxi) in subrole_limits.items():
            # Take existing players first to satisfy min
            while len(current_players_by_role[r]) > 0 and mini > 0:

                id,role = current_players_by_role[r].pop(0)
           
                new_squad.append(id)
                mini -= 1
                new_squad_role[r].append((id,role))
 
            # If still under min, pull NEW players from the pool
            if mini > 0:
                candidates = [p['original_idx'] for p in self.player_pool_micro[global_role][r] 
                            if p['original_idx'] not in new_squad]
                for _ in range(mini):
                    if candidates:
             
                        new_p = np.random.choice(candidates)
                        relative_new_p = self.id_to_relative_idx[global_role][new_p]
                        candidate_role = np.random.choice([role for role in self.player_pool_global[global_role][relative_new_p]['PossiblePositions'] if role in r])
          
                 
                        new_squad.append(relative_new_p)
                        candidates.remove(new_p)
                        new_squad_role[r].append((relative_new_p,candidate_role))

        # Fill remaining slots until we hit og_length
        # Flatten all remaining original players who weren't used for "Min"
        remaining_pool = [idx for sublist in current_players_by_role.values() for idx in sublist]
        
        # print('remaining pool',remaining_pool)
        # print("current squad : ",new_squad_role)
   
        while len(new_squad) < og_length:
            if remaining_pool:
                # Check if adding this player would break a MAX condition
                candidate_idx,candidate_role = remaining_pool.pop()   
                new_squad_role[MICRO_TO_SUBROLE[candidate_role]].append((candidate_idx,candidate_role))
                # # new_squad_rol
                new_squad.append(candidate_idx)

                # new_squad_role[r].append((candidate_idx,role))
            else:
                # If we run out of original players, grab any valid player from the global group
                # that fits a role that hasn't hit MAX yet       
                break

        if len(new_squad) > og_length:
            new_squad = new_squad[:og_length]
        # FINAL WRITEBACK
        indices[:] = np.array(new_squad)

        player_to_role = {}
        for role, player_list in new_squad_role.items():
            for player_idx, assigned_role in player_list:
                player_to_role[player_idx] = assigned_role
        # assigning to the player positions
        for player_idx in new_squad:
            role = player_to_role[player_idx]
            self.roles_assigned.append(role)
            try:
                player = self.player_pool_global[global_role][player_idx]
                roles = player['rating_per_roles']
                rating = roles[role]
                
            except:
                    print('id:', player_idx, 'name:', player['Name'], 'rating:', roles, 'assigned:', role)
                    print("ERROR: assigned role not in rating_per_roles!")

      
class SquadOptimizatoinProblem(ElementwiseProblem):

    def __init__(self,player_info:Dict,budget:float,min_age:int=16,max_age:int=41,team_size:int=11,formation:Dict={'DF':4,'MF':3,'FW':3,'GK':1}):
        """
        Docstring for __init__
        
        :param player_info: player info as dictionary, each row corresponds to a single player
        :type player_info: Dict
        :param player_number: number of players in the team (11 1GK+10players)
        """
        self.players_by_pos = categorize_players_by_roles(player_info)
        self.players_by_subroles = categorize_players_by_subroles(player_info)

        # for storing the selected team and their chosen role
        self.assigned_roles = {}

        self.formation  = formation
        self.budget = budget
        self.team_size = team_size
        self.age_range = (min_age,max_age)

        # build genome bounds
        xl = []
        xu  = []

        for pos in ['GK','DF','MF','FW']:
            for _ in range(self.formation[pos]):
                xl.append(0)
                xu.append(len(self.players_by_pos[pos])-1)
        
        assert len(xl) == len(xu) == 11, 'Bounds must match chromosome length (11)'

        super().__init__(n_var = team_size ,
                         n_obj=3,
                         n_ieq_constr = 3,
                         xl= np.array(xl),
                         xu= np.array(xu))

    def _evaluate(self, x, out, *args, **kwargs):
        # return super()._evaluate(x, out, *args, **kwargs)
        # print(f"EVALUATE called with x[0:3] = {x}")  # 

        genome_key = tuple(x)
        roles_assigned = self.assigned_roles[genome_key]
        # print(roles_assigned)
        idx = 0 
        gk = self.players_by_pos['GK'][int(x[idx])]
        idx+=1
        players = {'DF':[],'MF':[],'FW':[]}

        gk_rating = gk['rating_per_roles']['GK']
        players_role_rating =  [gk_rating]

        for pos in ['DF','MF','FW']:
            for _ in range(self.formation[pos]):
                p = self.players_by_pos[pos][int(x[idx])]
                
                name = p['Name']      
                # retrieve the role rating
                role_given = roles_assigned[idx]
                rating_available = p['rating_per_roles']
                try:
                    role_rating = p['rating_per_roles'][role_given]
                    players[pos].append(p)
                    players_role_rating.append(role_rating)
                    # print('genome_idx:\t', idx,'player_idx: ',x[idx],'\t name:', name, '\t possible_roles: ',rating_available,'\t role_rating: ',role_rating,'assigned\t:',role_given)
                except:
                    print('genome: ',x)
                    print('genome_idx:\t',idx,'player_idx: ',x[idx],'\t name:', name, '\t role_rating: ',role_rating,'available_roles:\t',rating_available,'\t assigned role: ', roles_assigned[idx])
                    quit()
               
                idx+=1


        assert idx == len(x),'Final index after looping should be genome length(11)'
        # selected_gk = self.gk_players[int(x[0])]
        # selected_outfield = [self.outfield_players[int(x[i])] for i in range(1, 11)]
        team = [gk] + players['DF']+players['MF']+players['FW']
        # actual_player_ids = [p['original_idx'] for p in team]
        total_cost = sum(p['WageEUR'] for p in team)
        avg_age = np.mean([p['Age'] for p in team])
        # # objective functions
        # out['F'] = [-sum(players_role_rating),]


        out['F'] = [-sum(players_role_rating),
                    # -sum(p['Potential'] for p in team),
                    -sum(p['attack_score'] for p in team[1:]),
                    
                    -sum(p['defense_score'] for p in team[1:])]
                    # -team[0]['gk_score']]

        out['G'] = [total_cost - self.budget, self.age_range[0]-avg_age,avg_age-self.age_range[1]]



if __name__ == '__main__':

    print(f'{BASE_DIR}')
    player_data_file = BASE_DIR /"data"/"final_squad_cleaned.json"

    with open(player_data_file, "r") as f:
        player_squad = json.load(f) 

    budget = 1_000_000
    
    #define the problem
    problem = SquadOptimizatoinProblem(player_squad,budget=budget)

    # configure the algorithm
    algorithm = NSGA2(pop_size=200,
                      sampling= IntegerRandomSampling(),
                      crossover=TwoPointCrossover(prob=0.9),
                      mutation =PolynomialMutation(eta=30,prob=1/11),
                      repair = MicroRoleAwareDuplicateRepair(),
                      eliminate_duplicates=True)

    # run optimization
    result = minimize(  problem,
                        algorithm,
                        ('n_gen', 200),
                        seed=1,
                        verbose=True
                        )
    if result.X.ndim == 1:
        result.X = result.X[np.newaxis, :]
    
    # print('length of results ', result.X)
    # # 4. Extract results
    print("Number of solutions:", len(result.F))
    print("\nBest teams (Pareto front):")


    obj_score = []
    budget_used = []
    for i in range(len(result.X)):
        genome = result.X[i]
        # quit()
        objectives = result.F[i]
        # print(genome)
        unique = set(genome[1:])
        if len(unique)<10:
            print(f'solution {i} contains duplicate players')
        
        # Decode genome to actual team
        idx=1
        gk = problem.players_by_pos['GK'][int(genome[0])]
        outfield_players = []
        outfield_players_role = []

        roles_genome = problem.assigned_roles[tuple(genome)]

        # print(problem.assigned_roles[tuple(genome)])
        # quit()
        print(roles_genome)
        print(genome)

        for pos in ['DF','MF','FW']:
            for _ in range(problem.formation[pos]):
                outfield_players.append(problem.players_by_pos[pos][int(genome[idx])])
                try:
                    outfield_players_role.append(roles_genome[idx])
                except:
                    print(idx,genome[idx],roles_genome)
                    quit()
                idx+=1

        team = [gk] + outfield_players
        team_role = ['GK']+outfield_players_role
        # team selected        
        print(f"\nTeam {i+1}:")
        # print(f" Total rating: {-objectives[0]:.1f}")
        # print(f"  Overall: {-objectives[1]:.1f}")
        # # print(f"  Potential: {-objectives[2]:.1f}")
        # print(f"  Attack: {-objectives[2]:.1f}")
        # print(f"  Defense: {-objectives[3]:.1f}")
        # print(f"  GK: {-objectives[4]:.1f}")
        # print(f"  Players: {[p['Name'] for p in team]}")
        rows = []
        print(genome)
        for idx,p in enumerate(team):
            rows.append({
                "Name": p["Name"],
                "Position": p["GlobalPos"],
                "Overall": p["Overall"],
                'Assigned role':team_role[idx],
                'Wage' : p['WageEUR'],
                
            })
      
        df = pd.DataFrame(rows)
        print(df)
        print(f"Total cost of the team: ",sum(df['Wage']))

        # print(objectives)

        # obj_score.append(objectives)
        budget_used.append(sum(df['Wage']))
        obj_score.append(-sum(df['Overall']))
        # if i ==2:
        #     break

    import matplotlib.pyplot as plt 
    print(budget_used,obj_score)
    
    plt.scatter(budget_used,obj_score)
    plt.show()

