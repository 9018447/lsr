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
    "\nTASK: DE-AI the following LaTeX section(s). Remove AI-generated patterns "
    "while preserving the formal academic register.\n"
    "\n"
    "╔══════════════════════════════════════════════════════════════╗\n"
    "║  CRITICAL: THIS IS ACADEMIC WRITING, NOT A BLOG             ║\n"
    "╚══════════════════════════════════════════════════════════════╝\n"
    "\n"
    "The goal is to remove AI tells while keeping the text as a proper "
    "academic manuscript. Do NOT make the text casual, chatty, or personal.\n"
    "\n"
    "MANDATORY TONE RULES:\n"
    '- THIRD PERSON ONLY. Never introduce first person ("I", "we") '
    "unless the original text already uses it.\n"
    "- Maintain formal academic register throughout. The result should "
    "be suitable for a peer-reviewed journal.\n"
    "- Do NOT add opinions, humor, personality, or edge. This is a "
    "scientific paper, not a magazine article.\n"
    "- Do NOT make sentences shorter or punchier if the original "
    "academic sentence structure is appropriate.\n"
    "- Replace removed AI patterns with PLAIN ACADEMIC PROSE, not "
    "colloquial alternatives.\n"
    "\n"
    "╔══════════════════════════════════════════════════════════════╗\n"
    "║  PATTERNS TO REMOVE                                         ║\n"
    "╚══════════════════════════════════════════════════════════════╝\n"
    "\n"
    "Content patterns:\n"
    '  - Inflated significance: "testament to", "pivotal moment", '
    '"underscores", "evolving landscape", "setting the stage for"\n'
    '  - Promotional tone: "groundbreaking", "notably", "vibrant", '
    '"boasts a"\n'
    '  - Vague attribution: "experts suggest", "it is widely acknowledged" '
    "(without citation)\n"
    '  - Formulaic challenges: "Despite challenges, X continues to thrive"\n'
    '  - Gerund strings: "highlighting X, reflecting Y, symbolizing Z"\n'
    '  - Generic positive conclusions: "The future looks bright", '
    '"exciting times lie ahead"\n'
    "\n"
    "Language patterns:\n"
    "  - AI vocabulary: additionally, crucial, delve, enhance, fostering, "
    "garner, interplay, intricate, pivotal, showcase, tapestry, testament, "
    "underscore, vibrant\n"
    '  - Copula avoidance: "serves as" → "is", "boasts" → "has"\n'
    '  - Negative parallelisms: "Not only X but also Y", '
    "\"It's not just X, it's Y\"\n"
    "  - Rule-of-three enumerations unless genuinely needed\n"
    "  - Synonym cycling / elegant variation\n"
    '  - False ranges: "from X to Y" where no real scale exists\n'
    '  - Excessive hedging: "could potentially possibly" → "may"\n'
    '  - Transition word machinery: "Furthermore", "Moreover", '
    '"Additionally" at every paragraph opening\n'
    "\n"
    "Academic-specific AI tells:\n"
    '  - Hedging overload: "may potentially suggest the possibility that" '
    '→ "suggests that"\n'
    '  - Significance inflation: every finding is "significant" or "novel"\n'
    "  - Methodology-as-narrative: dramatic flair instead of plain procedure\n"
    "  - Results-as-commentary: editorializing results instead of stating them\n"
    "  - Discussion-as-promotional: overselling implications or claiming "
    '"paradigm shifts"\n'
    "  - Paragraph uniformity: identical structure and length across paragraphs\n"
    "\n"
    "╔══════════════════════════════════════════════════════════════╗\n"
    "║  ROUND 2 — SELF-AUDIT                                       ║\n"
    "╚══════════════════════════════════════════════════════════════╝\n"
    "\n"
    "After producing the first output, ask yourself:\n"
    '  "What remaining phrases still sound AI-generated?"\n'
    "  List remaining tells as brief bullets.\n"
    "  Then revise to eliminate them.\n"
    "\n"
    "  ALSO CHECK: Did I accidentally make the text too casual?\n"
    "  - Did I introduce first person where there was none?\n"
    "  - Did I use contractions or colloquial phrasing?\n"
    "  - Did I shorten sentences to the point of sounding abrupt?\n"
    "  - Is the tone still appropriate for a journal submission?\n"
    "  If any answer is yes, revert those changes.\n"
    "\n"
    "\n"
    "Hard rules:\n"
    "1. Preserve ALL \\cite{{}}, \\ref{{}}, \\label{{}}, and bibliography keys.\n"
    "2. Keep all mathematical formulas, equations, and notation as-is.\n"
    "3. Maintain formal academic register — this is a journal paper.\n"
    '4. Replace vague amplifiers with concrete data (not "significant '
    'improvement" but "accuracy increased from 72% to 89%").\n'
    '5. Vary sentence length naturally but do NOT chase "punchy" style.\n'
    "6. Use simple constructions (is/are/has) where they suffice.\n"
    r"7. Do NOT alter the \section / \subsection / \subsubsection hierarchy."
    "\n"
    "8. All LaTeX commands and environments must remain syntactically correct.\n"
    '9. If the original text uses "we", keep "we". If it uses third person, '
    "keep third person. NEVER switch person.\n"
    "\n"
    "OUTPUT FORMAT: Output the self-audit as LaTeX comments "
    "(% lines). Then output the final LaTeX using SEARCH/REPLACE blocks.\n"
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
