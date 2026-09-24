# Related Work

> **Draft status.** Every claim about a cited paper is now grounded in a direct
> read of its title page and abstract (the PDFs under `docs/paper/`). The seven
> entries previously marked **[verify]** were checked on 24/09: five held as
> written, two were reworded (MemPoison [15] and the harness-scaling paper [22]).
> See §7.7 for the citation errors found in our own reading list.

Our work sits at the junction of three literatures that have not yet been
joined: attacks that persist inside an agent harness, benchmarks that measure
how far such attacks travel, and Stackelberg security games for allocating a
scarce inspection budget. The first two tell us what to defend and how to score
a defence; the third tells us where to look. What is missing from all three, and
what this paper supplies, is a *priced* model — one in which auditing a carrier
costs a measured amount, the budget is finite, and the defender's problem is
therefore an allocation problem rather than a detection problem.

## 7.1 Persistent poisoning of agent carriers

Poisoning an agent's durable state is now a well-established attack class.
AgentPoison [5] red-teams LLM agents by corrupting memory or knowledge bases,
and shows that a small number of injected records suffices to steer later
retrievals. MINJA [8] demonstrates a memory-injection attack mounted entirely
through ordinary interaction: the attacker only issues queries and observes
outputs, and never writes to the memory bank directly. At web
scale, Carlini et al. [4] establish that poisoning real training corpora is
practical and cheap, which is the background condition that makes agent-level
persistence worth worrying about.

The property our threat model turns on is *delay*. Sleeper Agents [11] shows
that a backdoor can survive safety training and fire only on a trigger,
establishing that dormancy is achievable rather than hypothetical. We take the
same structure one level up: a payload is written into a carrier at task
$\iota$, lies dormant, and detonates at task $\sigma = \iota + \Delta$. Our
contribution here is not the attack but the measurement — we report $\Delta$ as
observed on the histories of ten real SWE-bench repositories, and find the
median is 0 tasks in eight of the ten, with only 19% of instances at
$\Delta \ge 2$. Work that assumes long dormancy is describing a minority of the
workload.

MemPoison [15] is the closest measurement of the dormancy we model: a
1,227-case benchmark whose third tier is *context-triggered dormant
corruption*, and whose finding is that write-time defences suppress direct
single-record attacks but fail on compositional and trigger-conditioned ones.
That is the regime in which inspecting at write time is not enough and
inspection has to be spread over the window between write and trigger — the
allocation problem this paper studies. The repair line acts later:
MemTxn [17] puts a transaction boundary around memory updates and restores the
complete application-visible state after a fault, and dependency-guided
rollback [7] repairs downstream state given memories already diagnosed as
faulty. Both are complementary to us: they act after detection, whereas our
defender must decide where to spend inspection effort before it knows anything.

## 7.2 Benchmarks for persistent-carrier safety

Two recent benchmarks are the closest prior work, and the comparison is worth
making precisely.

**HarnessSafe** [10] evaluates safety across persistent carriers in agent
harnesses: 328 executable cases over seven persistent-carrier families, each
specified as a *Persistent-Risk Lifecycle* that traces attacker influence from
entry, through retention across carriers and boundary crossing, to a later
benign trigger and an observable violation. Its seven-stage, trace-based scheme
assigns each run to the furthest stage the evidence supports, and its headline
finding is that containment is carrier-specific and depends strongly on the
harness–model configuration — so end-to-end attack-success rates cannot
distinguish lifecycle progression patterns.

**MemSecBench** [16] tracks memory poisoning from persistence to consequence and
repair: 310 cases from 48 contexts under a controlled *Write–Execute–Forget*
protocol, across a 24-configuration matrix of two harnesses, four memory
backends and three LLM backends. Malicious memory persists in 84.2% of cases and
the full Write–Execute chain succeeds in 50.3%.

We share their subject and differ in the question. Both measure *whether* a
defence contains an attack, holding the defence fixed and varying the system.
We hold the system fixed and ask *where a limited audit budget should go*, which
requires three things neither benchmark has: a cost for auditing each carrier,
a budget constraint, and an adversary that best-responds to the defender's
committed policy. Their carrier taxonomies and lifecycle staging are, in our
view, the right substrate for that question, and our four carriers
(memory, skill, queue, branch) are a coarser cut of the same structure.

Colosseum [6] audits collusion in cooperative multi-agent systems, measuring
collusive behaviour as regret against the cooperative optimum — a different
failure mode, and a regret-based audit metric close in spirit to ours.

## 7.3 Stackelberg security games

The defender's problem — commit to a randomised allocation of scarce inspection
resources over targets, against an attacker who observes the commitment and then
chooses where to strike — is a Stackelberg security game. The field has a mature
theory and a deployment record: Tambe [20] collects the deployed systems and
lessons; Conitzer and Sandholm's complexity results and the subsequent LP
formulations [14] give the solution concepts we use; Kiekintveld et al. [13]
address computing optimal randomised allocations when the target set is large.
Our minimax LP and its receding-horizon variants are standard instruments from
this literature, not contributions.

