# Role-Aware Squad Optimization

A football squad optimization framework that selects an optimal lineup using **Mixed Integer Linear Programming (MILP)** and **PCA-based player profiling**, supporting both **role-agnostic** and **role-aware** team selection.

This project demonstrates how modern optimization techniques can be combined with statistical feature extraction to model **playing styles**, **positional flexibility**, and **formation constraints** in football squad selection.


##  Problem Statement

Selecting an optimal football squad is a constrained optimization problem:

- Limited squad size
- Fixed formation requirements (DF / MF / FW)
- Players can play **multiple roles**
- Player quality depends on **playing style**, not just raw stats

Traditional approaches rely on heuristic scoring or manual selection.  
This project formulates squad selection as a **mathematical optimization problem**, solved exactly using MILP.


## Methodology Overview

### 1. Feature Engineering with PCA
- Player performance metrics (from FBref-style data) are standardized
- **Principal Component Analysis (PCA)** is applied to extract dominant playing styles
- Interpretable components:
  - **PC1** → Attacking / Finishing influence
  - **PC2** → Midfield control / progression
  - **PC3** → Wide play/ball carrying
- Defensive and holding roles are modeled using **negative combinations** of PCs

These components serve as **style-aware player scores**.

### 2. Optimization via MILP

The squad selection problem is solved using **PuLP**:

#### Decision Variables
- Role-agnostic:
  - `x[player] ∈ {0,1}`
- Role-aware:
  - `x[player, role] ∈ {0,1}`

#### Objective
Maximize total squad score: max Σ score(player, role) × x(player,role)  

#### Constraints
- Total squad Size -- currently 10 (excluding GK)
- Formation Constraints (DF/MF/FW)
- A player can be assigned at most **one role**
- Sub roles like (AM, CM, DM) for a midfield are considered
#### Role Modelling:
- Example role-style mapping:
        'CF':PC_1
        'AM': 0.5 * PC_1 + PC_2
        'CM': PC_2
        'DM': -PC_1- PC_2
        'CB': -PC_1
        'WM': PC_3
        'FB': -0.5 * PC_1 + PC_3
This could be changed upon new data

Currently implemented with the Portuguese Football squad, example usage
```
from src.milp_solver import SquadMILPSolver
formation = (4,3,3)
solver = SquadMILPSolver( player_info, players: # must be dict, with name,score : {'cm':0.4,'AM':0.3}, roles:['cm','AM'],
                            formation = formation, total_players =10, role_aware=True)
results = solver.solve()

squad_selected = pd.DataFrame(results['selected_players'])
```

### Limitations (V1):
- Small player pool (only 22 Portugal squad members )
- PCA trained on limited data
- Single Objective optimization

#### Tech Stack
- Python, PULP  (MILP) , Numpy, Pandas, Scikit-Learn (PCA)
