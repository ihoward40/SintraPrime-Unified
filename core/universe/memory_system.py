"""
UniVerse Hive Mind Memory System
Distributed knowledge and learning system for collective agent improvement
"""

import json
import sqlite3
import time
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, asdict
import hashlib
import re
from pathlib import Path
from collections import defaultdict, Counter

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False

# Database configuration
DB_PATH = "/agent/home/universe/memory.db"
VECTOR_DIMENSION = 384  # Using all-MiniLM-L6-v2 model


@dataclass
class Knowledge:
    """Represents a piece of shared knowledge/experience"""
    id: str
    content: str
    type: str  # 'experience', 'skill', 'pattern', 'insight'
    source_agent: str
    created_at: datetime
    embedding: Optional[List[float]] = None
    tags: List[str] = None
    relevance_score: float = 1.0
    usage_count: int = 0
    success_rate: float = 1.0
    metadata: Dict = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class Skill:
    """Represents a learned skill that can be inherited by agents"""
    id: str
    name: str
    description: str
    implementation: str  # Serialized code/function
    source_agent: str
    created_at: datetime
    version: int = 1
    usage_count: int = 0
    success_rate: float = 1.0
    dependencies: List[str] = None
    tags: List[str] = None
    embedding: Optional[List[float]] = None
    performance_metrics: Dict = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.tags is None:
            self.tags = []
        if self.performance_metrics is None:
            self.performance_metrics = {}


