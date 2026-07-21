"""
Indeed Email Parser

Parses Indeed job alert emails to extract job details
"""

import re
from typing import Dict, Optional


def parse_indeed_email(body: str, subject: str) -> Optional[Dict]:
    """
    Parse Indeed job alert email

    Indeed email format (example):
    ---
    Subject: React Developer jobs in San Francisco, CA

    React Developer
    Company Name
    San Francisco, CA
    $80,000 - $120,000 a year

    Job description goes here...

    Apply on Indeed: https://www.indeed.com/viewjob?jk=abc123def456
    ---

    TODO: Implement actual parsing logic based on real Indeed emails
    """

    # TODO: Extract job_id from URL
    job_id_match = re.search(r'jk=(\w+)', body)
    job_id = job_id_match.group(1) if job_id_match else f"indeed_{hash(body)}"[:16]

    # TODO: Extract title
    # Usually first significant line
    title = subject.split(" jobs")[0].strip() if " jobs" in subject else subject

    # TODO: Extract salary/budget
    # Look for "$X - $Y" or "$X a year" or "$X/hour"
    salary_match = re.search(r'\$(\d+)', body)
    budget = int(salary_match.group(1)) if salary_match else 0

    # TODO: Extract description
    description = body[:500]  # Placeholder

    # TODO: Extract skills
    # Indeed doesn't always list skills explicitly
    skills = []

    # TODO: Extract job URL
    url_match = re.search(r'(https://www\.indeed\.com/viewjob[^\s]+)', body)
    url = url_match.group(1) if url_match else ""

    # TODO: Extract company name
    company = ""

    # TODO: Extract location
    location = ""

    return {
        "job_id": job_id,
        "title": title,
        "budget": budget,
        "description": description,
        "skills": skills,
        "url": url,
        "posted_at": "",
        "deadline": None,
        "platform": "indeed",
        "client_info": {
            "company": company,
            "location": location
        },
        "raw_email": body
    }
