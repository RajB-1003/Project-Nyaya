
"""
form_pdf_builder.py -- Project Nyaya
Generates formatted government legal document drafts as PDFs.
Uses ONLY Latin-1 safe characters (Helvetica core font compatibility).

Three document types:
  1. RTI Application (Section 6, Right to Information Act 2005)
  2. Domestic Violence Complaint (PWDVA 2005 -- to Protection Officer / Police)
  3. Mutual Consent Divorce Petition Draft (Section 13B, Hindu Marriage Act 1955)
"""

from pathlib import Path
from fpdf import FPDF

                             
C_HEADER    = (30,  58, 138)                             
C_ACCENT    = (37,  99, 235)                                   
C_GRAY      = (100, 116, 139)                              
C_BLACK     = (15,  23,  42)               
C_MISSING   = (180, 60,  0)                                 
C_FILLED    = (0,   100, 0)                                  

BLANK       = "_________________________________"
BLANK_SHORT = "__________________"


                                                                             
                       
                                                                             

def _start(pdf: FPDF, title: str, subtitle: str, note: str) -> None:
    """Render the Nyaya header + document title block."""
                 
    pdf.set_fill_color(*C_HEADER)
    pdf.rect(0, 0, 210, 28, "F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_xy(10, 5)
    pdf.cell(190, 8, "PROJECT NYAYA -- AI Legal Assistance", align="C")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_xy(10, 13)
    pdf.cell(190, 6, "Free Legal Document Generation for Marginalized Communities in India", align="C")
    pdf.set_font("Helvetica", "I", 7)
    pdf.set_xy(10, 20)
    pdf.cell(190, 5, note, align="C")

               
    pdf.set_fill_color(*C_ACCENT)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(10, 31)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(190, 10, title, align="C", fill=True)
    pdf.set_text_color(80, 80, 80)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_xy(10, 43)
    pdf.cell(190, 6, subtitle, align="C")
    pdf.set_y(52)


def _sec(pdf: FPDF, label: str) -> None:
    """Blue section heading strip."""
    pdf.set_fill_color(*C_ACCENT)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_x(10)
    pdf.cell(190, 6, "  " + label.upper(), fill=True, ln=True)
    pdf.ln(2)


def _row(pdf: FPDF, label: str, value) -> None:
    """Single labelled value row."""
    pdf.set_x(12)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*C_BLACK)
    pdf.cell(55, 7, label + ":", border="B")
    pdf.set_font("Helvetica", "", 9)
    if value:
        pdf.set_text_color(*C_FILLED)
        pdf.cell(133, 7, str(value).strip(), border="B", ln=True)
    else:
        pdf.set_text_color(*C_MISSING)
        pdf.cell(133, 7, BLANK, border="B", ln=True)
    pdf.set_text_color(*C_BLACK)
    pdf.ln(1)


def _row2(pdf: FPDF, lbl1: str, v1, lbl2: str, v2) -> None:
    """Two fields on one line."""
    pdf.set_x(12)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*C_BLACK)
    pdf.cell(30, 7, lbl1 + ":")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(C_FILLED if v1 else C_MISSING)
    pdf.cell(55, 7, str(v1).strip() if v1 else BLANK_SHORT, border="B")
    pdf.set_text_color(*C_BLACK)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(30, 7, "  " + lbl2 + ":")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(C_FILLED if v2 else C_MISSING)
    pdf.cell(60, 7, str(v2).strip() if v2 else BLANK_SHORT, border="B", ln=True)
    pdf.set_text_color(*C_BLACK)
    pdf.ln(1)


