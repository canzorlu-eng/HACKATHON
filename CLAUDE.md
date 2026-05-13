# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Project:** HIWALOY  
**Meaning:** “How It Will ACTUALLY Look On You”  
**Project Type:** AI-powered fashion fit & purchase risk analysis platform  
**Primary Language:** Turkish (ALL user-facing inputs/outputs MUST be Turkish)  
**Reference Document:** The implementation MUST follow the SRS(@HIWALOY_FULL_SRS.pdf) document as the source of truth. First of all you should examine it to get our aim

---

# IMPORTANT PRODUCT CONTEXT

HIWALOY is NOT:
- a generic AI stylist chatbot
- a virtual try-on clone
- a fashion recommendation toy project

HIWALOY IS:
- an AI-powered purchase confidence system
- a fit prediction and return-risk reduction platform
- a multimodal reasoning system
- an explainable AI shopping assistant

The system's primary goal is:
> Help users understand how clothing will ACTUALLY fit and appear on THEIR body before purchase.

The system should reduce:
- wrong size purchases
- fit mismatch
- purchase regret
- e-commerce return rates

The project MUST prioritize:
1. explainability
2. relevance
3. realistic reasoning
4. trustworthiness
5. low hallucination rate

---

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### HIWALOY-specific requirements

Before implementing ANY AI feature:
- Explain WHY the feature needs AI.
- Explain whether the feature truly requires:
  - LLM reasoning
  - RAG
  - multimodal processing
  - agentic workflow
- Avoid fake AI usage.

Before implementing any recommendation:
- Define:
  - input
  - reasoning steps
  - confidence calculation
  - uncertainty handling

Never silently invent:
- body metrics
- fashion preferences
- clothing attributes
- sizing information
- product metadata

If data is uncertain:
- explicitly communicate uncertainty.

Example:
GOOD:
> "Confidence is low because the uploaded image angle limits shoulder estimation."

BAD:
> "You should buy size M."

---

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### HIWALOY-specific simplicity rules

DO NOT:
- build full virtual try-on systems
- build realistic cloth simulation systems
- build advanced body mesh reconstruction systems
- build production-grade avatar pipelines
- build full social features
- build marketplace systems
- build live scraping infrastructure
- build massive product ingestion pipelines
- build production-scale recommendation engines

Hackathon scope ONLY.

The MVP should focus ONLY on:
- body analysis
- garment analysis
- fit reasoning
- size recommendation
- purchase risk prediction
- community insight retrieval

Avoid:
- unnecessary microservices
- overengineered abstractions
- premature optimization
- complex rendering pipelines
- GPU-heavy browser logic

Prefer:
- clean pipelines
- deterministic flows
- understandable prompts
- explainable outputs
- lightweight visualization systems

IMPORTANT:
The visual layer exists to SUPPORT the AI reasoning system.

The product's value comes from:
- reasoning
- explainability
- purchase confidence
- risk prediction

NOT from flashy visuals.

---

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

### HIWALOY-specific engineering rules

When modifying prompts:
- preserve existing response format
- preserve Turkish output structure
- preserve explainability

When modifying AI pipelines:
- explain why the change improves:
  - accuracy
  - latency
  - hallucination resistance
  - user trust

Never rewrite entire agent flows unnecessarily.

When modifying frontend visuals:
- maintain minimal design consistency
- avoid adding unnecessary animation systems
- prioritize clarity over visual complexity

---

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:

1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

### HIWALOY-specific success criteria

Every AI feature MUST be verifiable through:
- explainability
- confidence score
- deterministic formatting
- realistic reasoning

Success is NOT:
- "model answered something"

Success IS:
- relevant
- explainable
- uncertainty-aware
- user-trustworthy
- grounded in provided data

Frontend success criteria:
- clean interaction flow
- understandable AI reasoning
- responsive animations
- smooth upload experience
- premium but lightweight UX

---

# PROJECT ARCHITECTURE

## High-Level Architecture

Architecture Style:
- AI-first modular architecture
- lightweight service-oriented backend
- NOT traditional MVC-heavy architecture

Frontend:
- Next.js App Router
- TailwindCSS
- shadcn/ui
- Framer Motion
- Three.js (minimal usage only)

Backend:
- FastAPI (Python)

AI Layer:
- Gemini API
- LangChain
- LangGraph

Databases:
- PostgreSQL
- ChromaDB

Deployment:
- Vercel (frontend)
- Railway / Render (backend)

Infrastructure:
- Docker
- Docker Compose

---

# FRONTEND ARCHITECTURE RULES

Frontend priorities:
1. clean UX
2. AI explainability
3. upload simplicity
4. premium feel
5. responsiveness

The frontend should feel:
- modern
- minimal
- intelligent
- smooth
- trustworthy

DO NOT:
- create gaming-style interfaces
- create cyberpunk dashboards
- overload the screen
- use excessive glassmorphism
- create distracting animations

---

# THREE.JS & BLENDER RULES

Three.js MAY be used ONLY for:
- lightweight mannequin visualization
- subtle interactive body silhouettes
- floating UI objects
- premium landing animations
- fit-zone highlighting
- lightweight transitions

