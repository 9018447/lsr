#!/usr/bin/env python
"""HTML generation for /note command.

Generates self-contained HTML with kami-style styling, highlight/comments,
and MathJax support for LaTeX formula rendering.
"""

import html
import os


def generate_note_html(filename, paragraphs, port=0):
    """Generate a kami-style HTML file for reviewing LaTeX sections.

    Args:
        filename: Source .tex filename
        paragraphs: list of dicts from extract_text_environments()
        port: Local server port (injected into JS for POST requests)

    Returns:
        Path to the generated HTML file (in ~/.lsr/tmp/)
    """
    # Build sections from paragraphs
    sections = {}
    for para in paragraphs:
        sec = para["section"]
        if sec not in sections:
            sections[sec] = []
        sections[sec].append(para)

    # Generate section HTML
    sections_html = []
    for sec_name, paras in sections.items():
        paras_html = []
        for para in paras:
            if para.get("is_html"):
                # Raw HTML (e.g. converted tables) — skip escaping
                paras_html.append(
                    f'<div class="paragraph table-paragraph" '
                    f'data-section="{html.escape(sec_name)}" '
                    f'data-para-id="{para["para_id"]}">{para["text"]}</div>'
                )
            else:
                escaped = html.escape(para["text"])
                # Restore HTML tags we created (bold, italic, underline)
                escaped = escaped.replace("&lt;b&gt;", "<b>").replace("&lt;/b&gt;", "</b>")
                escaped = escaped.replace("&lt;i&gt;", "<i>").replace("&lt;/i&gt;", "</i>")
                escaped = escaped.replace("&lt;u&gt;", "<u>").replace("&lt;/u&gt;", "</u>")
                # Preserve newlines as <br>
                escaped = escaped.replace("\n", "<br>")
                paras_html.append(
                    f'<p class="paragraph" data-section="{html.escape(sec_name)}" '
                    f'data-para-id="{para["para_id"]}">{escaped}</p>'
                )
        sections_html.append(
            f'<div class="section" data-section="{html.escape(sec_name)}">'
            f'<h2 class="section-title">{html.escape(sec_name)}</h2>'
            f'{"".join(paras_html)}</div>'
        )

    body_html = "\n".join(sections_html)

    return _write_html(filename, body_html, port)


def _write_html(filename, body_html, port):
    """Write the complete HTML file."""
    content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Note Review: {html.escape(filename)}</title>
<script>
MathJax = {{
  tex: {{
    inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
    displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
    processEscapes: true
  }},
  options: {{
    skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'code']
  }}
}};
</script>
<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js" async></script>
<style>
:root {{
  --parchment: #f5f4ed;
  --ivory: #faf9f5;
  --warm-sand: #e8e6dc;
  --brand: #1B365D;
  --brand-light: #2D5A8A;
  --near-black: #141413;
  --dark-warm: #3d3d3a;
  --olive: #504e49;
  --stone: #6b6a64;
  --border: #e8e6dc;
  --border-soft: #e5e3d8;
  --serif: Charter, Georgia, Palatino, "Times New Roman", "Source Han Serif SC", "Noto Serif CJK SC", serif;
}}

* {{ margin: 0; padding: 0; box-sizing: border-box; }}

body {{
  font-family: var(--serif);
  font-size: 10pt;
  line-height: 1.6;
  color: var(--near-black);
  background: var(--parchment);
  padding: 0;
}}

header {{
  position: sticky;
  top: 0;
  z-index: 100;
  background: var(--ivory);
  border-bottom: 1px solid var(--border);
  padding: 12pt 24pt;
  display: flex;
  justify-content: space-between;
  align-items: center;
}}

header h1 {{
  font-size: 16pt;
  font-weight: 500;
  color: var(--near-black);
}}

.actions {{
  display: flex;
  gap: 8pt;
}}

button {{
  font-family: var(--serif);
  font-size: 10pt;
  padding: 6pt 16pt;
  border: 1px solid var(--border);
  border-radius: 3pt;
  cursor: pointer;
  transition: all 0.15s;
}}

#approve-btn {{
  background: var(--brand);
  color: white;
  border-color: var(--brand);
}}

#approve-btn:hover {{
  background: var(--brand-light);
}}

