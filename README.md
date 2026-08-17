# Role-Aware Squad Optimization
An advanced football squad optimization framework that selects an optimal lineup using **Mixed Integer Linear Programming (MILP)**, an interactive Streamlit user interface, and a natural language constraint injection layer.

This project demonstrates how modern optimization techniques can be combined with statistical feature extraction to model **playing styles**, **positional flexibility**, and **formation constraints** in football squad selection.


##  Problem Statement

Selecting an optimal football squad is a constrained optimization problem:

- Limited squad size
- Fixed formation requirements (DF / MF / FW) and micro roles: (CB,LB,RB,LWB,RWB,CDM,CM,LM,RM,LCM,RCM,CAM,LW,RW,ST,CF)
- Players can play **multiple roles**
- Player quality depends on **playing style**, not just raw stats (need more data)

Traditional approaches rely on heuristic scoring or manual selection.  
This project formulates squad selection as a **mathematical optimization problem**and solves it exactly using MILP.

## 🚀 Key Features

* **Exact Optimization via MILP:** Formulates squad selection as a Mixed-Integer Linear Program solved to optimality using `PuLP`. Handles complex constraints including formation requirements (e.g., 4-3-3), positional hierarchies, budget caps, and bound constraints.
* **Advanced Constraint Handling:** Supports locking pre-fixed player selections, scenario-dependent rule sets, and multi-role assignments.
* **Natural Language (LLM) Input Layer:** Allows users to input plain text descriptions of team requirements, which are parsed into dynamic optimization constraints.
* **Interactive Streamlit Dashboard:** A user-facing web app backed by relational data (SoFIFA dataset stored in SQLite) allowing dynamic scenario configuration and visual inspection of trade-offs.

### Optimization via MILP

The squad selection problem is solved using **PuLP**:

#### Decision Variables
- Role-agnostic:
  - `x[player] ∈ {0,1}`
- Role-aware:
  - `x[player, role] ∈ {0,1}`

#### Objective
Maximize total squad score: max Σ score(player, role) × x(player,role)  

#### Constraints
- Total squad Size --11 players
- Formation Constraints (DF/MF/FW)
- A player can be assigned at most **one role**
- Sub roles like (AM, CM, DM) for a midfield are considered

#### DataSet:
- SoFifa25 dataset is used
- it contains overall scores for a player for every possible roles

#### Tech Stack
- Python, PULP  (MILP), Numpy, Pandas, Streamlit


#### Limitations (V2):

- Single Objective optimization
- 


# Removed from current version

** following PCA feature and a sqlite database handling removed from the current version
### Feature Engineering with PCA
- Player performance metrics (from FBref-style data) are standardized
- **Principal Component Analysis (PCA)** is applied to extract dominant playing styles
- Interpretable components:
  - **PC1** → Attacking / Finishing influence
  - **PC2** → Midfield control / progression
  - **PC3** → Wide play/ball carrying
- Defensive and holding roles are modeled using **negative combinations** of PCs

These components serve as **style-aware player scores**.

#### Role Modelling:
- Example role-style mapping:
       ``` CF:PC_1
        AM: 0.5 * PC_1 + PC_2
        CM: PC_2
        DM: -PC_1- PC_2
        CB: -PC_1
        WM: PC_3
        FB: -0.5 * PC_1 + PC_3```






