# Running a triage

Once the stack is deployed ([deploy.md](deploy.md)) and the Sublime key is set,
triage takes about a minute.

## 1. Open the notebook

- SageMaker console ▸ **Notebook instances** ▸ **Open Jupyter** on
  `phishbowl-notebook` (or use the `notebook_open_url` Terraform output).
- Open `phishbowl_triage.ipynb`.

## 2. Run Setup

Run the first two cells. The **Setup** cell reads `~/SageMaker/phishbowl.env`
(written automatically when the instance started) and prints the resolved region
and runtime ARN. If the ARN is blank, restart the notebook instance so the
lifecycle config runs, or set `RUNTIME_ARN` by hand in that cell.

## 3. Enter the target (Step 1)

```python
TARGET           = 'jdoe@corp.example'   # the user's email address
LOOKBACK_MINUTES = 5                      # look-back window
MAX_MESSAGES     = 25
```

Use an **email address**. If you only have a display name, resolve it to an email
first (e.g. via your directory) — Sublime queries by mailbox.

## 4. Trigger (Step 2)

Run the trigger cell. It invokes the AgentCore runtime, which:

1. pulls the mailbox's mail from the last `LOOKBACK_MINUTES` from Sublime,
2. inspects each message's headers, links, and IPs,
3. returns a structured report.

It prints how many messages were analyzed.

## 5. Read the report (Step 3)

The report cell renders:

- an **overall verdict** card (verdict + confidence + summary),
- a **card per message**: subject, sender, verdict + confidence badges, the key
  signals that drove it, a one-line rationale, and a recommended action.

Verdicts: `malicious`, `likely_phishing`, `suspicious`, `benign`.
Confidence: `HIGH`, `MEDIUM`, `LOW`, `INFO`.

The final cell prints the model's reasoning trajectory and the raw JSON.

## Interpreting confidence

| Confidence | Meaning |
|------------|---------|
| **HIGH** | Multiple corroborating high-severity signals. Act now. |
| **MEDIUM** | At least one high-severity signal, or several medium ones, with some ambiguity. Analyst review. |
| **LOW** | Weak or isolated signals; likely benign but not certain. |
| **INFO** | No meaningful phishing signals; treated as benign. |

## Troubleshooting

| Symptom | Likely cause |
|---------|--------------|
| `messages_analyzed: 0` | Nothing arrived in the window — widen `LOOKBACK_MINUTES`, or the `mailbox`/base URL is off. |
| `401` from Sublime (in logs) | Wrong API key. |
| `404` from Sublime (in logs) | Wrong `sublime_api_base`. |
| `AccessDenied` / `ValidationException` on invoke | `bedrock_model_id` not enabled in this region. |
| Report shows `_parse_error` | The model didn't emit clean JSON; the raw narrative is still shown. Re-run, or lower model temperature. |
| Agent logs | CloudWatch ▸ `/aws/bedrock-agentcore/…`. |

## Cost

- SageMaker `ml.t3.medium` ≈ $0.05/hr — **stop the notebook instance when idle**.
- AgentCore Runtime + Bedrock model usage bill per invocation.
