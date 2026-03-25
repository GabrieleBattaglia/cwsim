import re

with open(r'e:\git\Mine\GBUtils\gbutils.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the start of the CWzator function
start_idx = content.find('def CWzator(')
if start_idx != -1:
    # Find the next def to mark the end, or end of file
    next_def_idx = content.find('\ndef ', start_idx + 1)
    if next_def_idx == -1:
        extracted = content[start_idx:]
    else:
        extracted = content[start_idx:next_def_idx]
        
    with open('cwzator_reference.py', 'w', encoding='utf-8') as f2:
        f2.write(extracted)
    print("Estrazione completata con successo.")
else:
    print("Funzione CWzator non trovata.")
