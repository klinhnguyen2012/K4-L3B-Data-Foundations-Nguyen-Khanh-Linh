# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** Skynet
**Thành viên:** [Họ tên từng thành viên]
**Ngày:** [Ngày nộp]

> **Nộp 1 bản / nhóm.** Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán…) mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Chủ đề (Domain) & Lý Do Chọn

**Chủ đề:** Chính sách bảo hành dành cho người mua và người bán trên sàn thương mại điện tử.

**Tại sao nhóm chọn chủ đề này?**
> Chính sách bảo hành có các điều kiện, thời hạn và quy trình cụ thể nên phù hợp để đánh giá khả năng truy xuất thông tin chính xác. Corpus gồm quy định cho cả người mua và người bán, vì vậy nhóm có thể kiểm chứng giá trị của metadata filter `audience` khi hai đối tượng có cùng chủ đề nhưng câu trả lời khác nhau.

### Danh sách tài liệu (Data Inventory)

| # | Tên tài liệu | Nguồn (Source URL) | Ngày lấy / Phiên bản | Số ký tự | Metadata đã gán |
|---|--------------|------------|--------------------|----------|-----------------|
| 1 | Chính sách bảo hành cho sản phẩm mua tại Shopee | https://help.shopee.vn/4/article/79046-[Quy-định]-Chính-sách-bảo-hành-cho-sản-phẩm-mua-tại-Shopee | 2026-09-20 / not-stated | 2,899 | `doc_id`, `audience=buyer`, `category`, `language`, `platform` |
| 2 | FAQ xử lý bảo hành dành cho Nhà Bán (Tiki) | https://hocvien.tiki.vn/faq/cau-hoi-thuong-gap-ve-xu-ly-doi-tra-bao-hanh/ | 2026-09-20 / not-stated | 3,306 | `doc_id`, `audience=seller`, `category`, `language`, `platform` |
| 3 | Hướng dẫn bảo hành mô hình FBT (Tiki) | https://hocvien.tiki.vn/faq/mo-hinh-fbt-huong-dan-quy-trinh-xu-ly-doi-tra-bao-hanh/ | 2026-09-20 / not-stated | 1,643 | `doc_id`, `audience=seller`, `category`, `language`, `platform`, `fulfillment_model=fbt` |
| 4 | Hướng dẫn bảo hành mô hình Dropship (Tiki) | https://hocvien.tiki.vn/faq/huong-dan-quy-trinh-xu-ly-doi-tra-bao-hanh-mo-hinh-dropship/ | 2026-09-20 / not-stated | 2,246 | `doc_id`, `audience=seller`, `category`, `language`, `platform`, `fulfillment_model=dropship` |
| 5 | Hướng dẫn bảo hành mô hình SD (Tiki) | https://hocvien.tiki.vn/faq/huong-dan-quy-trinh-xu-ly-doi-tra-bao-hanh-mo-hinh-sd/ | 2026-09-20 / not-stated | 2,031 | `doc_id`, `audience=seller`, `category`, `language`, `platform`, `fulfillment_model=sd` |

**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**
- [x] Tập tài liệu (Corpus) chỉ chứa nguồn công khai/được phép dùng và không chứa dữ liệu cá nhân, thông tin đăng nhập hoặc tài liệu nội bộ.
- [x] Mỗi tài liệu có `source_url`, `retrieved_at`, `document_version` (hoặc ngày hiệu lực) trong metadata.

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho truy xuất (retrieval)? |
|----------------|------|---------------|-------------------------------|
| `doc_id` | string | `warranty-seller-fbt-tiki` | Liên kết mọi chunk với tài liệu nguồn; cần cho `delete_document()`. |
| `audience` | enum | `buyer`, `seller` | Lọc đúng quy định theo đối tượng, tránh trả lời quy định của người bán cho người mua. |
| `category` | string | `warranty-policy` | Giới hạn truy xuất theo chủ đề chính sách khi corpus mở rộng. |
| `platform` | string | `shopee`, `tiki` | Phân biệt chính sách của từng sàn thương mại điện tử. |
| `fulfillment_model` | string (optional) | `fbt`, `dropship`, `sd` | Phân biệt các quy trình bảo hành khác nhau dành cho Nhà Bán Tiki. |
| `language` | string | `vi` | Hỗ trợ phân loại hoặc lọc theo ngôn ngữ khi thêm tài liệu đa ngữ. |
| `source_url` | URL string | URL trang chính sách gốc | Giúp truy vết và kiểm chứng câu trả lời. |
| `retrieved_at` | date string | `2026-09-20` | Cho biết độ mới của dữ liệu đã thu thập. |
| `document_version` | string | `not-stated` | Lưu phiên bản/ngày hiệu lực khi nguồn cung cấp; không bịa phiên bản nếu nguồn không nêu. |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

