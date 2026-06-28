# API Reference Manual

This document provides a comprehensive API reference for the **Operational Intelligence Platform (OIP)** backend authentication service.

---

## 1. Global Specifications

*   **API Prefix:** `/api/v1`
*   **Documentation Endpoint:** `/api/v1/docs` (Swagger UI) or `/api/v1/redoc` (ReDoc)
*   **Response Format:** JSON (`application/json`)
*   **Date/Time Format:** ISO 8601 (`YYYY-MM-DDTHH:MM:SSZ`)

---

## 2. Authentication Status Summary

| HTTP Status | Meaning | Scenario |
| :--- | :--- | :--- |
| `200 OK` / `201 Created` | Success | Request succeeded. |
| `400 Bad Request` | Client Error | Invalid registration input, duplicate email. |
| `401 Unauthorized` | Auth Error | Missing token, invalid signature, expired credentials. |
| `403 Forbidden` | Access Error | Account is suspended/disabled (`is_active=False`). |
| `422 Unprocessable` | Validation Error | Request body failed Pydantic schema constraints. |

---

## 3. Endpoint Specifications

### 3.1. User Registration

Registers a new user profile on the OIP platform. Passwords are automatically hashed via bcrypt.

*   **Route:** `/api/v1/auth/register`
*   **Method:** `POST`
*   **Authentication:** None (Public)
*   **Request Body Schema:**
    ```json
    {
      "email": "user@example.com",
      "password": "securepassword123",
      "first_name": "Jane",
      "last_name": "Smith"
    }
    ```
    *Constraints:* `email` must be valid syntax; `password` must be between 8 and 128 characters; `first_name` and `last_name` are optional (max 100 characters).
*   **Response Schema (201 Created):**
    ```json
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "email": "user@example.com",
      "first_name": "Jane",
      "last_name": "Smith",
      "is_active": true,
      "is_verified": false,
      "created_at": "2026-06-20T16:53:25Z",
      "updated_at": "2026-06-20T16:53:25Z"
    }
    ```
*   **Error Responses:**
    *   **400 Bad Request:** Email already in use.
        ```json
        {
          "detail": "User with this email already exists"
        }
        ```
    *   **422 Unprocessable Entity:** Invalid email structure or short password.
        ```json
        {
          "detail": [
            {
              "type": "string_too_short",
              "loc": ["body", "password"],
              "msg": "String should have at least 8 characters"
            }
          ]
        }
        ```

---

### 3.2. User Login

Authenticates credentials and establishes a session.

*   **Route:** `/api/v1/auth/login`
*   **Method:** `POST`
*   **Authentication:** None (Public)
*   **Request Body Schema:**
    ```json
    {
      "email": "user@example.com",
      "password": "securepassword123"
    }
    ```
*   **Response Headers Set:**
    *   `Set-Cookie`: `refresh_token=<token>; Max-Age=604800; Path=/; HttpOnly; SameSite=lax` (Includes `Secure` flag in production).
*   **Response Schema (200 OK):**
    ```json
    {
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "token_type": "bearer",
      "refresh_token": null
    }
    ```
*   **Error Responses:**
    *   **401 Unauthorized:** Invalid password or email.
        ```json
        {
          "detail": "Incorrect email or password"
        }
        ```

---

### 3.3. Token Refresh

Rotates session tokens. Issues a new Access Token in the response and sets a new rotated Refresh Token cookie.

*   **Route:** `/api/v1/auth/refresh`
*   **Method:** `POST`
*   **Authentication:** None (Requires `refresh_token` in cookies)
*   **Request Headers/Cookies:**
    *   `Cookie`: `refresh_token=<refresh_token_string>`
*   **Response Headers Set:**
    *   `Set-Cookie`: `refresh_token=<new_rotated_refresh_token>; Max-Age=604800; Path=/; HttpOnly; SameSite=lax`
*   **Response Schema (200 OK):**
    ```json
    {
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.new_access_token...",
      "token_type": "bearer",
      "refresh_token": null
    }
    ```
*   **Error Responses:**
    *   **401 Unauthorized:** Missing, expired, or invalid refresh token.
        ```json
        {
          "detail": "Refresh token missing"
        }
        ```
        or
        ```json
        {
          "detail": "Could not validate refresh credentials"
        }
        ```

---

### 3.4. Retrieve Current Profile

Fetches the profile details of the authenticated user.

*   **Route:** `/api/v1/auth/me`
*   **Method:** `GET`
*   **Authentication:** Required (`Authorization: Bearer <access_token>`)
*   **Request Headers:**
    *   `Authorization`: `Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
*   **Response Schema (200 OK):**
    ```json
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "email": "user@example.com",
      "first_name": "Jane",
      "last_name": "Smith",
      "is_active": true,
      "is_verified": false,
      "created_at": "2026-06-20T16:53:25Z",
      "updated_at": "2026-06-20T16:53:25Z"
    }
    ```
*   **Error Responses:**
    *   **401 Unauthorized:** Invalid, expired, or missing Access Token.
        ```json
        {
          "detail": "Could not validate credentials"
        }
        ```
    *   **403 Forbidden:** User exists but account has been disabled (`is_active=False`).
        ```json
        {
          "detail": "Inactive user profile"
        }
        ```

---

### 3.5. User Logout

Invalidates client session by clearing the Refresh Token cookie.

*   **Route:** `/api/v1/auth/logout`
*   **Method:** `POST`
*   **Authentication:** None (Public - removes cookie state)
*   **Response Headers Set:**
    *   `Set-Cookie`: `refresh_token=; Max-Age=0; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT; HttpOnly; SameSite=lax`
*   **Response Schema (200 OK):**
    ```json
    {
      "message": "Logged out successfully"
    }
    ```
