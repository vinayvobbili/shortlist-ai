import pytest

from shortlist_ai.schema import Education, Experience, Link, Resume


@pytest.fixture
def resume() -> Resume:
    return Resume(
        full_name="Priya Raman",
        email="priya.raman@example.com",
        phone="+1 (206) 555-0142",
        location="Seattle, WA",
        links=[Link(label="LinkedIn", url="linkedin.com/in/priyaraman")],
        summary="Priya is a security engineer; she led IR at Northwind. Contact priya.raman@example.com.",
        experience=[
            Experience(company="Northwind Health", title="Senior Security Engineer", location="Remote",
                       start_date="2022-03", end_date=None, is_current=True,
                       highlights=["Built SOAR playbooks in Python that cut triage time by 60%",
                                   "Ms. Raman led her team through 3 ransomware incidents"]),
            Experience(company="Contoso Bank", title="Security Analyst II", location="Charlotte, NC",
                       start_date="2018-06", end_date="2022-02", is_current=False,
                       highlights=["Tuned Splunk correlation searches; built ASP.NET tooling"]),
        ],
        education=[Education(institution="Georgia Tech", degree="B.S.", field_of_study="Computer Science",
                             graduation_year=2018)],
        skills=["Python", "Splunk", "ASP.NET"],
        certifications=["GCIH"],
        languages=["English", "Tamil"],
    )
