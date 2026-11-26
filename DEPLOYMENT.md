# Day 14 — CP6 Cloud Deployment

Agent trong `06-lab-complete/` được deploy lên **Render** từ nhánh `main`, commit `6b92e40`, qua Blueprint `06-lab-complete/render.yaml`. Web service dùng Docker và kết nối Render Key Value qua mạng nội bộ.

**URL public** · [day14-agent-hi1s.onrender.com](https://day14-agent-hi1s.onrender.com)

## Kiểm tra API

```bash
BASE='https://day14-agent-hi1s.onrender.com'
read -rsp 'Dán AGENT_API_KEY rồi bấm Enter: ' AGENT_API_KEY
printf '\n'
curl -sS -o /dev/null -w '/health: %{http_code}\n' "$BASE/health"
curl -sS -o /dev/null -w '/ready: %{http_code}\n' "$BASE/ready"
curl -sS -o /dev/null -w '/ask thiếu key: %{http_code}\n' -X POST "$BASE/ask" -H 'Content-Type: application/json' -d '{"question":"Hello"}'
curl -sS -o /dev/null -w '/ask có key: %{http_code}\n' -X POST "$BASE/ask" -H 'Content-Type: application/json' -H "X-API-Key: $AGENT_API_KEY" -d '{"question":"Hello"}'
```

Kết quả từ terminal Ubuntu:

```text
/health: 200
/ready: 200
/ask thiếu key: 401
/ask có key: 200
```

## Biến môi trường

| Biến | Cách cấp |
| --- | --- |
| `ENVIRONMENT` | Blueprint đặt `production`. |
| `PORT` | Render cấp cho web service. |
| `AGENT_API_KEY` | Render sinh theo cấu hình Blueprint. |
| `REDIS_URL` | URL nội bộ của Render Key Value, nhập khi tạo Blueprint. |

## Minh chứng

- [Dashboard Render](screenshots/dashboard.png)
- [Sự kiện deploy lên Live](screenshots/running.png)
- [Kết quả kiểm tra API](screenshots/test.png)
