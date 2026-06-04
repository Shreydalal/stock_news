import os
import subprocess
import logging
from datetime import date
from pathlib import Path
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class GitService:
    def __init__(self, workspace_root: Optional[str] = None):
        # Default to parent directory of app (which is the workspace root)
        if workspace_root:
            self.workspace_root = Path(workspace_root).resolve()
        else:
            self.workspace_root = Path(__file__).resolve().parent.parent.parent

    def save_report_to_disk(self, report_date: date, content: str) -> Path:
        """Saves the report content into a structured path: reports/YYYY/MM/DD/report.md"""
        # Formulate path
        year = str(report_date.year)
        month = f"{report_date.month:02d}"
        day = f"{report_date.day:02d}"
        
        report_dir = self.workspace_root / "reports" / year / month / day
        report_dir.mkdir(parents=True, exist_ok=True)
        
        report_file = report_dir / "report.md"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(content)
            
        logger.info(f"Report saved to disk at {report_file}")
        return report_file

    def run_git_command(self, args: list) -> subprocess.CompletedProcess:
        """Runs a git command in the workspace directory."""
        # Use shell=True on Windows if git is in PATH
        shell = os.name == 'nt'
        return subprocess.run(
            args,
            cwd=str(self.workspace_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=shell,
            check=True
        )

    def commit_and_push_report(self, report_date: date, file_path: Path) -> bool:
        """Commits and pushes the generated report file."""
        try:
            # Check if directory is a git repository
            git_dir = self.workspace_root / ".git"
            if not git_dir.exists():
                logger.warning("Workspace root is not a git repository. Skipping git operations.")
                return False

            # Format relative path for git command
            rel_path = file_path.relative_to(self.workspace_root).as_posix()
            
            # Step 1: git add
            logger.info(f"Git: Adding {rel_path}")
            self.run_git_command(["git", "add", rel_path])

            # Ensure local git identity is configured to avoid runner failure
            try:
                self.run_git_command(["git", "config", "user.email"])
            except subprocess.CalledProcessError:
                logger.info("Git author config not found. Setting local git user.name and user.email.")
                self.run_git_command(["git", "config", "user.name", "github-actions[bot]"])
                self.run_git_command(["git", "config", "user.email", "actions@github.com"])

            # Step 2: git commit
            commit_msg = f"Daily market report {report_date}"
            logger.info(f"Git: Committing with message: '{commit_msg}'")
            try:
                self.run_git_command(["git", "commit", "-m", commit_msg])
            except subprocess.CalledProcessError as e:
                if "nothing to commit" in e.stdout or "nothing to commit" in e.stderr:
                    logger.info("Git: Nothing to commit (file has not changed).")
                    return True
                raise e

            # Step 3: git push
            if settings.GITHUB_TOKEN and settings.GITHUB_REPOSITORY:
                # Build authenticated push URL
                # Example: https://<token>@github.com/owner/repo.git
                push_url = f"https://x-access-token:{settings.GITHUB_TOKEN}@github.com/{settings.GITHUB_REPOSITORY}.git"
                logger.info(f"Git: Pushing to GitHub repository {settings.GITHUB_REPOSITORY} using GITHUB_TOKEN")
                self.run_git_command(["git", "push", push_url, "main"])
            else:
                logger.info("Git: Pushing to default origin main")
                try:
                    self.run_git_command(["git", "push", "origin", "main"])
                except Exception as e:
                    logger.warning(f"Git push failed (possibly due to missing credentials): {e}")
                    return False

            logger.info("Git: Successfully pushed report to GitHub.")
            return True

        except FileNotFoundError:
            logger.warning("Git executable not found in system path. Git operations skipped.")
            return False
        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: stdout: {e.stdout}, stderr: {e.stderr}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Unexpected error during git automation: {e}", exc_info=True)
            return False
