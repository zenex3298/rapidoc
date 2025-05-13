import os
import shutil
import logging
import subprocess
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("file_organizer.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("file_organizer")

# Core file and directory utility functions
def list_recursively(root_directory):
    """List all paths (files and directories) recursively under the root directory."""
    all_paths = []
    for dirpath, dirnames, filenames in os.walk(root_directory):
        # Add directories
        for dirname in dirnames:
            all_paths.append(os.path.join(dirpath, dirname))
        # Add files
        for filename in filenames:
            all_paths.append(os.path.join(dirpath, filename))
    return all_paths

def list_files(directory):
    """List all files in the specified directory (non-recursive)."""
    if not os.path.isdir(directory):
        logger.error(f"The path {directory} is not a directory")
        return []
    
    return [os.path.join(directory, f) for f in os.listdir(directory) 
            if os.path.isfile(os.path.join(directory, f))]

def is_essential_root_file(file_path):
    """Determine if a file is essential and should remain in the root directory."""
    essential_files = [
        'requirements.txt',
        'alembic.ini',
        'run_dev.sh',
        'app.json',
        'Procfile',
        'heroku.yml',
        'readme.md',
        'CLAUDE.md',
        'sample.env',
        '.env',
        'init_db.py',
        'db_manage.py',
        '.gitignore',
        'API_DOCUMENTATION.md',
        'DATABASE_SCHEMA.md'
    ]
    
    filename = os.path.basename(file_path).lower()
    return filename in [f.lower() for f in essential_files]

def choose_subdirectory_for(file_path):
    """Determine the appropriate subdirectory for a given file."""
    filename = os.path.basename(file_path).lower()
    
    # Test files
    if filename.startswith('test_'):
        return os.path.join(os.path.dirname(file_path), 'tests')
    
    # Scripts
    if filename.endswith('.sh') or filename.endswith('.py') and 'script' in filename:
        return os.path.join(os.path.dirname(file_path), 'app/scripts')
    
    # Documentation
    if filename.endswith('.md') or filename.endswith('.txt'):
        return os.path.join(os.path.dirname(file_path), 'docs')
    
    # Default: move to "utils" directory
    return os.path.join(os.path.dirname(file_path), 'app/utils')

def is_unnecessary_file(file_path):
    """Identify unnecessary files that can be safely removed."""
    unnecessary_patterns = [
        r'\.pyc$',
        r'\.pyo$',
        r'__pycache__',
        r'\.DS_Store',
        r'\.idea',
        r'\.vscode',
        r'\.git/objects',
        r'~$',
        r'Thumbs\.db$'
    ]
    
    for pattern in unnecessary_patterns:
        if re.search(pattern, file_path):
            return True
    
    return False

def log(message):
    """Log a message to the console and log file."""
    logger.info(message)

def run_all_tests():
    """Run all tests for the project."""
    try:
        # Check if test script exists
        test_script = os.path.join('tests', 'scripts', 'run_tests.sh')
        if os.path.exists(test_script):
            result = subprocess.run(['bash', test_script], 
                                    capture_output=True, 
                                    text=True)
            return {
                'success': result.returncode == 0,
                'output': result.stdout,
                'error': result.stderr,
                'returncode': result.returncode
            }
        else:
            # Fallback to direct Python test execution
            test_dir = 'tests'
            if not os.path.exists(test_dir):
                return {'success': False, 'error': f"Test directory {test_dir} not found"}
            
            test_files = [f for f in os.listdir(test_dir) 
                         if f.startswith('test_') and f.endswith('.py')]
            
            all_results = []
            for test_file in test_files:
                test_path = os.path.join(test_dir, test_file)
                result = subprocess.run(['python', test_path], 
                                        capture_output=True, 
                                        text=True)
                all_results.append({
                    'file': test_file,
                    'success': result.returncode == 0,
                    'output': result.stdout,
                    'error': result.stderr,
                    'returncode': result.returncode
                })
            
            # Consider the overall run successful if all tests passed
            overall_success = all(r['success'] for r in all_results)
            return {
                'success': overall_success,
                'individual_results': all_results
            }
            
    except Exception as e:
        return {'success': False, 'error': str(e)}

def all_tests_pass():
    """Check if all tests pass."""
    results = run_all_tests()
    return results.get('success', False)

def update_readme_file(root_directory):
    """Update the readme file with the new directory structure."""
    readme_path = os.path.join(root_directory, 'readme.md')
    if not os.path.exists(readme_path):
        logger.warning(f"README file not found at {readme_path}")
        return False
    
    try:
        # Generate directory structure
        structure_lines = []
        structure_lines.append("## Directory Structure\n")
        
        # Get all directories and files
        structure = {}
        for root, dirs, files in os.walk(root_directory):
            # Skip certain directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != 'venv' and d != '__pycache__']
            
            # Calculate relative path
            rel_path = os.path.relpath(root, root_directory)
            if rel_path == '.':
                # Root directory
                structure['.'] = [f for f in files if not f.startswith('.')]
            else:
                # Subdirectories
                structure[rel_path] = [f for f in files if not f.startswith('.')]
        
        # Build the structure string
        for path in sorted(structure.keys()):
            indent = '  ' * (path.count(os.sep) + (0 if path == '.' else 1))
            if path == '.':
                structure_lines.append(f"- /")
            else:
                structure_lines.append(f"{indent}- {os.path.basename(path)}/")
            
            file_indent = indent + '  '
            for file in sorted(structure[path]):
                structure_lines.append(f"{file_indent}- {file}")
        
        # Read existing README
        with open(readme_path, 'r') as f:
            content = f.read()
        
        # Check if structure section already exists
        structure_pattern = r'## Directory Structure\s+.*?(?=^##|\Z)'
        if re.search(structure_pattern, content, re.DOTALL | re.MULTILINE):
            # Replace existing structure section
            new_content = re.sub(
                structure_pattern,
                '\n'.join(structure_lines),
                content,
                flags=re.DOTALL | re.MULTILINE
            )
        else:
            # Add structure section at the end
            new_content = content + '\n\n' + '\n'.join(structure_lines)
        
        # Write updated README
        with open(readme_path, 'w') as f:
            f.write(new_content)
        
        return True
        
    except Exception as e:
        logger.error(f"Error updating README: {str(e)}")
        return False

def organize_and_test(root_directory):
    """
    Organize files in the project directory and run tests to ensure everything works.
    
    Args:
        root_directory: The root directory of the project
        
    Returns:
        dict: Results of the organization and testing process
    """
    logger.info(f"Starting organization process for {root_directory}")
    results = {
        'moved_files': [],
        'deleted_files': [],
        'test_results': [],
        'errors': []
    }
    
    try:
        # Step 1: List all directories, subdirectories, and files
        logger.info("Listing all paths recursively")
        all_paths = list_recursively(root_directory)
        
        # Step 2: Get all files in the root directory
        logger.info("Getting all files in root directory")
        root_files = list_files(root_directory)
        
        # Step 3: Move non-essential root files to appropriate subdirectories
        logger.info("Moving non-essential root files")
        for file in root_files:
            if not is_essential_root_file(file):
                target_dir = choose_subdirectory_for(file)
                logger.info(f"Moving {file} to {target_dir}")
                
                # Create target directory if it doesn't exist
                if not os.path.exists(target_dir):
                    os.makedirs(target_dir, exist_ok=True)
                
                # Move file
                target_path = os.path.join(target_dir, os.path.basename(file))
                shutil.move(file, target_path)
                results['moved_files'].append({'from': file, 'to': target_path})
                
                # Run tests after each move
                test_result = run_all_tests()
                results['test_results'].append({
                    'action': f"Moved {file} to {target_path}",
                    'result': test_result
                })
                log(f"Test result after moving {file}: {test_result['success']}")
        
        # Step 4: Clean non-essential files from subdirectories
        logger.info("Cleaning non-essential files from subdirectories")
        for path in all_paths:
            if os.path.isdir(path):
                sub_files = list_files(path)
                for file in sub_files:
                    if is_unnecessary_file(file):
                        logger.info(f"Deleting unnecessary file: {file}")
                        os.remove(file)
                        results['deleted_files'].append(file)
                        
                        # Run tests after each deletion
                        test_result = run_all_tests()
                        results['test_results'].append({
                            'action': f"Deleted {file}",
                            'result': test_result
                        })
                        log(f"Test result after deleting {file}: {test_result['success']}")
        
        # Step 5: Final test check
        logger.info("Running final test check")
        final_test_result = run_all_tests()
        results['final_test_result'] = final_test_result
        log(f"Final test result: {final_test_result['success']}")
        
        # Step 6: Confirm all files cleaned from root
        logger.info("Confirming all non-essential files removed from root")
        remaining_root_files = list_files(root_directory)
        non_essential_remaining = []
        for file in remaining_root_files:
            if not is_essential_root_file(file):
                non_essential_remaining.append(file)
                logger.warning(f"Non-essential file still in root: {file}")
        
        if non_essential_remaining:
            error_message = f"Non-essential files still in root: {', '.join(non_essential_remaining)}"
            results['errors'].append(error_message)
            logger.error(error_message)
        
        # Step 7: Update ReadMe.md with new file directory
        if all_tests_pass():
            logger.info("Updating README file with new directory structure")
            readme_updated = update_readme_file(root_directory)
            if readme_updated:
                logger.info("README file updated successfully")
            else:
                error_message = "Failed to update README file"
                results['errors'].append(error_message)
                logger.error(error_message)
    
    except Exception as e:
        error_message = f"Error during organization process: {str(e)}"
        results['errors'].append(error_message)
        logger.error(error_message)
    
    logger.info("Organization process completed")
    return results