def _block(pdf: FPDF, label: str, value, lines: int = 3) -> None:
    """Multi-line text block field."""
    pdf.set_x(12)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*C_BLACK)
    pdf.cell(190, 6, label + ":", ln=True)
    pdf.set_x(12)
    pdf.set_font("Helvetica", "", 9)
    if value:
        pdf.set_text_color(*C_FILLED)
        pdf.multi_cell(186, 5, str(value).strip(), border=1)
    else:
        pdf.set_text_color(*C_MISSING)
        pdf.set_fill_color(255, 248, 230)
        pdf.cell(186, lines * 6, "", border=1, fill=True, ln=True)
    pdf.set_text_color(*C_BLACK)
    pdf.ln(2)


def _checkbox(pdf: FPDF, label: str, checked: bool) -> None:
    """Simple ASCII checkbox row."""
    pdf.set_x(14)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*C_BLACK)
    mark = "[X]" if checked else "[ ]"
    pdf.cell(12, 6, mark)
    pdf.cell(175, 6, label, ln=True)


def _disclaimer(pdf: FPDF) -> None:
    """Standard legal disclaimer box."""
    pdf.set_fill_color(254, 243, 199)
    pdf.set_draw_color(180, 120, 0)
    pdf.set_x(10)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(120, 70, 0)
    pdf.cell(190, 5, "IMPORTANT NOTICE", border="TB", fill=True, ln=True, align="C")
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_x(10)
    pdf.multi_cell(
        190, 4.5,
        "This document is an AI-assisted DRAFT generated by Project Nyaya for informational purposes only. "
        "It is NOT a substitute for professional legal advice. Before filing, please review it with a "
        "qualified legal aid advocate or lawyer. "
        "Fields shown in orange/blank lines are incomplete and MUST be filled before submission. "
        "Green fields were extracted from your voice statement.",
        border="LRB", fill=True,
    )


def _sig(pdf: FPDF) -> None:
    """Signature block."""
    pdf.ln(5)
    pdf.set_x(10)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(95, 6, "Place:  " + BLANK_SHORT)
    pdf.cell(95, 6, "Signature: " + BLANK_SHORT, ln=True)
    pdf.set_x(10)
    pdf.cell(95, 6, "Date:   " + BLANK_SHORT)
    pdf.cell(95, 6, "Name (in full): " + BLANK_SHORT, ln=True)


def _info_box(pdf: FPDF, heading: str, lines_text: str) -> None:
    """Blue info box at the end of document."""
    pdf.set_fill_color(219, 234, 254)
    pdf.set_x(10)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(30, 58, 138)
    pdf.cell(190, 5, heading, fill=True, ln=True, align="C")
    pdf.set_font("Helvetica", "", 8)
    pdf.set_x(10)
    pdf.multi_cell(190, 4.5, lines_text, fill=True, border="LRB")
    pdf.set_text_color(*C_BLACK)
    pdf.ln(5)


                                                                             
                            
                                                                             

