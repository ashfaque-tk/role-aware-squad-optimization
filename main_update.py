import anthropic
import streamlit as st
from src.create_pitch import plot_team
from src.milp_solver import optimize_squad
import pandas as pd
from pathlib import Path
from llm_input import *
from src.search_players import find_player

BASE_DIR = Path(__file__).resolve().parents[0]

st.set_page_config(page_title="Football Squad Optimizer", page_icon="⚽", layout="wide")


@st.cache_data
def load_players():
    player_data_file = BASE_DIR / "data" / "final_squad_cleaned.json"
    return pd.read_json(player_data_file, orient='records')


def formation_str_to_tuple(formation_str: str) -> tuple:
    parts = tuple(map(int, formation_str.split("-")))
    return (*parts, 1)  # always add GK


def render_inputs_modified(parsed=None):
    """Team settings, pre-filled from parsed NL constraints when available."""
    st.header("Team Settings")
    st.info("Settings extracted from your request. Adjust them below if needed.")

    parsed = parsed or {}
    parsed_budget = parsed.get('budget')
    if not parsed_budget:
        st.caption("No budget specified. Using default budget (€1,000,000)")
        budget_default = 1_000_000
    else:
        budget_default = int(parsed_budget)

    budget = st.number_input(
        "Weekly Wage Budget (€)",
        min_value=0,
        value=budget_default,
        step=100_000,
        format="%d"
    )

    formation_options = ['4-3-3', '4-4-2', '3-5-2']
    parsed_formation = parsed.get('formation')
    if parsed_formation:
        parsed_str = "-".join(str(x) for x in parsed_formation)
        formation_index = formation_options.index(parsed_str) if parsed_str in formation_options else 0
    else:
        formation_index = 0
    formation = st.selectbox('Formation', formation_options, index=formation_index)

    style_options = ["attack", "defend", "balanced"]
    style_index = style_options.index(parsed["style"]) if parsed.get("style") in style_options else 2
    style = st.radio("Playing Style", style_options, index=style_index)

    min_age = parsed.get("min_age") or 16
    max_age = parsed.get("max_age") or 41

    min_age = st.number_input("Minimum Average Age", min_value=16, max_value=max_age, value=min_age)
    max_age = st.number_input("Maximum Average Age", min_value=min_age, max_value=41, value=max_age)

    formation = formation_str_to_tuple(formation)
    return budget, formation, style, (min_age, max_age)


# def resolve_and_lock_player(candidate_name: str, candidate_role: str, key_suffix: str, players_df: pd.DataFrame):
#     """
#     Resolve a name (manual search or LLM-extracted) to a dataset row, handle
#     disambiguation when multiple matches exist, and render lock / edit / remove
#     controls. Single source of truth for locking — replaces the old
#     lock_player / choose_players / player_filtering_section trio.
#     """
#     matches = find_player(candidate_name, players_df)

#     if not matches:
#         st.warning(f"No player found matching '{candidate_name}'")
#         return

#     if len(matches) > 1:
#         chosen = st.selectbox(
#             f"Multiple matches for '{candidate_name}' — choose one",
#             [' '] + matches,
#             key=f"disambig_{key_suffix}"
#         )
#         if chosen == ' ':
#             return
#         matched_name = chosen
#     else:
#         matched_name = matches[0]

#     player_data = players_df[players_df['Name'] == matched_name].iloc[0]
#     available_positions = list(player_data['PossiblePositions'])

#     # --- already locked: show status + edit/remove ---
#     if matched_name in st.session_state.locked_players:
#         # current_role = st.session_state.locked_players[matched_name]['role']
#         current_role = candidate_role
#         st.success(f"🔒 {matched_name} — role set: **{candidate_role}**")
#         with st.expander("Edit"):
#             new_role = st.selectbox(
#                 "Change position", [None] + available_positions, key=f"edit_role_{matched_name}"
#             )
#             if st.button("Update role", key=f"update_{matched_name}"):
#                 st.session_state.locked_players[matched_name]['role'] = None if new_role == 'None' else new_role
#                 st.rerun()
#             if st.button("Remove player", key=f"remove_{matched_name}"):
#                 del st.session_state.locked_players[matched_name]
#                 st.rerun()
#         return

