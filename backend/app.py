from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests as http_requests
import numpy as np
import os
from dotenv import load_dotenv
from groq import Groq, APIStatusError

from backend.nlp_processor import extract_concepts
from backend.memory_store import MemoryStore
from backend.importance_scorer import compute_importance, build_reasons
from backend.rl_environment import MemoryEnv
from backend.rl_agent import QLearningAgent
from backend.consolidator import consolidate

load_dotenv()

app = Flask(__name__, static_folder="../frontend", static_url_path="")
# Configure CORS dynamically
frontend_url = os.getenv("FRONTEND_URL", "https://rl-based-dual-phase-memory-consolidation-system-oszu7eilt.vercel.app/")
allowed_origins = [frontend_url, "http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000"]

CORS(app, resources={
    r"/*": {
        "origins": allowed_origins,
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Initialize Groq Client
# Note: Never hardcode your API key. Use environment variables.
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
GROQ_MODEL = "llama-3.2-3b-preview"

memory = MemoryStore()
agent = QLearningAgent()
env = MemoryEnv()
conversation_history = []
MAX_HISTORY = 4

CONSOLIDATE_EVERY = 3


def generate_response(user_input: str, relevant: list, history: list) -> str:
    """LLM-powered response using Groq Cloud with memory context and history."""

    if relevant:
        memory_context = "\n".join(
            f"- {r['concept']} x{r['frequency']}" for r in relevant[:4]
        )
    else:
        memory_context = "none"

    history_str = ""
    for h in history[-MAX_HISTORY:]:
        history_str += f"U: {h['user'][:80]}\nA: {h['bot'][:80]}\n"

    system_prompt = f"""You are a memory-aware assistant. Answer using ONLY the facts below. Be concise.

Memory: {memory_context}
History:
{history_str}"""

    try:
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            temperature=0.2,
            max_tokens=100,
            top_p=0.8,
            stream=False
        )
        return completion.choices[0].message.content.strip()

    except APIStatusError as e:
        print(f"Groq API Error: {e.status_code} - {e.message}")
        if history:
            return f"Based on our conversation — {history[-1]['bot']}"
        return "I'm having trouble connecting to my brain right now. Please try again in a moment."
    except Exception as e:
        print(f"Unexpected error: {e}")
        if history:
            return f"Based on our conversation — {history[-1]['bot']}"
        if relevant:
            concepts = ", ".join(r["concept"] for r in relevant[:4])
            return f"I remember: {concepts}. What do you need help with?"
        return "I'm processing what you said. Keep going!"


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

    # 1. Extract concepts
    concepts = extract_concepts(user_input)
    memory.update(concepts)

    # 2. Search memory for relevant context
    relevant = memory.search_memory(user_input)

    # 3. Generate response via LLaMA with history
    response = generate_response(user_input, relevant, conversation_history)

    # 4. Store in conversation history
    conversation_history.append({"user": user_input, "bot": response})

    # 5. Compute importance + run RL agent for all working memory units
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

        action_name = env.action_name(action)
        reasons = build_reasons(unit, importance, action)

        memory_details.append({
            "concept": unit["concept"],
            "frequency": unit["frequency"],
            "recency": round(recency, 3),
            "importance": importance,
            "action": action_name,
            "reasons": reasons,
        })

    # 6. Periodic consolidation every N interactions
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


@app.route("/reset", methods=["POST"])
def reset():
    global memory, agent, conversation_history
    memory = MemoryStore()
    agent = QLearningAgent()
    conversation_history = []
    return jsonify({"status": "reset"})


@app.route("/memory", methods=["GET"])
def get_memory():
    units = memory.all_working()
    max_freq = max((u["frequency"] for u in units), default=1)
    enriched = []
    for u in units:
        imp = compute_importance(u, max_freq)
        enriched.append({**u, "importance": imp})
    return jsonify({
        "working": enriched,
        "persistent": memory.all_persistent(),
    })
