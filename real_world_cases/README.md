# Real-World Cases

Save anonymized real-world traces here as beta users arrive.

For each case, include:

- anonymized trace JSON
- diagnosis output
- whether diagnosis was correct
- whether the fix worked
- notes from the user

If the case has a known expected answer, include this in the trace:

```json
{
  "expected_diagnosis": {
    "root_cause_category": "tool_selection",
    "failed_at_step": 2
  }
}
```
