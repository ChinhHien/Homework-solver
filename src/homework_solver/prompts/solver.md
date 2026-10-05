Solve ONLY the task below. Use the assignment in the first user message as source of truth.

You may call the web_search tool if the task allows it and you need a fact, formula, library API, or similar problem statement. Do not search for trivia you already know.

After you are done, return a single JSON object:
{
  "task_id": "<same as given>",
  "files": [{"path": "relative/path.ext", "content": "full file contents"}],
  "answers": [{"id": "1", "choice": "A", "explanation": "short"}],
  "essay": "full written answer if kind is essay",
  "notes": "optional"
}

Rules for files:
- Use paths relative to the output folder (e.g. src/main.py, requirements.txt).
- Every file must be complete. Do not use placeholders like TODO or "...".
- Include only files needed for this task.

If kind is mcq, fill answers and leave files empty.
If kind is essay, fill essay and leave files empty unless the assignment asks for extra files.
If kind is code, fill files; essay may be a brief README body if useful.
