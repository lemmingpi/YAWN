# Authentication System Implementation

This document describes the User model and authentication system implementation for the multi-user Web Notes application.

## Overview

The authentication system provides:
- User registration and login with Chrome Identity integration
- JWT token-based authentication for API endpoints
- Role-based access control (admin vs regular users)
- Comprehensive security middleware
- Complete test coverage

## Components

### 1. User Model (`app/models.py`)

```python
class User(Base, TimestampMixin):
    """User model for multi-user Web Notes application with Chrome Identity integration."""

    __tablename__ = "users"

    id: int (Primary Key)
    chrome_user_id: str (Unique, Indexed)
    email: str (Unique, Indexed)
    display_name: str
    is_admin: bool (Default: False)
    is_active: bool (Default: True)
    created_at: datetime (Auto-generated)
    updated_at: datetime (Auto-updated)
```

**Key Features:**
- Chrome user ID integration for seamless authentication
- Email and Chrome ID uniqueness constraints
- Optimized indexes for performance
- Timestamp tracking with automatic updates

### 2. Authentication Utilities (`app/auth.py`)

**Core Functions:**
- `verify_chrome_token()`: Validates Chrome Identity tokens with Google
- `create_access_token()`: Generates JWT tokens for API access
- `verify_token()`: Validates and decodes JWT tokens
- `create_user_from_chrome_token()`: Creates/updates users from Chrome tokens

**Dependencies:**
- `get_current_user()`: FastAPI dependency for authenticated endpoints
- `get_current_active_user()`: Dependency for active user verification
- `get_current_admin_user()`: Dependency for admin-only endpoints

**Security Features:**
- JWT token expiration handling
- Chrome token verification with Google OAuth
- Email verification requirement
- Comprehensive error handling

### 3. User Router (`app/routers/users.py`)

**Endpoints:**

#### Public Endpoints:
- `POST /api/users/register` - Register new user with Chrome token
- `POST /api/users/login` - Login user with Chrome token

#### Authenticated Endpoints:
- `GET /api/users/me` - Get current user profile
- `PUT /api/users/me` - Update current user profile

#### Admin-only Endpoints:
- `GET /api/users/` - List all users (paginated)
- `GET /api/users/{user_id}` - Get user by ID
- `PUT /api/users/{user_id}` - Update user by ID
- `DELETE /api/users/{user_id}` - Delete user by ID

### 4. Pydantic Schemas (`app/schemas.py`)

**User Schemas:**
- `UserBase`: Common user fields
- `UserCreate`: Registration with Chrome token
- `UserUpdate`: User profile updates
- `UserResponse`: API response format
- `UserLogin`: Login with Chrome token
- `TokenResponse`: JWT token response
- `TokenData`: Token payload validation

### 5. Middleware (`app/middleware.py`)

**Available Middleware:**
- `AuthenticationMiddleware`: Automatic JWT validation for protected routes
- `RequestLoggingMiddleware`: HTTP request/response logging
- `SecurityHeadersMiddleware`: Security headers (XSS, CSRF protection)

### 6. Comprehensive Tests

**Test Coverage:**
- `tests/test_auth.py`: Authentication utility functions
- `tests/test_users_router.py`: User router endpoints
- `tests/test_middleware.py`: Middleware functionality
- `tests/test_models.py`: Database model validation
- `tests/conftest.py`: Test configuration and fixtures

## Environment Configuration

**Required Environment Variables:**

```bash
# JWT Configuration
JWT_SECRET_KEY=your-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=1440  # 24 hours

# Database Configuration
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/webnotes
```

## Usage Examples

### 1. User Registration

```bash
curl -X POST "http://localhost:8000/api/users/register" \
  -H "Content-Type: application/json" \
  -d '{
    "chrome_token": "chrome_identity_token_here",
    "display_name": "John Doe"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": 1,
    "chrome_user_id": "chrome_123",
    "email": "john@example.com",
    "display_name": "John Doe",
    "is_admin": false,
    "is_active": true,
    "created_at": "2024-01-01T12:00:00Z",
    "updated_at": "2024-01-01T12:00:00Z"
  }
}
```

### 2. Using JWT Token for API Access

```bash
curl -X GET "http://localhost:8000/api/users/me" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### 3. Admin User Management

```bash
# List all users (admin only)
curl -X GET "http://localhost:8000/api/users/" \
  -H "Authorization: Bearer admin_jwt_token"

# Update user by ID (admin only)
curl -X PUT "http://localhost:8000/api/users/2" \
  -H "Authorization: Bearer admin_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{
    "is_admin": true,
    "is_active": true
  }'
```

## Security Considerations

### 1. Token Security
- JWT tokens are signed with HS256 algorithm
- Tokens expire after 24 hours by default
- Secret key must be changed in production

### 2. Chrome Identity Integration
- Tokens are verified with Google's OAuth endpoint
- Email verification is required
- Invalid tokens are rejected immediately

### 3. Database Security
- Unique constraints on email and Chrome user ID
- Indexed fields for performance
- Soft deletion capabilities with is_active flag

### 4. API Security
- Role-based access control (RBAC)
- Input validation with Pydantic
- Comprehensive error handling
- Security headers middleware

## Testing

### Run All Tests
```bash
cd backend
python -m pytest tests/ -v
```

### Run Specific Test Categories
```bash
# Authentication tests
python -m pytest tests/test_auth.py -v

# User router tests
python -m pytest tests/test_users_router.py -v

# Model tests
python -m pytest tests/test_models.py -v
```

### Test Coverage
The test suite covers:
- JWT token creation and validation
- Chrome token verification (mocked)
- User registration and login flows
- Profile management
- Admin user operations
- Error handling and edge cases
- Database model constraints
- Middleware functionality

## Migration and Deployment

### Database Migration
```bash
# Generate migration
alembic revision --autogenerate -m "Add user authentication system"

# Apply migration
alembic upgrade head
```

### Production Deployment Checklist
- [ ] Set secure JWT_SECRET_KEY
- [ ] Configure proper DATABASE_URL
- [ ] Set appropriate token expiration time
- [ ] Enable HTTPS in production
- [ ] Configure CORS policies
- [ ] Set up proper logging
- [ ] Test Chrome Identity integration

## Chrome Extension Integration

### Frontend Implementation
The Chrome extension should:
1. Use Chrome Identity API to get user token
2. Send token to `/api/users/register` or `/api/users/login`
3. Store returned JWT token for API requests
4. Include token in Authorization header: `Bearer <jwt_token>`
5. Handle token expiration and refresh

### Example Chrome Extension Code
```javascript
// Get Chrome Identity token
chrome.identity.getAuthToken({interactive: true}, (token) => {
  // Register/login with backend
  fetch('http://localhost:8000/api/users/login', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({chrome_token: token})
  })
  .then(response => response.json())
  .then(data => {
    // Store JWT token
    localStorage.setItem('jwt_token', data.access_token);
  });
});
```

## Next Steps

1. **Multi-user Data Isolation**: Add user_id foreign keys to existing models (Site, Page, Note)
2. **User Preferences**: Extend User model with settings and preferences
3. **Advanced RBAC**: Implement more granular permissions
4. **Rate Limiting**: Add request rate limiting per user
5. **Session Management**: Implement refresh tokens for better security
6. **Audit Logging**: Track user actions for compliance
7. **Social Features**: Add user collaboration features

## Support

For questions or issues with the authentication system:
1. Check the test files for usage examples
2. Review error messages in logs
3. Verify environment variables are set correctly
4. Ensure Chrome Identity token is valid
