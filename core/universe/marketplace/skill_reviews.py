"""
Skill Reviews & Rating System
Handles review submission, rating aggregation, moderation, and spam detection.
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import re


logger = logging.getLogger(__name__)


class ReviewStatus(Enum):
    """Review status states"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    FLAGGED = "flagged"


class RatingScore(Enum):
    """Rating scale"""
    ONE_STAR = 1
    TWO_STAR = 2
    THREE_STAR = 3
    FOUR_STAR = 4
    FIVE_STAR = 5


@dataclass
class SkillReview:
    """A skill review"""
    id: Optional[int] = None
    skill_id: int = 0
    reviewer_id: str = ""
    rating: int = 0
    title: str = ""
    comment: str = ""
    helpful_count: int = 0
    unhelpful_count: int = 0
    created_at: Optional[datetime] = None
    status: str = ReviewStatus.PENDING.value


class SpamDetector:
    """Detects spam and malicious reviews"""
    
    # Patterns for spam detection
    SPAM_PATTERNS = [
        r"(?i)click\s+here",
        r"(?i)buy\s+now",
        r"(?i)visit\s+my\s+site",
        r"(?i)free\s+money",
        r"(?i)work\s+from\s+home",
    ]
    
    # Minimum review quality thresholds
    MIN_REVIEW_LENGTH = 10
    MAX_REVIEW_LENGTH = 5000
    
    SUSPICIOUS_PATTERNS = [
        r"[^a-zA-Z0-9\s\.\,\!\?\'\-]",  # Too many special characters
        r"([A-Z]{5,})",  # Excessive caps
        r"(.)(\1{4,})",  # Character repetition
    ]
    
    @staticmethod
    def is_spam(review_text: str) -> Tuple[bool, Optional[str]]:
        """Detect if review is spam"""
        
        if not review_text:
            return True, "Empty review"
        
        # Check length
        if len(review_text) < SpamDetector.MIN_REVIEW_LENGTH:
            return True, "Review too short"
        
        if len(review_text) > SpamDetector.MAX_REVIEW_LENGTH:
            return True, "Review too long"
        
        # Check for spam keywords
        for pattern in SpamDetector.SPAM_PATTERNS:
            if re.search(pattern, review_text):
                return True, "Contains spam keywords"
        
        # Check for suspicious patterns
        suspicious_count = 0
        for pattern in SpamDetector.SUSPICIOUS_PATTERNS:
            if re.search(pattern, review_text):
                suspicious_count += 1
        
        if suspicious_count >= 2:
            return True, "Suspicious formatting"
        
        return False, None
    
    @staticmethod
    def is_duplicate(new_review: str, existing_reviews: List[str]) -> bool:
        """Detect duplicate reviews"""
        # Simple similarity check
        new_words = set(new_review.lower().split())
        
        for existing in existing_reviews:
            existing_words = set(existing.lower().split())
            
            # If 80% of words match, consider it duplicate
            overlap = len(new_words & existing_words)
            similarity = overlap / max(len(new_words), len(existing_words))
            
            if similarity > 0.8:
                return True
        
        return False
    
    @staticmethod
    def is_abusive(review_text: str) -> bool:
        """Detect abusive language"""
        # Simple keyword-based detection
        ABUSIVE_KEYWORDS = [
            "stupid", "idiot", "worthless", "garbage",
            "hate", "disgusting", "terrible"
        ]
        
        text_lower = review_text.lower()
        for keyword in ABUSIVE_KEYWORDS:
            if keyword in text_lower:
                return True
        
        return False


