# Benchmark & Observability Report — Day 14

- **Họ tên:** Nguyen Hai Quang
- **Ngày chạy:** 26/11/2026 (GMT+7)
- **Môi trường:** Windows, Ubuntu 24.04 trên WSL2, Python 3.12 và Docker Desktop

---

## 1. SLO của agent

| SLI | SLO | Lý do chọn ngưỡng này |
|---|---|---|
| p95 latency `/ask` | ≤ 500 ms | Ngưỡng của script load test để theo dõi nhóm request phản hồi chậm. |
| Error rate `/ask` | ≤ 2% | Ngưỡng của script load test để theo dõi tỷ lệ request thất bại. |
| Accuracy trên golden dataset | ≥ 80% khi so sánh ban đầu, 100% sau khi sửa v2 | Ngưỡng 80% là mặc định của eval. Lần chấm cuối yêu cầu đúng cả 23 câu và không có regression. |

---

## 2. Benchmark hiệu năng (develop, `load_test.py`)

### 2.1 Concurrency vs latency (agent v2)

| Concurrency | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Error rate | SLO |
|---|---|---|---|---|---|---|
| 1 | 4,56 | 188,5 | 221,2 | 1.678,6 | 0,00% | PASS |
| 10 | 37,97 | 189,0 | 220,0 | 1.694,8 | 2,33% | FAIL (tỷ lệ lỗi) |
| 50 | 112,71 | 194,4 | 236,9 | 1.704,7 | 1,00% | PASS |
| 100 | 109,68 | 276,7 | 2.098,5 | 2.252,3 | 0,67% | FAIL (p95) |

**Nhận xét:** RPS có tăng tuyến tính theo concurrency không? Vì sao?

RPS tăng từ 4,56 ở concurrency 1 lên 112,71 ở concurrency 50, rồi giảm nhẹ còn 109,68 ở concurrency 100. Cùng lúc đó, p95 tăng từ 236,9 ms lên 2.098,5 ms, vượt ngưỡng 500 ms. Trong lượt đo này, tăng số request đồng thời từ 50 lên 100 khiến thời gian chờ tăng mà thông lượng không tăng thêm. Mức 10 có 7 phản hồi `503` trên 300 request, tương ứng 2,33% và vượt ngưỡng lỗi 2%.

### 2.2 Tail latency

| `MOCK_SLOW_RATE` | avg (ms) | p95 (ms) | p99 (ms) |
|---|---|---|---|
| 0 | 189,1 | 221,0 | 225,9 |
| 0.03 (mặc định) | 239,0 | 223,6 | 1.698,6 |
| 0.1 | 352,3 | 1.698,0 | 1.715,0 |

**Nhận xét:** Chỉ số nào nhạy nhất với request chậm? Vì sao SLO không nên đặt theo average?

Từ 0% lên 3%, p99 tăng từ 225,9 ms lên 1.698,6 ms trong khi p95 chỉ từ 221,0 lên 223,6 ms. Ở 10%, p95 tăng lên 1.698,0 ms, còn trung bình là 352,3 ms. p99 cho thấy nhóm request chậm ngay ở mức 3%. Đến mức 10%, độ chậm đã ảnh hưởng cả p95. Giá trị trung bình vẫn dưới 500 ms ở cả ba lượt, nên nếu chỉ nhìn trung bình sẽ bỏ sót lượt vi phạm SLO p95.

---

## 3. Benchmark chất lượng (develop, `eval/run_eval.py`)

| Chỉ số | Agent v1 | Agent v2 | Agent v2 (sau khi sửa KB) |
|---|---|---|---|
| Accuracy | 4,3% (1/23) | 91,3% (21/23) | 100% (23/23) |
| Avg tokens / câu | 56,9 | 109,0 | 113,3 |
| Tổng cost (USD) | 0,000402 | 0,000760 | 0,000787 |
| Cost / câu đúng (USD) | 0,00040155 | 0,00003619 | 0,00003423 |
| p95 (ms) | 1.511,3 | 213,7 | 221,1 |
| Quality gate | FAIL (ngưỡng 80%) | PASS (ngưỡng 80%) | PASS (ngưỡng 100%, 0 regression) |

**Những câu v2 trả lời sai ban đầu và cách bạn sửa:**

