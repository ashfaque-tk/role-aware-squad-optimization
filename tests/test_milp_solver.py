import pandas as pd 
import pytest 

from src.milp_solver import SquadMILPSolver



## MILP Solver Core logic tests

@pytest.fixture 
def dummy_player_pool():
    """Provides a controlled mini-squad for deterministic solver testing"""
    return [
        {"Name": "GK One", "PossiblePositions": ["GK"], "GlobalPos": {"GK": "GK"}, "rating_per_roles": {"GK": 85}, "Overall": 85, "WageEUR": 50000, "Age": 28},
        {"Name": "Def One", "PossiblePositions": ["CB"], "GlobalPos": {"CB": "DF"}, "rating_per_roles": {"CB": 80}, "Overall": 80, "WageEUR": 40000, "Age": 25},
        {"Name": "Def Two", "PossiblePositions": ["LB"], "GlobalPos": {"LB": "DF"}, "rating_per_roles": {"LB": 82}, "Overall": 82, "WageEUR": 45000, "Age": 24},
        {"Name": "Def Three", "PossiblePositions": ["RB"], "GlobalPos": {"RB": "DF"}, "rating_per_roles": {"RB": 81}, "Overall": 81, "WageEUR": 40000, "Age": 26},
        {"Name": "Def Four", "PossiblePositions": ["CB"], "GlobalPos": {"CB": "DF"}, "rating_per_roles": {"CB": 83}, "Overall": 83, "WageEUR": 50000, "Age": 29},
        {"Name": "Mid One", "PossiblePositions": ["CM","CAM"], "GlobalPos": {"CM": "MF","CAM":"MF"}, "rating_per_roles": {"CM": 86,"CAM":85}, "Overall": 86, "WageEUR": 60000, "Age": 27},
        {"Name": "Mid Two", "PossiblePositions": ["CDM"], "GlobalPos": {"CDM": "MF"}, "rating_per_roles": {"CDM": 84}, "Overall": 84, "WageEUR": 55000, "Age": 30},
        {"Name": "Mid Three", "PossiblePositions": ["CAM"], "GlobalPos": {"CAM": "MF"}, "rating_per_roles": {"CAM": 88}, "Overall": 88, "WageEUR": 70000, "Age": 23},
        {"Name": "Fwd One", "PossiblePositions": ["ST","CF"], "GlobalPos": {"ST": "FW","CF":"FW"}, "rating_per_roles": {"ST": 90,"CF":89}, "Overall": 90, "WageEUR": 100000, "Age": 29},
        {"Name": "Fwd Two", "PossiblePositions": ["LW"], "GlobalPos": {"LW": "FW"}, "rating_per_roles": {"LW": 87}, "Overall": 87, "WageEUR": 80000, "Age": 22},
        {"Name": "Fwd Three", "PossiblePositions": ["RW"], "GlobalPos": {"RW": "FW"}, "rating_per_roles": {"RW": 89}, "Overall": 89, "WageEUR": 90000, "Age": 26},
    ]

def make_solver(players, formation=(4, 3, 3, 1), style="balanced", locked_players=None, budget=1_000_000,role_aware=True):
    return SquadMILPSolver(
        players,
        formation=formation,
        age=(16, 41),
        total_budget=budget,
        playing_style=style,
        locked_players=locked_players or {},
        role_aware=role_aware
    )
 

def test_milp_solver_feasibility(dummy_player_pool):
    """Test sovler builds model and reaches optimal solution under budget"""
    solver = make_solver(dummy_player_pool,role_aware=True)
    result = solver.solve()

    assert result['status'] =='Optimal'
    assert len(result["selected_players"]) ==11
    assert result["total_budget"] <= 1_000_000

def test_milp_solver_budget_infeasible(dummy_player_pool):
    """Test solver flags infeasibility when budget is impossibly low."""
    solver = SquadMILPSolver(
        player_info=dummy_player_pool,
        formation=(4, 3, 3, 1),
        age=(18, 35),
        total_budget=10_000,  # Extremely low budget
        playing_style="balanced",
        locked_players={},
        total_players=11,
        role_aware=True
    )
    result = solver.solve()
    assert result["status"] != "Optimal"
    assert result["feasible"] is False

#### formation constraints 

def test_formation_constraints_known_combo_returns_dict_and_weights():
    solver = make_solver(players=[])
    constraints, weights = solver._get_formation_constraints((4, 3, 3), "balanced")
    assert constraints["CB"] == (2, 2)
    assert weights == [0.5, 0.5, 0.5]

def test_formation_constraints_attack_vs_defend_differ():
    solver = make_solver(players=[])
    attack, _ = solver._get_formation_constraints((4, 3, 3), "attack")
    defend, _ = solver._get_formation_constraints((4, 3, 3), "defend")
    assert attack["CAM"] != defend["CAM"]  # attack should allow more CAMs than defend


def test_formation_constraints_unsupported_formation_raises_keyerror():
    """Only (4,3,3) is implemented right now."""
    solver = make_solver(players=[])
    with pytest.raises(KeyError):
        solver._get_formation_constraints((3, 5, 2), "balanced")


#### build variables 

def test_variables_creates_one_var_per_player_role_pair():
    players = [{"Name":"A","PossiblePositions":["ST","LW"]},
                {"Name": "B","PossiblePositions":["CB"]}]
    
    solver = make_solver(players=players,role_aware=True)
    solver.build_variables()

    assert set(solver.x.keys()) == {("A","ST"),("A","LW"),("B","CB")}

 
def test_solve_with_empty_roster_is_infeasible_not_a_crash():
    solver = make_solver(players=[])
    result = solver.solve()
    assert result["status"] == "Infeasible"
    assert result["feasible"] is False