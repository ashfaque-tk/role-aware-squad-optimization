"""
All player-picking logic lives here, split into two clearly separated
blocks: LLM (automatic, from parsed text) and MANUAL (user picks from
a dropdown). They share the same session_state.locked_players dict but
never share widget keys, so editing one can't break the other.
"""
import os
from collections import Counter

import streamlit as st
import anthropic

from llm_input import parse_nl_input
from src.search_players import find_player

MAX_LOCKS = 3


# ---------------------------------------------------------------------------
# Shared state helpers — both blocks below go through these instead of
# touching st.session_state.locked_players directly.
# ---------------------------------------------------------------------------

def safe_get_player(players_df, name):
    match = players_df[players_df["Name"] == name]
    if match.empty:
        return None
    return match.iloc[0]


def can_lock_more() -> bool:
    return len(st.session_state.locked_players) < MAX_LOCKS


def lock_player(name, role, player_row, source: str):
    if name in st.session_state.locked_players:
        return  # idempotent — callers don't need to guard against double-calls
    if not can_lock_more():
        st.warning(f"Maximum {MAX_LOCKS} players can be chosen. Skipped **{name}**.")
        if source == "llm":
            # Stop retrying this one on future reruns — otherwise it silently
            # slots in the moment a spot frees up, which looks like it
            # "jumped the queue" days later in the session.
            st.session_state.setdefault("llm_dismissed", set()).add(name)
        return
    st.session_state.locked_players[name] = {
        "role": role,
        "age": player_row.get("Age"),
        "wage": player_row.get("WageEUR", 0),
        "source": source,
    }
    if source == "llm":
        st.session_state.last_llm_locked.add(name)


def unlock_player(name):
    st.session_state.locked_players.pop(name, None)
    st.session_state.last_llm_locked.discard(name)


def clear_all_locked():
    st.session_state.locked_players = {}
    st.session_state.last_llm_locked = set()
    st.session_state.llm_dismissed = set()


def find_duplicate_roles(locked_players: dict) -> list:
    """Returns role names assigned to more than one locked player."""
    roles = [info["role"] for info in locked_players.values() if info.get("role")]
    counts = Counter(roles)
    return [role for role, count in counts.items() if count > 1]


# ---------------------------------------------------------------------------
# CONSTRAINTS FROM LLM
# ---------------------------------------------------------------------------

def render_llm_block(players_df):
    st.subheader("🤖 Describe Your Ideal Team")

    user_text = st.text_input("Describe your ideal team")
    user_api_key = st.text_input(
        "Anthropic API Key (optional — needed to use AI parsing)",
        type="password",
    )
    api_key = user_api_key or os.getenv("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=api_key) if api_key else None

    parsed = st.session_state.get("parsed_constraints", {})

    if st.button("Parse with AI") and user_text:
        if client is None:
            st.error("Add your Anthropic API key above to use AI parsing.")
            return parsed

        # Fresh parse — clear players and dismissals from any previous parse
        # so old text doesn't keep re-locking or re-blocking new results.
        for name in list(st.session_state.get("last_llm_locked", set())):
            st.session_state.locked_players.pop(name, None)
        st.session_state.last_llm_locked = set()
        st.session_state.llm_dismissed = set()

        try:
            parsed = parse_nl_input(user_text, client)
            st.session_state.parsed_constraints = parsed
            st.success("Constraints parsed successfully")
        except Exception as e:
            st.error("Couldn't parse that request — try rephrasing, or use manual controls below.")
            st.caption(f"Details: {e}")
            return st.session_state.get("parsed_constraints", {})

    fixed_players = parsed.get("locked_players", [])
    if fixed_players:
        st.caption(f"Detected from text: {', '.join(p['name'] for p in fixed_players)}")
        for i, p in enumerate(fixed_players):
            # name_,role_ = p.get('name'), p.get('role')
            _resolve_llm_player(p.get("name", ""), p.get("role"), i, players_df)

    return parsed


def _resolve_llm_player(candidate_name, candidate_role, idx, players_df):
    if not candidate_name:
        return

    dismissed = st.session_state.setdefault("llm_dismissed", set())
    if candidate_name in dismissed:
        return  # user explicitly removed this one this session — don't re-add it

    if candidate_name in st.session_state.locked_players:
        st.caption(f"'{candidate_name}' is already locked — skipping duplicate mention.")
        return

    try:
        matches = find_player(candidate_name, players_df)
    except Exception as e:
        st.warning(f"Couldn't search for '{candidate_name}'.")
        st.caption(f"Details: {e}")
        return

    if not matches:
        st.warning(f"No exact match for '{candidate_name}'. Add them manually below if you meant someone specific.")
        return

    if len(matches) > 1:
        chosen = st.selectbox(
            f"Multiple matches for '{candidate_name}' — choose one",
            [" "] + matches,
            key=f"llm_disambig_{idx}",
        )
        if chosen == " ":
            return
        matched_name = chosen
    else:
        matched_name = matches[0]

    if matched_name in dismissed:
        return
    
    row = safe_get_player(players_df, matched_name)
    if row is None:
        st.warning(f"Player data missing for {matched_name}.")
        return

    if not can_lock_more():
        st.warning(f"Maximum players already chosen. Skipped **{matched_name}**.")
        return

    if not candidate_role in row['PossiblePositions']+[None]:
        st.warning(f"Player cannot play the specified role. Defaulted to None. Choose from the dropdown list")
        candidate_role = None
    lock_player(matched_name, candidate_role, row, source="llm")


# ---------------------------------------------------------------------------
# MANUAL CONSTRAINTS SELECTION
# ---------------------------------------------------------------------------

def render_manual_block(players_df):
    st.subheader("➕ Add a Player Manually")

    player_names = sorted(players_df["Name"].dropna().unique().tolist())
    choice = st.selectbox("Find a player", [" "] + player_names, key="manual_player_select")

    if choice == " ":
        return

    if choice in st.session_state.locked_players:
        st.info(f"**{choice}** is already locked. Pick a different player, or remove them in the panel on the right.")
        return

    if not can_lock_more():
        st.warning(f"Maximum {MAX_LOCKS} players can be chosen.")
        return

    row = safe_get_player(players_df, choice)
    if row is None:
        st.warning(f"Couldn't find data for {choice}.")
        return

    st.info(f"**{choice}** — €{row.get('WageEUR', 0):,.0f} | Age {row.get('Age')}")
    positions = list(row.get("PossiblePositions") or [])
    role_choice = st.selectbox("Position (optional)", ["None"] + positions, key="manual_role_select")

    if st.button(f"🔒 Lock {choice}", key="manual_lock_button"):
        lock_player(choice, None if role_choice == "None" else role_choice, row, source="manual")
        # If this player was previously dismissed from an AI parse, a fresh
        # manual lock should stick rather than being treated as a dismissal.
        st.session_state.setdefault("llm_dismissed", set()).discard(choice)
        st.rerun()