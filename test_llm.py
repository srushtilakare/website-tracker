"""
Test script for LLM structured extraction using Mistral.
"""

import json
import sys

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

from llm_extractor import extract_structured_data


sample_text = """
Example University provides undergraduate and postgraduate education across Science, Engineering, and Business.
Its admissions department publishes application deadlines and academic requirements.
Applicants should consult the official admissions page for details.
Contact us at admissions@example.edu or phone +1-555-0199.
Campus Address: 123 University Ave, Silicon Valley, CA.
"""

print("Testing Mistral LLM Extraction...")
try:
    result = extract_structured_data(
        page_title="Admissions - Example University",
        page_text=sample_text,
        page_url="https://example.com/admissions",
    )

    print("\nLLM extraction result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("\n[SUCCESS] Test passed!")

except Exception as error:
    print(f"\n[ERROR] LLM extraction failed: {error}")
    sys.exit(1)
