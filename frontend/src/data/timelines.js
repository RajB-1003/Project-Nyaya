/**
 * timelines.js
 * Hardcoded step-by-step legal procedure arrays for Project Nyaya.
 * Each step has: { id, title, description }
 */

export const RTI_TIMELINE = [
  {
    id: 1,
    title: "Identify the Right Department",
    description:
      "Find the government department or ministry that holds the information you need. Every public authority has a designated Public Information Officer (PIO).",
  },
  {
    id: 2,
    title: "Draft Your Application",
    description:
      "Write a simple letter addressed to the PIO. Clearly state what information you want. You do NOT need to give any reason for your request.",
  },
  {
    id: 3,
    title: "Pay the Fee & Submit",
    description:
      "Pay Rs. 10 application fee (by IPO, DD, cash, or court fee stamp). BPL card holders are exempt. Submit in person, by post, or online at rtionline.gov.in.",
  },
  {
    id: 4,
    title: "Wait for Response (30 Days)",
    description:
      "The PIO must respond within 30 days. For matters involving life or liberty, the response must be within 48 hours.",
  },
  {
    id: 5,
    title: "File First Appeal (if needed)",
    description:
      "If the PIO rejects your request, provides incomplete information, or does not reply, file a First Appeal with the First Appellate Authority within 30 days.",
  },
  {
    id: 6,
    title: "File Second Appeal / Complaint",
    description:
      "If the First Appeal also fails, escalate to the Central Information Commission (CIC) or State Information Commission (SIC) for a binding order.",
  },
];

export const DV_TIMELINE = [
  {
    id: 1,
    title: "Ensure Your Immediate Safety",
    description:
      "If you are in immediate danger, call Police: 100 or the National Women Helpline: 181. Leave the location if it is safe to do so.",
  },
  {
    id: 2,
    title: "Contact a Protection Officer or Service Provider",
    description:
      "Reach out to your district's Protection Officer (appointed by the State Government) or a registered NGO / Service Provider. They are legally obligated to assist you at no cost.",
  },
  {
    id: 3,
    title: "File a Domestic Incident Report (DIR)",
    description:
      "The Protection Officer will prepare a DIR documenting the abuse. You, a relative, or any person acting on your behalf can initiate this.",
  },
  {
    id: 4,
    title: "Magistrate Issues Orders",
    description:
      "The Magistrate can issue: a Protection Order (stops contact/harassment), a Residence Order (right to stay in shared household), or Monetary Relief (maintenance, medical expenses).",
  },
  {
    id: 5,
    title: "Section 498A IPC (Optional Parallel Route)",
    description:
      "You may also file a criminal complaint under Section 498A IPC (cruelty by husband/relatives) at the nearest police station for arrest and prosecution.",
  },
  {
    id: 6,
    title: "Follow Up & Seek Shelter if Needed",
    description:
      "Stay in touch with your Protection Officer. If you need a safe place, you are entitled to stay at a government-registered shelter home.",
  },
];

export const DIVORCE_TIMELINE = [
  {
    id: 1,
    title: "Confirm Mutual Agreement",
    description:
      "Both spouses must genuinely agree to divorce. You must have lived separately for at least 1 year (or more, depending on the court).",
  },
  {
    id: 2,
    title: "Settle All Terms First",
    description:
      "Agree on alimony/maintenance, child custody & visitation, and division of property BEFORE filing. Document everything in writing.",
  },
  {
    id: 3,
    title: "File Joint Petition in Family Court",
    description:
      "Both spouses file a joint petition under Section 13B of the Hindu Marriage Act (or applicable personal law) in the Family Court of the district where you last lived together.",
  },
  {
    id: 4,
    title: "First Motion — Court Statement",
    description:
      "Both appear before the Judge. Statements are recorded. The Court grants the First Motion and a 6-month cooling-off period begins (this may be waived by the court).",
  },
  {
    id: 5,
    title: "Wait / Seek Waiver of Cooling-Off Period",
    description:
      "Wait 6 months, OR apply for a waiver if both parties are certain and the marriage has irretrievably broken down. The Supreme Court has upheld the right to waive this period.",
  },
  {
    id: 6,
    title: "Second Motion — Decree of Divorce",
    description:
      "Both appear again to confirm consent. The Court passes the final Decree of Divorce. The marriage is legally dissolved from this date.",
  },
];

export const TIMELINE_MAP = {
  RTI: RTI_TIMELINE,
  "Domestic Violence": DV_TIMELINE,
  Divorce: DIVORCE_TIMELINE,
};
