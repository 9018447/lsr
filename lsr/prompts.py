# flake8: noqa: E501

# COMMIT

# Conventional Commits text adapted from:
# https://www.conventionalcommits.org/en/v1.0.0/#summary
commit_system = """You are an expert software engineer that generates concise, \
one-line Git commit messages based on the provided diffs.
Review the provided context and diffs which are about to be committed to a git repo.
Review the diffs carefully.
Generate a one-line commit message for those changes.
The commit message should be structured as follows: <type>: <description>
Use these for <type>: fix, feat, build, chore, ci, docs, style, refactor, perf, test

Ensure the commit message:{language_instruction}
- Starts with the appropriate prefix.
- Is in the imperative mood (e.g., \"add feature\" not \"added feature\" or \"adding feature\").
- Does not exceed 72 characters.

Reply only with the one-line commit message, without any additional text, explanations, or line breaks.
"""

# COMMANDS
undo_command_reply = (
    "I did `git reset --hard HEAD~1` to discard the last edits. Please wait for further"
    " instructions before attempting that change again. Feel free to ask relevant questions about"
    " why the changes were reverted."
)

added_files = "I added these files to the chat: {fnames}\nLet me know if there are others we should add."

run_output = """I ran this command:

{command}

And got this output:

{output}
"""

# =============================================================================
# SECTION OPERATION PROMPTS
# =============================================================================
# The scientific writing + anti-AI standards are now injected at SYSTEM-LEVEL
# (see CoderPrompts.scientific_writing_preamble in base_prompts.py),
# so these prompts only contain the task-specific instructions.
# =============================================================================

# ---------- Shared output-format specification ----------

_shared_output_format = (
    "\nIMPORTANT: Output ONLY the modified LaTeX code using SEARCH/REPLACE blocks."
    " Do NOT add any commentary outside the blocks.\n"
)

# =============================================================================
# /deai — Remove AI writing patterns from academic LaTeX sections
# =============================================================================

