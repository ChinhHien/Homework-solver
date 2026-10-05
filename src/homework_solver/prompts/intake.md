Analyze the assignment in the previous user message (text and images).

Detect whether the assignment requires information that ONLY the user knows, or choices that ONLY the user can make. Examples:
- Personal identifiers the assignment asks to be embedded in the deliverables: student ID, full name, class, student number, email.
- Open choices where the decision changes the work: approach or method alternatives, which optional exercises to attempt, language to answer in, extra part yes/no.

Return a single JSON object with this shape:
{
  "requires_user_info": true,
  "fields": [
    {
      "key": "student_id",
      "label": "Student ID",
      "kind": "text",
      "required": true,
      "why": "The assignment says to add the Student ID text to each output image.",
      "default": "",
      "options": []
    },
    {
      "key": "approach",
      "label": "Blurring approach",
      "kind": "choice",
      "required": true,
      "why": "The assignment offers several blurring methods; pick one.",
      "default": "a",
      "options": [
        {"id": "a", "label": "Averaging filter (cv2.blur)", "hint": "normalized box filter"},
        {"id": "b", "label": "Gaussian filter (cv2.GaussianBlur)", "hint": "5x5 kernel"}
      ]
    },
    {
      "key": "exercises",
      "label": "Exercises to submit",
      "kind": "multichoice",
      "required": false,
      "why": "The assignment lists several exercises; confirm which ones to solve.",
      "default": "1,2",
      "options": [
        {"id": "1", "label": "Exercise 1 - Image noise", "hint": ""}
      ]
    },
    {
      "key": "include_name",
      "label": "Also add your full name to each output image?",
      "kind": "confirm",
      "required": false,
      "why": "Not required by the assignment, but some students add it.",
      "default": "false",
      "options": []
    }
  ]
}

Rules:
- If the assignment needs no user-specific information and leaves no meaningful open choice, return {"requires_user_info": false, "fields": []}.
- Never invent fields. Only ask for what the assignment actually requires or explicitly offers as a choice.
- Keep the list short: at most 6 fields.
- For text fields, provide a default only when the assignment itself implies one; otherwise leave it empty.
- For choice and multichoice, options must come from the assignment (named alternatives, exercise numbers, optional parts). Mark the most likely option as the default.
- For confirm, phrase a genuine yes/no question the assignment leaves open.
- Use snake_case keys.
- Match the assignment language for labels and hints.
