"""
Git-Backed History System - Time travel, rollback, and audit trail
Implements version control for agent states with git integration
"""

import os
import json
import hashlib
import subprocess
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3


class CommitType(Enum):
    """Type of commit"""
    STATE_SNAPSHOT = "state_snapshot"      # Regular state capture
    TASK_EXECUTION = "task_execution"      # Task completion
    AGENT_CONFIG = "agent_config"          # Configuration change
    EMERGENCY_CHECKPOINT = "emergency"     # Emergency backup
    ROLLBACK = "rollback"                  # Rollback operation
    MERGE = "merge"                        # Branch merge


class BranchType(Enum):
    """Git branch types"""
    MAIN = "main"                          # Production branch
    EXPERIMENT = "experiment"              # Experimental branch
    HOTFIX = "hotfix"                      # Hot fix branch
    RECOVERY = "recovery"                  # Recovery/rollback branch


@dataclass
class GitCommit:
    """Represents a git commit"""
    commit_id: str
    commit_hash: str
    message: str
    author: str
    timestamp: datetime
    parent_commit: Optional[str]
    branch: str
    commit_type: CommitType
    state_snapshot: Dict[str, Any]
    agent_id: Optional[str] = None
    execution_id: Optional[str] = None
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []

    def to_dict(self):
        return {
            "commit_id": self.commit_id,
            "commit_hash": self.commit_hash,
            "message": self.message,
            "author": self.author,
            "timestamp": self.timestamp.isoformat(),
            "parent_commit": self.parent_commit,
            "branch": self.branch,
            "commit_type": self.commit_type.value,
            "agent_id": self.agent_id,
            "execution_id": self.execution_id,
            "tags": self.tags
        }


@dataclass
class StateDiff:
    """Difference between two states"""
    from_commit: str
    to_commit: str
    timestamp: datetime
    additions: Dict[str, Any]      # New/modified keys
    deletions: Dict[str, Any]      # Removed keys
    modifications: Dict[str, Tuple[Any, Any]]  # Changed values (old -> new)

    def to_dict(self):
        return {
            "from_commit": self.from_commit,
            "to_commit": self.to_commit,
            "timestamp": self.timestamp.isoformat(),
            "additions": self.additions,
            "deletions": self.deletions,
            "modifications": self.modifications,
            "change_count": len(self.additions) + len(self.deletions) + len(self.modifications)
        }


