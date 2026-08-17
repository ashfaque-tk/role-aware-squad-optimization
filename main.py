import anthropic 
import streamlit as st
from src.create_pitch import plot_team
from src.milp_solver import optimize_squad
import pandas as pd
from pathlib import Path
import json
from llm_input import *
from src.search_players import find_player
from typing import Dict

BASE_DIR = Path(__file__).resolve().parents[0]

# Configure page to use full width
st.set_page_config(
    page_title="Football Squad Optimizer",
    page_icon="⚽",
    layout="wide"
)


@st.cache_data
def load_players():
    player_data_file = BASE_DIR / "data" / "final_squad_cleaned.json"
    df = pd.read_json(player_data_file, orient='records')
    return df

def formation_str_to_tuple(formation_str: str) -> tuple:
    parts = tuple(map(int, formation_str.split("-")))
    return (*parts, 1)  # always add GK

def render_inputs():
    """Render the left column: all user inputs"""
    st.header(" Team Settings ")
    
    # FIXED: Budget now in millions, multiply by 1M when passing to optimizer
    budget = st.slider("Weekly Wage Budget (€M)", 0, 200, 20)  # Changed default to 80M (more realistic)
    formation = st.selectbox("Formation", ["4-3-3", "4-4-2", "3-5-2"])
    style = st.radio("Playing Style", ["attack", "defend", "balanced"])
    avg_age = st.selectbox("Average Team Age", ["None", "U20", "20-28", "28-32", "32-45", "<45"])

    age_dict = {
        "None": None,
        'U20': (12, 20),
        '20-28': (20, 28),
        '28-32': (28, 32),
        '32-45': (32, 45),
        '<45': (12, 45)
    }

    formation = formation_str_to_tuple(formation)
    return budget, formation, style, age_dict[avg_age]


def render_inputs_modified(parsed=None):
    """inputs pre-filled with text from chatbox"""
    st.header("Team Settings")
    st.info( "Settings extracted from your request. Adjust them below if needed.")

    parsed = parsed or {}
    print('inside the render modified', parsed)

    parsed_budget = parsed.get('budget')

    if not parsed_budget:
        st.caption("No budget specified. Using default budget (€1M)")
        budget = st.number_input("Weekly Budget (default)",
                                 min_value= 0,value=1_000_000,step=100_000)
    else:
        budget = parsed_budget

    formation_options = ['4-3-3','4-4-2','3-5-2'] 
    parsed_formation = parsed.get('formation')
    if parsed_formation:
        parsed_str = "-".join(str(x) for x in parsed_formation)
        print(parsed_str,'parsed_str')
        formation_index = formation_options.index(parsed_str) if parsed_str in formation_options else 0 
    else:
        formation_index = 0
    
    formation = st.selectbox('Formation',formation_options, index=formation_index)

    style_options = ["attack", "defend", "balanced"]
    style_index = style_options.index(parsed["style"]) if parsed.get("style") in style_options else 2
    style = st.radio("Playing Style", style_options, index=style_index)


    min_age = parsed.get("min_age")
    max_age = parsed.get("max_age")

    if min_age is None:
        min_age = 16

    if max_age is None:
        max_age = 41

    min_age = st.number_input("Minimum Average Age",
                            min_value=16,
                            max_value = max_age,
                            value=min_age
                        )
    
    max_age = st.number_input("Maximum Average Age",
                            min_value=min_age,
                            max_value=41,
                            value= max_age
                        )
    formation = formation_str_to_tuple(formation)
    return budget, formation, style, (min_age,max_age)

def render_locked_players():
    """Render the right column: locked players with remove buttons"""
    st.header("🔒 Chosen Players")
    
    if st.session_state.locked_players:
        for name, info in st.session_state.locked_players.items():
            # Create a container for each player
            with st.container():
                cols = st.columns([3, 2, 2, 1])
                cols[0].write(f"**{name}**")
                cols[1].write(info["role"])
                
                # FIXED: Display wage in millions for consistency
                wage_millions = info.get('wage', 0) / 1_000_000
                cols[2].write(f"€{wage_millions:.1f}M")
                
                if cols[3].button("❌", key=f"remove_{name}"):
                    st.session_state.locked_roles.remove(info["role"])
                    del st.session_state.locked_players[name]
                    st.rerun()
                st.divider()
    else:
        st.info("No players chosen yet")
    
    # Show impact of locked players
    if st.session_state.locked_players:
        st.subheader("📊 Lock Impact")
        num_locked = len(st.session_state.locked_players)
        st.metric("Chosen Players", f"{num_locked}/3")  
        total_locked_budget = sum(info.get('wage', 0) for info in st.session_state.locked_players.values())
        st.metric("Budget of Chosen Players", f"€{total_locked_budget:.1f}M")
        # Show remaining budget
        if 'current_budget' in st.session_state:
            remaining = st.session_state.current_budget - total_locked_budget
            st.metric("Remaining Budget for player allocation", f"€{remaining:.1f}M")

