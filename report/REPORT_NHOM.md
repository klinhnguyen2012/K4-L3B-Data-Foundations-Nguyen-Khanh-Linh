# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** Skynet

**Thành viên:** Phùng Trọng Chiến (`2A202602430`, thành viên 1); Ngô Lê Thuỳ Tiên (`2A202602614`, thành viên 2); Nguyễn Khánh Linh (`2A202602409`, thành viên 3); Nguyễn Hồng Khoa (`2A202602534`, thành viên 4)

**Ngày:** 2026-09-20

## 1. Lựa chọn tài liệu (10 điểm)

### Chủ đề và lý do chọn

**Chủ đề:** Chính sách bảo hành và quy trình xử lý bảo hành trên Shopee và Tiki.

Chủ đề có cấu trúc phân cấp rõ gồm điều kiện, thời hạn, quy trình và chế tài; đồng thời chứa nhiều mốc SLA cụ thể như 02, 15–30, 32 và 45 ngày. Corpus cũng phân tách rõ `buyer` và `seller`, cùng các mô hình FBT, Dropship và SD, phù hợp để đánh giá cả chunking lẫn metadata filtering.

### Data inventory

| # | Tài liệu | Nguồn | Ngày lấy / phiên bản | Số ký tự nội dung | Metadata chính |
|---|---|---|---|---:|---|
| 1 | Chính sách bảo hành cho sản phẩm mua tại Shopee | [Shopee Help Center](https://help.shopee.vn/4/article/79046-[Quy-định]-Chính-sách-bảo-hành-cho-sản-phẩm-mua-tại-Shopee) | 2026-09-20 / not-stated | 2.897 | `buyer`, `shopee`, `warranty-policy` |
| 2 | FAQ xử lý bảo hành dành cho Nhà Bán | [Học viện Tiki](https://hocvien.tiki.vn/faq/cau-hoi-thuong-gap-ve-xu-ly-doi-tra-bao-hanh/) | 2026-09-20 / not-stated | 3.304 | `seller`, `tiki`, `warranty-policy` |
| 3 | Quy trình bảo hành FBT | [Học viện Tiki](https://hocvien.tiki.vn/faq/mo-hinh-fbt-huong-dan-quy-trinh-xu-ly-doi-tra-bao-hanh/) | 2026-09-20 / not-stated | 1.641 | `seller`, `tiki`, `fbt` |
| 4 | Quy trình bảo hành Dropship | [Học viện Tiki](https://hocvien.tiki.vn/faq/huong-dan-quy-trinh-xu-ly-doi-tra-bao-hanh-mo-hinh-dropship/) | 2026-09-20 / not-stated | 2.244 | `seller`, `tiki`, `dropship` |
| 5 | Quy trình bảo hành SD | [Học viện Tiki](https://hocvien.tiki.vn/faq/huong-dan-quy-trinh-xu-ly-doi-tra-bao-hanh-mo-hinh-sd/) | 2026-09-20 / not-stated | 2.029 | `seller`, `tiki`, `sd` |

Corpus nằm tại `data/warranty-policy/`; nguồn được tổng hợp trong `sources.csv`.

### Data governance

- [x] Có 5 tài liệu công khai, không chứa dữ liệu cá nhân hoặc thông tin đăng nhập.
- [x] Mỗi tài liệu có `source_url`, `retrieved_at`, `document_version`.
- [x] Mỗi tài liệu có `audience`, `category`, `language`, `platform`.
- [x] Tài liệu theo mô hình vận hành có thêm `fulfillment_model`.
- [x] Gold answer đều trích được từ corpus, không suy đoán chính sách.

### Metadata schema

| Trường | Kiểu | Ví dụ | Công dụng |
|---|---|---|---|
| `doc_id` | string | `warranty-seller-fbt-tiki` | Truy vết, cập nhật và xóa toàn bộ chunk của tài liệu. |
| `source_url` | string | URL trang chính sách | Kiểm chứng nguồn. |
| `retrieved_at` | ISO date | `2026-09-20` | Theo dõi độ mới. |
| `document_version` | string | `not-stated` | Ghi nhận phiên bản/hiệu lực mà nguồn công bố. |
| `audience` | enum | `buyer`, `seller` | Tránh truy xuất nhầm đối tượng. |
| `category` | string | `warranty-policy` | Phân loại nghiệp vụ. |
| `platform` | enum | `shopee`, `tiki` | Giới hạn theo sàn. |
| `fulfillment_model` | enum | `fbt`, `dropship`, `sd` | Giới hạn đúng quy trình vận hành. |
| `language` | string | `vi` | Định tuyến theo ngôn ngữ. |

## 2. Thiết kế chiến lược (15 điểm)

### Baseline trên ba tài liệu

Thông số chung: `chunk_size=500`; Fixed-size baseline dùng `overlap=0` trong comparator.

| Tài liệu | Chiến lược | Số chunk | Độ dài TB | Nhận xét |
|---|---|---:|---:|---|
| Shopee buyer | Fixed-size | 6 | 482,83 | Kích thước đều nhưng có thể cắt giữa câu. |
| Shopee buyer | Sentence | 9 | 320,00 | Mạch lạc theo câu, đôi lúc mang heading sang chunk khác. |
| Shopee buyer | Recursive | 8 | 360,38 | Ưu tiên đoạn/dòng/câu nên cân bằng độ dài và ngữ cảnh. |
| Tiki FAQ | Fixed-size | 7 | 472,00 | Có nguy cơ trộn hai câu hỏi FAQ. |
| Tiki FAQ | Sentence | 11 | 298,00 | Chunk nhỏ, dễ đọc. |
| Tiki FAQ | Recursive | 9 | 365,33 | Giữ đoạn tốt hơn fixed-size. |
| Tiki FBT | Fixed-size | 4 | 410,25 | Ít chunk nhưng có ranh giới cơ học. |
| Tiki FBT | Sentence | 5 | 326,00 | Giữ câu hoàn chỉnh. |
| Tiki FBT | Recursive | 4 | 408,75 | Giữ cấu trúc đoạn tương đối tốt. |

### Các cấu hình được so sánh

| Cấu hình | Chiến lược | Tham số | Lý do |
|---|---|---|---|
| A | Fixed-size | 500 ký tự, overlap 120 | Baseline có overlap để giảm mất ngữ cảnh ở biên. |
| B | Recursive | 500 ký tự | Ưu tiên đoạn, dòng, câu rồi từ. |
| C | Heading custom | Tách heading, recursive nếu section >500 | Khai thác cấu trúc Markdown và đáp ứng yêu cầu chunk theo heading/section. |
| Thành viên 2 | `HeadingChunker` | Tách nguyên mục theo heading `##`/`###`, không fallback theo kích thước | Giữ mỗi điều khoản gốc thành một đơn vị hoàn chỉnh. |
| Thành viên 3 | `RecursiveChunker` | 500 ký tự, separator `\n\n`, `\n`, `. `, khoảng trắng, ký tự | Cân bằng ranh giới cấu trúc và kích thước; là lựa chọn mặc định được Nguyễn Khánh Linh kết luận trong báo cáo thử nghiệm. |

`HeadingSectionChunker` được cài trong `src/chunking.py`: regex tìm heading Markdown, giữ chuỗi heading cha trong chunk rồi dùng `RecursiveChunker` làm fallback cho section quá dài.

### Kết quả benchmark đã chạy trong repo của Nguyễn Khánh Linh

Backend retrieval dùng NVIDIA API với embedding model `nvidia/nemotron-3-embed-1b`. Agent dùng NVIDIA Chat model `openai/gpt-oss-20b`, chỉ trả lời từ top-3 context và được yêu cầu trích số nguồn. Cách chấm: 2 điểm khi gold chunk ở top-1 và Agent đúng; 1 điểm khi gold chunk ở top-2/top-3 và Agent đúng; 0 điểm khi gold chunk không nằm trong top-3.

| Chiến lược | Chunk | Độ dài TB | Điểm có filter | Điểm mạnh | Điểm yếu |
|---|---:|---:|---:|---|---|
| Fixed-size 500/120 | 34 | 458,68 | 3/10 | Đơn giản, overlap giữ được một phần ngữ cảnh ở biên | Cắt cơ học làm evidence bị chia; Q1, Q4 và Q5 không có gold trong top-3. |
| Recursive 500 — Nguyễn Khánh Linh | 34 | 354,62 | 4/10 | Q1 và Q5 có gold trong top-3; Q3 đạt top-1 | Q2 và Q4 không có gold trong top-3. |
| Heading + recursive 500 | 41 | 366,78 | 4/10 | Bám cấu trúc chính sách; Q3 top-1 và Q4 top-3 | Q1 và Q5 không có gold trong top-3. |

Hai chiến lược Recursive và Heading cùng đạt 4/10 nhưng thành công ở các query khác nhau. Heading lấy được gold chunk của câu Dropship (Q4), còn Recursive lấy được gold chunk của câu Shopee buyer (Q1) và SD (Q5). Kết quả của các thành viên khác cần được chính các thành viên chạy lại trên đúng năm query này trước khi nhóm chốt bảng so sánh cuối.

### Thành viên 2 — Ngô Lê Thuỳ Tiên (`2A202602614`)

- **Repo:** [K4-DAY07-NgoLeThuyTien-2A202602614](https://github.com/tiennl/K4-DAY07-NgoLeThuyTien-2A202602614)
- **Chiến lược:** custom `HeadingChunker`, tách theo heading Markdown cấp `##`/`###`.
- **Lý do:** tài liệu chính sách dùng heading làm ranh giới điều khoản; giữ heading và nội dung trong cùng chunk giúp bảo toàn điều kiện, thời hạn và hậu quả.
- **Kết quả:** Thành viên 2 tự chạy lại trên năm query thống nhất và điền kết quả trước khi nộp.

### Thành viên 3 — Nguyễn Khánh Linh (2A202602409)

- **Repo:** [K4-L3B-Data-Foundations-Nguyen-Khanh-Linh](https://github.com/klinhnguyen2012/K4-L3B-Data-Foundations-Nguyen-Khanh-Linh)
- **Chiến lược:** `RecursiveChunker(chunk_size=500)` với thứ tự separator mặc định: đoạn trống, xuống dòng, dấu chấm, khoảng trắng rồi ký tự.
- **Lý do:** ưu tiên ranh giới cấu trúc lớn trước, chỉ tách nhỏ hơn khi cần; phù hợp tài liệu chính sách có cả đoạn văn, danh sách và FAQ.
- **Kết quả chạy thật:** 34 chunk, độ dài trung bình 354,62; đạt 4/10 sau metadata filter bằng `nvidia/nemotron-3-embed-1b` và `openai/gpt-oss-20b`.

## 3. Benchmark queries và retrieval quality (10 điểm)

### Bộ câu hỏi và gold answer

| # | Query | Gold answer | Chunk nguồn |
|---|---|---|---|
| 1 | Người mua cần chuẩn bị giấy tờ gì để được bảo hành miễn phí trên Shopee? | Có hóa đơn điện tử hoặc mã đơn hàng; đối với đồ điện gia dụng cần phiếu/tem bảo hành còn nguyên vẹn. | `warranty-buyer-shopee`, mục “Điều kiện bảo hành” |
| 2 | Nhà Bán Tiki không xác nhận phương án xử lý trong 02 ngày làm việc thì sao? | Tiki có thể xử lý theo yêu cầu khách hàng và từ chối tiếp nhận khiếu nại của Nhà Bán phát sinh sau thời hạn. | `warranty-seller-general-tiki`, Câu 4 |
| 3 | Trong mô hình FBT, Nhà Bán phải rút hàng lỗi không đủ điều kiện nhập kho trong bao lâu? | Nhà Bán phải sắp xếp rút hàng trong 32 ngày làm việc kể từ khi phiếu trả hàng được tạo. | `warranty-seller-fbt-tiki`, Bước 1–2 |
| 4 | Ở mô hình Dropship, nếu Nhà Bán từ chối xử lý đổi trả bảo hành thì phải cung cấp bằng chứng hợp lệ trong bao lâu? | Trong 02 ngày làm việc kể từ khi nhận yêu cầu hoàn tiền hoặc nhận sản phẩm từ đối tác vận chuyển. | `warranty-seller-dropship-tiki`, mục I |
| 5 | Trong mô hình SD, Tiki xử lý và quyết định khiếu nại trong thời gian bao lâu? | Tiki kiểm tra, xác minh và đưa ra quyết định trong 02–07 ngày làm việc. | `warranty-seller-sd-tiki`, mục II |

Metadata filter tương ứng lần lượt là: `{"audience": "buyer"}`; `{"audience": "seller"}`; `{"audience": "seller", "fulfillment_model": "fbt"}`; `{"audience": "seller", "fulfillment_model": "dropship"}`; và `{"audience": "seller", "fulfillment_model": "sd"}`.

### So sánh ba chiến lược trên cùng query, model và filter

| # | Fixed 500/120 | Recursive 500 | Heading + recursive 500 |
|---|---|---|---|
| 1 | Gold ngoài top-3; Agent không đủ context; 0/2 | Gold top-3; Agent đúng; 1/2 | Gold ngoài top-3; Agent không đủ context; 0/2 |
| 2 | Gold top-1; Agent đúng; 2/2 | Gold ngoài top-3; Agent không đủ context; 0/2 | Gold top-2; Agent đúng; 1/2 |
| 3 | Gold top-3; Agent đúng; 1/2 | Gold top-1; Agent đúng; 2/2 | Gold top-1; Agent đúng; 2/2 |
| 4 | Gold ngoài top-3; Agent không đủ context; 0/2 | Gold ngoài top-3; Agent không đủ context; 0/2 | Gold top-3; Agent đúng; 1/2 |
| 5 | Gold ngoài top-3; Agent trả lời sai; 0/2 | Gold top-3; Agent đúng; 1/2 | Gold ngoài top-3; Agent trả lời sai; 0/2 |
| **Tổng** | **3/10** | **4/10** | **4/10** |

Nếu chọn kết quả tốt nhất của từng chiến lược theo query thì tổng là 7/10: Q1 Recursive 1 điểm, Q2 Fixed 2 điểm, Q3 Recursive/Heading 2 điểm, Q4 Heading 1 điểm và Q5 Recursive 1 điểm.

### Phân tích A/B metadata filtering

Metadata filter có tác dụng rõ ở Q4 với Heading: trước filter, top-3 gồm hai chunk Dropship chưa đủ evidence và một chunk FAQ chung; sau filter `audience=seller, fulfillment_model=dropship`, gold chunk đi vào top-3 và Agent trả lời đúng. Q5 với Recursive cũng chỉ có gold chunk trong top-3 sau khi lọc đúng mô hình `sd`. Filter vẫn có rủi ro loại mất gold chunk nếu metadata sai hoặc điều kiện lọc quá hẹp.

### Failure analysis

- **Failure Q1:** Fixed và Heading ưu tiên các chunk cùng mục “Điều kiện bảo hành” nhưng không chứa đủ bốn evidence về giấy tờ; Recursive đưa gold vào top-3.
- **Failure Q2:** Recursive ưu tiên nội dung Dropship và các đoạn FAQ gần nghĩa, làm Câu 4 rơi khỏi top-3.
- **Failure Q4:** chỉ Heading giữ được gold chunk trong top-3; Fixed và Recursive xếp phần giới thiệu/quy định gần nghĩa lên trước.
- **Failure Q5:** Fixed và Heading nhận đúng tài liệu SD nhưng không lấy chunk chứa mốc 02–07 ngày; Agent vì thế trả lời nhầm từ context khác.
- **Cải tiến:** gắn tiêu đề con cụ thể vào từng subchunk, thử chunk size 300–400, bổ sung reranking theo keyword/mốc thời gian và giữ metadata filter theo `audience` + `fulfillment_model`.

## 4. Demo và bài học nhóm (5 điểm)

### Kịch bản demo 6–8 phút

1. Giới thiệu corpus và metadata.
2. So sánh ba chiến lược bằng số chunk và độ dài trung bình.
3. Chạy `benchmark.py --strategy heading` với Q4 để thể hiện metadata filter đưa gold chunk Dropship vào top-3.
4. Giải thích failure case Q1 và Q5.
5. So sánh tổng điểm Fixed 3/10, Recursive 4/10 và Heading 4/10.

### Insight chính

- Metadata tốt có thể cứu retrieval bằng cách loại bỏ sai đối tượng và sai mô hình vận hành.
- Chunk mạch lạc chưa đảm bảo retrieval tốt nếu embedding không biểu diễn ngữ nghĩa.
- Benchmark phải giữ corpus, query, metadata filter, embedding model và LLM model cố định khi so sánh chunking.

### Nếu làm lại

Nhóm dùng MockEmbedder để kiểm thử contract và NVIDIA Nemotron để đánh giá retrieval thật. Metadata schema vẫn được giữ, nhưng filter có thể bổ sung `platform` khi query nêu rõ Shopee/Tiki; heading chunker sẽ gắn tiêu đề cụ thể hơn vào mọi subchunk sau khi section bị chia.

## Tự đánh giá hiện tại

| Tiêu chí | Điểm hiện tại |
|---|---:|
| Lựa chọn tài liệu | 10 / 10 |
| Thiết kế chiến lược | 15 / 15 |
| Kết quả retrieval tốt nhất ghép theo query | 7 / 10 |
| Demo thực tế | Chưa tự đánh giá |
| **Tổng trước demo** | **32 / 35** |
