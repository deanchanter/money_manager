"""Shared auto-categorization logic.

Used by both the CSV importer and the SimpleFIN sync so the two paths stay
consistent. Learned rules win over category keywords.
"""
from typing import Callable, Optional
from sqlalchemy.orm import Session

from models import Category, AutoCategoryRule
from services.mcc import category_name_for_mcc


def build_categorizer(db: Session) -> Callable[[str], Optional[int]]:
    """Load rules once and return a reusable categorizer.

    The CSV importer used to re-query the rules table for every row; loading
    them up front matters more for sync, which can process a few thousand
    transactions in one backfill.
    """
    categories = db.query(Category).all()
    rules = db.query(AutoCategoryRule).order_by(AutoCategoryRule.priority.desc()).all()

    by_name = {category.name.lower(): category.id for category in categories}

    keyword_index = []
    for category in categories:
        if not category.keywords:
            continue
        for keyword in category.keywords.split(","):
            keyword = keyword.strip().lower()
            if keyword:
                keyword_index.append((keyword, category.id))

    def categorize(*texts: str, mcc: object = None) -> Optional[int]:
        """Categorize against one or more description-ish strings.

        SimpleFIN gives us description, payee and memo; any of them may carry
        the recognizable merchant name, so all are matched against.

        Precedence is learned rules, then merchant category code, then
        keywords: a rule is an explicit user correction so it always wins, but
        an MCC is assigned by the card network and beats guessing from text.
        """
        haystacks = [t.lower() for t in texts if t]

        for rule in rules:
            for text in haystacks:
                if rule.match_type == "exact" and rule.pattern == text:
                    return rule.category_id
                if rule.match_type == "starts_with" and text.startswith(rule.pattern):
                    return rule.category_id
                if rule.match_type == "contains" and rule.pattern in text:
                    return rule.category_id

        mcc_name = category_name_for_mcc(mcc)
        if mcc_name and mcc_name.lower() in by_name:
            return by_name[mcc_name.lower()]

        for keyword, category_id in keyword_index:
            for text in haystacks:
                if keyword in text:
                    return category_id
        return None

    return categorize


def auto_categorize(db: Session, description: str) -> Optional[int]:
    """One-shot categorization. Prefer build_categorizer() in loops."""
    return build_categorizer(db)(description)