> Mỗi thành viên thử **một chiến lược khác nhau** trên cùng bộ tài liệu; nhóm tổng hợp và so sánh ở đây.

### Phân tích đường cơ sở (Baseline Analysis)

Chạy `ChunkingStrategyComparator().compare()` trên 2-3 tài liệu:

| Tài liệu | Chiến lược (Strategy) | Số lượng Chunk | Độ dài trung bình | Giữ được ngữ cảnh không? |
|-----------|----------|-------------|------------|-------------------|
| Chính sách bảo hành người mua Shopee | FixedSizeChunker (`fixed_size`) | 8 | 467.1 ký tự | Có ở mức cơ bản; overlap cần thiết tại ranh giới chunk. |
| Chính sách bảo hành người mua Shopee | SentenceChunker (`by_sentences`) | 9 | 320.0 ký tự | Có; câu không bị cắt giữa chừng nhưng phần điều kiện có thể bị tách khỏi tiêu đề. |
| Chính sách bảo hành người mua Shopee | RecursiveChunker (`recursive`) | 8 | 360.4 ký tự | Có; ưu tiên đoạn và câu trước khi cắt theo ký tự. |
| FAQ bảo hành Nhà Bán Tiki | FixedSizeChunker (`fixed_size`) | 9 | 473.8 ký tự | Có ở mức cơ bản; có rủi ro cắt giữa câu hỏi và câu trả lời. |
| FAQ bảo hành Nhà Bán Tiki | SentenceChunker (`by_sentences`) | 11 | 298.0 ký tự | Có; các câu FAQ được giữ nguyên nhưng chunk ngắn hơn. |
| FAQ bảo hành Nhà Bán Tiki | RecursiveChunker (`recursive`) | 9 | 365.3 ký tự | Có; phù hợp với cấu trúc đoạn/FAQ của tài liệu. |
| Hướng dẫn bảo hành Dropship Tiki | FixedSizeChunker (`fixed_size`) | 6 | 474.0 ký tự | Có ở mức cơ bản; cần overlap để giữ bước xử lý liền kề. |
| Hướng dẫn bảo hành Dropship Tiki | SentenceChunker (`by_sentences`) | 5 | 446.6 ký tự | Có; ít cắt câu nhưng phụ thuộc độ dài câu gốc. |
| Hướng dẫn bảo hành Dropship Tiki | RecursiveChunker (`recursive`) | 7 | 318.9 ký tự | Có; giữ được cụm hướng dẫn theo đoạn tốt hơn. |

### Chiến lược của từng thành viên

> Mỗi thành viên điền một khối dưới đây (copy thêm nếu nhóm có nhiều hơn 3 người).

**Thành viên 1 — Nguyễn Khánh Linh**
- **Loại chiến lược:** `FixedSizeChunker(chunk_size=500, overlap=120)`.
- **Mô tả & lý do chọn cho chủ đề này:** Mỗi chunk dài tối đa 500 ký tự và lặp lại 120 ký tự ở chunk kế tiếp. Đây là đường cơ sở rõ ràng, dễ đối chiếu với các chiến lược khác; overlap giúp không mất thông tin khi thời hạn, điều kiện hoặc một bước trong quy trình bảo hành nằm tại ranh giới giữa hai chunk.
- **Code snippet (nếu custom):** Không dùng custom chunker; dùng lớp `FixedSizeChunker` đã có trong `src/chunking.py`.
```python
chunker = FixedSizeChunker(chunk_size=500, overlap=120)
```

**Thành viên 2 — [Bổ sung họ tên]**
- **Loại chiến lược:** `RecursiveChunker(chunk_size=500)`.
- **Mô tả & lý do chọn:** Ưu tiên ngắt theo đoạn trống, xuống dòng, câu rồi mới đến khoảng trắng. Cách này phù hợp để giữ một bước xử lý hoặc một cụm FAQ trong cùng chunk, đồng thời vẫn kiểm soát độ dài khi một mục chính sách quá dài.
- **Code snippet (nếu custom):** Không dùng custom chunker.

