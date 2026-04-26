#!/usr/bin/env python3
"""Parse pytest -v output and print score JSON to stdout."""
import re, json, sys

CHAIN_ISSUES = set(range(16, 21))
TEST_FILTERS = {
    1:'create_status', 2:'page_offset', 3:'search_case',
    4:'delete_status', 5:'websocket_unsubscribe', 6:'retry_check',
    7:'ws_close', 8:'schedule_order', 9:'audit_typo',
    10:'min_length', 11:'semaphore_leak', 12:'naive_datetime',
    13:'dep_eligibility', 14:'event_type', 15:'step_status',
    16:'chain_flush', 17:'chain_list', 18:'chain_run',
    19:'chain_step', 20:'chain_schedule',
}
TIERS = {**{i:1 for i in range(1,6)}, **{i:2 for i in range(6,11)},
         **{i:3 for i in range(11,16)}, **{i:4 for i in range(16,21)}}

txt = sys.stdin.read()
passed_fns = set(re.findall(r'PASSED\s+scoring/test_issues\.py::(test_\w+)', txt))

results = []
for num in range(1, 21):
    tf = TEST_FILTERS[num]
    fn = f'test_{num:02d}_{tf}'
    passed = fn in passed_fns
    results.append({'id': num, 'title': tf.replace('_', '-'), 'tier': TIERS[num], 'passed': passed})

fixed = sum(1 for r in results if r['passed'])
chain_passed = sum(1 for i in CHAIN_ISSUES if results[i-1]['passed'])
chain_bonus = 10 if chain_passed == 5 else (5 if chain_passed > 0 else 0)
final_score = min(110, fixed * 5 + chain_bonus)

out = {'fixed': fixed, 'total': 20, 'baseScore': fixed * 5,
       'chainBonus': chain_bonus, 'finalScore': final_score, 'results': results}
print(json.dumps(out))