def player_filtering_section():
    """Player selection interface"""
    st.session_state.optimization_run = False
    st.subheader("➕ Choose Your Favourite Player")  
    # Check if max players locked
    if len(st.session_state.locked_players) >= 3:
        st.warning("⚠️ Maximum 3 players can be chosen")
        return
    players_df = load_players()
    nationalities = sorted(players_df['Nationality'].unique()) 
    # Country selection
    selected_country = st.selectbox("Country", ['-- Select Country --'] + nationalities, key="country_select")    
    if selected_country != '-- Select Country --':
        # Filter players by country
        country_players = players_df[players_df['Nationality'] == selected_country]
        player_options = sorted(country_players['Name'].tolist())   
        # Player selection
        selected_player = st.selectbox("Player",['-- Select Player --'] + player_options, key="player_select" )     
        if selected_player != '-- Select Player --':
            # Get player data
            player_data = players_df[players_df['Name'] == selected_player].iloc[0]
            player_roles = player_data['PossiblePositions']
            
            st.info(f"**Wage:** €{player_data.get('WageEUR', 0):.1f}M | **Age:** {player_data['Age']}")     
            # Filter out already locked roles
            available_roles = [r for r in player_roles if r not in st.session_state.locked_roles]  
            if not available_roles:
                st.error("No available positions for this player (all positions locked)")
                return      
            # Role selection
            selected_role = st.selectbox("Playing Position", ['-- Select Position --'] + available_roles, key="role_select" )    
            if selected_role != '-- Select Position --':
                # Lock button
                if st.button("🔒 Choose Player", type="primary"):
                    st.session_state.locked_players[selected_player] = {
                        "role": selected_role,
                        "age": player_data['Age'],
                        "wage": player_data.get('WageEUR', 0)  # Store in EUR (not millions)
                    }
                    st.session_state.locked_roles.add(selected_role)
                    st.success(f"✓ Locked {selected_player} as {selected_role}")
                    st.rerun()

def render_results(budget, formation, style, age_range):
    """Render the optimization results in the center column"""
    
    # FIXED: Ensure budget is passed correctly (already in EUR from slider * 1M)
    budget_eur = budget 
    
    # # Debug info (optional - can remove later)
    # with st.expander("Debug Info"):
    #     st.write(f"Budget passed to optimizer: €{budget_eur:,} ({budget}M)")
    #     if st.session_state.locked_players:
    #         for name, info in st.session_state.locked_players.items():
    #             st.write(f"- {name}: €{info['wage']:,}")
    
    # Run MILP  
 
    solution = optimize_squad(
        budget_eur, 
        formation,
        style,
        locked_players=st.session_state.locked_players,
        age=age_range
    )
   
    status = solution['status']

    if status != 'Optimal':
        st.error("A team cannot be found with given constraints")
        st.info("Try adjusting: Budget, Age limits, or remove locked players")
    else:
        playing_team = solution['selected_players']
        cost  =  solution['total_budget']
        age   = solution['average age']
        st.success(" Your Dream Team is Ready!")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Cost", f"€{cost/1_000_000:.1f}M")
        with col2:
            st.metric("Average Age", f"{age:.1f}")
        # Plot the team formation with controlled size
        fig = plot_team(playing_team, formation=formation[:3])        
        # FIXED: Set explicit figure size for better control
        fig.set_size_inches(10, 7)  # Width, Height in inches  
        # Display with constrained width
        st.pyplot(fig, width="content")  # Don't use full container width   
        # Show team details in expandable section
        with st.expander("📋 View Full Squad Details"):
            st.dataframe(
                pd.DataFrame(playing_team),
                width="stretch",
                hide_index=True
            )


