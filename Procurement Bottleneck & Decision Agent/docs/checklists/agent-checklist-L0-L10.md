# Agent Checklist — Full Enriched Master List (L2)

**10 Pillars · 60 L1 Items · L2 Descriptions & SAP Standard Content Links**
*Source: Agent_Checklist_Master_List (2).md — authoritative L0/L1 structure preserved exactly*
*L2 layer: crisp description + KG-sourced SAP references added to every item*

---

> **Link key**
> Links prefixed `idea-agent` are the provided Idea2Value tool URL.
> All other links are SAP Help Portal, SAP API Business Hub, or SAP Trust Centre.

---

## L0-1 · AI Feature & Agent Onboarding Governance
*Structured intake and classification for every AI feature or agent entering the product lifecycle.*

---

### 1.0 — Idea2Value
Converts an unstructured agentic AI idea into a CXO-ready business value case through a guided Socratic conversation with an AI agent grounded in **14+ SAP Enterprise Knowledge sources**. In under ten minutes, any SAP advisor, consultant, or customer can produce a CXO-grade use case — with persona clarity, pain quantification, SAP module fit, and defensible ROI — validated against the customer's actual SAP landscape and priced against real cost-per-decision economics. The output is a structured document covering all five stages with cited sources, packaged for leadership buy-in regardless of the author's specialisation.

**Five stages and their gates:**

| Stage | What it captures |
|---|---|
| **Discovery** | Raw idea intake, target persona, and primary pain point |
| **Grounding** | SAP module and landscape fit, validated against the customer's actual system footprint |
| **Tools** | Agentic tool and capability mapping — which SAP and third-party capabilities satisfy the use case |
| **ROI** | Cost-per-decision economics, value quantification, and investment case |
| **TRUST** | Responsible AI alignment, regulatory risk, and governance requirements |

Each stage gate requires documented evidence before the case advances. The completed Idea2Value document is the primary traceability record consumed by ESCE sign-off (1.5).

---

### 1.1 — Feature Type Classification
Classify the AI feature as embedded AI, generative AI (conversational), agentic, or process automation before any design work begins. Classification is a routing decision: each type activates a distinct sub-checklist within the AI Golden Path (1.3), determines LLM selection depth, and sets the Responsible AI evaluation tier. Incorrect classification is the most common cause of late-stage rework; confirm with the AI architecture guild before proceeding.

