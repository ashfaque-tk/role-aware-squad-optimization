import streamlit as st
import pandas as pd
from pathlib import Path

from src.create_pitch import plot_team
from src.milp_solver import optimize_squad
from squad_blocks import (
    render_llm_block,
    render_manual_block,
    safe_get_player,
    find_duplicate_roles,
    clear_all_locked,
    MAX_LOCKS,
)

BASE_DIR = Path(__file__).resolve().parents[0]
st.set_page_config(page_title="Football Squad Optimizer", page_icon="⚽", layout="wide")


def init_state():
    defaults = {
        "locked_players": {},
        "optimization_run": False,
        "last_solution": None,
        "last_error": None,
        "current_budget": 1_000_000,
        "last_llm_locked": set(),
        "llm_dismissed": set(),
        "parsed_constraints": {},
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


@st.cache_data
def load_players():
    path = BASE_DIR / "data" / "final_squad_cleaned.json"
    return pd.read_json(path, orient="records")


def formation_str_to_tuple(formation_str: str) -> tuple:
    parts = tuple(map(int, formation_str.split("-")))
    return (*parts, 1)  # always add GK


def render_team_settings(parsed: dict):
    st.header("Team Settings")

    budget_default = int(parsed.get("budget") or 1_000_000)
    budget = st.number_input(
        "Weekly Wage Budget (€)", min_value=0, value=budget_default, step=100_000, format="%d"
    )

    formation_options = ["4-3-3"]
    formation = st.selectbox("Formation", formation_options)

    style_options = ["attack", "defend", "balanced"]
    style_index = style_options.index(parsed["style"]) if parsed.get("style") in style_options else 2
    style = st.radio("Playing Style", style_options, index=style_index)

    min_age = parsed.get("min_age") or 16
    max_age = parsed.get("max_age") or 41
    if min_age > max_age:  # guards against a malformed LLM extraction
        min_age, max_age = 16, 41
    min_age = st.number_input("Minimum Average Age", min_value=16, max_value=max_age, value=min_age)
    max_age = st.number_input("Maximum Average Age", min_value=min_age, max_value=41, value=max_age)

    return budget, formation_str_to_tuple(formation), style, (min_age, max_age)


def render_locked_players_panel(players_df):
    """Shows every locked player (any source) with role-edit + remove.
    This is the single place role conflicts are surfaced and fixed."""
    st.header("🔒 Chosen Players")
    if not st.session_state.locked_players:
        st.info("No players chosen yet")
        return

    duplicate_roles = find_duplicate_roles(st.session_state.locked_players)
    if duplicate_roles:
        st.warning(
            f"⚠️ Role conflict: **{', '.join(duplicate_roles)}** is assigned to more than one "
            "player. Change a role below or remove one player before optimizing."
        )

    if st.button("🗑️ Clear all chosen players", key="clear_all_locked"):
        clear_all_locked()
        st.rerun()

    for name, info in list(st.session_state.locked_players.items()):
        row = safe_get_player(players_df, name)
        possible = list(row.get("PossiblePositions") or []) if row is not None else []
        current_role = info.get("role") or "None"
        options = ["None"] + possible
        if current_role not in options:
            options.append(current_role)  # keep an LLM-assigned role even if not in the list

        cols = st.columns([2.5, 2, 1.7, 1])
        cols[0].write(f"**{name}**")

        new_role = cols[1].selectbox(
            "Role", options, index=options.index(current_role),
            key=f"panel_role_{name}", label_visibility="collapsed",
        )
        if new_role != current_role:
            st.session_state.locked_players[name]["role"] = None if new_role == "None" else new_role
            st.rerun()

        cols[2].write(f"€{info.get('wage', 0):,.0f}")

        if cols[3].button("❌", key=f"panel_remove_{name}"):
            if info.get("source") == "llm":
                st.session_state.llm_dismissed.add(name)
            st.session_state.locked_players.pop(name, None)
            st.session_state.last_llm_locked.discard(name)
            st.rerun()
        st.divider()

    num_locked = len(st.session_state.locked_players)
    st.metric("Chosen Players", f"{num_locked}/{MAX_LOCKS}")
    total_locked_budget = sum(info.get("wage", 0) for info in st.session_state.locked_players.values())
    st.metric("Budget of Chosen Players", f"€{total_locked_budget:,.0f}")
    remaining = st.session_state.current_budget - total_locked_budget
    st.metric("Remaining Budget", f"€{remaining:,.0f}")


def check_duplicate_role_error():
    duplicate_roles = find_duplicate_roles(st.session_state.locked_players)
    if duplicate_roles:
        return (
            f"Two locked players are both set to **{duplicate_roles[0]}**. "
            "Fix that in the Chosen Players panel before optimizing."
        )
    return None


def compute_solution(budget, formation, style, age_range):
    """Runs the optimizer exactly once, when called. Returns (solution, error_message) —
    exactly one of the two is None. Nothing here should run on a rerun that isn't
    the actual button click, or every edit re-triggers a full MILP solve."""
    error = check_duplicate_role_error()
    if error:
        return None, error

    try:
        solution = optimize_squad(
            budget, formation, style,
            locked_players=st.session_state.locked_players,
            age=age_range,
        )
    except Exception as e:
        return None, f"The optimizer hit an unexpected error — this is a bug, not a bad input.\n\nDetails: {e}"

    if solution.get("status") != "Optimal":
        return None, "A team cannot be found with the given constraints. Try adjusting: budget, age limits, or remove a locked player."

    return solution, None


def display_solution(solution, formation):
    """Pure display — no solving here, so it's cheap to redraw on every rerun."""
    playing_team = solution["selected_players"]
    st.success("✅ Your Dream Team is Ready!")
    col1, col2 = st.columns(2)
    col1.metric("Total Cost", f"€{solution['total_budget']/1_000_000:.1f}M")
    col2.metric("Average Age", f"{solution['average age']:.1f}")

    try:
        fig = plot_team(playing_team, formation=formation[:3])
        fig.set_size_inches(10, 7)
        st.pyplot(fig, width="content")
    except Exception:
        st.warning("Couldn't render the pitch diagram — showing the table instead.")

    with st.expander("📋 View Full Squad Details"):
        st.dataframe(pd.DataFrame(playing_team), width="stretch", hide_index=True)


def main():
    init_state()

    try:
        players_df = load_players()
    except Exception as e:
        st.error("Couldn't load player data. Check that data/final_squad_cleaned.json exists.")
        st.caption(f"Details: {e}")
        return

    st.title("⚽ Football Squad Optimizer")
    col_left, col_middle, col_right = st.columns([2, 5, 2])

    budget, formation, style, age_range = 0, (4, 3, 3, 1), "balanced", (16, 41)

    with col_left:
        # 1. AI description — first thing the user sees
        try:
            parsed = render_llm_block(players_df)
        except Exception as e:
            st.error("The AI parsing panel hit an error — falling back to manual controls.")
            st.caption(f"Details: {e}")
            parsed = st.session_state.get("parsed_constraints", {})

        st.markdown("---")

        # 2. Team settings — the main configuration
        try:
            budget, formation, style, age_range = render_team_settings(parsed)
        except Exception as e:
            st.error("Couldn't render team settings — using defaults.")
            st.caption(f"Details: {e}")

        st.session_state.current_budget = budget

        st.markdown("---")

        # 3. Manual add — last resort / fine-tuning, placed at the bottom
        try:
            render_manual_block(players_df)
        except Exception as e:
            st.error("The manual picker hit an error.")
            st.caption(f"Details: {e}")

        st.markdown("---")
        if st.button("⚡ Optimize Team", type="primary", width="stretch"):
            with st.spinner("Finding Optimal Squad..."):
                solution, error = compute_solution(budget, formation, style, age_range)
            st.session_state.last_solution = solution
            st.session_state.last_error = error
            st.session_state.optimization_run = True

    with col_middle:
        st.header("⚽ Team Visualization")
        if st.session_state.optimization_run:
            if st.session_state.last_error:
                st.error(st.session_state.last_error)
            elif st.session_state.last_solution:
                display_solution(st.session_state.last_solution, formation)
        else:
            st.info("👈 Configure settings and click 'Optimize Team' to see your dream squad!")

    with col_right:
        render_locked_players_panel(players_df)


if __name__ == "__main__":
    main()