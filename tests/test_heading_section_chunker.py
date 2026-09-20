from src.chunking import HeadingSectionChunker


def test_heading_section_chunker_keeps_each_section_with_its_heading():
    text = (
        "## Thời gian bảo hành\n"
        "Thời gian xử lý là 20 đến 45 ngày làm việc.\n\n"
        "## Trường hợp không được bảo hành\n"
        "Sản phẩm hư hỏng do người dùng sẽ không được bảo hành miễn phí."
    )

    chunks = HeadingSectionChunker(chunk_size=500).chunk(text)

    assert chunks == [
        "## Thời gian bảo hành\nThời gian xử lý là 20 đến 45 ngày làm việc.",
        "## Trường hợp không được bảo hành\n"
        "Sản phẩm hư hỏng do người dùng sẽ không được bảo hành miễn phí.",
    ]


def test_heading_section_chunker_repeats_heading_when_a_section_is_too_long():
    heading = "## Quy trình xử lý"
    text = f"{heading}\n" + "bước xử lý " * 30

    chunks = HeadingSectionChunker(chunk_size=80).chunk(text)

    assert len(chunks) > 1
    assert all(chunk.startswith(heading) for chunk in chunks)
    assert all(len(chunk) <= 80 for chunk in chunks)


def test_heading_section_chunker_excludes_yaml_front_matter_from_chunks():
    text = (
        "---\n"
        "source_url: https://example.com/policy\n"
        "audience: buyer\n"
        "---\n\n"
        "# Chính sách\n"
        "Nội dung chính sách dành cho người mua."
    )

    chunks = HeadingSectionChunker(chunk_size=500).chunk(text)

    assert chunks == ["# Chính sách\nNội dung chính sách dành cho người mua."]
