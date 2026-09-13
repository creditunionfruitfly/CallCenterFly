#!/usr/bin/env python3
"""Build CallCenterFly Synthetic Credit-Union Calls v0.1.

This generator creates synthetic member utterances and structured decision targets.
It intentionally does not create agent scripts or fly-response wording; those are a
separate, downstream layer.
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path


VERSION = "0.1.0"
RELEASE_DATE = "2026-09-12"
SEED = 20260912
EPISODES_PER_SCENARIO = 100
SPLIT_LIMITS = (("train", 70), ("validation", 85), ("test", 100))

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DOCS_DIR = ROOT / "docs"
QA_DIR = ROOT / "qa"


SOURCES = {
    "REG_E_ERROR": {
        "title": "CFPB Regulation E § 1005.11 — Procedures for resolving errors",
        "url": "https://www.consumerfinance.gov/rules-policy/regulations/1005/11/",
        "use": "EFT error intake, investigation, documentation, and timing review.",
    },
    "REG_E_LIABILITY": {
        "title": "CFPB Regulation E § 1005.6 — Liability for unauthorized transfers",
        "url": "https://www.consumerfinance.gov/rules-policy/regulations/1005/6/",
        "use": "Unauthorized-EFT classification and escalation; never hard-code an outcome.",
    },
    "REG_Z_DISCLOSURES": {
        "title": "CFPB Regulation Z § 1026.6 — Account-opening disclosures",
        "url": "https://www.consumerfinance.gov/rules-policy/regulations/1026/6/",
        "use": "Card APR, finance-charge, transaction-fee, and other-term review.",
    },
    "REG_CC_GUIDE": {
        "title": "Federal Reserve — Regulation CC Compliance Guide",
        "url": "https://www.federalreserve.gov/supervisionreg/regcccg.htm",
        "use": "Deposit availability and check-hold scenario framing.",
    },
    "ACH_BASICS": {
        "title": "CFPB — What is an ACH transaction?",
        "url": "https://www.consumerfinance.gov/ask-cfpb/what-is-an-ach-transaction-en-1065/",
        "use": "ACH clearing, direct deposit, debits, returns, and institution-specific limits.",
    },
    "ZELLE_ENROLLMENT": {
        "title": "Zelle — Recipient has not enrolled",
        "url": "https://www.zelle.com/faq/what-if-person-i-am-sending-money-hasnt-enrolled-zelle",
        "use": "Distinguish recipient-enrollment pending status from fraud or a bank security review.",
    },
    "IDENTITY_THEFT": {
        "title": "CFPB — How can I spot identity theft?",
        "url": "https://www.consumerfinance.gov/ask-cfpb/how-can-i-spot-identity-theft-en-1359/",
        "use": "Suspicious withdrawals, unknown accounts, and account-takeover escalation.",
    },
    "NCUA_CAC": {
        "title": "NCUA MyCreditUnion.gov — Consumer Assistance Center",
        "url": "https://mycreditunion.gov/about/consumer-assistance-center",
        "use": "Credit-union complaint escalation context; not an internal call script.",
    },
}


ACTIONS = [
    ("VERIFY_IDENTITY", "Complete approved identity verification before account-specific disclosure."),
    ("CLARIFY_REQUEST", "Collect the minimum facts needed to classify the member's request."),
    ("SECURE_ACCOUNT", "Initiate the approved account-security containment path."),
    ("CHECK_TRANSACTION_STATUS", "Inspect the institution's authoritative transaction-status source."),
    ("CHECK_RECIPIENT_ENROLLMENT", "Determine whether recipient enrollment explains a pending P2P payment."),
    ("TRACE_PAYMENT", "Start or route an approved payment trace using available transaction identifiers."),
    ("EXPLAIN_GENERAL_PROCESS", "Explain a process without asserting institution-specific terms or outcomes."),
    ("REVIEW_CARD_TERMS", "Retrieve the member's applicable card agreement, offer, APR, fee, and eligibility terms."),
    ("REVIEW_ACCOUNT_FEES", "Review posted or pending fees and the institution's approved adjustment policy."),
    ("CHECK_CARD_STATUS", "Check card activation, controls, limits, fraud blocks, and network status."),
    ("START_EFT_ERROR_INTAKE", "Capture an alleged EFT error using the institution's Regulation E workflow."),
    ("START_CARD_DISPUTE", "Open or route a card-transaction dispute through the approved workflow."),
    ("BLOCK_OR_REPLACE_CARD", "Block, replace, or digitally suspend a card through approved controls."),
    ("REVIEW_DEPOSIT_HOLD", "Review deposit type, notice, availability date, and any applicable exception."),
    ("REVIEW_DEPOSIT_RETURN", "Review return reason, adjustment, notice, and next eligible deposit action."),
    ("RESTORE_DIGITAL_ACCESS", "Use the approved access-recovery and device-security workflow."),
    ("REVIEW_LOAN_ACCOUNT", "Review authoritative loan posting, due-date, balance, and servicing records."),
    ("PROVIDE_PAYOFF_QUOTE_PATH", "Initiate the official payoff-quote process and delivery method."),
    ("REVIEW_MEMBERSHIP_ELIGIBILITY", "Apply the institution's field-of-membership and account-opening criteria."),
    ("REFER_CARD_SPECIALIST", "Route to the designated card-servicing team with a complete case summary."),
    ("REFER_PAYMENTS_SPECIALIST", "Route to ACH, P2P, bill-pay, ATM, or wire operations as appropriate."),
    ("REFER_FRAUD_SPECIALIST", "Route to fraud operations with priority appropriate to the risk signal."),
    ("REFER_LENDING_SPECIALIST", "Route to lending or loan-servicing operations with collected facts."),
    ("DOCUMENT_CASE", "Record the member's claim, facts, actions, and required follow-up."),
    ("CONFIRM_NEXT_STEP", "Confirm the approved next action, owner, and policy-sourced expectation."),
    ("CLOSE_INTERACTION", "Close only after the request, ownership, and follow-up are confirmed."),
]


PROHIBITED = [
    ("DISCLOSE_ACCOUNT_DATA_BEFORE_AUTH", "Reveal account-specific information before required verification."),
    ("GUARANTEE_OUTCOME_OR_TIMING", "Promise posting, release, recovery, or completion without authoritative support."),
    ("STATE_UNVERIFIED_POLICY", "Invent or assume an APR, fee, limit, eligibility rule, or institution policy."),
    ("PROMISE_CREDIT_OR_REFUND", "Promise provisional credit, permanent credit, reimbursement, or fee reversal."),
    ("BYPASS_SECURITY_CONTROLS", "Disable or evade fraud, authentication, or transaction controls."),
    ("REVERSE_TRANSFER_WITHOUT_REVIEW", "Claim a transfer can be reversed without status and authorization review."),
    ("IGNORE_IDENTITY_WARNING", "Treat a credible identity-theft or takeover signal as routine service."),
    ("MISCLASSIFY_AUTHORIZED_SCAM", "Automatically label an authorized scam payment as an unauthorized transfer."),
    ("MAKE_ELIGIBILITY_DECISION_WITHOUT_POLICY", "Approve or deny membership or credit without the governing policy."),
]


MASKS = {
    "INTAKE_ROUTINE": ["VERIFY_IDENTITY", "CLARIFY_REQUEST", "DOCUMENT_CASE"],
    "INTAKE_HIGH_RISK": ["VERIFY_IDENTITY", "SECURE_ACCOUNT", "REFER_FRAUD_SPECIALIST", "DOCUMENT_CASE"],
    "CARD_TERMS": ["REVIEW_CARD_TERMS", "EXPLAIN_GENERAL_PROCESS", "REFER_CARD_SPECIALIST", "DOCUMENT_CASE"],
    "CARD_SERVICE": ["CHECK_CARD_STATUS", "START_CARD_DISPUTE", "BLOCK_OR_REPLACE_CARD", "REFER_CARD_SPECIALIST", "DOCUMENT_CASE"],
    "ZELLE_PENDING": ["CHECK_TRANSACTION_STATUS", "CHECK_RECIPIENT_ENROLLMENT", "EXPLAIN_GENERAL_PROCESS", "REFER_PAYMENTS_SPECIALIST", "DOCUMENT_CASE"],
    "PAYMENT_STATUS": ["CHECK_TRANSACTION_STATUS", "TRACE_PAYMENT", "EXPLAIN_GENERAL_PROCESS", "REFER_PAYMENTS_SPECIALIST", "DOCUMENT_CASE"],
    "EFT_ERROR": ["START_EFT_ERROR_INTAKE", "CHECK_TRANSACTION_STATUS", "SECURE_ACCOUNT", "REFER_PAYMENTS_SPECIALIST", "REFER_FRAUD_SPECIALIST", "DOCUMENT_CASE"],
    "FRAUD_HIGH": ["VERIFY_IDENTITY", "CLARIFY_REQUEST", "SECURE_ACCOUNT", "START_EFT_ERROR_INTAKE", "BLOCK_OR_REPLACE_CARD", "REFER_FRAUD_SPECIALIST", "DOCUMENT_CASE"],
    "DEPOSIT": ["REVIEW_DEPOSIT_HOLD", "REVIEW_DEPOSIT_RETURN", "EXPLAIN_GENERAL_PROCESS", "REFER_PAYMENTS_SPECIALIST", "DOCUMENT_CASE"],
    "ACCOUNT_FEES": ["REVIEW_ACCOUNT_FEES", "EXPLAIN_GENERAL_PROCESS", "DOCUMENT_CASE", "CONFIRM_NEXT_STEP"],
    "DIGITAL_ACCESS": ["VERIFY_IDENTITY", "SECURE_ACCOUNT", "RESTORE_DIGITAL_ACCESS", "REFER_FRAUD_SPECIALIST", "DOCUMENT_CASE"],
    "LOAN_SERVICE": ["REVIEW_LOAN_ACCOUNT", "PROVIDE_PAYOFF_QUOTE_PATH", "REFER_LENDING_SPECIALIST", "DOCUMENT_CASE"],
    "MEMBERSHIP": ["CLARIFY_REQUEST", "REVIEW_MEMBERSHIP_ELIGIBILITY", "EXPLAIN_GENERAL_PROCESS", "DOCUMENT_CASE"],
    "CLOSE_ROUTINE": ["DOCUMENT_CASE", "CONFIRM_NEXT_STEP", "CLOSE_INTERACTION"],
    "CLOSE_CARD": ["DOCUMENT_CASE", "CONFIRM_NEXT_STEP", "REFER_CARD_SPECIALIST", "CLOSE_INTERACTION"],
    "CLOSE_PAYMENTS": ["DOCUMENT_CASE", "CONFIRM_NEXT_STEP", "REFER_PAYMENTS_SPECIALIST", "CLOSE_INTERACTION"],
    "CLOSE_FRAUD": ["DOCUMENT_CASE", "CONFIRM_NEXT_STEP", "REFER_FRAUD_SPECIALIST", "CLOSE_INTERACTION"],
    "CLOSE_LENDING": ["DOCUMENT_CASE", "CONFIRM_NEXT_STEP", "REFER_LENDING_SPECIALIST", "CLOSE_INTERACTION"],
}


def scenario(
    sid, family, category, product, short_label, goal, summary, issues, details,
    status, authorization, risk, regulatory, policy, sources,
    investigate_action, investigate_mask, resolve_action, resolve_mask,
    amount_range=(10, 2500), intake_action=None, intake_mask=None, extra_prohibited=None,
):
    return {
        "scenario_id": sid,
        "scenario_family": family,
        "category": category,
        "product": product,
        "short_label": short_label,
        "member_goal": goal,
        "case_summary": summary,
        "issue_options": issues,
        "detail_options": details,
        "status_claim": status,
        "authorization_claim": authorization,
        "risk_tier": risk,
        "regulatory_flags": regulatory,
        "policy_dependency": policy,
        "source_keys": sources,
        "investigate_action": investigate_action,
        "investigate_mask": investigate_mask,
        "resolve_action": resolve_action,
        "resolve_mask": resolve_mask,
        "amount_range": amount_range,
        "intake_action": intake_action or ("SECURE_ACCOUNT" if risk == "high" else "VERIFY_IDENTITY"),
        "intake_mask": intake_mask or ("INTAKE_HIGH_RISK" if risk == "high" else "INTAKE_ROUTINE"),
        "extra_prohibited": extra_prohibited or [],
    }


SCENARIOS = [
    scenario("CU001", "card_balance_transfer_request", "cards", "credit_card", "balance-transfer request",
             "determine whether a balance transfer can be requested and what facts are needed",
             "Member wants to move an outside card balance to a credit-union card.",
             ["I want to move a balance from another card", "I am trying to consolidate an outside card balance", "I would like to request a balance transfer"],
             ["my outside account is open", "the requested amount may be close to my available credit", "I have not submitted the request yet"],
             "not_submitted", "authorized", "routine", ["reg_z_terms_review"], "card_agreement_and_offer_terms",
             ["REG_Z_DISCLOSURES"], "REVIEW_CARD_TERMS", "CARD_TERMS", "REFER_CARD_SPECIALIST", "CLOSE_CARD", (250, 12000)),
    scenario("CU002", "card_balance_transfer_pending", "cards", "credit_card", "pending balance transfer",
             "locate the transfer status and identify the correct servicing path",
             "Member submitted a balance transfer that has not posted as expected.",
             ["my balance transfer still has not posted", "a submitted balance transfer is showing as pending", "the other card has not received the balance-transfer payment"],
             ["I have a confirmation marker", "the source account still shows the old balance", "I submitted the transfer through digital banking"],
             "pending", "authorized", "elevated", ["reg_z_terms_review"], "card_servicing_status_and_offer_terms",
             ["REG_Z_DISCLOSURES"], "CHECK_TRANSACTION_STATUS", "PAYMENT_STATUS", "REFER_CARD_SPECIALIST", "CLOSE_CARD", (250, 12000)),
    scenario("CU003", "card_balance_transfer_terms", "cards", "credit_card", "balance-transfer terms",
             "understand the applicable fee, APR, promotion, and eligible amount without assuming terms",
             "Member asks how a balance-transfer offer applies to their account.",
             ["I need to understand the balance-transfer fee and rate", "I am comparing the balance-transfer promotion with my regular APR", "I want to know which terms apply before I transfer a balance"],
             ["I may have a targeted offer", "purchase and transfer rates may differ", "I want the applicable agreement rather than a generic estimate"],
             "information_request", "authorized", "routine", ["reg_z_terms_review"], "card_agreement_and_offer_terms",
             ["REG_Z_DISCLOSURES"], "REVIEW_CARD_TERMS", "CARD_TERMS", "CONFIRM_NEXT_STEP", "CLOSE_ROUTINE", (250, 12000)),
    scenario("CU004", "zelle_pending_recipient_unenrolled", "p2p_payments", "zelle", "unenrolled-recipient Zelle payment",
             "determine whether recipient enrollment explains the pending status",
             "Member sent a Zelle payment to a recipient who may not be enrolled.",
             ["my Zelle payment says pending and the recipient has not received it", "the person I paid may not be enrolled with Zelle", "a Zelle payment is waiting on the recipient"],
             ["the recipient used a different contact point", "the recipient has not completed enrollment", "I still see a pending status rather than completed"],
             "pending", "authorized", "routine", ["p2p_status_review"], "zelle_and_institution_status_rules",
             ["ZELLE_ENROLLMENT"], "CHECK_RECIPIENT_ENROLLMENT", "ZELLE_PENDING", "CONFIRM_NEXT_STEP", "CLOSE_PAYMENTS", (5, 2500)),
    scenario("CU005", "zelle_security_review", "p2p_payments", "zelle", "Zelle security review",
             "identify the authoritative status and route a security-review hold without promising release",
             "Member reports a Zelle payment delayed by an institution security review.",
             ["my Zelle transfer appears to be under review", "a Zelle payment is delayed by a security check", "the app shows a review message for my Zelle payment"],
             ["the recipient is already enrolled", "the payment has not completed", "I see a message that additional review may be required"],
             "security_review", "authorized", "elevated", ["p2p_status_review"], "institution_fraud_and_payment_controls",
             ["REG_E_ERROR", "NCUA_CAC"], "CHECK_TRANSACTION_STATUS", "PAYMENT_STATUS", "REFER_PAYMENTS_SPECIALIST", "CLOSE_PAYMENTS", (5, 2500), extra_prohibited=["BYPASS_SECURITY_CONTROLS"]),
    scenario("CU006", "zelle_recipient_nonreceipt", "p2p_payments", "zelle", "Zelle recipient nonreceipt",
             "compare sender status, recipient enrollment, and destination details before tracing",
             "Member says a completed or sent Zelle payment was not received.",
             ["the recipient says my Zelle payment never arrived", "my Zelle history shows activity but the other person sees nothing", "I need help locating a Zelle payment the recipient cannot find"],
             ["I recognize the intended recipient", "the payment contact point needs confirmation", "my status and the recipient's status may not match"],
             "recipient_nonreceipt", "authorized", "elevated", ["reg_e_review_possible", "p2p_status_review"], "zelle_and_institution_status_rules",
             ["REG_E_ERROR", "ZELLE_ENROLLMENT"], "TRACE_PAYMENT", "PAYMENT_STATUS", "REFER_PAYMENTS_SPECIALIST", "CLOSE_PAYMENTS", (5, 2500)),
    scenario("CU007", "zelle_authorized_scam_report", "fraud", "zelle", "authorized Zelle scam report",
             "capture the scam report, preserve the authorization distinction, and escalate",
             "Member says they personally sent a Zelle payment after being deceived.",
             ["I sent a Zelle payment and now believe the request was a scam", "I authorized the payment but the recipient deceived me", "I was tricked into sending money with Zelle"],
             ["I initiated the payment", "the recipient is now unreachable", "I want to know what review options exist"],
             "completed_or_pending", "authorized_under_deception", "high", ["fraud_review", "reg_e_classification_required"], "institution_scam_and_recovery_process",
             ["REG_E_ERROR", "NCUA_CAC"], "CLARIFY_REQUEST", "FRAUD_HIGH", "REFER_FRAUD_SPECIALIST", "CLOSE_FRAUD", (20, 5000),
             extra_prohibited=["MISCLASSIFY_AUTHORIZED_SCAM", "REVERSE_TRANSFER_WITHOUT_REVIEW"]),
    scenario("CU008", "zelle_unauthorized_transfer", "fraud", "zelle", "unauthorized Zelle transfer",
             "secure the account and initiate the approved unauthorized-EFT review",
             "Member denies initiating a Zelle transfer from the account.",
             ["there is a Zelle transfer I did not authorize", "I did not send the Zelle payment showing on my account", "someone appears to have used Zelle from my account"],
             ["I did not share access", "the transaction is unfamiliar to me", "my account credentials may be compromised"],
             "posted_or_pending", "unauthorized_claim", "high", ["reg_e_error_possible", "reg_e_liability_review", "fraud_review"], "reg_e_and_institution_fraud_process",
             ["REG_E_ERROR", "REG_E_LIABILITY", "IDENTITY_THEFT"], "START_EFT_ERROR_INTAKE", "FRAUD_HIGH", "REFER_FRAUD_SPECIALIST", "CLOSE_FRAUD", (20, 5000)),
    scenario("CU009", "ach_direct_deposit_missing", "ach", "checking", "missing direct deposit",
             "verify whether an expected ACH credit was received, pending, returned, or never originated",
             "Member expected a payroll or benefit direct deposit that is not visible.",
             ["my expected direct deposit is missing", "a payroll deposit has not appeared", "I cannot see the ACH credit I expected"],
             ["the originator says it was sent", "the expected date has passed", "I can identify the deposit type without sharing sensitive data"],
             "missing", "not_applicable", "elevated", ["reg_e_information_request_possible"], "ach_status_and_originator_records",
             ["ACH_BASICS", "REG_E_ERROR"], "CHECK_TRANSACTION_STATUS", "PAYMENT_STATUS", "TRACE_PAYMENT", "PAYMENT_STATUS", (50, 6000)),
    scenario("CU010", "ach_debit_unrecognized", "fraud", "checking", "unrecognized ACH debit",
             "secure the account as needed and capture an alleged unauthorized or incorrect EFT",
             "Member does not recognize an ACH debit on the account.",
             ["I do not recognize an ACH withdrawal", "an unfamiliar electronic debit posted to my checking account", "there is an ACH charge I did not approve"],
             ["the company descriptor is unfamiliar to me", "I did not set up the debit", "the transaction may recur"],
             "posted", "unauthorized_claim", "high", ["reg_e_error_possible", "reg_e_liability_review", "fraud_review"], "reg_e_and_institution_fraud_process",
             ["ACH_BASICS", "REG_E_ERROR", "REG_E_LIABILITY"], "START_EFT_ERROR_INTAKE", "FRAUD_HIGH", "REFER_FRAUD_SPECIALIST", "CLOSE_FRAUD", (5, 3500)),
    scenario("CU011", "ach_transfer_returned", "ach", "checking", "returned ACH transfer",
             "identify the return status and route the member to the correct corrective action",
             "Member's ACH transfer was returned or reversed.",
             ["my ACH transfer was returned", "an electronic transfer reversed after appearing to post", "I need to understand why an ACH payment came back"],
             ["the return reason is not yet clear to me", "my available funds may have changed", "the originator or receiver may need updated information"],
             "returned", "authorized", "routine", ["reg_e_information_request_possible"], "ach_return_code_and_account_policy",
             ["ACH_BASICS", "REG_E_ERROR"], "CHECK_TRANSACTION_STATUS", "PAYMENT_STATUS", "REFER_PAYMENTS_SPECIALIST", "CLOSE_PAYMENTS", (10, 5000)),
    scenario("CU012", "debit_card_declined", "cards", "debit_card", "declined debit card",
             "check card and account status without assuming the decline reason",
             "Member's debit card was declined at a merchant or ATM.",
             ["my debit card was declined", "a purchase would not go through on my debit card", "the ATM rejected my debit card transaction"],
             ["I still have the physical card", "I see no clear explanation", "card controls or my available balance may be relevant"],
             "declined", "authorized", "routine", [], "card_controls_network_and_account_status",
             ["REG_E_ERROR"], "CHECK_CARD_STATUS", "CARD_SERVICE", "CONFIRM_NEXT_STEP", "CLOSE_CARD", (5, 2000)),
    scenario("CU013", "debit_card_lost_or_stolen", "cards", "debit_card", "lost or stolen debit card",
             "secure access and block or replace the card through approved controls",
             "Member reports a lost or stolen debit card.",
             ["my debit card is missing", "I believe my debit card was stolen", "I cannot locate my debit card and need it secured"],
             ["I have not identified a disputed transaction yet", "the physical card is unavailable", "my digital-wallet access may also need review"],
             "access_device_missing", "unclear", "high", ["reg_e_review_if_unauthorized_use"], "card_security_and_replacement_policy",
             ["REG_E_ERROR", "REG_E_LIABILITY"], "BLOCK_OR_REPLACE_CARD", "FRAUD_HIGH", "CONFIRM_NEXT_STEP", "CLOSE_CARD", (0, 0)),
    scenario("CU014", "debit_card_transaction_dispute", "cards", "debit_card", "debit-card transaction dispute",
             "classify the transaction concern and start the appropriate dispute or EFT-error path",
             "Member disputes a debit-card purchase amount, duplicate, or merchant transaction.",
             ["I need to dispute a debit-card purchase", "a debit-card transaction posted with the wrong amount", "my account shows a duplicate debit-card charge"],
             ["I recognize the merchant", "the amount or duplication is the issue", "I see the transaction as posted rather than merely authorized"],
             "posted", "authorized_or_incorrect", "elevated", ["reg_e_error_possible"], "card_dispute_and_reg_e_process",
             ["REG_E_ERROR"], "START_CARD_DISPUTE", "CARD_SERVICE", "REFER_CARD_SPECIALIST", "CLOSE_CARD", (5, 3500)),
    scenario("CU015", "atm_cash_dispense_error", "atm", "checking", "ATM cash error",
             "capture an EFT error involving cash dispensed, cash not received, or an incorrect amount",
             "Member reports an ATM debit with no cash or the wrong cash amount.",
             ["the ATM debited me but did not give me cash", "the ATM gave me less cash than the account debit", "I have an ATM cash-dispense error"],
             ["I can identify the terminal location", "the debit appears on my account", "I retained the available receipt"],
             "posted_or_pending", "authorized_but_incorrect", "elevated", ["reg_e_error_possible"], "reg_e_atm_error_process",
             ["REG_E_ERROR"], "START_EFT_ERROR_INTAKE", "EFT_ERROR", "REFER_PAYMENTS_SPECIALIST", "CLOSE_PAYMENTS", (20, 1000)),
    scenario("CU016", "mobile_banking_lockout", "digital_access", "online_banking", "mobile-banking lockout",
             "restore access through approved verification and device-security steps",
             "Member cannot access mobile or online banking.",
             ["I am locked out of mobile banking", "online banking will not accept my login", "I cannot get past the digital-banking security check"],
             ["I still control the enrolled contact channel", "my device or password recently changed", "I understand account details require verification"],
             "access_blocked", "not_applicable", "elevated", ["identity_verification_required"], "digital_access_and_identity_policy",
             ["IDENTITY_THEFT"], "RESTORE_DIGITAL_ACCESS", "DIGITAL_ACCESS", "CONFIRM_NEXT_STEP", "CLOSE_ROUTINE", None),
    scenario("CU017", "account_takeover_suspected", "fraud", "deposit_account", "suspected account takeover",
             "contain access, preserve evidence, and escalate with high priority",
             "Member reports password, profile, device, or transaction changes they did not make.",
             ["someone may have taken over my account", "my login details changed without my permission", "I see profile or device activity I did not initiate"],
             ["I see an unknown device", "my contact details may have changed", "unrecognized transactions may also be present"],
             "security_event", "unauthorized_claim", "high", ["fraud_review", "reg_e_review_if_eft"], "account_security_and_reg_e_process",
             ["IDENTITY_THEFT", "REG_E_ERROR", "REG_E_LIABILITY"], "SECURE_ACCOUNT", "FRAUD_HIGH", "REFER_FRAUD_SPECIALIST", "CLOSE_FRAUD", None,
             extra_prohibited=["IGNORE_IDENTITY_WARNING"]),
    scenario("CU018", "check_deposit_hold", "deposits", "checking", "check-deposit hold",
             "review the deposit, hold notice, availability date, and applicable exception",
             "Member asks why deposited check funds are not yet available.",
             ["my deposited check is on hold", "the funds from my check deposit are not available", "I need to understand the availability date on a check deposit"],
             ["I can identify the deposit channel", "I may have a hold notice", "the deposit type and my account history may affect availability"],
             "held", "authorized", "routine", ["reg_cc_review"], "deposit_type_hold_notice_and_exception_policy",
             ["REG_CC_GUIDE"], "REVIEW_DEPOSIT_HOLD", "DEPOSIT", "CONFIRM_NEXT_STEP", "CLOSE_PAYMENTS", (25, 15000),
             extra_prohibited=["GUARANTEE_OUTCOME_OR_TIMING"]),
    scenario("CU019", "check_deposit_returned", "deposits", "checking", "returned check deposit",
             "review the return reason, adjustment, notice, and safe next step",
             "Member's deposited check was returned or reversed.",
             ["a check I deposited was returned", "my check deposit was reversed", "the deposited-check credit disappeared from my account"],
             ["the return reason needs authoritative review", "I may have used some provisionally available funds", "I may have a deposited-item notice"],
             "returned", "authorized", "elevated", ["reg_cc_review"], "deposit_return_and_adjustment_policy",
             ["REG_CC_GUIDE"], "REVIEW_DEPOSIT_RETURN", "DEPOSIT", "REFER_PAYMENTS_SPECIALIST", "CLOSE_PAYMENTS", (25, 15000)),
    scenario("CU020", "overdraft_or_nsf_fee", "fees", "checking", "overdraft or NSF fee",
             "identify the fee, related transaction, and applicable institution policy",
             "Member questions an overdraft or nonsufficient-funds fee.",
             ["I have a question about an overdraft fee", "an NSF fee posted and I do not understand why", "I want the transactions behind this account fee reviewed"],
             ["I can identify the related item", "my pending and posted balances may differ", "I understand any adjustment depends on approved policy"],
             "fee_posted", "authorized_or_not_applicable", "routine", ["institution_fee_policy_review"], "account_agreement_and_fee_adjustment_policy",
             ["NCUA_CAC"], "REVIEW_ACCOUNT_FEES", "ACCOUNT_FEES", "CONFIRM_NEXT_STEP", "CLOSE_ROUTINE", (5, 150)),
    scenario("CU021", "bill_pay_payment_missing", "bill_pay", "checking", "missing bill-pay payment",
             "trace a scheduled payment and distinguish debit status from payee receipt",
             "Member says a bill-pay item was scheduled or debited but the payee did not receive it.",
             ["the payee says my bill payment never arrived", "a scheduled bill-pay item is missing", "my account shows bill-pay activity but the company has no payment"],
             ["the payment may have been electronic or check-based", "I can see the account debit status", "the payee details need confirmation"],
             "payee_nonreceipt", "authorized", "elevated", ["reg_e_information_request_possible"], "bill_pay_rail_status_and_trace_policy",
             ["REG_E_ERROR", "ACH_BASICS"], "TRACE_PAYMENT", "PAYMENT_STATUS", "REFER_PAYMENTS_SPECIALIST", "CLOSE_PAYMENTS", (10, 5000)),
    scenario("CU022", "wire_transfer_status_or_recall", "wires", "deposit_account", "wire status or recall",
             "verify wire status and route any recall request without promising recovery",
             "Member requests the status of a wire or asks whether a sent wire can be recalled.",
             ["I need the status of a wire transfer", "I want to ask whether a sent wire can be recalled", "the recipient has not confirmed receipt of my wire"],
             ["I authorized the wire", "the receiving institution details need confirmation", "I understand recall availability depends on status and wire policy"],
             "sent_or_pending", "authorized", "elevated", ["wire_policy_review"], "wire_status_recall_and_cutoff_policy",
             ["NCUA_CAC"], "CHECK_TRANSACTION_STATUS", "PAYMENT_STATUS", "REFER_PAYMENTS_SPECIALIST", "CLOSE_PAYMENTS", (250, 25000),
             extra_prohibited=["REVERSE_TRANSFER_WITHOUT_REVIEW", "GUARANTEE_OUTCOME_OR_TIMING"]),
    scenario("CU023", "loan_payment_posting", "loans", "consumer_loan", "loan-payment posting",
             "review the loan ledger, payment channel, posting date, and due-date impact",
             "Member says a loan payment is missing, late, duplicated, or posted unexpectedly.",
             ["my loan payment has not posted", "a loan payment posted on an unexpected date", "I need a recent loan payment reviewed"],
             ["I can identify the payment channel", "I have an expected effective date", "late-fee or due-date impact may require servicing review"],
             "missing_or_misposted", "authorized", "routine", ["loan_servicing_policy_review"], "loan_agreement_and_servicing_ledger",
             ["NCUA_CAC"], "REVIEW_LOAN_ACCOUNT", "LOAN_SERVICE", "REFER_LENDING_SPECIALIST", "CLOSE_LENDING", (25, 5000)),
    scenario("CU024", "loan_payoff_quote", "loans", "consumer_loan", "loan payoff quote",
             "initiate an official payoff quote for the requested date and delivery method",
             "Member wants the amount and process to pay a loan in full.",
             ["I need a payoff quote for my loan", "I want to know the official amount to pay the loan in full", "please help me request a dated loan payoff"],
             ["I have an intended payoff date", "the delivery method needs confirmation", "I understand the current principal balance may differ from the payoff amount"],
             "information_request", "authorized", "routine", ["loan_servicing_policy_review"], "loan_agreement_and_payoff_process",
             ["NCUA_CAC"], "PROVIDE_PAYOFF_QUOTE_PATH", "LOAN_SERVICE", "CONFIRM_NEXT_STEP", "CLOSE_LENDING", (1000, 45000)),
    scenario("CU025", "membership_account_opening_eligibility", "membership", "membership", "membership eligibility",
             "apply the credit union's field-of-membership and account-opening criteria",
             "Prospective member asks whether they are eligible to join and open an account.",
             ["I want to know whether I am eligible to join the credit union", "I am trying to understand the membership requirements", "I would like to open an account and need the eligibility steps"],
             ["my eligibility may depend on geography, employer, association, or family relationship", "I have not submitted an application", "I understand identity and account-opening checks occur after eligibility review"],
             "pre_application", "not_applicable", "routine", ["membership_policy_review"], "field_of_membership_and_account_opening_policy",
             ["NCUA_CAC"], "REVIEW_MEMBERSHIP_ELIGIBILITY", "MEMBERSHIP", "CONFIRM_NEXT_STEP", "CLOSE_ROUTINE", None,
             intake_action="CLARIFY_REQUEST", intake_mask="MEMBERSHIP", extra_prohibited=["MAKE_ELIGIBILITY_DECISION_WITHOUT_POLICY"]),
]


TEMPLATES = {
    "train": {
        0: [
            "I'm calling {business_context_phrase} because {issue}. This came up {time_context}. I need help to {goal}. A useful detail is that {detail}. {urgency_sentence}",
            "I need some help: {issue}. This came up {time_context}. My goal is to {goal}; {detail}. {urgency_sentence}",
            "Can you look into this for me? {issue_cap}; this came up {time_context}. I want to {goal}. I am reaching out {business_context_phrase}, and {detail}.",
            "Here's what brought me in {business_context_phrase}: {issue}. This came up {time_context}. Please help me {goal}. For context, {detail}. {urgency_sentence}",
            "I'm trying to sort out a credit-union issue. {issue_cap}; this came up {time_context}, and I need to {goal}. I called {business_context_phrase}; {detail}.",
        ],
        1: [
            "{amount_fact}. It happened {age_phrase}. The useful detail is that {detail}.",
            "For context, {amount_fact_lower}; the event was {age_phrase}, and {detail}.",
            "The timing was {age_phrase}. {amount_fact} and {detail}.",
            "What I can confirm is this: {amount_fact_lower}, it was {age_phrase}, and {detail}.",
            "The main facts are that {detail}; {amount_fact_lower}; and it occurred {age_phrase}.",
        ],
        2: [
            "For this {short_label} involving {amount_short} from {age_phrase}, what is the safe next step and who owns it? {urgency_sentence}",
            "What should happen next when {issue}, with the event occurring {age_phrase}, given that {detail}, and what outcome should not be promised yet?",
            "Please confirm the next approved action for the {short_label} from {age_phrase}, involving {amount_short}, and what still depends on policy review.",
            "Given that {detail} and the event was {age_phrase}, which team or process should take the next step? I reached out {business_context_phrase}.",
            "Before we finish, what action is appropriate when {issue}, with {amount_short} involved, and what expectation can be confirmed?",
        ],
    },
    "validation": {
        0: [
            "Could you help with this situation {business_context_phrase}: {issue}? It came up {time_context}, and I want to {goal}. Also, {detail}.",
            "The reason for my call {business_context_phrase} is that {issue}. This came up {time_context}. I am looking to {goal}; {detail}. {urgency_sentence}",
            "I have a service question because {issue}. This came up {time_context}. Can we {goal}? For context, {detail}. {urgency_sentence}",
        ],
        1: [
            "Here are the facts I have: {amount_fact_lower}; the event was {age_phrase}; and {detail}.",
            "The event occurred {age_phrase}. Also, {detail}, and {amount_fact_lower}.",
            "To narrow it down, {detail}. {amount_fact} and the timing was {age_phrase}.",
        ],
        2: [
            "For the {short_label} from {age_phrase}, involving {amount_short}, which approved path fits these facts and what needs specialist review?",
            "What is the appropriate handoff or next action when {issue}, involving {amount_short}, given that {detail}?",
            "How should this {short_label} from {age_phrase}, where {detail}, be documented and advanced without guaranteeing the result?",
        ],
    },
    "test": {
        0: [
            "I am contacting the credit union {business_context_phrase} because {issue}. This came up {time_context}; please help me {goal}. A key detail is that {detail}. {urgency_sentence}",
            "This is about {short_label}: {issue}. This came up {time_context}. I need to {goal}. I called {business_context_phrase}, and {detail}.",
            "My current problem is that {issue}. It started {time_context}, and I want to {goal}. For context, {detail}. {urgency_sentence}",
        ],
        1: [
            "The case details are: {amount_fact_lower}; {detail}; timing, {age_phrase}.",
            "I can add that {detail}. The event was {age_phrase}, and {amount_fact_lower}.",
            "A relevant detail is that {detail}; the timing is {age_phrase}; {amount_fact_lower}.",
        ],
        2: [
            "Which action objective is safest for this {short_label} from {age_phrase}, involving {amount_short}, given that {detail}?",
            "When {issue}, with the event occurring {age_phrase}, what should be done next without assuming a fee, deadline, or outcome? {urgency_sentence}",
            "What is the correct next-step category for the {short_label} involving {amount_short}, where {detail}, after contact {business_context_phrase}?",
        ],
    },
}


AGE_OPTIONS = [
    (1, "about an hour ago", "today"),
    (3, "earlier today", "today"),
    (8, "this morning", "today"),
    (20, "yesterday", "yesterday"),
    (36, "roughly a day and a half ago", "this week"),
    (72, "about three days ago", "this week"),
    (120, "about five days ago", "this week"),
    (240, "around ten days ago", "recently"),
    (480, "a few weeks ago", "recently"),
]

BUSINESS_CONTEXTS = ["weekday_business_hours", "weekday_after_hours", "weekend", "holiday_status_unknown"]
BUSINESS_CONTEXT_PHRASES = {
    "weekday_business_hours": "during regular business hours",
    "weekday_after_hours": "after regular business hours",
    "weekend": "over the weekend",
    "holiday_status_unknown": "around a possible holiday closure",
}
URGENCY_SENTENCES = {
    "routine": "It is not an emergency, but I need a clear next step.",
    "time_sensitive": "This is time-sensitive for me.",
    "immediate": "I need this secured or routed immediately.",
}
URGENCY_BY_RISK = {
    "routine": ["routine", "routine", "time_sensitive"],
    "elevated": ["time_sensitive", "time_sensitive", "routine", "immediate"],
    "high": ["immediate", "immediate", "time_sensitive"],
}
VALENCE_BY_RISK = {
    "routine": ["neutral", "neutral", "negative", "positive"],
    "elevated": ["negative", "negative", "neutral"],
    "high": ["negative"],
}
AROUSAL_BY_RISK = {
    "routine": ["low", "medium", "low"],
    "elevated": ["medium", "high", "medium"],
    "high": ["high", "high", "medium"],
}


def split_for_index(index: int) -> str:
    for name, upper in SPLIT_LIMITS:
        if index <= upper:
            return name
    raise ValueError(index)


def money_for(rng: random.Random, amount_range):
    if amount_range is None:
        return None
    low, high = amount_range
    if high == 0:
        return None
    value = round(rng.uniform(low, high), 2)
    return value


def format_money(value):
    if value is None:
        return "no transaction amount is involved"
    return f"the amount is ${value:,.2f}"


def candidate_rewards(mask_name: str, preferred: str, acceptable: list[str]):
    rewards = {}
    for action in MASKS[mask_name]:
        rewards[action] = 1.0 if action == preferred else (0.25 if action in acceptable else -1.0)
    return rewards


def stage_unsafe(stage: int, sc: dict):
    if stage == 0:
        codes = ["DISCLOSE_ACCOUNT_DATA_BEFORE_AUTH"]
        if sc["risk_tier"] == "high":
            codes += ["IGNORE_IDENTITY_WARNING", "BYPASS_SECURITY_CONTROLS"]
    elif stage == 1:
        codes = ["GUARANTEE_OUTCOME_OR_TIMING", "STATE_UNVERIFIED_POLICY"]
        if sc["risk_tier"] == "high":
            codes += ["BYPASS_SECURITY_CONTROLS", "PROMISE_CREDIT_OR_REFUND"]
    else:
        codes = ["GUARANTEE_OUTCOME_OR_TIMING", "PROMISE_CREDIT_OR_REFUND"]
    return sorted(set(codes + sc["extra_prohibited"]))


def stage_spec(stage: int, sc: dict):
    if stage == 0:
        preferred = sc["intake_action"]
        mask_name = sc["intake_mask"]
        phase = "authenticate_and_scope"
        acceptable = ["CLARIFY_REQUEST", "DOCUMENT_CASE"]
        if preferred == "CLARIFY_REQUEST":
            acceptable = ["EXPLAIN_GENERAL_PROCESS", "DOCUMENT_CASE"]
    elif stage == 1:
        preferred = sc["investigate_action"]
        mask_name = sc["investigate_mask"]
        phase = "investigate_and_classify"
        acceptable = ["DOCUMENT_CASE"]
        if "EXPLAIN_GENERAL_PROCESS" in MASKS[mask_name]:
            acceptable.append("EXPLAIN_GENERAL_PROCESS")
    else:
        preferred = sc["resolve_action"]
        mask_name = sc["resolve_mask"]
        phase = "resolve_or_escalate"
        acceptable = ["DOCUMENT_CASE", "CONFIRM_NEXT_STEP"]
        if preferred == "CONFIRM_NEXT_STEP":
            acceptable.append("CLOSE_INTERACTION")
    acceptable = sorted(set(a for a in acceptable if a in MASKS[mask_name] and a != preferred))
    return phase, preferred, mask_name, acceptable


def make_utterance(rng, split, stage, values):
    templates = TEMPLATES[split][stage]
    template_idx = rng.randrange(len(templates))
    text = templates[template_idx].format(**values)
    return re.sub(r"\s+", " ", text).strip(), f"{split}_stage{stage}_template{template_idx + 1}"


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_jsonl(path: Path, values: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for value in values:
            handle.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")


def build():
    rng = random.Random(SEED)
    episodes_by_split = defaultdict(list)
    decisions_by_split = defaultdict(list)
    scenario_rows = []

    for sc in SCENARIOS:
        scenario_rows.append({
            "scenario_id": sc["scenario_id"],
            "scenario_family": sc["scenario_family"],
            "category": sc["category"],
            "product": sc["product"],
            "member_goal": sc["member_goal"],
            "case_summary": sc["case_summary"],
            "risk_tier": sc["risk_tier"],
            "regulatory_flags": "|".join(sc["regulatory_flags"]),
            "policy_dependency": sc["policy_dependency"],
            "source_keys": "|".join(sc["source_keys"]),
            "intake_action": sc["intake_action"],
            "investigate_action": sc["investigate_action"],
            "resolve_action": sc["resolve_action"],
            "script_status": "DEFERRED_TO_NEXT_PHASE",
        })

        for local_index in range(1, EPISODES_PER_SCENARIO + 1):
            split = split_for_index(local_index)
            call_id = f"SYN-CU-{VERSION.replace('.', '')}-{sc['scenario_id']}-{local_index:03d}"
            amount = money_for(rng, sc["amount_range"])
            age_hours, age_phrase, time_context = rng.choice(AGE_OPTIONS)
            detail = rng.choice(sc["detail_options"])
            issue = rng.choice(sc["issue_options"])
            business_context = rng.choice(BUSINESS_CONTEXTS)
            urgency = rng.choice(URGENCY_BY_RISK[sc["risk_tier"]])
            difficulty = rng.choices(["standard", "ambiguous", "high_attention"], weights=[55, 30, 15], k=1)[0]
            amount_fact_lower = format_money(amount)
            amount_fact = amount_fact_lower[0].upper() + amount_fact_lower[1:]
            values = {
                "issue": issue,
                "issue_cap": issue[0].upper() + issue[1:],
                "goal": sc["member_goal"],
                "time_context": time_context,
                "business_context_phrase": BUSINESS_CONTEXT_PHRASES[business_context],
                "urgency_sentence": URGENCY_SENTENCES[urgency],
                "amount_fact": amount_fact,
                "amount_fact_lower": amount_fact_lower,
                "amount_short": f"${amount:,.2f}" if amount is not None else "no monetary transaction",
                "age_phrase": age_phrase,
                "detail": detail,
                "short_label": sc["short_label"],
            }
            case_facts = {
                "amount_usd": amount,
                "event_age_hours": age_hours,
                "business_day_context": business_context,
                "status_claim": sc["status_claim"],
                "authorization_claim": sc["authorization_claim"],
                "policy_dependency": sc["policy_dependency"],
                "member_supplied_detail": detail,
            }
            episode = {
                "dataset_version": VERSION,
                "call_id": call_id,
                "split": split,
                "synthetic": True,
                "language": "en-US",
                "scenario_id": sc["scenario_id"],
                "scenario_family": sc["scenario_family"],
                "category": sc["category"],
                "product": sc["product"],
                "difficulty": difficulty,
                "risk_tier": sc["risk_tier"],
                "member_goal": sc["member_goal"],
                "case_facts": case_facts,
                "regulatory_flags": sc["regulatory_flags"],
                "source_keys": sc["source_keys"],
                "turns": [],
            }

            for stage in range(3):
                phase, preferred, mask_name, acceptable = stage_spec(stage, sc)
                utterance, template_family_id = make_utterance(rng, split, stage, values)
                authentication_state = (
                    "not_required" if sc["scenario_id"] == "CU025" else
                    ("not_started" if stage == 0 else "verified")
                )
                valence = rng.choice(VALENCE_BY_RISK[sc["risk_tier"]])
                arousal = rng.choice(AROUSAL_BY_RISK[sc["risk_tier"]])
                decision_id = f"{call_id}-D{stage + 1}"
                unsafe = stage_unsafe(stage, sc)
                rewards = candidate_rewards(mask_name, preferred, acceptable)
                decision = {
                    "dataset_version": VERSION,
                    "decision_id": decision_id,
                    "call_id": call_id,
                    "split": split,
                    "turn_index": stage + 1,
                    "phase": phase,
                    "scenario_id": sc["scenario_id"],
                    "scenario_family": sc["scenario_family"],
                    "category": sc["category"],
                    "product": sc["product"],
                    "intent": sc["scenario_family"],
                    "member_utterance": utterance,
                    "utterance_hash": hashlib.sha256(utterance.encode("utf-8")).hexdigest()[:16],
                    "template_family_id": template_family_id,
                    "valence": valence,
                    "arousal": arousal,
                    "urgency": urgency,
                    "authentication_state": authentication_state,
                    "risk_tier": sc["risk_tier"],
                    "authorization_claim": sc["authorization_claim"],
                    "status_claim": sc["status_claim"],
                    "amount_usd": "" if amount is None else f"{amount:.2f}",
                    "event_age_hours": age_hours,
                    "business_day_context": business_context,
                    "regulatory_flags_json": json.dumps(sc["regulatory_flags"], separators=(",", ":")),
                    "case_facts_json": json.dumps(case_facts, separators=(",", ":"), ensure_ascii=False),
                    "action_mask_group": mask_name,
                    "candidate_actions_json": json.dumps(MASKS[mask_name], separators=(",", ":")),
                    "preferred_action_family": preferred,
                    "acceptable_action_families_json": json.dumps(acceptable, separators=(",", ":")),
                    "prohibited_behaviors_json": json.dumps(unsafe, separators=(",", ":")),
                    "candidate_rewards_json": json.dumps(rewards, separators=(",", ":"), sort_keys=True),
                    "reward_preferred": "1.00",
                    "reward_acceptable": "0.25",
                    "reward_wrong": "-1.00",
                    "reward_prohibited": "-3.00",
                    "script_text_status": "NOT_INCLUDED",
                }
                decisions_by_split[split].append(decision)
                episode["turns"].append({
                    "turn_index": stage + 1,
                    "role": "member",
                    "phase": phase,
                    "text": utterance,
                    "observation": {
                        "intent": sc["scenario_family"],
                        "valence": valence,
                        "arousal": arousal,
                        "urgency": urgency,
                        "authentication_state": authentication_state,
                        "risk_tier": sc["risk_tier"],
                    },
                    "target": {
                        "action_mask_group": mask_name,
                        "candidate_actions": MASKS[mask_name],
                        "preferred_action_family": preferred,
                        "acceptable_action_families": acceptable,
                        "prohibited_behaviors": unsafe,
                    },
                })
            episodes_by_split[split].append(episode)

    decision_fields = [
        "dataset_version", "decision_id", "call_id", "split", "turn_index", "phase",
        "scenario_id", "scenario_family", "category", "product", "intent", "member_utterance",
        "utterance_hash", "template_family_id", "valence", "arousal", "urgency",
        "authentication_state", "risk_tier", "authorization_claim", "status_claim", "amount_usd",
        "event_age_hours", "business_day_context", "regulatory_flags_json", "case_facts_json",
        "action_mask_group", "candidate_actions_json", "preferred_action_family",
        "acceptable_action_families_json", "prohibited_behaviors_json", "candidate_rewards_json",
        "reward_preferred", "reward_acceptable", "reward_wrong", "reward_prohibited", "script_text_status",
    ]
    scenario_fields = [
        "scenario_id", "scenario_family", "category", "product", "member_goal", "case_summary",
        "risk_tier", "regulatory_flags", "policy_dependency", "source_keys", "intake_action",
        "investigate_action", "resolve_action", "script_status",
    ]

    for split in ("train", "validation", "test"):
        write_jsonl(DATA_DIR / f"episodes_{split}.jsonl", episodes_by_split[split])
        write_csv(DATA_DIR / f"decision_points_{split}.csv", decisions_by_split[split], decision_fields)
    sample_fields = [
        "decision_id", "split", "turn_index", "phase", "scenario_id", "scenario_family",
        "product", "member_utterance", "valence", "arousal", "urgency",
        "authentication_state", "risk_tier", "preferred_action_family", "action_mask_group",
        "acceptable_action_families_json", "prohibited_behaviors_json", "script_text_status",
    ]
    representative_sample = []
    for sc in SCENARIOS:
        representative_sample.extend([
            row for row in decisions_by_split["train"]
            if row["scenario_id"] == sc["scenario_id"]
        ][:3])
    write_csv(DATA_DIR / "decision_sample.csv", representative_sample, sample_fields)
    write_csv(DATA_DIR / "scenario_catalog.csv", scenario_rows, scenario_fields)
    write_csv(DATA_DIR / "action_catalog.csv", [
        {"action_family": code, "description": description, "contains_script_text": "no"}
        for code, description in ACTIONS
    ], ["action_family", "description", "contains_script_text"])
    write_csv(DATA_DIR / "prohibited_behavior_catalog.csv", [
        {"behavior_code": code, "description": description}
        for code, description in PROHIBITED
    ], ["behavior_code", "description"])
    write_csv(DATA_DIR / "source_registry.csv", [
        {"source_key": key, **value, "accessed": RELEASE_DATE}
        for key, value in SOURCES.items()
    ], ["source_key", "title", "url", "use", "accessed"])

    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://example.invalid/callcenterfly/synthetic-credit-union-call.schema.json",
        "title": "CallCenterFly Synthetic Credit-Union Call Episode",
        "description": "Synthetic member-only call episode with abstract action targets; no agent scripts.",
        "type": "object",
        "required": ["dataset_version", "call_id", "split", "synthetic", "scenario_id", "turns"],
        "properties": {
            "dataset_version": {"const": VERSION},
            "call_id": {"type": "string", "pattern": "^SYN-CU-"},
            "split": {"enum": ["train", "validation", "test"]},
            "synthetic": {"const": True},
            "language": {"const": "en-US"},
            "scenario_id": {"type": "string"},
            "scenario_family": {"type": "string"},
            "category": {"type": "string"},
            "product": {"type": "string"},
            "difficulty": {"enum": ["standard", "ambiguous", "high_attention"]},
            "risk_tier": {"enum": ["routine", "elevated", "high"]},
            "member_goal": {"type": "string"},
            "case_facts": {"type": "object"},
            "regulatory_flags": {"type": "array", "items": {"type": "string"}},
            "source_keys": {"type": "array", "items": {"type": "string"}},
            "turns": {
                "type": "array", "minItems": 3, "maxItems": 3,
                "items": {
                    "type": "object",
                    "required": ["turn_index", "role", "phase", "text", "observation", "target"],
                    "properties": {
                        "role": {"const": "member"},
                        "text": {"type": "string"},
                        "target": {"type": "object"},
                    },
                },
            },
        },
    }
    write_json(DOCS_DIR / "episode_schema.json", schema)

    all_decisions = sum((decisions_by_split[s] for s in ("train", "validation", "test")), [])
    all_episodes = sum((episodes_by_split[s] for s in ("train", "validation", "test")), [])
    template_sets = {
        split: {d["template_family_id"] for d in decisions_by_split[split]}
        for split in ("train", "validation", "test")
    }
    utterance_sets = {
        split: {d["member_utterance"] for d in decisions_by_split[split]}
        for split in ("train", "validation", "test")
    }
    pii_patterns = {
        "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        "us_phone": re.compile(r"\b(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}\b"),
        "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        "long_account_number": re.compile(r"\b\d{12,19}\b"),
    }
    pii_hits = []
    for row in all_decisions:
        for label, pattern in pii_patterns.items():
            if pattern.search(row["member_utterance"]):
                pii_hits.append({"decision_id": row["decision_id"], "pattern": label})
    duplicates = len(all_decisions) - len({d["member_utterance"] for d in all_decisions})
    preferred_outside_mask = [
        d["decision_id"] for d in all_decisions
        if d["preferred_action_family"] not in json.loads(d["candidate_actions_json"])
    ]
    exact_split_counts = {
        split: Counter(e["scenario_id"] for e in episodes_by_split[split])
        for split in ("train", "validation", "test")
    }
    expected_per_scenario = {"train": 70, "validation": 15, "test": 15}
    balance_failures = []
    for split, counts in exact_split_counts.items():
        for sc in SCENARIOS:
            if counts[sc["scenario_id"]] != expected_per_scenario[split]:
                balance_failures.append({
                    "split": split, "scenario_id": sc["scenario_id"],
                    "actual": counts[sc["scenario_id"]], "expected": expected_per_scenario[split],
                })
    qa = {
        "dataset_version": VERSION,
        "seed": SEED,
        "scenario_count": len(SCENARIOS),
        "episode_count": len(all_episodes),
        "decision_count": len(all_decisions),
        "episodes_by_split": {split: len(episodes_by_split[split]) for split in ("train", "validation", "test")},
        "decisions_by_split": {split: len(decisions_by_split[split]) for split in ("train", "validation", "test")},
        "exact_scenario_balance": not balance_failures,
        "scenario_balance_failures": balance_failures,
        "template_family_overlap": {
            "train_validation": sorted(template_sets["train"] & template_sets["validation"]),
            "train_test": sorted(template_sets["train"] & template_sets["test"]),
            "validation_test": sorted(template_sets["validation"] & template_sets["test"]),
        },
        "exact_utterance_overlap": {
            "train_validation": len(utterance_sets["train"] & utterance_sets["validation"]),
            "train_test": len(utterance_sets["train"] & utterance_sets["test"]),
            "validation_test": len(utterance_sets["validation"] & utterance_sets["test"]),
        },
        "pii_pattern_hits": pii_hits,
        "preferred_action_outside_mask": preferred_outside_mask,
        "duplicate_utterance_count": duplicates,
        "duplicate_utterance_rate": round(duplicates / len(all_decisions), 6),
        "script_text_rows": sum(d["script_text_status"] != "NOT_INCLUDED" for d in all_decisions),
        "checks_passed": (
            not balance_failures and not pii_hits and not preferred_outside_mask and
            duplicates / len(all_decisions) <= 0.05 and
            not any([
                template_sets["train"] & template_sets["validation"],
                template_sets["train"] & template_sets["test"],
                template_sets["validation"] & template_sets["test"],
            ]) and not any(qa_overlap for qa_overlap in [
                utterance_sets["train"] & utterance_sets["validation"],
                utterance_sets["train"] & utterance_sets["test"],
                utterance_sets["validation"] & utterance_sets["test"],
            ]) and all(d["script_text_status"] == "NOT_INCLUDED" for d in all_decisions)
        ),
    }
    write_json(QA_DIR / "qa_report.json", qa)
    qa_summary_rows = [
        {"check": "scenario_count", "observed": len(SCENARIOS), "expected": 25, "status": "PASS" if len(SCENARIOS) == 25 else "FAIL"},
        {"check": "episode_count", "observed": len(all_episodes), "expected": 2500, "status": "PASS" if len(all_episodes) == 2500 else "FAIL"},
        {"check": "decision_count", "observed": len(all_decisions), "expected": 7500, "status": "PASS" if len(all_decisions) == 7500 else "FAIL"},
        {"check": "scenario_balance_failures", "observed": len(balance_failures), "expected": 0, "status": "PASS" if not balance_failures else "FAIL"},
        {"check": "pii_pattern_hits", "observed": len(pii_hits), "expected": 0, "status": "PASS" if not pii_hits else "FAIL"},
        {"check": "preferred_actions_outside_mask", "observed": len(preferred_outside_mask), "expected": 0, "status": "PASS" if not preferred_outside_mask else "FAIL"},
        {"check": "split_template_overlaps", "observed": sum(len(v) for v in qa["template_family_overlap"].values()), "expected": 0, "status": "PASS" if not any(qa["template_family_overlap"].values()) else "FAIL"},
        {"check": "exact_utterance_cross_split_overlaps", "observed": sum(qa["exact_utterance_overlap"].values()), "expected": 0, "status": "PASS" if not any(qa["exact_utterance_overlap"].values()) else "FAIL"},
        {"check": "exact_duplicate_utterance_rate", "observed": qa["duplicate_utterance_rate"], "expected": "<=0.05", "status": "PASS" if qa["duplicate_utterance_rate"] <= 0.05 else "FAIL"},
        {"check": "script_text_rows", "observed": qa["script_text_rows"], "expected": 0, "status": "PASS" if qa["script_text_rows"] == 0 else "FAIL"},
        {"check": "all_release_checks", "observed": str(qa["checks_passed"]).lower(), "expected": "true", "status": "PASS" if qa["checks_passed"] else "FAIL"},
    ]
    write_csv(QA_DIR / "qa_summary.csv", qa_summary_rows, ["check", "observed", "expected", "status"])
    scenario_distribution_rows = []
    for sc in SCENARIOS:
        sid = sc["scenario_id"]
        scenario_distribution_rows.append({
            "scenario_id": sid,
            "scenario_family": sc["scenario_family"],
            "train_episodes": exact_split_counts["train"][sid],
            "validation_episodes": exact_split_counts["validation"][sid],
            "test_episodes": exact_split_counts["test"][sid],
            "total_episodes": sum(exact_split_counts[split][sid] for split in ("train", "validation", "test")),
            "total_decisions": sum(1 for row in all_decisions if row["scenario_id"] == sid),
        })
    write_csv(QA_DIR / "scenario_distribution.csv", scenario_distribution_rows, [
        "scenario_id", "scenario_family", "train_episodes", "validation_episodes",
        "test_episodes", "total_episodes", "total_decisions",
    ])
    action_distribution_rows = []
    for action, _ in ACTIONS:
        action_distribution_rows.append({
            "action_family": action,
            "train_preferred_count": sum(row["preferred_action_family"] == action for row in decisions_by_split["train"]),
            "validation_preferred_count": sum(row["preferred_action_family"] == action for row in decisions_by_split["validation"]),
            "test_preferred_count": sum(row["preferred_action_family"] == action for row in decisions_by_split["test"]),
            "total_preferred_count": sum(row["preferred_action_family"] == action for row in all_decisions),
        })
    write_csv(QA_DIR / "action_distribution.csv", action_distribution_rows, [
        "action_family", "train_preferred_count", "validation_preferred_count",
        "test_preferred_count", "total_preferred_count",
    ])

    data_dictionary = [
        ("call_id", "Opaque synthetic episode identifier; never a member or account identifier."),
        ("split", "Fixed train, validation, or test assignment."),
        ("phase", "Decision phase: authenticate_and_scope, investigate_and_classify, or resolve_or_escalate."),
        ("scenario_family", "Stable real-world issue taxonomy used as intent."),
        ("member_utterance", "Generated English member utterance; never copied from a real call."),
        ("valence", "Coarse affect label: positive, neutral, or negative."),
        ("urgency", "Routine, time_sensitive, or immediate triage label."),
        ("authentication_state", "Whether identity verification is not started, verified, or not required."),
        ("authorization_claim", "Member's claim about transaction authorization; not a final legal finding."),
        ("regulatory_flags_json", "Potential review flags. These do not determine legal coverage or outcome."),
        ("action_mask_group", "Contextual group of selectable abstract actions."),
        ("preferred_action_family", "Gold abstract action objective for the decision point."),
        ("acceptable_action_families_json", "Non-preferred but reasonable actions receiving partial reward."),
        ("prohibited_behaviors_json", "Unsafe or noncompliant behaviors excluded from selection."),
        ("candidate_rewards_json", "Per-candidate rewards: preferred 1.0, acceptable 0.25, other allowed -1.0."),
        ("script_text_status", "Always NOT_INCLUDED in v0.1; wording is intentionally deferred."),
    ]
    write_csv(DOCS_DIR / "data_dictionary.csv", [
        {"field": field, "definition": definition} for field, definition in data_dictionary
    ], ["field", "definition"])

    index_rows = [
        {"path": "data/decision_points_train.csv", "format": "CSV", "record_count": len(decisions_by_split["train"]), "primary_use": "Contextual-bandit or supervised training rows"},
        {"path": "data/decision_points_validation.csv", "format": "CSV", "record_count": len(decisions_by_split["validation"]), "primary_use": "Model selection and threshold tuning"},
        {"path": "data/decision_points_test.csv", "format": "CSV", "record_count": len(decisions_by_split["test"]), "primary_use": "Held-out evaluation"},
        {"path": "data/decision_sample.csv", "format": "CSV", "record_count": len(representative_sample), "primary_use": "Fast human review; one complete episode per scenario"},
        {"path": "data/episodes_train.jsonl", "format": "JSONL", "record_count": len(episodes_by_split["train"]), "primary_use": "Sequential three-decision training episodes"},
        {"path": "data/episodes_validation.jsonl", "format": "JSONL", "record_count": len(episodes_by_split["validation"]), "primary_use": "Sequential validation episodes"},
        {"path": "data/episodes_test.jsonl", "format": "JSONL", "record_count": len(episodes_by_split["test"]), "primary_use": "Sequential held-out episodes"},
        {"path": "data/scenario_catalog.csv", "format": "CSV", "record_count": len(SCENARIOS), "primary_use": "Scenario taxonomy and policy dependencies"},
        {"path": "data/action_catalog.csv", "format": "CSV", "record_count": len(ACTIONS), "primary_use": "Abstract selectable action definitions"},
        {"path": "data/prohibited_behavior_catalog.csv", "format": "CSV", "record_count": len(PROHIBITED), "primary_use": "Safety and compliance exclusions"},
        {"path": "data/source_registry.csv", "format": "CSV", "record_count": len(SOURCES), "primary_use": "Primary-source grounding registry"},
        {"path": "docs/data_dictionary.csv", "format": "CSV", "record_count": len(data_dictionary), "primary_use": "Field definitions"},
        {"path": "docs/episode_schema.json", "format": "JSON", "record_count": 1, "primary_use": "Episode schema contract"},
        {"path": "qa/qa_report.json", "format": "JSON", "record_count": 1, "primary_use": "Generation and leakage checks"},
        {"path": "qa/qa_summary.csv", "format": "CSV", "record_count": len(qa_summary_rows), "primary_use": "Human-readable release gate"},
        {"path": "qa/scenario_distribution.csv", "format": "CSV", "record_count": len(scenario_distribution_rows), "primary_use": "Per-scenario split balance"},
        {"path": "qa/action_distribution.csv", "format": "CSV", "record_count": len(action_distribution_rows), "primary_use": "Preferred-action label distribution"},
        {"path": "source/generate_dataset.py", "format": "Python", "record_count": "", "primary_use": "Deterministic regeneration"},
        {"path": "source/validate_dataset.py", "format": "Python", "record_count": "", "primary_use": "Independent validation"},
        {"path": "source/package_release.py", "format": "Python", "record_count": "", "primary_use": "Reproducible ZIP and SHA-256 manifest"},
    ]
    write_csv(ROOT / "dataset_index.csv", index_rows, ["path", "format", "record_count", "primary_use"])

    card = f"""# CallCenterFly Synthetic Credit-Union Calls v{VERSION}

