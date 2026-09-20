# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Nguyễn Khánh Linh
**Nhóm:** Skynet
**Ngày:** 2026-09-20

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
> Hai vector embedding có hướng gần giống nhau, nghĩa là hai đoạn văn bản có nội dung hoặc ý nghĩa gần nhau. Giá trị càng gần 1 thì mức độ tương đồng càng cao.

**Ví dụ có độ tương tự CAO:**
- Câu A: Người mua có thể yêu cầu hoàn tiền nếu sản phẩm bị lỗi.
- Câu B: Khách hàng được hoàn tiền khi nhận được hàng bị lỗi.
- Tại sao tương đồng: Hai câu dùng từ khác nhau nhưng cùng diễn đạt điều kiện được hoàn tiền do sản phẩm bị lỗi.

**Ví dụ có độ tương tự THẤP:**
- Câu A: Người mua có thể yêu cầu đổi trả sản phẩm trong thời hạn quy định.
- Câu B: Hệ thống cần sao lưu dữ liệu trước khi cập nhật phần mềm.
- Tại sao khác: Hai câu nói về hai chủ đề khác nhau là chính sách đổi trả và bảo trì phần mềm.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
> Cosine similarity tập trung vào hướng của vector, tức là sự tương đồng về ý nghĩa, và ít bị ảnh hưởng bởi độ dài văn bản hơn. Hai đoạn có cùng nội dung nhưng một đoạn dài hơn vẫn có thể có cosine similarity cao.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> *Trình bày phép tính:* `ceil((10000 - 50) / (500 - 50)) = ceil(9950 / 450) = ceil(22.11) = 23`.
> *Đáp án:* 23 chunks.

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> Khi `overlap=100`, số chunk là `ceil((10000 - 100) / (500 - 100)) = ceil(9900 / 400) = 25` chunks. Overlap lớn hơn giúp giữ lại ngữ cảnh nằm ở ranh giới giữa hai chunk, nhưng làm tăng số chunk và chi phí lưu trữ/embedding.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
> Hàm dùng regex `(?<=[.!?])\s+` để tách sau dấu chấm, chấm than hoặc chấm hỏi rồi loại bỏ khoảng trắng thừa. Các câu sau đó được gom theo `max_sentences_per_chunk`; văn bản rỗng hoặc chỉ có khoảng trắng trả về danh sách rỗng để tránh sinh chunk không có nội dung.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> Thuật toán lần lượt ưu tiên tách theo đoạn trống, xuống dòng, kết thúc câu, khoảng trắng và cuối cùng là ký tự. Base case là khi đoạn rỗng hoặc đã ngắn hơn/equal `chunk_size`; nếu không còn separator phù hợp, hàm cắt cố định theo `chunk_size` để luôn kết thúc.

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
> `add_documents` gọi embedding function cho từng document/chunk và lưu `id`, `content`, `metadata`, embedding vào danh sách trong bộ nhớ. `search` nhúng query, tính dot product giữa vector query và từng vector đã lưu, sau đó sắp xếp giảm dần theo score và lấy `top_k`.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> `search_with_filter` lọc metadata trước rồi mới nhúng query và xếp hạng các record còn lại; cách này ngăn policy buyer và seller lẫn vào nhau. `delete_document` loại mọi record có `metadata["doc_id"]` trùng với doc_id cần xóa và trả về liệu có record nào thực sự bị xóa hay không.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> Agent truy xuất top-k chunks, dùng `search_with_filter` khi có metadata filter, đánh số từng nguồn rồi ghép thành phần `Context` trong prompt. Prompt yêu cầu LLM chỉ dùng context, báo không tìm thấy nếu thiếu thông tin và trích số nguồn như `[1]`; sau đó `llm_fn` nhận prompt để sinh câu trả lời.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```
55 passed
```

**Số lượng bài test vượt qua (pass):** 55 / 55

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | Người mua có thể yêu cầu hoàn tiền nếu sản phẩm bị lỗi. | Khách hàng được hoàn tiền khi nhận được hàng bị lỗi. | Cao | 0.8796 | Có |
| 2 | Người mua có thể yêu cầu đổi trả sản phẩm trong thời hạn quy định. | Hệ thống cần sao lưu dữ liệu trước khi cập nhật phần mềm. | Thấp | 0.7595 | Có |
| 3 | Nhà Bán cần lưu video đóng gói trong 45 ngày. | Tiki yêu cầu người bán giữ clip đóng gói tối thiểu 45 ngày. | Cao | 0.8403 | Có |
| 4 | Bảo hành qua Shopee dự kiến mất 20 đến 45 ngày làm việc. | Nhà Bán Tiki cam kết bảo hành tối đa 30 ngày. | Thấp | 0.7402 | Có |
| 5 | Mô hình FBT yêu cầu Nhà Bán rút hàng trong 32 ngày. | Mô hình Dropship yêu cầu Nhà Bán cung cấp bằng chứng trong 2 ngày. | Thấp | 0.7817 | Có |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> Cặp 5 vẫn đạt 0.7817 dù hai câu nói về hai mô hình và hai nghĩa vụ khác nhau. Điều này cho thấy embedding nhận ra chủ đề chung là quy định bảo hành cho Nhà Bán, nên similarity cao không tự động có nghĩa là hai câu có cùng câu trả lời hoặc cùng điều kiện áp dụng.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của bạn trong gói `src`. **5 câu hỏi này phải trùng với các thành viên cùng nhóm** (xem `REPORT_NHOM.md`).