#     # --- not yet locked: show details + lock control ---
#     # NOTE: WageEUR is stored/displayed in millions already based on your data —
#     # confirm this matches final_squad_cleaned.json; see flag below.
#     st.info(f"**{matched_name}** — €{player_data.get('WageEUR', 0):.2f} | Age {player_data['Age']}")
#     selected_role = st.selectbox(
#         "Position (optional — leave as None to let the optimizer decide)",
#         ['None'] + available_positions,
#         key=f"role_select_{key_suffix}"
#     )
#     if st.button(f"🔒 Lock {matched_name}", key=f"lock_{key_suffix}"):
#         st.session_state.locked_players[matched_name] = {
#             "role": None if selected_role == 'None' else selected_role,
#             "age": player_data['Age'],
#             "wage": player_data.get('WageEUR', 0)
#         }
#         st.rerun()

def resolve_and_lock_player(candidate_name: str, candidate_role, key_suffix: str,
                             players_df: pd.DataFrame, source: str = "manual"):
    matches = find_player(candidate_name, players_df)

    if not matches:
        st.warning(f"No player found matching '{candidate_name}'")
        return

    if len(matches) > 1:
        chosen = st.selectbox(
            f"Multiple matches for '{candidate_name}' — choose one",
            [' '] + matches,
            key=f"disambig_{key_suffix}"
        )
        if chosen == ' ':
            return
        matched_name = chosen
    else:
        matched_name = matches[0]

    player_data = players_df[players_df['Name'] == matched_name].iloc[0]
    available_positions = list(player_data['PossiblePositions'])

    # --- not yet locked ---
    if matched_name not in st.session_state.locked_players:
        if source == "llm":
            # auto-lock immediately, no button wait
            st.session_state.locked_players[matched_name] = {
                "role": candidate_role,
                "age": player_data['Age'],
                "wage": player_data.get('WageEUR', 0),
                "source": "llm"
            }
            st.session_state.last_llm_locked.add(matched_name)
        else:
            st.info(f"**{matched_name}** — €{player_data.get('WageEUR', 0):.2f}M | Age {player_data['Age']}")
            selected_role = st.selectbox(
                "Position (optional — leave as None to let the optimizer decide)",
                ['None'] + available_positions,
                key=f"role_select_{key_suffix}"
            )
            if st.button(f"🔒 Lock {matched_name}", key=f"lock_{key_suffix}"):
                st.session_state.locked_players[matched_name] = {
                    "role": None if selected_role == 'None' else selected_role,
                    "age": player_data['Age'],
                    "wage": player_data.get('WageEUR', 0),
                    "source": "manual"
                }
                st.rerun()
            return  # nothing locked yet, skip edit UI below

    # --- already locked: show status + edit/remove (same for both sources) ---
    current_role = st.session_state.locked_players[matched_name]['role']
    st.success(f"🔒 {matched_name} — role set: **{current_role or 'None'}**")
    with st.expander("Edit"):
        new_role = st.selectbox(
            "Change position", ['None'] + available_positions, key=f"edit_role_{matched_name}"
        )
        if st.button("Update role", key=f"update_{matched_name}"):
            st.session_state.locked_players[matched_name]['role'] = None if new_role == 'None' else new_role
            st.rerun()
        if st.button("Remove player", key=f"remove_{matched_name}"):
            del st.session_state.locked_players[matched_name]
            st.rerun()

