import matplotlib 
matplotlib.use("Agg") # headless backend for testing
import matplotlib.pyplot as plt 
import pytest 

from src.create_pitch import get_formation_coords,assign_players_to_slots,plot_team,FORMATIONS_DICT



# get formation coords

def test_get_formation_coords():
    """Verify coordinate layout length matches 11 players."""
    coords = get_formation_coords((4, 3, 3))
    assert len(coords) == 11
    assert coords[0] == (40, 15)  # Default GK position check

def test_get_formation_coords_unknown_line_size_raises_keyerror():
    """xaxis_locations only defines layouts for 1–5 players per line —
    a formation like (6,3,3) has no defined defender spacing."""
    with pytest.raises(KeyError):
        get_formation_coords((6, 3, 3))

### player assigning

def test_assign_players_to_slots_matches_by_role():
    players = [{"Name":"A","role":'GK'}]
    assignments  = assign_players_to_slots(players,(4,3,3))
    assert assignments[0]["Name"] == "A" 

def test_assign_players_to_slots_matches_via_alternate_position_label():
    """Slot 'RCB|CB' should accept a player whose role is plain 'CB'."""
    players = [{"Name": "A", "role": "CB"}]
    assignments = assign_players_to_slots(players, (4, 3, 3))
    slot_labels = FORMATIONS_DICT[(4, 3, 3)]
    cb_slot_index = slot_labels.index("RCB|CB")
    assert assignments[cb_slot_index]["Name"] == "A"

def test_plot_team_returns_figure_without_raising():
    players = [
        {"Name": "L. Messi", "role": "RW"},
        {"Name": "Cristiano Ronaldo", "role": "ST"},
    ]
    fig = plot_team(players, formation=(4, 3, 3))
    assert isinstance(fig, plt.Figure)
    plt.close(fig)

def test_plot_team_handles_empty_roster_without_raising():
    """All 11 slots should render as empty red placeholder markers."""
    fig = plot_team([], formation=(4, 3, 3))
    assert isinstance(fig, plt.Figure)
    plt.close(fig)
 