The paper closest to our framing is Kim, Choo, Neoh and Tambe [12], a position
paper at AAMAS 2026 arguing that AI oversight should be modelled as strategic
resource allocation rather than as a static optimisation, and proposing three
directions across the LLM lifecycle. Their second direction is, almost verbatim,
our problem: *optimising the allocation of auditing and evaluation resources to
identify weaknesses or misaligned behaviour under limited reviewer capacity.*
They propose it; we instantiate it on a concrete harness, measure every
parameter of the resulting game, and report what happens. We regard our negative
results as the more useful half of that contribution, precisely because the
direction is being proposed and has not yet been stress-tested: two of the three
mechanisms in our own best-designed policy contribute nothing measurable, and
the advantage of allocation over a fixed commit-gate audit exists only inside a
band of budget levels.

## 7.4 Adaptive attackers and evaluation hygiene

Nasr et al. [25] argue that defences against jailbreaks and prompt injection are
routinely evaluated against static attack sets or weak optimisers, and that this
evaluation process is flawed: by scaling general optimisation techniques and
human-guided exploration they bypass 12 recent defences with attack success
above 90%, most of which had originally reported near-zero rates. Related, [24]
bypasses all eight defences it evaluates against indirect prompt injection on
LLM agents, with attack success above 50% under adaptive attacks.

We take this as a methodological requirement rather than a related result, and
we report having failed it ourselves. Our harness originally *sampled* the
attacker's placement $(\iota, \sigma)$ from the feasible set rather than letting
the attacker choose it — one placement of eight at $\Delta = 0$. Against a true
best response the $\Delta = 0$ column collapses: every policy reaches maximal
harm. Any allocation result measured against a sampled adversary is an upper
bound on the defence, and we state ours against the best-responding one.

## 7.5 Statistical methodology

Our confidence intervals resample by workflow rather than by case, because cases
within a workflow share a task chain and a clean-run outcome; Cameron, Gelbach
and Miller [3] give the cluster-bootstrap improvements we follow. Where we
screen many grid cells we control the false discovery rate in the sense of
Benjamini and Hochberg [2]. For the benign-corpus gate we report a permutation
test alongside a parametric bound, and the two disagree in a way worth naming:
the parametric bound rejects two cells the permutation test does not, so we
treat it as conservative and certify on the permutation result.

## 7.6 Software-engineering substrate

Our workflows are built from SWE-bench Verified instances and the agent-harness
design follows the open agent platforms, of which OpenHands [21] is
representative. Two recent papers move attention from the model to the harness
around it: [22] argues that the execution layer — memory, retrieval, skill
routing, verification — should be a first-class object of design and
evaluation, and [23] shows that security controls for coding agents can be
distributed through the harness itself. Our defender is a harness-level
control in exactly that sense. To measure the real trigger delay $\Delta$ we need to know which files
change together, for which we use the conceptual- and logical-coupling and
co-change literature from empirical software engineering.

## 7.7 A note on our own citations

Three entries in our working catalogue carry titles that do not match the papers
at the cited identifiers, and we record it so the error does not reach the
bibliography:

- arXiv:2602.07259 is *Incentive-Aware AI Safety via **Strategic Resource
  Allocation**: A Stackelberg Security Games Perspective*, not "…via Stackelberg
  security games".
- arXiv:2608.06984 is *HarnessSafe: **Evaluating Safety Across** Persistent
  Carriers in Agent Harnesses*, not "…Tracing persistent influence across agent
  carriers".
- arXiv:2607.27080 is *MemSecBench: **Tracking Agent Memory Poisoning from
  Persistence to Consequence and Repair***, not "…Benchmarking the poisoning
  lifecycle and selective repair of agent memory".

Two further entries (arXiv:2512.21794 and arXiv:2604.23374) were catalogued
under titles that appear to be system names used *inside* those papers rather
than the paper titles.

The 24/09 read of the remaining PDFs adds three more title mismatches, all
entries whose catalogue name is not the title on the paper:

- arXiv:2503.03704 (MINJA) is, in the version on file (v5, NeurIPS 2025),
  *Memory Injection Attacks on LLM Agents via Query-Only Interaction*; "A
  practical memory injection attack against LLM agents" is the v1 title. The
  bibliography must cite the published version.
- arXiv:2602.15198 is *Colosseum: Auditing Collusion in **Cooperative
  Multi-Agent Systems***, not "…among language-model agents".
- The dependency-guided rollback entry [7] (arXiv:2608.10502) is *From Faulty
  Memories to Corrected Actions: Dependency-Guided Rollback Repair for
  Memory-Augmented Agents*.

All eight are corrected before submission.
