# Roteiro de governança do README, executado literalmente (2026-10-13T17:53:41Z)
$ curl -s -X POST localhost:8090/admin/reset
{"status":"ok"}+ calls
$ curl -s 'localhost:8090/admin/calls?last=100'
$ python -c 'import sys,json;print(len(json.load(sys.stdin)))'
0
$ chat sk-demo-budget-0001
$ curl -s -w ' [%{http_code}]\n' localhost:4000/chat/completions -H 'Authorization: Bearer sk-demo-budget-0001' -H 'Content-Type: application/json' -d '{"model": "helpdesk-classify", "messages": [{"role": "user", "content": "TASK: classify\nMeu pedido atrasou"}]}'
{"id":"chatcmpl-d5f26f0a1c7a401c93d8896c","created":1791914021,"model":"helpdesk-classify","object":"chat.completion","choices":[{"finish_reason":"stop","index":0,"message":{"content":"{\"category\": \"other\", \"priority\": \"medium\"}","role":"assistant","provider_specific_fields":{"refusal":null}},"provider_specific_fields":{}}],"usage":{"completion_tokens":11,"prompt_tokens":9,"total_tokens":20}} [200]
$ calls
$ curl -s 'localhost:8090/admin/calls?last=100'
$ python -c 'import sys,json;print(len(json.load(sys.stdin)))'
1
$ chat sk-demo-budget-0001
$ curl -s -w ' [%{http_code}]\n' localhost:4000/chat/completions -H 'Authorization: Bearer sk-demo-budget-0001' -H 'Content-Type: application/json' -d '{"model": "helpdesk-classify", "messages": [{"role": "user", "content": "TASK: classify\nMeu pedido atrasou"}]}'
{"error":{"message":"Budget has been exceeded! Key=demo-budget (sk-...0001) Current cost: 0.00013249999999998896, Max budget: 0.0001","type":"budget_exceeded","param":null,"code":"429"}} [429]
$ calls
$ curl -s 'localhost:8090/admin/calls?last=100'
$ python -c 'import sys,json;print(len(json.load(sys.stdin)))'
1
$ chat sk-demo-rpm-0001
$ curl -s -w ' [%{http_code}]\n' localhost:4000/chat/completions -H 'Authorization: Bearer sk-demo-rpm-0001' -H 'Content-Type: application/json' -d '{"model": "helpdesk-classify", "messages": [{"role": "user", "content": "TASK: classify\nMeu pedido atrasou"}]}'
{"id":"chatcmpl-cfa194458eb84db9b28b0c02","created":1791914023,"model":"helpdesk-classify","object":"chat.completion","choices":[{"finish_reason":"stop","index":0,"message":{"content":"{\"category\": \"other\", \"priority\": \"medium\"}","role":"assistant","provider_specific_fields":{"refusal":null}},"provider_specific_fields":{}}],"usage":{"completion_tokens":11,"prompt_tokens":9,"total_tokens":20}} [200]
$ chat sk-demo-rpm-0001
$ curl -s -w ' [%{http_code}]\n' localhost:4000/chat/completions -H 'Authorization: Bearer sk-demo-rpm-0001' -H 'Content-Type: application/json' -d '{"model": "helpdesk-classify", "messages": [{"role": "user", "content": "TASK: classify\nMeu pedido atrasou"}]}'
{"id":"chatcmpl-581fd04de1584a848885054f","created":1791914024,"model":"helpdesk-classify","object":"chat.completion","choices":[{"finish_reason":"stop","index":0,"message":{"content":"{\"category\": \"other\", \"priority\": \"medium\"}","role":"assistant","provider_specific_fields":{"refusal":null}},"provider_specific_fields":{}}],"usage":{"completion_tokens":11,"prompt_tokens":9,"total_tokens":20}} [200]
$ calls
$ curl -s 'localhost:8090/admin/calls?last=100'
$ python -c 'import sys,json;print(len(json.load(sys.stdin)))'
3
$ chat sk-demo-rpm-0001
$ curl -s -w ' [%{http_code}]\n' localhost:4000/chat/completions -H 'Authorization: Bearer sk-demo-rpm-0001' -H 'Content-Type: application/json' -d '{"model": "helpdesk-classify", "messages": [{"role": "user", "content": "TASK: classify\nMeu pedido atrasou"}]}'
{"error":{"message":"Rate limit exceeded for api_key: <hash-da-chave>. Limit type: requests. Current limit: 2, Remaining: 0. Limit resets at: 2026-10-13 17:54:45 UTC","type":"throttling_error","param":null,"code":"429"}} [429]
$ calls
$ curl -s 'localhost:8090/admin/calls?last=100'
$ python -c 'import sys,json;print(len(json.load(sys.stdin)))'
3
