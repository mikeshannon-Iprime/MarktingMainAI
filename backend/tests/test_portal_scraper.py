"""Unit tests for live portal URL construction and Dice payload parsing."""

from __future__ import annotations

import json

from app.services.portal_scraper import _extract_dice_jobs, build_portal_search_url


def test_dice_search_url_includes_posted_date_location_and_ai_keyword():
    url = build_portal_search_url(
        {"name": "Dice", "url": "https://www.dice.com"},
        "Java Developer",
        "Dallas, TX",
        posted_within="3",
        keyword="Java",
    )

    assert url == (
        "https://www.dice.com/jobs?"
        "filters.postedDate=THREE&countryCode=US&location=Dallas%2C+TX&q=Java"
    )


def test_extract_dice_jobs_from_next_flight_payload():
    expected = [
        {
            "guid": "c3dfa91f-3461-4b36-a730-65ece0d8b660",
            "detailsPageUrl": (
                "https://www.dice.com/job-detail/"
                "c3dfa91f-3461-4b36-a730-65ece0d8b660"
            ),
            "companyName": "Example Corp",
            "title": "Java Developer",
        }
    ]
    payload = f'12:["page",{{"jobList":{{"data":{json.dumps(expected)}}}}}]'
    page_html = f"<script>self.__next_f.push([1,{json.dumps(payload)}])</script>"

    assert _extract_dice_jobs(page_html) == expected


def test_search_parameters_are_applied_to_all_supported_portals():
    cases = {
        "Monster": (
            "https://www.monster.com",
            "https://www.monster.com/jobs/search?"
            "q=Java&where=Dallas%2C+TX&page=1",
        ),
        "CareerBuilder": (
            "https://www.careerbuilder.com",
            "https://www.careerbuilder.com/jobs?"
            "keywords=Java&location=Dallas%2C+TX&posted=3",
        ),
        "LinkedIn": (
            "https://www.linkedin.com",
            "https://www.linkedin.com/jobs/search/?"
            "keywords=Java&location=Dallas%2C+TX&f_TPR=r259200",
        ),
        "Indeed": (
            "https://www.indeed.com",
            "https://www.indeed.com/jobs?"
            "q=Java&l=Dallas%2C+TX&fromage=3",
        ),
        "ZipRecruiter": (
            "https://www.ziprecruiter.com",
            "https://www.ziprecruiter.com/jobs-search?"
            "search=Java&location=Dallas%2C+TX&days=5",
        ),
        "Custom Portal": (
            "https://jobs.example.com/search",
            "https://jobs.example.com/search?"
            "q=Java&location=Dallas%2C+TX&postedWithin=3&countryCode=US",
        ),
    }

    for name, (base_url, expected_url) in cases.items():
        actual = build_portal_search_url(
            {"name": name, "url": base_url},
            "Java Developer",
            "Dallas, TX",
            posted_within="3",
            keyword="Java",
        )
        assert actual == expected_url
