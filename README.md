# Dating Sim Demo

A minimal experiment in AI-driven dating simulation.

## Architecture

The game uses two sequential Ollama calls:

1. Interpreter: converts natural-language player instructions into
   structured actions and checks physical possibility.
2. Player confirmation: the player approves or cancels the actions.
3. Narrator: executes the confirmed actions narratively, controls NPC
   reactions and proposes a relationship score change.

Python controls the game state and persists it in JSON.

## Requirements

- Python 3.10+
- Ollama installed and running
- An Ollama model supporting structured JSON output

## Installation

Clone the repository:

```bash
git clone https://github.com/dmillour/datingsim_demo.git
cd datingsim_demo
```

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows:

```powershell
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Download the default model:

```bash
ollama pull llama3.1:8b
```

Start Ollama if it is not already running:

```bash
ollama serve
```

## Run

```bash
streamlit run app.py
```

Open the URL displayed by Streamlit, normally
http://localhost:8501.

## Game state
