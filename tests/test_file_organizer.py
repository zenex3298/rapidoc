#!/usr/bin/env python3
"""
Test script for the file_organizer module.
This shows how to use the organize_and_test function and displays the results.
"""

import os
import json
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.utils.file_organizer import organize_and_test

# Create a modified version that skips tests for faster execution
def organize_without_tests(root_directory):
    """Modified version of organize_and_test that skips running tests after each change"""
    from app.utils.file_organizer import (
        list_recursively, list_files, is_essential_root_file,
        choose_subdirectory_for, is_unnecessary_file, log
    )
    
    log(f"Starting organization process for {root_directory} (skipping tests)")
    results = {
        'moved_files': [],
        'deleted_files': [],
        'test_results': [],
        'errors': []
    }
    
    try:
        # Step 1: List all directories, subdirectories, and files
        log("Listing all paths recursively")
        all_paths = list_recursively(root_directory)
        
        # Step 2: Get all files in the root directory
        log("Getting all files in root directory")
        root_files = list_files(root_directory)
        
        # Step 3: Move non-essential root files to appropriate subdirectories
        log("Moving non-essential root files")
        for file in root_files:
            if not is_essential_root_file(file):
                target_dir = choose_subdirectory_for(file)
                log(f"Moving {file} to {target_dir}")
                
                # Create target directory if it doesn't exist
                if not os.path.exists(target_dir):
                    os.makedirs(target_dir, exist_ok=True)
                
                # Move file
                target_path = os.path.join(target_dir, os.path.basename(file))
                os.rename(file, target_path)
                results['moved_files'].append({'from': file, 'to': target_path})
        
        # Step 4: Clean non-essential files from subdirectories
        log("Cleaning non-essential files from subdirectories")
        for path in all_paths:
            if os.path.isdir(path):
                sub_files = list_files(path)
                for file in sub_files:
                    if is_unnecessary_file(file):
                        log(f"Deleting unnecessary file: {file}")
                        os.remove(file)
                        results['deleted_files'].append(file)
        
        # Step 6: Confirm all files cleaned from root
        log("Confirming all non-essential files removed from root")
        remaining_root_files = list_files(root_directory)
        non_essential_remaining = []
        for file in remaining_root_files:
            if not is_essential_root_file(file):
                non_essential_remaining.append(file)
                log(f"Non-essential file still in root: {file}")
        
        if non_essential_remaining:
            error_message = f"Non-essential files still in root: {', '.join(non_essential_remaining)}"
            results['errors'].append(error_message)
            log(error_message)
    
    except Exception as e:
        error_message = f"Error during organization process: {str(e)}"
        results['errors'].append(error_message)
        log(error_message)
    
    log("Organization process completed")
    return results

def main():
    """Run the file organizer on the current directory."""
    # Get the project root directory (current working directory)
    root_dir = os.getcwd()
    
    # Check for --skip-tests flag
    skip_tests = "--skip-tests" in sys.argv
    
    print(f"Starting organization of project directory: {root_dir}")
    if skip_tests:
        print("Running without tests for faster execution.")
    else:
        print("This will organize files and run tests after each operation.")
    print("------------------------------------------------------------")
    
    # Run the organization process
    if skip_tests:
        results = organize_without_tests(root_dir)
    else:
        results = organize_and_test(root_dir)
    
    # Display results
    print("\nOrganization completed. Results:")
    print("================================")
    
    # Files moved
    print(f"\n{len(results['moved_files'])} files were moved:")
    for move in results['moved_files']:
        print(f"  - {move['from']} → {move['to']}")
    
    # Files deleted
    print(f"\n{len(results['deleted_files'])} unnecessary files were deleted:")
    for file in results['deleted_files']:
        print(f"  - {file}")
    
    # Test results (summarized) - only if tests were run
    if not skip_tests:
        successful_tests = sum(1 for test in results['test_results'] if test['result']['success'])
        print(f"\nTests: {successful_tests} successful out of {len(results['test_results'])} runs")
        
        # Final test result
        if results.get('final_test_result', {}).get('success'):
            print("\nFinal test run: SUCCESS")
        else:
            print("\nFinal test run: FAILED")
            if 'error' in results.get('final_test_result', {}):
                print(f"Error: {results['final_test_result']['error']}")
    
    # Any errors
    if results['errors']:
        print("\nErrors encountered during organization:")
        for error in results['errors']:
            print(f"  - {error}")
    else:
        print("\nNo errors encountered during organization.")
    
    # Save detailed results to file
    with open('file_organizer_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    print("\nDetailed results saved to file_organizer_results.json")

if __name__ == "__main__":
    main()