| ID | Keyword bị thiếu | Bạn đã sửa gì |
|---|---|---|
| `security-02` | `token`, `hết hạn`, `chữ ký` | Thêm mục JWT mô tả token có chữ ký, thời hạn và sự khác biệt với API key. |
| `scaling-03` | `cpu`, `memory`, `custom metrics` | Thêm mục Kubernetes HPA mô tả cách điều chỉnh số replica theo các chỉ số này. |

**Nhận xét về trade-off chất lượng / chi phí / latency giữa v1 và v2:**

V2 dùng trung bình 109,0 token mỗi câu so với 56,9 của v1. Tổng chi phí ước tính tăng, trong khi chi phí trên mỗi câu đúng giảm từ 0,00040155 USD xuống 0,00003619 USD vì v2 trả lời đúng 21 câu. Sau khi bổ sung kiến thức, v2 đúng thêm hai câu và chi phí trên mỗi câu đúng giảm còn 0,00003423 USD. So với bản v2 ban đầu, p95 của lần eval sau khi sửa tăng 7,4 ms. V1 có hai request chậm bất thường trong lần đo, nên chênh lệch p95 giữa v1 và v2 ở đây chỉ mô tả hai lượt đo đó.

**Quality gate trong CI.** Job chạy v2, sau đó gọi `run_eval.py` với `--min-accuracy 1.0` và `--baseline` trỏ tới báo cáo của bản chuẩn đã lưu. Script trả exit code `1` khi accuracy dưới ngưỡng hoặc có câu đúng ở baseline trở thành sai. Nếu cấu hình job này là kiểm tra bắt buộc của nhánh, CI sẽ chặn merge khi job thất bại.

---

## 4. Observability stack (production)

### 4.1 Screenshot

- [x] [Dashboard Grafana khi đang có tải](screenshots/grafana-dashboard.png)
- [x] [Trace chậm trong Jaeger](screenshots/jaeger-slow-trace.png), thấy span gọi LLM chiếm phần lớn thời gian
- [x] [Trace lỗi trong Jaeger](screenshots/jaeger-error-trace.png), thấy HTTP `503`, span `agent.run` và event `exception` với thông báo lỗi upstream của mock LLM.
- [x] [Trang Alerts của Prometheus có 2 alert cùng firing](screenshots/prometheus-alert-firing.png)

Ảnh Grafana ghi nhận `/ask` ở **15,8 req/s**, tỷ lệ lỗi **21,02%**, p95 **1,90 giây** và **3 instance**. [Ảnh Locust](screenshots/locust-load.png) ghi nhận 30 người dùng mô phỏng đang gửi tải qua Nginx.

Ở mốc truy vấn Prometheus 18:38:12 (GMT+7), độ trễ trung bình của `/ask` trong cửa sổ 1 phút là **586,6 ms**. p95 gần **1,90 giây** cho thấy nhóm request chậm chờ lâu hơn nhiều so với trung bình. Ba instance lần lượt xử lý khoảng **5,38**, **5,21** và **5,32 req/s**, khá đồng đều trong cửa sổ này.

Prometheus đo khoảng **937 input token/s** và **498 output token/s** ở cùng mốc. Prompt v2 gồm cả câu hỏi và ngữ cảnh truy xuất, nên số input token nhiều hơn output. Thử `curl http://localhost:8080/metrics` qua Nginx trả `404`. Prometheus scrape `/metrics` trực tiếp từ agent trong mạng nội bộ để endpoint này chỉ phục vụ giám sát trong stack.

### 4.2 Thí nghiệm "phá hệ thống"

| # | Thay đổi | Alert nào firing | Thời gian từ lúc đổi → firing | Panel nào phản ánh rõ nhất |
|---|---|---|---|---|
| A | `MOCK_ERROR_RATE=0.2` | `AgentHighErrorRate` | Khoảng 7 phút 03 giây từ mốc tạo lại container | Error rate |
| B | `MOCK_SLOW_RATE=0.3` | `AgentHighLatencyP95` | Khoảng 8 phút 03 giây từ mốc tạo lại container | Latency p95 |
| C | `LLM_MODEL=mock-llm-large` | Chưa đo | — | — |
| D | `docker pause` 1 instance | Chưa đo | — | — |
| E | `AGENT_VERSION=v1` | Giải thích bên dưới | — | — |

