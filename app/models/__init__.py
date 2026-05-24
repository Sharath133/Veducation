"""
Database Models
"""
from app.models.user import User, OTPVerification
from app.models.duel import DailyDuel, Registration
from app.models.question import Question
from app.models.leaderboard import UserAttempt, UserAnswer
from app.models.payment import Payment, Reward
from app.models.referral import Referral, LoyaltyTransaction
from app.models.pyq import PYQ, PYQQuestion, PYQCategory, PYQSection, PYQSectionPDF
from app.models.settlement import DuelSettlement, SettlementPayout
from app.models.support_ticket import SupportTicket
from app.models.user_feedback import UserFeedback
from app.models.admin_user_message import AdminUserMessage
from app.models.app_setting import AppSetting

__all__ = [
    "User",
    "OTPVerification",
    "DailyDuel",
    "Registration",
    "Question",
    "UserAttempt",
    "UserAnswer",
    "Payment",
    "Reward",
    "Referral",
    "LoyaltyTransaction",
    "PYQ",
    "PYQQuestion",
    "PYQCategory",
    "PYQSection",
    "PYQSectionPDF",
    "DuelSettlement",
    "SettlementPayout",
    "SupportTicket",
    "UserFeedback",
    "AdminUserMessage",
    "AppSetting",
]

