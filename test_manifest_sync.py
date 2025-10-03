#!/usr/bin/env python3
"""
E2E Test for Manifest-based Sync with Mixed Git State

This test simulates a manifest-based synchronization process where files
are in various git states (modified, staged, untracked, ignored, etc.)
"""

import os
import json
import shutil
import tempfile
import subprocess
import unittest
from pathlib import Path
from typing import Dict, List, Any


class ManifestSyncTest(unittest.TestCase):
    """Test manifest-based sync operations with mixed git states"""

    def setUp(self):
        """Set up a temporary git repository for testing"""
        self.test_dir = tempfile.mkdtemp(prefix='manifest_sync_test_')
        self.repo_path = Path(self.test_dir) / 'test_repo'
        self.repo_path.mkdir()

        # Initialize git repo
        self._run_git(['init'])
        self._run_git(['config', 'user.email', 'test@example.com'])
        self._run_git(['config', 'user.name', 'Test User'])

        # Create initial manifest structure
        self.manifest_path = self.repo_path / 'manifest.json'
        self.initial_manifest = {
            "version": "1.0.0",
            "files": {
                "src/main.py": {"hash": "abc123", "size": 100},
                "src/utils.py": {"hash": "def456", "size": 200},
                "config/settings.json": {"hash": "ghi789", "size": 50},
                "docs/README.md": {"hash": "jkl012", "size": 300}
            },
            "dependencies": {
                "flask": "2.0.0",
                "requests": "2.28.0"
            }
        }

    def tearDown(self):
        """Clean up temporary directory"""
        if Path(self.test_dir).exists():
            shutil.rmtree(self.test_dir)

    def _run_git(self, args: List[str]) -> subprocess.CompletedProcess:
        """Run a git command in the test repository"""
        return subprocess.run(
            ['git'] + args,
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=False
        )

    def _create_file(self, relative_path: str, content: str = None) -> Path:
        """Create a file in the test repository"""
        file_path = self.repo_path / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)

        if content is None:
            content = f"Content of {relative_path}"

        file_path.write_text(content)
        return file_path

    def _write_manifest(self, manifest: Dict[str, Any]) -> None:
        """Write manifest to file"""
        self.manifest_path.write_text(json.dumps(manifest, indent=2))

    def _read_manifest(self) -> Dict[str, Any]:
        """Read manifest from file"""
        if self.manifest_path.exists():
            return json.loads(self.manifest_path.read_text())
        return {}

    def _sync_manifest(self, strategy: str = 'merge') -> Dict[str, Any]:
        """
        Simulate manifest sync operation

        Args:
            strategy: Sync strategy ('merge', 'overwrite', 'selective')

        Returns:
            Sync result with status and changes
        """
        result = {
            'status': 'success',
            'strategy': strategy,
            'changes': {
                'added': [],
                'modified': [],
                'deleted': [],
                'conflicts': []
            }
        }

        current_manifest = self._read_manifest()
        git_status = self._run_git(['status', '--porcelain'])

        # Parse git status
        git_files = {}
        for line in git_status.stdout.splitlines():
            if line:
                status = line[:2]
                filename = line[3:]
                git_files[filename] = status.strip()

        # Simulate sync based on strategy
        if strategy == 'merge':
            # Merge changes preserving local modifications
            for file_path in git_files:
                if 'M' in git_files[file_path]:
                    result['changes']['modified'].append(file_path)
                elif 'A' in git_files[file_path]:
                    result['changes']['added'].append(file_path)
                elif 'D' in git_files[file_path]:
                    result['changes']['deleted'].append(file_path)
                elif '??' == git_files[file_path]:
                    result['changes']['added'].append(file_path)

        elif strategy == 'overwrite':
            # Overwrite local changes with manifest
            for file_path in current_manifest.get('files', {}):
                if file_path in git_files:
                    result['changes']['modified'].append(file_path)
                else:
                    result['changes']['added'].append(file_path)

        elif strategy == 'selective':
            # Selective sync based on file patterns
            for file_path in git_files:
                if file_path.endswith('.py'):
                    result['changes']['modified'].append(file_path)

        return result

    def test_clean_state_sync(self):
        """Test sync with clean git state"""
        # Create initial files and commit
        self._write_manifest(self.initial_manifest)
        for file_path in self.initial_manifest['files']:
            self._create_file(file_path)

        self._run_git(['add', '.'])
        self._run_git(['commit', '-m', 'Initial commit'])

        # Verify clean state
        status = self._run_git(['status', '--porcelain'])
        self.assertEqual(status.stdout.strip(), '', "Repository should be clean")

        # Perform sync
        result = self._sync_manifest('merge')
        self.assertEqual(result['status'], 'success')
        self.assertEqual(len(result['changes']['added']), 0)
        self.assertEqual(len(result['changes']['modified']), 0)

    def test_modified_files_sync(self):
        """Test sync with modified files"""
        # Setup initial state
        self._write_manifest(self.initial_manifest)
        for file_path in self.initial_manifest['files']:
            self._create_file(file_path)

        self._run_git(['add', '.'])
        self._run_git(['commit', '-m', 'Initial commit'])

        # Modify files
        self._create_file('src/main.py', 'Modified content')
        self._create_file('config/settings.json', '{"modified": true}')

        # Perform sync
        result = self._sync_manifest('merge')
        self.assertEqual(result['status'], 'success')
        self.assertIn('src/main.py', result['changes']['modified'])
        self.assertIn('config/settings.json', result['changes']['modified'])

    def test_staged_files_sync(self):
        """Test sync with staged files"""
        # Setup initial state
        self._write_manifest(self.initial_manifest)
        for file_path in self.initial_manifest['files']:
            self._create_file(file_path)

        self._run_git(['add', '.'])
        self._run_git(['commit', '-m', 'Initial commit'])

        # Modify and stage files
        self._create_file('src/utils.py', 'Staged changes')
        self._run_git(['add', 'src/utils.py'])

        # Perform sync
        result = self._sync_manifest('merge')
        self.assertEqual(result['status'], 'success')
        self.assertIn('src/utils.py', result['changes']['modified'])

    def test_untracked_files_sync(self):
        """Test sync with untracked files"""
        # Setup initial state
        self._write_manifest(self.initial_manifest)
        for file_path in self.initial_manifest['files']:
            self._create_file(file_path)

        self._run_git(['add', '.'])
        self._run_git(['commit', '-m', 'Initial commit'])

        # Create untracked files
        self._create_file('src/new_feature.py')
        self._create_file('tests/test_new.py')

        # Perform sync
        result = self._sync_manifest('merge')
        self.assertEqual(result['status'], 'success')
        # Check that the new files are detected
        # Git may show directory as 'tests/' instead of individual files
        added_files = ' '.join(result['changes']['added'])
        self.assertTrue(
            'src/new_feature.py' in result['changes']['added'],
            f"Expected 'src/new_feature.py' in {result['changes']['added']}"
        )
        self.assertTrue(
            'tests/test_new.py' in result['changes']['added'] or
            'tests/' in result['changes']['added'],
            f"Expected 'tests/test_new.py' or 'tests/' in {result['changes']['added']}"
        )

    def test_mixed_state_sync(self):
        """Test sync with mixed git states"""
        # Setup initial state
        self._write_manifest(self.initial_manifest)
        for file_path in self.initial_manifest['files']:
            self._create_file(file_path)

        self._run_git(['add', '.'])
        self._run_git(['commit', '-m', 'Initial commit'])

        # Create mixed states
        # 1. Modified file
        self._create_file('src/main.py', 'Modified in working directory')

        # 2. Staged modification
        self._create_file('src/utils.py', 'Staged modification')
        self._run_git(['add', 'src/utils.py'])

        # 3. Untracked file
        self._create_file('src/untracked.py')

        # 4. Deleted file
        (self.repo_path / 'docs/README.md').unlink()

        # 5. Staged new file
        self._create_file('src/staged_new.py')
        self._run_git(['add', 'src/staged_new.py'])

        # Perform sync
        result = self._sync_manifest('merge')

        # Verify results
        self.assertEqual(result['status'], 'success')
        self.assertIn('src/main.py', result['changes']['modified'])
        self.assertIn('src/utils.py', result['changes']['modified'])
        self.assertIn('src/untracked.py', result['changes']['added'])
        self.assertIn('docs/README.md', result['changes']['deleted'])
        self.assertIn('src/staged_new.py', result['changes']['added'])

    def test_conflict_detection(self):
        """Test conflict detection during sync"""
        # Setup initial state
        self._write_manifest(self.initial_manifest)
        for file_path in self.initial_manifest['files']:
            self._create_file(file_path)

        self._run_git(['add', '.'])
        self._run_git(['commit', '-m', 'Initial commit'])

        # Create a conflicting scenario
        # Modify file locally
        self._create_file('src/main.py', 'Local changes')

        # Update manifest with different content expectation
        updated_manifest = self.initial_manifest.copy()
        updated_manifest['files']['src/main.py']['hash'] = 'different_hash'
        updated_manifest['files']['src/main.py']['size'] = 500
        self._write_manifest(updated_manifest)

        # Stage the manifest change
        self._run_git(['add', 'manifest.json'])

        # Verify mixed state exists
        status = self._run_git(['status', '--porcelain'])
        # Git status shows staged files with 'M ' format
        self.assertIn('M  manifest.json', status.stdout)
        self.assertIn(' M src/main.py', status.stdout)

    def test_ignored_files_handling(self):
        """Test handling of gitignored files during sync"""
        # Create .gitignore
        gitignore_content = """
*.pyc
__pycache__/
.env
build/
dist/
"""
        self._create_file('.gitignore', gitignore_content)

        # Setup initial state
        self._write_manifest(self.initial_manifest)
        for file_path in self.initial_manifest['files']:
            self._create_file(file_path)

        self._run_git(['add', '.'])
        self._run_git(['commit', '-m', 'Initial commit with gitignore'])

        # Create ignored files
        self._create_file('src/__pycache__/main.pyc')
        self._create_file('.env', 'SECRET_KEY=test')
        self._create_file('build/output.txt')

        # Create non-ignored file
        self._create_file('src/new_module.py')

        # Perform sync
        result = self._sync_manifest('merge')

        # Verify ignored files are not included
        self.assertEqual(result['status'], 'success')
        self.assertIn('src/new_module.py', result['changes']['added'])
        self.assertNotIn('.env', result['changes']['added'])
        self.assertNotIn('build/output.txt', result['changes']['added'])

    def test_sync_strategies(self):
        """Test different sync strategies"""
        # Setup initial state
        self._write_manifest(self.initial_manifest)
        for file_path in self.initial_manifest['files']:
            self._create_file(file_path)

        self._run_git(['add', '.'])
        self._run_git(['commit', '-m', 'Initial commit'])

        # Create various changes
        self._create_file('src/main.py', 'Modified')
        self._create_file('src/new.py')

        # Test merge strategy
        merge_result = self._sync_manifest('merge')
        self.assertEqual(merge_result['strategy'], 'merge')
        self.assertGreater(len(merge_result['changes']['modified']), 0)

        # Test overwrite strategy
        overwrite_result = self._sync_manifest('overwrite')
        self.assertEqual(overwrite_result['strategy'], 'overwrite')

        # Test selective strategy
        selective_result = self._sync_manifest('selective')
        self.assertEqual(selective_result['strategy'], 'selective')

    def test_partial_staged_changes(self):
        """Test sync with partial staged changes"""
        # Setup initial state
        self._write_manifest(self.initial_manifest)
        for file_path in self.initial_manifest['files']:
            self._create_file(file_path)

        self._run_git(['add', '.'])
        self._run_git(['commit', '-m', 'Initial commit'])

        # Make changes to a file
        self._create_file('src/main.py', 'First change\nSecond change\nThird change')

        # Stage the file
        self._run_git(['add', 'src/main.py'])

        # Make additional unstaged changes
        self._create_file('src/main.py', 'First change\nModified second change\nThird change\nFourth change')

        # Verify file has both staged and unstaged changes
        status = self._run_git(['status', '--porcelain'])
        self.assertIn('MM src/main.py', status.stdout)

        # Perform sync
        result = self._sync_manifest('merge')
        self.assertEqual(result['status'], 'success')
        self.assertIn('src/main.py', result['changes']['modified'])

    def test_renamed_files_sync(self):
        """Test sync with renamed files"""
        # Setup initial state
        self._write_manifest(self.initial_manifest)
        for file_path in self.initial_manifest['files']:
            self._create_file(file_path)

        self._run_git(['add', '.'])
        self._run_git(['commit', '-m', 'Initial commit'])

        # Rename a file using git mv
        self._run_git(['mv', 'src/utils.py', 'src/utilities.py'])

        # Verify rename is detected
        status = self._run_git(['status', '--porcelain'])
        self.assertIn('R', status.stdout)

        # Perform sync
        result = self._sync_manifest('merge')
        self.assertEqual(result['status'], 'success')

    def test_submodule_handling(self):
        """Test handling of git submodules during sync"""
        # This is a placeholder for submodule testing
        # In a real scenario, you'd add a submodule and test its behavior
        self.skipTest("Submodule testing requires external repository")

    def test_large_manifest_sync(self):
        """Test sync with large number of files"""
        # Create a large manifest
        large_manifest = {
            "version": "1.0.0",
            "files": {}
        }

        # Add many files to manifest
        for i in range(100):
            file_path = f"src/module_{i}/file_{i}.py"
            large_manifest['files'][file_path] = {
                "hash": f"hash_{i}",
                "size": 100 + i
            }

        self._write_manifest(large_manifest)

        # Create all files
        for file_path in large_manifest['files']:
            self._create_file(file_path)

        self._run_git(['add', '.'])
        self._run_git(['commit', '-m', 'Large manifest commit'])

        # Modify some files
        for i in range(0, 10):
            file_path = f"src/module_{i}/file_{i}.py"
            self._create_file(file_path, f"Modified content {i}")

        # Perform sync
        result = self._sync_manifest('merge')
        self.assertEqual(result['status'], 'success')
        self.assertEqual(len(result['changes']['modified']), 10)


def run_tests():
    """Run the test suite"""
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(ManifestSyncTest)

    # Run tests with verbosity
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Return success status
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    exit(0 if success else 1)