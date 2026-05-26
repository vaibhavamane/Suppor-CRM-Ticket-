import logging
import re
from typing import Set
from pybloom_live import ScalableBloomFilter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.ticket import Ticket
from app.config.settings import settings

logger = logging.getLogger("bloom_service")
# Set logging level
logging.basicConfig(level=logging.INFO)

class BloomFilterService:
    def __init__(self):
        # ScalableBloomFilter grows dynamically to handle any number of tickets
        self.bf = ScalableBloomFilter(
            initial_capacity=settings.BLOOM_CAPACITY,
            error_rate=settings.BLOOM_ERROR_RATE,
            mode=ScalableBloomFilter.SMALL_SET_GROWTH
        )
        self._initialized = False

    def get_searchable_tokens(
        self,
        ticket_id: str,
        customer_name: str,
        customer_email: str,
        subject: str,
        description: str
    ) -> Set[str]:
        """
        Tokenizes ticket attributes to populate the Bloom Filter.
        Extracts full fields, words, and prefixes of length >= 2 to support partial queries.
        """
        tokens = set()
        
        # Raw fields to add (fully lowercased and stripped)
        raw_fields = [ticket_id, customer_name, customer_email, subject]
        for field in raw_fields:
            if field:
                val = field.lower().strip()
                tokens.add(val)
                # Add prefixes for full field (e.g. "john d" for "john doe")
                for i in range(2, len(val) + 1):
                    tokens.add(val[:i])
                    
        # Tokenized individual words (split by space and punctuation)
        all_text = f"{ticket_id} {customer_name} {customer_email} {subject} {description}"
        words = re.findall(r'[a-z0-9\-]+', all_text.lower())
        for word in words:
            if len(word) >= 2:
                tokens.add(word)
                for i in range(2, len(word) + 1):
                    tokens.add(word[:i])
                    
        return tokens

    def add_ticket(self, ticket: Ticket):
        """
        Add a single ticket's searchable tokens to the Bloom Filter.
        """
        tokens = self.get_searchable_tokens(
            ticket_id=ticket.ticket_id,
            customer_name=ticket.customer_name,
            customer_email=ticket.customer_email,
            subject=ticket.subject,
            description=ticket.description
        )
        for token in tokens:
            self.bf.add(token)

    def check_query(self, query: str) -> bool:
        """
        Checks if the search query could potentially match any ticket.
        If any token/word in the search query is NOT in the Bloom Filter,
        then a match definitely does not exist. We can safely bypass the DB.
        """
        if not query or not query.strip():
            return True
            
        query_clean = query.lower().strip()
        # Direct check for the whole query
        if query_clean in self.bf:
            return True
            
        # Check individual word tokens
        words = re.findall(r'[a-z0-9\-]+', query_clean)
        if not words:
            return True  # Fallback to DB query if no words parsed
            
        for word in words:
            if len(word) >= 2:
                if word not in self.bf:
                    logger.info(f"[BloomFilter] Cache MISS: Token '{word}' not present in Bloom Filter. DB query bypassed.")
                    return False
                    
        logger.info(f"[BloomFilter] Cache HIT: Query '{query_clean}' might exist in DB. Proceeding to DB query.")
        return True

    async def initialize_from_db(self, db: AsyncSession):
        """
        Initializes the Bloom Filter by loading all existing tickets from the DB.
        Called on application startup.
        """
        if self._initialized:
            return
            
        logger.info("Initializing Bloom Filter from database...")
        stmt = select(Ticket)
        result = await db.execute(stmt)
        tickets = result.scalars().all()
        
        count = 0
        for ticket in tickets:
            self.add_ticket(ticket)
            count += 1
            
        self._initialized = True
        logger.info(f"Bloom Filter initialization completed. Indexed {count} tickets.")

# Export a single global instance
bloom_service = BloomFilterService()
