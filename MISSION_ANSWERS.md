# Day 14 Lab — Mission Answers

## Part 1 — Localhost vs Production

### Exercise 1.1 — Vấn đề trong bản develop

| # | Vấn đề trong bản `develop` | Vì sao đáng ghi vào bài? |
|---|---|---|
| 1 | **API key nằm trong code và bị in ra log** — dòng 17 và 34. | Bạn đã thấy `[DEBUG] Using key: …`. Đây là key giả của lab. Nếu dùng key thật, người có quyền xem repo hoặc log có thể lấy được key. |
| 2 | **Thiếu endpoint `/health`** — dòng 42. | Bạn đã thấy `GET /health` trả `404`. Nền tảng triển khai không thể dùng đường dẫn này để kiểm tra app còn hoạt động. |
| 3 | **Chỉ lắng nghe trên `localhost`** — dòng 51. | `curl` chạy cùng môi trường vẫn gọi được. Nếu giữ cấu hình này khi đóng gói, request từ bên ngoài container sẽ không vào được app. |
| 4 | **Cổng `8000` bị ghi cố định** — dòng 52. | Nếu nền tảng cấp một cổng khác qua biến `PORT`, app vẫn mở cổng `8000` và có thể không nhận được lưu lượng. |
| 5 | **Bật `reload=True`** — dòng 53. | Log của bạn có `Started reloader process … using WatchFiles`. App theo dõi file và tự khởi động lại khi file đổi. Điều này tiện khi sửa code local, nhưng trên production có thể làm gián đoạn xử lý request. |

### Exercise 1.2 — Chạy bản develop

```bash
curl -i -X POST "http://localhost:8000/ask?question=Hello"
```

```text
HTTP/1.1 200 OK
content-type: application/json

{"answer":"Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ OpenAI/Anthropic."}
```

Gọi `GET /health` trên bản develop trả `404 Not Found`.

### Exercise 1.3 — So sánh develop và production

Khởi động bản production trong Ubuntu và kiểm tra hai endpoint:

```bash
curl -i http://localhost:8000/health
curl -i http://localhost:8000/ready
```

Kết quả kiểm tra lại trong Ubuntu: `/health` trả `200 OK` với trường `"status":"ok"`. `/ready` trả `200 OK` với `{"ready":true}`. Khi dừng server, Uvicorn ghi `Application shutdown complete.`

| Tiêu chí | Develop | Production | Vì sao quan trọng? |
| --- | --- | --- | --- |
| Cấu hình | Cổng `8000` và các giá trị cấu hình được ghi trực tiếp trong code. | `production/config.py` đọc các biến môi trường như `HOST`, `PORT` và `DEBUG`. | Có thể đổi cấu hình giữa máy local và nền tảng deploy mà không sửa code. |
| Health check | `/health` và `/ready` trả `404`. | `/health` báo tiến trình còn chạy. `/ready` báo app có sẵn sàng nhận request hay chưa. | Nền tảng có thể kiểm tra tình trạng app và chỉ gửi lưu lượng đến instance đã sẵn sàng. |
| Logging | Dùng `print()` và in cả giá trị API key mẫu vào log. | Dùng `logging`, ghi sự kiện request và response theo trường JSON, như `event` và `question_length`, và bỏ API key khỏi log. | Dễ lọc sự kiện khi tìm lỗi và giảm nguy cơ lộ thông tin nhạy cảm. |
| Shutdown | App dùng cơ chế dừng mặc định của Uvicorn. | App bổ sung bước shutdown trong `lifespan` của FastAPI, đặt `is_ready = False` và ghi log khi kết thúc. | Có chỗ để đóng kết nối hoặc giải phóng tài nguyên khi dừng hay triển khai lại dịch vụ. |

## Part 2 — Docker

### Exercise 2.1 — Đọc Dockerfile

