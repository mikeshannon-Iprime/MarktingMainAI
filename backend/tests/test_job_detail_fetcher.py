from app.services.job_detail_fetcher import (
    html_to_text,
    is_placeholder_description,
    _extract_from_json_blobs,
)


def test_html_to_text_strips_tags():
    text = html_to_text("<div>Build <b>APIs</b></div><script>evil()</script>")
    assert "Build APIs" in text
    assert "evil" not in text


def test_placeholder_detection():
    assert is_placeholder_description("Java Developer at Acme. Live job from Dice.", role="Java Developer", company="Acme")
    assert is_placeholder_description("Short blurb", role="Engineer", company="Acme")
    assert not is_placeholder_description(
        "Responsibilities include designing distributed systems and mentoring engineers across multiple product squads for cloud delivery.",
        role="Engineer",
        company="Acme",
    )


def test_extract_job_posting_from_json_ld():
    page = """
    <html><head>
    <script type="application/ld+json">
    {
      "@type": "JobPosting",
      "title": "Senior Java Developer",
      "description": "<p>Design Spring Boot microservices and own production reliability for payment APIs across multiple regions.</p>"
    }
    </script>
    </head></html>
    """
    found = _extract_from_json_blobs(page)
    assert found["title"] == "Senior Java Developer"
    assert "Spring Boot microservices" in found["description"]


def test_is_search_listing_url():
    from app.services.job_detail_fetcher import is_search_listing_url

    assert is_search_listing_url("https://www.dice.com/jobs?q=Java&location=Remote")
    assert not is_search_listing_url("https://www.dice.com/job-detail/abc-123")


def test_normalize_detail_candidates_from_search_html():
    from app.services.job_detail_fetcher import _normalize_detail_candidates

    page = '''
    <a href="/job-detail/aaaa1111-bbbb-cccc-dddd-eeeeeeeeeeee">Java Dev</a>
    <a href="https://www.dice.com/job-detail/ffff2222-bbbb-cccc-dddd-eeeeeeeeeeee">Other</a>
    '''
    urls = _normalize_detail_candidates(page, "https://www.dice.com/jobs?q=Java")
    assert any("/job-detail/aaaa1111" in url for url in urls)
    assert any("/job-detail/ffff2222" in url for url in urls)
