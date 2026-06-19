import { Injectable, computed, signal } from '@angular/core';

import { Me, Role } from '@app/core/models';

const TOKEN_KEY = 'wtn.token';
const ORG_KEY = 'wtn.activeOrg';

/** Estado de autenticação e contexto de organização (Signals). */
@Injectable({ providedIn: 'root' })
export class AuthStore {
  readonly token = signal<string | null>(localStorage.getItem(TOKEN_KEY));
  readonly me = signal<Me | null>(null);
  readonly activeOrgId = signal<string | null>(localStorage.getItem(ORG_KEY));

  readonly isAuthenticated = computed(() => this.token() !== null);
  readonly isSuperAdmin = computed(() => this.me()?.is_super_admin ?? false);

  /** Papel do usuário na organização ativa (super admin ⇒ super_admin). */
  readonly currentRole = computed<Role | null>(() => {
    const me = this.me();
    if (!me) {
      return null;
    }
    if (me.is_super_admin) {
      return 'super_admin';
    }
    const orgId = this.activeOrgId();
    const membership = me.memberships.find((m) => m.tenant_id === orgId);
    return membership ? membership.role : null;
  });

  setToken(token: string): void {
    this.token.set(token);
    localStorage.setItem(TOKEN_KEY, token);
  }

  setMe(me: Me): void {
    this.me.set(me);
    // Auto-seleciona a organização quando há exatamente um vínculo.
    if (!this.activeOrgId() && !me.is_super_admin && me.memberships.length === 1) {
      this.setActiveOrg(me.memberships[0].tenant_id);
    }
  }

  setActiveOrg(orgId: string | null): void {
    this.activeOrgId.set(orgId);
    if (orgId) {
      localStorage.setItem(ORG_KEY, orgId);
    } else {
      localStorage.removeItem(ORG_KEY);
    }
  }

  clear(): void {
    this.token.set(null);
    this.me.set(null);
    this.activeOrgId.set(null);
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(ORG_KEY);
  }
}