class ReviewModeration:
    """Manages review moderation and approval"""
    
    def __init__(self, db_path: str = "marketplace.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize reviews database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skill_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_id INTEGER NOT NULL,
                reviewer_id TEXT NOT NULL,
                rating INTEGER NOT NULL,
                title TEXT,
                comment TEXT,
                helpful_count INTEGER DEFAULT 0,
                unhelpful_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (skill_id) REFERENCES skills(id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS review_flags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                review_id INTEGER NOT NULL,
                flag_type TEXT,
                reason TEXT,
                flagger_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (review_id) REFERENCES skill_reviews(id)
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_reviews_skill_id 
            ON skill_reviews(skill_id)
        """)
        
        conn.commit()
        conn.close()
    
    def submit_review(self, skill_id: int, reviewer_id: str, rating: int,
                     title: str, comment: str) -> Tuple[bool, Optional[int], str]:
        """Submit a new review"""
        
        # Validate rating
        if rating < 1 or rating > 5:
            return False, None, "Rating must be between 1 and 5"
        
        # Check for spam
        is_spam, reason = SpamDetector.is_spam(comment)
        if is_spam:
            return False, None, f"Review flagged as spam: {reason}"
        
        # Check for abusive language
        if SpamDetector.is_abusive(comment):
            return False, None, "Review contains abusive language"
        
        # Store review (initially pending approval)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO skill_reviews 
                (skill_id, reviewer_id, rating, title, comment, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (skill_id, reviewer_id, rating, title, comment, 
                  ReviewStatus.PENDING.value))
            
            review_id = cursor.lastrowid
            conn.commit()
            
            logger.info(f"Review submitted for skill {skill_id}: {review_id}")
            return True, review_id, "Review submitted for moderation"
        
        except sqlite3.Error as e:
            logger.error(f"Error submitting review: {e}")
            return False, None, "Failed to submit review"
        finally:
            conn.close()
    
    def approve_review(self, review_id: int) -> bool:
        """Approve a pending review"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE skill_reviews 
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (ReviewStatus.APPROVED.value, review_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Review {review_id} approved")
        return True
    
    def reject_review(self, review_id: int, reason: str = "") -> bool:
        """Reject a pending review"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE skill_reviews 
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (ReviewStatus.REJECTED.value, review_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Review {review_id} rejected: {reason}")
        return True
    
    def flag_review(self, review_id: int, flag_type: str, 
                   reason: str, flagger_id: str) -> bool:
        """Flag a review as problematic"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO review_flags (review_id, flag_type, reason, flagger_id)
                VALUES (?, ?, ?, ?)
            """, (review_id, flag_type, reason, flagger_id))
            
            # Mark review as flagged
            cursor.execute("""
                UPDATE skill_reviews 
                SET status = ?
                WHERE id = ?
            """, (ReviewStatus.FLAGGED.value, review_id))
            
            conn.commit()
            logger.info(f"Review {review_id} flagged: {flag_type}")
            return True
        
        except sqlite3.Error as e:
            logger.error(f"Error flagging review: {e}")
            return False
        finally:
            conn.close()
    
    def get_pending_reviews(self, limit: int = 20) -> List[SkillReview]:
        """Get reviews pending moderation"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, skill_id, reviewer_id, rating, title, comment,
                   helpful_count, unhelpful_count, status, created_at
            FROM skill_reviews 
            WHERE status = ?
            ORDER BY created_at ASC
            LIMIT ?
        """, (ReviewStatus.PENDING.value, limit))
        
        reviews = []
        for row in cursor.fetchall():
            reviews.append(SkillReview(
                id=row[0],
                skill_id=row[1],
                reviewer_id=row[2],
                rating=row[3],
                title=row[4],
                comment=row[5],
                helpful_count=row[6],
                unhelpful_count=row[7],
                status=row[8],
                created_at=datetime.fromisoformat(row[9])
            ))
        
        conn.close()
        return reviews


class RatingAggregator:
    """Aggregates and calculates skill ratings"""
    
    def __init__(self, db_path: str = "marketplace.db"):
        self.db_path = db_path
    
    def get_skill_rating(self, skill_id: int) -> Dict:
        """Get aggregated rating for a skill"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get approved reviews only
        cursor.execute("""
            SELECT rating, COUNT(*) as count
            FROM skill_reviews 
            WHERE skill_id = ? AND status = ?
            GROUP BY rating
        """, (skill_id, ReviewStatus.APPROVED.value))
        
        rating_counts = {}
        total_reviews = 0
        rating_sum = 0
        
        for row in cursor.fetchall():
            rating, count = row
            rating_counts[rating] = count
            total_reviews += count
            rating_sum += rating * count
        
        conn.close()
        
        if total_reviews == 0:
            return {
                "average_rating": 0.0,
                "total_reviews": 0,
                "rating_distribution": {}
            }
        
        average_rating = rating_sum / total_reviews
        
        # Build distribution
        distribution = {}
        for i in range(1, 6):
            distribution[i] = rating_counts.get(i, 0)
        
        return {
            "average_rating": round(average_rating, 2),
            "total_reviews": total_reviews,
            "rating_distribution": distribution
        }
    
    def get_trending_skills(self, limit: int = 10) -> List[Dict]:
        """Get trending skills by recent reviews"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get skills with recent approved reviews
        since = (datetime.now() - timedelta(days=7)).isoformat()
        
        cursor.execute("""
            SELECT sr.skill_id, s.name, COUNT(*) as review_count,
                   AVG(sr.rating) as avg_rating
            FROM skill_reviews sr
            JOIN skills s ON sr.skill_id = s.id
            WHERE sr.status = ? AND sr.created_at > ?
            GROUP BY sr.skill_id
            ORDER BY review_count DESC, avg_rating DESC
            LIMIT ?
        """, (ReviewStatus.APPROVED.value, since, limit))
        
        trending = []
        for row in cursor.fetchall():
            trending.append({
                "skill_id": row[0],
                "name": row[1],
                "recent_reviews": row[2],
                "average_rating": round(row[3], 2)
            })
        
        conn.close()
        return trending
    
    def get_review_history(self, skill_id: int) -> List[SkillReview]:
        """Get all approved reviews for a skill"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, skill_id, reviewer_id, rating, title, comment,
                   helpful_count, unhelpful_count, status, created_at
            FROM skill_reviews 
            WHERE skill_id = ? AND status = ?
            ORDER BY created_at DESC
        """, (skill_id, ReviewStatus.APPROVED.value))
        
        reviews = []
        for row in cursor.fetchall():
            reviews.append(SkillReview(
                id=row[0],
                skill_id=row[1],
                reviewer_id=row[2],
                rating=row[3],
                title=row[4],
                comment=row[5],
                helpful_count=row[6],
                unhelpful_count=row[7],
                status=row[8],
                created_at=datetime.fromisoformat(row[9])
            ))
        
        conn.close()
        return reviews
    
    def mark_helpful(self, review_id: int) -> bool:
        """Mark a review as helpful"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE skill_reviews 
            SET helpful_count = helpful_count + 1
            WHERE id = ?
        """, (review_id,))
        
        conn.commit()
        conn.close()
        return True
    
    def mark_unhelpful(self, review_id: int) -> bool:
        """Mark a review as unhelpful"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE skill_reviews 
            SET unhelpful_count = unhelpful_count + 1
            WHERE id = ?
        """, (review_id,))
        
        conn.commit()
        conn.close()
        return True