class MemorySystem:
    """Distributed knowledge and learning system for UniVerse agents"""
    
    def __init__(self, db_path: str = DB_PATH):
        """Initialize the memory system"""
        self.db_path = db_path
        self.connection = None
        self.cursor = None
        self.embedder = None
        self.embedding_cache = {}
        
        # Initialize database
        self._init_database()
        
        # Initialize embedder if available
        if EMBEDDINGS_AVAILABLE:
            try:
                self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
            except Exception as e:
                print(f"Warning: Could not load embedder: {e}")
    
    def _init_database(self):
        """Create or connect to the database and initialize tables"""
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.cursor = self.connection.cursor()
            
            # Create tables if they don't exist
            self._create_tables()
            self.connection.commit()
        except Exception as e:
            print(f"Database initialization error: {e}")
            raise
    
    def _create_tables(self):
        """Create all necessary tables for the memory system"""
        tables = [
            """
            CREATE TABLE IF NOT EXISTS knowledge_base (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                type TEXT NOT NULL,
                source_agent TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                embedding BLOB,
                tags TEXT,
                relevance_score REAL DEFAULT 1.0,
                usage_count INTEGER DEFAULT 0,
                success_rate REAL DEFAULT 1.0,
                metadata TEXT,
                UNIQUE(content, type, source_agent)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS knowledge_relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_knowledge_id TEXT NOT NULL,
                target_knowledge_id TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                strength REAL DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,
                FOREIGN KEY(source_knowledge_id) REFERENCES knowledge_base(id),
                FOREIGN KEY(target_knowledge_id) REFERENCES knowledge_base(id),
                UNIQUE(source_knowledge_id, target_knowledge_id, relationship_type)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS skills (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                implementation TEXT,
                source_agent TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                version INTEGER DEFAULT 1,
                usage_count INTEGER DEFAULT 0,
                success_rate REAL DEFAULT 1.0,
                dependencies TEXT,
                tags TEXT,
                embedding BLOB,
                performance_metrics TEXT,
                active BOOLEAN DEFAULT 1
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS skill_inheritance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                inherited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                usage_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                performance_score REAL DEFAULT 1.0,
                metadata TEXT,
                FOREIGN KEY(skill_id) REFERENCES skills(id),
                UNIQUE(skill_id, agent_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS learning_sessions (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                trigger_type TEXT NOT NULL,
                trigger_task_id TEXT,
                mentor_agent_id TEXT,
                content TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                generated_skills TEXT,
                improvements TEXT,
                metadata TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS agent_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                metric_type TEXT NOT NULL,
                value REAL NOT NULL,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                context TEXT,
                UNIQUE(agent_id, metric_type, recorded_at)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS knowledge_search_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                query_hash TEXT UNIQUE,
                results TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                hit_count INTEGER DEFAULT 0
            )
            """
        ]
        
        for table_sql in tables:
            try:
                self.cursor.execute(table_sql)
            except sqlite3.OperationalError as e:
                if "already exists" not in str(e):
                    raise
    
    def _generate_id(self, *parts) -> str:
        """Generate a deterministic ID from parts"""
        content = "|".join(str(p) for p in parts)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _extract_tags(self, content: str) -> List[str]:
        """Automatically extract tags from content"""
        # Remove common words and extract meaningful terms
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'is', 'was', 'are', 'be', 'been', 'have',
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those', 'i',
            'you', 'he', 'she', 'it', 'we', 'they', 'what', 'which', 'who', 'when',
            'where', 'why', 'how'
        }
        
        # Extract words, capitalize them
        words = re.findall(r'\b[a-z]{3,}\b', content.lower())
        tags = [w for w in words if w not in stop_words]
        
        # Get top unique terms by frequency
        tag_freq = Counter(tags)
        return [tag for tag, _ in tag_freq.most_common(10)]
    
    def _encode(self, text: str):
        """Generate embedding for text"""
        if not EMBEDDINGS_AVAILABLE or not self.embedder:
            return None
        
        try:
            # Check cache
            text_hash = hashlib.md5(text.encode()).hexdigest()
            if text_hash in self.embedding_cache:
                return self.embedding_cache[text_hash]
            
            # Generate embedding
            embedding = self.embedder.encode(text, convert_to_numpy=True)
            self.embedding_cache[text_hash] = embedding
            return embedding
        except Exception as e:
            print(f"Embedding error: {e}")
            return None
    
    def _serialize_embedding(self, embedding: Optional[List[float]]) -> Optional[bytes]:
        """Serialize embedding to bytes for storage"""
        if embedding is None:
            return None
        if NUMPY_AVAILABLE:
            if not isinstance(embedding, np.ndarray):
                embedding = np.array(embedding)
            return embedding.astype(np.float32).tobytes()
        else:
            # Fallback: convert to json
            return json.dumps(embedding).encode('utf-8')
    
    def _deserialize_embedding(self, blob: Optional[bytes]) -> Optional[List[float]]:
        """Deserialize bytes to embedding"""
        if blob is None:
            return None
        if NUMPY_AVAILABLE:
            return np.frombuffer(blob, dtype=np.float32)
        else:
            # Fallback: decode from json
            try:
                return json.loads(blob.decode('utf-8'))
            except:
                return None
    
    # ========== KNOWLEDGE STORAGE ==========
    
    def store_knowledge(self, content: str, knowledge_type: str, 
                       source_agent: str, metadata: Dict = None) -> str:
        """Store a new piece of knowledge/experience"""
        try:
            # Generate ID
            kid = self._generate_id(content, knowledge_type, source_agent)
            
            # Extract tags
            tags = self._extract_tags(content)
            
            # Generate embedding
            embedding = self._encode(content)
            embedding_blob = self._serialize_embedding(embedding)
            
            # Insert knowledge
            self.cursor.execute("""
                INSERT OR IGNORE INTO knowledge_base 
                (id, content, type, source_agent, embedding, tags, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (kid, content, knowledge_type, source_agent, embedding_blob,
                  json.dumps(tags), json.dumps(metadata or {})))
            
            self.connection.commit()
            return kid
        except Exception as e:
            print(f"Error storing knowledge: {e}")
            return None
    
    def update_knowledge_usage(self, knowledge_id: str, success: bool = True):
        """Update usage statistics for a piece of knowledge"""
        try:
            # Increment usage count
            self.cursor.execute("""
                UPDATE knowledge_base 
                SET usage_count = usage_count + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (knowledge_id,))
            
            # Update success rate
            if success:
                self.cursor.execute("""
                    UPDATE knowledge_base 
                    SET success_rate = (success_rate * usage_count + 1) / (usage_count + 1)
                    WHERE id = ?
                """, (knowledge_id,))
            
            self.connection.commit()
        except Exception as e:
            print(f"Error updating knowledge: {e}")
    
    def search_knowledge_semantic(self, query: str, limit: int = 10, 
                                 knowledge_type: str = None) -> List[Dict]:
        """Semantic search across knowledge base using vector similarity"""
        try:
            # Check cache first
            query_hash = hashlib.md5(query.encode()).hexdigest()
            self.cursor.execute("""
                SELECT results FROM knowledge_search_cache 
                WHERE query_hash = ? AND expires_at > CURRENT_TIMESTAMP
            """, (query_hash,))
            cached = self.cursor.fetchone()
            if cached:
                self.cursor.execute("""
                    UPDATE knowledge_search_cache 
                    SET hit_count = hit_count + 1 
                    WHERE query_hash = ?
                """, (query_hash,))
                self.connection.commit()
                return json.loads(cached[0])
            
            # Get query embedding
            if not EMBEDDINGS_AVAILABLE or not self.embedder:
                return self.search_knowledge_keyword(query, limit, knowledge_type)
            
            query_embedding = self._encode(query)
            if query_embedding is None:
                return self.search_knowledge_keyword(query, limit, knowledge_type)
            
            # Helper function for cosine similarity
            def cosine_similarity(a, b):
                if NUMPY_AVAILABLE:
                    a = np.array(a) if not isinstance(a, np.ndarray) else a
                    b = np.array(b) if not isinstance(b, np.ndarray) else b
                    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))
                else:
                    # Manual cosine similarity
                    dot_product = sum(x * y for x, y in zip(a, b))
                    norm_a = sum(x * x for x in a) ** 0.5
                    norm_b = sum(x * x for x in b) ** 0.5
                    return dot_product / (norm_a * norm_b + 1e-8)
            
            # Get all knowledge with embeddings
            type_filter = f"AND type = '{knowledge_type}'" if knowledge_type else ""
            self.cursor.execute(f"""
                SELECT id, content, type, source_agent, created_at, tags, 
                       relevance_score, usage_count, success_rate, embedding
                FROM knowledge_base 
                WHERE embedding IS NOT NULL {type_filter}
                ORDER BY usage_count DESC
            """)
            
            results = []
            for row in self.cursor.fetchall():
                kid, content, ktype, agent, created, tags, relevance, usage, success, emb_blob = row
                
                if emb_blob is None:
                    continue
                
                embedding = self._deserialize_embedding(emb_blob)
                if embedding is None:
                    continue
                
                # Calculate cosine similarity
                similarity = cosine_similarity(query_embedding, embedding)
                
                # Combine with relevance and success metrics
                score = (similarity * 0.6 + (relevance / 10.0) * 0.2 + 
                        (success * 0.2))
                
                results.append({
                    'id': kid,
                    'content': content,
                    'type': ktype,
                    'source_agent': agent,
                    'created_at': created,
                    'tags': json.loads(tags or '[]'),
                    'score': score,
                    'usage_count': usage,
                    'success_rate': success
                })
            
            # Sort by score and limit
            results = sorted(results, key=lambda x: x['score'], reverse=True)[:limit]
            
            # Cache results (1 hour expiry)
            cache_expiry = (datetime.now() + timedelta(hours=1)).isoformat()
            self.cursor.execute("""
                INSERT INTO knowledge_search_cache 
                (query_hash, query, results, expires_at)
                VALUES (?, ?, ?, ?)
            """, (query_hash, query, json.dumps(results), cache_expiry))
            self.connection.commit()
            
            return results
        except Exception as e:
            print(f"Error in semantic search: {e}")
            return []
    
    def search_knowledge_keyword(self, query: str, limit: int = 10, 
                                knowledge_type: str = None) -> List[Dict]:
        """Keyword-based search across knowledge base"""
        try:
            keywords = query.lower().split()
            type_filter = f"AND type = '{knowledge_type}'" if knowledge_type else ""
            
            self.cursor.execute(f"""
                SELECT id, content, type, source_agent, created_at, tags, 
                       relevance_score, usage_count, success_rate
                FROM knowledge_base {f"WHERE type = '{knowledge_type}'" if knowledge_type else ""}
                ORDER BY usage_count DESC, success_rate DESC
                LIMIT ?
            """, (limit * 2,))
            
            results = []
            for row in self.cursor.fetchall():
                kid, content, ktype, agent, created, tags, relevance, usage, success = row
                
                # Score based on keyword matches
                content_lower = content.lower()
                matches = sum(1 for kw in keywords if kw in content_lower)
                
                if matches > 0:
                    score = (matches / len(keywords) * 0.4 + 
                            (relevance / 10.0) * 0.3 + (success * 0.3))
                    
                    results.append({
                        'id': kid,
                        'content': content,
                        'type': ktype,
                        'source_agent': agent,
                        'created_at': created,
                        'tags': json.loads(tags or '[]'),
                        'score': score,
                        'usage_count': usage,
                        'success_rate': success
                    })
            
            return sorted(results, key=lambda x: x['score'], reverse=True)[:limit]
        except Exception as e:
            print(f"Error in keyword search: {e}")
            return []
    
    # ========== KNOWLEDGE RELATIONSHIPS ==========
    
    def link_knowledge(self, source_id: str, target_id: str, 
                      relationship_type: str, strength: float = 1.0):
        """Create a relationship between two pieces of knowledge"""
        try:
            self.cursor.execute("""
                INSERT OR IGNORE INTO knowledge_relationships
                (source_knowledge_id, target_knowledge_id, relationship_type, strength)
                VALUES (?, ?, ?, ?)
            """, (source_id, target_id, relationship_type, strength))
            
            self.connection.commit()
        except Exception as e:
            print(f"Error linking knowledge: {e}")
    
    def get_related_knowledge(self, knowledge_id: str, 
                            relationship_type: str = None, depth: int = 1) -> List[Dict]:
        """Get knowledge related to a given piece of knowledge"""
        try:
            related = []
            visited = {knowledge_id}
            queue = [(knowledge_id, 0)]
            
            while queue:
                current_id, current_depth = queue.pop(0)
                
                if current_depth >= depth:
                    continue
                
                # Get related knowledge
                type_filter = f"AND relationship_type = '{relationship_type}'" if relationship_type else ""
                self.cursor.execute(f"""
                    SELECT kr.target_knowledge_id, kr.relationship_type, kr.strength,
                           kb.content, kb.type, kb.source_agent, kb.success_rate
                    FROM knowledge_relationships kr
                    JOIN knowledge_base kb ON kr.target_knowledge_id = kb.id
                    WHERE kr.source_knowledge_id = ? {type_filter}
                    ORDER BY kr.strength DESC
                """, (current_id,))
                
                for row in self.cursor.fetchall():
                    target_id, rel_type, strength, content, ktype, agent, success = row
                    
                    if target_id not in visited:
                        visited.add(target_id)
                        queue.append((target_id, current_depth + 1))
                        
                        related.append({
                            'id': target_id,
                            'content': content,
                            'type': ktype,
                            'source_agent': agent,
                            'relationship_type': rel_type,
                            'strength': strength,
                            'success_rate': success,
                            'depth': current_depth + 1
                        })
            
            return sorted(related, key=lambda x: (x['depth'], -x['strength']))
        except Exception as e:
            print(f"Error getting related knowledge: {e}")
            return []
    
    # ========== SKILL LIBRARY ==========
    
    def register_skill(self, name: str, description: str, implementation: str,
                      source_agent: str, dependencies: List[str] = None,
                      tags: List[str] = None) -> str:
        """Register a new skill in the library"""
        try:
            skill_id = self._generate_id(name, source_agent)
            
            # Generate embedding
            embedding = self._encode(f"{name} {description}")
            embedding_blob = self._serialize_embedding(embedding)
            
            # Get current version
            self.cursor.execute("SELECT MAX(version) FROM skills WHERE name = ?", (name,))
            max_version = self.cursor.fetchone()[0]
            version = (max_version or 0) + 1
            
            self.cursor.execute("""
                INSERT OR REPLACE INTO skills
                (id, name, description, implementation, source_agent, 
                 version, dependencies, tags, embedding)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (skill_id, name, description, implementation, source_agent,
                  version, json.dumps(dependencies or []), json.dumps(tags or []),
                  embedding_blob))
            
            self.connection.commit()
            return skill_id
        except Exception as e:
            print(f"Error registering skill: {e}")
            return None
    
    def search_skills(self, query: str, limit: int = 10) -> List[Dict]:
        """Search skills by semantic meaning"""
        try:
            if not EMBEDDINGS_AVAILABLE or not self.embedder:
                # Fallback to keyword search
                keywords = query.lower().split()
                self.cursor.execute("""
                    SELECT id, name, description, source_agent, version, 
                           usage_count, success_rate, tags
                    FROM skills WHERE active = 1
                    ORDER BY usage_count DESC, success_rate DESC
                    LIMIT ?
                """, (limit,))
                results = self.cursor.fetchall()
                return [{'id': r[0], 'name': r[1], 'description': r[2],
                        'source_agent': r[3], 'version': r[4], 'usage_count': r[5],
                        'success_rate': r[6], 'tags': json.loads(r[7] or '[]')}
                       for r in results]
            
            # Semantic search with embeddings
            query_embedding = self._encode(query)
            
            # Helper function for cosine similarity
            def cosine_similarity(a, b):
                if NUMPY_AVAILABLE:
                    a = np.array(a) if not isinstance(a, np.ndarray) else a
                    b = np.array(b) if not isinstance(b, np.ndarray) else b
                    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))
                else:
                    dot_product = sum(x * y for x, y in zip(a, b))
                    norm_a = sum(x * x for x in a) ** 0.5
                    norm_b = sum(x * x for x in b) ** 0.5
                    return dot_product / (norm_a * norm_b + 1e-8)
            
            self.cursor.execute("""
                SELECT id, name, description, source_agent, version, 
                       usage_count, success_rate, tags, embedding
                FROM skills WHERE active = 1 AND embedding IS NOT NULL
                ORDER BY version DESC
            """)
            
            results_with_scores = []
            for row in self.cursor.fetchall():
                skill_id, name, desc, agent, version, usage, success, tags, emb_blob = row
                
                if emb_blob is None:
                    continue
                
                embedding = self._deserialize_embedding(emb_blob)
                if embedding is None:
                    continue
                
                similarity = cosine_similarity(query_embedding, embedding)
                
                results_with_scores.append((
                    similarity * 0.6 + (success * 0.4),  # score
                    (skill_id, name, desc, agent, version, usage, success, 
                     json.loads(tags or '[]'))
                ))
            
            results = [row for _, row in sorted(results_with_scores, 
                                               key=lambda x: x[0], reverse=True)[:limit]]
            return [{'id': r[0], 'name': r[1], 'description': r[2],
                    'source_agent': r[3], 'version': r[4], 'usage_count': r[5],
                    'success_rate': r[6], 'tags': r[7]} for r in results]
        except Exception as e:
            print(f"Error searching skills: {e}")
            return []
    
    # ========== SKILL INHERITANCE ==========
    
    def inherit_skill(self, skill_id: str, agent_id: str) -> bool:
        """Allow an agent to inherit a skill"""
        try:
            self.cursor.execute("""
                INSERT OR IGNORE INTO skill_inheritance (skill_id, agent_id)
                VALUES (?, ?)
            """, (skill_id, agent_id))
            
            self.connection.commit()
            return self.cursor.rowcount > 0
        except Exception as e:
            print(f"Error inheriting skill: {e}")
            return False
    
    def discover_skills_for_agent(self, agent_id: str, 
                                 recent_task_ids: List[str] = None) -> List[Dict]:
        """Automatically discover relevant skills for an agent based on tasks"""
        try:
            # Get skills already inherited
            self.cursor.execute("""
                SELECT skill_id FROM skill_inheritance WHERE agent_id = ?
            """, (agent_id,))
            inherited_skills = set(row[0] for row in self.cursor.fetchall())
            
            # Get all available skills that agent hasn't inherited
            self.cursor.execute("""
                SELECT id, name, description, source_agent, version, 
                       usage_count, success_rate, tags
                FROM skills 
                WHERE active = 1 AND id NOT IN ({})
                ORDER BY success_rate DESC, usage_count DESC
                LIMIT 20
            """.format(','.join('?' * len(inherited_skills)) if inherited_skills else "''"))
            
            discovered = []
            for row in self.cursor.fetchall():
                skill_id, name, desc, agent, version, usage, success, tags = row
                discovered.append({
                    'id': skill_id,
                    'name': name,
                    'description': desc,
                    'source_agent': agent,
                    'version': version,
                    'usage_count': usage,
                    'success_rate': success,
                    'tags': json.loads(tags or '[]'),
                    'recommendation_score': success * (1 + usage / 100)
                })
            
            return sorted(discovered, key=lambda x: x['recommendation_score'], reverse=True)
        except Exception as e:
            print(f"Error discovering skills: {e}")
            return []
    
    def update_skill_performance(self, skill_id: str, agent_id: str, 
                                success: bool, metrics: Dict = None):
        """Update performance metrics for a skill used by an agent"""
        try:
            if success:
                self.cursor.execute("""
                    UPDATE skill_inheritance 
                    SET usage_count = usage_count + 1,
                        success_count = success_count + 1,
                        performance_score = (performance_score * usage_count + 1) / (usage_count + 1)
                    WHERE skill_id = ? AND agent_id = ?
                """, (skill_id, agent_id))
            else:
                self.cursor.execute("""
                    UPDATE skill_inheritance 
                    SET usage_count = usage_count + 1,
                        failure_count = failure_count + 1,
                        performance_score = (performance_score * usage_count) / (usage_count + 1)
                    WHERE skill_id = ? AND agent_id = ?
                """, (skill_id, agent_id))
            
            # Update global skill metrics
            self.cursor.execute("""
                UPDATE skills 
                SET usage_count = usage_count + 1
                WHERE id = ?
            """, (skill_id,))
            
            if success:
                self.cursor.execute("""
                    UPDATE skills 
                    SET success_rate = (success_rate * usage_count + 1) / (usage_count + 1)
                    WHERE id = ?
                """, (skill_id,))
            
            self.connection.commit()
        except Exception as e:
            print(f"Error updating skill performance: {e}")
    
    # ========== LEARNING LOOPS ==========
    
    def start_learning_session(self, agent_id: str, trigger_type: str,
                              trigger_task_id: str = None, 
                              mentor_agent_id: str = None) -> str:
        """Start a learning session triggered by a failure"""
        try:
            session_id = self._generate_id(agent_id, trigger_task_id, 'learning', 
                                          str(time.time()))
            
            self.cursor.execute("""
                INSERT INTO learning_sessions
                (id, agent_id, trigger_type, trigger_task_id, mentor_agent_id)
                VALUES (?, ?, ?, ?, ?)
            """, (session_id, agent_id, trigger_type, trigger_task_id, 
                  mentor_agent_id))
            
            self.connection.commit()
            return session_id
        except Exception as e:
            print(f"Error starting learning session: {e}")
            return None
    
    def record_learning_improvement(self, session_id: str, 
                                   generated_skills: List[str] = None,
                                   improvements: Dict = None,
                                   content: str = None):
        """Record improvements from a learning session"""
        try:
            self.cursor.execute("""
                UPDATE learning_sessions 
                SET status = 'completed',
                    completed_at = CURRENT_TIMESTAMP,
                    generated_skills = ?,
                    improvements = ?,
                    content = ?
                WHERE id = ?
            """, (json.dumps(generated_skills or []),
                  json.dumps(improvements or {}),
                  content,
                  session_id))
            
            self.connection.commit()
        except Exception as e:
            print(f"Error recording learning: {e}")
    
    def get_learning_sessions(self, agent_id: str = None, 
                             limit: int = 20) -> List[Dict]:
        """Get learning sessions for analysis and improvement"""
        try:
            if agent_id:
                self.cursor.execute("""
                    SELECT id, agent_id, trigger_type, mentor_agent_id, status,
                           created_at, completed_at, generated_skills, improvements
                    FROM learning_sessions
                    WHERE agent_id = ? AND status = 'completed'
                    ORDER BY completed_at DESC
                    LIMIT ?
                """, (agent_id, limit))
            else:
                self.cursor.execute("""
                    SELECT id, agent_id, trigger_type, mentor_agent_id, status,
                           created_at, completed_at, generated_skills, improvements
                    FROM learning_sessions
                    WHERE status = 'completed'
                    ORDER BY completed_at DESC
                    LIMIT ?
                """, (limit,))
            
            results = []
            for row in self.cursor.fetchall():
                results.append({
                    'id': row[0],
                    'agent_id': row[1],
                    'trigger_type': row[2],
                    'mentor_agent_id': row[3],
                    'status': row[4],
                    'created_at': row[5],
                    'completed_at': row[6],
                    'generated_skills': json.loads(row[7] or '[]'),
                    'improvements': json.loads(row[8] or '{}')
                })
            
            return results
        except Exception as e:
            print(f"Error getting learning sessions: {e}")
            return []
    
    # ========== AGENT PERFORMANCE ==========
    
    def record_agent_performance(self, agent_id: str, metric_type: str,
                                value: float, context: Dict = None):
        """Record performance metrics for an agent"""
        try:
            self.cursor.execute("""
                INSERT INTO agent_performance 
                (agent_id, metric_type, value, context)
                VALUES (?, ?, ?, ?)
            """, (agent_id, metric_type, value, json.dumps(context or {})))
            
            self.connection.commit()
        except Exception as e:
            print(f"Error recording performance: {e}")
    
    def get_agent_analytics(self, agent_id: str, 
                           metric_type: str = None,
                           days: int = 30) -> Dict:
        """Get performance analytics for an agent"""
        try:
            time_filter = f"AND recorded_at > datetime('now', '-{days} days')"
            metric_filter = f"AND metric_type = '{metric_type}'" if metric_type else ""
            
            self.cursor.execute(f"""
                SELECT metric_type, COUNT(*) as count, AVG(value) as avg_value,
                       MIN(value) as min_value, MAX(value) as max_value
                FROM agent_performance
                WHERE agent_id = ? {time_filter} {metric_filter}
                GROUP BY metric_type
            """, (agent_id,))
            
            analytics = {}
            for row in self.cursor.fetchall():
                metric, count, avg_val, min_val, max_val = row
                analytics[metric] = {
                    'count': count,
                    'average': avg_val,
                    'min': min_val,
                    'max': max_val
                }
            
            return analytics
        except Exception as e:
            print(f"Error getting analytics: {e}")
            return {}
    
    # ========== UTILITY FUNCTIONS ==========
    
    def get_stats(self) -> Dict:
        """Get overall memory system statistics"""
        try:
            stats = {}
            
            # Knowledge stats
            self.cursor.execute("SELECT COUNT(*) FROM knowledge_base")
            stats['total_knowledge'] = self.cursor.fetchone()[0]
            
            self.cursor.execute("""
                SELECT COUNT(DISTINCT source_agent) FROM knowledge_base
            """)
            stats['knowledge_sources'] = self.cursor.fetchone()[0]
            
            # Skill stats
            self.cursor.execute("SELECT COUNT(*) FROM skills WHERE active = 1")
            stats['active_skills'] = self.cursor.fetchone()[0]
            
            self.cursor.execute("""
                SELECT COUNT(DISTINCT agent_id) FROM skill_inheritance
            """)
            stats['agents_learning'] = self.cursor.fetchone()[0]
            
            # Learning stats
            self.cursor.execute("""
                SELECT COUNT(*) FROM learning_sessions WHERE status = 'completed'
            """)
            stats['completed_learning_sessions'] = self.cursor.fetchone()[0]
            
            # Performance stats
            self.cursor.execute("""
                SELECT COUNT(DISTINCT agent_id) FROM agent_performance
            """)
            stats['agents_tracked'] = self.cursor.fetchone()[0]
            
            # Relationship stats
            self.cursor.execute("SELECT COUNT(*) FROM knowledge_relationships")
            stats['knowledge_relationships'] = self.cursor.fetchone()[0]
            
            return stats
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {}
    
    def export_knowledge_graph(self, limit: int = 1000) -> Dict:
        """Export knowledge graph as JSON for visualization"""
        try:
            # Get knowledge nodes
            self.cursor.execute("""
                SELECT id, content, type, source_agent, success_rate, usage_count
                FROM knowledge_base
                ORDER BY success_rate DESC, usage_count DESC
                LIMIT ?
            """, (limit,))
            
            nodes = []
            node_ids = []
            for row in self.cursor.fetchall():
                nodes.append({
                    'id': row[0],
                    'label': row[1][:50],
                    'type': row[2],
                    'source': row[3],
                    'success_rate': row[4],
                    'usage_count': row[5]
                })
                node_ids.append(row[0])
            
            # Get relationships
            edges = []
            if node_ids:
                placeholders = ','.join('?' * len(node_ids))
                self.cursor.execute(f"""
                    SELECT source_knowledge_id, target_knowledge_id, relationship_type, strength
                    FROM knowledge_relationships
                    WHERE source_knowledge_id IN ({placeholders})
                    ORDER BY strength DESC
                """, node_ids)
                
                for row in self.cursor.fetchall():
                    edges.append({
                        'source': row[0],
                        'target': row[1],
                        'type': row[2],
                        'weight': row[3]
                    })
            
            return {
                'nodes': nodes,
                'edges': edges,
                'node_count': len(nodes),
                'edge_count': len(edges)
            }
        except Exception as e:
            print(f"Error exporting knowledge graph: {e}")
            return {'nodes': [], 'edges': []}
    
    def cleanup_old_cache(self, days: int = 7):
        """Clean up expired search cache"""
        try:
            self.cursor.execute("""
                DELETE FROM knowledge_search_cache
                WHERE expires_at < CURRENT_TIMESTAMP
                OR created_at < datetime('now', ? || ' days')
            """, (f'-{days}',))
            
            self.connection.commit()
        except Exception as e:
            print(f"Error cleaning cache: {e}")
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()


# ========== CONVENIENCE FUNCTIONS ==========

def create_memory_system(db_path: str = DB_PATH) -> MemorySystem:
    """Factory function to create a memory system instance"""
    return MemorySystem(db_path)


def demonstrate_memory_system():
    """Demonstrate the memory system with example operations"""
    print("Initializing UniVerse Memory System...")
    system = MemorySystem()
    
    # Example: Store knowledge
    print("\n1. Storing knowledge...")
    k1 = system.store_knowledge(
        "Always validate user input before processing to prevent injection attacks",
        "security_insight",
        "agent_001",
        {"domain": "security", "risk_level": "high"}
    )
    
    k2 = system.store_knowledge(
        "Use connection pooling for database operations to improve performance",
        "optimization_pattern",
        "agent_002",
        {"domain": "database", "impact": "high"}
    )
    
    print(f"Stored knowledge: {k1}, {k2}")
    
    # Example: Link knowledge
    print("\n2. Creating knowledge relationships...")
    system.link_knowledge(k1, k2, "complements", 0.8)
    
    # Example: Search knowledge
    print("\n3. Searching knowledge semantically...")
    results = system.search_knowledge_semantic("How to improve database security", limit=5)
    print(f"Found {len(results)} relevant pieces of knowledge")
    
    # Example: Register skills
    print("\n4. Registering skills...")
    skill1 = system.register_skill(
        "input_validation",
        "Comprehensive input validation framework",
        "def validate(input): ...",
        "agent_001",
        tags=["security", "validation"]
    )
    
    print(f"Registered skill: {skill1}")
    
    # Example: Skill inheritance
    print("\n5. Agent inheriting skills...")
    system.inherit_skill(skill1, "agent_003")
    system.update_skill_performance(skill1, "agent_003", success=True)
    
    # Example: Learning session
    print("\n6. Starting learning session...")
    session = system.start_learning_session("agent_003", "task_failure", "task_123", "agent_001")
    system.record_learning_improvement(
        session,
        generated_skills=[skill1],
        improvements={"error_reduction": 0.3}
    )
    
    # Example: Performance tracking
    print("\n7. Recording performance...")
    system.record_agent_performance("agent_003", "success_rate", 0.95)
    system.record_agent_performance("agent_003", "avg_response_time", 1.2)
    
    # Show stats
    print("\n8. Memory System Statistics:")
    stats = system.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # Analytics
    print("\n9. Agent Analytics:")
    analytics = system.get_agent_analytics("agent_003")
    for metric, data in analytics.items():
        print(f"   {metric}: avg={data['average']:.2f}, min={data['min']:.2f}, max={data['max']:.2f}")
    
    system.close()


if __name__ == "__main__":
    demonstrate_memory_system()
