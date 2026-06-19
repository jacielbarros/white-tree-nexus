import { hasPermission } from '@app/core/permissions';

describe('hasPermission (espelho do RBAC do backend)', () => {
  it('super_admin tem todas as permissões da fundação', () => {
    expect(hasPermission('super_admin', 'manage_organizations')).toBe(true);
    expect(hasPermission('super_admin', 'manage_memberships')).toBe(true);
    expect(hasPermission('super_admin', 'invite_users')).toBe(true);
  });

  it('org_admin convida e gerencia, mas não cria organização', () => {
    expect(hasPermission('org_admin', 'invite_users')).toBe(true);
    expect(hasPermission('org_admin', 'manage_memberships')).toBe(true);
    expect(hasPermission('org_admin', 'manage_organizations')).toBe(false);
  });

  it('consultant convida mas não gerencia vínculos', () => {
    expect(hasPermission('consultant', 'invite_users')).toBe(true);
    expect(hasPermission('consultant', 'manage_memberships')).toBe(false);
  });

  it('client só visualiza a organização', () => {
    expect(hasPermission('client', 'view_organization')).toBe(true);
    expect(hasPermission('client', 'invite_users')).toBe(false);
  });

  it('papel nulo não tem permissão', () => {
    expect(hasPermission(null, 'view_organization')).toBe(false);
  });
});
