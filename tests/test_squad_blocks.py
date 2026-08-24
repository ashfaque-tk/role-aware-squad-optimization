import pandas as pd
import pytest
import streamlit as st
 
import squad_blocks
import main


class FakeSessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as e:
            raise AttributeError(name) from e
 
    def __setattr__(self, name, value):
        self[name] = value

@pytest.fixture(autouse=True)
def fresh_session_state(monkeypatch):
    """Every test gets a clean, isolated session_state, and st.warning/
    st.info/etc. are silenced so test output stays readable."""
    fake_state = FakeSessionState(
        locked_players={},
        last_llm_locked=set(),
        llm_dismissed=set(),
    )
    monkeypatch.setattr(st, "session_state", fake_state)
    for fn_name in ("warning", "info", "caption", "success", "error"):
        monkeypatch.setattr(st, fn_name, lambda *a, **k: None)
    return fake_state

@pytest.fixture
def players_df():
    return pd.DataFrame([
        {"Name": "L. Messi", "Age": 36, "WageEUR": 195_000, "PossiblePositions": ["RW", "CAM"]},
        {"Name": "Cristiano Ronaldo", "Age": 39, "WageEUR": 220_000, "PossiblePositions": ["ST"]},
        {"Name": "K. Mbappé", "Age": 25, "WageEUR": 230_000, "PossiblePositions": ["ST", "LW"]},
    ])

def test_can_lock_more_false_at_cap():
    for i in range(squad_blocks.MAX_LOCKS):
        st.session_state.locked_players[f"Player {i}"] = {"role": None, "source": "manual"}
    assert squad_blocks.can_lock_more() is False

def test_lock_player_is_idempotent(players_df):
    row = squad_blocks.safe_get_player(players_df, "L. Messi")
    squad_blocks.lock_player("L. Messi", "RW", row, source="manual")
    squad_blocks.lock_player("L. Messi", "CAM", row, source="llm")  # second call, different args
 
    # First lock wins; second call must not overwrite or duplicate.
    assert len(st.session_state.locked_players) == 1
    assert st.session_state.locked_players["L. Messi"]["role"] == "RW"
    assert st.session_state.locked_players["L. Messi"]["source"] == "manual"

def test_lock_player_at_cap_is_rejected(players_df):
    row = squad_blocks.safe_get_player(players_df, "L. Messi")
    for i in range(squad_blocks.MAX_LOCKS):
        st.session_state.locked_players[f"Filler {i}"] = {"role": None, "source": "manual"}
 
    squad_blocks.lock_player("L. Messi", "RW", row, source="manual")
    assert "L. Messi" not in st.session_state.locked_players

def test_clear_all_locked_resets_everything(players_df):
    row = squad_blocks.safe_get_player(players_df, "L. Messi")
    squad_blocks.lock_player("L. Messi", "RW", row, source="llm")
    st.session_state.llm_dismissed.add("Someone Else")
 
    squad_blocks.clear_all_locked()
 
    assert st.session_state.locked_players == {}
    assert st.session_state.last_llm_locked == set()
    assert st.session_state.llm_dismissed == set()

def test_check_duplicate_role_error_message_when_conflicting():
    st.session_state.locked_players = {"A": {"role": "ST"}, "B": {"role": "ST"}}
    error = main.check_duplicate_role_error()
    assert error is not None
    assert "ST" in error
 