import sys
import os
import json

# Add the directory containing coderabbit_ai_formatter.py to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from coderabbit_ai_formatter import format_ai_prompts, get_language_from_filename

# Dummy parsed_comments data
dummy_comments = [
    {
        'file': 'src/main.go',
        'line': 10,
        'action': 'The variable `x` is unused.',
        'type': 'linter_fix',
        'priority': 'low',
        'suggestions': [],
        'detailed_instruction': 'The variable `x` is declared but never used. Please remove it to clean up the code.',
        'full_comment': 'Linter: unused variable x'
    },
    {
        'file': 'src/utils.js',
        'line': 25,
        'action': 'Replace `var` with `const` or `let`.',
        'type': 'format_fix',
        'priority': 'medium',
        'suggestions': ['const myVar = 1;'],
        'detailed_instruction': 'The use of `var` is outdated. Replace it with `const` if the variable is not reassigned, or `let` if it is.',
        'full_comment': 'Code style: use const/let instead of var'
    }
]

# Test with gemini_format=True
gemini_formatted_prompts = format_ai_prompts(dummy_comments, gemini_format=True)

print(json.dumps(gemini_formatted_prompts, indent=2))
