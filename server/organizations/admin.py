from django.contrib import admin
from organizations.models import Organization, OrganizationMembership, OrganizationInvitation


class MembershipInline(admin.TabularInline):
    model = OrganizationMembership
    extra = 1
    fields = ('user', 'role', 'is_active', 'created_at')
    readonly_fields = ('created_at',)


class InvitationInline(admin.TabularInline):
    model = OrganizationInvitation
    extra = 0
    fields = ('email', 'role', 'status', 'expires_at', 'created_at')
    readonly_fields = ('token', 'created_at')


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'created_by', 'created_at')
    search_fields = ('name', 'slug')
    list_filter = ('is_active',)
    prepopulated_fields = {'slug': ('name',)}
    inlines = [MembershipInline, InvitationInline]


@admin.register(OrganizationMembership)
class OrganizationMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'organization', 'role', 'is_active', 'created_at')
    list_filter = ('role', 'is_active', 'organization')
    search_fields = ('user__email', 'organization__name')


@admin.register(OrganizationInvitation)
class OrganizationInvitationAdmin(admin.ModelAdmin):
    list_display = ('email', 'organization', 'role', 'status', 'expires_at')
    list_filter = ('status', 'role', 'organization')
    search_fields = ('email', 'organization__name')
    readonly_fields = ('token', 'created_at')