class GitHistoryEngine:
    """Core git history engine"""

    def __init__(self, repo_path: str = "/tmp/agent_history_repo"):
        self.repo_path = repo_path
        self.commits = {}  # commit_hash -> GitCommit
        self.branches = {}  # branch_name -> latest_commit_hash
        self.tags = {}     # tag_name -> commit_hash
        self.current_branch = "main"
        self.current_commit = None
        self._init_repository()

    def _init_repository(self):
        """Initialize or open git repository"""
        os.makedirs(self.repo_path, exist_ok=True)
        
        # Initialize with main branch
        self.branches["main"] = None
        self.branches["experiment"] = None
        self.branches["hotfix"] = None
        self.branches["recovery"] = None

    def create_commit(self, author: str, message: str, state_snapshot: Dict,
                     commit_type: CommitType = CommitType.STATE_SNAPSHOT,
                     agent_id: str = None, execution_id: str = None,
                     parent_commit: str = None) -> GitCommit:
        """Create a new commit"""
        commit_id = str(uuid.uuid4())
        
        # Generate commit hash
        commit_hash = self._generate_commit_hash(
            message, author, str(state_snapshot)
        )

        # If no parent specified, use current commit
        if parent_commit is None:
            parent_commit = self.current_commit

        commit = GitCommit(
            commit_id=commit_id,
            commit_hash=commit_hash,
            message=message,
            author=author,
            timestamp=datetime.now(),
            parent_commit=parent_commit,
            branch=self.current_branch,
            commit_type=commit_type,
            state_snapshot=state_snapshot,
            agent_id=agent_id,
            execution_id=execution_id
        )

        # Store commit
        self.commits[commit_hash] = commit
        
        # Update branch pointer
        self.branches[self.current_branch] = commit_hash
        
        # Update current commit
        self.current_commit = commit_hash

        return commit

    def create_checkpoint(self, agent_id: str, state: Dict, 
                        reason: str = "Automatic checkpoint") -> GitCommit:
        """Create emergency checkpoint"""
        return self.create_commit(
            author="system",
            message=f"CHECKPOINT: {reason}",
            state_snapshot=state,
            commit_type=CommitType.EMERGENCY_CHECKPOINT,
            agent_id=agent_id
        )

    def get_commit(self, commit_hash: str) -> Optional[GitCommit]:
        """Retrieve a commit"""
        return self.commits.get(commit_hash)

    def get_current_state(self) -> Optional[Dict]:
        """Get current state snapshot"""
        if self.current_commit:
            commit = self.commits.get(self.current_commit)
            if commit:
                return commit.state_snapshot
        return None

    def calculate_state_diff(self, from_hash: str, to_hash: str) -> Optional[StateDiff]:
        """Calculate difference between two states"""
        from_commit = self.commits.get(from_hash)
        to_commit = self.commits.get(to_hash)

        if not from_commit or not to_commit:
            return None

        from_state = from_commit.state_snapshot or {}
        to_state = to_commit.state_snapshot or {}

        additions = {}
        deletions = {}
        modifications = {}

        # Find additions and modifications
        for key, value in to_state.items():
            if key not in from_state:
                additions[key] = value
            elif from_state[key] != value:
                modifications[key] = (from_state[key], value)

        # Find deletions
        for key, value in from_state.items():
            if key not in to_state:
                deletions[key] = value

        return StateDiff(
            from_commit=from_hash,
            to_commit=to_hash,
            timestamp=datetime.now(),
            additions=additions,
            deletions=deletions,
            modifications=modifications
        )

    def rollback_to_commit(self, commit_hash: str, reason: str = "Manual rollback") -> Tuple[bool, str]:
        """Rollback to a previous commit"""
        target_commit = self.commits.get(commit_hash)

        if not target_commit:
            return False, f"Commit not found: {commit_hash}"

        # Create rollback commit
        rollback_message = f"ROLLBACK to {commit_hash[:8]}: {reason}"
        rollback_commit = self.create_commit(
            author="system",
            message=rollback_message,
            state_snapshot=target_commit.state_snapshot,
            commit_type=CommitType.ROLLBACK,
            parent_commit=commit_hash
        )

        return True, rollback_commit.commit_hash

    def create_branch(self, branch_name: str, branch_type: BranchType = BranchType.EXPERIMENT,
                     from_commit: str = None) -> Tuple[bool, str]:
        """Create a new branch"""
        if branch_name in self.branches:
            return False, f"Branch already exists: {branch_name}"

        if from_commit is None:
            from_commit = self.current_commit

        self.branches[branch_name] = from_commit
        return True, f"Branch created: {branch_name}"

    def switch_branch(self, branch_name: str) -> Tuple[bool, str]:
        """Switch to a different branch"""
        if branch_name not in self.branches:
            return False, f"Branch not found: {branch_name}"

        self.current_branch = branch_name
        self.current_commit = self.branches[branch_name]
        return True, f"Switched to branch: {branch_name}"

    def merge_branch(self, source_branch: str, target_branch: str = None,
                    author: str = "system") -> Tuple[bool, str]:
        """Merge one branch into another"""
        if target_branch is None:
            target_branch = "main"

        if source_branch not in self.branches:
            return False, f"Source branch not found: {source_branch}"

        if target_branch not in self.branches:
            return False, f"Target branch not found: {target_branch}"

        source_commit_hash = self.branches[source_branch]
        target_commit_hash = self.branches[target_branch]

        if not source_commit_hash:
            return False, "Source branch is empty"

        # Switch to target branch
        self.switch_branch(target_branch)

        # Create merge commit
        source_commit = self.commits.get(source_commit_hash)
        merge_message = f"MERGE: {source_branch} -> {target_branch}"

        self.create_commit(
            author=author,
            message=merge_message,
            state_snapshot=source_commit.state_snapshot if source_commit else {},
            commit_type=CommitType.MERGE,
            parent_commit=target_commit_hash
        )

        return True, f"Merged {source_branch} into {target_branch}"

    def tag_commit(self, commit_hash: str, tag_name: str) -> Tuple[bool, str]:
        """Tag a commit"""
        if commit_hash not in self.commits:
            return False, f"Commit not found: {commit_hash}"

        self.tags[tag_name] = commit_hash
        return True, f"Tagged commit: {tag_name}"

    def get_commit_history(self, limit: int = 50, 
                          branch: str = None) -> List[Dict]:
        """Get commit history"""
        history = []
        current = self.branches.get(branch or self.current_branch)

        while current and len(history) < limit:
            commit = self.commits.get(current)
            if commit:
                history.append(commit.to_dict())
                current = commit.parent_commit
            else:
                break

        return history

    def get_branch_info(self) -> Dict[str, Any]:
        """Get information about all branches"""
        return {
            "current_branch": self.current_branch,
            "branches": {
                name: {
                    "current_commit": commit_hash,
                    "commit_count": self._count_commits_in_branch(name)
                }
                for name, commit_hash in self.branches.items()
            },
            "total_commits": len(self.commits)
        }

    def _count_commits_in_branch(self, branch_name: str) -> int:
        """Count commits in a branch"""
        count = 0
        current = self.branches.get(branch_name)

        while current:
            commit = self.commits.get(current)
            if commit:
                count += 1
                current = commit.parent_commit
            else:
                break

        return count

    @staticmethod
    def _generate_commit_hash(message: str, author: str, 
                             state_str: str) -> str:
        """Generate commit hash"""
        content = f"{message}:{author}:{state_str}:{datetime.now().isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()


