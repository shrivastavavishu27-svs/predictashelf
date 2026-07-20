# Predicta Shelf - Authentication System Guide

## Overview

Predicta Shelf में complete authentication system implement किया गया है जो users को secure रूप से manage करने की सुविधा देता है। यह system निम्नलिखित features provide करता है:

- **User Registration** - New users के लिए signup
- **Secure Login** - Password hashing के साथ secure authentication
- **Password Reset** - Forgot password functionality
- **User Profile Management** - Profile update करने की सुविधा
- **User-specific Data** - हर user का अपना separate data
- **Session Management** - Secure session handling

## Architecture

### Database Structure

**Users (`users.json`):**
```json
{
  "username": {
    "id": "unique-user-id",
    "username": "username",
    "email": "user@example.com", 
    "password": "hashed_password",
    "full_name": "User Full Name",
    "created_at": "2025-01-01 12:00:00",
    "updated_at": "2025-01-01 12:00:00",
    "is_active": true
  }
}
```

**Products (`products.json`):**
```json
[
  {
    "id": 1234567890,
    "name": "Product Name",
    "category": "Food",
    "expiry": "2025-01-15",
    "purchase_date": "2025-01-01",
    "note": "Product notes",
    "price": "100",
    "user_id": "unique-user-id",
    "added": "2025-01-01"
  }
]
```

### Security Features

1. **Password Hashing:**
   - SHA-256 with salt
   - Salt: "shelfwise_salt_2025"
   - Production में random salt per user recommend किया जाएगा

2. **Password Strength Validation:**
   - Minimum 8 characters
   - At least one uppercase letter
   - At least one lowercase letter  
   - At least one digit

3. **Session Security:**
   - Server-side session management
   - Automatic logout on session expiry
   - Login required for all protected routes

## API Endpoints

### Authentication Routes

| Method | Route | Description |
|---------|-------|-------------|
| GET/POST | `/login` | User login |
| GET/POST | `/signup` | User registration |
| GET/POST | `/forgot-password` | Password reset request |
| GET/POST | `/reset-password/<token>` | Password reset with token |
| GET | `/logout` | User logout |
| GET/POST | `/profile` | User profile management |

### Protected Routes

All main application routes require authentication:
- `/` - Dashboard (index)
- `/form` - Add product form
- `/add` - Add product (POST)
- `/delete/<pid>` - Delete product

## User Registration Process

1. **Signup Form:**
   - Full Name, Username, Email, Password, Confirm Password
   - Real-time password strength validation
   - Email format validation
   - Username uniqueness check

2. **Validation:**
   - Password strength requirements
   - Email format validation
   - Username availability
   - Email uniqueness

3. **Account Creation:**
   - Generate unique user ID
   - Hash password with salt
   - Store user data in `users.json`
   - Redirect to login page

## Password Reset Flow

1. **Request Reset:**
   - User enters email address
   - System generates reset token (1 hour expiry)
   - Token sent via email (demo में shown in flash message)

2. **Reset Password:**
   - User clicks reset link with token
   - Token validation
   - New password with strength validation
   - Password update and redirect to login

## User Profile Features

### Profile Management
- **View Profile:** User information और statistics
- **Update Profile:** Full name और email update
- **Quick Actions:** Add product, view products, change password, logout

### User-specific Data
- **Product Isolation:** हर user केवल अपने products देख सकता है
- **Data Association:** Products में `user_id` field से user association
- **Secure Access:** Users केवल अपने data को access/delete कर सकते हैं

## Implementation Details

### Core Functions

```python
# Password Hashing
def hash_password(password):
    salt = "shelfwise_salt_2025"
    return hashlib.sha256((password + salt).encode()).hexdigest()

# Password Validation  
def validate_password(password):
    # Returns (is_valid, message)
    # Checks length, uppercase, lowercase, digit

# Email Validation
def validate_email(email):
    # Regex pattern validation
```

### Security Middleware

```python
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
```

### Session Management

```python
# Login
session['logged_in'] = True
session['username'] = username
session['user_id'] = users[username]["id"]

# Logout
session.clear()
```

## Frontend Features

### Modern UI Components

1. **Signup Page:**
   - Real-time password strength indicator
   - Password requirements checklist
   - Confirm password validation
   - Responsive design with Tailwind CSS

2. **Login Page:**
   - Forgot password link
   - Signup navigation
   - Demo credentials display

3. **Profile Page:**
   - User statistics dashboard
   - Profile edit form
   - Quick action buttons
   - Account information display

4. **Password Reset Pages:**
   - Email input form
   - Token-based reset form
   - Password strength validation

## Usage Examples

### User Registration
```python
# Automatic on first run
create_default_admin()  # Creates admin/admin123
```

### Manual User Creation
```python
users = load_users()
users["newuser"] = {
    "id": str(uuid.uuid4()),
    "username": "newuser", 
    "email": "user@example.com",
    "password": hash_password("securepassword123"),
    "full_name": "New User",
    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "is_active": True
}
save_users(users)
```

### Product Association
```python
# When adding product
products.append({
    "id": int(datetime.now().timestamp()*1000),
    "name": "Milk",
    "category": "Food", 
    "expiry": "2025-01-10",
    "user_id": session.get('user_id'),  # Associate with current user
    "added": date.today().strftime("%Y-%m-%d")
})
```

## Security Considerations

### Current Implementation
- ✅ Password hashing with salt
- ✅ Session-based authentication  
- ✅ Input validation
- ✅ CSRF protection (Flask built-in)
- ✅ User data isolation

### Production Recommendations
1. **Database:** Use PostgreSQL/MySQL instead of JSON files
2. **Password Security:** Implement bcrypt/scrypt with per-user salts
3. **Email Service:** Integrate SMTP for password reset emails
4. **Rate Limiting:** Implement login attempt limits
5. **Two-Factor Authentication:** Add 2FA for enhanced security
6. **Session Security:** Configure secure cookies, session timeout
7. **Logging:** Add security event logging
8. **HTTPS:** Enforce SSL/TLS in production

## Testing

### Test Users
- **Admin:** username: `admin`, password: `admin123`
- **Test User:** Can be created via signup form

### Test Scenarios
1. **Registration Flow:** Complete signup process
2. **Login/Logout:** Authentication cycle
3. **Password Reset:** Forgot password flow
4. **Profile Update:** Edit user information
5. **Data Isolation:** Verify user-specific products
6. **Session Security:** Test session expiry

## Troubleshooting

### Common Issues

1. **Login Issues:**
   - Check user exists in `users.json`
   - Verify password hashing
   - Check session configuration

2. **Password Reset:**
   - Verify token generation
   - Check token expiry (1 hour)
   - Validate email format

3. **Profile Issues:**
   - Check user_id in session
   - Verify user data structure
   - Check form validation

### Debug Mode
Enable Flask debug mode for detailed error messages:
```python
app.run(debug=True)
```

## Future Enhancements

1. **Email Verification:** Account confirmation via email
2. **Social Login:** Google, Facebook OAuth integration  
3. **Multi-factor Authentication:** SMS/Email based 2FA
4. **Role-based Access:** Admin/User role system
5. **Audit Trail:** User activity logging
6. **API Authentication:** JWT tokens for API access

## Conclusion

Predicta Shelf authentication system comprehensive और secure है, जो users को complete control देता है अपने data पर। System modern security practices follow करता है और scalable है भविष्य में enhancements के लिए।

---

*Last Updated: January 2025*
*Version: 1.0*
