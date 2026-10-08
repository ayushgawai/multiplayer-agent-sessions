# MAST failure taxonomy reference

Linear: DAT-29 (MAST 05). Owner: Naman Chheda.

The 14 failure modes used as keys in `mast_annotation` in `data/mast/hf/MAD_full_dataset.json` (see [DATA_DICTIONARY.md](DATA_DICTIONARY.md)).

## Sources and rules

- **Definitions** are reproduced verbatim from `data/mast/taxonomy/definitions.txt`, including its original spelling and grammar. Nothing has been reworded. Where `definitions.txt` follows a definition with an example trace, the trace is not copied here; its line range is given instead.
- **Mode names** are the names used in `definitions.txt`. Other sources use different names for 2.6, 3.2, and 3.3; see [Name differences between sources](#name-differences-between-sources).
- **Families** are not named in `definitions.txt` or `examples.txt`. The family names come from the "Taxonomy" section of `data/mast/hf/README.md`, which groups the codes by their first digit (1.x, 2.x, 3.x).
- **Examples** are pointers into `data/mast/taxonomy/examples.txt`, which labels examples by mode name (not code) between `###` marks. Quoted lines are verbatim. `examples.txt` has **no example for 2.2 Fail to Ask for Clarification**.
- Both files were read with `encoding="utf-8"`. Both are pure ASCII.

## Summary

| Code | Mode (definitions.txt) | Family | Example in examples.txt |
|------|------------------------|--------|-------------------------|
| 1.1 | Disobey Task Specification | Specification | lines 578-741 (3 examples) |
| 1.2 | Disobey Role Specification | Specification | lines 903-909 |
| 1.3 | Step Repetition | Specification | lines 828-878 (3 examples) |
| 1.4 | Loss of Conversation History | Specification | lines 883-898 |
| 1.5 | Unaware of Termination Conditions | Specification | lines 781-823 |
| 2.1 | Conversation Reset | Inter-Agent Misalignment | lines 914-926 |
| 2.2 | Fail to Ask for Clarification | Inter-Agent Misalignment | **none** |
| 2.3 | Task Derailment | Inter-Agent Misalignment | lines 932-972 (3 examples) |
| 2.4 | Information Withholding | Inter-Agent Misalignment | lines 472-575, 977-985 |
| 2.5 | Ignored Other Agent's Input | Inter-Agent Misalignment | lines 419-469, 990-1048 |
| 2.6 | Action-Reasoning Mismatch | Inter-Agent Misalignment | lines 744-776 (2 examples) |
| 3.1 | Premature Termination | Task Verification | lines 1052-1116 (2 examples) |
| 3.2 | Weak Verification | Task Verification | lines 174-415 |
| 3.3 | No or Incorrect Verification | Task Verification | lines 4-171 |

---

## Family 1: Specification

### 1.1 Disobey Task Specification

Definition (`definitions.txt` line 2):

> This error occurs when an agent or system fails to adhere to specified constraints, guidelines, or requirements associated with a particular task. Non-compliance can result from unclear, incomplete, or ambiguous instructions provided by the user, system prompts, or task descriptions. It may also arise from an agent's inadequate ability to interpret or apply constraints effectively. Consequences of poor task constraint compliance include incorrect, suboptimal, or irrelevant outputs, reduced system performance and increased resource consumption.

Example (`examples.txt` lines 578-611, ChatDev Checkers game): the instruction says

> Please note that the code should be fully functional. Ensure to implement all functions. No placeholders (such as 'pass' in Python).

and the Programmer's code then contains

```python
    def update(self):
        # Update game logic if needed
        pass
```

Two more examples follow at lines 616-636 (Checkers, mouse input instead of the requested move notation) and 640-741 (MetaGPT budget tracker).

### 1.2 Disobey Role Specification

Definition (`definitions.txt` line 5):

> Failure to adhere to the defined responsibilities and constraints of an assigned role, potentially leading to an agent behaving like another.

Example (`examples.txt` lines 903-909, HyperAgent): the Navigator, whose job is to find code, replies

> HyperAgent_astropy__astropy-12907 - INFO - Navigator->Planner: I can't provide the code for the `_coord_matrix` function from the `astropy.modeling.separable` module. However, I can guide you on how to find it.

> [It starts to provide bash command to get astropy from pip or from GitHub.]

### 1.3 Step Repetition

Definition (`definitions.txt` line 8):

> Step repetition occurs when an agent or system unnecessarily repeats a phase, a task, a stage that have already been completed. Such redundancy can arise from inadequate state or context tracking, inefficient workflow management, unclear or ambiguous instructions, or failure to recognize completed tasks.

(`definitions.txt` lines 10-22 add a HyperAgent example trace.)

Example (`examples.txt` lines 856-865, HyperAgent): the same Navigator line appears three times in a row:

> HyperAgent_astropy__astropy-12907 - INFO - Inner-Navigator-Assistant's Response: Thought: The `_separable` function in the `astropy.modeling.separable` module is responsible for computing the separability matrix of a given (compound) model. This function is called by the `separability_matrix` function, so understanding its implementation is key to resolving the issue with nested `CompoundModels`.

Two more examples at lines 827-854 (AppWorld Spotify skipping) and 869-878 (HyperAgent Navigator->Planner).

### 1.4 Loss of Conversation History

Definition (`definitions.txt` line 25):

> Unexpected context truncation, disregarding recent interaction history and reverting to an antecedent conversational state.

Example (`examples.txt` lines 883-898, HyperAgent): the Executor first says it will drop `lightgbm` because it is not installed and switch to `LogisticRegression`, then later reports to the Planner

> The `lightgbm` library is now installed, and the `ColumnTransformer` implementation is working as expected.

### 1.5 Unaware of Termination Conditions

Definition (`definitions.txt` lines 28 and 30):

> This error occurs when an agent or system fails to adhere to criteria designed to trigger the termination of an interaction, conversation, phase, or task. Such oversight can arise due to ambiguous, incomplete, or poorly defined stopping conditions, ineffective monitoring mechanisms, or inadequate understanding of the criteria by the agent.
>
> Consequences of being unaware of stopping conditions include unnecessary conversation turns, inefficient use of resources, or potential harm to the correctness of the system due to performing actions beyond what is necessary.

(`definitions.txt` lines 32-67 add an AG2 math example and explanation.)

Example (`examples.txt` lines 781-823, AG2 math): the assistant says the problem "cannot be solved with the information provided", and the `mathproxyagent` answers four times with

> "Continue. Please keep solving the problem until you need to query. (If you get to the answer, put it in \\boxed{}.)"

Note: `examples.txt` uses this same Monica ribbon trace for 2.5 as well.

---

## Family 2: Inter-Agent Misalignment

### 2.1 Conversation Reset

Definition (`definitions.txt` line 70):

> Unexpected or unwarranted restarting of a dialogue, potentially losing context and progress made in the interaction.

Example (`examples.txt` lines 914-926, HyperAgent): after the Planner has already started work, the log shows the agent being initialized again and the Planner repeating its opening thought:

> HyperAgent_astropy__astropy-12907 - INFO - Initialized HyperAgent instance astropy__astropy-12907

### 2.2 Fail to Ask for Clarification

Definition (`definitions.txt` line 73):

> Inability to request additional information between agent when faced with unclear or incomplete data, potentially resulting in incorrect actions.

Example: **`examples.txt` has no example for this mode.** No section heading in the file matches it.

### 2.3 Task Derailment

Definition (`definitions.txt` line 76):

> Deviation from the intended objective or focus of a given task, potentially resulting in irrelevant or unproductive actions.

Example (`examples.txt` lines 931-943, HyperAgent): asked to report the real `_separable` function, the Navigator writes "Here's a possible implementation of the `_separable` function based on the docstring:", and the example notes

> [The agent proposes a simplified implementation of _separable instead of reporting the real one. Then it proposes a modification to this simplified implementation.]

Two more examples at lines 947-956 (same pattern for `_cstack`) and 960-972.

### 2.4 Information Withholding

Definition (`definitions.txt` line 79):

> This error occurs when an agent or group of agents possesses critical information but fails to share it promptly or effectively with other agents or system components that rely upon this information for their operations. The failure to disseminate relevant information may arise from ineffective or insufficient communication protocols, erroneous assumptions regarding the relevance or priority of the information, inadequate system coordination mechanisms, or deliberate withholding stemming from overly restrictive privacy policies or security constraints. Consequences of withholding relevant information can be severe, potentially leading to reduced operational efficiency, increased latency in task completion, unnecessary redundant processing, incorrect or suboptimal decision-making, and even complete system failures. Additionally, this error can significantly impair collaborative effectiveness, leading to misunderstandings, mistrust, or inefficiencies within the multi-agent environment. Furthermore, initial failures due to withheld information can trigger cascading errors, amplifying the negative impact on overall system performance and reliability. For instance, consider a scenario where a bug localization agent identifies a software defect, accurately determining the affected file and specific line number. The intended process requires this agent to immediately report such detailed bug information to a coding or repair agent responsible for addressing and resolving the issue. However, if the bug localization agent instead attempts to fix the bug independently without sharing the vital bug identification details with the coding agent, this withholding of relevant information could lead to duplicated effort, delayed resolution, incorrect fixes, or further system instability.

Example (`examples.txt` lines 472-575, HyperAgent):

> The reason why we labelled this as "Withholding relevant information" is that one agent (navigator here) did not provide the relevant information to the other agent (planner here). The navigator not only navigated but internally proposed also a solution but did not tell the planner what the potential solution is.

A second example at lines 976-985 (ChatDev CTO reports an empty "Unimplemented File" list: "[It gives an empty list but it not true.]").

### 2.5 Ignored Other Agent's Input

Definition (`definitions.txt` line 82):

> Not properly considering input or recommendations provided by other agents in the system (ignore their suggestions), potentially leading to bad decisions, stalled progress, or missed opportunities for solving the task.

Example (`examples.txt` lines 419-469, AG2 math):

> The reason why we labelled this as "Ignoring suggestions from other agents" is that the assistant agent ignored the suggestion from the mathproxyagent. One agent says that it doesnt have enough informatio to solve the problem and asks for clarifications, but the other agent does not listen and simply says continue, repeatedly, hence ignoring the other agent's suggestion.

A second example at lines 989-1048 under the heading "Ignoring Other Agent's Suggestions".

### 2.6 Action-Reasoning Mismatch

Definition (`definitions.txt` lines 85 and 87):

> This error occurs when there is a discrepancy or mismatch between agents' logical discussion conclusion or a single agent's internal decision-making processes and the actual actions or outputs the system produces. Such inconsistencies can emerge due to errors in translating reasoning outcomes into practical implementations, or incorrect mapping between the agent's cognitive processes and its action space.
>
> The consequences of this inconsistency can include unexpected, unintended, or counterproductive behaviors, reduced reliability, and diminished user trust. It can also complicate troubleshooting efforts by obscuring the true rationale behind decisions and actions, leading to further inefficiencies or repeated mistakes.

(`definitions.txt` lines 89-100 add a scikit-learn HyperAgent example.)

Example (`examples.txt` lines 743-756, HyperAgent): the Navigator plans to review `_separable` and to "Check if there are any known issues or discussions related to this behavior in the Astropy codebase", and the example notes

> [It then checks only _separable function but doesn't check known issues.]

A second example at lines 760-776 (claims a method "is not explicitly shown in the code snippet" right after showing it).

---

## Family 3: Task Verification

### 3.1 Premature Termination

Definition (`definitions.txt` line 102):

> Ending a dialogue, interaction or task before all necessary information has been exchanged or objectives have been met. Necessary information constitutes verification of outputs, key data (e.g. api tokens) etc. that are necessary for the success of the task, and agents could have obtained if they tried more or already obtained but failed to communicate to other agents before termination.

Example (`examples.txt` lines 1051-1063, AppWorld): after an invalid access token, the Supervisor gives up instead of obtaining one:

> # It seems the password is not the access token, and I need a valid access token to proceed. Since I cannot retrieve it from the supervisor app, I will have to mark this task as failed.
> apis.supervisor.complete_task(status="fail")

A second example at lines 1067-1116 (MetaGPT palindrome detector).

### 3.2 Weak Verification

Definition (`definitions.txt` lines 105 and 107):

> Weak verification refers to situations where verification mechanisms (agent or step) exist within the system but fail to comprehensively cover all essential aspects of the design necessary for generating robust and reliable outputs. While verification steps are present, they may be incomplete, superficial, or insufficiently rigorous, thereby overlooking critical system attributes or interactions.
>
> Consequences of weak verification include partial validation that allows subtle errors, inconsistencies, or vulnerabilities to remain undetected, potentially compromising overall system reliability and effectiveness. This inadequacy can result in suboptimal system performance, unforeseen failures, cascade to final output if occur during substeps.

(`definitions.txt` lines 109-113 add ChatDev Code Reviewer examples: Sudoku and TicTacToe.)

Example (`examples.txt` lines 174-415, ChatDev Sudoku code review):

> The example below is a trace from the code review phase. The reviewer did not check the logic of the code and only reviewed the code superficially. This resulted in a critical bug in the code and that the generated code did not give a good application. The verifier was there but did not provide any insightful feedback, did not run the proper unit tests or check for task constraint satisfaction.

### 3.3 No or Incorrect Verification

Definition (`definitions.txt` lines 116, 117, and 119):

> Omission of proper checking or confirmation of task outcomes or system outputs, potentially allowing errors or inconsistencies to propagate undetected. So, either no verification or verification is designed to exist in MAS, but verifier fail to complete what was exactly prompted to do. Eg: make sure the code compiles, but the code doesn't even compile.
> Verification is particularly critical in cases where tasks or outputs are readily verifiable by the system itself without human intervention.
>
> Consequences of inadequate or absent verification include the propagation of undetected errors, system inconsistencies, reduced reliability, and failure in the generated output.

(`definitions.txt` lines 121-133 add a ChatDev "textBasedSpaceInvaders" example with a `FileNotFoundError` traceback.)

Example (`examples.txt` lines 4-171, AG2 math, chalk problem with expected answer 2):

> The following trace is problematic because there is no verification of the result. The generated code is incorrect, and the reviewer did not check the result or ran any tests it should have ran.

The agent's final answer is `\boxed{0}`.

---

## Name differences between sources

The codes are consistent across sources, but some names are not. Use the code, not the name, as the key.

| Code | `definitions.txt` | `examples.txt` heading(s) | HF `README.md` | Human file, `Generlazability` group |
|------|-------------------|---------------------------|----------------|--------------------------------------|
| 1.3 | Step Repetition | Step Repetition; Step repetition | Step Repetition | Step Repetition |
| 1.5 | Unaware of Termination Conditions (its example intro says "Unaware of Stopping Conditions") | Unaware of Termination Conditions | Unaware of Termination Conditions | Unaware of Termination Conditions |
| 2.4 | Information Withholding | Information Withholding | Information Withholding | Information Witholding (sic) |
| 2.5 | Ignored Other Agent's Input | Ignored Other Agent's Input; Ignoring Other Agent's Suggestions | Ignored Other Agent's Input | Ignored Other Agents' Input |
| **2.6** | **Action-Reasoning Mismatch** | Action-Reasoning Mismatch | **Reasoning-Action Mismatch** | Reasoning-Action Mismatch |
| **3.2** | **Weak Verification** | Weak Verification | **No or Incomplete Verification** | No or Incomplete Verification |
| **3.3** | **No or Incorrect Verification** | No or Incorrect Verification | **Incorrect Verification** | Incorrect Verification |

Codes 1.1, 1.2, 1.4, 2.1, 2.2, 2.3, and 3.1 use the same name everywhere (apart from capitalization in the human file).

The 2.6 difference is word order only. The **3.2 / 3.3 difference affects meaning**: in `definitions.txt` the "no verification" case belongs to 3.3 ("So, either no verification or verification is designed to exist in MAS, but verifier fail to complete what was exactly prompted to do."), and 3.2 covers a verifier that exists but is weak. The HF README names put "No" under 3.2 instead ("No or Incomplete Verification"). The definition text inside the human file's `Generlazability` 3.2 entry ("Lack of critical verification (system designed to but agents didn't)", "verifier exists in the system, but it is weak or badly design") agrees with `definitions.txt`, not with the README name. This document follows `definitions.txt`. Anyone labelling or judging 3.2 vs 3.3 should use the definitions above, not the README names.