class HistoryTimeTravel:
    """Time travel functionality for state inspection"""

    def __init__(self, git_engine: GitHistoryEngine):
        self.git_engine = git_engine

    def get_state_at_time(self, timestamp: datetime) -> Optional[Dict]:
        """Get state at a specific point in time"""
        commits = sorted(
            self.git_engine.commits.values(),
            key=lambda c: c.timestamp,
            reverse=True
        )

        for commit in commits:
            if commit.timestamp <= timestamp:
                return commit.state_snapshot

        return None

    def get_state_change_timeline(self, start_time: datetime = None,
                                 end_time: datetime = None,
                                 limit: int = 50) -> List[Dict]:
        """Get timeline of state changes"""
        commits = sorted(
            self.git_engine.commits.values(),
            key=lambda c: c.timestamp
        )

        timeline = []
        for commit in commits:
            if start_time and commit.timestamp < start_time:
                continue
            if end_time and commit.timestamp > end_time:
                continue

            timeline.append({
                "timestamp": commit.timestamp.isoformat(),
                "commit_hash": commit.commit_hash,
                "message": commit.message,
                "commit_type": commit.commit_type.value,
                "agent_id": commit.agent_id
            })

        return timeline[-limit:]

    def compare_states(self, timestamp1: datetime,
                      timestamp2: datetime) -> Optional[StateDiff]:
        """Compare states at two points in time"""
        commit1 = self._find_commit_at_time(timestamp1)
        commit2 = self._find_commit_at_time(timestamp2)

        if not commit1 or not commit2:
            return None

        return self.git_engine.calculate_state_diff(
            commit1.commit_hash,
            commit2.commit_hash
        )

    def _find_commit_at_time(self, timestamp: datetime) -> Optional[GitCommit]:
        """Find commit closest to timestamp"""
        commits = sorted(
            self.git_engine.commits.values(),
            key=lambda c: abs((c.timestamp - timestamp).total_seconds())
        )
        return commits[0] if commits else None


class AuditTrail:
    """Immutable audit trail with git backing"""

    def __init__(self, git_engine: GitHistoryEngine):
        self.git_engine = git_engine

    def log_action(self, action: str, agent_id: str, details: Dict,
                  execution_id: str = None) -> str:
        """Log an action to the audit trail"""
        commit = self.git_engine.create_commit(
            author=agent_id,
            message=f"ACTION: {action}",
            state_snapshot=details,
            commit_type=CommitType.TASK_EXECUTION,
            agent_id=agent_id,
            execution_id=execution_id
        )
        return commit.commit_hash

    def get_audit_trail(self, agent_id: str = None, 
                       limit: int = 100) -> List[Dict]:
        """Retrieve audit trail entries"""
        commits = []
        
        for commit in self.git_engine.commits.values():
            if agent_id and commit.agent_id != agent_id:
                continue
            commits.append(commit)

        # Sort by timestamp, newest first
        commits.sort(key=lambda c: c.timestamp, reverse=True)

        return [c.to_dict() for c in commits[:limit]]

    def verify_integrity(self) -> Dict[str, Any]:
        """Verify audit trail integrity"""
        total_commits = len(self.git_engine.commits)
        integrity_ok = True
        
        # Check parent-child consistency
        for commit in self.git_engine.commits.values():
            if commit.parent_commit:
                if commit.parent_commit not in self.git_engine.commits:
                    integrity_ok = False
                    break

        return {
            "integrity_ok": integrity_ok,
            "total_commits": total_commits,
            "verified_at": datetime.now().isoformat()
        }

    def export_audit_trail(self, filepath: str) -> bool:
        """Export audit trail to file"""
        try:
            trail = self.get_audit_trail(limit=10000)
            with open(filepath, 'w') as f:
                json.dump(trail, f, indent=2)
            return True
        except Exception as e:
            print(f"Export failed: {e}")
            return False
