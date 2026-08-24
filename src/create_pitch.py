
import mplsoccer
import matplotlib.pyplot as plt

FORMATIONS_DICT = {
    (4, 3, 3): [
        'GK',
        'LB|LWB|CB', 'CB|LCB', 'CB|RCB', 'RB|RWB|CB',
        'LM|CAM|CM|CDM', 'CDM|CM|CAM|LM|RM', 'RM|CAM|CM|CDM',
        'LW|LM|ST|CF|LF', 'ST|CF|RF|LF|CAM', 'RW|RM|ST|CF|RF'
    ]
}


xaxis_locations = {
    1: [40], 
    2: [20, 60], 
    3: [15, 40, 65], 
    4: [10, 30, 50, 70], 
    5: [5, 25, 40, 55, 75]
}

y_positions = {
    "GK": 120-105,
    "DEF": 120-85,
    "MID": 120-55,
    "ATT": 120-25
}

def get_formation_coords(formation):
    """
    Returns list of (x, y) coordinates for each position slot
    in the formation, in the same order as FORMATIONS_DICT
    """
    coords = []
    
    # Goalkeeper
    coords.append((40, y_positions["GK"]))
    
    # Defenders (4 players)
    def_xs = xaxis_locations[formation[0]]
    for x in def_xs:
        coords.append((x, y_positions["DEF"]))
    
    # Midfielders (3 players)
    mid_xs = xaxis_locations[formation[1]]
    for x in mid_xs:
        coords.append((x, y_positions["MID"]))
    
    # Attackers (3 players)
    att_xs = xaxis_locations[formation[2]]
    for x in att_xs:
        coords.append((x, y_positions["ATT"]))
    
    return coords

# def assign_players_to_slots(players: list[dict], pitch_slots: list[str]) -> dict | None:
#     """
#     Guarantees 100% optimal bipartite matching using clean backtracking.
#     Does not mutate lists during iteration.
#     """
#     assignment = {}

#     def backtrack(slot_idx: int, used_indices: set) -> bool:
#         if slot_idx == len(pitch_slots):
#             return True  # Success! All 11 slots filled.

#         allowed_roles = {r.strip() for r in pitch_slots[slot_idx].split('|')}

#         for idx, player in enumerate(players):
#             if idx in used_indices:
#                 continue  # Player already assigned to an earlier slot

#             # Check primary role or list of possible positions
#             player_roles = player.get('PossiblePositions', [player.get('role', '')])
#             if isinstance(player_roles, str):
#                 player_roles = [player_roles]

#             # If player fits this slot
#             if any(role in allowed_roles for role in player_roles):
#                 assignment[slot_idx] = player
#                 used_indices.add(idx)

#                 # Explore deeper down the tree
#                 if backtrack(slot_idx + 1, used_indices):
#                     return True

#                 # BACKTRACK: undo selection and try next candidate
#                 used_indices.remove(idx)
#                 del assignment[slot_idx]

#         return False

#     success = backtrack(0, set())
#     return assignment if success else None

def assign_players_to_slots(players:list[dict], formation:tuple[int,int,int]):
  
    formation_slots = FORMATIONS_DICT[formation]
    assignments = [None] * len(formation_slots)
    
    from collections import defaultdict
    role_to_players = defaultdict(list)
    for p in players:

        role_to_players[p['role']].append(p)
    
    used_players = set()
    
    for i, slot in enumerate(formation_slots):
        possible_positions = slot.split("|")  
        
        for pos in possible_positions:  
            if pos in role_to_players:
                for player in role_to_players[pos]:
                    if player['Name'] not in used_players:
                        assignments[i] = player
                        used_players.add(player['Name'])
                        break
                
                if assignments[i] is not None:
                    break
    
    return assignments

def plot_team(players,ax=None, formation=(4,3,3)):
    """
    Args:
        players: List with {'Name': str, 'role': str}  
    """
    if ax == None:
        fig, ax = plt.subplots(figsize=(6, 7))
    
    pitch = mplsoccer.VerticalPitch(
        pitch_color='grass',
        line_color='white',
        stripe=True
    )
    pitch.draw(ax=ax)
    
    coords = get_formation_coords(formation)
    assignments = assign_players_to_slots(players, formation)
    
    for i, (player, (x, y)) in enumerate(zip(assignments, coords)):
        if player is None:
            slot_name = FORMATIONS_DICT[formation][i]
            ax.scatter(x, y, s=200, c='red', alpha=0.3)
            ax.text(x, y, slot_name.split('|')[0], 
                   ha="center", va="center", fontsize=8, color='white')
        else:
            ax.scatter(x, y, s=200, c='blue', linewidth=2)
            
            name_parts = player["Name"].split()
            display_name = name_parts[0] + '\n' + name_parts[-1] if len(name_parts)>=2 else name_parts[0]
            # last_name =  name_parts[0]+'\n'+name_parts[-1] if len(name_parts) < 2 else name_parts[0]+'\n'+name_parts[-1]
            # last_name = player['Name']
            
            ax.text(x, y+5, display_name, 
                   ha="center", va="center", 
                   fontsize=9, color='Black', weight='bold')
            
            # Show role below
            ax.text(x, y - 3, player["role"],  # ← Changed from 'AssignedPosition'
                   ha="center", va="top", 
                   fontsize=11, color='yellow')
    
    # plt.title(f"Formation: {formation[0]}-{formation[1]}-{formation[2]}", 
            #  fontsize=11, color='white', weight='bold')
    plt.tight_layout()
    # plt.close()
    return fig

# Example usage
# if __name__ == '__main__':
#     # This is what your MILP solver should return
#     # (converted from x[('player', 'position')] = 1)
#     optimized_team = [{'Name': 'Lionel Messi', 'role': 'RW'},
#                         {'Name': 'Kevin De Bruyne', 'role': 'CM'},
#                         {'Name': 'Kylian Mbappé', 'role': 'ST'},
#                         {'Name': 'Manuel Neuer', 'role': 'GK'},
#                         {'Name': 'Neymar da Silva Santos Jr.', 'role': 'LW'},
#                         {'Name': 'Sadio Mané', 'role': 'LM'},
#                         {'Name': 'Joshua Kimmich', 'role': 'RB'},
#                         {'Name': 'Rúben Santos Gato Alves Dias', 'role': 'CB'},
#                         {'Name': 'Marcos Aoás Corrêa', 'role': 'CB'},
#                         {'Name': 'Andrew Robertson', 'role': 'LB'},
#                         {'Name': 'Christopher Nkunku', 'role': 'CAM'}]
                            
#     fig = plot_team(optimized_team, formation=(4, 3, 3))
#     # plt.savefig("4-3-3-formation.png")
    # plt.show()