Cả hai thay đổi được áp dụng cùng lúc. Docker ghi nhận agent được tạo lại lúc 18:30:09 (GMT+7). Mẫu `firing` đầu tiên trong Prometheus xuất hiện lúc 18:37:12 cho tỷ lệ lỗi và 18:38:12 cho p95. Khoảng thời gian từ lúc tạo lại container gồm cả lúc chờ trước khi tạo đủ tải. Cả hai alert bắt đầu `pending` lúc 18:36:12 và chuyển sang `firing` sau lần lượt 60 và 120 giây.

**Thí nghiệm E không làm alert nào firing. Bạn sẽ phát hiện loại sự cố này trong production bằng cách nào?**

Chạy eval định kỳ trên bộ câu hỏi đại diện và so với baseline. Trong CP7, v1 chỉ đạt 1/23 câu, nên quality gate phát hiện được regression về nội dung. Các alert hiện tại theo dõi lỗi HTTP, độ trễ, instance và chi phí, trong khi một câu trả lời sai vẫn có thể trả HTTP `200`.

### 4.3 Debug bằng trace

**Trace chậm**

- `trace_id` · `092aa75df881f4e9b53de3ae241f01c8`
- Tổng thời gian · **1.720,36 ms**.
- Span `chat mock-llm-small` mất **1.694,87 ms**, khoảng **98,5%** tổng thời gian. `agent.retrieve_context` mất **22,90 ms**.
- Dòng log cùng `trace_id`:

```json
{"ts":"2026-11-26T11:41:28.110305+00:00","level":"INFO","service":"observable-agent","instance":"8eddab6ed3e9","event":"http_request","trace_id":"092aa75df881f4e9b53de3ae241f01c8","span_id":"c88e4c802a45ff2d","request_id":"75e004936602","method":"POST","route":"/ask","status":200,"ms":1719.8}
```

**Trace lỗi**

- `trace_id` · `2d3181faa30475867db08705e2220ec5`
- Tổng thời gian · **106,92 ms**. Ảnh mở event `exception` của `agent.run`. Dữ liệu trace cũng ghi event này trong span `chat mock-llm-small`. Request `/ask` trả `503` do lỗi upstream mô phỏng.
- Dòng log cùng `trace_id`:

```json
{"ts":"2026-11-26T11:41:28.539388+00:00","level":"INFO","service":"observable-agent","instance":"8eddab6ed3e9","event":"llm_error","trace_id":"2d3181faa30475867db08705e2220ec5","span_id":"35e6aa12b110faaa","request_id":"8f1c94422861","error":"Upstream LLM error: 503 Service Unavailable (mock)"}
```

---

## 5. Benchmark scaling (production, Locust headless, 100 users, 2 phút)

Số liệu lấy từ dòng `POST /ask` trong hai file `*_stats.csv`.

| Số instance | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Failures |
|---|---|---|---|---|---|
| 1 | 62,56 | 190 | 230 | 1.700 | 66/7.121 (0,93%) |
| 3 | 63,09 | 190 | 230 | 1.700 | 68/7.196 (0,94%) |

**Giải thích kết quả:** Scale có cải thiện p95 không? Nút thắt nằm ở đâu?

p95 giữ ở 230 ms và RPS tăng nhẹ từ 62,56 lên 63,09 khi chuyển từ 1 lên 3 replica. Lượt đo với 100 người dùng chưa cho thấy lợi ích rõ rệt từ việc tăng replica. Locust có thời gian nghỉ giữa các request và cả hai lượt đều gặp độ trễ mô phỏng của LLM. p99 ở 1.700 ms trong cả hai lượt phù hợp với nhóm request chậm do mock LLM. Hai số đo này chưa đủ để xác định giới hạn công suất của cụm.

---

## 6. Kết luận

1. p99 phản ánh nhóm request chậm khi độ trễ trung bình và p95 còn ít thay đổi. Khi số request chậm tăng, p95 cũng tăng rõ rệt.
2. Eval đo chất lượng nội dung. Quality gate phát hiện câu trả lời sai ngay cả khi API trả `200`.
3. Dashboard cho thấy thời điểm độ trễ và tỷ lệ lỗi tăng. Trace và log cùng `trace_id` chỉ ra bước gọi LLM là nơi cần kiểm tra.

Nếu triển khai thật, tôi sẽ thêm một kiểm tra định kỳ qua URL public với timeout và câu trả lời kỳ vọng. Alert này giúp phát hiện lỗi tại DNS, TLS hoặc reverse proxy và phát hiện một số regression chất lượng từ góc nhìn người dùng.
