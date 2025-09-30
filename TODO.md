# Project TODOs

## Technical Debt
- No automated tests for Chrome extension (manual testing only)
- Icons are basic SVG placeholders
- No build process or bundling (not needed for current scope)
- Rate limiting not implemented on backend APIs
- Audit logging for admin actions not implemented
- Email integration for sharing invitations pending

## Future Features (PROJECT_SPEC.md)
- Share tokens via invite codes
- Text highlighting with note association
- URL pattern migration tools
- Workflows: game master notes, school notes

## Testing Requirements
- Chrome extension automated tests
- Integration tests for sharing system
- Performance tests for multi-user queries
- Security tests for data isolation

## Documentation
- API documentation generation (OpenAPI/Swagger)
- Chrome extension user guide
- Developer onboarding guide

## DevOps & Deployment
- Configure Google Cloud Platform deployment
- Set up Cloud SQL PostgreSQL with auto-pause
- Implement Cloud Run with scale-to-zero
- Configure production environment variables
- Set up monitoring and alerting

## Security Enhancements
- Implement rate limiting on all APIs
- Add request validation middleware
- Set up security headers (CORS, CSP, etc.)
- Implement audit logging for sensitive operations

## Performance Optimizations
- Database query optimization with proper indexing
- Implement caching strategy (if needed at scale)
- Optimize Chrome extension storage operations
- Bundle size optimization for extension

## Code Quality
- Increase test coverage to 80%+
- Add more comprehensive type hints
- Implement stricter linting rules
- Set up continuous integration (CI) pipeline

## User Experience
- Improve error messages and user feedback
- Add keyboard shortcuts for common operations
- Implement undo/redo for note operations
- Add note search and filtering capabilities
