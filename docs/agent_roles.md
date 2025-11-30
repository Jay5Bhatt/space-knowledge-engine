Agent Roles & Responsibilities

This project uses a set of focused agents that work together to turn raw space-science text into structured, summarized knowledge. Each agent has a clearly defined role so the overall workflow stays predictable, modular, and easy to evaluate.

1. Orchestrator Agent
Role: Coordinator
Purpose: Controls the full pipeline and manages the overall workflow.

Responsibilities:

Initializes all agents

Runs the full sequence (fetch → analyze → evaluate → summarize → memory)

Logs each run and writes outputs to data/demo_outputs/

Maintains session state for multi-iteration runs

Ensures failures in one item don't break the system

2. Fetcher Agent
Role: Data Ingestion
Purpose: Collects raw text inputs.

Responsibilities:

Reads local sample files in data/samples/

Normalizes each item into a consistent dict format

Provides stubs for real API fetching (arXiv, NASA)

Keeps the ingestion step deterministic and offline-friendly

3. Analyzer Agent
Role: Scientific Text Interpreter
Purpose: Converts unstructured text into structured analysis.

Responsibilities:

Cleans and normalizes text

Splits text into sentences

Extracts numbers, simple measurements, and domain keywords

Identifies “claims” — sentences containing factual statements

Produces analysis dicts used by the evaluator and summarizer

4. Evaluator Agent
Role: Quality Control
Purpose: Scores items and determines what is worth keeping.

Responsibilities:

Applies weighted scoring for keywords, numeric density, measurements, length, and claims

Produces human-readable reasoning for each score

Marks items as passed/failed

Ensures noisy or low-value text does not enter memory

5. Summarizer Agent
Role: Scientific Writer
Purpose: Produces short, readable summaries.

Responsibilities:

Generates local (offline) summaries

Includes a clean optional pathway for Gemini integration

Uses analysis output to highlight keywords and claims

Produces concise briefs that are stored in memory

6. Memory Agent
Role: Archivist
Purpose: Stores structured knowledge for long-term use.

Responsibilities:

Saves processed entries to data/memory.json

Deduplicates by item key

Supports simple keyword retrieval

Runs compaction to trim unnecessary raw text from stored records

Summary
Together, these agents form the following pipeline:

Fetcher → Analyzer → Evaluator → Summarizer → Memory
                  ↑
             Orchestrator
             
Each component focuses on a single responsibility, making the system easier to understand, test, extend, and evaluate.