1. **Base image:** `FROM python:3.11` cung cấp Python và các thành phần hệ thống để build và chạy app.
2. **Working directory:** `WORKDIR /app` đặt `/app` làm thư mục làm việc bên trong container. Các đường dẫn tương đối trong các lệnh sau được tính từ thư mục này.
3. **Thứ tự `COPY`:** Dockerfile copy `requirements.txt` và cài thư viện trước khi copy `app.py`. Khi chỉ đổi code, Docker có thể dùng lại lớp đã cài thư viện nếu `requirements.txt` giữ nguyên.
4. **`CMD` và `ENTRYPOINT`:** `ENTRYPOINT` đặt chương trình chính của container. `CMD` cung cấp lệnh mặc định khi đứng riêng hoặc đối số mặc định khi dùng cùng `ENTRYPOINT`. Bản develop đặt `CMD ["python", "app.py"]`.

### Exercise 2.2 — Build và chạy container develop

```bash
docker build -f 02-docker/develop/Dockerfile -t my-agent:develop .
docker run --rm -p 8000:8000 my-agent:develop
curl -i -X POST "http://localhost:8000/ask?question=Hello"
```

Build hoàn tất sau `167.3s`. Container mở cổng `8000` và Uvicorn ghi nhận `POST /ask?question=Hello` trả `200 OK`.

```text
HTTP/1.1 200 OK
server: uvicorn
content-type: application/json

{"answer":"Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ OpenAI/Anthropic."}
```

Sau khi test, tôi bấm `Ctrl+C`. Log ghi `Application shutdown complete.` rồi hiện `KeyboardInterrupt`.

### Exercise 2.3 — Multi-stage build và kích thước image

```bash
docker build -f 02-docker/production/Dockerfile -t my-agent:advanced .
docker images my-agent
```

Build production hoàn tất sau `322.3s`. Stage `builder` cài `gcc`, `libpq-dev` và các thư viện Python. Stage `runtime` bắt đầu từ `python:3.11-slim`, copy thư viện Python đã cài cùng mã nguồn, và chạy app bằng user `appuser`. Image cuối dùng base slim và bỏ được các lớp chứa công cụ build của stage `builder`.

| Image | Image ID | `DISK USAGE` | `CONTENT SIZE` |
| --- | --- | ---: | ---: |
| `my-agent:develop` | `136a0258ae0f` | 1.67 GB | 426 MB |
| `my-agent:advanced` | `75b5fd116be6` | 240 MB | 57.4 MB |

Tính theo cột `CONTENT SIZE`, image advanced giảm khoảng **86,5%** so với develop (`(426 − 57,4) / 426 × 100`).

### Exercise 2.4 — Docker Compose và Nginx

```bash
docker compose -p k5-day14-docker up -d --build
docker compose -p k5-day14-docker ps
curl -i http://localhost/health
curl -i -X POST http://localhost/ask -H "Content-Type: application/json" -d '{"question":"Explain microservices"}'
```

```text
curl → Nginx (cổng 80 trên máy) → Agent (cổng 8000 trong mạng internal)
                                  ├─ chờ Redis (6379) healthy
                                  └─ chờ Qdrant (6333) healthy
```

Nginx chuyển tiếp `/health` và `/ask` tới agent qua mạng `internal`. Compose dùng health check của Redis và Qdrant để quyết định khi nào khởi động agent. Endpoint `/ask` của bài này dùng mock LLM. Khi chạy `ps`, Redis và Qdrant đều `healthy`, Nginx đã `Up`, còn health check của agent đang ở trạng thái `starting`. Hai lệnh `curl` sau đó đều nhận `200 OK` với header `Server: nginx`.

**`GET /health`**

```text
HTTP/1.1 200 OK
Server: nginx

{"status":"ok","uptime_seconds":11.0,"version":"2.0.0","timestamp":"2026-11-26T08:10:10.570920"}
```

**`POST /ask`**

```text
HTTP/1.1 200 OK
Server: nginx

{"answer":"Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé."}
```

## Part 3 — Cloud Deployment (CP6)

### Exercise 3.2 — Deploy lên Render

Tôi deploy agent trong `06-lab-complete/` từ nhánh `main` bằng Blueprint. Commit `6b92e40` hiển thị **Live** trên Render. Dịch vụ dùng Render Key Value làm Redis.

