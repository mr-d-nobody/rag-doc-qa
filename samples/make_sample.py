"""Generate samples/company_policy.pdf (fictional) used by eval.py. Run: python samples/make_sample.py"""
from pathlib import Path

from fpdf import FPDF

PAGES = [
    "Northwind Labs Company Policy Manual. Chapter 1: Working hours. Core working hours are 10:00 to 16:00 local time. "
    "Employees are expected to complete 40 hours per week. Flexible start times between 7:00 and 10:00 are allowed with "
    "team agreement. Overtime must be approved in advance by a department head and is compensated at 1.5 times the base rate.",
    "Chapter 2: Leave. Employees receive 22 days of paid vacation per year, accrued monthly. Up to 5 unused days may be "
    "carried over until March 31 of the next year. Parental leave is 16 weeks fully paid for the primary caregiver and "
    "6 weeks for the secondary caregiver. Bereavement leave is 5 days for immediate family.",
    "Chapter 3: Remote and hybrid work. Employees may work remotely up to 2 days per week by default. Fully remote "
    "arrangements require VP approval and are reviewed every 6 months. A home office stipend of 400 dollars is paid once "
    "at joining. Remote employees must be reachable on the team chat during core hours.",
    "Chapter 4: Travel and expenses. Book flights at least 14 days in advance when possible. Economy class is required "
    "for flights under 5 hours. Hotel stays are capped at 180 dollars per night in major cities and 120 dollars elsewhere. "
    "Expense reports must be filed within 45 days with itemised receipts for any amount over 25 dollars.",
    "Chapter 5: Information security. Passwords must be at least 14 characters and rotated every 180 days. Multi-factor "
    "authentication is mandatory for email, the code repository and the cloud console. Lost or stolen devices must be "
    "reported to the security team within 2 hours. Personal USB drives are prohibited on company laptops.",
    "Chapter 6: Performance reviews. Reviews happen twice a year, in June and December. Ratings use a 5 point scale. "
    "A rating of 4 or higher makes an employee eligible for the annual bonus. Employees rated below 2 for two consecutive "
    "cycles are placed on a 90 day improvement plan with a named mentor.",
    "Chapter 7: Learning and development. Each employee has an annual learning budget of 1200 dollars for courses, books "
    "and conferences. Certifications that are directly relevant to the role are reimbursed in full after passing the exam. "
    "Employees must share a 15 minute summary with their team after attending a paid conference.",
    "Chapter 8: Health and wellbeing. The company covers 90 percent of employee health insurance premiums and 60 percent "
    "for dependants. A wellness allowance of 50 dollars per month can be used for gym memberships or meditation apps. "
    "Free confidential counselling is available through the employee assistance programme, up to 8 sessions per year.",
]

pdf = FPDF()
pdf.set_font("Helvetica", size=12)
for text in PAGES:
    pdf.add_page()
    pdf.multi_cell(0, 8, text)
out = Path(__file__).parent / "company_policy.pdf"
pdf.output(str(out))
print("wrote", out)