def lock_player(player_name):
    players_df = load_players()
    if player_name != ' ':
            # Get player data
            player_data = players_df[players_df['Name'] == player_name].iloc[0]
            player_roles = player_data['PossiblePositions']
            
            st.info(f"**Wage:** €{player_data.get('WageEUR', 0)/1_000_000:.1f}M | **Age:** {player_data['Age']}")     
            # Filter out already locked roles
            available_roles = [r for r in player_roles if r not in st.session_state.locked_roles]  
            if not available_roles:
                st.error("No available positions for this player (all positions locked)")
                return      
            # Role selection
            selected_role = st.selectbox("Playing Position", ['-- Select Position --'] + available_roles + ['None'], key="role_select" )    
            if selected_role != '-- Select Position --':
                # Lock button
                if st.button("🔒 Choose Player", type="primary"):
                    st.session_state.locked_players[player_name] = {
                        "role": selected_role,
                        "age": player_data['Age'],
                        "wage": player_data.get('WageEUR', 0)  # Store in EUR (not millions)
                    }
                    st.session_state.locked_roles.add(selected_role)


def choose_players(players):
    players_df = load_players()

    for player in players:

        matched_name = find_player(player,players_df)
        if not matched_name:
            st.warning("No players with the name found")
        elif len(matched_name)>1:
            st.info("More than one player found, Select from the list")
            # st.selectbox("Players",matched_name)
        elif len(matched_name)==1:
            st.info("Found your player")
            st.info(f"Found Player: {matched_name[0]}")
            # find the player details from the player data frame
            # player_data = players_df[players_df['Name']==matched_name[0]]
            player_data = players_df[players_df['Name'] == matched_name].iloc[0]
            player_roles = player_data['PossiblePositions']
            st.info(f"**Wage:** €{player_data.get('WageEUR', 0)/1_000_000:.1f}M | **Age:** {player_data['Age']}")     

            st.session_state.locked_players[matched_name] = {"role": 'none',
                        "age": player_data['Age'],
                        "wage": player_data.get('WageEUR', 0)  # Store in EUR (not millions)
                    }
            st.session_state.locked_roles.add('none')
    return 

def render_layout():
    """Main layout function: full-width three-column layout"""
    # Create three columns with proper width distribution
    col_left, col_middle, col_right = st.columns([2, 5, 2])
    players = load_players()
    players_names = sorted(players['Name'].tolist())

    with col_left:
        user_text = st.text_input("Describe your ideal team")
        if st.button("Parse with AI") and user_text:
            st.session_state.parsed_constraints = parse_nl_input(user_text)
        parsed = st.session_state.get("parsed_constraints", {})
        budget, formation, style, age_range = render_inputs_modified(parsed)

        fixed_players = parsed.get('locked_players')
        print(fixed_players)


        player_name = st.selectbox("Find you player",[' '] + players_names,key='player_select')
        lock_player(player_name)

        if fixed_players:
            st.caption(f"Detected from text: {', '.join(parsed['locked_players'])}.")

            for player in fixed_players:
                match_player_name = find_player(player,players)
                print('matched player name',match_player_name)
                if len(match_player_name) > 1:
                    st.info("More than one player found, choose ")
                    player_select = st.selectbox('Choose your player', [' '] + match_player_name,key='player_select')
                    print(match_player_name)
                    lock_player(player_select)
                else: 
                    st.info("player found")
                    # print(type(players),players)
                    matched_player_data = players[players['Name']==match_player_name[0]].iloc[0]
                    # print(matched_player_data)
                    st.session_state.locked_players[match_player_name[0]]={"role":'none','age':matched_player_data['Age'],'wage':matched_player_data.get('WageEUR',0)}
                
        # st.session_state.locked_players[]
        # # Team settings inputs
        # budget, formation, style, age_range = render_inputs()
        # st.session_state.current_budget = budget
        # Optimize button at bottom of left column
        st.markdown("---")
        if st.button("⚡ Optimize Team", type="primary", width='stretch'):
            st.session_state.optimization_run = True
            # Results will be rendered in the middle column below

    with col_middle:
        # Main pitch area
        st.header("⚽ Team Visualization")
        if st.session_state.optimization_run:
            with st.spinner("Finding Optimal Squad..."):
                render_results(budget, formation, style, age_range)
        else:
            # Placeholder when no optimization has run
            st.info("👈 Configure settings and click 'Optimize Team' to see your dream squad!")
        
    with col_right:
        # Player selection and locked players
        # player_filtering_section()
        st.markdown("---")
        render_locked_players()

if __name__ == '__main__':
    # Initialize session state
    if "locked_players" not in st.session_state:
        st.session_state.locked_players = {}

    if "locked_roles" not in st.session_state:
        st.session_state.locked_roles = set()

    if "optimization_run" not in st.session_state:
        st.session_state.optimization_run = False
    
    if "current_budget" not in st.session_state:
        st.session_state.current_budget = 80  # Default budget in millions

    # Page title
    st.title("⚽ Football Squad Optimizer")
    
    # Render the layout
    render_layout()