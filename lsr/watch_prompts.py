watch_code_prompt = """
I've written your instructions in LaTeX comments and marked them with "% AI"
You can see the "AI" comments shown below (marked with █).
Find them in the LaTeX files I've shared with you, and follow their instructions.

After completing those instructions, also be sure to remove all the "AI" comments from the LaTeX files too.
"""

watch_ask_prompt = """/ask
Find the "AI" comments below (marked with █) in the LaTeX files I've shared with you.
They contain my questions that I need you to answer and other instructions for you.
"""