> **References:** [Golden Path Concept](https://architecture.learning.sap.com/docs/ai-golden-path)

---

### 1.2 — Commercial Tier Determination
Assign the feature to a SAP Business AI commercial tier (included, optional, or premium) based on LLM cost profile, expected usage volume, and value delivery model. Tier determination gates the Floor Price Impact Review (4.3). Incorrect tier assignment is one of the most common sources of commercial model rework after release; validate against LLM Calculator output (4.1) before submission.

> **References:** [SAP Business AI Pricing Model (video)](https://www.sap.com/products/artificial-intelligence/ai-units.html) · [SAP AI Core Pricing](https://discovery-center.cloud.sap/serviceCatalog/sap-ai-core/?region=all&tab=service_plan&commercialModel=payg)

---

### 1.3 — AI Golden Path
SAP's prescribed end-to-end governance pathway for AI features, consolidating security, Responsible AI, commercialization, and quality requirements into a single tracked workflow. Features on the Golden Path receive streamlined approval routing and a pre-validated integration architecture. Deviations require a documented exception with sign-off from the AI governance function; undocumented deviations are a release blocker.

> **References:** [Golden Path Concept](https://architecture.learning.sap.com/docs/ai-golden-path)

---

### 1.4 — Document - AI Commercialization Tracker
Perform commercial calculations to determine the cost-optimal processing path based on expected user data volume: compare per-page pricing for standard Document AI services against the volume economics of GDH accelerators. Document the break-even threshold, selected approach, and pricing assumptions before any customer-scale processing begins. The chosen track drives the billing anchor for AI Scenario Metering Integration (4.2).

> **References:** [SAP Business AI Pricing Model (video)](https://www.sap.com/products/artificial-intelligence/ai-units.html)

---

### 1.5 — SAP BTP Data and AI Architect Group Support
Engage the central SAP BTP Data and AI Architect Group early to identify the architectural support needs for this project. Raise a callout to the region architect group covering: solution design review, AI platform guidance, integration architecture, and any escalation paths required for delivery. Architect group involvement must be confirmed before the build phase begins.

---

## L0-2 · LLM Selection & Benchmarking
*Select the right foundational model per use case, balancing performance and cost.*

---

### 2.1 — Test Data Preparation & Submission
Curate a representative evaluation dataset covering the agent's intended use cases, edge cases, multi-language inputs (where applicable), and adversarial prompts. Dataset must be approved and submitted to the Benchmarking Agent before automated evaluation begins; production customer data is prohibited — use synthetic or masked data only. Dataset quality directly determines the reliability of the model selection decision.

> **References:** [Generative AI Hub](https://www.sap.com/products/artificial-intelligence/generative-ai-hub.html)

---

### 2.2 — Automated Multi-Model Evaluation
Run the approved test dataset against all candidate models via the Benchmarking Agent to produce objective, comparable quality and latency scores. Evaluation covers accuracy, token efficiency, latency, and safety. Results are recorded in the Internal Evaluation Dashboard (2.4) and form the evidence base for the Frontier Model Justification Gate (2.6).

> **References:** [Generative AI Hub](https://www.sap.com/products/artificial-intelligence/generative-ai-hub.html)

---

### 2.3 — Generative AI Evaluation Roadmap
The forward-looking plan for SAP's model evaluation capabilities, covering planned improvements to benchmarking methodology, new model integrations, automated quality scoring, and agentic task-completion rate metrics. Teams track the roadmap so that upcoming mandatory evaluation criteria are incorporated into test data design before they become gate requirements at GA.

> **References:** [Generative AI Hub](https://www.sap.com/products/artificial-intelligence/generative-ai-hub.html)

---

### 2.4 — Internal Evaluation Dashboard
The Internal Evaluation Dashboard is the internal reporting surface where multi-model benchmarking results are visualised, compared, and archived for audit. Results are immutable after submission. Dashboard output is the canonical evidence referenced during the Frontier Model Justification Gate (2.6).

> **References:** [AI Launchpad](https://help.sap.com/docs/ai-launchpad/sap-ai-launchpad/what-is-sap-ai-launchpad?locale=en-US)

---

### 2.5 — Ongoing Model Version Re-evaluation
Re-run the full benchmarking suite whenever the underlying model receives a provider-side update, safety-tuning patch, or infrastructure swap — re-evaluation is not optional. Any quality regression against the production baseline must be resolved before the updated model reaches customer production tenants. Results feed the Model Update & Retraining Governance workflow (2.7) and are the primary trigger for the Model Drift Detection alert (10.3).

> **References:** [AI Launchpad](https://help.sap.com/docs/ai-launchpad/sap-ai-launchpad/what-is-sap-ai-launchpad?locale=en-US)

---

### 2.6 — Frontier Model Justification Gate
For each fully agentic decision step, document why a frontier model is required over a smaller or cheaper alternative. Multi-model evaluation results from 2.2 serve as the evidence base. A required sign-off document must name the specific frontier model, state its cost tier, quote the 2.2 evaluation results showing no smaller model met the quality threshold, and receive dual approval from the product owner and AI economics lead before the model is provisioned in production.

> **References:** [Generative AI Hub](https://www.sap.com/products/artificial-intelligence/generative-ai-hub.html) · [SAP AI Core Pricing](https://discovery-center.cloud.sap/serviceCatalog/sap-ai-core/?region=all&tab=service_plan&commercialModel=payg) · [SAP Business AI Pricing Model (video)](https://www.sap.com/products/artificial-intelligence/ai-units.html)

---

### 2.7 — Model Update & Retraining GovernanceDocument fine-tuning cadence, foundational model swap schedule, customer notification protocol, and data usage policy for any training or fine-tuning operation. The governance record must specify: model identity and version, fine-tuning dataset source with data-rights confirmation, customer notification lead time, rollback procedure, and attestation that customer data was not used in training without explicit consent. Post-update output quality must be confirmed before full rollout.

> **References:** [Responsible AI](https://www.sap.com/india/products/artificial-intelligence/ai-ethics.html)

---

## L0-3 · Document Grounding & RAG Quality Evaluation
*Ground AI outputs in enterprise documents and validate quality using the RAG Evaluation Scorecard.*

---

### 3.1 — Document Grounding Setup
Connect the agent to enterprise document repositories via the SAP Document Grounding API, configuring chunking strategy, metadata tagging, and access-control filters. Grounding scope determines which documents are available at inference time and must be validated against the RAG Evaluation Scorecard (3.3) before production. Only documents covered by data governance approval (5.7) may be indexed; any out-of-scope document is an indirect injection risk (5.6).

---

### 3.2 — Vector Embedding & Retrieval Pipeline
Select the embedding model, configure vector store dimensions, and validate retrieval precision and recall on the evaluation dataset. SAP HANA Cloud Vector Engine is the SAP-native vector store providing enterprise-grade security and tenant isolation. Pipeline parameters (chunk size, overlap, top-k) must be documented, version-controlled alongside prompt templates, and re-validated after any parameter change.

---

### 3.3 — RAG Evaluation Scorecard
The consolidated quality gate for a grounded agent: eight metrics across two families, scored before production sign-off. A per-metric threshold is defined per agent, measured automatically on the evaluation dataset before release, and re-evaluated after any retrieval-pipeline or model change; any metric below its threshold is a release blocker. Scores are archived alongside the Responsible AI evaluation results (5.1).

**Retrieval quality — are the right chunks retrieved?**
- **Context Relevance** — proportion of retrieved chunks actually relevant to the query
- **Context Recall** — whether retrieved chunks cover everything the gold answer needs
- **Retrieval Recall** — share of all relevant chunks that were successfully retrieved
- **Retrieval Precision** — share of retrieved chunks that are on-target (low noise)

**Answer quality — is the generated answer good?**
- **Groundedness** — every claim supported by retrieved context; the primary anti-hallucination metric
- **Answer Relevance** — the answer directly addresses the question asked
- **Answer Correctness** — coverage of the gold answer's facts; contradictions capped low
- **Answer Similarity** — semantic closeness to the gold answer

RagEval, a RAG evaluation tool, produces the full scorecard: groundedness and context relevance need no gold set, while answer correctness, answer similarity, and context recall are scored against a curated gold set of questions and answers — so gold-set quality drives how trustworthy the scores are.

> **References:** [Responsible AI](https://www.sap.com/india/products/artificial-intelligence/ai-ethics.html) · [Generative AI Hub](https://www.sap.com/products/artificial-intelligence/generative-ai-hub.html)

---

### 3.4 — Prompt Engineering Governance
Version-control all system prompts, few-shot examples, and prompt templates in a central repository with a change approval workflow; prompt changes are treated as configuration changes subject to the same regression gate as code changes. Templates must be reviewed for injection vulnerabilities, unauthorised capability disclosure, and role boundary erosion before deployment. Unapproved prompt changes in production are a governance violation.

> **References:** [Generative AI Hub](https://www.sap.com/products/artificial-intelligence/generative-ai-hub.html) · [Responsible AI](https://www.sap.com/india/products/artificial-intelligence/ai-ethics.html)

---

### 3.5 — Automated Grounding Roadmap
The forward plan for SAP's document grounding automation capabilities, covering automated chunking optimisation, embedding model updates, semantic metadata extraction, and real-time document refresh. Teams use the roadmap to anticipate when manual grounding setup steps will be automated and when new quality thresholds will become mandatory gates. Items reaching GA status are automatically promoted to required checklist gates.

> **References:** [Document Grounding](https://discovery-center.cloud.sap/ai-feature/fedeca14-3e69-472c-a0ea-82396735c35f/)

---

### 3.6 — Runtime Hallucination Guardrail ArchitectureDefine and implement the output validation layer including grounding confidence threshold, automatic answer rejection below the threshold, and customer-visible citation or grounding indicators on AI responses. Architecture specification must include: scoring method, rejection threshold value, user-facing fallback message format, the monitoring dashboard where hallucination rate is tracked continuously in production, and the alert threshold that triggers incident response.

> **References:** [Responsible AI](https://www.sap.com/india/products/artificial-intelligence/ai-ethics.html)

---

## L0-4 · AI Commercialization & Metering
*Governs the commercial lifecycle from pricing definition through production billing.*

---

### 4.1 — LLM Calculator
SAP's internal pricing tool that estimates the LLM cost component of an AI feature based on expected prompt token volume, completion token volume, and model pricing tier. Calculator output is a required input to the Floor Price Impact Review (4.3); estimates must be updated whenever the target model or expected usage profile changes materially. Teams must save a dated snapshot of the calculator output in the feature's governance record at each approval milestone.

> **References:** [SAP Business AI Pricing Model (video)](https://www.sap.com/products/artificial-intelligence/ai-units.html) · [SAP AI Core Pricing](https://discovery-center.cloud.sap/serviceCatalog/sap-ai-core/?region=all&tab=service_plan&commercialModel=payg)

---

### 4.2 — AI Scenario Metering Integration
Integrate the AI feature with SAP's central metering infrastructure so every LLM call, agent invocation, and tool execution is captured and attributed to the correct tenant, scenario, and commercial SKU. Metering must be validated end-to-end in the test environment before go-live, with billing records verified against actual API call logs. Metering gaps post go-live cause revenue leakage and contractual risk; post-launch metering failures are a P1 commercial incident.

> **References:** [SAP AI Core Pricing](https://discovery-center.cloud.sap/serviceCatalog/sap-ai-core/?region=all&tab=service_plan&commercialModel=payg) · [SAP Business AI Pricing Model (video)](https://www.sap.com/products/artificial-intelligence/ai-units.html)

---

### 4.3 — Floor Price Impact Review
Confirm that the commercial tier price exceeds the direct LLM cost floor across the expected usage distribution, including cost variance across model versions and token volume spikes. A feature cannot proceed if floor price analysis shows negative margin at median usage. Review must be refreshed whenever the target model, pricing tier, or usage forecast changes materially.

> **References:** [SAP Business AI Pricing Model (video)](https://www.sap.com/products/artificial-intelligence/ai-units.html) · [SAP AI Core Pricing](https://discovery-center.cloud.sap/serviceCatalog/sap-ai-core/?region=all&tab=service_plan&commercialModel=payg)

---

### 4.4 — SAP Business AI Pricing Model
SAP's consumption-based pricing model for Business AI features, where customers pay based on AI units or credits consumed rather than per-seat licensing. The pricing model documentation defines the billable unit, how credits map to LLM token volumes, and how pricing tiers are structured for different customer segments. Product teams must align AI Scenario Metering Integration (4.2) exactly with the published pricing model to ensure billing accuracy and auditability.

> **References:** [SAP Business AI Pricing Model (video)](https://www.sap.com/products/artificial-intelligence/ai-units.html) · [SAP AI Core Pricing](https://discovery-center.cloud.sap/serviceCatalog/sap-ai-core/?region=all&tab=service_plan&commercialModel=payg)

---

### 4.5 — Customer Token Consumption ForecastProduce a pre-deployment estimate of token usage per interaction type and provide it to the customer as part of commercial onboarding. Distinguishes from the LLM Calculator (4.1), which is an internal pricing tool. The forecast document must cover: estimated tokens per interaction type (simple query, multi-step reasoning, agentic loop), expected interaction volume per month, total monthly token estimate, cost range in commercial units, and key assumptions. Updated when actual usage diverges materially from forecast.

> **References:** [SAP Business AI Pricing Model (video)](https://www.sap.com/products/artificial-intelligence/ai-units.html) · [SAP AI Core Pricing](https://discovery-center.cloud.sap/serviceCatalog/sap-ai-core/?region=all&tab=service_plan&commercialModel=payg)

---

### 4.6 — Cost Per Transaction BaselineDefine and instrument cost per agent invocation across LLM calls, tool calls, and retrieval operations, then establish ceiling thresholds before go-live. Baseline is recorded as part of the go-live checklist and reviewed quarterly. Any cost per transaction exceeding the ceiling triggers a cost review before the next model or tool change is applied. Connected to AI Scenario Metering Integration (4.2) for raw cost data and Customer Token Consumption Forecast (4.5) for customer-facing estimates.

> **References:** [SAP AI Core Pricing](https://discovery-center.cloud.sap/serviceCatalog/sap-ai-core/?region=all&tab=service_plan&commercialModel=payg) · [SAP Business AI Pricing Model (video)](https://www.sap.com/products/artificial-intelligence/ai-units.html)

---

## L0-5 · Responsible AI & Safety Validation
*Mandatory pre-release evaluation — safety, ethics, fairness, and regulatory compliance.*

---

### 5.1 — Responsible AI Pre-Release Evaluation
Before release, evaluate the AI feature's model and prompt configuration against SAP's Responsible AI standards — covering harm detection, content safety, bias screening, and regulatory requirement alignment. This evaluation is a hard gate: features that do not pass cannot proceed to the cross-functional sign-off (7.4). Results are archived and referenced during GDPR / EU AI Act compliance review (5.5).

> **References:** [Responsible AI](https://www.sap.com/india/products/artificial-intelligence/ai-ethics.html)

---

### 5.2 — AI Bias & Fairness AssessmentEvaluate outputs for demographic bias and fairness gaps using a defined measurement framework (e.g., demographic parity, equalized odds), with explicit acceptance thresholds and a required output report including a customer-facing disclosure. Post-release re-evaluation cadence must be no less frequent than every six months or following any model change. Assessment report must state measurement framework selection rationale, demographic categories evaluated, metric values against each threshold, and pass/fail determination.

> **References:** [Responsible AI](https://www.sap.com/india/products/artificial-intelligence/ai-ethics.html)

---

### 5.3 — Adversarial & Red Team Testing
Execute structured adversarial testing covering direct prompt injection (via user input), jailbreak attempts, role boundary erosion, and denial-of-service via oversized inputs. Red team results must be documented with severity classification, reproduction steps, and remediation actions before the release gate. Testing must be repeated after any significant prompt template change or model update. Note: indirect injection via enterprise business data is a separate and distinct item (5.6).

> **References:** [Adversarial Attack Term](https://learning.sap.com/courses/architecting-security-for-sap-business-technology-platform/differentiating-ai-vulnerabilities-and-attack-vectors) · [Responsible AI](https://www.sap.com/india/products/artificial-intelligence/ai-ethics.html)

---

### 5.4 — AI Ethics & Governance Alignment
Confirm alignment with SAP's AI Ethics guidelines covering transparency, explainability, human oversight, and prohibition of specific high-risk use cases. Ethics review requires sign-off from the Responsible AI governance function — not only the product team — and must document how the agent communicates its AI nature to end users and what explanation is available for consequential decisions. Undisclosed AI agency in high-stakes business contexts is a compliance failure.

> **References:** [Responsible AI](https://www.sap.com/india/products/artificial-intelligence/ai-ethics.html)

---

### 5.5 — GDPR / EU AI Act Compliance
Confirm compliance with GDPR data processing obligations and, where applicable, EU AI Act requirements including risk classification, technical documentation, conformity assessment, and human oversight obligations. For high-risk AI systems, a conformity assessment and CE marking process applies. Documentation must state which regulatory category applies to the agent and what evidence satisfies each requirement; this record is reviewed during the cross-functional sign-off (7.4).

> **References:** [Responsible AI](https://www.sap.com/india/products/artificial-intelligence/ai-ethics.html)

---

### 5.6 — Indirect Prompt Injection via Business DataAdversarial scanning of the RAG corpus and all connected business data sources (CRM records, supplier documents, procurement data, HR records) for injected instructions — distinct from direct prompt injection via user input (5.3), which is the primary attack surface in SAP's connected agent context. Sanitisation gate requires: automated scan for embedded instruction patterns, human review queue for ambiguous findings, and documented rejection or sanitisation of flagged records. Gate must be re-executed whenever new data sources are added to the retrieval pipeline.

> **References:** [Adversarial Attack Term](https://learning.sap.com/courses/architecting-security-for-sap-business-technology-platform/differentiating-ai-vulnerabilities-and-attack-vectors) · [Responsible AI](https://www.sap.com/india/products/artificial-intelligence/ai-ethics.html)

---

### 5.7 — IP Rights & Data Ownership GovernanceDeclare output ownership position (customer, SAP, or shared), document customer data isolation at tenant level, confirm non-use of customer data in any model training step, state the copyright position for AI-generated content, and document SAP's indemnification position if AI output infringes third-party IP. IP governance record must be a distinct artefact — not embedded in a broader privacy policy — and must be updated whenever the foundational model or fine-tuning approach changes. Escalation path for customer disputes over output ownership must be defined.

> **References:** [Responsible AI](https://www.sap.com/india/products/artificial-intelligence/ai-ethics.html)

---

## L0-6 · Agent Development & Deployment Standards
*Tooling, patterns, and governance for building, registering, and deploying AI agents at scale.*

---

### 6.1 — Agent Builder in Joule Studio
SAP's low-code tool within Joule Studio for configuring, testing, and registering AI agents against the SAP agent framework, providing the runtime execution environment, tool registration interface, and prompt management UI. All agents destined for SAP products must be registered and validated via Agent Builder before they are eligible for the release gate. Custom agents built outside Agent Builder require a documented exception and additional security review.

> **References:** [Agent Builder](https://www.sap.com/products/financial-management/joule-studio-agent-builder.html) · [Joule Studio Product](https://www.sap.com/products/artificial-intelligence/joule-studio.html)

---

### 6.2 — Skill Builder in Joule Studio
Joule Studio's Skill Builder enables product teams to define, test, and publish individual skills (tools) that agents may invoke; each skill maps to one or more backend API calls and carries a declared access scope. Skills published via Skill Builder become selectable in Agent Builder in Joule Studio (6.1). Skill definitions must include input/output schema, error handling, and a latency SLA commitment.

> **References:** [Skill Builder (video)](https://www.sap.com/assetdetail/2025/10/1cde5328-287f-0010-bca6-c68f7e60039b.html) · [Joule Studio Product](https://www.sap.com/products/artificial-intelligence/joule-studio.html)

---

### 6.3 — Generative AI Hub (J17)
SAP's managed LLM access layer (Joule feature J17) providing a unified API endpoint for model inference, prompt playground, token consumption tracking, and model version management. All LLM calls from SAP agents must route through the Generative AI Hub to ensure centralised access control, audit logging, and cost metering. The Hub also provides model lifecycle management including deprecation notices and version pinning against unplanned provider-side changes.

> **References:** [Generative AI Hub](https://www.sap.com/products/artificial-intelligence/generative-ai-hub.html) · [SAP AI Core Pricing](https://discovery-center.cloud.sap/serviceCatalog/sap-ai-core/?region=all&tab=service_plan&commercialModel=payg)

---

### 6.4 — SAP AI Core & AI Launchpad
SAP AI Core is the runtime infrastructure for serving AI models, managing training pipelines, and executing agentic workloads at scale within the SAP BTP ecosystem; SAP AI Launchpad is the operations interface providing model deployment management, resource monitoring, and lifecycle orchestration. Together they form the foundational infrastructure layer on which all SAP-hosted agents run; production deployments must use AI Core as the serving runtime unless an approved exception is documented.

> **References:** [SAP AI Core Pricing](https://discovery-center.cloud.sap/serviceCatalog/sap-ai-core/?region=all&tab=service_plan&commercialModel=payg) · [AI Launchpad](https://www.sap.com/india/products/artificial-intelligence/ai-launchpad.html) · [AI Launchpad (Help)](https://learning.sap.com/courses/introduction-to-ai-core/configuring-sap-ai-core-and-sap-ai-launchpad_a51c5214-d9ab-4f22-bc81-b683d09697fc)

---

### 6.5 — Agent Tool Access GovernanceDefine RBAC for all agent tool invocations, establish customer-controlled per-tenant policy for which tools an agent may call, apply least-privilege scope, and implement an approval workflow for granting new or sensitive system access. The governance artefact must enumerate every callable tool, the minimum required permission scope, available tenant administrator controls, and the audit log schema with retention period. Segregation of duties must be explicitly documented for agents with write access to financial, procurement, or HR systems.

> **References:** [Skills Governance Agent (J2259)](https://learning.sap.com/courses/exploring-joule-and-ai-agents-in-sap-successfactors/introducing-skills-assistants-and-agents_ad8e62d6-372b-4ba4-ad74-152130786666)

---

### 6.6 — Human-in-the-Loop Approval GovernanceTreats the approval pattern itself as a governance item: defines which agent actions need mandatory human sign-off versus which can run autonomously, how overrides are audited, and how the approval workflow is validated at release. The governance document must provide an explicit action classification table — each action categorised as fully autonomous, advisory, or blocked pending approval. Override events must be logged with approver identity, timestamp, and reason; the approval workflow is integration-tested as part of the release gate.

> **References:** [Agent Builder](https://www.sap.com/products/financial-management/joule-studio-agent-builder.html) · [Responsible AI](https://www.sap.com/india/products/artificial-intelligence/ai-ethics.html)

---

### 6.7 — Agent Execution Observability & TracingRequire step-level tracing for any agent with more than one reasoning or tool-call hop, capturing inputs, intermediate decisions, and tool calls in a structured (not free-text) form that supports programmatic querying for debugging and audit. Minimum trace fields: step ID, step type (LLM call / tool call / routing decision), inputs, outputs, latency, model or tool identity, and error state. Trace data must be accessible to both engineering (debugging) and support tiers (incident investigation) with a defined, compliance-aligned retention period.

> **References:** [AI Launchpad](https://help.sap.com/docs/ai-launchpad/sap-ai-launchpad/what-is-sap-ai-launchpad?locale=en-US)

---

## L0-7 · End-to-End Release Validation & Go-Live `TITLE CORRECTED`
*Final gate confirming all pillars are satisfied before a feature is released to production.*

---

### 7.1 — AI-Driven Exploratory Testing (AET)
AET (J1186) to generate and execute test flows across the agent's functional surface, including edge cases not covered by the regression suite. AET clearance is distinct from the Agent Regression Testing Environment (7.5) and both must pass. GA is targeted for December 2027. Maintain an interim testing approach until GA is confirmed.

> **References:** [AET (Product)](https://community.sap.com/t5/technology-blog-posts-by-sap/ai-driven-exploratory-testing-aet-a-tester-s-point-of-view/ba-p/14370086)

---

### 7.2 — Integration Validation
End-to-end validation that the agent integrates correctly with all connected backend systems, APIs, and data sources under production-like conditions. Must cover authentication flows, permission boundary enforcement, error handling for downstream failures, and performance under expected peak load. Integration validation must be repeated after any backend system change, API version update, or agent tool addition — it is not a one-time pre-release activity.

---

### 7.3 — CBC Toggle Activation
Production CBC toggle activation is the final configuration step before the feature is live in customer tenants, coordinated against the completed go-live readiness checklist. Toggle must be tested in both activation and deactivation states; a rollback procedure (toggle-off + remediation playbook) must be documented and tested before go-live. CBC state post-activation is the production artefact monitored by architecture drift detection (10.5).

> **References:** —

---

### 7.4 — Cross-Functional Sign-Off
Structured sign-off from all mandatory review functions before go-live: Product, Engineering, Commercialisation, Legal / Compliance, Responsible AI, Support (ESCE), and Security. Each function confirms that their respective pillar checklist items are complete; sign-off is recorded in the feature's governance record. Cross-functional sign-off is the final gate before CBC toggle activation (7.3) and the official release record.

> **References:** [Responsible AI](https://www.sap.com/india/products/artificial-intelligence/ai-ethics.html)

---

### 7.5 — Agent Regression Testing EnvironmentEstablish a dedicated non-production environment with production parity and a versioned regression test suite covering all known agent behaviours. Full regression suite execution is mandatory before any model update, tool change, KG schema change, or prompt template update is promoted to production. The environment maintains a pass/fail baseline from the previous production release; any change causing a regression is an automatic release blocker. Distinct from AI-Driven Exploratory Testing (AET) (7.1).

---

## L0-8 · Agent Design Classification & Performance Engineering `TITLE CORRECTED`
*Classify every agent step by trigger type and reasoning mode. Measure performance at each layer.*

---

### 8.1 — Trigger Type Classification
Classify every agent entry point by trigger mechanism: user-initiated (synchronous, UI-driven), event-driven (asynchronous, system event), scheduled (periodic, time-based), or multi-agent (triggered by another agent). Trigger type determines timeout budget, error handling strategy, and UX design requirements. All trigger types for an agent must be documented and confirmed before performance SLAs (8.4–8.6) are defined.

> **References:** [Agent Builder](https://www.sap.com/products/financial-management/joule-studio-agent-builder.html) · [Generative AI Hub](https://www.sap.com/products/artificial-intelligence/generative-ai-hub.html)

---

### 8.2 — Agentic Reasoning Classification
Classify the agent's reasoning mode at each step: reactive (single-turn LLM call), chain-of-thought (sequential multi-step reasoning), ReAct (reasoning + tool calls), or multi-agent delegation. Classification determines which governance items apply — single-turn reactive agents carry a lighter checklist than multi-hop ReAct agents — and is the direct input to the Frontier Model Justification Gate (2.6). Classification must be confirmed at design time and reviewed if the agent's reasoning architecture changes.

> **References:** [Generative AI Hub](https://www.sap.com/products/artificial-intelligence/generative-ai-hub.html) · [Agent Builder](https://www.sap.com/products/financial-management/joule-studio-agent-builder.html)

---

### 8.3 — Cross-Agent Intent Conflict ResolutionWhen multiple agents are active in a user session or business process, conflicting intent signals can produce contradictory actions or feedback loops. This item requires: identification of all scenarios where two or more agents may act on the same entity or event, a defined conflict resolution priority hierarchy, and a documented escalation path when autonomous resolution is not possible. Conflict resolution logic must be tested in the Agent Regression Testing Environment (7.5) before go-live.

> **References:** [Agent Builder](https://www.sap.com/products/financial-management/joule-studio-agent-builder.html) · [Joule Studio Product](https://www.sap.com/products/artificial-intelligence/joule-studio.html)

---

### 8.4 — UI Layer Performance
Define and measure the response time budget for user-facing interactions from user input to first visible response (time-to-first-token or time-to-complete-response). SLA must be set at p50, p95, and p99 levels and validated end-to-end — not only at the API level — under peak load conditions. UI layer performance is a customer-visible SLA commitment and a required input to the ESCE support concept (1.5).

> **References:** [Joule Studio Product](https://www.sap.com/products/artificial-intelligence/joule-studio.html) · [AI Launchpad](https://help.sap.com/docs/ai-launchpad/sap-ai-launchpad/what-is-sap-ai-launchpad?locale=en-US)

---

### 8.5 — Orchestration / Reasoning Layer PerformanceMeasure the time and token cost of the agent's orchestration and reasoning steps, excluding UI rendering and backend API calls. For multi-hop agents, each reasoning hop must have an individual latency budget; runaway reasoning loops that consume excessive tokens must be detected and bounded by configurable step limits. Orchestration performance directly impacts the Cost Per Transaction Baseline (4.6) — unbudgeted reasoning hops are one of the leading causes of unexpected cost overrun.

> **References:** [Orchestration Service](https://help.sap.com/docs/ai-launchpad/sap-ai-launchpad/orchestration-4953dc10c6dd48fe85f37b41109dffe2?locale=en-US)

---

### 8.6 — Backend / Tool Call Performance
Measure the latency of each tool call (API invocation, database query, KG lookup) as an independent performance dimension; backend latency is typically the dominant contributor to total agent response time in multi-tool agentic workflows. Each tool must have a defined timeout and a tested fallback when the timeout is breached. Tool call performance is logged by Agent Execution Observability & Tracing (6.7) and reported on the operational dashboard post go-live.

---

## L0-9 · Knowledge & Data Grounding Strategy `TITLE CORRECTED`
*Define when and how agents use SAP KG, custom KG, and document RAG — at runtime, not just design time.*

---

### 9.1 — SAP KG as Runtime Grounding Source
The SAP Knowledge Graph is the enterprise's authoritative structured data source for entity relationships, process definitions, and product taxonomies; when used as a runtime grounding source, it provides agents with current, structured context that is more reliable than document RAG for factual entity lookups. Teams must document which KG entity types and relationships the agent queries at runtime, the expected query latency, the staleness threshold from KG Freshness & Staleness Management (9.4), and how KG unavailability is handled at runtime.

> **References:** [SAP Knowledge Graph Concept](https://www.sap.com/products/artificial-intelligence/knowledge-graph.html)

---

### 9.2 — Custom KG Design & Governance
Where the SAP standard KG does not contain the domain-specific entities required by the agent, teams may define a custom KG extension following SAP's information model conventions. Custom KG design must define a governance owner, ingestion cadence, versioning approach, and a data architecture review is required before use in production. Custom KGs that diverge from standard KG schema without review introduce schema drift risk flagged by Architecture Drift Detection (10.5).

> **References:** [SAP Knowledge Graph Concept](https://www.sap.com/products/artificial-intelligence/knowledge-graph.html)

---

### 9.3 — KG vs RAG Decision Framework
A documented decision framework specifying which grounding strategy applies per query category: KG for structured entity and relationship lookups where the schema is known; RAG for unstructured document-based context where content is dynamic or semi-structured; structured context injection (9.5) for small, deterministic data sets that fit within the context window. Framework must be applied at design time and reviewed whenever new data sources or query types are added to the agent.

> **References:** [SAP Knowledge Graph Concept](https://www.sap.com/products/artificial-intelligence/knowledge-graph.html)

---

### 9.4 — KG Freshness & Staleness Management
Define the maximum acceptable age of KG data for each entity type the agent relies on, and implement a staleness detection mechanism that alerts when data exceeds the threshold. KG staleness can cause agents to act on outdated pricing, inventory, organisational structure, or regulatory data — especially critical in agentic workflows that write back to business systems. Staleness thresholds, alert routing, and fallback behaviour must be documented as part of the KG grounding architecture.

> **References:** [SAP Knowledge Graph Concept](https://www.sap.com/products/artificial-intelligence/knowledge-graph.html)

---

### 9.5 — Context Engineering - Structured Context Injection
For small, deterministic data sets (e.g., user profile, current session context, configuration parameters), inject structured data directly into the prompt context rather than retrieving via KG or RAG; this reduces retrieval latency, increases determinism, and lowers hallucination risk for predictable data. The maximum context window budget allocated to structured injection must be documented and tested to prevent context overflow, which silently degrades retrieval quality in the same prompt.

> **References:** [Prompt & Context Engineering](https://learning.sap.com/courses/solve-your-business-problems-using-prompts-and-llms-in-sap-generative-ai-hub/implementing-prompt-engineering-techniques)

---

## L0-10 · Dependency & Change Resilience
*Agents adapt to architectural changes via runtime KG. Quality maintained via continuous drift detection.*

---

### 10.1 — Runtime KG Dependency Resolution
Implement dynamic resolution of agent dependencies (skills, tools, model endpoints, data sources) via the SAP KG at runtime rather than hard-coding references at build time, enabling agents to adapt automatically to infrastructure changes without a code deployment. The dependency resolution mechanism must have a defined and tested fallback when the KG is unavailable, preventing a KG outage from propagating into an agent outage. Connects to the architecture drift detection loop (10.5).

> **References:** [SAP Knowledge Graph Concept](https://www.sap.com/products/artificial-intelligence/knowledge-graph.html)

---

### 10.2 — Agent Tool Dependency Map
Maintain a live dependency map documenting every external tool, API, data source, and model endpoint the agent calls, with version pinning, SLA requirements, and change-notification contacts. The dependency map is the primary input to impact analysis when any dependency changes and is used by the Agent Regression Testing Environment (7.5) to determine which test scenarios must be re-run. An out-of-date dependency map is treated as an Architecture Drift Detection incident (10.5).

> **References:** [Skills Governance Agent (J2259)](https://learning.sap.com/courses/exploring-joule-and-ai-agents-in-sap-successfactors/introducing-skills-assistants-and-agents_ad8e62d6-372b-4ba4-ad74-152130786666)

---

### 10.3 — Model Drift Detection
Continuously monitor the selected LLM for quality degradation relative to the production baseline, detecting drift caused by provider-side model updates, inference infrastructure changes, or distributional shift in production inputs. Model drift is the primary trigger for Ongoing Model Version Re-evaluation (2.5) and must produce an automated alert with quantitative comparison against baseline. Alert threshold and escalation path must be defined before go-live.

> **References:** —

---

### 10.4 — Data Drift Detection
Monitor the statistical properties of data flowing through the RAG pipeline (document corpus, user query distribution, retrieved context distribution) to detect shifts that degrade grounding quality below acceptable thresholds. Data drift that goes undetected silently reduces faithfulness and context relevance scores — the primary cause of invisible quality degradation in production. Automated alerts when drift metrics exceed thresholds must trigger re-evaluation of the RAG Evaluation Scorecard scores (L0-3).

> **References:** [Document Grounding](https://discovery-center.cloud.sap/ai-feature/fedeca14-3e69-472c-a0ea-82396735c35f/)

---

### 10.5 — Architecture Drift Detection
Detect unauthorised or unplanned changes to the agent's deployed architecture including model endpoint substitution, tool version changes, KG schema modifications, and infrastructure configuration drift. Architecture drift detection closes the loop between the Agent Tool Dependency Map (10.2) and live production state. Any detected drift must be investigated and either accepted with a governance record update or remediated within the defined SLA.

> **References:** [Reference Architecture](https://architecture.learning.sap.com/docs/ref-arch/39eb58)

---

## Cross-Pillar Feedback Loops `MISSING FROM OVERVIEW — RESTORED`
*Three continuous loops that connect the pillars — quality gates become quality pipelines.*

---

### Loop 1 — Model Quality
**L0-2 LLM Benchmarking ↔ L0-10.3 Model Drift Detection**
Production Model Drift Detection alerts (10.3) feed directly back into the LLM benchmarking pipeline (L0-2): a drift alert triggers an automatic Ongoing Model Version Re-evaluation run (2.5), with results assessed against the Frontier Model Justification Gate (2.6). The loop prevents model quality degradation from persisting silently between scheduled evaluation cycles.

> **References:** —

---

### Loop 2 — Data & Grounding Quality
**L0-3 RAG Quality Evaluation ↔ L0-10.4 Data Drift Detection**
Data Drift Detection alerts (10.4) feed back into the RAG quality evaluation pipeline (L0-3): a drift event triggers re-evaluation of the RAG Evaluation Scorecard (3.3) and review of the document grounding setup (3.1). The loop closes the gap between pre-release grounding quality and the evolving state of the enterprise document corpus in production.

---

### Loop 3 — Architecture Resilience
**L0-9.1 Runtime KG Consumption ↔ L0-10.1 Runtime KG Dependency Resolution**
Architecture Drift Detection events (10.5) and KG Freshness & Staleness Management alerts (9.4) feed back into the runtime KG dependency resolution mechanism (10.1), which triggers re-validation of KG-dependent agent behaviours against the Agent Regression Testing Environment (7.5). The loop ensures that changes in SAP KG schema or entity availability do not silently break agent behaviour in production.

> **References:** [SAP Knowledge Graph Concept](https://www.sap.com/products/artificial-intelligence/knowledge-graph.html)

---

## Agent Lifecycle → Pillar Mapping

### Ideation
**Anchor:** L0-1 AI Feature & Agent Onboarding Governance · L0-4 AI Commercialization & Metering
**Key checkpoints:** 1.1 Feature Type Classification · 1.2 Commercial Tier · 4.5 Customer Token Consumption Forecast · 5.7 IP Rights & Data Ownership (confirm before any customer data enters scope)

### Design
**Anchor:** L0-8 Agent Design Classification & Performance Engineering · L0-9 Knowledge & Data Grounding Strategy · L0-2 LLM Selection & Benchmarking
**Contributing:** L0-3 (grounding architecture) · L0-4 (cost design) · L0-6 (tooling selection)
**Key checkpoints:** 8.2 Agentic Reasoning Classification · 2.6 Frontier Model Justification Gate · 9.3 KG vs RAG Decision · 6.5 Agent Tool Access Governance · 4.6 Cost Per Transaction Baseline

### Build
**Anchor:** L0-3 Document Grounding & RAG Quality Evaluation · L0-6 Agent Development & Deployment Standards
**Contributing:** L0-2 (test data, multi-model eval) · L0-8 (performance engineering) · L0-9 (KG integration)
**Key checkpoints:** 3.6 Runtime Hallucination Guardrail Architecture · 5.6 Indirect Prompt Injection via Business Data · 7.5 Agent Regression Testing Environment ready before Validate

### Validate
**Anchor:** L0-5 Responsible AI & Safety Validation · L0-7 End-to-End Release Validation & Go-Live · L0-2 LLM Selection & Benchmarking (results confirmed)
**Contributing:** L0-3 (RAG Evaluation Scorecard evaluated) · L0-4 (floor price, metering sign-off) · L0-8 (performance SLAs validated)
**Key checkpoints:** 5.2 Bias Evaluation thresholds met · 5.1 Responsible AI evaluation cleared · 7.4 Cross-Functional Sign-Off · 7.5 Regression suite cleared

### Deploy
**Anchor:** L0-7 (go-live activation) · L0-10 Dependency & Change Resilience · Cross-Pillar Feedback Loops (all 3 activate)
**Contributing:** L0-4 (metering live) · L0-5 (continuous bias monitoring) · L0-6 (deployment standards, audit logs) · L0-9 (runtime KG active) · L0-2 (ongoing re-evaluation)
**Key checkpoints:** 2.7 Model Update Governance active · 7.5 Regression suite mandatory before any post-go-live change

---

## Pillar Lifecycle Span — Quick Reference

| Pillar | Lifecycle Stages |
|---|---|
| L0-1 | Ideation |
| L0-2 | Design → Validate → Deploy |
| L0-3 | Build → Validate |
| L0-4 | Ideation → Design → Validate → Deploy |
| L0-5 | Validate → Deploy |
| L0-6 | Build → Deploy |
| L0-7 | Validate → Deploy |
| L0-8 | Design → Build |
| L0-9 | Design → Build → Deploy |
| L0-10 | Deploy |
| Cross-Pillar Loops | Deploy (continuous) |

---

## Change Log

### Title corrections (4)
- L0-7 · "End-to-End Release & Go-Live" → "End-to-End Release **Validation** & Go-Live"
- L0-8 · "Agent Design & Performance" → "Agent Design **Classification** & Performance **Engineering**"
- L0-9 · "Knowledge & Data Grounding" → "Knowledge & Data Grounding **Strategy**"
- L0-10.6 · "Continuous Accuracy Testing" → "Continuous Accuracy Testing **Pipeline**"

### Item name corrections (3)
- 7.5 · "Official Release" → "Official Release **(AI112)**"
- 8.3 · "Cross-Agent Intent Conflict" → "Cross-Agent Intent Conflict **Resolution**"
- 8.5 · "Orchestration Layer Performance" → "Orchestration **/ Reasoning** Layer Performance"

### Expansions (1)
- 5.2 · AI Bias & Fairness Assessment — measurement methodology, thresholds, and continuous cadence added

### New advisory items (13)
- 2.6 Frontier Model Justification Gate
- 2.7 Model Update & Retraining Governance
- 3.8 Runtime Hallucination Guardrail Architecture
- 4.7 Customer Token Consumption Forecast
- 4.8 Cost Per Transaction Baseline
- 5.6 Indirect Prompt Injection via Business Data
- 5.7 IP Rights & Data Ownership Governance
- 6.6 Agent Tool Access Governance
- 6.7 Human-in-the-Loop Approval Governance
- 6.8 Agent Execution Observability & Tracing
- 7.6 Agent Regression Testing Environment
- 10.7 Post Go-Live Operational Governance
- 10.8 Agent Incident Definition & Support Tier Ownership

### Missing section restored
- Cross-Pillar Feedback Loops (Loops 1, 2, 3) added to overview

---

*Enriched with L2 descriptions and SAP reference links. Public references sourced from sap.com, help.sap.com, learning.sap.com, community.sap.com, architecture.learning.sap.com, and the SAP Discovery Center.*