**Thành viên 3 — [Bổ sung họ tên]**
- **Loại chiến lược:** Custom heading/section-aware chunker.
- **Mô tả & lý do chọn:** Tài liệu chính sách có tiêu đề, mục và FAQ rõ ràng, nên mỗi chunk cần mang theo tiêu đề/mục gốc để không tách câu trả lời khỏi phạm vi áp dụng. Mỗi mục dài có thể chia tiếp bằng `RecursiveChunker`, nhưng các chunk con vẫn phải giữ tiêu đề của mục đó.
- **Code snippet (nếu custom):** Đã triển khai `HeadingSectionChunker` trong `src/chunking.py`; chunker bỏ YAML front matter, nhận diện Markdown heading và lặp heading khi mục quá dài.
```python
chunker = HeadingSectionChunker(chunk_size=500)
```

### So Sánh Giữa Các Thành Viên

| Thành viên | Chiến lược (Strategy) | Điểm truy xuất (/10) | Điểm mạnh | Điểm yếu |
|-----------|----------|----------------------|-----------|----------|
| Nguyễn Khánh Linh | Fixed size 500, overlap 120 | 2 / 10 (1/5 có evidence đúng trong top-3) | Độ dài ổn định, giảm mất ngữ cảnh ở ranh giới. | Có thể cắt giữa tiêu đề/câu hỏi và nội dung trả lời. |
| [Bổ sung họ tên] | Recursive, tối đa 500 ký tự | 4 / 10 (2/5 có evidence đúng trong top-3) | Tôn trọng cấu trúc đoạn và câu của văn bản. | Chunk có thể không đồng đều; câu Dropship và video chưa lấy được evidence. |
| [Bổ sung họ tên] | Heading/section-aware custom | 4 / 10 (2/5 có evidence đúng trong top-3) | Giữ phạm vi điều khoản và tiêu đề chính sách rõ ràng; lấy đúng top-1 cho câu video. | Mục dài vẫn cần chia nhỏ hơn để truy xuất đủ danh sách SD và mốc thời gian Shopee/Dropship. |

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**
> Không có một chiến lược thắng tuyệt đối trong lần chạy này: RecursiveChunker và heading/section-aware cùng có 2/5 câu chứa evidence đúng trong top-3 (4/10 theo thang retrieval). RecursiveChunker là lựa chọn tốt nhất cho câu thời hạn có filter `audience=buyer`, còn heading/section-aware lấy đúng FAQ video ở top-1; kết quả cho thấy cần kết hợp chia theo mục với việc tách nhỏ các bước/bullet dài.

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

> **Đúng 5 câu hỏi**, đa dạng, có thể kiểm chứng; **ít nhất 1 câu** cần lọc metadata mới trả lời tốt. Đây là bộ câu hỏi chung cho mọi thành viên chạy.

| # | Câu hỏi (Query) | Câu trả lời chuẩn (Gold Answer) | Chunk nào chứa thông tin? |
|---|-------|-------------------------------|--------------------------|
| 1 | Thời gian bảo hành là bao lâu? *(bắt buộc chạy với `metadata_filter={"audience": "buyer"}` để xác định chính sách cho Người Mua)* | Khoảng 20–45 ngày làm việc kể từ khi Shopee nhận được sản phẩm. | `warranty-buyer-shopee` — mục **4. Thời gian bảo hành**, ý b. |
| 2 | Trong mô hình FBT, nếu hàng lỗi không đủ điều kiện nhập kho, Nhà Bán có bao lâu để rút hàng? | 32 ngày làm việc kể từ lúc phiếu trả hàng được tạo. | `warranty-seller-fbt-tiki` — mục **II. Quy trình xử lý bảo hành**, bước 1–2. |
| 3 | Theo mô hình Dropship, khi từ chối xử lý bảo hành, Nhà Bán phải cung cấp bằng chứng trong bao lâu? | Trong vòng 2 ngày làm việc kể từ khi nhận yêu cầu hoàn tiền hoặc nhận sản phẩm từ đơn vị vận chuyển. | `warranty-seller-dropship-tiki` — mục **I. Quy định chung**. |
| 4 | Nhà Bán cần lưu video đóng gói hàng hóa tối thiểu bao lâu? | 45 ngày: 30 ngày sau khi giao thành công cộng thời gian giao/thu hồi hàng. | `warranty-seller-general-tiki` — **Câu hỏi 11**. |
| 5 | Theo mô hình SD, Tiki có thể xử lý những phương án nào sau khi có kết quả xác minh? | Hoàn tiền, đổi sản phẩm, bảo hành hoặc từ chối trả hàng, tùy trường hợp. | `warranty-seller-sd-tiki` — mục **II. Quy trình xử lý bảo hành**. |

