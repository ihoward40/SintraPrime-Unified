-- =============================================================================
-- Migration: Add relational RBAC permission tables
-- R3-D: Resolve ORM-only tables — permissions, role_permissions, user_permissions
-- Context:
--   portal_schema.sql defines roles.permissions as a TEXT[] convenience column
--   (seed values, fast runtime checks). This migration adds the relational
--   permission model used by the ORM (Permission, RolePermission, UserPermission)
--   as the authoritative fine-grained RBAC mechanism. Both coexist.
-- =============================================================================

-- =============================================================================
-- 1. permissions — canonical permission catalog
-- =============================================================================

CREATE TABLE IF NOT EXISTS permissions (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        VARCHAR(100) NOT NULL UNIQUE,
    resource    VARCHAR(50)  NOT NULL,
    action      VARCHAR(50)  NOT NULL,
    description TEXT,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_permissions_resource_action
    ON permissions(resource, action);

-- =============================================================================
-- 2. role_permissions — role ↔ permission many-to-many join
-- =============================================================================

CREATE TABLE IF NOT EXISTS role_permissions (
    role_id       UUID NOT NULL REFERENCES roles(id)       ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

CREATE INDEX IF NOT EXISTS ix_role_permissions_permission
    ON role_permissions(permission_id);

-- =============================================================================
-- 3. user_permissions — per-user permission overrides (additions or explicit denies)
-- =============================================================================

CREATE TABLE IF NOT EXISTS user_permissions (
    user_id       UUID    NOT NULL REFERENCES users(id)       ON DELETE CASCADE,
    permission_id UUID    NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    granted       BOOLEAN NOT NULL DEFAULT TRUE,   -- FALSE = explicit deny
    granted_by    UUID    REFERENCES users(id),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, permission_id)
);

CREATE INDEX IF NOT EXISTS ix_user_permissions_user
    ON user_permissions(user_id);
CREATE INDEX IF NOT EXISTS ix_user_permissions_permission
    ON user_permissions(permission_id);

COMMENT ON TABLE permissions IS
    'Canonical fine-grained permission catalog. Coexists with roles.permissions TEXT[] '
    'convenience column used for fast seed/runtime checks.';
COMMENT ON TABLE role_permissions IS
    'Role-to-permission many-to-many join. Authority for role-based access control.';
COMMENT ON TABLE user_permissions IS
    'Per-user permission overrides. granted=TRUE adds, granted=FALSE explicitly denies.';

-- =============================================================================
-- DOWN migration notes:
--   DROP TABLE IF EXISTS user_permissions;
--   DROP TABLE IF EXISTS role_permissions;
--   DROP TABLE IF EXISTS permissions;
-- =============================================================================
