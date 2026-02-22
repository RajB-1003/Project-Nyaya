
with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

LANGUAGE_RULE = (
    "LANGUAGE RULE (CRITICAL -- FOLLOW FIRST):\n"
    "Detect the language the user wrote or spoke in. Respond in THAT SAME LANGUAGE for all text fields:\n"
    "simplified_explanation, immediate_action_steps, extracted_user_issue, follow_up_question.\n"
    "Examples: Tamil query -> Tamil response. Hindi query -> Hindi. Telugu, Kannada, Bengali,\n"
    "Malayalam, Marathi, Gujarati, Punjabi, Odia -> respond in that exact language.\n"
    "EXCEPTION: The 'relevant_acts' field MUST ALWAYS be in English (legal section numbers are official English terms).\n"
    "The 'intent_detected' value MUST ALWAYS be: RTI | Domestic Violence | Divorce | Unknown (English).\n"
    "\n"
)

MARKER = "YOUR CORE MISSION: Give SPECIFIC"

if MARKER in content:
    content = content.replace(MARKER, LANGUAGE_RULE + MARKER, 1)
    with open("main.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("PATCHED OK -- language rule added before CORE MISSION")
else:
    print("ERROR: marker not found")
    idx = content.find("SYSTEM_PROMPT")
    print(repr(content[idx : idx + 200]))
