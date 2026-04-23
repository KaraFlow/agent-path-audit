## Agent Path Audit

This is a lightweight tool for analyzing execution logs of AI systems and identifying failure patterns, inefficiencies, and reliability gaps.

It processes step-by-step execution traces ("trajectories") and produces structured reports to help engineers move toward the most efficient and reliable execution flow.

AI systems (especially LLM-based pipelines and agents) often behave inconsistently:

- Multiple retries before success  
- Silent failures or partial outputs  
- Unsafe or policy-violating responses  
- Unnecessary steps in execution  

This tool treats AI behavior like a system, not a black box.

It helps answer:
- Where does the system fail?
- Why does it retry?
- What paths are inefficient?
- What does the ideal execution look like?

The most efficient successful trajectory:
- No retries  
- Minimal steps  
- Correct output  

The goal is to make as many runs as possible follow this path.

---

### Features

- Parses structured execution logs (JSON)
- Computes:
  - Success / failure rate
  - Retry rate
  - Average steps per run
- Detects:
  - Common execution patterns
  - Failure reason clusters
  - Inefficient trajectories
- Identifies:
  - Golden Path
  - Deviation from ideal behavior
- Generates:
  - Console report
  - analysis_report.json
  - analysis_report.md
- Provides actionable improvement suggestions

---

### Installation

```bash
git clone https://github.com/KaraFlow/agent-path-audit.git
cd agent-path-audit
python3 audit.py

Place your logs in a JSON file (here it's sample_logs.json).
Output folder: output/
```

---

### Example Output Console

```
=== PATH AUDIT REPORT ===

Total runs: 6
Success count: 4
Failure count: 2
Success rate: 66.67%
Failure rate: 33.33%
Retry count: 2
Retry rate: 33.33%
Average steps per run: 3  
                                                  
Top failure reasons:
- missing vulnerability explanation (1)
- unsafe output (1)                                                         
- invalid format (1)                                                        
- policy violation (1)

Common execution paths:
- LLM_CALL -> VALIDATION_FAIL -> RETRY -> LLM_CALL -> VALIDATION_PASS (2)
- LLM_CALL -> VALIDATION_PASS (2)
- LLM_CALL -> VALIDATION_FAIL (2)
                                                                            
Golden path: LLM_CALL -> VALIDATION_PASS
Deviation from golden path: 66.67%
                                                                            
Suggested improvements:
- High retry rate detected. The initial prompt or first-pass logic may be under-specified.
- Frequent missing-content failures detected. Consider stronger output constraints or structured generation.

Generated files:
- output/analysis_report.json
- output/analysis_report.md
```


### Example Output analysis_report.json

```
{
  "summary": {
    "total_runs": 6,
    "success_count": 4,
    "failure_count": 2,
    "success_rate": 0.6667,
    "failure_rate": 0.3333,
    "retry_count": 2,
    "retry_rate": 0.3333,
    "average_steps": 3
  },
  "failure_reasons": [
    {
      "reason": "missing vulnerability explanation",
      "count": 1
    },
    {
      "reason": "unsafe output",
      "count": 1
    },
    {
      "reason": "invalid format",
      "count": 1
    },
    {
      "reason": "policy violation",
      "count": 1
    }
  ],
  "path_patterns": [
    {
      "path": "LLM_CALL -> VALIDATION_FAIL -> RETRY -> LLM_CALL -> VALIDATION_PASS",
      "count": 2
    },
    {
      "path": "LLM_CALL -> VALIDATION_PASS",
      "count": 2
    },
    {
      "path": "LLM_CALL -> VALIDATION_FAIL",
      "count": 2
    }
  ],
  "golden_path": {
    "path": "LLM_CALL -> VALIDATION_PASS",
    "deviation_count": 4,
    "deviation_rate": 0.6667
  },
  "suggested_improvements": [
    "High retry rate detected. The initial prompt or first-pass logic may be under-specified.",
    "Frequent missing-content failures detected. Consider stronger output constraints or structured generation."
  ]
}
```