#cancel-btn {{
  background: var(--warm-sand);
  color: var(--dark-warm);
}}

#cancel-btn:hover {{
  background: var(--border);
}}

main {{
  max-width: 720pt;
  margin: 0 auto;
  padding: 24pt;
}}

.section {{
  margin-bottom: 24pt;
}}

.section-title {{
  font-size: 14pt;
  font-weight: 500;
  color: var(--near-black);
  border-left: 2.5pt solid var(--brand);
  border-radius: 1.5pt;
  padding-left: 8pt;
  margin-bottom: 12pt;
}}

.paragraph {{
  padding: 8pt 12pt;
  margin-bottom: 6pt;
  border-radius: 3pt;
  cursor: pointer;
  transition: background 0.15s;
  position: relative;
}}

.paragraph:hover {{
  background: var(--ivory);
}}

.paragraph.highlighted {{
  background: #fef3c7;
  border-left: 3pt solid #f59e0b;
}}

.paragraph.has-comment {{
  border-right: 3pt solid var(--brand);
}}

.paragraph .comment-dot {{
  position: absolute;
  right: -8pt;
  top: 50%;
  transform: translateY(-50%);
  width: 8pt;
  height: 8pt;
  background: var(--brand);
  border-radius: 50%;
  display: none;
}}

.paragraph.has-comment .comment-dot {{
  display: block;
}}

/* Comment selection popup */
#selection-popup {{
  display: none;
  position: absolute;
  background: var(--ivory);
  border: 1px solid var(--border);
  border-radius: 4pt;
  padding: 6pt 10pt;
  box-shadow: 0 2pt 8pt rgba(0,0,0,0.1);
  z-index: 200;
  font-size: 9pt;
}}

#selection-popup button {{
  background: var(--brand);
  color: white;
  border: none;
  padding: 4pt 10pt;
  font-size: 9pt;
  cursor: pointer;
  border-radius: 2pt;
}}

/* Comment panel */
#comment-panel {{
  position: fixed;
  right: 0;
  top: 0;
  bottom: 0;
  width: 320pt;
  background: var(--ivory);
  border-left: 1px solid var(--border);
  overflow-y: auto;
  padding: 16pt;
  transform: translateX(100%);
  transition: transform 0.2s;
  z-index: 150;
}}

#comment-panel.open {{
  transform: translateX(0);
}}

#comment-panel .panel-header {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12pt;
  padding-bottom: 8pt;
  border-bottom: 1px solid var(--border);
}}

#comment-panel .panel-header h3 {{
  font-size: 12pt;
  font-weight: 500;
  color: var(--near-black);
  margin: 0;
}}

#comment-panel .close-btn {{
  background: none;
  border: none;
  font-size: 16pt;
  cursor: pointer;
  color: var(--stone);
  padding: 2pt 6pt;
  line-height: 1;
}}

#comment-panel .close-btn:hover {{
  color: var(--near-black);
}}

.comment-item {{
  background: var(--parchment);
  border: 1px solid var(--border);
  border-radius: 4pt;
  padding: 10pt;
  margin-bottom: 8pt;
}}

.comment-item .comment-section {{
  font-size: 9pt;
  color: var(--brand);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.4pt;
  margin-bottom: 4pt;
}}

.comment-item .comment-highlight {{
  font-size: 9pt;
  color: var(--olive);
  font-style: italic;
  margin-bottom: 6pt;
  border-left: 2pt solid var(--border);
  padding-left: 6pt;
}}

.comment-item .comment-text {{
  font-size: 10pt;
  color: var(--near-black);
}}

.comment-item .comment-delete {{
  font-size: 8pt;
  color: var(--stone);
  cursor: pointer;
  float: right;
}}

.comment-item .comment-delete:hover {{
  color: #dc2626;
}}

/* Comment input modal */
#comment-modal {{
  display: none;
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.3);
  z-index: 300;
  justify-content: center;
  align-items: center;
}}

#comment-modal.open {{
  display: flex;
}}

#comment-modal .modal-content {{
  background: var(--ivory);
  border-radius: 6pt;
  padding: 20pt;
  width: 400pt;
  max-width: 90vw;
}}

