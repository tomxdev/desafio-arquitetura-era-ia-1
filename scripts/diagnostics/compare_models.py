"""F01: compara as saídas dos quatro modelos do provider simulado nas quatro tarefas.

Chama o provider-fake direto (http://localhost:8090), sem passar pela aplicação, numa amostra
fixa de tickets de data/tickets.jsonl (só leitura). Grava um CSV por tarefa e um resumo em
docs/evidence/f01/models-compare/. Usa só a biblioteca padrão.

    python scripts/diagnostics/compare_models.py [--sample 40] [--suggest-sample 5]
"""

import argparse
import csv
import json
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "evidence" / "f01" / "models-compare"
PROVIDER = "http://localhost:8090"
KEYS = {"openai": "sk-fake-openai-0001", "anthropic": "sk-ant-fake-0001"}
MODELS = [
    ("openai", "gpt-fake-large"),
    ("anthropic", "claude-fake-large"),
    ("openai", "gpt-fake-mini"),
    ("anthropic", "claude-fake-mini"),
]
ORDER_IN_TEXT = re.compile(r"#\d{6}")


def call(provider: str, model: str, task: str, content: str) -> tuple[str, float]:
    message = f"TASK: {task}\n{content}"
    if provider == "openai":
        url = f"{PROVIDER}/openai/v1/chat/completions"
        body = {"model": model, "messages": [{"role": "user", "content": message}]}
        headers = {"Authorization": f"Bearer {KEYS['openai']}"}
    else:
        url = f"{PROVIDER}/anthropic/v1/messages"
        body = {"model": model, "max_tokens": 2000, "messages": [{"role": "user", "content": message}]}
        headers = {"x-api-key": KEYS["anthropic"], "anthropic-version": "2023-06-01"}
    request = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), method="POST",
                                     headers={"Content-Type": "application/json", **headers})
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=120) as response:
        data = json.loads(response.read())
    elapsed = time.perf_counter() - started
    text = data["choices"][0]["message"]["content"] if provider == "openai" else data["content"][0]["text"]
    return text, elapsed


def load_tickets() -> list[dict]:
    with open(ROOT / "data" / "tickets.jsonl", encoding="utf-8") as file:
        return [json.loads(line) for line in file]


def run_all(jobs: list[tuple]) -> dict:
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {key: pool.submit(call, *args) for key, args in jobs}
    return {key: future.result() for key, future in futures.items()}


def compare_per_ticket(task: str, tickets: list[dict], fields: list[str]) -> dict:
    jobs = [((t["id"], model), (provider, model, task, t["text"])) for t in tickets for provider, model in MODELS]
    results = run_all(jobs)
    rows, stats = [], {}
    for t in tickets:
        parsed = {model: json.loads(results[(t["id"], model)][0]) for _, model in MODELS}
        row = {"ticket_id": t["id"], "text": t["text"],
               "order_in_text": ",".join(ORDER_IN_TEXT.findall(t["text"])) or ""}
        for _, model in MODELS:
            for field in fields:
                row[f"{model}.{field}"] = parsed[model].get(field)
        for _, model in MODELS:
            if model == "gpt-fake-large":
                continue
            diff = [f for f in fields if parsed[model].get(f) != parsed["gpt-fake-large"].get(f)]
            row[f"{model}.diverge"] = "|".join(diff)
            stat = stats.setdefault(model, {"tickets": 0, "divergent": 0, **{f: 0 for f in fields}})
            stat["tickets"] += 1
            stat["divergent"] += bool(diff)
            for f in diff:
                stat[f] += 1
        rows.append(row)
    write_csv(f"{task}.csv", rows)
    durations = {model: round(sum(results[(t["id"], model)][1] for t in tickets) / len(tickets), 2)
                 for _, model in MODELS}
    return {"stats": stats, "avg_seconds": durations, "rows": rows}


def compare_suggest(tickets: list[dict]) -> dict:
    jobs = [((t["id"], model), (provider, model, "suggest", t["text"])) for t in tickets for provider, model in MODELS]
    results = run_all(jobs)
    rows = []
    for t in tickets:
        reference = results[(t["id"], "gpt-fake-large")][0]
        row = {"ticket_id": t["id"]}
        for _, model in MODELS:
            text, seconds = results[(t["id"], model)]
            row[f"{model}.chars"] = len(text)
            row[f"{model}.seconds"] = round(seconds, 2)
            row[f"{model}.equal_to_gpt_large"] = text == reference
            row[f"{model}.text"] = text
        rows.append(row)
    write_csv("suggest.csv", rows)
    return {"rows": rows}