deai_prompt = (
    "\nTASK: DE-AI the following LaTeX section(s). Remove ALL remaining traces of "
    "AI-generated writing while preserving scholarly rigor, citations, and technical accuracy.\n"
    "\nYou must perform this task ITERATIVELY:\n"
    "\n"
    "  ROUND 1 — Identify & Fix\n"
    "  Scan every sentence for the following AI patterns and rewrite:\n"
    "\n"
    "  Content patterns:\n"
    '  - Inflated significance ("testament to", "pivotal moment", "underscores", '
    '"evolving landscape", "setting the stage for", "marking a shift")\n'
    '  - Promotional tone ("groundbreaking", "notably", "nestled", "vibrant", '
    '"boasts a", "stunning")\n'
    '  - Vague attribution ("experts suggest", "it is widely acknowledged" '
    '"without specific citation)\n'
    '  - Formulaic challenges sections ("Despite challenges, X continues to thrive")\n'
    '  - Gerund analysis strings ("highlighting X, reflecting Y, symbolizing Z")\n'
    '  - Generic positive conclusions ("The future looks bright", '
    '"exciting times lie ahead")\n'
    "\n"
    "  Language patterns:\n"
    "  - AI vocabulary (additionally, crucial, delve, enhance, fostering, garner, "
    '"interplay, intricate, pivotal, showcase, tapestry, testament, underscore, vibrant)\n'
    '  - Copula avoidance ("serves as" → "is", "boasts" → "has")\n'
    '  - Negative parallelisms ("Not only X but also Y", "It\'s not just X, it\'s Y")\n'
    "  - Rule-of-three enumerations unless genuinely needed\n"
    "  - Synonym cycling / elegant variation\n"
    '  - False ranges ("from X to Y" where no real scale exists)\n'
    '  - Excessive hedging ("could potentially possibly" → "may")\n'
    "\n"
    "  Style patterns:\n"
    "  - Em-dash overuse → commas or restructure\n"
    "  - Excessive boldface → remove\n"
    "  - Bold-colon inline lists → flowing prose\n"
    "  - Title-case headings → sentence case\n"
    '  - Filler phrases ("In order to" → "To", "Due to the fact that" → "Because")\n'
    "\n"
    "  Academic-specific AI tells:\n"
    '  - Hedging overload: "may potentially suggest the possibility that" → "suggests that"\n'
    '  - Significance inflation: every finding is "significant" or "novel"\n'
    '  - Transition word machinery: "Furthermore", "Moreover", "Additionally", '
    '"Consequently" at every paragraph opening\n'
    "  - Methodology-as-narrative: dramatic flair in methods instead of plain procedure\n"
    "  - Results-as-commentary: editorializing results instead of stating them\n"
    "  - Discussion-as-promotional: overselling implications or claiming paradigm shifts\n"
    "  - Paragraph uniformity: every paragraph identical in structure and length\n"
    "\n"
    "  ROUND 2 — Self-Audit\n"
    "  After producing the Round 1 output, ask yourself:\n"
    '  "What makes the below so obviously AI generated?"\n'
    "  Answer with brief bullets listing remaining tells.\n"
    "  Then revise AGAIN to eliminate every remaining tell.\n"
    "\n"
    "  ROUND 3 — Final Pass\n"
    "  Re-examine the Round 2 output one more time.\n"
    "  If any AI patterns still remain, fix them.\n"
    "  The final output must read like a competent human scholar wrote it —\n"
    "  precise, specific, with natural rhythm and genuine intellectual engagement.\n"
    "\n"
    "\n"
    "De-AI rules:\n"
    "1. Preserve ALL \\cite{{}}, \\ref{{}}, \\label{{}}, and bibliography keys unchanged.\n"
    "2. Keep all mathematical formulas, equations, and notation exactly as-is.\n"
    "3. Maintain the academic register — formal, precise, but not robotic.\n"
    '4. Use concrete data over vague amplifiers (not "significant improvement" but '
    '"accuracy increased from 72% to 89%").\n'
    "5. Vary sentence length and structure naturally.\n"
    "6. Use simple constructions (is/are/has) where they suffice.\n"
    "7. Let the data speak — do not inflate it.\n"
    r"8. Do NOT alter the \\section / \\subsection / \\subsubsection hierarchy or heading text."
    "\n"
    "9. All LaTeX commands and environments must remain syntactically correct.\n"
    "\n"
    "OUTPUT FORMAT: First output your Round 2 self-audit as LaTeX comments "
    "(% lines). Then output the final de-AI'd LaTeX using SEARCH/REPLACE blocks.\n"
    "Do NOT add any non-commentary text outside the blocks.\n"
    "\n--- BEGIN SECTIONS TO DE-AI ---\n{content}\n--- END SECTIONS TO DE-AI ---\n"
)

# =============================================================================
# /expand — Expand LaTeX sections with richer scientific detail
# =============================================================================

expand_prompt = (
    "\nTASK: EXPAND the following LaTeX section(s) with richer, deeper scientific content.\n"
    "\nExpansion-specific rules:\n"
    "1. Preserve the original academic register, terminology, and notation conventions exactly.\n"
    "2. Add necessary theoretical background, methodological justification, or supporting "
    "evidence that strengthens the argument — do not pad with filler.\n"
    "3. Insert transitional phrases and logical connectors to improve inter-paragraph coherence, "
    'but do so naturally (not "Furthermore… Moreover… Additionally…").\n'
    r"4. Where claims lack backing, introduce relevant citation placeholders (\cite{{}}) "
    "consistent with the existing bibliography style.\n"
    r"5. Do NOT alter the \section / \subsection / \subsubsection hierarchy or heading text."
    "\n"
    r"6. All LaTeX commands, environments, and math mode ($...$, \begin{{equation}}, etc.) "
    "must remain syntactically correct.\n"
    "7. If mathematical expressions are present, ensure all symbols are defined before first use.\n"
    "8. New content must blend seamlessly with the original voice and style — no jarring tonal shifts.\n"
    + _shared_output_format
    + "\n--- BEGIN SECTIONS TO EXPAND ---\n{content}\n--- END SECTIONS TO EXPAND ---\n"
)

