import pandas as pd 
import pytest 

from src.search_players import find_player, normalize 


def test_normalize():
    """Verify text normalization removes accents, special chars, and handles spacing."""
    assert normalize("Kylián Mbappé") == "kylian mbappe"
    assert normalize("  Neymar  Jr.  ") == "neymar jr"
    assert normalize("Cristiano-Ronaldo!") == "cristianoronaldo"

def test_find_player():
    """Verify player search matches exact subset tokens correctly."""
    df = pd.DataFrame({
        "Name": ["Lionel Messi", "Lionel Messias", "Neymar Jr", "Cristiano Ronaldo"
                 ,"Ronaldo Cabral",'Ronaldo Vieira']
    })
    
    # Matching exact full word subset
    assert find_player("messi", df) == ["Lionel Messi"]
    assert find_player("lionel", df) == ["Lionel Messi", "Lionel Messias"]
    assert find_player("Mbappe", df) == []
    assert find_player("messsssi",df) == []
    assert set(find_player('Ronaldo',df)) == {"Cristiano Ronaldo","Ronaldo Cabral","Ronaldo Vieira"}