def build_rti_pdf(data: dict, pdf_path: Path) -> None:
    """RTI Application -- Section 6, RTI Act 2005."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_margins(10, 10, 10)

    _start(
        pdf,
        "APPLICATION FOR INFORMATION UNDER THE RIGHT TO INFORMATION ACT, 2005",
        "Section 6(1), Right to Information Act 2005  |  Address to the Public Information Officer (PIO)",
        "Ref: RTI Act 2005 -- BPL holders exempt from Rs. 10 fee.",
    )

    _sec(pdf, "PART A -- Applicant Details")
    _row(pdf, "Full Name", data.get("name"))
    _row(pdf, "Complete Address", data.get("address"))
    _row2(pdf, "Phone", data.get("phone"), "Email", data.get("email"))
    _row(pdf, "BPL Card Holder?", data.get("bpl_status", "No -- fee of Rs. 10 applies"))
    pdf.ln(2)

    _sec(pdf, "PART B -- Department / Authority Details")
    _row(pdf, "Department Name", data.get("department_name"))
    _row(pdf, "Department Address", data.get("department_address"))
    _row(pdf, "PIO Name (if known)", data.get("pio_name", "The Public Information Officer"))
    pdf.ln(2)

    _sec(pdf, "PART C -- Information Requested")
    _block(pdf, "Specific information I wish to obtain", data.get("information_requested"), lines=5)
    _row(pdf, "Time period of information", data.get("time_period"))
    _row(pdf, "Format required", data.get("format_required", "Certified true copies"))
    pdf.ln(2)

    _sec(pdf, "PART D -- Fee Details")
    _row(pdf, "Fee payment mode", data.get("fee_payment_mode"))
    pdf.set_x(12)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(*C_GRAY)
    pdf.multi_cell(
        186, 5,
        "Fee: Rs. 10 (General) | BPL cardholders -- EXEMPT (attach BPL card copy) | "
        "Payment: Court fee stamp / IPO / DD / Online at rtionline.gov.in"
    )
    pdf.set_text_color(*C_BLACK)
    pdf.ln(3)

    _sec(pdf, "PART E -- Declaration")
    pdf.set_x(12)
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(
        186, 5.5,
        "I hereby declare that the information requested does not relate to or affect the sovereignty "
        "and integrity of India, the security, strategic, scientific or economic interests of the State, "
        "relation with foreign State or lead to incitement of an offence. I am a citizen of India.",
    )
    pdf.ln(2)
    _sig(pdf)
    pdf.ln(5)

    _info_box(pdf, "HOW TO FILE THIS APPLICATION",
        "1. Hand deliver (get acknowledgement copy) or send by Registered Post to the PIO.\n"
        "2. File online at rtionline.gov.in for central government departments.\n"
        "3. PIO must respond within 30 days (Sec. 7) or 48 hours if life/liberty is concerned.\n"
        "4. No response or refusal? File First Appeal FREE within 30 days.\n"
        "5. Still no response? File Second Appeal to Central Information Commission -- cic.gov.in"
    )
    _disclaimer(pdf)
    pdf.output(str(pdf_path))


                                                                             
                                        
                                                                             

def build_dv_pdf(data: dict, pdf_path: Path) -> None:
    """DV Complaint -- PWDVA 2005, to Protection Officer / Police."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_margins(10, 10, 10)

    _start(
        pdf,
        "COMPLAINT UNDER THE PROTECTION OF WOMEN FROM DOMESTIC VIOLENCE ACT, 2005",
        "To: Protection Officer / Magistrate / Police Station  |  Section 12, PWDVA 2005",
        "Filing is FREE. Emergency Protection Order: Section 18. Response within 3 days.",
    )

    _sec(pdf, "PART A -- Complainant (Aggrieved Person)")
    _row(pdf, "Full Name", data.get("complainant_name"))
    _row2(pdf, "Age", data.get("complainant_age"), "Phone", data.get("complainant_phone"))
    _row(pdf, "Safe Address", data.get("complainant_address"))
    pdf.ln(2)

    _sec(pdf, "PART B -- Respondent")
    _row(pdf, "Respondent Name", data.get("respondent_name"))
    _row2(pdf, "Relation", data.get("respondent_relation"), "Address", data.get("respondent_address"))
    pdf.ln(2)

    _sec(pdf, "PART C -- Nature of Violence (Section 3, PWDVA 2005)")
    violence = data.get("nature_of_violence") or []
    if isinstance(violence, str):
        violence = [violence]
    joined = " ".join(violence)
    _checkbox(pdf, "Physical Abuse (Sec. 3(a))",        "Physical"  in joined)
    _checkbox(pdf, "Sexual Abuse (Sec. 3(b))",          "Sexual"    in joined)
    _checkbox(pdf, "Verbal / Emotional Abuse (Sec. 3(c))", any(x in joined for x in ["Verbal","Emotional"]))
    _checkbox(pdf, "Economic Abuse (Sec. 3(d))",        "Economic"  in joined)
    _checkbox(pdf, "Dowry Harassment (Sec. 498A IPC)",  "Dowry"     in joined)
    pdf.ln(2)

    _sec(pdf, "PART D -- Incident Details")
    _row(pdf, "Date(s) of Incident", data.get("incident_date"))
    _block(pdf, "Describe incidents in your own words", data.get("incident_description"), lines=6)
    _row(pdf, "Witnesses (name & contact)", data.get("witnesses"))
    pdf.ln(2)

    _sec(pdf, "PART E -- Children (if any)")
    children = data.get("children") or []
    if children:
        for c in children:
            n = c.get("name", "") if isinstance(c, dict) else str(c)
            a = c.get("age", "")  if isinstance(c, dict) else ""
            _row2(pdf, "Child Name", n, "Age", a)
    else:
        _row(pdf, "Children", data.get("children_text"))
    pdf.ln(2)

    _sec(pdf, "PART F -- Relief Sought (Sections 18-22, PWDVA 2005)")
    _checkbox(pdf, "Protection Order (Sec. 18) -- stop respondent from further violence",
              data.get("relief_protection", True))
    _checkbox(pdf, "Residence Order (Sec. 19) -- right to live in shared household",
              data.get("relief_residence", False))
    monetary = data.get("relief_monetary_amount")
    _checkbox(pdf, "Monetary Relief (Sec. 20) -- Amount: Rs. " + (str(monetary) if monetary else BLANK_SHORT),
              bool(monetary))
    _checkbox(pdf, "Child Custody (Sec. 21) -- interim custody",
              data.get("relief_custody", False))
    pdf.ln(3)

    _sec(pdf, "PART G -- Declaration")
    pdf.set_x(12)
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(
        186, 5.5,
        "I, the undersigned, declare that the information given above is true and correct to the best "
        "of my knowledge. I request the Hon'ble Magistrate / Protection Officer to take immediate action "
        "on my complaint and grant the reliefs sought above under the PWDVA 2005.",
    )
    pdf.ln(2)
    _sig(pdf)
    pdf.ln(5)

    _info_box(pdf, "EMERGENCY CONTACTS -- ACT IMMEDIATELY IF IN DANGER",
        "Women Helpline: 181 (Free, 24x7)  |  Police: 100  |  One Stop Centre: 181\n"
        "Protection Officer: At district court or nearest police station -- completely FREE.\n"
        "Magistrate MUST issue Protection Order within 3 days of receiving complaint (Sec. 12, PWDVA).\n"
        "You can ALSO file Section 498A IPC at the police station for criminal action."
    )
    _disclaimer(pdf)
    pdf.output(str(pdf_path))


                                                                             
                                                                    
                                                                             