#comment-modal textarea {{
  width: 100%;
  min-height: 80pt;
  font-family: var(--serif);
  font-size: 10pt;
  padding: 8pt;
  border: 1px solid var(--border);
  border-radius: 3pt;
  resize: vertical;
  margin-top: 8pt;
}}

#comment-modal .modal-actions {{
  margin-top: 12pt;
  display: flex;
  justify-content: flex-end;
  gap: 8pt;
}}

/* Status message */
#status-msg {{
  display: none;
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: var(--ivory);
  border: 2pt solid var(--brand);
  border-radius: 6pt;
  padding: 24pt 32pt;
  font-size: 14pt;
  color: var(--brand);
  z-index: 400;
  text-align: center;
}}

/* Toggle panel button */
#toggle-panel {{
  position: fixed;
  right: 16pt;
  bottom: 16pt;
  width: 32pt;
  height: 32pt;
  border-radius: 50%;
  background: var(--brand);
  color: white;
  border: none;
  font-size: 14pt;
  cursor: pointer;
  z-index: 160;
  display: flex;
  align-items: center;
  justify-content: center;
}}

#toggle-panel:hover {{
  background: var(--brand-light);
}}

/* Table rendering */
.table-paragraph {{
  padding: 0;
  margin-bottom: 12pt;
}}

.table-paragraph table {{
  border-collapse: collapse;
  width: 100%;
  margin: 12pt 0;
  font-family: var(--serif);
  font-size: 10pt;
}}

.table-paragraph th,
.table-paragraph td {{
  border: 1px solid var(--border);
  padding: 6pt 10pt;
  text-align: left;
  vertical-align: top;
}}

.table-paragraph th {{
  background: var(--warm-sand);
  font-weight: 600;
}}

.table-paragraph caption {{
  font-style: italic;
  margin-bottom: 6pt;
  color: var(--olive);
  text-align: left;
}}
</style>
</head>
<body>

<header>
  <h1>{html.escape(filename)}</h1>
  <div class="actions">
    <button id="cancel-btn" onclick="cancelNote()">Cancel</button>
    <button id="approve-btn" onclick="approveNote()">Approve</button>
  </div>
</header>

<main>
{body_html}
</main>

<div id="selection-popup">
  <button onclick="addComment()">Add Comment</button>
</div>

<div id="comment-panel">
  <div class="panel-header">
    <h3>Comments</h3>
    <button class="close-btn" onclick="togglePanel(false)" title="Close panel">&times;</button>
  </div>
  <div id="comment-list"></div>
</div>

<div id="comment-modal">
  <div class="modal-content">
    <div style="font-size:10pt; color:var(--olive); font-style:italic;" id="modal-highlight"></div>
    <textarea id="comment-input" placeholder="Enter your comment..."></textarea>
    <div class="modal-actions">
      <button onclick="closeModal()">Cancel</button>
      <button id="approve-btn" onclick="saveComment()">Save</button>
    </div>
  </div>
</div>

<div id="status-msg"></div>

<button id="toggle-panel" onclick="togglePanel()">N</button>

<script>
const PORT = {port};
const FILENAME = "{html.escape(filename)}";

// State
const comments = [];
let selectedText = "";
let selectedPara = null;
let selectionRange = null;

// Paragraph click for highlighting
document.querySelectorAll('.paragraph').forEach(p => {{
  p.addEventListener('click', function(e) {{
    if (e.target.closest('.comment-dot')) return;
    this.classList.toggle('highlighted');
  }});
}});

// Text selection for comments
document.addEventListener('mouseup', function(e) {{
  const sel = window.getSelection();
  if (!sel.rangeCount || sel.isCollapsed) {{
    document.getElementById('selection-popup').style.display = 'none';
    return;
  }}

  const range = sel.getRangeAt(0);
  const para = range.startContainer.parentElement?.closest('.paragraph');
  if (!para) {{
    document.getElementById('selection-popup').style.display = 'none';
    return;
  }}

  selectedText = sel.toString().trim();
  selectedPara = para;
  selectionRange = range.cloneRange();

  if (selectedText.length > 0) {{
    const popup = document.getElementById('selection-popup');
    const rect = range.getBoundingClientRect();
    popup.style.display = 'block';
    popup.style.left = (rect.left + window.scrollX) + 'px';
    popup.style.top = (rect.bottom + window.scrollY + 8) + 'px';
  }}
}});

