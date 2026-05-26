from sqladmin import ModelView

from app.api.auth.model import OTPCode, RefreshToken
from app.api.files.model import FileUpload
from app.api.todos.model import Todo
from app.api.users.model import User


class UserAdmin(ModelView, model=User):
    name = "User"
    name_plural = "Users"
    icon = "fa-solid fa-users"
    category = "Auth"

    column_list = [User.id, User.email, User.full_name, User.role, User.is_active, User.is_email_verified, User.created_at]
    column_searchable_list = [User.email, User.first_name, User.last_name]
    column_sortable_list = [User.email, User.role, User.created_at]
    column_filters = [User.role, User.is_active, User.is_email_verified]

    form_excluded_columns = [User.hashed_password, User.totp_secret, User.refresh_tokens, User.otp_codes, User.todos, User.files]
    can_delete = True


class TodoAdmin(ModelView, model=Todo):
    name = "Todo"
    name_plural = "Todos"
    icon = "fa-solid fa-list-check"
    category = "Content"

    column_list = [Todo.id, Todo.title, Todo.priority, Todo.is_completed, Todo.due_at, Todo.created_at]
    column_searchable_list = [Todo.title]
    column_sortable_list = [Todo.created_at, Todo.priority, Todo.is_completed]
    column_filters = [Todo.priority, Todo.is_completed]


class FileUploadAdmin(ModelView, model=FileUpload):
    name = "File"
    name_plural = "Files"
    icon = "fa-solid fa-file"
    category = "Content"

    column_list = [FileUpload.id, FileUpload.original_filename, FileUpload.content_type, FileUpload.size_bytes, FileUpload.storage_driver, FileUpload.created_at]
    column_searchable_list = [FileUpload.original_filename]
    can_create = False
    can_edit = False


class RefreshTokenAdmin(ModelView, model=RefreshToken):
    name = "Refresh Token"
    name_plural = "Refresh Tokens"
    icon = "fa-solid fa-key"
    category = "Auth"

    column_list = [RefreshToken.id, RefreshToken.user_id, RefreshToken.is_revoked, RefreshToken.expires_at, RefreshToken.ip_address, RefreshToken.created_at]
    can_create = False
    can_edit = False


class OTPCodeAdmin(ModelView, model=OTPCode):
    name = "OTP Code"
    name_plural = "OTP Codes"
    icon = "fa-solid fa-lock"
    category = "Auth"

    column_list = [OTPCode.id, OTPCode.user_id, OTPCode.purpose, OTPCode.is_used, OTPCode.expires_at, OTPCode.attempts, OTPCode.created_at]
    can_create = False
    can_edit = False