Three.js MUST NOT be used for:
- realistic cloth simulation
- advanced physics systems
- full body reconstruction
- metaverse-like environments
- heavy GPU rendering
- production virtual try-on systems

Blender assets MAY be used for:
- static mannequin assets
- lightweight body meshes
- optimized visual components

DO NOT:
- create complex rigging pipelines
- create animation-heavy workflows
- build full avatar systems

IMPORTANT:
3D is ONLY a visual enhancement layer.

The core value remains:
- fit prediction
- reasoning
- purchase confidence
- return-risk reduction

---

# CORE SYSTEM MODULES

## 1. User Profile Module

Responsibilities:
- collect user data
- store body-related preferences
- manage analysis history

Inputs:
- height
- weight
- fit preference
- body image

Outputs:
- normalized user profile

---

## 2. Body Analyzer Agent

Responsibilities:
- analyze body proportions
- estimate fit tendencies
- extract silhouette-related insights

IMPORTANT:
- NEVER insult users
- NEVER generate offensive descriptions
- NEVER use negative body terminology

GOOD:
> "Relaxed fit clothing may suit your proportions better."

BAD:
> "You are overweight."

The agent should:
- remain neutral
- remain respectful
- focus on fit behavior
- avoid attractiveness judgments

---

## 3. Garment Analyzer Agent

Responsibilities:
- analyze clothing screenshots/images
- detect:
  - fit type
  - garment category
  - fabric clues
  - oversize/slim/regular cuts

The agent should reason visually.

DO NOT hardcode all logic.

The garment analyzer should prioritize:
- explainability
- visible garment characteristics
- realistic uncertainty handling

---

## 4. Review Intelligence Agent (RAG)

Responsibilities:
- retrieve customer reviews
- summarize complaint patterns
- identify sizing issues

Data Sources:
- preprocessed review datasets
- embedded review chunks
- manually curated examples

DO NOT:
- build real-time scraping infrastructure for MVP

RAG goals:
- identify:
  - sizing complaints
  - fabric complaints
  - fit mismatch patterns
  - quality concerns

The RAG pipeline should prioritize:
- relevance
- concise outputs
- low hallucination rate
- grounded retrieval

---

## 5. Fit Recommendation Agent

Responsibilities:
- combine:
  - body analysis
  - garment analysis
  - review insights

Outputs:
- recommended size
- fit explanation
- confidence score

Every recommendation MUST explain:
- WHY
- uncertainty
- possible issues

Example:
> "M beden öneriliyor çünkü marka büyük kalıplı ve omuz genişliğiniz için L fazla bol durabilir."

The recommendation system should NEVER:
- sound overly certain
- invent unsupported fit claims
- make subjective beauty judgments

---

## 6. Purchase Risk Agent

Responsibilities:
- estimate dissatisfaction probability
- identify return risks

Risk examples:
- sleeve length risk
- tight neck opening
- oversized appearance mismatch
- low stretch fabric risk

Output should ALWAYS include:
- risk level
- explanation
- confidence

The risk engine should focus on:
- practical purchase risks
- fit mismatch likelihood
- realistic user expectations

---

# LANGGRAPH REQUIREMENTS

LangGraph MUST be used meaningfully.

DO NOT create fake agent workflows.

Required graph flow:

1. User Input
2. Intent Validation
3. Body Analysis
4. Garment Analysis
5. Review Retrieval
6. Recommendation Generation
7. Risk Evaluation
8. Final Response Formatting

Parallel execution is encouraged where logical.

Example:
- body analysis and garment analysis may run concurrently.

The graph should prioritize:
- deterministic execution
- explainability
- modularity
- debugging simplicity

---

# GEMINI API REQUIREMENTS

Gemini MUST be used for:
- multimodal reasoning
- image understanding
- structured Turkish output
- fit reasoning

DO NOT:
- use Gemini only as a generic chatbot.

Use structured prompts.

Preferred outputs:
- JSON
- schema-constrained responses
- deterministic formatting

The model should:
- express uncertainty
- avoid overconfidence
- avoid unsupported assumptions
- remain grounded in image evidence

---

# LANGUAGE REQUIREMENTS

CRITICAL:
ALL user-facing outputs MUST be Turkish.

Internal code/comments may remain English.

Examples:
- prompts → English allowed
- schemas → English allowed
- UI text → Turkish REQUIRED
- AI responses → Turkish REQUIRED

DO NOT mix languages in user-facing outputs.

The UI tone should feel:
- modern
- natural
- premium
- concise

Avoid:
- robotic translations
- excessive technical jargon
- unnatural Turkish phrasing

---

# UI/UX REQUIREMENTS

The UI should feel:
- premium
- minimal
- modern
- trustworthy

DO NOT:
- overload the interface
- create cyberpunk dashboards
- use excessive animations

Main UI sections:
- Upload Area
- AI Analysis Progress
- Recommendation Card
- Risk Analysis
- Community Insights
- Confidence Score

Preferred UX behavior:
- smooth transitions
- progressive analysis feedback
- responsive uploads
- clear recommendation hierarchy

