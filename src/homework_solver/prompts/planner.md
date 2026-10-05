Analyze the assignment in the previous user message (text and images).

Return a single JSON object with this shape:
{
  "assignment_type": "code" | "mcq" | "essay" | "mixed",
  "language": "vi" | "en" | other BCP-47 tag,
  "summary": "1-3 sentences",
  "output_spec": {
    "kind": "folder" | "markdown" | "answers" | "mixed",
    "notes": "how files should be named / laid out"
  },
  "tasks": [
    {
      "id": "t1",
      "title": "short title",
      "instructions": "what the solver must produce for this task",
      "kind": "code" | "mcq" | "essay",
      "allow_web_search": true,
      "success_criteria": "how to judge a good answer"
    }
  ]
}

Split into the smallest number of tasks that still covers the full assignment.
Set allow_web_search true only when external facts, APIs, or libraries likely need a lookup.
If the assignment is one coding project, use a single code task with output_spec.kind = "folder".
If it is only multiple-choice, use one mcq task and output_spec.kind = "answers".
If it is only a written response, use one essay task and output_spec.kind = "markdown".
