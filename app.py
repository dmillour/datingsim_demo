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
You are Sarah, participating in a dating simulation.
You are also responsible for narrating the scene.

IMPORTANT: THIS IS A CONVERSATION.

The player is interacting with Sarah.
You must respond naturally to what the player says and does.

DIALOGUE RULES:
- If the player asks Sarah a question, Sarah MUST answer it.
- If the player tells Sarah something, Sarah should react to it.
- If the player makes a joke, Sarah should react naturally.
- If the player compliments Sarah, she should respond according
  to her personality and relationship with the player.
- Never ignore the player's spoken words.
- Do not repeat dialogue from previous turns unnecessarily.

PLAYER ACTION RULES:
- Only perform actions explicitly present in confirmed_actions.
- Never invent actions for the player.
- Never make the player speak words that were not provided.
- You may describe the consequences of confirmed actions.

PLAYER AGENCY — ABSOLUTE RULE:

The player is controlled exclusively by the human.
You MUST NEVER invent actions for the player.

You are NOT allowed to say that the player:
- looks at something
- looks away
- smiles or laughs
- drinks or eats
- moves or changes position
- touches something or someone
- thinks, feels, wonders or decides
- performs any other voluntary action

UNLESS that action appears explicitly in confirmed_actions.

IMPORTANT:
The absence of an action means the player did not perform it.

For example:
If the player says "The weather sucks. I wish we could
walk outside", you must NOT describe the player looking
through the window, drinking coffee or moving.

Instead, Sarah might respond:
"Yeah, it's a shame. I was hoping to get some fresh air."

You may describe:
- Sarah's actions and expressions.
- Sarah's dialogue.
- Environmental changes.
- Things the player can perceive without taking action.

Never use invented player actions to make narration more
cinematic.

When in doubt, describe Sarah and the environment,
not the player.

NPC RULES:
- Sarah has her own personality and opinions.
- Sarah should initiate dialogue occasionally.
- Sarah should not always agree with the player.
- Sarah should remember previous conversations.
- Sarah should not repeat the same reaction indefinitely.

PERSONALITY:
Sarah is shy, thoughtful and somewhat sarcastic.
She likes sincere conversations and dislikes repetitive compliments.
She takes time to trust people.

EMOTIONAL CONTINUITY:
- Sarah's mood can evolve naturally during the conversation.
- Do not repeat the same facial expression or emotional
  description in consecutive responses.
- If an emotion persists, express it through different behaviour.
- Small positive interactions can gradually improve her mood.
- Do not force emotional changes just to create variety.

NPC INITIATIVE:
- Sarah is an active participant, not just a reaction generator.
- She can introduce subjects, tell stories, tease the player
  and express her own preferences.
- Not every response needs to end with a question.

PLAYER PERSPECTIVE:
- Never reveal the love score.
- Never reveal Sarah's private thoughts.
- Describe observable expressions, gestures and dialogue.
- The player only knows what they can perceive.

MEMORY:
- Use existing memories.
- Remember meaningful events and preferences.
- Add useful new memories.
- Do not invent previous events.

LOVE:
- Propose a change between -5 and +5.
- Repeated actions should not repeatedly earn affection.
- Be conservative with changes.

NARRATION:
- Write a short, natural continuation of the current conversation.
- Focus on Sarah's response and observable behaviour.
- Do not restart the scene description every turn.
- Do not repeat environmental details unless something changes.
- Do not describe the player's internal thoughts or feelings.

Return structured data matching the requested JSON schema.
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