def build_divorce_pdf(data: dict, pdf_path: Path) -> None:
    """Section 13B Mutual Consent Divorce Petition Draft."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_margins(10, 10, 10)

    _start(
        pdf,
        "MUTUAL CONSENT DIVORCE PETITION -- DRAFT",
        "Section 13B, Hindu Marriage Act 1955  |  File in Family Court of last shared residence",
        "Both petitioners must have lived separately for min. 1 year. Court fee: approx. Rs. 200-500.",
    )

    _sec(pdf, "IN THE FAMILY COURT AT ___________________")
    pdf.set_x(12)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(190, 6, "Divorce Petition No. _____ / 20____  (to be filled by court)", ln=True)
    pdf.ln(3)

    _sec(pdf, "PETITIONER 1 (Husband / First Party)")
    _row(pdf, "Full Name", data.get("petitioner1_name"))
    _row2(pdf, "Age", data.get("petitioner1_age"), "Occupation", data.get("petitioner1_occupation"))
    _row(pdf, "Current Address", data.get("petitioner1_address"))
    pdf.ln(2)

    _sec(pdf, "PETITIONER 2 (Wife / Second Party)")
    _row(pdf, "Full Name", data.get("petitioner2_name"))
    _row2(pdf, "Age", data.get("petitioner2_age"), "Occupation", data.get("petitioner2_occupation"))
    _row(pdf, "Current Address", data.get("petitioner2_address"))
    pdf.ln(2)

    _sec(pdf, "MARRIAGE DETAILS")
    _row(pdf, "Date of Marriage", data.get("marriage_date"))
    _row(pdf, "Place of Marriage", data.get("marriage_place"))
    _row(pdf, "Marriage Reg. No.", data.get("marriage_registration_number"))
    pdf.ln(2)

    _sec(pdf, "SEPARATION DETAILS")
    _row(pdf, "Date of Separation", data.get("separation_date"))
    _row(pdf, "Address (living separately)", data.get("separation_address"))
    pdf.set_x(12)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(*C_GRAY)
    pdf.cell(186, 5, "Note: Minimum 1 year of separation required under Section 13B(1), HMA 1955.")
    pdf.set_text_color(*C_BLACK)
    pdf.ln(4)

    _sec(pdf, "CHILDREN (if any)")
    children = data.get("children") or []
    if children:
        for c in children:
            n = c.get("name", "") if isinstance(c, dict) else str(c)
            a = c.get("age", "")  if isinstance(c, dict) else ""
            _row2(pdf, "Child Name", n, "Age", a)
    else:
        _row(pdf, "Children details", data.get("children_text", "No children / Not provided"))
    pdf.ln(2)

    _sec(pdf, "SETTLEMENT TERMS (must be agreed by BOTH parties before filing)")
    _row(pdf, "Alimony / Maintenance", data.get("alimony_amount"))
    _row(pdf, "Alimony Payment Terms", data.get("alimony_terms"))
    _row(pdf, "Child Custody Arrangement", data.get("custody_arrangement"))
    _row(pdf, "Stridhan / Dowry settled?", data.get("stridhan_settled"))
    _row(pdf, "Immovable property settled?", data.get("property_settled"))
    pdf.ln(2)

    _sec(pdf, "PRAYER TO THE HON'BLE COURT")
    pdf.set_x(12)
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(
        186, 5.5,
        "The petitioners, having mutually agreed and having lived separately for more than one year, "
        "most respectfully pray that this Hon'ble Court may be pleased to:\n"
        "  (a) Pass a decree of dissolution of marriage under Section 13B, Hindu Marriage Act 1955.\n"
        "  (b) Record the settlement terms as agreed regarding alimony, child custody, and property.\n"
        "  (c) Grant any other relief this Hon'ble Court deems fit.",
    )
    pdf.ln(3)

    _sec(pdf, "DECLARATION & VERIFICATION")
    pdf.set_x(12)
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(
        186, 5.5,
        "We, the petitioners, verify that the contents of this petition are true and correct "
        "to the best of our knowledge and belief. Nothing has been concealed or falsely stated herein.",
    )
    pdf.ln(4)
    pdf.set_x(12)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(90, 6, "Signature of Petitioner 1: " + BLANK_SHORT)
    pdf.cell(90, 6, "Signature of Petitioner 2: " + BLANK_SHORT, ln=True)
    pdf.set_x(12)
    pdf.cell(90, 6, "Date: " + BLANK_SHORT)
    pdf.cell(90, 6, "Date: " + BLANK_SHORT, ln=True)
    pdf.ln(3)

    _info_box(pdf, "PROCEDURE -- WHAT TO DO NEXT",
        "1. Get this draft reviewed and finalised by a lawyer before filing.\n"
        "2. File in the Family Court of the district where you last lived together.\n"
        "3. First Motion: Both appear together; judge records statements on oath.\n"
        "4. Wait 6 months (cooling-off under Sec. 13B(2)) -- court may waive if marriage is irretrievably broken.\n"
        "   (Amardeep Singh v. Harveen Kaur, Supreme Court 2017)\n"
        "5. Second Motion: Both confirm mutual consent. Decree of divorce is granted."
    )
    _disclaimer(pdf)
    pdf.output(str(pdf_path))