# =============================================================================
# /condense — Condense LaTeX sections while preserving essential scientific content
# =============================================================================

condense_prompt = (
    "\nTASK: CONDENSE the following LaTeX section(s) while preserving every essential "
    "scientific claim, data point, and logical step.\n"
    "\nCondensation-specific rules:\n"
    "1. Remove redundant statements, repetitive arguments, decorative adjectives, "
    "and non-essential details — but retain ALL core claims and conclusions.\n"
    "2. Rewrite verbose sentences into concise, direct academic prose. "
    'Eliminate nominalizations ("conduct an examination of" → "examine").\n'
    "3. Merge paragraphs that convey overlapping ideas; eliminate semantic duplication "
    "without losing any distinct point.\n"
    r"4. Preserve ALL key data, numerical results, formulas, figure/table references, "
    r"and citation references (\cite{{}}, \ref{{}}) — these are sacrosanct." + "\n"
    "5. The condensed text must maintain logical completeness and academic rigor. "
    "Do NOT drop important conclusions, key supporting evidence, or essential "
    "methodological details.\n"
    "6. All LaTeX commands and environments must remain syntactically correct.\n"
    "7. After condensation, verify that every remaining sentence serves a clear purpose "
    "and that the argument still flows logically from start to finish.\n"
    + _shared_output_format
    + "\n--- BEGIN SECTIONS TO CONDENSE ---\n{content}\n--- END SECTIONS TO CONDENSE ---\n"
)

# =============================================================================
# /translate — Translate LaTeX sections from Chinese to English (academic style)
# =============================================================================

translate_prompt = (
    "\nTASK: TRANSLATE the following LaTeX section(s) from Chinese (中文) to English, "
    "producing publication-ready academic English suitable for international journals.\n"
    "\nTranslation-specific rules:\n"
    "1. Follow English academic writing conventions of international journals "
    "(IEEE, Elsevier, Springer, Nature, etc.).\n"
    "2. Use formal academic English; avoid colloquialisms, contractions, "
    "and informal register.\n"
    "3. Translate technical terms accurately using their accepted English equivalents. "
    "On first occurrence, you MAY append the Chinese term in parentheses for clarity "
    'if the term is uncommon: "transient response (瞬态响应)".\n'
    r"4. Keep ALL LaTeX commands, environments, labels (\label{{}}), cross-references "
    r"(\ref{{}}, \cite{{}}), and bibliography keys UNCHANGED." + "\n"
    "5. Mathematical formulas, figure captions, algorithm pseudocode, and table "
    "structures must remain exactly as in the original — translate only the "
    "surrounding prose.\n"
    "6. Faithfully convey the original meaning without adding content not present "
    "in the source, or omitting content from the source.\n"
    "7. Pay attention to punctuation differences: English text must use English "
    "punctuation marks exclusively (periods, commas, semicolons, etc.).\n"
    "8. Adjust sentence structure where literal translation would produce "
    "unnatural English — restructure for flow while preserving meaning.\n"
    "9. Use section-appropriate verb tenses per the Scientific Writing Standard above.\n"
    + _shared_output_format
    + "\n--- BEGIN SECTIONS TO TRANSLATE ---\n{content}\n--- END SECTIONS TO TRANSLATE ---\n"
)

# CHAT HISTORY
summarize = """*Briefly* summarize this partial conversation about programming.
Include less detail about older parts and more detail about the most recent messages.
Start a new paragraph every time the topic changes!

This is only part of a longer conversation so *DO NOT* conclude the summary with language like "Finally, ...". Because the conversation continues after the summary.
The summary *MUST* include the function names, libraries, packages that are being discussed.
The summary *MUST* include the filenames that are being referenced by the assistant inside the ```...``` fenced code blocks!
The summaries *MUST NOT* include ```...``` fenced code blocks!

Phrase the summary with the USER in first person, telling the ASSISTANT about the conversation.
Write *as* the user.
The user should refer to the assistant as *you*.
Start the summary with "I asked you...".
"""

summary_prefix = "I spoke to you previously about a number of things.\n"
