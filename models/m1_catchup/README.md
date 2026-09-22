# M1 Catch-up summarizer

Input: query + event-window transcript spans. Output: summary of what happened,
what is in progress, and what is blocked.

Training and inference scripts land with the bake-off. Configs live in
`eval/configs/m1-*.yaml`. Serving entrypoint: `serving/adapters/m1.py`.
