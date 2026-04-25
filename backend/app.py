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

# Environment handling: load_dotenv() only in development
if os.environ.get('FLASK_ENV') == 'development':
    load_dotenv()

# Use absolute paths to avoid "Folder Not Found" errors on Linux/Render
current_dir = os.path.dirname(os.path.abspath(__file__))
static_folder = os.path.join(current_dir, "../frontend/dist")

app = Flask(__name__, static_folder=static_folder, static_url_path="")

# Robust CORS Configuration for Distributed System
# Explicitly allows Vercel frontend to communicate with Render backend
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

# Initialize Groq Client
# Note: API key will be injected via Render Dashboard
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
print(f"DEBUG: GROQ_API_KEY found: {bool(GROQ_API_KEY)}")
if not GROQ_API_KEY:
    print('ERROR: GROQ_API_KEY not found in environment variables')
    print('Please set GROQ_API_KEY in Render Dashboard or local .env file')
else:
    print(f"DEBUG: GROQ_API_KEY length: {len(GROQ_API_KEY)}")
    print(f"DEBUG: GROQ_API_KEY starts with: {GROQ_API_KEY[:10]}...")

try:
    client = Groq(api_key=GROQ_API_KEY)
    print("DEBUG: Groq client initialized successfully")
except Exception as e:
    print(f"ERROR: Failed to initialize Groq client: {e}")
    client = None

GROQ_MODEL = "llama3-8b-8192"
print(f"DEBUG: Using model: {GROQ_MODEL}")

memory = MemoryStore()
agent = QLearningAgent()
env = MemoryEnv()
conversation_history = []
MAX_HISTORY = 4

CONSOLIDATE_EVERY = 3


def generate_response(user_input: str, relevant: list, history: list) -> str:
    """LLM-powered response using Groq Cloud with memory context and history."""
    
    print(f"DEBUG: generate_response called with input: '{user_input[:50]}...'")
    print(f"DEBUG: relevant concepts: {len(relevant) if relevant else 0}")
    print(f"DEBUG: history length: {len(history) if history else 0}")
    print(f"DEBUG: client exists: {bool(client)}")
    
    if not client:
        print("ERROR: Groq client not initialized")
        return "I'm having trouble with my brain connection. Please try again."

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

    print(f"DEBUG: About to call Groq API with model: {GROQ_MODEL}")
    
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
        response = completion.choices[0].message.content.strip()
        print(f"DEBUG: Groq API success, response: '{response[:50]}...'")
        return response

    except APIStatusError as e:
        print(f"DEBUG: Groq API Status Error: {e.status_code} - {e.message}")
        if history:
            return f"Based on our conversation — {history[-1]['bot']}"
        return "I'm having trouble connecting to my brain right now. Please try again in a moment."
    except Exception as e:
        print(f"DEBUG: General Groq Error: {type(e).__name__}: {e}")
        print(f"DEBUG: Error details: {str(e)}")
        # Intelligent fallback using memory context
        if relevant:
            top_concept = relevant[0]['concept']
            return f"I remember your point about {top_concept}, but I am having trouble connecting to my response engine right now."
        return "I've noted what you said, but I'm having trouble generating a response right now."


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/chat", methods=["POST", "OPTIONS"])
def chat():
    print("Request received at /chat")
    if request.method == "OPTIONS":
        print("OPTIONS request received")
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