def compare_topics(tickets: list[dict]) -> dict:
    content = "\n".join(f"[{t['id']}] {t['text']}" for t in tickets)
    results = run_all([((model,), (provider, model, "topics", content)) for provider, model in MODELS])
    rows, parsed = [], {}
    for _, model in MODELS:
        text, seconds = results[(model,)]
        parsed[model] = json.loads(text)["topics"]
        for item in parsed[model]:
            rows.append({"model": model, "seconds": round(seconds, 2), "topic": item["topic"],
                         "count": item["count"], "examples": "|".join(item["examples"])})
    write_csv("topics.csv", rows)
    return {"parsed": parsed, "seconds": {m: round(results[(m,)][1], 2) for _, m in MODELS}}


def write_csv(name: str, rows: list[dict]) -> None:
    with open(OUT / name, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=40, help="tickets para classify/extract")
    parser.add_argument("--suggest-sample", type=int, default=5)
    parser.add_argument("--topics-batch", type=int, default=150)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    tickets = load_tickets()

    classify = compare_per_ticket("classify", tickets[:args.sample], ["category", "priority"])
    extract = compare_per_ticket("extract", tickets[:args.sample], ["order_number", "product"])
    suggest = compare_suggest(tickets[:args.suggest_sample])
    topics = compare_topics(tickets[:args.topics_batch])

    lines = ["# Comparação large × mini no provider simulado (F01)", "",
             f"Amostra: os {args.sample} primeiros tickets de `data/tickets.jsonl` (classify/extract), "
             f"{args.suggest_sample} (suggest) e um lote de {args.topics_batch} (topics). "
             "Referência: `gpt-fake-large`. Gerado por `scripts/diagnostics/compare_models.py`.", ""]
    for name, result, fields in (("classify", classify, ["category", "priority"]),
                                 ("extract", extract, ["order_number", "product"])):
        lines += [f"## {name}", "", "| modelo | tickets divergentes | " + " | ".join(fields) + " | s/chamada |",
                  "|---|---|" + "---|" * len(fields) + "---|"]
        lines.append(f"| gpt-fake-large | referência | " + " | ".join("—" for _ in fields)
                     + f" | {result['avg_seconds']['gpt-fake-large']} |")
        for model, stat in result["stats"].items():
            lines.append(f"| {model} | {stat['divergent']}/{stat['tickets']} | "
                         + " | ".join(str(stat[f]) for f in fields) + f" | {result['avg_seconds'][model]} |")
        lines.append("")
    if extract["rows"]:
        wrong = {m: 0 for _, m in MODELS}
        cited = [r for r in extract["rows"] if r["order_in_text"]]
        for row in cited:
            for _, model in MODELS:
                if row[f"{model}.order_number"] not in row["order_in_text"].split(","):
                    wrong[model] += 1
        lines += ["### extract: `order_number` contra o número citado no texto", "",
                  f"Tickets da amostra que citam `#NNNNNN` no texto: {len(cited)}.", "",
                  "| modelo | order_number diferente do citado no texto |", "|---|---|"]
        lines += [f"| {m} | {wrong[m]}/{len(cited)} |" for _, m in MODELS]
        lines.append("")
    lines += ["## suggest", "", "| ticket | " + " | ".join(f"{m} chars (s)" for _, m in MODELS)
              + " | claude-large == gpt-large | minis == gpt-large |", "|---|" + "---|" * (len(MODELS) + 2)]
    for row in suggest["rows"]:
        lines.append(f"| {row['ticket_id']} | " + " | ".join(
            f"{row[f'{m}.chars']} ({row[f'{m}.seconds']})" for _, m in MODELS)
            + f" | {row['claude-fake-large.equal_to_gpt_large']} | "
            + f"{row['gpt-fake-mini.equal_to_gpt_large']}/{row['claude-fake-mini.equal_to_gpt_large']} |")
    lines += ["", "## topics (um lote)", "", "| modelo | temas | soma dos counts | s |", "|---|---|---|---|"]
    for _, model in MODELS:
        items = topics["parsed"][model]
        lines.append(f"| {model} | {len(items)} | {sum(i['count'] for i in items)} | {topics['seconds'][model]} |")
    lines.append(f"\nSaída do topics idêntica entre os dois large: "
                 f"{topics['parsed']['gpt-fake-large'] == topics['parsed']['claude-fake-large']}.")
    (OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
