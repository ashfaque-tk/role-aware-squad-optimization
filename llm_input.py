import anthropic
import os 

from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_KEY_KEY"))  # reads ANTHROPIC_API_KEY from env

tools = [{
    "name": "extract_squad_constraints",
    "description": "Extract football squad constraints from a user's natural language request",
    "input_schema": {
        "type": "object",
        "properties": {
            "budget": {"type": ["number", "null"], "description": "Budget in euros, e.g. 500000. Null if not stated."},
            "style": {"type": ["string", "null"], "enum": ["attack", "defend", "balanced", None]},
            "min_age": {"type": ["number", "null"],
                    "description": "Minimum average age of the squad."},

            "max_age": {"type": ["number", "null"],
                    "description": "Maximum average age of the squad."
                },
            "formation": {
                "type": ["array", "null"],
                "items": {"type": "integer"},
                "minItems": 3, "maxItems": 3,
                "description": "[defenders, midfielders, forwards], e.g. [4,3,3]. Null if not specified."
            },
            "locked_players": { "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "role": {
                                            "type": ["string", "null"],
                                            "enum": ["GK","CB","LB","RB","LWB","RWB","CDM","CM","CAM","LM","RM","LW","RW","ST","CF", None]
                                        }
                                    },
                                    "required": ["name", "role"]
                                }
                            }
            # "locked_players": {
            #     "type": "array",
            #     "items": {"type": "string"},
            #     "description": "Player names mentioned by the user, as written. Empty array if none."
            # }
        },
        "required": ["budget", "style", "min_age","max_age" ,"formation", "locked_players"]
    }
}]

def parse_nl_input(user_text):
    messages = [{"role": "user", "content": user_text}]
    response = client.messages.create(
        model='claude-sonnet-5',
        max_tokens=1000,
        thinking={'type': 'disabled'},
        tools=tools,
        tool_choice={"type": "tool", "name": "extract_squad_constraints"},
        messages=messages
    )
    tool_block = next(b for b in response.content if b.type == "tool_use")
    result = tool_block.input
    if result.get("formation") is None:
        result["formation"] = [4, 3, 3]
    return result


message = 'team with Neymar with min age of 32'

print(parse_nl_input(message))