from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests as http_requests
import numpy as np
import os
import traceback
from dotenv import load_dotenv
from groq import Groq, APIStatusError

from backend.nlp_processor import extract_concepts
from backend.memory_store import MemoryStore
from backend.importance_scorer import compute_importance, build_reasons
from backend.rl_environment import MemoryEnv
from backend.rl_agent import QLearningAgent
from backend.consolidator import consolidate

# 1. Environment handling: Only load .env if not in production
if os.environ.get('FLASK_ENV') != 'production':
    load_dotenv()

# 2. Path Handling for Render
current_dir = os.path.dirname(os.path.abspath(__file__))
static_folder = os.path.normpath(os.path.join(current_dir, "../frontend/dist"))

app = Flask(__name__, static_folder=static_folder, static_url_path="")

# 3. Robust CORS for Distributed Systems
# This allows your specific Vercel app AND local development
CORS(app, resources={
    r"/*": {
        "origins": [
            "https://rl-based-dual-phase-memory-consolid.vercel.app",
            "https://rl-based-dual-phase-memory-consolidation-system.vercel.app",
            "http://localhost:3000",
            "http://localhost:5173"
        ],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# 4. Groq Client Initialization with Debugging
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GROQ_MODEL = "llama3-8b-8192" 

client = None
if GROQ_API_KEY:
    try:
        client = Groq(api_key=GROQ_API_KEY)
        print("DEBUG: Groq client initialized.")
    except Exception as e:
        print(f"ERROR: Groq init failed: {e}")
else:
    print("CRITICAL: No GROQ_API_KEY found in environment variables!")

# Global Logic Objects
memory = MemoryStore()
agent = QLearningAgent()
env = MemoryEnv()
conversation_history = []
MAX_HISTORY = 4
CONSOLIDATE_EVERY = 3

def generate_response(user_input: str, relevant: list, history: list) -> str:
    """LLM-powered response with fallback logic."""
    if not client:
        return "System logic is active, but the LLM brain is not initialized. Check API keys."

    # Build Context
    memory_context = "\n".join(f"- {r['concept']}" for r in relevant[:4]) if relevant else "None"
    history_str = "".join([f"U: {h['user']}\nA: {h['bot']}\n" for h in history[-MAX_HISTORY:]])

    system_prompt = f"You are a memory-aware assistant. Use these facts: {memory_context}. History: {history_str}"

    try:
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            temperature=0.2,
            max_tokens=150
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"LLM Error: {e}")
        # Safe Fallback: Check if relevant exists before indexing
        if relevant and len(relevant) > 0:
            return f"I've noted that. I'm focusing on your mention of '{relevant[0]['concept']}'."
        return "I've processed your message and updated my RL memory model."

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/chat", methods=["POST", "OPTIONS"])
def chat():
    if request.method == "OPTIONS":
        return "", 200
    
    global conversation_history
    data = request.json
    user_input = data.get("message", "").strip()
    
    if not user_input:
        return jsonify({"error": "Empty message"}), 400

    # RL Logic Pipeline
    concepts = extract_concepts(user_input)
    memory.update(concepts)
    relevant = memory.search_memory(user_input)
    
    # LLM Step
    response = generate_response(user_input, relevant, conversation_history)
    conversation_history.append({"user": user_input, "bot": response})

    # RL Agent Learning Step
    units = memory.all_working()
    max_freq = max((u["frequency"] for u in units), default=1)
    memory_details = []

    for unit in units:
        importance = compute_importance(unit, max_freq)
        freq_norm = unit["frequency"] / max_freq
        recency = unit.get("recency_score", 0.0)

        state = np.array([freq_norm, recency, importance], dtype=np.float32)
        env.set_state(freq_norm, recency, importance)
        action = agent.choose_action(state)
        _, reward, _, _, _ = env.step(action)
        agent.learn(state, action, reward, state)

        memory_details.append({
            "concept": unit["concept"],
            "frequency": unit["frequency"],
            "importance": importance,
            "action": env.action_name(action),
            "reasons": build_reasons(unit, importance, action),
        })

    consolidation_log = []
    if memory.interaction_count % CONSOLIDATE_EVERY == 0:
        consolidation_log = consolidate(memory, agent)

    return jsonify({
        "response": response,
        "memory_details": memory_details,
        "consolidation_log": consolidation_log,
        "agent_stats": agent.stats(),
        "persistent_memory": memory.all_persistent(),
    })

# Main entry point for Render
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)