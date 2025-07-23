# Implementation Plan

- [x] 1. Modify the load_decision_trees function to use filenames as display names

  - Open the visualization/app.py file
  - Locate the load_decision_trees() function
  - Change the display_name assignment from descriptive text to filename
  - Ensure the function still returns all required metadata for filtering
  - _Requirements: 1.1, 1.2_

- [ ] 2. Test the filename display functionality

  - Create test JSON files with different naming patterns
  - Verify that filenames appear correctly in the dropdown list
  - Test with files using the new c_check format
  - Ensure long filenames are displayed properly
  - _Requirements: 1.1, 1.2, 1.3_

- [ ] 3. Verify filtering functionality still works

  - Test the query type filter with filename display
  - Ensure "Все" (All) filter shows all files
  - Verify filtered lists show correct filenames
  - Test edge cases with different file types
  - _Requirements: 2.1, 2.2, 2.3_

- [ ] 4. Test sorting and file selection

  - Verify files are sorted by creation time (newest first)
  - Test file selection from the dropdown
  - Ensure selected files load and display correctly
  - Verify all visualization features work after selection
  - _Requirements: 3.1, 3.2, 4.1, 4.2, 4.3, 4.4_

- [ ] 5. Perform comprehensive testing
  - Test with empty directory
  - Test with files containing special characters
  - Test with files missing metadata
  - Verify error handling remains intact
  - Test all existing functionality (export, analysis, etc.)
  - _Requirements: 4.1, 4.2, 4.3, 4.4_