**Chiến lược cá nhân:** `RecursiveChunker(chunk_size=500)`; 34 chunk, độ dài trung bình 354,62 ký tự.

| # | Câu hỏi (Query) | Metadata filter | Nguồn gold | Top-1 chunk (tóm tắt) | Similarity | Gold chunk trong top-3? | Câu trả lời Agent | Embedding / LLM | Điểm |
|---|---|---|---|---|---:|---|---|---|---:|
| 1 | Người mua cần chuẩn bị giấy tờ gì để được bảo hành miễn phí trên Shopee? | `{"audience": "buyer"}` | `warranty-buyer-shopee`, “Điều kiện bảo hành” | Shopee: các trường hợp cần Trung tâm bảo hành thẩm định và các trường hợp không được bảo hành. | 0.901 | Có, top-3 | Cần hóa đơn điện tử hoặc mã đơn hàng; phiếu/tem bảo hành còn nguyên vẹn; serial/model khớp thông tin bảo hành. | `nvidia/nemotron-3-embed-1b` / `openai/gpt-oss-20b` | 1/2 |
| 2 | Nhà Bán Tiki không xác nhận phương án xử lý trong 02 ngày làm việc thì sao? | `{"audience": "seller"}` | `warranty-seller-general-tiki`, Câu 4 | Dropship: trách nhiệm xử lý khi lỗi do Nhà Bán hoặc không do Nhà Bán. | 0.762 | Không | “I could not find an answer to that question in the provided context.” | `nvidia/nemotron-3-embed-1b` / `openai/gpt-oss-20b` | 0/2 |
| 3 | Trong mô hình FBT, Nhà Bán phải rút hàng lỗi không đủ điều kiện nhập kho trong bao lâu? | `{"audience": "seller", "fulfillment_model": "fbt"}` | `warranty-seller-fbt-tiki`, Bước 1–2 | Quy trình FBT Bước 1–2: tiếp nhận, tạo mã khiếu nại, thu hồi và xử lý hàng không đủ điều kiện nhập kho. | 0.877 | Có, top-1 | Nhà Bán cần rút hàng trong **32 ngày làm việc** kể từ khi phiếu được tạo. `[1]` | `nvidia/nemotron-3-embed-1b` / `openai/gpt-oss-20b` | 2/2 |
| 4 | Ở mô hình Dropship, nếu Nhà Bán từ chối xử lý đổi trả bảo hành thì phải cung cấp bằng chứng hợp lệ trong bao lâu? | `{"audience": "seller", "fulfillment_model": "dropship"}` | `warranty-seller-dropship-tiki`, mục I | Phần giới thiệu mô hình Dropship và phạm vi hướng dẫn. | 0.904 | Không | “I could not find that information in the provided context.” | `nvidia/nemotron-3-embed-1b` / `openai/gpt-oss-20b` | 0/2 |
| 5 | Trong mô hình SD, Tiki xử lý và quyết định khiếu nại trong thời gian bao lâu? | `{"audience": "seller", "fulfillment_model": "sd"}` | `warranty-seller-sd-tiki`, mục II | Cam kết vận hành SD về thanh toán, đóng gói và bàn giao hàng. | 0.707 | Có, top-3 | Tiki xử lý và quyết định khiếu nại trong **02–07 ngày làm việc**. `[3]` | `nvidia/nemotron-3-embed-1b` / `openai/gpt-oss-20b` | 1/2 |

**Bao nhiêu câu hỏi có gold chunk trong top-3?** 3 / 5

**Tổng điểm benchmark:** 4 / 10.

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
> Chunk theo heading/mục giữ điều khoản và tiêu đề nguồn đi cùng nhau; trong benchmark hiện tại, chiến lược này lấy được gold chunk Dropship ở top-3 trong khi Recursive không lấy được. Metadata filter cũng quan trọng: với Heading ở Q4 và Recursive ở Q5, filter đúng `fulfillment_model` đưa gold chunk vào top-3 sau khi kết quả không filter bị lẫn các quy trình gần nghĩa.

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | 5 / 5 |
| Hướng tiếp cận của tôi (My Approach) | 10 / 10 |
| Hoàn thiện code (Core Implementation — tests) | 30 / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | 5 / 5 |
| Kết quả truy xuất của tôi (Competition Results) | 4 / 10 |
| **Tổng phần cá nhân** | **54 / 60** |
