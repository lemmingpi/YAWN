## Standing Rules for All Development Sessions

### Git Workflow
- **Use Alt Name** set env variables 
    export GIT_AUTHOR_NAME="Gogo (Claude Code)"
    export GIT_AUTHOR_EMAIL="gordon.palumbo+claude@gmail.com"
- **Always create feature branch**: `git checkout -b feature/[descriptive-name]`
- **Commit frequently**: Small, logical commits over large changes
- **Push to origin**: `git push origin feature/[branch-name]`
- **Create PR to upstream/main**: Never push directly to main

### Commit Message Format
- type(scope): description [CLAUDE-ASSISTED]
    - Types: feat|fix|docs|test|refactor|style|chore
    - Scope: api|extension|db|dashboard|sync|auth

### Testing Requirements
1. **Create tests alongside features**: Every new function needs at least one test
2. **Run tests before committing**: `pytest` must pass
3. **Test file naming**: `test_[module_name].py`
4. **Never delete or modify existing tests without explicit permission**
5. **Ask before changing test assertions**: "May I update this test because [reason]?"

### Code Standards
- **Type hints required**: All functions must have type annotations
- **Docstrings required**: All public functions need docstrings
- **No commented code**: Delete, don't comment out
- **Import order**: stdlib → third-party → local (use isort)

### PR Checklist (include in every PR body)
#### Changes
- [Brief description of what changed]
#### Testing
- [ ] All existing tests pass
- [ ] New tests added for new features
- [Suggested manaul testing steps]
#### Documentation
- [ ] CLAUDE_CONTEXT.md updated if needed
- [ ] Docstrings added/updated
- [ ] API spec updated if endpoints changed

### Claude Session Notes
- Session goal: [What was requested]
- Decisions made: [Any divergences from plan]
- Next session should: [What to do next]
- Permission Required For
    - Deleting or modifying existing tests
    - Changing database schema after MVP
    - Modifying API contracts
    - Removing existing functionality
    - Major dependency updates
    - Changing architecture from PROJECT_SPEC.md
- Always Do Without Asking
    - Add new tests
    - Fix obvious typos
    - Add error handling
    - Improve logging
    - Add type hints
    - Write docstrings
    -  Create feature branches

### Session End Checklist
Before ending any development session:
- All code committed with proper messages
- Tests written and passing
- PR created if feature complete
- CLAUDE_CONTEXT.md updated with current state
- Next steps documented

