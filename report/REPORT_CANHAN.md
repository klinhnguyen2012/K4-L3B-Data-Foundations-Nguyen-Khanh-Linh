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
> Agent truy xuất top-k chunks, đánh số từng nguồn rồi ghép thành phần `Context` trong prompt. Prompt yêu cầu LLM chỉ dùng context, báo không tìm thấy nếu thiếu thông tin và trích số nguồn như `[1]`; sau đó `llm_fn` nhận prompt để sinh câu trả lời.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```
============================== 51 passed in 0.04s ==============================
```

**Số lượng bài test vượt qua (pass):** 51 / 51

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

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | Thời gian bảo hành là bao lâu? | Chunk điều kiện bảo hành của Shopee, không chứa mốc 20–45 ngày. | 0.813 | Không đủ để trả lời | Chưa sinh bằng LLM; top-3 sau filter không có evidence 20–45 ngày. |
| 2 | Trong mô hình FBT, nếu hàng lỗi không đủ điều kiện nhập kho, Nhà Bán có bao lâu để rút hàng? | FAQ chung Tiki về xử lý bảo hành, không chứa mốc FBT 32 ngày. | 0.900 | Không | Chưa sinh bằng LLM; evidence 32 ngày không nằm trong top-3. |
| 3 | Theo mô hình Dropship, khi từ chối xử lý bảo hành, Nhà Bán phải cung cấp bằng chứng trong bao lâu? | FAQ chung Tiki có nội dung bằng chứng đóng gói nhưng không có điều kiện Dropship 02 ngày. | 0.723 | Không đủ để trả lời | Chưa sinh bằng LLM; evidence 02 ngày không nằm trong top-3. |
| 4 | Nhà Bán cần lưu video đóng gói hàng hóa tối thiểu bao lâu? | FAQ chung Tiki về thời hạn bảo hành 30 ngày; evidence video 45 ngày ở top-3. | 0.827 | Có trong top-3 | Có thể trả lời 45 ngày từ context top-3; chưa gọi LLM thật. |
| 5 | Theo mô hình SD, Tiki có thể xử lý những phương án nào sau khi có kết quả xác minh? | FAQ chung Tiki, không chứa đủ 4 phương án của mô hình SD. | 0.909 | Không | Chưa sinh bằng LLM; top-3 không có đầy đủ gold answer. |

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** 1 / 5

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
> Chunk theo heading/mục giúp giữ câu hỏi FAQ cùng nội dung trả lời, nên lấy đúng evidence video 45 ngày ở top-1. Metadata filter cũng quan trọng: với RecursiveChunker, filter `audience=buyer` đưa evidence 20–45 ngày vào top-3, trong khi không filter thì không có evidence này trong top-3.

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | 5 / 5 |
| Hướng tiếp cận của tôi (My Approach) | 10 / 10 |
| Hoàn thiện code (Core Implementation — tests) | 30 / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | 5 / 5 |
| Kết quả truy xuất của tôi (Competition Results) | 2 / 10 |
| **Tổng phần cá nhân** | **52 / 60** |
