"""
Branden P. Connolly — resume profile for job matching.
Update this file if your resume changes.
"""

RESUME_TEXT = """
Name: Branden P. Connolly
Contact: BrandenPConnolly@Gmail.com | (414) 870-0443

SKILLS
Technical: Python, R, T-SQL, Oracle SQL, Spark SQL
BI/Dashboards: Crystal Reports, Tableau, Power BI
BI Tools: SSIS, SSMS, Azure DevOps
ETL: Microsoft Integration Services, Python-based pipelines
Databases: SQL Server, Oracle, Databricks
Data Governance: Collibra
Project Management: Jira
AI/ML: LLMs, feature engineering, predictive modeling, Gen AI

CERTIFICATIONS
- Healthcare Certified: Clinical, Clarity & Caboodle Data Models (EPIC)
- Vizient: UHC Analyst Certification Program
- Coursera: R Programming, Data Scientist's Toolbox, Data Engineering & ML on GCP
- DataCamp: pandas, Intermediate Python
- Databricks: Gen AI Fundamentals, Lakehouse, ML

EXPERIENCE
Lead Clinical Informatics Specialist — UCLA Health, Los Angeles, CA (09/2024–Present)
- Supervise and mentor Clinical Informatics Specialists
- Utilize LLMs to extract features from unstructured text
- Develop ML features for predictive models (Supportive Care, Oncology Care)
- Lead cross-functional team moving ML models from experimentation to production
- Design executive/clinical dashboards; build and deploy ETL pipelines
- Silver Award for AI Impact, 2025 UC Tech Conference

Clinical Informatics Specialist IV — UCLA Health (08/2022–09/2024)
- ML feature development for Population Risk, Medicare cost, Supportive Care models
- Migrated legacy ML features from SQL Server to Databricks
- Dashboard development; ETL development and deployment

Senior Data Engineer, Enterprise Analytics — Froedtert Health, Milwaukee, WI (05/2022–08/2022)
- Integrated Patient Experience external files into enterprise data warehouse
- Optimized data warehouse queries; led initial requirements for DW expansion

Programmer/Analyst IV — UCLA Health, Office of Population Health (07/2019–05/2022)
- Oracle to MS SQL Server migration
- Population Health metrics, Tableau dashboards, ETL development

Data Engineer — Froedtert | MCW CIN (06/2018–07/2019)
- Supplemental data feeds with insurance companies
- Data extracts and transforms for third parties and Enterprise Data Warehouse

Reporting Analyst / Clinical Data Analyst — Froedtert Health (01/2016–06/2018)
- SSIS and Python data extracts; pharmacy pricing DW extension
- Readmission audit tool; clinical reporting and go-live support
"""

# Keywords extracted from resume for regex-based matching
MUST_HAVE_KEYWORDS = [
    "python",
    "sql",
    "data engineer",
    "data engineering",
    "etl",
    "analytics",
    "data analyst",
    "clinical informatics",
    "clinical data",
    "health informatics",
    "databricks",
    "machine learning",
    "ml",
    "pipeline",
]

NICE_TO_HAVE_KEYWORDS = [
    "tableau",
    "power bi",
    "ssis",
    "azure",
    "spark",
    "population health",
    "healthcare",
    "epic",
    "llm",
    "generative ai",
    "r programming",
    "oracle",
    "sql server",
    "collibra",
    "bi",
    "data warehouse",
    "informatica",
    "dbt",
    "airflow",
]

# Job titles to target
TARGET_TITLES = [
    "data engineer",
    "clinical data",
    "health data",
    "clinical informatics",
    "data analyst",
    "analytics engineer",
    "bi developer",
    "etl developer",
    "ml engineer",
    "data platform",
    "informatics specialist",
]
