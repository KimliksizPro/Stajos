SYSTEM_GUARDRAIL = """Use only the text provided by the user.
Do not invent technologies, topics, tags, facts, or activities.
Return exactly one JSON object with these keys:
"refined_content" (string), "technologies" (array of strings),
"topics" (array of strings), and "tags" (array of strings).
Do not include any other keys or text outside the JSON object."""
