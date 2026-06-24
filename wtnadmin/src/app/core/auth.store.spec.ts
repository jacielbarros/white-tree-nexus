import { TestBed } from '@angular/core/testing';

import { AuthStore } from '@app/core/auth.store';
import { Me } from '@app/core/models';

function makeMe(partial: Partial<Me>): Me {
  return {
    user_id: 'u1',
    email: 'a@acme.com',
    full_name: 'A',
    is_super_admin: false,
    memberships: [],
    ...partial,
  };
}

describe('AuthStore', () => {
  let store: AuthStore;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({});
    store = TestBed.inject(AuthStore);
  });

  it('auto-seleciona a organização quando há um único vínculo', () => {
    store.setMe(makeMe({ memberships: [{ tenant_id: 't1', org_name: 'Org', role: 'org_admin' }] }));
    expect(store.activeOrgId()).toBe('t1');
    expect(store.currentRole()).toBe('org_admin');
  });

  it('não auto-seleciona quando há múltiplos vínculos (Consultor)', () => {
    store.setMe(
      makeMe({
        memberships: [
          { tenant_id: 't1', org_name: 'A', role: 'consultant' },
          { tenant_id: 't2', org_name: 'B', role: 'consultant' },
        ],
      }),
    );
    expect(store.activeOrgId()).toBeNull();
  });

  it('Super Admin ⇒ currentRole super_admin', () => {
    store.setMe(makeMe({ is_super_admin: true }));
    expect(store.isSuperAdmin()).toBe(true);
    expect(store.currentRole()).toBe('super_admin');
  });

  it('clear() encerra a sessão', () => {
    store.setToken('tok');
    expect(store.isAuthenticated()).toBe(true);
    store.clear();
    expect(store.isAuthenticated()).toBe(false);
    expect(store.activeOrgId()).toBeNull();
  });

  it('incrementa a versao do contexto apenas quando a organizacao ativa muda', () => {
    expect(store.orgContextVersion()).toBe(0);

    store.setActiveOrg('t1');
    expect(store.activeOrgId()).toBe('t1');
    expect(store.orgContextVersion()).toBe(1);

    store.setActiveOrg('t1');
    expect(store.orgContextVersion()).toBe(1);

    store.setActiveOrg('t2');
    expect(store.activeOrgId()).toBe('t2');
    expect(store.orgContextVersion()).toBe(2);
  });

  it('clear() tambem invalida o contexto de organizacao', () => {
    store.setActiveOrg('t1');
    const version = store.orgContextVersion();

    store.clear();

    expect(store.activeOrgId()).toBeNull();
    expect(store.orgContextVersion()).toBe(version + 1);
  });
});