Recommended libraries:
- Framer Motion
- shadcn/ui
- TailwindCSS

---

# AI OUTPUT REQUIREMENTS

Every recommendation MUST contain:

## 1. Recommended Size

Example:
> Önerilen Beden: M

---

## 2. Confidence Score

Example:
> Güven Skoru: %81

---

## 3. Explanation

Example:
> Marka büyük kalıplı olduğu için L beden fazla bol durabilir.

---

## 4. Risk Analysis

Example:
> Kol boyu beklediğinizden uzun gelebilir.

---

## 5. Community Insight

Example:
> Benzer kullanıcılar kumaşın ince olduğunu belirtmiş.

---

# PROMPT ENGINEERING RULES

Prompts MUST:
- reduce hallucinations
- avoid overconfidence
- request explicit uncertainty handling
- avoid subjective beauty judgments

NEVER:
- rate attractiveness
- judge physical appearance negatively
- generate harmful body commentary

The AI is a:
- fit advisor
- purchase assistant

NOT:
- a beauty judge

The prompts should encourage:
- grounded reasoning
- explainability
- confidence scoring
- realistic outputs

---

# DATASET RULES

Use:
- small curated datasets
- realistic examples
- deterministic metadata

DO NOT:
- simulate massive production datasets
- invent unsupported attributes

Preferred MVP scale:
- 50-200 clothing items
- 200-1000 review chunks

Enough for hackathon demonstrations.

Dataset quality matters more than dataset size.

---

# TESTING REQUIREMENTS

Test:
- invalid image uploads
- unsupported formats
- empty review retrieval
- low-confidence predictions
- hallucination edge cases

Verify:
- Turkish output correctness
- deterministic formatting
- confidence score presence
- explanation presence

Frontend testing should include:
- upload flow
- responsive layouts
- animation smoothness
- mobile rendering

---

# PERFORMANCE REQUIREMENTS

Target:
- recommendation pipeline < 10 seconds
- review retrieval < 5 seconds
- responsive UI interactions

Hackathon optimization priorities:
1. reliability
2. demo stability
3. explainability

NOT:
- hyperscale optimization

Three.js rendering should remain lightweight.

Avoid:
- unnecessary GPU load
- large 3D assets
- excessive shaders

---

# DOCKER & CONTAINERIZATION REQUIREMENTS

The project MUST support containerized deployment.

Docker should be used for:
- backend packaging
- frontend packaging
- environment consistency
- simplified deployment
- local development setup

Docker Compose should orchestrate:
- frontend service
- backend service
- PostgreSQL
- ChromaDB

Requirements:
- containers should remain lightweight
- multi-stage builds are preferred
- environment variables must be externalized
- secrets must NOT be hardcoded into images

The Docker setup should prioritize:
1. fast local setup
2. reproducible environments
3. hackathon demo stability
4. simple deployment workflow

DO NOT:
- overengineer Kubernetes infrastructure
- introduce unnecessary orchestration complexity
- optimize for hyperscale production traffic

---

# SECURITY & PRIVACY

User body images are sensitive.

Requirements:
- do not expose uploaded images publicly
- avoid unnecessary retention
- avoid logging sensitive image data
- securely store user metadata

DO NOT:
- use images outside analysis scope

The MVP should minimize:
- stored biometric-like data
- unnecessary image persistence
- sensitive logging

---

# MVP BOUNDARY (VERY IMPORTANT)

The MVP DOES NOT include:
- full virtual try-on
- realistic cloth simulation
- advanced 3D avatar systems
- social media features
- influencer integrations
- payment systems
- live marketplace integrations
- full fashion recommendation engine

Stay focused on:
- fit prediction
- purchase confidence
- return-risk reduction

---

# FINAL ENGINEERING PRINCIPLE

The product should always answer:

> "How will this ACTUALLY look on ME?"

NOT:
> "Does this look good in general?"

Every feature should reinforce:
- personalization
- realism
- trust
- explainability
- purchase confidence


## Model Usage Policy

- Use Claude Opus ONLY for:
  - system design
  - architecture planning
  - SRS interpretation
  - complex reasoning

- Use Claude Sonnet for:
  - all code generation
  - implementation
  - refactoring
  - debugging
  - testing

- Never use Opus for routine coding tasks
- Prefer minimal-cost model unless reasoning complexity requires escalation


# RUFLO / SWARM USAGE POLICY

RuFlo MUST be used for multi-agent coordination when tasks involve:
- architecture review
- code review
- cross-module implementation

For implementation tasks:
- Use Claude Sonnet as the main coding model.
- Use RuFlo swarm to delegate supporting review work:
  - chef agent: orchestrate all agents
  - developer agent: implement logic, code
  - reviewer agent: code quality and requirement compliance
  - researcher/planner agent: edge-case analysis when needed

Do NOT use RuFlo swarm for trivial one-file edits or simple copy/text changes.

Before completing a major feature, Claude must run or simulate a RuFlo-backed review pass covering:
1. SRS compliance
2. Turkish user-facing output correctness


# Remainder

Your code will be reviewed by CODEX