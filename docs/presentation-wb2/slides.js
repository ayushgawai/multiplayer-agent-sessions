/* Workbook 2 deck. Audience and presenter both load this file.
   Notes: first paragraph(s) are spoken word for word. Blue "qa" blocks are answers to likely questions. */
const who = (name, secs) => `<span class="who">${name} speaks · about ${secs} s</span>`;
const qa = (q, a) => `<span class="qa"><b>If asked: ${q}</b><br>${a}</span>`;
const tag = (name) => `<div class="speaker">${name}</div>`;

window.DECK = [
  {
    rubric: "Title · Ayush",
    title: "Workbook 2: the data and the models",
    notes: [
      who("AYUSH", 30) + "Good afternoon. We are Team 4, and our project is a shared live session where several people and several agents work in one workspace.",
      "Workbook 2 is sections three and four of the report: how the data is collected and prepared, and which models we build and how we will judge them.",
      "One thing up front. We have no model results yet, and we will not show any. Everything today is real data, a working prototype, and rules committed before results. Manav will start with the prototype.",
      qa("Why no results yet?", "The template leaves 4.5 and 4.6 for the final report on 7 December. The M1 contract (ADR-005) also forbids a selection run until the annotated product-session split is frozen, and that split does not exist yet."),
      qa("What changed since Workbook 1?", "Two things, both in the carry-forward table. The M1 candidates are now BM25, ModernBERT, Phi-4-mini and Qwen3.5-4B. And M1 is selected on critical-fact recall behind safety gates, not on ROUGE-L alone.")
    ],
    html: `
      <div class="title-stage">
        <p class="kicker">Team 4 · DATA 298A · Workbook 2 · 12 November 2026</p>
        <h1>The data is frozen.<br>The rules are committed.</h1>
        <p class="lede">Report sections 3 and 4: data engineering and model development for a shared human-agent session.</p>
        <div class="tape"><b>3</b> data sources <b>4</b> models <b>1</b> reproduced baseline <b>0</b> results claimed</div>
      </div>${tag("Ayush")}`
  },
  {
    rubric: "Prototype · Manav",
    title: "The prototype runs against the real service",
    notes: [
      who("MANAV", 40) + "This is the client running against our real session service. On the left, two people are editing the same document at the same time. Their edits merge through a CRDT, so nobody's change is lost.",
      "On the right is the session event log. After we roll back to event two, the two instructions are removed for everyone in the session.",
      "That log is the source of our own data, and the input our first model reads. Naman will explain the data.",
      qa("Is the model output shown in the client?", "No. The client does not call or display any model yet. The serving adapters are stubs behind a frozen interface until a bake-off winner is locked."),
      qa("Is this deployed in the cloud?", "Not yet. It runs locally with Docker Compose: PostgreSQL, Redis, the session service and serving. Cloud deployment is deferred to the 298B study, when people outside the team need access."),
      qa("Why a CRDT and an event log, both?", "The CRDT (Yjs) makes concurrent text edits converge. It cannot order agent commands or undo them. The event log gives total order, audit, interruption and rollback.")
    ],
    html: `
      <p class="kicker">Working today, on main</p>
      <div class="sheet reveal">
        <h2>Two people, one document, one ordered log</h2>
        <div class="pair">
          <div><img class="shot" src="figures/crdt_two_tabs.png" alt="Two browser tabs editing the same document"><p class="cap">Concurrent editing through a Yjs CRDT. Each edit is also a doc_update event.</p></div>
          <div><img class="shot" src="figures/rollback_before_after.png" alt="Event log before and after a rollback"><p class="cap">Rollback to seq 2 removes two events for everyone in the session.</p></div>
        </div>
      </div>${tag("Manav")}`
  },
  {
    rubric: "3.1 Data Process · Naman",
    title: "Three sources, five steps",
    notes: [
      who("NAMAN", 40) + "We use three data sources, and each answers a different question. MAST is the corpus of the published baseline we reproduce. QMSum is supervision for Model 1 only. Product sessions, recorded on our own platform, are the only source that contains our real task, and they select the winner.",
      "Every source goes through the same five steps: collect, pre-process, transform, prepare, and describe. Blue is built and on main. Amber is planned.",
      "Public data is rebuilt from pinned versions, nothing is dropped silently, and test data is read only once.",
      qa("Why is the product-session row amber?", "No session has been recorded yet, because the end-to-end integration gate has not been passed. The risk trigger from Workbook 1 has fired and the fallback is in effect: internal sessions plus 18 scripted smoke examples."),
      qa("Why keep the three paths separate?", "MAST has two label sources, judge labels on 1,642 traces and human labels on 19. Mixing paths is how a baseline number gets scored against the wrong labels.")
    ],
    html: `
      <p class="kicker">3.1 Data process</p>
      <div class="sheet reveal">
        <h2>Each path is pinned and frozen separately</h2>
        <img class="shot" src="figures/fig03_data_process.png" alt="Data process and lineage for three sources">
      </div>${tag("Naman")}`
  },
  {
    rubric: "3.2 and 3.3 · Naman",
    title: "Collected in full, cleaned with rules that run",
    notes: [
      who("NAMAN", 40) + "For collection, we retrieved all 1,642 MAST traces, which is exactly the number in the paper, and 232 QMSum meetings with 1,810 query and summary pairs. Every file is verified by a SHA-256 checksum.",
      "For pre-processing, every rule is code, and every rule reports what it removed. In total we removed four records from MAST, which had no labels at all, and none from QMSum.",
      "The important rule is this one: a missing label stays missing. We never read it as a zero, because a missing judgement is not a negative judgement.",
      qa("Only four rows removed. Did you really clean the data?", "Yes. Both are curated research releases, so the value is the guarantee, not the volume: unique record keys, label domain 0, 1 or null over 22,988 cells, and ten quality gates that pass. The four excluded traces are named in the committed summary."),
      qa("Workbook 1 said 1,808 QMSum pairs.", "That is the paper's figure. The pinned release yields 1,810: 1,576 specific and 234 general queries. It is corrected in the carry-forward table."),
      qa("Which tools?", "download_mast.py, download_qmsum.py, eda_mast.py and make_splits.py, plus pytest checks in CI.")
    ],
    html: `
      <p class="kicker">3.2 Data collection · 3.3 Pre-processing</p>
      <div class="sheet reveal">
        <h2>The counts match the papers, and the rules report their effect</h2>
        <div class="nums">
          <div class="num">1,642<span>MAST traces, equal to the paper</span></div>
          <div class="num">1,810<span>QMSum query pairs, 232 meetings</span></div>
          <div class="num">4<span>records removed, all 14 labels null</span></div>
          <div class="num">0<span>invalid labels in 22,988 cells</span></div>
        </div>
        <table>
          <tr><th>Rule</th><th>Effect on the pinned data</th></tr>
          <tr><td>Checksum and record count equal the pinned values</td><td>Pass, 0 removed</td></tr>
          <tr><td>Record key (trace.key, trace_id) is unique</td><td>1,642 unique, 0 duplicates</td></tr>
          <tr><td>A null label stays null, never 0</td><td>56 null cells preserved</td></tr>
          <tr><td>Exclude a record only if all 14 labels are null</td><td>4 removed (0.24%)</td></tr>
          <tr><td>QMSum: non-empty query, context, summary; unique ids</td><td>0 removed of 1,810</td></tr>
        </table>
      </div>${tag("Naman")}`
  },
  {
    rubric: "3.4 Transformation · Shriram",
    title: "Same facts, a shape the model can use",
    notes: [
      who("SHRIRAM", 35) + "Transformation changes the shape of the data, not what it says.",
      "For MAST, we flatten the nested labels into a table of 1,638 rows and 26 columns.",
      "For QMSum, each query becomes one example, and each piece of context becomes an ordered event with a stable id. That is the same shape as a live session, which is why every claim a model makes can cite the events it came from. The reference summary is kept outside the input, so the answer cannot leak.",
      qa("Why turn meeting transcripts into events?", "All four M1 candidates must consume one input contract, m1-input-v1, which is also what live sessions produce. One adapter in the evaluation layer does the mapping, so no candidate invents its own."),
      qa("Why drop the trajectory text from the MAST table?", "The analysis table is 142 KB instead of 199.6 MB. The full text is read from the pinned file when the judge needs it.")
    ],
    html: `
      <p class="kicker">3.4 Data transformation</p>
      <div class="sheet reveal">
        <h2>Every transformation has a reason</h2>
        <table>
          <tr><th>From</th><th>To</th><th>Why</th></tr>
          <tr><td>MAST nested labels</td><td>14 label columns, failure count, 3 category counts (1,638 × 26)</td><td>A flat table can be aggregated and compared with the paper</td></tr>
          <tr><td>QMSum meeting with many queries</td><td>One example per query (1,810 rows)</td><td>Model 1 answers one query at a time</td></tr>
          <tr><td>Context spans</td><td>Ordered events with stable ids</td><td>Same shape as a live session, so claims can cite events</td></tr>
          <tr><td>Reference summary</td><td>Kept outside the input</td><td>A target inside the input leaks the answer</td></tr>
        </table>
        <div class="cmd">{"event_id": "qmsum_test_9_s3:span:0000", "sequence": 0, "event_type": "doc_update", "text": "Grad B: And they wouldn't look pretty . So ."}</div>
      </div>${tag("Shriram")}`
  },
  {
    rubric: "3.5 and 3.6 · Manav",
    title: "Frozen splits, checked for leakage",
    notes: [
      who("MANAV", 45) + "The Model 1 splits are frozen and version controlled, with a checksum for each file: 1,257 training rows, 272 validation and 281 test.",
      "We split by whole meeting, so no meeting appears in two splits. We checked, and nothing is shared. We did find two duplicated reference summaries in the original release, four rows out of 1,810, and we report them.",
      "The statistics shaped our metrics. Summaries are short, about 65 words, so one missing fact is a large part of the answer. And in MAST the labels are very imbalanced, from 40 percent down to under 2 percent, so accuracy alone would mislead.",
      qa("Did you stratify?", "No. We inherit the official QMSum partition by meeting, which keeps our numbers comparable with the literature. Because we did not stratify, we checked that the three splits have the same distributions, and they do."),
      qa("Why leave the duplicate summaries in?", "They are upstream duplicates with different queries and transcripts. Removing them would change the published partition. They are 0.22% of rows and are disclosed."),
      qa("Who is disadvantaged by these gaps?", "QMSum is English meeting speech, so other languages and terse tool-and-code sessions are not covered. MAST has agents only, with no multi-human steering, which is exactly our target. That is why product sessions, not QMSum, select the winner."),
      qa("Where is the correlation plot?", "Workbook Figure 9. All 91 label pairs are positively correlated, from 0.04 to 0.66; the strongest is step repetition with unawareness of termination, 0.66.")
    ],
    html: `
      <p class="kicker">3.5 Data preparation · 3.6 Data statistics</p>
      <div class="sheet reveal">
        <h2>1,257 / 272 / 281, and no meeting crosses a split</h2>
        <div class="pair">
          <div><img class="shot" src="figures/fig6_qmsum_distributions.png" alt="QMSum distributions by split"><p class="cap">Model 1 data: the three splits overlap closely. Summaries are short; context is long-tailed.</p></div>
          <div><img class="shot" src="figures/fig06_mast_prevalence.png" alt="MAST failure mode prevalence"><p class="cap">MAST: 14 failure modes range from 40.5% to 1.5% of traces.</p></div>
        </div>
      </div>${tag("Manav")}`
  },
  {
    rubric: "4.1 Model Proposals · Ayush",
    title: "Four models, sixteen candidates, one baseline",
    notes: [
      who("AYUSH", 45) + "We propose four models. Model 1 catches up a person who joins late. Model 2 decides who an instruction is for. Model 3 arbitrates when two people redirect the same agent. Model 4 breaks a task down and routes it.",
      "Each model is a bake-off of four candidates, always including a simple control with no learned model. So that is sixteen candidates, plus the published MAST judge that we reproduce, which is deliberately not one of the four.",
      "What is new is in Model 1. Its output is structured, and every claim must cite the session events that support it. A claim without evidence is invalid.",
      qa("Which model is innovative?", "Model 1. Three things: evidence-cited output by construction; selection that is safety-gated before it is quality-ranked; and approved memory that can change behaviour but can never be used as evidence."),
      qa("Why these four M1 candidates?", "Each neighbouring pair isolates one question. BM25 to ModernBERT changes only the ranker: the value of learned relevance. ModernBERT to Phi-4-mini moves from copying to writing: the value and risk of generation. Phi-4-mini to Qwen3.5-4B changes only capacity."),
      qa("Why QLoRA and small models?", "One 16 GB GPU in the university lab, at zero cost. 4-bit quantisation with adapters fits, and adapter-only checkpoints survive an interrupted session."),
      qa("Has any candidate been trained?", "Only feasibility. ModernBERT ran a 40-step smoke on the GPU with checkpoint and resume, and 10 of 10 outputs parsed. That is not a result and is not in the workbook as one.")
    ],
    html: `
      <p class="kicker">4.1 Model proposals</p>
      <div class="sheet reveal">
        <h2>Every model has a control it must beat</h2>
        <table>
          <tr><th>Model</th><th>Problem it removes</th><th>Candidates (control first)</th><th>Built</th></tr>
          <tr><td><b>M1</b> catch-up</td><td>A late joiner cannot cheaply learn the state</td><td>BM25 · ModernBERT · Phi-4-mini QLoRA · Qwen3.5-4B QLoRA</td><td>298A</td></tr>
          <tr><td><b>M2</b> intent attribution</td><td>Unclear whom an instruction addresses</td><td>TF-IDF · DeBERTaV3 · ModernBERT · Qwen head</td><td>298B</td></tr>
          <tr><td><b>M3</b> merge arbitration</td><td>Two people redirect one agent</td><td>Last-writer-wins · ModernBERT · Qwen LoRA · few-shot Qwen</td><td>298B</td></tr>
          <tr><td><b>M4</b> decompose and route</td><td>Subtasks assigned by availability</td><td>Rules · planner + learned router · planner · single prompt</td><td>298B</td></tr>
          <tr><td><b>Baseline</b> MAST judge</td><td>Do we measure failures correctly?</td><td>Published: accuracy 0.94, F1 0.80, kappa 0.77</td><td>298A</td></tr>
        </table>
        <p class="warn">New in Model 1: every claim cites the events that support it. No evidence, no claim.</p>
      </div>${tag("Ayush")}`
  },
  {
    rubric: "4.2 Model Supports · Ayush",
    title: "The platform, and why it is local",
    notes: [
      who("AYUSH", 45) + "This is the supporting platform: the client and session service on top, the agent runtime and one prediction endpoint per model below, then data, training on one lab GPU, and a single evaluation layer.",
      "We were asked to consider AWS and Airflow. We evaluated both and decided not to use them this semester. Our two datasets are static and pinned, so nothing is scheduled. The pipeline is four steps in a line and runs in about six seconds on a laptop. And training is free on the university GPU.",
      "We will adopt them when the workload asks for it: when sessions are recorded more often than weekly, and when people outside the team join in 298B.",
      qa("Then how do you monitor the pipeline?", "Every run writes 19 quality checks and a per-stage run history, with start time, duration, rows in and out, status and git commit, into the warehouse. The pipeline tests run in CI, so a broken stage is a red check on the pull request."),
      qa("Why not at least run Airflow locally?", "It needs a metadata database, a scheduler and a web server to run four functions on data that never changes. Each stage is a plain function, so wrapping it in an Airflow task later is mechanical. The first step up will be a scheduled GitHub Actions job."),
      qa("How would it map to AWS?", "Raw files to S3, stage functions to Airflow tasks, DuckDB schemas to Redshift or Athena. The checkpoint utility is being extended to accept s3:// paths (PR #32)."),
      qa("Is DuckDB really a data warehouse?", "It is a columnar analytical database. We use it with raw, staging and marts layers and a star schema: four dimensions and three fact tables.")
    ],
    html: `
      <p class="kicker">4.2 Model supports</p>
      <div class="sheet reveal">
        <h2>Owners talk through a network call or a committed file</h2>
        <div class="pair" style="grid-template-columns:1.25fr 0.75fr">
          <div><img class="shot" src="figures/fig11_platform_architecture.png" alt="Platform architecture"></div>
          <div>
            <table>
              <tr><th>AWS and Airflow?</th><th>Our workload</th></tr>
              <tr><td>Scheduled?</td><td>No. Static, pinned data</td></tr>
              <tr><td>Complex graph?</td><td>Four steps in a line</td></tr>
              <tr><td>Large?</td><td>220 MB, about 6 s</td></tr>
              <tr><td>GPU?</td><td>University lab, $0</td></tr>
            </table>
            <p class="warn">Adopt when ingestion recurs or outside users join (298B).</p>
          </div>
        </div>
      </div>${tag("Ayush")}`
  },
  {
    rubric: "4.3 and 4.4 · Pramod",
    title: "Safety first, then quality",
    notes: [
      who("PRAMOD", 45) + "This is how a winner is chosen for Model 1, and it was committed before any result exists.",
      "First, a candidate must finish all three seeds. Second, it must pass the safety gates on every single seed: at most two percent unsupported claims, at least 95 percent correct attribution and status, and at least 98 percent valid outputs. Only then do we rank, on critical-fact recall first, then BERTScore, then ROUGE-L.",
      "Our preferred model is a generative one. It loses if it invents claims on even one seed, or if it only ties BM25, because the faster model then wins. If nothing passes, nothing is promoted.",
      qa("Why is ROUGE-L not the primary metric?", "Summaries are about 65 words. A summary can score well on overlap and still omit the one blocker, or assign an action to the wrong person. ROUGE-L is still reported and still used to break ties, after the gates."),
      qa("Metrics for the other models?", "M2: macro-F1 with per-class F1. M3: macro-F1, harmful-merge rate, escalation precision and recall. M4: DAG validity as a gate, then routing accuracy, completion, latency and cost. Baseline: accuracy, precision, recall, F1 and Cohen's kappa against the 19 human-labelled traces, with a 95% interval."),
      qa("Why three seeds?", "Seeds 13, 29 and 47. We report each seed and the mean, never pooled. The gates apply per seed so one unsafe run cannot hide behind two good ones."),
      qa("Is the harness finished?", "No. It is in review (DAT-61). Review found the comparison step applying gates to the three-seed mean, which the contract forbids, so it is being fixed before merge.")
    ],
    html: `
      <p class="kicker">4.3 Comparison and justification · 4.4 Evaluation methods</p>
      <div class="sheet reveal">
        <h2>A fluent answer that invents a fact cannot win</h2>
        <img class="shot" src="figures/fig13_selection_rule.png" alt="Model 1 selection rule" style="flex:0 1 46%">
        <table style="margin-top:0.6rem">
          <tr><th>Gate, on every seed</th><th>Threshold</th><th>Then rank by</th></tr>
          <tr><td>Unsupported claims</td><td>at most 2%, and no worse than BM25</td><td>1. Critical-fact recall</td></tr>
          <tr><td>Attribution and status</td><td>at least 95% each</td><td>2. BERTScore-F1</td></tr>
          <tr><td>Valid structured output</td><td>at least 98%</td><td>3. ROUGE-L, then latency and memory</td></tr>
        </table>
      </div>${tag("Pramod")}`
  },
  {
    rubric: "4.5 Pipeline demo · Shriram",
    title: "From source to warehouse, live",
    notes: [
      who("SHRIRAM", 50) + "Now the pipeline, live. I will run one command. It ingests both datasets from the pinned sources and checks the checksums. It cleans and validates them. It transforms them into a small star schema in a local warehouse. And it runs nineteen quality checks.",
      "SWITCH TO THE TERMINAL. Run: python infra/warehouse/pipeline.py. It takes about six seconds. Point at the four stages as they print, and at the line that says all checks passed.",
      "Then run it a second time and run the report command. The report shows the run history: two runs, each stage with its duration and its rows in and out. That history is our monitoring.",
      qa("What if a stage fails?", "The run stops at that stage, the failure is written to the run history with the error, and the exit code is non-zero. Tables are replaced on each run, so a rerun after a fix gives the same warehouse as a clean run."),
      qa("What is in the warehouse?", "Raw: 1,642 traces and 1,810 examples. Staging: 1,638 clean traces and 22,932 label rows. Marts: fact_trace 1,638, fact_trace_failure 5,141, fact_m1_example 1,810, and four dimension tables."),
      qa("Does your own session data flow into it?", "Not yet. No session has been recorded, so the export from the PostgreSQL event log is the one ingestion path that does not exist. It is in the carry-forward table."),
      qa("If the demo breaks", "Fall back to the committed transcript: infra/warehouse/SAMPLE_RUN.md. Before the meeting, run download_mast.py once so the raw file is on the laptop.")
    ],
    html: `
      <p class="kicker">Data pipeline demo</p>
      <div class="sheet reveal">
        <h2>Ingest, transform, load, check, and keep a history</h2>
        <div class="row four">
          <div class="lane"><b>1</b><h3>Ingest</h3><p>Pinned sources, SHA-256 verified, landed in raw.</p></div>
          <div class="lane"><b>2</b><h3>Clean</h3><p>Validated into staging. 4 records excluded.</p></div>
          <div class="lane"><b>3</b><h3>Transform</h3><p>Star schema in marts: 3 facts, 4 dimensions.</p></div>
          <div class="lane"><b>4</b><h3>Monitor</h3><p>19 quality checks and per-stage run history.</p></div>
        </div>
        <div class="cmd">python infra/warehouse/pipeline.py<br>python infra/warehouse/pipeline.py --report</div>
      </div>${tag("Shriram")}`
  },
  {
    rubric: "Close · Pramod",
    title: "What is not done, and when",
    notes: [
      who("PRAMOD", 30) + "To close, here is what is not done. No product session is recorded yet, and that is our critical dependency, because it selects the Model 1 winner. The evaluation harness is in review. The MAST judge has not been run. And the Model 1 bake-off is at risk for this semester.",
      "The final report on December seventh will carry either a winner, or the documented shortfall.",
      "Thank you. We are happy to take questions.",
      qa("What is your biggest risk?", "The session corpus. Sessions need the end-to-end integration gate, annotation needs sessions, splits need annotation. If it slips, we shorten collection, not the freeze date."),
      qa("What if the MAST baseline does not reproduce?", "Check the prompt and scoring code before the model. The paper's zero-shot figure is 0.89, so few-shot matters. MultiAgentBench is the documented fallback. If the gap stays, we report it."),
      qa("Who does what?", "Ayush: platform, serving, Model 1. Naman: data, Model 2. Manav: client, Model 3. Shriram: agent runtime, Model 4. Pramod: evaluation and the MAST baseline.")
    ],
    html: `
      <p class="kicker">Carry-forward and next steps</p>
      <div class="sheet reveal">
        <h2>The session corpus is the critical dependency</h2>
        <table>
          <tr><th>Open item</th><th>Status</th><th>Owner</th></tr>
          <tr><td>Product-session corpus</td><td>0 sessions; fallback in effect</td><td>Naman</td></tr>
          <tr><td>Shared evaluation harness</td><td>In review; per-seed gate fix</td><td>Pramod</td></tr>
          <tr><td>Model 1 bake-off and winner</td><td>At risk; needs the session split</td><td>Ayush</td></tr>
          <tr><td>MAST judge runs</td><td>Tooling done; judge not yet run</td><td>Ayush, Shriram, Pramod</td></tr>
          <tr><td>Cloud deployment</td><td>Deferred to the 298B study</td><td>Ayush</td></tr>
        </table>
        <p class="muted" style="margin-top:auto">Final report, 7 December: a winner, or the documented shortfall.</p>
      </div>${tag("Pramod")}`
  }
];
