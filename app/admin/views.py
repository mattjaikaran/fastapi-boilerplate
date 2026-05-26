from sqladmin import ModelView

from app.api.api_keys.model import APIKey
from app.api.audit.model import AuditLog
from app.api.auth.model import OTPCode, RefreshToken
from app.api.billing.model import BillingCustomer, Subscription
from app.api.feature_flags.model import FeatureFlag, OrgFeatureFlag
from app.api.files.model import FileUpload
from app.api.jobs.model import BackgroundJob
from app.api.notifications.model import Notification
from app.api.organizations.model import Organization, OrganizationMember
from app.api.todos.model import Todo
from app.api.users.model import User
from app.api.webhooks.model import WebhookEvent


class UserAdmin(ModelView, model=User):
    name = "User"
    name_plural = "Users"
    icon = "fa-solid fa-users"
    category = "Auth"

    column_list = [User.id, User.email, User.first_name, User.last_name, User.role, User.is_active, User.is_email_verified, User.created_at]
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


class OrganizationAdmin(ModelView, model=Organization):
    name = "Organization"
    name_plural = "Organizations"
    icon = "fa-solid fa-building"
    category = "Organizations"

    column_list = [Organization.id, Organization.name, Organization.slug, Organization.plan, Organization.is_active, Organization.owner_id, Organization.created_at]
    column_searchable_list = [Organization.name, Organization.slug]
    column_sortable_list = [Organization.name, Organization.created_at]
    column_filters = [Organization.plan, Organization.is_active]


class OrganizationMemberAdmin(ModelView, model=OrganizationMember):
    name = "Organization Member"
    name_plural = "Organization Members"
    icon = "fa-solid fa-user-group"
    category = "Organizations"

    column_list = [OrganizationMember.id, OrganizationMember.organization_id, OrganizationMember.user_id, OrganizationMember.role, OrganizationMember.created_at]
    column_filters = [OrganizationMember.role]
    can_create = False


class WebhookEventAdmin(ModelView, model=WebhookEvent):
    name = "Webhook Event"
    name_plural = "Webhook Events"
    icon = "fa-solid fa-bolt"
    category = "Integrations"

    column_list = [WebhookEvent.id, WebhookEvent.source, WebhookEvent.event_type, WebhookEvent.status, WebhookEvent.signature_valid, WebhookEvent.created_at]
    column_searchable_list = [WebhookEvent.source, WebhookEvent.event_type]
    column_sortable_list = [WebhookEvent.created_at, WebhookEvent.status]
    column_filters = [WebhookEvent.source, WebhookEvent.status, WebhookEvent.signature_valid]
    can_create = False
    can_edit = False


class BillingCustomerAdmin(ModelView, model=BillingCustomer):
    name = "Billing Customer"
    name_plural = "Billing Customers"
    icon = "fa-solid fa-credit-card"
    category = "Billing"

    column_list = [BillingCustomer.id, BillingCustomer.user_id, BillingCustomer.stripe_customer_id, BillingCustomer.created_at]
    column_searchable_list = [BillingCustomer.stripe_customer_id]
    can_create = False
    can_edit = False


class SubscriptionAdmin(ModelView, model=Subscription):
    name = "Subscription"
    name_plural = "Subscriptions"
    icon = "fa-solid fa-receipt"
    category = "Billing"

    column_list = [Subscription.id, Subscription.stripe_subscription_id, Subscription.plan, Subscription.status, Subscription.current_period_end, Subscription.cancel_at_period_end, Subscription.created_at]
    column_sortable_list = [Subscription.created_at, Subscription.status]
    column_filters = [Subscription.plan, Subscription.status, Subscription.cancel_at_period_end]
    can_create = False


class NotificationAdmin(ModelView, model=Notification):
    name = "Notification"
    name_plural = "Notifications"
    icon = "fa-solid fa-bell"
    category = "System"

    column_list = [Notification.id, Notification.user_id, Notification.type, Notification.title, Notification.read_at, Notification.created_at]
    column_searchable_list = [Notification.title]
    column_sortable_list = [Notification.created_at]
    column_filters = [Notification.type]
    can_create = False


class AuditLogAdmin(ModelView, model=AuditLog):
    name = "Audit Log"
    name_plural = "Audit Logs"
    icon = "fa-solid fa-shield"
    category = "System"

    column_list = [AuditLog.id, AuditLog.actor_id, AuditLog.action, AuditLog.resource_type, AuditLog.resource_id, AuditLog.ip_address, AuditLog.created_at]
    column_searchable_list = [AuditLog.action, AuditLog.resource_type]
    column_sortable_list = [AuditLog.created_at, AuditLog.action]
    column_filters = [AuditLog.action, AuditLog.resource_type]
    can_create = False
    can_edit = False
    can_delete = False


class FeatureFlagAdmin(ModelView, model=FeatureFlag):
    name = "Feature Flag"
    name_plural = "Feature Flags"
    icon = "fa-solid fa-flag"
    category = "System"

    column_list = [FeatureFlag.id, FeatureFlag.key, FeatureFlag.name, FeatureFlag.enabled, FeatureFlag.created_at]
    column_searchable_list = [FeatureFlag.key, FeatureFlag.name]
    column_sortable_list = [FeatureFlag.key, FeatureFlag.created_at]
    column_filters = [FeatureFlag.enabled]


class OrgFeatureFlagAdmin(ModelView, model=OrgFeatureFlag):
    name = "Org Feature Override"
    name_plural = "Org Feature Overrides"
    icon = "fa-solid fa-toggle-on"
    category = "System"

    column_list = [OrgFeatureFlag.id, OrgFeatureFlag.flag_id, OrgFeatureFlag.org_id, OrgFeatureFlag.enabled, OrgFeatureFlag.created_at]
    column_filters = [OrgFeatureFlag.enabled]


class APIKeyAdmin(ModelView, model=APIKey):
    name = "API Key"
    name_plural = "API Keys"
    icon = "fa-solid fa-key"
    category = "Integrations"

    column_list = [APIKey.id, APIKey.user_id, APIKey.name, APIKey.key_prefix, APIKey.scopes, APIKey.expires_at, APIKey.last_used_at, APIKey.revoked_at, APIKey.created_at]
    column_searchable_list = [APIKey.name, APIKey.key_prefix]
    column_sortable_list = [APIKey.created_at, APIKey.last_used_at]
    can_create = False


class BackgroundJobAdmin(ModelView, model=BackgroundJob):
    name = "Background Job"
    name_plural = "Background Jobs"
    icon = "fa-solid fa-gears"
    category = "System"

    column_list = [BackgroundJob.id, BackgroundJob.name, BackgroundJob.task_name, BackgroundJob.status, BackgroundJob.started_at, BackgroundJob.completed_at, BackgroundJob.created_at]
    column_searchable_list = [BackgroundJob.name, BackgroundJob.task_name]
    column_sortable_list = [BackgroundJob.created_at, BackgroundJob.status]
    column_filters = [BackgroundJob.status, BackgroundJob.task_name]
    can_create = False
    can_edit = False
