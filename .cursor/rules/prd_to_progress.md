# Cursor Rules: PRD to PROGRESS Plan Conversion

## IMPORTANT: Documentation Style Notes
- Use bullet points over paragraphs
- Problem/Solution format for decisions
- Code examples: Essential snippets only
- No over-explanation of obvious concepts

### Anti-Patterns to Avoid
- ❌ Long explanations of basic concepts
- ❌ Detailed code walkthroughs in docs
- ❌ Repetitive sections
- ❌ Verbose implementation details

## PRD Structure Rules

### 1. Core PRD Components
- Title must be in format: `PRD: [Feature Name] v[Version] - [Brief Description]`
- Overview section must be concise (2-3 sentences max)
- Problem Statement must clearly identify pain points and any relevant-but-short user stories and jobs-to-be-done
- Solution Design must be broken into numbered sections
- Implementation Plan must include concrete steps
- Success Metrics must be measurable and clear

### 2. Required Sections
```markdown
# PRD: [Feature Name] v[Version] - [Brief Description]

## Overview
[2-3 sentences describing the feature]

## Problem Statement
[Clear identification of pain points]

## Solution Design
[Detailed solution broken into sections]

### 1. [Main Component]
### 2. Implementation Plan
### 3. File Structure Changes
### 4. Configuration
### 5. Implementation Steps

## Success Metrics
- [ ] [Metric 1]
- [ ] [Metric 2]

## Honest Assessment
[Realistic evaluation of the solution]
```

### 3. Code Block Rules
- All code blocks must specify language
- Example code must be complete and runnable
- Configuration examples must include comments
- File paths must be relative to project root

## PROGRESS Plan Conversion

### 1. PROGRESS File Naming
- Name format: `PROGRESS_[FEATURE_NAME]_V[VERSION].md`
- Must match corresponding PRD version

### 2. Required PROGRESS Sections
```markdown
# Progress: [Feature Name] v[Version]

Implementation progress for [brief description from PRD].

## Implementation Steps

### Core Implementation
[Convert PRD Implementation Steps to checkboxes]
- [ ] Step 1
- [ ] Step 2

### Testing & Validation
[Convert PRD Testing Strategy to checkboxes]
- [ ] Test 1
- [ ] Test 2

### Documentation
[Convert documentation tasks to checkboxes]
- [ ] Task 1
- [ ] Task 2

## Key Requirements
[List key requirements from PRD]
```

### 3. Conversion Rules

#### From PRD to PROGRESS
1. Extract implementation steps from PRD's Implementation Plan
2. Convert each step to a checkbox item
3. Group steps into Core Implementation, Testing, and Documentation
4. Pull key requirements from PRD's Success Metrics
5. Keep descriptions minimal and actionable

#### Status Tracking
- Use checkboxes `- [ ]` for pending items
- Use checked boxes `- [x]` for completed items
- Add completion dates in parentheses when checked

## Best Practices

### 1. PRD Writing
- Focus on the "why" before the "how"
- Include concrete examples
- Provide realistic time estimates
- Consider backward compatibility
- Document security implications

### 2. PROGRESS Tracking
- Keep items atomic and verifiable
- Update regularly with progress
- Include blockers and dependencies
- Link to relevant PRD sections
- Track time estimates vs actuals

### 3. Code Examples
- Include complete, runnable examples
- Show both simple and complex cases
- Document environment requirements
- Include error handling
- Show configuration options

### 4. Documentation
- Link between PRD and PROGRESS files
- Keep implementation notes
- Document decisions and changes
- Track deviations from PRD

## Example Conversion

### PRD Implementation Section:
```markdown
### Implementation Steps
1. Add configuration classes (~20 lines)
2. Add cooldown manager (~40 lines)
3. Enhance validate_message() (~30 lines)
4. Add basic personality (~20 lines)
5. Update .env.template (4 lines)
6. Add startup logging (~10 lines)
```

### Converted PROGRESS Section:
```markdown
### Core Implementation
- [ ] Add configuration classes
  - Estimated: 20 lines
  - Status: Not started
- [ ] Add cooldown manager
  - Estimated: 40 lines
  - Dependencies: Configuration classes
- [ ] Enhance validate_message()
  - Estimated: 30 lines
  - Dependencies: Cooldown manager

### Testing & Validation
- [ ] Test configuration loading
- [ ] Verify cooldown functionality
- [ ] Validate message handling

### Documentation
- [ ] Update configuration docs
- [ ] Document new functions
- [ ] Add usage examples
```

## Validation Checklist

### PRD Validation
- [ ] All required sections present
- [ ] Clear problem statement
- [ ] Concrete implementation steps
- [ ] Measurable success metrics
- [ ] Realistic time estimates
- [ ] Security considerations
- [ ] Backward compatibility plan

### PROGRESS Validation
- [ ] Matches PRD version
- [ ] All steps converted to checkboxes
- [ ] Clear grouping of tasks
- [ ] Dependencies identified
- [ ] Time estimates included
- [ ] Testing tasks included
- [ ] Documentation tasks included 

## Completion and Archiving

### 1. Completion Criteria
- All PROGRESS checkboxes are marked complete
- All Success Metrics from PRD are achieved
- Documentation is up to date
- No outstanding issues or bugs
- Final review has been conducted

### 2. Archiving Process
- Move both PRD and corresponding PROGRESS file to `x-workings/x-done/` subdirectory
- Keep original filenames intact
- Add completion date to both files' frontmatter
- Update any relevant links in other documents
- Create a brief completion summary

### 3. Completion Summary Format
```markdown
# Completion Summary
Added to start of both PRD and PROGRESS files:

---
status: completed
completed_date: YYYY-MM-DD
time_to_completion: X days
key_achievements:
  - Achievement 1
  - Achievement 2
migration_notes:
  - Any important notes about the archival
---
```

### 4. Post-Completion Tasks
- Update any documentation referencing the PRD/PROGRESS
- Notify relevant team members of completion
- Archive any associated feature branches
- Update project tracking tools
- Document lessons learned for future PRDs 