function addComment() {{
  document.getElementById('selection-popup').style.display = 'none';
  const modal = document.getElementById('comment-modal');
  document.getElementById('modal-highlight').textContent = '"' + selectedText.substring(0, 100) + (selectedText.length > 100 ? '...' : '') + '"';
  document.getElementById('comment-input').value = '';
  modal.classList.add('open');
  document.getElementById('comment-input').focus();
}}

function closeModal() {{
  document.getElementById('comment-modal').classList.remove('open');
}}

function saveComment() {{
  const text = document.getElementById('comment-input').value.trim();
  if (!text) return;

  const section = selectedPara.dataset.section;
  const paraId = selectedPara.dataset.paraId;

  comments.push({{
    section: section,
    para_id: parseInt(paraId),
    text: text,
    highlight: selectedText
  }});

  selectedPara.classList.add('has-comment');
  renderComments();
  closeModal();
  togglePanel(true);
}}

function deleteComment(idx) {{
  comments.splice(idx, 1);
  // Update paragraph classes
  document.querySelectorAll('.paragraph').forEach(p => {{
    const sec = p.dataset.section;
    const pid = parseInt(p.dataset.paraId);
    const hasComment = comments.some(c => c.section === sec && c.para_id === pid);
    p.classList.toggle('has-comment', hasComment);
  }});
  renderComments();
}}

function renderComments() {{
  const list = document.getElementById('comment-list');
  if (comments.length === 0) {{
    list.innerHTML = '<p style="color:var(--stone); font-size:9pt;">No comments yet. Select text to add comments.</p>';
    return;
  }}
  list.innerHTML = comments.map((c, i) => `
    <div class="comment-item">
      <span class="comment-delete" onclick="deleteComment(${{i}})">✕</span>
      <div class="comment-section">${{c.section}}</div>
      <div class="comment-highlight">"${{c.highlight.substring(0, 60)}}${{c.highlight.length > 60 ? '...' : ''}}"</div>
      <div class="comment-text">${{c.text}}</div>
    </div>
  `).join('');
}}

function togglePanel(forceOpen) {{
  const panel = document.getElementById('comment-panel');
  if (forceOpen === true) {{
    panel.classList.add('open');
  }} else if (forceOpen === false) {{
    panel.classList.remove('open');
  }} else {{
    panel.classList.toggle('open');
  }}
}}

// Escape key closes panel
document.addEventListener('keydown', function(e) {{
  if (e.key === 'Escape') {{
    const panel = document.getElementById('comment-panel');
    const modal = document.getElementById('comment-modal');
    if (modal.classList.contains('open')) {{
      closeModal();
    }} else if (panel.classList.contains('open')) {{
      togglePanel(false);
    }}
  }}
}});

async function approveNote() {{
  if (comments.length === 0) {{
    if (!confirm('No comments added. Approve anyway?')) return;
  }}

  const data = {{
    file: FILENAME,
    comments: comments
  }};

  try {{
    const resp = await fetch(`http://localhost:${{PORT}}/approve`, {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify(data)
    }});

    if (resp.ok) {{
      showStatus('Comments submitted! You can close this tab.');
    }} else {{
      showStatus('Error submitting comments. Check lsr terminal.');
    }}
  }} catch (err) {{
    showStatus('Error: ' + err.message);
  }}
}}

async function cancelNote() {{
  try {{
    await fetch(`http://localhost:${{PORT}}/cancel`, {{ method: 'POST' }});
  }} catch (err) {{}}
  showStatus('Cancelled. You can close this tab.');
}}

function showStatus(msg) {{
  const el = document.getElementById('status-msg');
  el.textContent = msg;
  el.style.display = 'block';
}}

// Init
renderComments();
</script>
</body>
</html>"""

    # Write to temp file
    lsr_home = os.path.join(os.path.expanduser("~"), ".lsr", "tmp")
    os.makedirs(lsr_home, exist_ok=True)

    # Sanitize filename
    import re
    safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", os.path.splitext(filename)[0])
    tmp_path = os.path.join(lsr_home, f"lsr_note_{safe_name}.html")

    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(content)

    return tmp_path