def render_locked_players():
    """Right column: locked players with remove buttons + lock impact summary."""
    st.header("🔒 Chosen Players")

    if not st.session_state.locked_players:
        st.info("No players chosen yet")
        return

    for name, info in st.session_state.locked_players.items():
        with st.container():
            cols = st.columns([3, 2, 2, 1])
            cols[0].write(f"**{name}**")
            cols[1].write(info["role"] or "no role set")
            cols[2].write(f"€{info.get('wage', 0):.1f}M")
            if cols[3].button("❌", key=f"remove_locked_{name}"):
                del st.session_state.locked_players[name]
                st.rerun()
            st.divider()

    st.subheader("📊 Lock Impact")
    num_locked = len(st.session_state.locked_players)
    st.metric("Chosen Players", f"{num_locked}/3")
    total_locked_budget = sum(info.get('wage', 0) for info in st.session_state.locked_players.values())
    st.metric("Budget of Chosen Players", f"€{total_locked_budget:.1f}")
    if 'current_budget' in st.session_state:
        remaining = st.session_state.current_budget - total_locked_budget
        st.metric("Remaining Budget for player allocation", f"€{remaining:.1f}")


def render_results(budget, formation, style, age_range):
    """Run the optimizer and render results in the center column."""
    solution = optimize_squad(
        budget, formation, style,
        locked_players=st.session_state.locked_players,
        age=age_range
    )
    status = solution['status']

    if status != 'Optimal':
        st.error("A team cannot be found with given constraints")
        st.info("Try adjusting: Budget, Age limits, or remove locked players")
        return

    playing_team = solution['selected_players']
    st.success("Your Dream Team is Ready!")
    col1, col2 = st.columns(2)
    col1.metric("Total Cost", f"€{solution['total_budget']/1_000_000:.1f}M")
    col2.metric("Average Age", f"{solution['average age']:.1f}")
    print('found team' , playing_team)

    fig = plot_team(playing_team, formation=formation[:3])
    fig.set_size_inches(10, 7)
    st.pyplot(fig, width="content")

    with st.expander("📋 View Full Squad Details"):
        st.dataframe(pd.DataFrame(playing_team), width="stretch", hide_index=True)


def render_layout():
    col_left, col_middle, col_right = st.columns([2, 5, 2])
    players_df = load_players()
    players_names = sorted(players_df['Name'].tolist())
    
    with col_left:
        user_text = st.text_input("Describe your ideal team")
        if st.button("Parse with AI") and user_text:
            for name in st.session_state.get("last_llm_locked", set()):
                st.session_state.locked_players.pop(name, None)
            st.session_state.last_llm_locked = set()

            st.session_state.parsed_constraints = parse_nl_input(user_text)

        parsed = st.session_state.get("parsed_constraints", {})

        budget, formation, style, age_range = render_inputs_modified(parsed)
        st.session_state.current_budget = budget

        st.markdown("---")
        st.subheader("➕ Add a Player")

        manual_name = st.selectbox("Find your player", [' '] + players_names, key='manual_player_select')
        if manual_name != ' ':
            resolve_and_lock_player(manual_name, key_suffix="manual", players_df=players_df)

        fixed_players = parsed.get('locked_players', [])
        print("fixed players", fixed_players)

        if fixed_players:
            st.caption(f"Detected from text: {', '.join(p['name'] for p in fixed_players)}")
            for i, p in enumerate(fixed_players):
                resolve_and_lock_player(p['name'], p['role'], key_suffix=f"llm_{i}",
                                        players_df=players_df, source="llm")

        st.markdown("---")
        if st.button("⚡ Optimize Team", type="primary", width='stretch'):
            st.session_state.optimization_run = True

    with col_middle:
        st.header("⚽ Team Visualization")
        if st.session_state.optimization_run:
            with st.spinner("Finding Optimal Squad..."):
                render_results(budget, formation, style, age_range)
        else:
            st.info("👈 Configure settings and click 'Optimize Team' to see your dream squad!")

    with col_right:
        render_locked_players()


if __name__ == '__main__':
    if "locked_players" not in st.session_state:
        st.session_state.locked_players = {}
    if "optimization_run" not in st.session_state:
        st.session_state.optimization_run = False
    if "current_budget" not in st.session_state:
        st.session_state.current_budget = 1_000_000
    if "last_llm_locked" not in st.session_state:
        st.session_state.last_llm_locked = set()

    st.title("⚽ Football Squad Optimizer")
    render_layout()