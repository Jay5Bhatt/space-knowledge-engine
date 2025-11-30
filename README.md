Space Knowledge Engine — Python Multi-Agent System

A modular multi-agent pipeline that ingests space-science text data, analyzes it, evaluates scientific relevance, summarizes key findings (optionally using Gemini), and stores refined knowledge in a persistent memory store.

The system is built to demonstrate real agent workflows: deliberate reasoning, tool use, long-term memory, deterministic evaluation, and clean orchestration — all running locally with optional API upgrades.

🚀 Key Features
Fetcher Agent
Collects data from:

Local sample files (data/samples/*.txt)

Mock Arxiv feed (offline/demo mode)

Mock NASA API (offline/demo mode)

Analyzer Agent
Extracts structured information:

Word & sentence counts

Numeric values

Scientific measurements

Keyword matches

Scientific “claims”

Snippets for summarization

Evaluator Agent
Scores each item with transparent heuristics:

Keyword relevance

Numeric density

Measurement bonus

Claim strength

Length checks & penalties

Items passing the threshold flow deeper into the pipeline.

Summarizer Agent
Two modes:

Local deterministic summary

Gemini-powered summary (if enabled)

Memory Agent
Handles long-term storage:

Saves analysis + summaries

Deduplicates items

Compacts raw text to reduce footprint

Orchestrator Agent
The central controller:

Runs each cycle

Passes data between agents

Logs every run to data/demo_outputs/

Manages robust error handling + observability

Everything works completely offline, with API integrations available when desired.

📂 Project Structure

space-knowledge-engine/
│
├── agents/
│   ├── orchestrator_agent.py
│   ├── fetcher_agent.py
│   ├── analyzer_agent.py
│   ├── evaluator_agent.py
│   └── summarizer_agent.py
│
├── tools/
│   ├── arxiv_fetcher.py
│   ├── nasa_api.py
│   ├── code_execution.py
│   └── parser_utils.py
│
├── data/
│   ├── samples/
│   │   └── example1.txt
│   ├── demo_outputs/
│   │   └── readme_demo_output.json
│   └── memory.json
│
├── docs/
│   ├── agent_roles.md
│   ├── architecture_diagram.png
│   └── workflow_diagram.png
│
├── main.py
├── run_demo.py
├── requirements.txt
└── README.md

🔧 Installation
1. Create a virtual environment
Windows (PowerShell):

python -m venv venv
Set-ExecutionPolicy -Scope Process Bypass
.\venv\Scripts\activate

Mac/Linux:

python3 -m venv venv
source venv/bin/activate

2. Install dependencies

pip install -r requirements.txt

▶️ Run the Demo
Runs a single end-to-end cycle:

python run_demo.py

Outputs written to:

data/demo_outputs/*.json

data/memory.json

▶️ Continuous Mode
Runs multiple cycles with delays:

python main.py --iterations 3 --interval 1

🧠 Optional: Enable Gemini Summarization
To switch summarization from rule-based → Gemini:

1. Create a .env file in project root:

GEMINI_API_KEY=your_key_here

2. Enable Gemini in code

In summarizer_agent.py:

summarizer = SummarizerAgent(use_gemini=True)
If no API key is present, the system automatically falls back to the local summarizer.

📘 Documentation
Agent Roles: docs/agent_roles.md

Architecture Diagram: docs/architecture_diagram.png

Workflow Diagram: docs/workflow_diagram.png

🔭 Example Pipeline Run
Given an input file like:

data/samples/example1.txt

The pipeline:

Reads sample

Extracts measurements & keywords

Scores scientific relevance

Summarizes findings

Saves structured results to memory

💡 Future Work
If extended further, the system can support:

Real Arxiv & NASA API ingestion

PDF ingestion + table extraction

Vector embeddings for semantic memory search

Richer claim extraction using transformer models

A Streamlit dashboard to inspect processed knowledge

📄 License
MIT License