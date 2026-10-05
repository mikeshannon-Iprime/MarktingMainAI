from app.services.resume_ai import _rule_based_profile_parse


def test_parses_name_label_with_flattened_title_header():
    text = (
        "Name: Ramya Morampudi                                                                                            "
        "Sr. Java Full Stack Developer Email: ramyam849881@gmail.com Ph: 908-356-9903\n"
        "Location: Edison, NJ\n"
        "https://www.linkedin.com/in/ramya-morampudi\n"
        "Skills: Java, Spring Boot, Microservices\n"
    )
    parsed = _rule_based_profile_parse(text)
    assert parsed["fullName"] == "Ramya Morampudi"
    assert parsed["email"] == "ramyam849881@gmail.com"
    assert parsed["phone"] == "908-356-9903"
    assert parsed["location"] == "Edison, NJ"
    assert parsed["linkedin"] == "https://www.linkedin.com/in/ramya-morampudi"
    assert len(parsed["fullName"]) <= 120


def test_skips_curriculum_vitae_header_for_name():
    text = (
        "CURRICULUM VITAE\n"
        "Alex Chen\n"
        "alex.chen@example.com\n"
        "(415) 555-0100\n"
        "San Francisco, CA\n"
        "Senior Backend Engineer\n"
    )
    parsed = _rule_based_profile_parse(text)
    assert parsed["fullName"] == "Alex Chen"
    assert parsed["email"] == "alex.chen@example.com"
    assert parsed["location"] == "San Francisco, CA"