URL public · [day14-agent-hi1s.onrender.com](https://day14-agent-hi1s.onrender.com)

Kết quả lần lượt là `200` cho `/health`, `200` cho `/ready`, `401` khi gọi `/ask` thiếu key và `200` khi có key hợp lệ. Xem lệnh và ảnh trong [DEPLOYMENT.md](DEPLOYMENT.md).

### So sánh cấu hình Railway và Render

`railway.toml` mẫu tách cấu hình thành `[build]` và `[deploy]`, chỉ định builder, lệnh chạy và `healthcheckPath`. `render.yaml` khai báo dịch vụ trong `services`, dùng Dockerfile trong `rootDir`, chỉ định `healthCheckPath` và cách cấp biến môi trường. Cả hai đều cấu hình health check ở `/health`.

### Exercise 3.3 — Pipeline Cloud Run

1. Cloud Build chạy test bằng `pytest`.
2. Sau bước test, Cloud Build build image Docker, gắn tag theo commit và đẩy lên registry.
3. Bước deploy dùng image theo commit để tạo phiên bản mới trên Cloud Run. File `service.yaml` mẫu mô tả cấu hình runtime như cổng, tài nguyên, health probe và giới hạn scale.

## Part 4 — API Security

### Exercise 4.1 — Xác thực bằng API key

`verify_api_key()` đọc header `X-API-Key` và so sánh giá trị với cấu hình `AGENT_API_KEY`. Để đổi key trong bản demo, đặt giá trị mới cho `AGENT_API_KEY`, khởi động lại app và cập nhật key phía client.

Kết quả gọi `POST /ask` với `{"question":"Hello"}` trên bản develop:

**Thiếu API key**

```text
HTTP/1.1 401 Unauthorized

{"detail":"Missing API key. Include header: X-API-Key: <your-key>"}
```

**Sai API key**

```text
HTTP/1.1 403 Forbidden

{"detail":"Invalid API key."}
```

**Đúng API key**

```text
HTTP/1.1 200 OK

{"question":"Hello","answer":"Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ OpenAI/Anthropic."}
```

### Exercise 4.2 — Xác thực bằng JWT

Trên bản production, tôi gửi `POST /auth/token` với tài khoản demo `student` và nhận `200 OK`. Token được lưu vào biến `TOKEN`. Tôi gọi `POST /ask` với header `Authorization: Bearer $TOKEN`. App kiểm tra chữ ký và thời hạn token trước khi xử lý câu hỏi. Token của bản mẫu có thời hạn 60 phút.

```text
HTTP/1.1 200 OK

{"question":"Explain JWT","answer":"Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé.","usage":{"requests_remaining":9,"budget_remaining_usd":1.6e-05}}
```

Trong response mẫu, trường `usage.budget_remaining_usd` lấy giá trị từ `usage.total_cost_usd`. Giá trị `1.6e-05` vì vậy là chi phí ước tính đã dùng ở thời điểm đó.

### Exercise 4.3 — Giới hạn tần suất gọi

Rate limiter dùng **cửa sổ trượt 60 giây** theo từng người dùng. Mỗi lần gọi, app loại các mốc thời gian đã nằm ngoài cửa sổ rồi đếm các request còn lại. Tài khoản `student` có hạn mức 10 request mỗi 60 giây. Vai trò `admin` dùng hạn mức 100 request mỗi 60 giây.

Tôi dùng JWT để gọi `/ask` liên tiếp 20 lần. Request 1–10 trả `200 OK`. Request 10 có `requests_remaining: 0`. Request 11–20 trả `429 Too Many Requests`. Đây là trích đoạn của request 11:

```text
HTTP/1.1 429 Too Many Requests
retry-after: 59

{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":59}}
```

### Exercise 4.4 — Giới hạn chi phí

- **Bản demo:** Trước khi gọi mock LLM, app kiểm tra chi phí đã ghi nhận. Sau khi có câu trả lời, app ước tính số token đầu vào và đầu ra rồi cộng chi phí vào bộ đếm trong bộ nhớ. Code đặt ngưỡng `1 USD/ngày` mỗi người và `10 USD` toàn dịch vụ, với mã `402` khi người dùng chạm ngưỡng và `503` khi toàn dịch vụ chạm ngưỡng.
- **Phương án ngân sách tháng trong đề:** Lưu chi phí theo khóa Redis `budget:<user_id>:<YYYY-MM>`. Trước khi gọi LLM, cộng chi phí ước tính vào tổng hiện tại và từ chối nếu vượt `10 USD`. Gom thao tác kiểm tra và cập nhật thành một thao tác nguyên tử để các request đồng thời không cùng vượt qua ngưỡng. Khi sang tháng mới, dùng khóa tháng mới.
- **Vai trò của hai lớp:** Rate limiter giới hạn số lần gọi trong một khoảng thời gian. Cost guard giới hạn chi phí tích lũy vì chi phí mỗi lần gọi thay đổi theo số token.

## Part 5 — Scaling & Reliability

### Exercise 5.1 — Health và readiness

`/health` cho biết tiến trình còn hoạt động. `/ready` cho biết app đã sẵn sàng nhận request. Bản develop trả `503` từ `/ready` khi cờ `_is_ready` chưa bật.

**`curl -i http://localhost:8000/health`**

```text
HTTP/1.1 200 OK
content-type: application/json

{"status":"ok","uptime_seconds":33.9,"version":"1.0.0","environment":"development","timestamp":"2026-11-26T08:58:23.925858+00:00","checks":{"memory":{"status":"ok","used_percent":15.1}}}
```

**`curl -i http://localhost:8000/ready`**

```text
HTTP/1.1 200 OK
content-type: application/json

{"ready":true,"in_flight_requests":1}
```

### Exercise 5.2 — Graceful shutdown

`SIGTERM` yêu cầu Uvicorn dừng có trật tự. App dùng `lifespan` để đánh dấu đang dừng và ghi log khi hoàn tất shutdown.

Tôi gửi tín hiệu dừng tới PID của bản develop bằng `kill -TERM "$APP_PID"`, rồi dùng `wait "$APP_PID"` để chờ tiến trình kết thúc. Trích log terminal:

```text
INFO:     Shutting down
INFO:     Waiting for application shutdown.
2026-11-26 15:59:03,399 INFO 🔄 Graceful shutdown initiated...
2026-11-26 15:59:03,400 INFO ✅ Shutdown complete
INFO:     Application shutdown complete.
INFO:     Finished server process [1904]
2026-11-26 15:59:03,400 INFO Received signal 15 — uvicorn will handle graceful shutdown
[1]+  Done                    python app.py
```

### Exercise 5.3 — Lưu session trong Redis

Mỗi instance có RAM riêng. Nếu lưu lịch sử chat trong RAM, một request chuyển sang instance khác có thể mất ngữ cảnh. Bản production dùng khóa Redis `session:<session_id>` để các instance đọc và ghi cùng lịch sử. Mỗi lần lưu đặt TTL là 3.600 giây.

### Exercise 5.4 — Chạy ba instance qua Nginx

```bash
docker compose -p k5-day14-scaling up -d --build --scale agent=3
docker compose -p k5-day14-scaling ps
curl -i http://localhost:8080/health
```

`docker compose ps` ghi nhận ba container agent và Redis đều `healthy`. Nginx đang chạy và chuyển tiếp từ cổng `8080` trên máy tới cụm agent. Kiểm tra lại `/health` qua Nginx cho thấy `status=ok`, `storage=redis` và `redis_connected=true`.

### Exercise 5.5 — Kiểm tra lịch sử của một session

```bash
python test_stateless.py
```

Log Nginx ghi nhận 5 lượt `POST /chat` đều trả `200`. Log container cho thấy request được phân phối như sau:

| Container | Instance ID | Số lượt `POST /chat` thành công |
| --- | --- | ---: |
| `agent-1` | `instance-0edd8b` | 1 |
| `agent-2` | `instance-28c79f` | 2 |
| `agent-3` | `instance-5f6f15` | 2 |

Lượt `GET /chat/{session_id}/history` trong log trả `200`. Đọc lại chính session đó từ API cho kết quả **10 tin nhắn**, gồm 5 câu hỏi và 5 câu trả lời. Kết quả xác nhận ba instance đã xử lý các lượt chat và lịch sử vẫn đầy đủ nhờ Redis dùng chung.

## Part 6 — Final Project (CP5)

Codex chạy `python check_production_ready.py` trong Ubuntu từ `06-lab-complete/`, với Docker đang chạy. Script đo image **273 MB**, kiểm tra `/ready` trả `503` khi Redis gián đoạn trong khi `/health` trả `200`, và xác nhận Docker dừng trong **0,7 giây** với exit code `0`.

```text
  📋 Checklist Deliverable
     ✅ Dockerfile (multi-stage, < 500 MB)
     ✅ docker-compose.yml (agent + redis)
     ✅ .dockerignore
     ✅ Health check endpoint (GET /health)
     ✅ Readiness endpoint (GET /ready)
     ✅ API Key authentication
     ✅ Rate limiting
     ✅ Cost guard
     ✅ Config từ environment variables
     ✅ Structured logging
     ✅ Graceful shutdown
     ✅ Public URL ready (Railway / Render config)
----------------------------------------------------------------
  Result: 12/12 tiêu chí đạt · 42/42 checks passed
  🎉 PASS 12/12 — PRODUCTION READY! Deploy nào!
```

## AI log

- Hỏi Codex cách thực hiện CP1 và lưu output. Codex hướng dẫn các lệnh kiểm tra và tạo khung cho file này. Tôi đã tự chạy bản develop trong Ubuntu, nhận `200 OK` từ `/ask` và `404 Not Found` từ `/health`.
- Tôi đã chạy bản production theo hướng dẫn. Tôi nhờ Codex điền mục 1.3. Codex đối chiếu hai app mẫu, chạy lại `/health` và `/ready` trong Ubuntu để xác nhận mã `200`, rồi ghi kết quả và bảng so sánh.
- Tôi tự build hai image, chạy container develop, đo kích thước bằng `docker images` và gọi API qua Nginx. Tôi gửi log cho Codex để đối chiếu với yêu cầu CP2, tóm tắt output và tính tỷ lệ giảm kích thước từ số liệu đã đo. Codex dựa vào Dockerfile và Docker Compose của repo để giải thích các bước build và vẽ sơ đồ service.
- Tôi tự chạy các lệnh thử API key, lấy JWT và gọi `/ask` liên tiếp 20 lần trong Ubuntu. Tôi gửi log cho Codex để kiểm tra và ghi các mã HTTP vào Part 4. Codex đối chiếu code mẫu để giải thích cửa sổ trượt, cost guard và trường chi phí trong response.
- Tôi chạy bản develop, thử `/health` và `/ready`, gửi `SIGTERM`, rồi gửi output terminal cho Codex để ghi vào mục 5.1 và 5.2. Tôi chạy stack CP4 và kiểm tra lịch sử chat. Codex đọc trạng thái Compose và log các container, rồi gọi lại endpoint lịch sử của session trong log để xác nhận số tin nhắn trước khi tổng hợp Part 5.
- Tôi nhờ Codex triển khai các TODO của CP5 và hướng dẫn build Docker. Codex viết phần cấu hình, xác thực, health/readiness, giới hạn tần suất và chi phí qua Redis, logging và shutdown. Codex cập nhật Dockerfile, Compose và cấu hình Render, sau đó build image và chạy script chấm đầy đủ trong Ubuntu. Kết quả ở Part 6 là từ lần chạy kiểm tra của Codex.
- Tôi deploy trên Render, tự chạy bốn lệnh curl và gửi ảnh minh chứng. Codex tổng hợp kết quả vào `DEPLOYMENT.md` và đối chiếu các file cấu hình mẫu để viết Part 3.
- Tôi tự chạy bảy lượt load test của CP7. Codex đọc các JSON đã lưu, điền bảng hiệu năng và tóm tắt kết quả concurrency và tail latency trong `BENCHMARK_REPORT.md`.
- Tôi chạy eval v1 và v2. Codex đối chiếu hai câu v2 còn sai và gợi ý hai mục knowledge base. Tôi cập nhật code, khởi động lại v2 và chạy lần eval cuối, đạt 23/23 với 0 regression. Codex dùng ba file JSON để điền bảng chất lượng và giải thích quality gate trong báo cáo.
- Tôi chạy hai lượt Locust, bật lỗi và độ trễ mô phỏng, rồi chụp Grafana, Prometheus và hai trace Jaeger. Codex sửa đường dẫn thư viện trong Dockerfile CP8, kiểm tra stack khởi động lại và đối chiếu ảnh, CSV, dữ liệu Prometheus và log cùng trace ID để hoàn thiện báo cáo.