## Purpose

This is the first dataset layer for the CallCenterFly experiment: a deterministic,
fully synthetic set of member call situations and abstract response objectives for a
frozen-connectome-plus-trainable-readout system.

It contains **no customer-service scripts and no fly-response wording**. The next
project phase can map the stable action families in `action_catalog.csv` to separately
reviewed, institution-specific scripts.

## Contents

- CSV-first release; no spreadsheet workbook is included.
- {len(SCENARIOS)} balanced scenario families.
- {len(all_episodes):,} three-decision call episodes.
- {len(all_decisions):,} flattened decision points.
- Fixed split: {len(episodes_by_split['train']):,} train / {len(episodes_by_split['validation']):,} validation / {len(episodes_by_split['test']):,} test episodes.
- JSONL episode files and CSV decision files.
- Scenario, action, prohibited-behavior, source, schema, and QA artifacts.

## Synthetic-data rules

- Every utterance is generated from project-authored templates and synthetic facts.
- No real call recording, transcript, member name, employee name, institution name,
  account number, card number, phone number, email, street address, SSN, or credentials
  are used.
- Dollar values and event ages are random synthetic variables and must not be treated
  as institution policy.
- `Zelle` is used only as a payment-rail scenario label. No Zelle or credit-union
  service promise is inferred.

