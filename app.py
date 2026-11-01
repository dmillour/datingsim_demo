import json
from pathlib import Path

import ollama
import streamlit as st
from pydantic import BaseModel, Field


# --------------------------------------------------
# Configuration
# --------------------------------------------------

OLLAMA_HOST="http://localhost:9999"
MODEL = "llama3.1:8b"
SAVE_FILE = Path("game_state.json")

client = ollama.Client(host=OLLAMA_HOST)

st.set_page_config(page_title="Dating Sim", page_icon="💕")
st.title("💕 Dating Sim Prototype")


# --------------------------------------------------
# AI response schemas
# --------------------------------------------------

class Action(BaseModel):
    type: str
    target: str
    content: str = ""


class Interpretation(BaseModel):
    valid: bool
    actions: list[Action]
    explanation: str = ""


class Narration(BaseModel):
    narration: str
    love_delta: int = Field(ge=-5, le=5)
    memories: list[str] = []


# --------------------------------------------------
# Game state
# --------------------------------------------------

def new_game():
    return {
        "love": 20,
        "scene": (
            "You are sitting across from Sarah in a quiet café. "
            "It is a rainy afternoon. Sarah is drinking tea."
        ),
        "personality": (
            "Sarah is shy, thoughtful and somewhat sarcastic. "
            "She likes sincerity and dislikes repetitive compliments."
        ),
        "memories": [],
        "history": [
            {
                "role": "assistant",
                "content": "Sarah smiles at you. 'How was your day?'"
            }
        ],
    }


def load_game():
    if SAVE_FILE.exists():
        return json.loads(SAVE_FILE.read_text(encoding="utf-8"))
    state = new_game()
    save_game(state)
    return state


def save_game(state):
    SAVE_FILE.write_text(
        json.dumps(state, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


if "game" not in st.session_state:
    st.session_state.game = load_game()

if "pending" not in st.session_state:
    st.session_state.pending = None

game = st.session_state.game


# --------------------------------------------------
# AI helper
# --------------------------------------------------

def ask_ai(system_prompt, context, schema):
    response = client.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": json.dumps(context, ensure_ascii=False),
            },
        ],
        format=schema.model_json_schema(),
    )
    return schema.model_validate_json(response.message.content)


# --------------------------------------------------
# Phase 1: Interpret player intention
# --------------------------------------------------

INTERPRETER_PROMPT = """
You interpret player instructions for a text dating sim.

Extract all individual actions from the player's instruction.
Preserve the player's intended meaning and exact spoken words.

Check whether actions are physically possible in the current scene.
Reject impossible actions, such as grabbing the moon.

Touching another person is physically possible, but their reaction
and consent are not guaranteed.

Do not execute actions.
Do not narrate.
Do not modify the world.
Do not invent additional actions.

Return structured data matching the requested schema.
"""


def interpret(player_input):
    return ask_ai(
        INTERPRETER_PROMPT,
        {
            "scene": game["scene"],
            "player_input": player_input,
            "recent_history": game["history"][-10:],
        },
        Interpretation,
    )


# --------------------------------------------------
# Phase 2: Execute confirmed actions
# --------------------------------------------------

NARRATOR_PROMPT = """
You are the narrator of a text-based dating sim.

The player has confirmed the actions provided.
Resolve them in the current scene.

You control Sarah's reactions and dialogue.
Respect her personality and memories.

PLAYER PERSPECTIVE:
- Never reveal the hidden love score.
- Never reveal Sarah's private thoughts as facts.
- Describe observable behaviour, dialogue and expressions.
- The player only knows what they can perceive.

NPC AUTONOMY:
- Sarah has her own personality and boundaries.
- Player actions do not dictate Sarah's reactions.
- Do not make Sarah automatically agree with everything.

MEMORY:
- Remember meaningful events and preferences.
- Do not reward repetitive compliments indefinitely.
- Add only useful new memories.

LOVE:
- Propose a change between -5 and +5.
- Be conservative.
- Repeated actions should not repeatedly earn affection.

Write natural, immersive narration.
Return structured data matching the requested schema.
"""


def execute(actions):
    return ask_ai(
        NARRATOR_PROMPT,
        {
            "scene": game["scene"],
            "personality": game["personality"],
            "love": game["love"],
            "memories": game["memories"],
            "recent_history": game["history"][-10:],
            "confirmed_actions": actions,
        },
        Narration,
    )



# --------------------------------------------------
# Interface
# --------------------------------------------------

st.subheader("Sarah")
st.caption(game["scene"])

# Display conversation
for message in game["history"]:
    with st.chat_message(message["role"]):
        st.write(message["content"])

st.divider()

# Player input
player_input = st.chat_input("What would you like to do?")

if player_input:
    try:
        with st.spinner("Interpreting your actions..."):
            result = interpret(player_input)

        st.session_state.pending = {
            "input": player_input,
            "valid": result.valid,
            "actions": [a.model_dump() for a in result.actions],
            "explanation": result.explanation,
        }
        st.rerun()

    except Exception as error:
        st.error(f"Interpreter error: {error}")


# Confirmation
pending = st.session_state.pending

if pending:
    st.subheader("Proposed actions")

    if pending["valid"]:
        for action in pending["actions"]:
            st.write(f"**{action['type']}** — {action['target']}")
            if action["content"]:
                st.caption(action["content"])

        if st.button("Confirm actions", type="primary"):
            try:
                with st.spinner("Sarah is responding..."):
                    result = execute(pending["actions"])

                game["love"] = max(
                    0,
                    min(100, game["love"] + result.love_delta),
                )

                for memory in result.memories:
                    if memory not in game["memories"]:
                        game["memories"].append(memory)

                game["memories"] = game["memories"][-30:]

                game["history"].append({
                    "role": "user",
                    "content": pending["input"],
                })
                game["history"].append({
                    "role": "assistant",
                    "content": result.narration,
                })

                game["history"] = game["history"][-40:]

                save_game(game)
                st.session_state.pending = None
                st.rerun()

            except Exception as error:
                st.error(f"Narrator error: {error}")

    else:
        st.warning(pending["explanation"] or "Impossible action.")

    if st.button("Cancel"):
        st.session_state.pending = None
        st.rerun()


# Sidebar
with st.sidebar:
    st.header("Game")
    st.caption("Relationship score is hidden.")

    if st.button("Restart game"):
        st.session_state.game = new_game()
        save_game(st.session_state.game)
        st.session_state.pending = None
        st.rerun()