### Tổng hợp chất lượng truy xuất của nhóm

> Cách chấm (theo `docs/SCORING.md`): **2 điểm/câu** — top-3 chứa chunk liên quan + agent trả lời đúng (2), có liên quan nhưng thiếu/không ở top-1 (1), không có trong top-3 (0).

| # | Câu hỏi | Chiến lược tốt nhất cho câu này | Có chunk liên quan trong top-3? | Ghi chú |
|---|---------|-------------------------------|-------------------------------|---------|
| 1 | Thời gian bảo hành người mua | Recursive | Có, khi dùng `audience=buyer` | Không filter: không có evidence 20–45 ngày trong top-3; có filter: evidence xuất hiện ở top-3. |
| 2 | Thời hạn rút hàng FBT | Recursive / heading (đều top-1) | Có | Evidence 32 ngày làm việc nằm trong top-1. |
| 3 | Bằng chứng Dropship | Chưa có chiến lược đạt | Không | Document đúng xuất hiện top-1 ở recursive/heading nhưng chunk không chứa mốc 02 ngày: failure case. |
| 4 | Lưu video đóng gói | Heading/section-aware (top-1) | Có | Chunk giữ tiêu đề **Câu 11** và evidence 45 ngày. |
| 5 | Phương án xử lý SD | Chưa có chiến lược đạt | Không | Top-3 chỉ chứa một phần danh sách; chưa đủ 4 phương án trong gold answer. |

**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**
> Có, ở câu 1 với RecursiveChunker. Không filter, top-3 không có evidence “20 đến 45 ngày làm việc” dù corpus có nhiều quy định thời hạn cho seller; khi dùng `metadata_filter={"audience": "buyer"}`, evidence đúng xuất hiện trong top-3. Đây là ví dụ filter tránh nhầm chính sách theo đối tượng.

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**
> 1. Recursive và heading/section-aware cùng đạt 2/5 evidence đúng trong top-3, cao hơn fixed size (1/5) trong lần chạy này.
> 2. `audience=buyer` giúp câu hỏi thời hạn mơ hồ lấy được evidence chính sách người mua; không filter, evidence này không nằm trong top-3 của RecursiveChunker.
> 3. Câu Dropship và SD là failure case: document đúng đứng top-1 nhưng chunk không có mốc “02 ngày làm việc” hoặc không chứa đủ 4 phương án SD, cho thấy relevance theo document không đủ để trả lời đúng.

**Bài học rút ra khi so sánh trong nhóm:**
> Cùng một corpus nhưng chiến lược khác nhau tạo ra khác biệt rõ rệt về vị trí của evidence: fixed-size ổn định độ dài nhưng hay cắt phạm vi điều khoản; recursive tốt hơn cho câu thời hạn có filter; heading giữ được ngữ cảnh FAQ tốt cho câu video. Nhóm cần đánh giá chunk chứa đúng toàn bộ evidence, không chỉ nhìn doc_id ở top-1, vì câu Dropship và SD cho thấy hai điều này có thể khác nhau.

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**
> Nhóm sẽ chia thêm các mục dài theo heading con, bold label hoặc danh sách bước để tách riêng evidence “02 ngày làm việc” của Dropship. Nhóm cũng sẽ lưu heading và số mục vào metadata từng chunk, đồng thời thử `fulfillment_model` filter cho các câu FBT/Dropship/SD để giảm nhiễu giữa các quy trình seller.

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Lựa chọn tài liệu (Document Set Quality) | / 10 |
| Thiết kế chiến lược (Strategy Design) | / 15 |
| Chất lượng truy xuất (Retrieval Quality) | / 10 |
| Thuyết trình (Demo) | / 5 |
| **Tổng phần nhóm** | **/ 40** |