## Intended learning task

At each decision point, the model observes structured call state plus one synthetic
member utterance. It selects one action from `candidate_actions_json`. The frozen
connectome may supply a state embedding; a small trainable readout or contextual bandit
selects the abstract action family. A compliance mask removes actions that are not
eligible for that context.

Reward defaults:

- Preferred action: `+1.00`
- Acceptable action: `+0.25`
- Other mask-eligible action: `-1.00`
- Prohibited behavior: `-3.00` and never presented as an eligible production action

## Important limitations

- This is a research dataset, not legal advice, operating procedure, or production QA.
- Potential Regulation E, Regulation Z, or Regulation CC flags require institution and
  counsel review; they are not final legal determinations.
- Institution-specific authentication, disclosures, holds, limits, fees, SLAs,
  escalation ownership, and complaint handling are intentionally not encoded as facts.
- The templates are English-only and do not yet model ASR noise, accents, multilingual
  calls, accessibility needs, vulnerable-adult handling, deceased-member servicing,
  bankruptcy, subpoenas, or complex commercial accounts.
- Before any real deployment, validate with credit-union operations, compliance, legal,
  information security, fair-lending, accessibility, and model-risk owners.

## Reproduction

Run:

```bash
python3 source/generate_dataset.py
```

The generator uses seed `{SEED}`. The release date is `{RELEASE_DATE}`.
"""
    (DOCS_DIR / "dataset_card.md").write_text(card, encoding="utf-8")

    readme = f"""# CallCenterFly dataset release v{VERSION}

Start with `dataset_index.csv` and `docs/dataset_card.md`, then review
`data/decision_sample.csv`, `data/scenario_catalog.csv`, and
`data/action_catalog.csv`. Use the JSONL files for sequential episode training and the
CSV files for inspection or contextual-bandit baselines. No spreadsheet workbook is
included.

Scripts and fly-response wording are explicitly deferred to the next project phase.
"""
    (ROOT / "README.md").write_text(readme, encoding="utf-8")

    manifest = {
        "name": "CallCenterFly Synthetic Credit-Union Calls",
        "version": VERSION,
        "release_date": RELEASE_DATE,
        "seed": SEED,
        "scenario_count": len(SCENARIOS),
        "episode_count": len(all_episodes),
        "decision_count": len(all_decisions),
        "scripts_included": False,
    }
    write_json(ROOT / "manifest.json", manifest)
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    build()
